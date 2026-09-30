from dataclasses import dataclass
from pathlib import Path


@dataclass
class Detection:
    asset_type: str
    asset_name: str
    bbox: tuple       # (x, y, w, h) in full-frame pixels
    confidence: float


class YoloDetector:
    def __init__(self, model_path, confidence=0.25, device=""):
        # Deferred import so this module is importable before ultralytics is needed
        # and before a trained model exists.
        from ultralytics import YOLO
        path = Path(model_path)
        if not path.exists():
            raise FileNotFoundError(
                f"Model not found: {path}\n"
                "Train one first:  python main.py train"
            )
        self.model = YOLO(str(path))
        self.confidence = confidence
        self.device = device

    def detect(self, frame) -> list[Detection]:
        results = self.model(frame, verbose=False, conf=self.confidence,
                             device=self.device)[0]
        out = []
        for box in results.boxes:
            label = self.model.names[int(box.cls)]
            asset_type, _, asset_name = label.partition(":")
            x1, y1, x2, y2 = map(int, box.xyxy[0].tolist())
            out.append(Detection(
                asset_type=asset_type,
                asset_name=asset_name,
                bbox=(x1, y1, x2 - x1, y2 - y1),
                confidence=float(box.conf),
            ))
        return out

    def detect_filtered(self, frame, asset_type=None) -> list[Detection]:
        dets = self.detect(frame)
        return [d for d in dets if d.asset_type == asset_type] if asset_type else dets
