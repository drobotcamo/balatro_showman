# Superseded by detectors/yolo_detector.py. Kept for reference only.
"""
Generic multi-template asset detector.

Loads all recorded templates from recorded_gameplay_asset_images/<type>/.
Groups them by asset name (strips trailing _N suffix so Strength.png,
Strength_1.png, Strength_2.png all count as "Strength" templates).
For each asset, all its templates are tried; the best score wins.
"""

import re
import cv2
import numpy as np
from pathlib import Path
from dataclasses import dataclass

RECORDED_DIR = Path(__file__).parent.parent / "recorded_gameplay_asset_images"
TEMPLATE_BASE_WIDTH = 1280
DEFAULT_THRESHOLD = 0.75
IOU_THRESHOLD = 0.3


@dataclass
class Detection:
    asset_name: str
    bbox: tuple  # (x, y, w, h) in full-frame coords
    confidence: float
    scale: float


def _iou(a, b):
    ax, ay, aw, ah = a
    bx, by, bw, bh = b
    ix1, iy1 = max(ax, bx), max(ay, by)
    ix2, iy2 = min(ax + aw, bx + bw), min(ay + ah, by + bh)
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


def _stem_to_name(stem):
    return re.sub(r"_\d+$", "", stem).replace("_", " ")


def _load_gray(path):
    """Load image as grayscale. Handles RGBA by compositing onto mid-gray."""
    img = cv2.imread(str(path), cv2.IMREAD_UNCHANGED)
    if img is None:
        return None
    if len(img.shape) == 2:
        return img
    if img.shape[2] == 4:
        bgr = img[:, :, :3].astype(np.float32)
        alpha = img[:, :, 3:].astype(np.float32) / 255.0
        bg = np.full_like(bgr, 128.0)
        composited = (bgr * alpha + bg * (1.0 - alpha)).astype(np.uint8)
        return cv2.cvtColor(composited, cv2.COLOR_BGR2GRAY)
    return cv2.cvtColor(img, cv2.COLOR_BGR2GRAY)


class AssetDetector:
    def __init__(self, asset_type, threshold=DEFAULT_THRESHOLD,
                 video_width=TEMPLATE_BASE_WIDTH, roi=None):
        self.asset_type = asset_type
        self.threshold = threshold
        self.roi = roi  # (x1_frac, y1_frac, x2_frac, y2_frac) or None
        base = video_width / TEMPLATE_BASE_WIDTH
        self.scales = [round(base * f, 4) for f in (0.85, 1.0, 1.15)]
        self.prepared = self._load_templates()

    def _load_templates(self):
        templates_dir = RECORDED_DIR / self.asset_type
        if not templates_dir.exists():
            return []

        # Group files by logical asset name
        by_name: dict[str, list[Path]] = {}
        for path in sorted(templates_dir.glob("*.png")):
            name = _stem_to_name(path.stem)
            by_name.setdefault(name, []).append(path)

        # Pre-scale every (name, template_file, scale) variant at init
        prepared = []
        for name, paths in sorted(by_name.items()):
            for path in paths:
                gray = _load_gray(path)
                if gray is None:
                    continue
                h, w = gray.shape
                for scale in self.scales:
                    new_w = max(1, int(w * scale))
                    new_h = max(1, int(h * scale))
                    scaled = cv2.resize(gray, (new_w, new_h), interpolation=cv2.INTER_AREA)
                    prepared.append((name, scale, scaled))
        return prepared

    def roi_pixels(self, frame_h, frame_w):
        if self.roi is None:
            return 0, 0, frame_w, frame_h
        x1f, y1f, x2f, y2f = self.roi
        return int(frame_w * x1f), int(frame_h * y1f), int(frame_w * x2f), int(frame_h * y2f)

    def detect(self, frame):
        fh, fw = frame.shape[:2]
        rx1, ry1, rx2, ry2 = self.roi_pixels(fh, fw)
        gray_frame = cv2.cvtColor(frame[ry1:ry2, rx1:rx2], cv2.COLOR_BGR2GRAY)
        ch, cw = gray_frame.shape

        all_detections = []
        for asset_name, scale, gray_tmpl in self.prepared:
            th, tw = gray_tmpl.shape
            if tw > cw or th > ch:
                continue
            result = cv2.matchTemplate(gray_frame, gray_tmpl, cv2.TM_CCOEFF_NORMED)
            ys, xs = np.where(result >= self.threshold)
            for y, x in zip(ys, xs):
                all_detections.append(Detection(
                    asset_name=asset_name,
                    bbox=(int(x) + rx1, int(y) + ry1, tw, th),
                    confidence=float(result[y, x]),
                    scale=scale,
                ))
        return _nms(all_detections)

    def debug_scores(self, frame):
        """Best score per asset name across all templates and scales, sorted descending."""
        fh, fw = frame.shape[:2]
        rx1, ry1, rx2, ry2 = self.roi_pixels(fh, fw)
        gray_frame = cv2.cvtColor(frame[ry1:ry2, rx1:rx2], cv2.COLOR_BGR2GRAY)
        ch, cw = gray_frame.shape

        best: dict[str, tuple[float, float]] = {}
        for asset_name, scale, gray_tmpl in self.prepared:
            th, tw = gray_tmpl.shape
            if tw > cw or th > ch:
                continue
            result = cv2.matchTemplate(gray_frame, gray_tmpl, cv2.TM_CCOEFF_NORMED)
            score = float(result.max())
            if asset_name not in best or score > best[asset_name][0]:
                best[asset_name] = (score, scale)
        return sorted(best.items(), key=lambda kv: kv[1][0], reverse=True)
