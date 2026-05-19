"""
Build a synthetic YOLO detection dataset from game_asset_images/ wiki sprites.

Composites sprites at random positions and scales onto random background frames
extracted from gameplay footage. Writes a YOLO-format dataset ready for training.

Usage:
    python main.py dataset synthetic [--output-dir dataset_synthetic]
                                     [--n-backgrounds 500]
                                     [--sprites-per-frame 4]
                                     [--val-frac 0.2]

Domain gap note: wiki sprites don't perfectly match in-game rendering (video
compression shifts pixel values). This synthetic dataset gives full class
coverage as a baseline; fine-tune on real labeled footage for best accuracy.
"""

import random
from pathlib import Path

import cv2
import numpy as np
import yaml

from tools.assets import ASSET_TYPE_TO_DIR
from tools.videos import list_videos
from utils import progress

GAME_ASSETS = Path("game_asset_images")


def _load_sprites():
    """Return [(class_label, bgra_array), ...] for all sprites in game_asset_images/."""
    sprites = []
    for type_name, dir_name in ASSET_TYPE_TO_DIR.items():
        if dir_name is None:
            continue
        asset_dir = GAME_ASSETS / dir_name
        if not asset_dir.exists():
            continue
        for path in sorted(asset_dir.glob("*.png")):
            img = cv2.imread(str(path), cv2.IMREAD_UNCHANGED)
            if img is None:
                continue
            # Normalise to 4-channel BGRA
            if img.ndim == 2:
                img = cv2.cvtColor(img, cv2.COLOR_GRAY2BGRA)
            elif img.shape[2] == 3:
                alpha = np.full((*img.shape[:2], 1), 255, dtype=np.uint8)
                img = np.concatenate([img, alpha], axis=2)
            name = path.stem.replace("_", " ")
            sprites.append((f"{type_name}:{name}", img))
    return sprites


def _extract_backgrounds(n_frames):
    """Extract n_frames random frames spread across all available footage videos."""
    videos = list_videos()
    if not videos:
        return []
    frames = []
    per_video = max(1, n_frames // len(videos))
    with progress(total=n_frames, desc="Extracting backgrounds", unit="frame") as bar:
        for path in videos.values():
            cap = cv2.VideoCapture(str(path))
            total = int(cap.get(cv2.CAP_PROP_FRAME_COUNT))
            if total == 0:
                cap.release()
                continue
            indices = random.sample(range(total), min(per_video, total))
            for idx in sorted(indices):
                cap.set(cv2.CAP_PROP_POS_FRAMES, idx)
                ret, frame = cap.read()
                if ret:
                    frames.append(frame)
                    bar.update(1)
            cap.release()
    return frames


def _iou(a, b):
    ix1, iy1 = max(a[0], b[0]), max(a[1], b[1])
    ix2, iy2 = min(a[2], b[2]), min(a[3], b[3])
    inter = max(0, ix2 - ix1) * max(0, iy2 - iy1)
    union = (a[2]-a[0])*(a[3]-a[1]) + (b[2]-b[0])*(b[3]-b[1]) - inter
    return inter / union if union > 0 else 0.0


def _composite(frame, sprite_bgra, scale):
    """
    Paste sprite onto a copy of frame at a random valid position.
    Returns (modified_frame, bbox_xyxy) or (None, None) if sprite doesn't fit.
    """
    fh, fw = frame.shape[:2]
    sh, sw = sprite_bgra.shape[:2]
    new_w = max(1, int(sw * scale))
    new_h = max(1, int(sh * scale))
    if new_w >= fw or new_h >= fh:
        return None, None

    resized = cv2.resize(sprite_bgra, (new_w, new_h), interpolation=cv2.INTER_AREA)
    x = random.randint(0, fw - new_w)
    y = random.randint(0, fh - new_h)

    out = frame.copy()
    bgr   = resized[:, :, :3].astype(np.float32)
    alpha = resized[:, :, 3:].astype(np.float32) / 255.0
    region = out[y:y+new_h, x:x+new_w].astype(np.float32)
    out[y:y+new_h, x:x+new_w] = (bgr * alpha + region * (1.0 - alpha)).astype(np.uint8)
    return out, (x, y, x + new_w, y + new_h)


def _to_yolo(bbox, fw, fh):
    x1, y1, x2, y2 = bbox
    return (x1+x2)/2/fw, (y1+y2)/2/fh, (x2-x1)/fw, (y2-y1)/fh


def run(args):
    out_dir = Path(args.output_dir)
    for split in ("train", "val"):
        (out_dir / "images" / split).mkdir(parents=True, exist_ok=True)
        (out_dir / "labels" / split).mkdir(parents=True, exist_ok=True)

    print("Loading sprites...")
    sprites = _load_sprites()
    if not sprites:
        print("No sprites found in game_asset_images/.")
        return
    n_types = len({lbl.split(":")[0] for lbl, _ in sprites})
    print(f"  {len(sprites)} sprites across {n_types} types")

    all_labels = sorted({lbl for lbl, _ in sprites})
    label_to_idx = {lbl: i for i, lbl in enumerate(all_labels)}

    print(f"Extracting {args.n_backgrounds} background frames from footage...")
    backgrounds = _extract_backgrounds(args.n_backgrounds)
    if not backgrounds:
        print("No footage found. Download some with: python main.py download <url>")
        return
    print(f"  Got {len(backgrounds)} background frames")

    random.shuffle(backgrounds)
    n_train = int(len(backgrounds) * (1 - args.val_frac))

    # Scale sprites relative to 1280px reference width
    base_scale = backgrounds[0].shape[1] / 1280

    print(f"Compositing ({args.sprites_per_frame} sprites/frame)...")
    n_written = 0

    with progress(total=len(backgrounds), desc="Compositing", unit="frame") as bar:
        for i, bg in enumerate(backgrounds):
            split = "train" if i < n_train else "val"
            fh, fw = bg.shape[:2]
            frame = bg.copy()
            placed = []  # [(class_idx, bbox_xyxy)]

            # Draw a fresh random batch — 3x pool so we have fallbacks for failed placements
            batch = random.sample(sprites, min(args.sprites_per_frame * 3, len(sprites)))

            for label, sprite in batch:
                if len(placed) >= args.sprites_per_frame:
                    break
                scale = base_scale * random.uniform(0.8, 1.2)
                for _ in range(8):  # retry positions to avoid overlaps
                    candidate, bbox = _composite(frame, sprite, scale)
                    if bbox is None:
                        break
                    if not any(_iou(bbox, p[1]) > 0.15 for p in placed):
                        frame = candidate
                        placed.append((label_to_idx[label], bbox))
                        break

            if placed:
                img_name = f"synthetic_{i:06d}.jpg"
                cv2.imwrite(
                    str(out_dir / "images" / split / img_name),
                    frame,
                    [cv2.IMWRITE_JPEG_QUALITY, 95],
                )
                lines = [
                    f"{cls} {' '.join(f'{v:.6f}' for v in _to_yolo(bbox, fw, fh))}"
                    for cls, bbox in placed
                ]
                (out_dir / "labels" / split / img_name.replace(".jpg", ".txt")).write_text(
                    "\n".join(lines)
                )
                n_written += 1

            bar.update(1)

    # Write classes.txt and dataset.yaml
    (out_dir / "classes.txt").write_text("\n".join(all_labels))

    dataset_yaml = out_dir / "dataset.yaml"
    dataset_yaml.write_text(yaml.dump(
        {
            "path":  str(out_dir.resolve()),
            "train": "images/train",
            "val":   "images/val",
            "nc":    len(all_labels),
            "names": {i: lbl for i, lbl in enumerate(all_labels)},
        },
        default_flow_style=False,
        allow_unicode=True,
    ))

    n_tr = len(list((out_dir / "images" / "train").glob("*.jpg")))
    n_va = len(list((out_dir / "images" / "val").glob("*.jpg")))
    print(f"\nSynthetic dataset written to {out_dir}/")
    print(f"  {len(all_labels)} classes  |  {n_tr} train  /  {n_va} val images")
    print(f"  YAML: {dataset_yaml}")
    print(f"\nTrain with:  python main.py train --data {dataset_yaml} --name balatro_synthetic")


def _add_args(parser):
    parser.add_argument("--output-dir", default="dataset_synthetic",
                        help="Output directory (default: dataset_synthetic)")
    parser.add_argument("--n-backgrounds", type=int, default=200,
                        help="Background frames to extract from footage (default: 200)")
    parser.add_argument("--sprites-per-frame", type=int, default=4,
                        help="Sprites composited per frame (default: 4)")
    parser.add_argument("--val-frac", type=float, default=0.2,
                        help="Fraction of frames held out for validation (default: 0.2)")


def main():
    import argparse
    parser = argparse.ArgumentParser(
        description="Build synthetic YOLO dataset from wiki sprites"
    )
    _add_args(parser)
    run(parser.parse_args())


if __name__ == "__main__":
    main()
