import argparse
import json
import random
import sys
from pathlib import Path

import cv2
from tqdm import tqdm

from detectors.skip_tags import SkipTagDetector

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
        label = f"{det.tag_name} {det.confidence:.2f}"
        cv2.putText(out, label, (x, max(y - 5, 10)), cv2.FONT_HERSHEY_SIMPLEX, 0.4, color, 1)
    return out


def main():
    parser = argparse.ArgumentParser(description="Run skip tag detection on sampled video frames")
    parser.add_argument("video", help="Path to gameplay footage mp4")
    parser.add_argument("--sample-rate", type=float, default=0.01, help="Fraction of frames to sample (default 0.01)")
    parser.add_argument("--threshold", type=float, default=0.75, help="Detection confidence threshold")
    parser.add_argument("--output-dir", default="test_output", help="Root output directory")
    parser.add_argument("--seed", type=int, default=42)
    args = parser.parse_args()

    video_path = Path(args.video)
    out_dir = Path(args.output_dir) / f"run_{video_path.stem}"
    frames_dir = out_dir / "frames"
    frames_dir.mkdir(parents=True, exist_ok=True)

    cap = cv2.VideoCapture(str(video_path))
    total_frames = int(cap.get(cv2.CAP_PROP_FRAME_COUNT))
    fps = cap.get(cv2.CAP_PROP_FPS)

    n_sample = max(1, int(total_frames * args.sample_rate))
    random.seed(args.seed)
    sample_indices = sorted(random.sample(range(total_frames), n_sample))

    detector = SkipTagDetector(threshold=args.threshold)

    print(f"Video:    {video_path.name}  ({total_frames} frames @ {fps:.0f}fps)")
    print(f"Sampling: {n_sample} frames ({args.sample_rate * 100:.1f}%)")
    print(f"Output:   {out_dir}\n")

    n_with_detections = 0
    detections_path = out_dir / "detections.jsonl"

    sample_set = set(sample_indices)

    with open(detections_path, "w") as f:
        with tqdm(total=n_sample, unit="frame") as bar:
            current = 0
            while True:
                ret, frame = cap.read()
                if not ret:
                    break
                frame_idx = current
                current += 1

                if frame_idx not in sample_set:
                    continue

                detections = detector.detect(frame)
                if detections:
                    timestamp = frame_idx / fps
                    img_name = f"frame_{frame_idx:06d}_t{timestamp:.1f}s.jpg"
                    cv2.imwrite(str(frames_dir / img_name), annotate(frame, detections), [cv2.IMWRITE_JPEG_QUALITY, 90])

                    record = {
                        "frame": frame_idx,
                        "timestamp": round(timestamp, 2),
                        "image": img_name,
                        "detections": [
                            {
                                "tag": d.tag_name,
                                "bbox": list(d.bbox),
                                "confidence": round(d.confidence, 4),
                                "scale": d.scale,
                            }
                            for d in detections
                        ],
                    }
                    f.write(json.dumps(record) + "\n")
                    n_with_detections += 1

                bar.set_postfix(hits=n_with_detections)
                bar.update(1)

    cap.release()
    print(f"\nDone. {n_with_detections}/{n_sample} frames had detections.")
    print(f"Annotated frames: {frames_dir}")
    print(f"Detections log:   {detections_path}")


if __name__ == "__main__":
    main()
