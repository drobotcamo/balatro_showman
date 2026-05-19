import argparse
import json
import random
from datetime import datetime
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


def annotate(frame, detections, roi_box=None):
    out = frame.copy()
    if roi_box:
        rx1, ry1, rx2, ry2 = roi_box
        cv2.rectangle(out, (rx1, ry1), (rx2, ry2), (200, 200, 200), 1)
    for i, det in enumerate(detections):
        color = COLORS[i % len(COLORS)]
        x, y, w, h = det.bbox
        cv2.rectangle(out, (x, y), (x + w, y + h), color, 2)
        label = f"{det.tag_name} {det.confidence:.2f}"
        cv2.putText(out, label, (x, max(y - 5, 10)), cv2.FONT_HERSHEY_SIMPLEX, 0.4, color, 1)
    return out


def run(args):
    video_path = Path(args.video)
    timestamp = datetime.now().strftime("%Y-%m-%d_%H-%M")
    out_dir = Path(args.output_dir) / timestamp
    frames_dir = out_dir / "frames"
    frames_dir.mkdir(parents=True, exist_ok=True)

    cap = cv2.VideoCapture(str(video_path))
    total_frames = int(cap.get(cv2.CAP_PROP_FRAME_COUNT))
    fps = cap.get(cv2.CAP_PROP_FPS)
    video_width = int(cap.get(cv2.CAP_PROP_FRAME_WIDTH))

    if args.frames:
        sample_indices = sorted(args.frames)
    else:
        n_sample = min(args.n_frames, total_frames)
        random.seed(args.seed)
        sample_indices = sorted(random.sample(range(total_frames), n_sample))
    n_sample = len(sample_indices)

    detector = SkipTagDetector(threshold=args.threshold, video_width=video_width, roi=args.roi)

    print(f"Video:    {video_path.name}  ({total_frames} frames @ {fps:.0f}fps, {video_width}px wide)")
    print(f"Sampling: {n_sample} frame(s)  scales={detector.scales}")
    print(f"ROI:      x={args.roi[0]}-{args.roi[2]}  y={args.roi[1]}-{args.roi[3]}")
    print(f"Output:   {out_dir}\n")

    n_with_detections = 0
    detections_path = out_dir / "detections.jsonl"

    with open(detections_path, "w") as f:
        with tqdm(total=n_sample, unit="frame") as bar:
            for frame_idx in sample_indices:
                cap.set(cv2.CAP_PROP_POS_FRAMES, frame_idx)
                ret, frame = cap.read()
                if not ret:
                    bar.update(1)
                    continue

                if args.debug:
                    scores = detector.debug_scores(frame)
                    print(f"\n--- frame {frame_idx} ---")
                    for tag_name, (score, scale) in scores[:15]:
                        marker = " ***" if score >= args.threshold else ""
                        print(f"  {score:.4f} @ {scale:.3f}x  {tag_name}{marker}")

                    fh2, fw2 = frame.shape[:2]
                    rx1, ry1, rx2, ry2 = detector.roi_pixels(fh2, fw2)
                    crop_path = frames_dir / f"frame_{frame_idx:06d}_roi_crop.png"
                    cv2.imwrite(str(crop_path), frame[ry1:ry2, rx1:rx2])

                detections = detector.detect(frame)
                frame_ts = frame_idx / fps
                img_name = f"frame_{frame_idx:06d}_t{frame_ts:.1f}s.jpg"

                fh, fw = frame.shape[:2]
                roi_box = detector.roi_pixels(fh, fw)

                if detections:
                    cv2.imwrite(str(frames_dir / img_name), annotate(frame, detections, roi_box), [cv2.IMWRITE_JPEG_QUALITY, 90])
                    record = {
                        "frame": frame_idx,
                        "timestamp": round(frame_ts, 2),
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
                elif args.save_all:
                    cv2.imwrite(str(frames_dir / img_name), annotate(frame, [], roi_box), [cv2.IMWRITE_JPEG_QUALITY, 90])

                bar.set_postfix(hits=n_with_detections)
                bar.update(1)

    cap.release()
    print(f"\nDone. {n_with_detections}/{n_sample} frames had detections.")
    print(f"Annotated frames: {frames_dir}")
    print(f"Detections log:   {detections_path}")


def main():
    parser = argparse.ArgumentParser(description="Run skip tag detection on sampled video frames")
    _add_args(parser)
    run(parser.parse_args())


def _add_args(parser):
    parser.add_argument("video", help="Path to gameplay footage mp4")
    parser.add_argument("--n-frames", type=int, default=25, help="Number of frames to sample (default 25)")
    parser.add_argument("--threshold", type=float, default=0.75, help="Detection confidence threshold")
    parser.add_argument("--roi", type=float, nargs=4, default=[0.25, 0.55, 0.65, 0.90],
                        metavar=("X1", "Y1", "X2", "Y2"),
                        help="ROI as frame fractions x1 y1 x2 y2")
    parser.add_argument("--frames", type=int, nargs="+", metavar="N",
                        help="Target specific frame indices instead of random sampling")
    parser.add_argument("--save-all", action="store_true", help="Save every sampled frame, not just hits")
    parser.add_argument("--debug", action="store_true", help="Print top template scores per frame")
    parser.add_argument("--output-dir", default="test_output", help="Root output directory")
    parser.add_argument("--seed", type=int, default=42)


if __name__ == "__main__":
    main()
