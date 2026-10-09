"""Validate and deterministically export the bounded evaluation slice."""
from __future__ import annotations

import argparse
import json
import math
import re
from pathlib import Path
from typing import Any

SCHEMA_VERSION = "evaluation-slice-1.0"
STATUSES = {"observed", "unknown", "missing", "occluded", "ambiguous", "unsupported"}
SUPPORTED_FIELDS = {"page", "zone", "identity", "modifier", "edition", "seal", "sticker", "ocr"}

def _has_nonfinite(value: Any) -> bool:
    if isinstance(value, float):
        return not math.isfinite(value)
    if isinstance(value, dict):
        return any(_has_nonfinite(item) for item in value.values())
    if isinstance(value, list):
        return any(_has_nonfinite(item) for item in value)
    return False

def validate_manifest(manifest: dict[str, Any]) -> list[str]:
    errors: list[str] = []
    if not isinstance(manifest, dict):
        return ["manifest must be an object"]
    if manifest.get("schema_version") != SCHEMA_VERSION: errors.append("unsupported schema_version")
    if not isinstance(manifest.get("protocol"), str) or not manifest["protocol"]: errors.append("protocol is required")
    source = manifest.get("source")
    if not isinstance(source, dict): errors.append("source must be an object")
    else:
        for key in ("video_sha256", "run_sha256", "alignment_sha256"):
            if not isinstance(source.get(key), str) or not re.fullmatch(r"[0-9a-f]{64}", source[key]): errors.append(f"source.{key} must be sha256")
        if not isinstance(source.get("split"), str) or source["split"] not in {"development", "held_out"}: errors.append("source.split is invalid")
        for key in ("width", "height"):
            if isinstance(source.get(key), bool) or not isinstance(source.get(key), int) or source[key] <= 0: errors.append(f"source.{key} is invalid")
    frames = manifest.get("frames")
    if not isinstance(frames, list):
        return errors + ["frames must be an array"]
    seen: set[str] = set()
    for i, frame in enumerate(frames):
        prefix = f"frames[{i}]"
        if not isinstance(frame, dict): errors.append(f"{prefix} must be an object"); continue
        fid = frame.get("frame_id")
        if not isinstance(fid, str) or not fid: errors.append(f"{prefix}.frame_id is required")
        elif fid in seen: errors.append(f"duplicate frame_id: {fid}")
        else: seen.add(fid)
        if not isinstance(frame.get("frame_index"), int) or isinstance(frame.get("frame_index"), bool) or frame["frame_index"] < 0: errors.append(f"{prefix}.frame_index is invalid")
        if not isinstance(frame.get("annotations"), dict): errors.append(f"{prefix}.annotations is required")
        if frame.get("synthetic_background") is True: errors.append(f"{prefix} uses a synthetic background")
        mapping = frame.get("mapping", {})
        if not isinstance(mapping, dict) or any(isinstance(mapping.get(k), bool) or not isinstance(mapping.get(k), (int, float)) or not math.isfinite(mapping[k]) for k in ("x", "y", "width", "height")) or mapping.get("width", 0) <= 0 or mapping.get("height", 0) <= 0:
            errors.append(f"{prefix}.mapping is malformed")
        transform = frame.get("canonical_to_source")
        if not isinstance(transform, list) or len(transform) != 6 or any(isinstance(v, bool) or not isinstance(v, (int, float)) or not math.isfinite(v) for v in transform):
            errors.append(f"{prefix}.canonical_to_source is malformed")
        review = frame.get("review", {})
        if not isinstance(review, dict):
            errors.append(f"{prefix}.review must be an object")
            review = {}
        reviewers = review.get("reviewers")
        if review.get("status") != "reviewed" or not isinstance(reviewers, list) or any(not isinstance(r, str) or not r for r in reviewers) or len(set(reviewers)) < 2: errors.append(f"{prefix} is not independently reviewed")
        annotations = frame.get("annotations")
        if not isinstance(annotations, dict):
            continue
        unsupported = set(annotations) - SUPPORTED_FIELDS
        if unsupported: errors.append(f"{prefix} has unsupported fields: {','.join(sorted(unsupported))}")
        for field, value in annotations.items():
            if not isinstance(value, dict) or value.get("status") not in STATUSES: errors.append(f"{prefix}.annotations.{field} has invalid status")
            elif value.get("status") == "observed" and "raw" not in value: errors.append(f"{prefix}.annotations.{field} lacks raw value")
            if isinstance(value, dict) and "normalized" in value and "raw" not in value: errors.append(f"{prefix}.annotations.{field} normalized value lacks raw value")
            if isinstance(value, dict) and any(key in value for key in ("oracle", "ground_truth", "reference_value")): errors.append(f"{prefix}.annotations.{field} contains oracle/reference data")
            if isinstance(value, dict) and _has_nonfinite(value): errors.append(f"{prefix}.annotations.{field} contains non-finite number")
            if isinstance(value, dict) and value.get("contradictory") is True: errors.append(f"{prefix}.annotations.{field} is contradictory")
    return errors

def validate_split_assignments(manifests: list[dict[str, Any]]) -> list[str]:
    """Reject source reuse across splits and adjacent source frames in different splits."""
    errors: list[str] = []
    source_splits: dict[tuple[str, str], str] = {}
    frame_splits: dict[tuple[str, str, int], str] = {}
    for manifest_index, manifest in enumerate(manifests):
        if not isinstance(manifest, dict):
            errors.append(f"manifests[{manifest_index}] must be an object")
            continue
        source = manifest.get("source")
        frames = manifest.get("frames")
        if not isinstance(source, dict) or not isinstance(frames, list):
            errors.append(f"manifests[{manifest_index}] requires source object and frames array")
            continue
        video_sha = source.get("video_sha256")
        run_sha = source.get("run_sha256")
        split = source.get("split")
        if not all(isinstance(value, str) and value for value in (video_sha, run_sha, split)):
            errors.append(f"manifests[{manifest_index}] has invalid source split identity")
            continue
        source_key = (video_sha, run_sha)
        previous_split = source_splits.setdefault(source_key, split)
        if previous_split != split:
            errors.append(f"source video/run assigned to multiple splits: {video_sha}/{run_sha}")
        for frame_index, frame in enumerate(frames):
            if not isinstance(frame, dict):
                continue
            index = frame.get("frame_index")
            if isinstance(index, bool) or not isinstance(index, int) or index < 0:
                continue
            frame_key = (video_sha, run_sha, index)
            previous = frame_splits.setdefault(frame_key, split)
            if previous != split:
                errors.append(f"source frame assigned to multiple splits: {video_sha}/{run_sha} frame {index}")
    by_source: dict[tuple[str, str], list[tuple[int, str]]] = {}
    for (video_sha, run_sha, frame_index), split in frame_splits.items():
        by_source.setdefault((video_sha, run_sha), []).append((frame_index, split))
    for source_key, assignments in by_source.items():
        assignments.sort()
        for (left_index, left_split), (right_index, right_split) in zip(assignments, assignments[1:]):
            if right_index - left_index <= 1 and left_split != right_split:
                errors.append(f"neighboring source frames cross splits: {source_key[0]}/{source_key[1]} frames {left_index},{right_index}")
    return errors

def pilot_report(manifest: dict[str, Any]) -> dict[str, Any]:
    """Return deterministic QA metrics; validation is intentionally separate."""
    frames = manifest.get("frames", []) if isinstance(manifest, dict) else []
    if not isinstance(frames, list):
        frames = []
    reviewed = sum(1 for f in frames if isinstance(f, dict) and isinstance(f.get("review"), dict) and f["review"].get("status") == "reviewed")
    disagreements = sum(1 for f in frames if isinstance(f, dict) and isinstance(f.get("review"), dict) and f["review"].get("disagreement") is True)
    missing = sum(1 for f in frames for v in (f.get("annotations", {}) if isinstance(f, dict) and isinstance(f.get("annotations"), dict) else {}).values() if isinstance(v, dict) and v.get("status") in {"missing", "unknown", "occluded"})
    exclusions = sum(1 for f in frames if isinstance(f, dict) and f.get("excluded") is True)
    return {"frames": len(frames), "reviewed": reviewed, "coverage": reviewed / len(frames) if frames else 0.0, "disagreements": disagreements, "missing_or_unavailable_values": missing, "exclusions": exclusions}

def export_manifest(manifest: dict[str, Any], destination: Path) -> None:
    errors = validate_manifest(manifest)
    if errors: raise ValueError("invalid evaluation manifest: " + "; ".join(errors))
    result = dict(manifest)
    result["frames"] = sorted(manifest["frames"], key=lambda f: (f["frame_index"], f["frame_id"]))
    destination.parent.mkdir(parents=True, exist_ok=True)
    destination.write_text(json.dumps(result, sort_keys=True, indent=2) + "\n", encoding="utf-8")

def main() -> int:
    parser = argparse.ArgumentParser()
    parser.add_argument("input", type=Path); parser.add_argument("output", type=Path)
    args = parser.parse_args()
    export_manifest(json.loads(args.input.read_text(encoding="utf-8")), args.output)
    return 0

if __name__ == "__main__": raise SystemExit(main())
