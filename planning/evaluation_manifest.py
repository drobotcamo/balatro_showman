"""Validate and deterministically export the bounded evaluation slice."""
from __future__ import annotations

import argparse
import json
import math
import re
import sys
from pathlib import Path
from typing import Any

SCHEMA_VERSION = "evaluation-slice-1.0"
STATUSES = {"observed", "unknown", "missing", "occluded", "ambiguous", "unsupported"}
SUPPORTED_FIELDS = {"page", "zone", "identity", "modifier", "edition", "seal", "sticker", "ocr"}

def _has_nonfinite(value: Any) -> bool:
    if isinstance(value, float):
        return not math.isfinite(value)
    if isinstance(value, int) and not isinstance(value, bool):
        return abs(value) > int(sys.float_info.max)
    if isinstance(value, dict):
        return any(_has_nonfinite(item) for item in value.values())
    if isinstance(value, list):
        return any(_has_nonfinite(item) for item in value)
    return False

def _finite_number(value: Any) -> bool:
    if isinstance(value, bool) or not isinstance(value, (int, float)):
        return False
    try:
        return math.isfinite(value)
    except OverflowError:
        return False

def validate_manifest(manifest: dict[str, Any]) -> list[str]:
    errors: list[str] = []
    if not isinstance(manifest, dict):
        return ["manifest must be an object"]
    unknown = set(manifest) - {"schema_version", "protocol", "source", "frames"}
    if unknown: errors.append(f"manifest has unknown fields: {','.join(sorted(map(str, unknown)))}")
    if manifest.get("schema_version") != SCHEMA_VERSION: errors.append("unsupported schema_version")
    if not isinstance(manifest.get("protocol"), str) or not manifest["protocol"]: errors.append("protocol is required")
    source = manifest.get("source")
    if not isinstance(source, dict): errors.append("source must be an object")
    else:
        unknown = set(source) - {"video_sha256", "run_sha256", "alignment_sha256", "split", "width", "height"}
        if unknown: errors.append(f"source has unknown fields: {','.join(sorted(map(str, unknown)))}")
        for key in ("video_sha256", "run_sha256", "alignment_sha256"):
            if not isinstance(source.get(key), str) or not re.fullmatch(r"[0-9a-f]{64}", source[key]): errors.append(f"source.{key} must be sha256")
        if not isinstance(source.get("split"), str) or source["split"] not in {"development", "held_out"}: errors.append("source.split is invalid")
        for key in ("width", "height"):
            if isinstance(source.get(key), bool) or not isinstance(source.get(key), int) or source[key] <= 0: errors.append(f"source.{key} is invalid")
    frames = manifest.get("frames")
    if not isinstance(frames, list):
        return errors + ["frames must be an array"]
    seen: set[str] = set()
    seen_indices: set[int] = set()
    for i, frame in enumerate(frames):
        prefix = f"frames[{i}]"
        if not isinstance(frame, dict): errors.append(f"{prefix} must be an object"); continue
        unknown = set(frame) - {"frame_id", "frame_index", "mapping", "canonical_to_source", "annotations", "review", "synthetic_background", "excluded"}
        if unknown: errors.append(f"{prefix} has unknown fields: {','.join(sorted(map(str, unknown)))}")
        fid = frame.get("frame_id")
        if not isinstance(fid, str) or not fid: errors.append(f"{prefix}.frame_id is required")
        elif fid in seen: errors.append(f"duplicate frame_id: {fid}")
        else: seen.add(fid)
        if not isinstance(frame.get("frame_index"), int) or isinstance(frame.get("frame_index"), bool) or frame["frame_index"] < 0: errors.append(f"{prefix}.frame_index is invalid")
        elif frame["frame_index"] in seen_indices: errors.append(f"duplicate source frame_index: {frame['frame_index']}")
        else: seen_indices.add(frame["frame_index"])
        if not isinstance(frame.get("annotations"), dict): errors.append(f"{prefix}.annotations is required")
        if "synthetic_background" in frame and not isinstance(frame["synthetic_background"], bool): errors.append(f"{prefix}.synthetic_background must be boolean")
        if frame.get("synthetic_background") is True: errors.append(f"{prefix} uses a synthetic background")
        if "excluded" in frame and not isinstance(frame["excluded"], bool): errors.append(f"{prefix}.excluded must be boolean")
        mapping = frame.get("mapping", {})
        if isinstance(mapping, dict):
            unknown = set(mapping) - {"x", "y", "width", "height"}
            if unknown: errors.append(f"{prefix}.mapping has unknown fields: {','.join(sorted(map(str, unknown)))}")
        if not isinstance(mapping, dict) or any(not _finite_number(mapping.get(k)) for k in ("x", "y", "width", "height")) or mapping.get("width", 0) <= 0 or mapping.get("height", 0) <= 0:
            errors.append(f"{prefix}.mapping is malformed")
        transform = frame.get("canonical_to_source")
        if not isinstance(transform, list) or len(transform) != 6 or any(not _finite_number(v) for v in transform):
            errors.append(f"{prefix}.canonical_to_source is malformed")
        if "review" not in frame:
            errors.append(f"{prefix}.review is required")
            review = {}
        else:
            review = frame["review"]
        if not isinstance(review, dict):
            errors.append(f"{prefix}.review must be an object")
            review = {}
        reviewers = review.get("reviewers")
        valid_reviewers = isinstance(reviewers, list) and all(isinstance(reviewer, str) and reviewer for reviewer in reviewers)
        if review.get("status") != "reviewed" or not valid_reviewers or len(set(reviewers)) < 2: errors.append(f"{prefix} is not independently reviewed")
        unknown = set(review) - {"reviewers", "status", "disagreement"}
        if unknown: errors.append(f"{prefix}.review has unknown fields: {','.join(sorted(map(str, unknown)))}")
        if not isinstance(review.get("disagreement"), bool): errors.append(f"{prefix}.review.disagreement must be boolean")
        annotations = frame.get("annotations")
        if not isinstance(annotations, dict):
            continue
        if any(not isinstance(field, str) for field in annotations):
            errors.append(f"{prefix}.annotations field names must be strings")
            continue
        unsupported = set(annotations) - SUPPORTED_FIELDS
        if unsupported: errors.append(f"{prefix} has unsupported fields: {','.join(sorted(unsupported))}")
        for field, value in annotations.items():
            if not isinstance(value, dict) or not isinstance(value.get("status"), str) or value["status"] not in STATUSES: errors.append(f"{prefix}.annotations.{field} has invalid status")
            if isinstance(value, dict):
                unknown = set(value) - {"status", "raw", "normalized", "contradictory", "oracle", "ground_truth", "reference_value"}
                if unknown: errors.append(f"{prefix}.annotations.{field} has unknown fields: {','.join(sorted(map(str, unknown)))}")
            if isinstance(value, dict) and value.get("status") == "observed" and "raw" not in value: errors.append(f"{prefix}.annotations.{field} lacks raw value")
            if isinstance(value, dict) and "normalized" in value and "raw" not in value: errors.append(f"{prefix}.annotations.{field} normalized value lacks raw value")
            if isinstance(value, dict) and any(key in value for key in ("oracle", "ground_truth", "reference_value")): errors.append(f"{prefix}.annotations.{field} contains oracle/reference data")
            if isinstance(value, dict) and _has_nonfinite(value): errors.append(f"{prefix}.annotations.{field} contains non-finite number")
            if isinstance(value, dict) and value.get("contradictory") is True: errors.append(f"{prefix}.annotations.{field} is contradictory")
    return errors

def validate_split_assignments(manifests: list[dict[str, Any]]) -> list[str]:
    """Reject video/run reuse across splits and adjacent source frames across partitions."""
    errors: list[str] = []
    video_splits: dict[str, str] = {}
    run_splits: dict[str, str] = {}
    frame_assignments: dict[tuple[str, int], tuple[str, int]] = {}
    for manifest_index, manifest in enumerate(manifests):
        if not isinstance(manifest, dict):
            errors.append(f"manifests[{manifest_index}] must be an object")
            continue
        source = manifest.get("source")
        frames = manifest.get("frames")
        if not isinstance(source, dict) or not isinstance(frames, list):
            errors.append(f"manifests[{manifest_index}] requires source object and frames array")
            continue
        validation_errors = validate_manifest(manifest)
        errors.extend(f"manifests[{manifest_index}]: {error}" for error in validation_errors)
        video_sha = source.get("video_sha256")
        run_sha = source.get("run_sha256")
        split = source.get("split")
        if not all(isinstance(value, str) and value for value in (video_sha, run_sha, split)):
            errors.append(f"manifests[{manifest_index}] has invalid source split identity")
            continue
        previous_split = video_splits.setdefault(video_sha, split)
        if previous_split != split:
            errors.append(f"source video assigned to multiple splits: {video_sha}")
        previous_split = run_splits.setdefault(run_sha, split)
        if previous_split != split:
            errors.append(f"source run assigned to multiple splits: {run_sha}")
        for frame_index, frame in enumerate(frames):
            if not isinstance(frame, dict):
                continue
            index = frame.get("frame_index")
            if isinstance(index, bool) or not isinstance(index, int) or index < 0:
                continue
            frame_key = (video_sha, index)
            previous = frame_assignments.setdefault(frame_key, (split, manifest_index))
            if previous[0] != split:
                errors.append(f"source frame assigned to multiple splits: {video_sha} frame {index}")
            elif previous[1] != manifest_index:
                errors.append(f"duplicate source frame across manifests: {video_sha} frame {index}")
    by_video: dict[str, list[tuple[int, str]]] = {}
    for (video_sha, frame_index), (split, _) in frame_assignments.items():
        by_video.setdefault(video_sha, []).append((frame_index, split))
    for video_sha, assignments in by_video.items():
        assignments.sort()
        for (left_index, left_split), (right_index, right_split) in zip(assignments, assignments[1:]):
            if right_index - left_index <= 1 and left_split != right_split:
                errors.append(f"neighboring source frames cross splits: {video_sha} frames {left_index},{right_index}")
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
    return {"frames": len(frames), "reviewed": reviewed, "review_status_is_self_reported": True, "coverage": reviewed / len(frames) if frames else 0.0, "disagreements": disagreements, "missing_or_unavailable_values": missing, "exclusions": exclusions}

def export_manifest(manifest: dict[str, Any], destination: Path, split_context: list[dict[str, Any]] | None = None) -> None:
    errors = validate_manifest(manifest)
    is_held_out = isinstance(manifest, dict) and isinstance(manifest.get("source"), dict) and manifest["source"].get("split") == "held_out"
    if is_held_out:
        if not split_context:
            errors.append("held-out export requires at least one development split_context manifest")
        elif not any(isinstance(context, dict) and isinstance(context.get("source"), dict) and context["source"].get("split") == "development" for context in split_context):
            errors.append("held-out split_context must include development manifests")
    if split_context is not None:
        errors.extend(validate_split_assignments([*split_context, manifest]))
    if errors: raise ValueError("invalid evaluation manifest: " + "; ".join(errors))
    result = dict(manifest)
    result["frames"] = sorted(manifest["frames"], key=lambda f: (f["frame_index"], f["frame_id"]))
    destination.parent.mkdir(parents=True, exist_ok=True)
    destination.write_text(json.dumps(result, sort_keys=True, indent=2) + "\n", encoding="utf-8")

def main() -> int:
    parser = argparse.ArgumentParser()
    parser.add_argument("input", type=Path); parser.add_argument("output", type=Path)
    parser.add_argument("--split-context", type=Path, action="append", default=[], help="sibling split manifests used to validate source/frame separation")
    args = parser.parse_args()
    manifest = json.loads(args.input.read_text(encoding="utf-8"))
    split_context = [json.loads(path.read_text(encoding="utf-8")) for path in args.split_context]
    export_manifest(manifest, args.output, split_context=split_context if args.split_context else None)
    return 0

if __name__ == "__main__": raise SystemExit(main())
