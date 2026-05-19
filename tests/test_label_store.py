"""Tests for label_store.py — all tests use tmp_path, no writes to project tree."""
import pytest
from pathlib import Path
from pydantic import ValidationError

from label_store import (
    Label,
    LabelNotFoundError,
    LabelStore,
    LabelStoreError,
    SchemaMismatchError,
    SCHEMA_VERSION,
)

# ── Fixtures ──────────────────────────────────────────────────────────────────

VALID_LABEL_KWARGS = dict(
    video_path="BU1.mp4",
    frame_idx=100,
    frame_w=1920,
    frame_h=1080,
    asset_type="joker",
    asset_name="Strength",
    bbox_xyxy=(10, 20, 100, 200),
)
FAKE_PNG = b"\x89PNG\r\n\x1a\n" + b"\x00" * 64  # minimal fake PNG bytes


def make_store(tmp_path: Path) -> LabelStore:
    return LabelStore(tmp_path / "labels.db")


# ── Label model validation ────────────────────────────────────────────────────

def test_label_valid():
    Label(**VALID_LABEL_KWARGS)


def test_label_frame_idx_zero_fails():
    with pytest.raises(ValidationError, match="positive"):
        Label(**{**VALID_LABEL_KWARGS, "frame_idx": 0})


def test_label_frame_w_negative_fails():
    with pytest.raises(ValidationError, match="positive"):
        Label(**{**VALID_LABEL_KWARGS, "frame_w": -1})


def test_label_frame_h_zero_fails():
    with pytest.raises(ValidationError, match="positive"):
        Label(**{**VALID_LABEL_KWARGS, "frame_h": 0})


def test_label_bbox_x1_less_than_x0_fails():
    with pytest.raises(ValidationError, match="x1 must be"):
        Label(**{**VALID_LABEL_KWARGS, "bbox_xyxy": (100, 20, 50, 200)})


def test_label_bbox_x1_equal_x0_fails():
    with pytest.raises(ValidationError, match="x1 must be"):
        Label(**{**VALID_LABEL_KWARGS, "bbox_xyxy": (100, 20, 100, 200)})


def test_label_bbox_y1_equal_y0_fails():
    with pytest.raises(ValidationError, match="y1 must be"):
        Label(**{**VALID_LABEL_KWARGS, "bbox_xyxy": (10, 200, 100, 200)})


def test_label_bbox_negative_coord_fails():
    with pytest.raises(ValidationError, match="non-negative"):
        Label(**{**VALID_LABEL_KWARGS, "bbox_xyxy": (-1, 20, 100, 200)})


def test_label_video_path_multicomponent_fails():
    with pytest.raises(ValidationError, match="bare filename"):
        Label(**{**VALID_LABEL_KWARGS, "video_path": "gameplay_sources/BU1.mp4"})


def test_label_video_path_absolute_fails():
    with pytest.raises(ValidationError, match="bare filename"):
        Label(**{**VALID_LABEL_KWARGS, "video_path": "/absolute/path/BU1.mp4"})


def test_label_crop_filename_requires_id():
    label = Label(**VALID_LABEL_KWARGS)
    with pytest.raises(RuntimeError, match="before label has an id"):
        label.crop_filename()


def test_label_crop_filename_zero_padded():
    label = Label(**{**VALID_LABEL_KWARGS, "id": 42})
    assert label.crop_filename() == "000042.png"


def test_label_crop_path(tmp_path):
    label = Label(**{**VALID_LABEL_KWARGS, "id": 7})
    p = label.crop_path(tmp_path)
    assert p == tmp_path / "joker" / "000007.png"


# ── LabelStore lifecycle ──────────────────────────────────────────────────────

def test_fresh_db_creates_schema(tmp_path):
    with make_store(tmp_path) as store:
        row = store._conn.execute("SELECT version FROM schema_version").fetchone()
        assert row[0] == SCHEMA_VERSION


def test_reopen_succeeds(tmp_path):
    with make_store(tmp_path):
        pass
    with make_store(tmp_path) as store:
        assert store.all() == []


def test_schema_mismatch_raises(tmp_path):
    db_path = tmp_path / "labels.db"
    with make_store(tmp_path):
        pass
    # manually corrupt the version
    import sqlite3
    conn = sqlite3.connect(str(db_path))
    conn.execute("UPDATE schema_version SET version = 999")
    conn.commit()
    conn.close()

    with pytest.raises(SchemaMismatchError, match="999"):
        LabelStore(db_path)


def test_context_manager(tmp_path):
    with make_store(tmp_path) as store:
        assert store.all() == []


# ── add ───────────────────────────────────────────────────────────────────────

def test_add_returns_label_with_id_and_created_at(tmp_path):
    with make_store(tmp_path) as store:
        label = Label(**VALID_LABEL_KWARGS)
        saved = store.add(label, FAKE_PNG)
    assert saved.id is not None
    assert saved.created_at is not None


def test_add_png_exists_at_correct_path(tmp_path):
    with make_store(tmp_path) as store:
        saved = store.add(Label(**VALID_LABEL_KWARGS), FAKE_PNG)
        crop_path = saved.crop_path(tmp_path)
    assert crop_path.exists()


def test_add_png_bytes_match(tmp_path):
    with make_store(tmp_path) as store:
        saved = store.add(Label(**VALID_LABEL_KWARGS), FAKE_PNG)
        crop_path = saved.crop_path(tmp_path)
    assert crop_path.read_bytes() == FAKE_PNG


def test_add_two_labels_same_frame_get_distinct_ids(tmp_path):
    with make_store(tmp_path) as store:
        a = store.add(Label(**VALID_LABEL_KWARGS), FAKE_PNG)
        b = store.add(Label(**{**VALID_LABEL_KWARGS, "asset_name": "Abstract Joker"}), FAKE_PNG)
    assert a.id != b.id


def test_add_empty_png_raises_and_no_row(tmp_path):
    with make_store(tmp_path) as store:
        with pytest.raises(LabelStoreError):
            store.add(Label(**VALID_LABEL_KWARGS), b"")
        assert store.all() == []


def test_add_atomicity_png_failure_leaves_no_row(tmp_path):
    # Block mkdir by placing a file where the type directory would be
    type_dir = tmp_path / "joker"
    type_dir.write_text("I am a file, blocking mkdir")

    with make_store(tmp_path) as store:
        with pytest.raises((LabelStoreError, Exception)):
            store.add(Label(**VALID_LABEL_KWARGS), FAKE_PNG)
        assert store.all() == []


# ── get ───────────────────────────────────────────────────────────────────────

def test_get_returns_matching_label(tmp_path):
    with make_store(tmp_path) as store:
        saved = store.add(Label(**VALID_LABEL_KWARGS), FAKE_PNG)
        fetched = store.get(saved.id)
    assert fetched.id == saved.id
    assert fetched.asset_name == saved.asset_name
    assert fetched.bbox_xyxy == saved.bbox_xyxy


def test_get_unknown_id_raises(tmp_path):
    with make_store(tmp_path) as store:
        with pytest.raises(LabelNotFoundError):
            store.get(9999)


# ── delete ────────────────────────────────────────────────────────────────────

def test_delete_removes_row(tmp_path):
    with make_store(tmp_path) as store:
        saved = store.add(Label(**VALID_LABEL_KWARGS), FAKE_PNG)
        store.delete(saved.id)
        with pytest.raises(LabelNotFoundError):
            store.get(saved.id)


def test_delete_removes_png(tmp_path):
    with make_store(tmp_path) as store:
        saved = store.add(Label(**VALID_LABEL_KWARGS), FAKE_PNG)
        crop_path = saved.crop_path(tmp_path)
        store.delete(saved.id)
    assert not crop_path.exists()


def test_delete_returns_deleted_label(tmp_path):
    with make_store(tmp_path) as store:
        saved = store.add(Label(**VALID_LABEL_KWARGS), FAKE_PNG)
        deleted = store.delete(saved.id)
    assert deleted.id == saved.id
    assert deleted.asset_name == "Strength"


def test_delete_unknown_id_raises(tmp_path):
    with make_store(tmp_path) as store:
        with pytest.raises(LabelNotFoundError):
            store.delete(9999)


def test_delete_missing_png_still_removes_row(tmp_path):
    with make_store(tmp_path) as store:
        saved = store.add(Label(**VALID_LABEL_KWARGS), FAKE_PNG)
        saved.crop_path(tmp_path).unlink()  # manually remove PNG first
        store.delete(saved.id)  # should not raise
        with pytest.raises(LabelNotFoundError):
            store.get(saved.id)


# ── all ───────────────────────────────────────────────────────────────────────

def test_all_returns_all_labels_ascending(tmp_path):
    with make_store(tmp_path) as store:
        a = store.add(Label(**VALID_LABEL_KWARGS), FAKE_PNG)
        b = store.add(Label(**{**VALID_LABEL_KWARGS, "asset_type": "tarot", "asset_name": "Death"}), FAKE_PNG)
        results = store.all()
    assert [r.id for r in results] == [a.id, b.id]


def test_all_asset_type_filter(tmp_path):
    with make_store(tmp_path) as store:
        store.add(Label(**VALID_LABEL_KWARGS), FAKE_PNG)
        store.add(Label(**{**VALID_LABEL_KWARGS, "asset_type": "tarot", "asset_name": "Death"}), FAKE_PNG)
        results = store.all(asset_type="joker")
    assert all(r.asset_type == "joker" for r in results)
    assert len(results) == 1


def test_all_video_path_filter(tmp_path):
    with make_store(tmp_path) as store:
        store.add(Label(**VALID_LABEL_KWARGS), FAKE_PNG)
        store.add(Label(**{**VALID_LABEL_KWARGS, "video_path": "BU2.mp4"}), FAKE_PNG)
        results = store.all(video_path="BU2.mp4")
    assert len(results) == 1
    assert results[0].video_path == "BU2.mp4"


def test_all_empty_db_returns_empty_list(tmp_path):
    with make_store(tmp_path) as store:
        assert store.all() == []


# ── count_by_frame ────────────────────────────────────────────────────────────

def test_count_by_frame_empty(tmp_path):
    with make_store(tmp_path) as store:
        assert store.count_by_frame() == {}


def test_count_by_frame_groups_correctly(tmp_path):
    with make_store(tmp_path) as store:
        for name in ["Strength", "Abstract Joker", "Bloodstone"]:
            store.add(Label(**{**VALID_LABEL_KWARGS, "asset_name": name}), FAKE_PNG)
        store.add(Label(**{**VALID_LABEL_KWARGS, "frame_idx": 200, "asset_name": "Death",
                          "asset_type": "tarot"}), FAKE_PNG)
        counts = store.count_by_frame()

    assert counts[("BU1.mp4", 100)] == 3
    assert counts[("BU1.mp4", 200)] == 1


# ── frame_label_count ─────────────────────────────────────────────────────────

def test_frame_label_count_zero_for_unknown(tmp_path):
    with make_store(tmp_path) as store:
        assert store.frame_label_count("BU1.mp4", 999) == 0


def test_frame_label_count_correct_after_adds(tmp_path):
    with make_store(tmp_path) as store:
        store.add(Label(**VALID_LABEL_KWARGS), FAKE_PNG)
        store.add(Label(**{**VALID_LABEL_KWARGS, "asset_name": "Abstract Joker"}), FAKE_PNG)
        assert store.frame_label_count("BU1.mp4", 100) == 2


def test_frame_label_count_updates_after_delete(tmp_path):
    with make_store(tmp_path) as store:
        saved = store.add(Label(**VALID_LABEL_KWARGS), FAKE_PNG)
        store.add(Label(**{**VALID_LABEL_KWARGS, "asset_name": "Abstract Joker"}), FAKE_PNG)
        store.delete(saved.id)
        assert store.frame_label_count("BU1.mp4", 100) == 1


# ── restore ───────────────────────────────────────────────────────────────────

def test_restore_recovers_original_id(tmp_path):
    with make_store(tmp_path) as store:
        saved = store.add(Label(**VALID_LABEL_KWARGS), FAKE_PNG)
        original_id = saved.id
        store.delete(original_id)
        restored = store.restore(saved, FAKE_PNG)
    assert restored.id == original_id


def test_restore_png_exists_again(tmp_path):
    with make_store(tmp_path) as store:
        saved = store.add(Label(**VALID_LABEL_KWARGS), FAKE_PNG)
        crop_path = saved.crop_path(tmp_path)
        store.delete(saved.id)
        assert not crop_path.exists()
        store.restore(saved, FAKE_PNG)
    assert crop_path.exists()


def test_restore_row_retrievable(tmp_path):
    with make_store(tmp_path) as store:
        saved = store.add(Label(**VALID_LABEL_KWARGS), FAKE_PNG)
        store.delete(saved.id)
        store.restore(saved, FAKE_PNG)
        fetched = store.get(saved.id)
    assert fetched.asset_name == "Strength"
