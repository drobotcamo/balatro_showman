import cv2
import numpy as np
from pathlib import Path
from dataclasses import dataclass

TEMPLATES_DIR = Path(__file__).parent.parent / "game_asset_images" / "tag_images"

# Footage is 640x360; templates are 68px designed for ~1280x720 → expected scale ~0.5
SCALES = [0.4, 0.5, 0.6]
DEFAULT_THRESHOLD = 0.8
IOU_THRESHOLD = 0.3


@dataclass
class Detection:
    tag_name: str
    bbox: tuple  # (x, y, w, h)
    confidence: float
    scale: float


def _iou(a, b):
    ax, ay, aw, ah = a
    bx, by, bw, bh = b
    ix1 = max(ax, bx)
    iy1 = max(ay, by)
    ix2 = min(ax + aw, bx + bw)
    iy2 = min(ay + ah, by + bh)
    inter = max(0, ix2 - ix1) * max(0, iy2 - iy1)
    union = aw * ah + bw * bh - inter
    return inter / union if union > 0 else 0.0


def _nms(detections):
    detections = sorted(detections, key=lambda d: d.confidence, reverse=True)
    kept = []
    for det in detections:
        if not any(_iou(det.bbox, k.bbox) > IOU_THRESHOLD for k in kept):
            kept.append(det)
    return kept


class SkipTagDetector:
    def __init__(self, threshold=DEFAULT_THRESHOLD):
        self.threshold = threshold
        self.prepared = self._load_and_scale_templates()

    def _load_and_scale_templates(self):
        # Pre-compute every (tag, scale) variant at init so detect() has no resize overhead.
        # Alpha-composite onto mid-gray so transparent corners become a uniform constant;
        # TM_CCOEFF_NORMED's mean subtraction then cancels them out, no mask needed.
        prepared = []
        for path in sorted(TEMPLATES_DIR.glob("*.png")):
            img = cv2.imread(str(path), cv2.IMREAD_UNCHANGED)
            if img is None or img.shape[2] != 4:
                continue
            name = path.stem.replace("_Tag", "").replace("_", " ")
            th, tw = img.shape[:2]
            for scale in SCALES:
                new_w = max(1, int(tw * scale))
                new_h = max(1, int(th * scale))
                scaled = cv2.resize(img, (new_w, new_h), interpolation=cv2.INTER_AREA)
                bgr = scaled[:, :, :3].astype(np.float32)
                alpha = scaled[:, :, 3:].astype(np.float32) / 255.0
                bg = np.full_like(bgr, 128.0)
                composited = (bgr * alpha + bg * (1.0 - alpha)).astype(np.uint8)
                gray = cv2.cvtColor(composited, cv2.COLOR_BGR2GRAY)
                prepared.append((name, scale, gray))
        return prepared

    def detect(self, frame):
        gray_frame = cv2.cvtColor(frame, cv2.COLOR_BGR2GRAY)
        fh, fw = gray_frame.shape
        all_detections = []

        for tag_name, scale, gray_tmpl in self.prepared:
            th, tw = gray_tmpl.shape
            if tw > fw or th > fh:
                continue

            result = cv2.matchTemplate(gray_frame, gray_tmpl, cv2.TM_CCOEFF_NORMED)

            ys, xs = np.where(result >= self.threshold)
            for y, x in zip(ys, xs):
                all_detections.append(Detection(
                    tag_name=tag_name,
                    bbox=(int(x), int(y), tw, th),
                    confidence=float(result[y, x]),
                    scale=scale,
                ))

        return _nms(all_detections)

