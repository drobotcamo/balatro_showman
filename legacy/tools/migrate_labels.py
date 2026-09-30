"""
One-time migration from JSON sidecar files to the SQLite label store.

Usage:
    python tools/migrate_labels.py              # dry run — shows what would happen
    python tools/migrate_labels.py --execute    # write to labels.db
    python tools/migrate_labels.py --execute --cleanup  # also delete old JSON+PNG pairs
    python tools/migrate_labels.py --execute --force    # re-migrate even if DB has rows
"""

import argparse
import json
import sys
from pathlib import Path

from pydantic import ValidationError

from label_store import LABEL_ROOT, DB_PATH, Label, LabelStore, LabelStoreError


def _parse_sidecar(json_path: Path):
    """Parse a sidecar JSON and return (Label, png_path, raw_data) or raise."""
    raw = json.loads(json_path.read_text())

    asset_type = raw.get("asset_type") or json_path.parent.name
    label = Label(
        video_path=Path(raw["video_path"]).name,  # normalise legacy absolute paths
        frame_idx=raw["frame_idx"],
        frame_w=raw["frame_w"],
        frame_h=raw["frame_h"],
        asset_type=asset_type,
        asset_name=raw["asset_name"],
        bbox_xyxy=tuple(raw["bbox_xyxy"]),
    )
    png_path = json_path.with_suffix(".png")
    return label, png_path


def run(args):
    json_files = sorted(p for p in LABEL_ROOT.rglob("*.json") if p.name != "labels.db")

    if not json_files:
        print("No sidecar JSON files found — nothing to migrate.")
        return

    print(f"Found {len(json_files)} sidecar JSON file(s) under {LABEL_ROOT}/\n")

    # Parse and validate all sidecars up front, collect failures
    parsed = []
    warnings = []
    for jp in json_files:
        try:
            label, png_path = _parse_sidecar(jp)
        except (KeyError, ValidationError, json.JSONDecodeError, ValueError) as e:
            warnings.append(f"  SKIP {jp.relative_to(LABEL_ROOT)}: {e}")
            continue

        if not png_path.exists():
            warnings.append(f"  SKIP {jp.relative_to(LABEL_ROOT)}: paired PNG not found at {png_path.name}")
            continue

        parsed.append((label, png_path, jp))

    if warnings:
        print("Warnings:")
        for w in warnings:
            print(w)
        print()

    print(f"Ready to migrate: {len(parsed)} labels  |  skipped: {len(warnings)}")

    if not args.execute:
        print("\n[DRY RUN] No changes made. Pass --execute to write to labels.db.")
        if parsed:
            print(f"  Would insert {len(parsed)} rows into {DB_PATH}")
            if args.cleanup:
                print(f"  Would delete {len(parsed) * 2} files (JSON + PNG pairs)")
        return

    # Check for existing data
    with LabelStore() as store:
        existing = store.all()

    if existing and not args.force:
        print(
            f"\nERROR: labels.db already has {len(existing)} rows. "
            "Pass --force to re-migrate anyway (existing rows are NOT cleared)."
        )
        sys.exit(1)

    n_ok = 0
    n_err = 0

    with LabelStore() as store:
        for label, png_path, json_path in parsed:
            try:
                png_bytes = png_path.read_bytes()
                store.add(label, png_bytes)
                n_ok += 1
            except LabelStoreError as e:
                print(f"  ERROR inserting {json_path.name}: {e}")
                n_err += 1
                continue

            if args.cleanup:
                json_path.unlink()
                png_path.unlink()

    print(f"\nMigration complete: {n_ok} inserted, {n_err} errors, {len(warnings)} skipped.")
    if args.cleanup:
        print(f"Old JSON+PNG pairs deleted ({n_ok * 2} files).")
    else:
        print("Old JSON+PNG files left in place (pass --cleanup to remove them).")


def main():
    parser = argparse.ArgumentParser(
        description="Migrate JSON sidecar labels to the SQLite label store"
    )
    parser.add_argument(
        "--execute", action="store_true",
        help="Actually write to labels.db (default is dry run)"
    )
    parser.add_argument(
        "--cleanup", action="store_true",
        help="Delete old JSON+PNG sidecar pairs after successful insert (requires --execute)"
    )
    parser.add_argument(
        "--force", action="store_true",
        help="Migrate even if labels.db already has rows"
    )
    run(parser.parse_args())


if __name__ == "__main__":
    main()
