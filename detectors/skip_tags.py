import cv2
import numpy as np
from pathlib import Path
from dataclasses import dataclass

TEMPLATES_DIR = Path(__file__).parent.parent / "game_asset_images" / "tag_images"

# Templates were authored for ~1280x720. Base scale = video_width / 1280;
# search ±15% around it to absorb minor rendering differences.
TEMPLATE_BASE_WIDTH = 1280
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
    def __init__(self, threshold=DEFAULT_THRESHOLD, video_width=TEMPLATE_BASE_WIDTH, roi=None):
        self.threshold = threshold
        # roi: (x1_frac, y1_frac, x2_frac, y2_frac) in [0,1], or None for full frame
        self.roi = roi
        base = video_width / TEMPLATE_BASE_WIDTH
        self.scales = [round(base * f, 4) for f in (0.85, 1.0, 1.15)]
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
            for scale in self.scales:
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

    def roi_pixels(self, frame_h, frame_w):
        if self.roi is None:
            return 0, 0, frame_w, frame_h
        x1f, y1f, x2f, y2f = self.roi
        return (
            int(frame_w * x1f),
            int(frame_h * y1f),
            int(frame_w * x2f),
            int(frame_h * y2f),
        )

    def debug_scores(self, frame):
        """Return best match score per tag name across all scales, sorted descending."""
        fh, fw = frame.shape[:2]
        rx1, ry1, rx2, ry2 = self.roi_pixels(fh, fw)
        crop = frame[ry1:ry2, rx1:rx2]
        gray_frame = cv2.cvtColor(crop, cv2.COLOR_BGR2GRAY)
        ch, cw = gray_frame.shape

        best = {}
        for tag_name, scale, gray_tmpl in self.prepared:
            th, tw = gray_tmpl.shape
            if tw > cw or th > ch:
                continue
            result = cv2.matchTemplate(gray_frame, gray_tmpl, cv2.TM_CCOEFF_NORMED)
            score = float(result.max())
            if tag_name not in best or score > best[tag_name][0]:
                best[tag_name] = (score, scale)

        return sorted(best.items(), key=lambda kv: kv[1][0], reverse=True)

    def detect(self, frame):
        fh, fw = frame.shape[:2]
        rx1, ry1, rx2, ry2 = self.roi_pixels(fh, fw)
        crop = frame[ry1:ry2, rx1:rx2]

        gray_frame = cv2.cvtColor(crop, cv2.COLOR_BGR2GRAY)
        ch, cw = gray_frame.shape
        all_detections = []

        for tag_name, scale, gray_tmpl in self.prepared:
            th, tw = gray_tmpl.shape
            if tw > cw or th > ch:
                continue

            result = cv2.matchTemplate(gray_frame, gray_tmpl, cv2.TM_CCOEFF_NORMED)

            ys, xs = np.where(result >= self.threshold)
            for y, x in zip(ys, xs):
                all_detections.append(Detection(
                    tag_name=tag_name,
                    bbox=(int(x) + rx1, int(y) + ry1, tw, th),
                    confidence=float(result[y, x]),
                    scale=scale,
                ))

        return _nms(all_detections)

