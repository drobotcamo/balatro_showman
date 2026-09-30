from __future__ import annotations

import os
import sqlite3
from datetime import datetime, timezone
from pathlib import Path
from typing import Dict, List, Optional, Tuple

from pydantic import BaseModel, root_validator, validator

LABEL_ROOT = Path("recorded_gameplay_asset_images")
DB_PATH = LABEL_ROOT / "labels.db"
SCHEMA_VERSION = 1


# ── Exceptions ────────────────────────────────────────────────────────────────

class LabelStoreError(Exception):
    """Base exception for all label store failures."""


class SchemaMismatchError(LabelStoreError):
    """DB schema version does not match this code's expected version."""


class LabelNotFoundError(LabelStoreError):
    """Requested label ID does not exist."""


# ── Data model ────────────────────────────────────────────────────────────────

class Label(BaseModel):
    id: Optional[int] = None
    video_path: str
    frame_idx: int
    frame_w: int
    frame_h: int
    asset_type: str
    asset_name: str
    bbox_xyxy: Tuple[int, int, int, int]
    created_at: Optional[str] = None

    @validator("frame_idx", "frame_w", "frame_h")
    def must_be_positive(cls, v: int) -> int:
        if v <= 0:
            raise ValueError(f"must be positive, got {v}")
        return v

    @validator("video_path")
    def must_be_bare_filename(cls, v: str) -> str:
        p = Path(v)
        if p.parent != Path("."):
            raise ValueError(
                f"video_path must be a bare filename (e.g. 'BU1.mp4'), got {v!r}"
            )
        return v

    @root_validator
    def bbox_must_be_valid(cls, values: dict) -> dict:
        bbox = values.get("bbox_xyxy")
        if bbox is None:
            return values
        x0, y0, x1, y1 = bbox
        if x0 < 0 or y0 < 0:
            raise ValueError(f"bbox coordinates must be non-negative, got {list(bbox)}")
        if x1 <= x0:
            raise ValueError(f"bbox x1 must be > x0, got {list(bbox)}")
        if y1 <= y0:
            raise ValueError(f"bbox y1 must be > y0, got {list(bbox)}")
        return values

    def crop_filename(self) -> str:
        if self.id is None:
            raise RuntimeError("crop_filename() called before label has an id")
        return f"{self.id:06d}.png"

    def crop_path(self, root: Path) -> Path:
        return root / self.asset_type / self.crop_filename()


# ── Internal helpers ──────────────────────────────────────────────────────────

def _row_to_label(row: sqlite3.Row) -> Label:
    return Label(
        id=row["id"],
        video_path=row["video_path"],
        frame_idx=row["frame_idx"],
        frame_w=row["frame_w"],
        frame_h=row["frame_h"],
        asset_type=row["asset_type"],
        asset_name=row["asset_name"],
        bbox_xyxy=(row["bbox_x0"], row["bbox_y0"], row["bbox_x1"], row["bbox_y1"]),
        created_at=row["created_at"],
    )


# ── Store ─────────────────────────────────────────────────────────────────────

class LabelStore:
    def __init__(self, db_path: Path = DB_PATH) -> None:
        db_path = Path(db_path)
        db_path.parent.mkdir(parents=True, exist_ok=True)
        self._root = db_path.parent
        self._conn = sqlite3.connect(
            str(db_path), isolation_level=None, check_same_thread=False
        )
        self._conn.row_factory = sqlite3.Row
        self._conn.execute("PRAGMA journal_mode=WAL")
        self._conn.execute("PRAGMA foreign_keys=ON")
        self._ensure_schema()

    def _ensure_schema(self) -> None:
        cur = self._conn.execute(
            "SELECT name FROM sqlite_master WHERE type='table' AND name='schema_version'"
        )
        has_version_table = cur.fetchone() is not None

        if has_version_table:
            row = self._conn.execute("SELECT version FROM schema_version").fetchone()
            if row is not None and row[0] != SCHEMA_VERSION:
                raise SchemaMismatchError(
                    f"DB schema version {row[0]} does not match expected {SCHEMA_VERSION}. "
                    "Run python tools/migrate_labels.py to upgrade."
                )

        self._conn.execute(
            "CREATE TABLE IF NOT EXISTS schema_version (version INTEGER NOT NULL)"
        )
        self._conn.execute(
            """
            CREATE TABLE IF NOT EXISTS labels (
                id         INTEGER PRIMARY KEY AUTOINCREMENT,
                video_path TEXT    NOT NULL,
                frame_idx  INTEGER NOT NULL,
                frame_w    INTEGER NOT NULL,
                frame_h    INTEGER NOT NULL,
                asset_type TEXT    NOT NULL,
                asset_name TEXT    NOT NULL,
                bbox_x0    INTEGER NOT NULL,
                bbox_y0    INTEGER NOT NULL,
                bbox_x1    INTEGER NOT NULL,
                bbox_y1    INTEGER NOT NULL,
                created_at TEXT    NOT NULL
            )
            """
        )
        self._conn.execute(
            "CREATE INDEX IF NOT EXISTS idx_labels_frame ON labels (video_path, frame_idx)"
        )
        if not has_version_table:
            self._conn.execute("INSERT INTO schema_version VALUES (?)", (SCHEMA_VERSION,))

    def close(self) -> None:
        self._conn.close()

    def __enter__(self) -> "LabelStore":
        return self

    def __exit__(self, *args) -> None:
        self.close()

    # ── Write operations ──────────────────────────────────────────────────────

    def add(self, label: Label, crop_png: bytes) -> Label:
        if not crop_png:
            raise LabelStoreError("crop_png must not be empty")

        x0, y0, x1, y1 = label.bbox_xyxy
        created_at = datetime.now(timezone.utc).strftime("%Y-%m-%dT%H:%M:%SZ")

        self._conn.execute("BEGIN")
        try:
            cur = self._conn.execute(
                """
                INSERT INTO labels
                    (video_path, frame_idx, frame_w, frame_h, asset_type, asset_name,
                     bbox_x0, bbox_y0, bbox_x1, bbox_y1, created_at)
                VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?)
                """,
                (
                    label.video_path, label.frame_idx, label.frame_w, label.frame_h,
                    label.asset_type, label.asset_name, x0, y0, x1, y1, created_at,
                ),
            )
            row_id = cur.lastrowid
            saved = label.copy(update={"id": row_id, "created_at": created_at})

            crop_path = saved.crop_path(self._root)
            crop_path.parent.mkdir(parents=True, exist_ok=True)
            tmp_path = crop_path.with_suffix(".png.tmp")
            try:
                tmp_path.write_bytes(crop_png)
                os.replace(str(tmp_path), str(crop_path))
            except Exception as e:
                tmp_path.unlink(missing_ok=True)
                raise LabelStoreError(f"Failed to write crop PNG: {e}") from e

            self._conn.execute("COMMIT")
            return saved
        except Exception:
            self._conn.execute("ROLLBACK")
            raise

    def delete(self, label_id: int) -> Label:
        row = self._conn.execute(
            "SELECT * FROM labels WHERE id = ?", (label_id,)
        ).fetchone()
        if row is None:
            raise LabelNotFoundError(f"Label {label_id} not found")

        label = _row_to_label(row)
        self._conn.execute("DELETE FROM labels WHERE id = ?", (label_id,))

        crop_path = label.crop_path(self._root)
        if crop_path.exists():
            crop_path.unlink()

        return label

    def restore(self, label: Label, crop_png: bytes) -> Label:
        if label.id is None:
            raise LabelStoreError("Cannot restore a label without an id")

        x0, y0, x1, y1 = label.bbox_xyxy
        created_at = label.created_at or datetime.now(timezone.utc).strftime(
            "%Y-%m-%dT%H:%M:%SZ"
        )

        self._conn.execute("BEGIN")
        try:
            existing = self._conn.execute(
                "SELECT id FROM labels WHERE id = ?", (label.id,)
            ).fetchone()

            if existing is None:
                self._conn.execute(
                    """
                    INSERT INTO labels
                        (id, video_path, frame_idx, frame_w, frame_h, asset_type, asset_name,
                         bbox_x0, bbox_y0, bbox_x1, bbox_y1, created_at)
                    VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?)
                    """,
                    (
                        label.id, label.video_path, label.frame_idx, label.frame_w,
                        label.frame_h, label.asset_type, label.asset_name,
                        x0, y0, x1, y1, created_at,
                    ),
                )
                restored = label
            else:
                # id already taken (shouldn't happen in single-user tool), auto-assign
                cur = self._conn.execute(
                    """
                    INSERT INTO labels
                        (video_path, frame_idx, frame_w, frame_h, asset_type, asset_name,
                         bbox_x0, bbox_y0, bbox_x1, bbox_y1, created_at)
                    VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?)
                    """,
                    (
                        label.video_path, label.frame_idx, label.frame_w, label.frame_h,
                        label.asset_type, label.asset_name, x0, y0, x1, y1, created_at,
                    ),
                )
                restored = label.copy(update={"id": cur.lastrowid})

            crop_path = restored.crop_path(self._root)
            crop_path.parent.mkdir(parents=True, exist_ok=True)
            tmp_path = crop_path.with_suffix(".png.tmp")
            try:
                tmp_path.write_bytes(crop_png)
                os.replace(str(tmp_path), str(crop_path))
            except Exception as e:
                tmp_path.unlink(missing_ok=True)
                raise LabelStoreError(f"Failed to write crop PNG on restore: {e}") from e

            self._conn.execute("COMMIT")
            return restored
        except Exception:
            self._conn.execute("ROLLBACK")
            raise

    # ── Read operations ───────────────────────────────────────────────────────

    def get(self, label_id: int) -> Label:
        row = self._conn.execute(
            "SELECT * FROM labels WHERE id = ?", (label_id,)
        ).fetchone()
        if row is None:
            raise LabelNotFoundError(f"Label {label_id} not found")
        return _row_to_label(row)

    def all(
        self,
        *,
        asset_type: Optional[str] = None,
        video_path: Optional[str] = None,
    ) -> List[Label]:
        query = "SELECT * FROM labels"
        params: list = []
        conditions = []
        if asset_type is not None:
            conditions.append("asset_type = ?")
            params.append(asset_type)
        if video_path is not None:
            conditions.append("video_path = ?")
            params.append(video_path)
        if conditions:
            query += " WHERE " + " AND ".join(conditions)
        query += " ORDER BY id ASC"
        rows = self._conn.execute(query, params).fetchall()
        return [_row_to_label(r) for r in rows]

    def count_by_frame(self) -> Dict[Tuple[str, int], int]:
        rows = self._conn.execute(
            "SELECT video_path, frame_idx, COUNT(*) as cnt "
            "FROM labels GROUP BY video_path, frame_idx"
        ).fetchall()
        return {(r["video_path"], r["frame_idx"]): r["cnt"] for r in rows}

    def frame_label_count(self, video_path: str, frame_idx: int) -> int:
        row = self._conn.execute(
            "SELECT COUNT(*) FROM labels WHERE video_path = ? AND frame_idx = ?",
            (video_path, frame_idx),
        ).fetchone()
        return row[0] if row else 0

    def crop_path(self, label_id: int) -> Path:
        label = self.get(label_id)
        return label.crop_path(self._root)
