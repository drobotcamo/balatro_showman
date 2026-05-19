"""
Build a YOLO detection dataset from labeled sidecar JSONs.

Each label session (python main.py extract) writes a .json sidecar next to each
saved crop. This script reads those sidecars, extracts full frames from the source
videos, and writes a YOLO-format dataset ready for training.

Usage:
    python main.py dataset build [--output-dir dataset] [--val-frac 0.2] [--jpg-quality 95]

Class naming convention: "type:name" (e.g. "joker:Strength", "tarot:Death").
Re-running is idempotent: already-extracted frames are skipped.
"""

import argparse
import json
import random
import sys
from collections import defaultdict
from pathlib import Path

import cv2
import yaml

from utils import progress

RECORDED = Path("recorded_gameplay_asset_images")


def _load_sidecars():
    sidecars = []
    for p in sorted(RECORDED.rglob("*.json")):
        try:
            data = json.loads(p.read_text())
            sidecars.append(data)
        except Exception as e:
            print(f"  WARNING: could not read {p}: {e}")
    return sidecars


def _class_label(sidecar):
    return f"{sidecar['asset_type']}:{sidecar['asset_name']}"


def _frame_key(sidecar):
    return (sidecar["video_path"], sidecar["frame_idx"])


def _yolo_bbox(sidecar):
    x0, y0, x1, y1 = sidecar["bbox_xyxy"]
    fw, fh = sidecar["frame_w"], sidecar["frame_h"]
    cx = (x0 + x1) / 2 / fw
    cy = (y0 + y1) / 2 / fh
    w  = (x1 - x0) / fw
    h  = (y1 - y0) / fh
    return cx, cy, w, h


def _split_groups(groups, class_to_groups, val_frac):
    """
    Assign each (video_path, frame_idx) group to train or val.
    - Groups containing a singleton class (only 1 labeled instance) are forced to train.
    - Remaining groups are split deterministically ~(1-val_frac)/val_frac.
    - Post-check: any class that ended up val-only is moved to train.
    """
    # Count instances per class
    class_counts = {cls: len(gks) for cls, gks in class_to_groups.items()}
    singleton_classes = {cls for cls, n in class_counts.items() if n == 1}

    forced_train = set()
    for cls in singleton_classes:
        for gk in class_to_groups[cls]:
            forced_train.add(gk)

    remaining = sorted(gk for gk in groups if gk not in forced_train)

    # Every k-th group goes to val
    val_set = set()
    if val_frac > 0 and remaining:
        k = max(2, round(1 / val_frac))
        for i, gk in enumerate(remaining):
            if (i + 1) % k == 0:
                val_set.add(gk)

    train_set = set(groups) - val_set

    # Post-check: move val-only-class groups to train
    moved = set()
    for cls, gks in class_to_groups.items():
        in_train = any(gk in train_set for gk in gks)
        if not in_train:
            for gk in gks:
                if gk in val_set:
                    val_set.remove(gk)
                    train_set.add(gk)
                    moved.add(gk)
            if moved:
                print(f"  NOTE: moved {cls!r} group(s) from val to train (only 1 frame for this class)")

    return train_set, val_set


def run(args):
    out_dir = Path(args.output_dir)
    for split in ("train", "val"):
        (out_dir / "images" / split).mkdir(parents=True, exist_ok=True)
        (out_dir / "labels" / split).mkdir(parents=True, exist_ok=True)

    sidecars = _load_sidecars()
    if not sidecars:
        print("No sidecar JSONs found under recorded_gameplay_asset_images/.")
        print("Label some footage first:  python main.py extract <video>")
        sys.exit(1)

    print(f"Found {len(sidecars)} labeled instances.")

    # Build class list
    all_labels = sorted({_class_label(s) for s in sidecars})
    label_to_idx = {lbl: i for i, lbl in enumerate(all_labels)}

    # Group by (video_path, frame_idx)
    groups: dict[tuple, list] = defaultdict(list)
    for s in sidecars:
        groups[_frame_key(s)].append(s)

    class_to_groups: dict[str, list] = defaultdict(list)
    for gk, ss in groups.items():
        for s in ss:
            class_to_groups[_class_label(s)].append(gk)
    # Deduplicate
    class_to_groups = {cls: list(dict.fromkeys(gks)) for cls, gks in class_to_groups.items()}

    train_keys, val_keys = _split_groups(list(groups.keys()), class_to_groups, args.val_frac)
    print(f"Split: {len(train_keys)} train frames, {len(val_keys)} val frames  "
          f"({len(all_labels)} classes)")

    # Open one VideoCapture per video path
    caps: dict[str, cv2.VideoCapture] = {}

    def get_cap(video_path):
        if video_path not in caps:
            caps[video_path] = cv2.VideoCapture(video_path)
            if not caps[video_path].isOpened():
                print(f"  ERROR: cannot open video {video_path}")
        return caps[video_path]

    n_written = 0
    n_skipped = 0

    all_groups = [(gk, "train") for gk in sorted(train_keys)] + \
                 [(gk, "val")   for gk in sorted(val_keys)]

    with progress(total=len(all_groups), desc="Extracting frames", unit="frame") as bar:
        for (video_path, frame_idx), split in all_groups:
            video_stem = Path(video_path).stem
            img_name = f"{video_stem}_frame{frame_idx:06d}.jpg"
            img_path = out_dir / "images" / split / img_name
            lbl_path = out_dir / "labels" / split / img_name.replace(".jpg", ".txt")

            bar.set_description(img_name[:40])
            bar.update(1)

            if img_path.exists() and lbl_path.exists():
                n_skipped += 1
                continue

            cap = get_cap(video_path)
            cap.set(cv2.CAP_PROP_POS_FRAMES, frame_idx)
            ret, frame = cap.read()
            if not ret:
                print(f"  WARNING: could not read frame {frame_idx} from {video_path}")
                continue

            cv2.imwrite(str(img_path), frame,
                        [cv2.IMWRITE_JPEG_QUALITY, args.jpg_quality])

            annotation_lines = []
            for s in groups[(video_path, frame_idx)]:
                cls_idx = label_to_idx[_class_label(s)]
                cx, cy, w, h = _yolo_bbox(s)
                annotation_lines.append(f"{cls_idx} {cx:.6f} {cy:.6f} {w:.6f} {h:.6f}")
            lbl_path.write_text("\n".join(annotation_lines))
            n_written += 1

    for cap in caps.values():
        cap.release()

    # Write classes.txt
    classes_txt = out_dir / "classes.txt"
    classes_txt.write_text("\n".join(all_labels))

    # Write dataset.yaml
    dataset_yaml = out_dir / "dataset.yaml"
    yaml_content = {
        "path": str(out_dir.resolve()),
        "train": "images/train",
        "val":   "images/val",
        "nc":    len(all_labels),
        "names": {i: lbl for i, lbl in enumerate(all_labels)},
    }
    dataset_yaml.write_text(yaml.dump(yaml_content, default_flow_style=False, allow_unicode=True))

    print(f"\nDataset written to {out_dir}/")
    print(f"  {n_written} frames extracted, {n_skipped} already existed (skipped)")
    print(f"  {len(all_labels)} classes  |  {len(train_keys)} train  /  {len(val_keys)} val frames")
    print(f"  Classes: {out_dir}/classes.txt")
    print(f"  YAML:    {out_dir}/dataset.yaml")
    print(f"\nTrain with:  python main.py train --data {dataset_yaml}")


def _add_args(parser):
    parser.add_argument("--output-dir", default="dataset",
                        help="Output directory for the YOLO dataset (default: dataset)")
    parser.add_argument("--val-frac", type=float, default=0.2,
                        help="Fraction of frames for validation (default: 0.2). Use 0 to train on all.")
    parser.add_argument("--jpg-quality", type=int, default=95,
                        help="JPEG quality for extracted frames (default: 95)")


def main():
    parser = argparse.ArgumentParser(description="Build YOLO dataset from labeled sidecars")
    _add_args(parser)
    run(parser.parse_args())


if __name__ == "__main__":
    main()
