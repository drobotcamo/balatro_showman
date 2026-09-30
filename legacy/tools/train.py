"""
Train a YOLO26 detection model on the built dataset.

Usage:
    python main.py train [--data dataset/dataset.yaml] [--base-model yolo26s.pt]
                        [--epochs 100] [--imgsz 640] [--batch 16] [--name balatro]
"""

import argparse
import sys
from pathlib import Path


def run(args):
    data_path = Path(args.data)
    if not data_path.exists():
        print(f"Dataset not found: {data_path}")
        print("Build it first:  python main.py dataset build")
        sys.exit(1)

    from ultralytics import YOLO
    model = YOLO(args.base_model)
    model.train(
        data=str(data_path.resolve()),
        epochs=args.epochs,
        imgsz=args.imgsz,
        batch=args.batch,
        name=args.name,
        patience=50,
        freeze=10,
        device=args.device,
    )

    best = Path("runs") / "detect" / args.name / "weights" / "best.pt"
    print(f"\nTraining complete. Best model: {best}")
    print(f"Detect with:  python main.py detect <video> --model {best}")


def _add_args(parser):
    parser.add_argument("--data", default="dataset/dataset.yaml",
                        help="Path to dataset.yaml (default: dataset/dataset.yaml)")
    parser.add_argument("--base-model", default="yolo26s.pt",
                        help="Base YOLO26 model to fine-tune (default: yolo26s.pt)")
    parser.add_argument("--epochs", type=int, default=100)
    parser.add_argument("--imgsz", type=int, default=640)
    parser.add_argument("--batch", type=int, default=16)
    parser.add_argument("--name", default="balatro",
                        help="Run name; model saved to runs/detect/<name>/weights/best.pt")
    parser.add_argument("--device", default="",
                        help="Device: '' (auto), 'cpu', '0' (GPU 0), 'directml' (AMD/Intel on Windows)")


def main():
    parser = argparse.ArgumentParser(description="Train YOLO26 on the built dataset")
    _add_args(parser)
    run(parser.parse_args())


if __name__ == "__main__":
    main()
