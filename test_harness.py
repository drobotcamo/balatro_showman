import argparse
import json
import random
import sys
from datetime import datetime
from pathlib import Path

import cv2

from utils import progress

from detectors.yolo_detector import YoloDetector
from tools.assets import ASSET_TYPE_TO_DIR

COLORS = [
    (100, 100, 255),
    (100, 255, 100),
    (255, 100, 100),
    (100, 255, 255),
    (255, 100, 255),
    (255, 255, 100),
]


def annotate(frame, detections):
    out = frame.copy()
    for i, det in enumerate(detections):
        color = COLORS[i % len(COLORS)]
        x, y, w, h = det.bbox
        cv2.rectangle(out, (x, y), (x + w, y + h), color, 2)
        label = f"{det.asset_type}:{det.asset_name} {det.confidence:.2f}"
        cv2.putText(out, label, (x, max(y - 5, 10)), cv2.FONT_HERSHEY_SIMPLEX, 0.4, color, 1)
    return out


def run(args):
    video_path = Path(args.video)
    timestamp = datetime.now().strftime("%Y-%m-%d_%H-%M")
    out_dir = Path(args.output_dir) / timestamp
    frames_dir = out_dir / "frames"
    frames_dir.mkdir(parents=True, exist_ok=True)

    try:
        detector = YoloDetector(model_path=args.model, confidence=args.threshold)
    except FileNotFoundError as e:
        print(e)
        sys.exit(1)

    cap = cv2.VideoCapture(str(video_path))
    total_frames = int(cap.get(cv2.CAP_PROP_FRAME_COUNT))
    fps = cap.get(cv2.CAP_PROP_FPS)

    if args.frames:
        sample_indices = sorted(args.frames)
    else:
        n_sample = min(args.n_frames, total_frames)
        random.seed(args.seed)
        sample_indices = sorted(random.sample(range(total_frames), n_sample))
    n_sample = len(sample_indices)

    print(f"Video:   {video_path.name}  ({total_frames} frames @ {fps:.0f}fps)")
    print(f"Model:   {args.model}")
    print(f"Filter:  {args.asset_type or 'all types'}")
    print(f"Frames:  {n_sample} sampled")
    print(f"Output:  {out_dir}\n")

    n_with_detections = 0
    detections_path = out_dir / "detections.jsonl"

    with open(detections_path, "w") as f:
        with progress(total=n_sample, desc="Detecting", unit="frame") as bar:
            for frame_idx in sample_indices:
                cap.set(cv2.CAP_PROP_POS_FRAMES, frame_idx)
                ret, frame = cap.read()
                if not ret:
                    bar.update(1)
                    continue

                detections = detector.detect_filtered(frame, args.asset_type or None)
                frame_ts = frame_idx / fps
                img_name = f"frame_{frame_idx:06d}_t{frame_ts:.1f}s.jpg"

                if args.debug:
                    print(f"\n--- frame {frame_idx} ({frame_ts:.1f}s) ---")
                    for det in detections:
                        print(f"  {det.confidence:.4f}  {det.asset_type}:{det.asset_name}  bbox={det.bbox}")

                if detections:
                    cv2.imwrite(str(frames_dir / img_name), annotate(frame, detections),
                                [cv2.IMWRITE_JPEG_QUALITY, 90])
                    record = {
                        "frame": frame_idx,
                        "timestamp": round(frame_ts, 2),
                        "image": img_name,
                        "detections": [
                            {
                                "asset_type": d.asset_type,
                                "asset_name": d.asset_name,
                                "bbox": list(d.bbox),
                                "confidence": round(d.confidence, 4),
                            }
                            for d in detections
                        ],
                    }
                    f.write(json.dumps(record) + "\n")
                    n_with_detections += 1
                elif args.save_all:
                    cv2.imwrite(str(frames_dir / img_name), frame,
                                [cv2.IMWRITE_JPEG_QUALITY, 90])

                bar.set_postfix(hits=n_with_detections)
                bar.update(1)

    cap.release()
    print(f"\nDone. {n_with_detections}/{n_sample} frames had detections.")
    print(f"Annotated frames: {frames_dir}")
    print(f"Detections log:   {detections_path}")


def main():
    parser = argparse.ArgumentParser(description="Run YOLO asset detection on sampled video frames")
    _add_args(parser)
    run(parser.parse_args())


def _add_args(parser):
    asset_types = list(ASSET_TYPE_TO_DIR.keys())
    parser.add_argument("video", help="Path to gameplay footage mp4 or BU alias")
    parser.add_argument("--model", default="runs/detect/balatro/weights/best.pt",
                        help="Path to trained YOLO .pt model")
    parser.add_argument("--asset-type", default=None, choices=asset_types,
                        help="Filter detections to one asset type (default: show all)")
    parser.add_argument("--n-frames", type=int, default=25,
                        help="Number of frames to sample (default: 25)")
    parser.add_argument("--threshold", type=float, default=0.25,
                        help="Detection confidence threshold (default: 0.25)")
    parser.add_argument("--frames", type=int, nargs="+", metavar="N",
                        help="Specific frame indices instead of random sampling")
    parser.add_argument("--save-all", action="store_true",
                        help="Save every sampled frame, not just hits")
    parser.add_argument("--debug", action="store_true",
                        help="Print detections per frame to stdout")
    parser.add_argument("--output-dir", default="test_output")
    parser.add_argument("--seed", type=int, default=42)


if __name__ == "__main__":
    main()
