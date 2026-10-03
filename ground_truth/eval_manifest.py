"""Reviewed first-slice visual annotations; never derives observations from oracle data.

Input is a caller-authored JSON document (see planning/FIRST_SLICE_ANNOTATION.md).
The exporter validates the complete document before writing a deterministic manifest.
"""

import argparse
import hashlib
import json
import math
from collections import Counter
from pathlib import Path


SCHEMA = "first-slice-annotations/1"
MANIFEST = "first-slice-evaluation/1"
PROTOCOL = "FIRST_SLICE_PROTOCOL_V1"
STAGES = {"start", "small_blind_select", "small_blind_play", "cash_out", "first_shop"}
FAMILIES = {"page", "control", "object", "ocr", "transition"}
STATES = {"observed", "unknown", "missing", "occluded", "ambiguous", "unsupported", "not_applicable"}
SPLITS = {"development", "held_out", "training", "synthetic"}


class AnnotationError(ValueError):
    """Input cannot be exported without inventing or losing evidence."""


def require(test, message):
    if not test:
        raise AnnotationError(message)


def fields(obj, required, allowed, where):
    require(isinstance(obj, dict), f"{where}: expected object")
    require(set(required) <= obj.keys(), f"{where}: missing {sorted(set(required) - obj.keys())}")
    require(obj.keys() <= set(allowed), f"{where}: unexpected {sorted(obj.keys() - set(allowed))}")


def text(value, where):
    require(isinstance(value, str) and bool(value.strip()), f"{where}: nonempty text required")


def number(value, where, positive=False):
    require(isinstance(value, (int, float)) and not isinstance(value, bool)
            and math.isfinite(value) and (not positive or value > 0), f"{where}: invalid number")


def digest(value, where):
    require(isinstance(value, str) and len(value) == 64
            and all(c in "0123456789abcdef" for c in value), f"{where}: lowercase sha256 required")


def unique_pairs(pairs):
    result = {}
    for key, value in pairs:
        require(key not in result, f"duplicate JSON key: {key}")
        result[key] = value
    return result


def invalid_constant(value):
    raise AnnotationError(f"non-finite JSON number: {value}")


def box(value, width, height, where):
    require(isinstance(value, list) and len(value) == 4, f"{where}: box must be [x,y,w,h]")
    for v in value:
        number(v, where)
    x, y, w, h = value
    require(w > 0 and h > 0 and x >= 0 and y >= 0 and x + w <= width + 1e-8
            and y + h <= height + 1e-8, f"{where}: box outside bounds or degenerate")


def validate(data):
    fields(data, {"schema", "protocol", "sources", "frames"},
           {"schema", "protocol", "sources", "frames"}, "input")
    require(data["schema"] == SCHEMA and data["protocol"] == PROTOCOL,
            "unsupported annotation schema or protocol")
    require(isinstance(data["sources"], list) and data["sources"], "sources required")
    require(isinstance(data["frames"], list) and data["frames"], "frames required")
    sources, groups = {}, {}
    for source in data["sources"]:
        fields(source, {"id", "run_id", "group", "split", "video_sha256", "session_sha256",
                        "steps_sha256", "alignment", "origin"},
               {"id", "run_id", "group", "split", "video_sha256", "session_sha256",
                "steps_sha256", "alignment", "origin"}, "source")
        for key in ("id", "run_id", "group"):
            text(source[key], f"source.{key}")
        for key in ("video_sha256", "session_sha256", "steps_sha256"):
            digest(source[key], f"source.{key}")
        require(isinstance(source["split"], str) and source["split"] in SPLITS,
                "invalid split")
        require(isinstance(source["origin"], str) and source["origin"] in {"real", "synthetic"},
                "invalid origin")
        require((source["origin"] == "synthetic") == (source["split"] == "synthetic"),
                "synthetic source must be isolated")
        fields(source["alignment"], {"method", "version", "marker", "offset_ns", "fps"},
               {"method", "version", "marker", "offset_ns", "fps"}, "alignment")
        for key in ("method", "version", "marker"):
            text(source["alignment"][key], f"alignment.{key}")
        number(source["alignment"]["offset_ns"], "alignment.offset_ns")
        number(source["alignment"]["fps"], "alignment.fps", positive=True)
        require(source["id"] not in sources, "duplicate source id")
        sources[source["id"]] = source
        for key in (source["group"], source["video_sha256"], source["run_id"]):
            if key in groups:
                require(groups[key] == source["split"], "source/run/group split leakage")
            groups[key] = source["split"]

    seen_frames = set()
    frame_splits = {}
    frame_indices = {}
    for frame in data["frames"]:
        fields(frame, {"source_id", "index", "timestamp_ns", "step_id", "stage", "frame_sha256",
                       "alignment", "geometry", "coverage", "labels"},
               {"source_id", "index", "timestamp_ns", "step_id", "stage", "frame_sha256",
                "alignment", "geometry", "coverage", "labels", "exclusion"}, "frame")
        text(frame["source_id"], "frame.source_id")
        require(frame["source_id"] in sources, "frame source missing")
        require(isinstance(frame["index"], int) and not isinstance(frame["index"], bool)
                and frame["index"] >= 0, "invalid frame index")
        identity = (frame["source_id"], frame["index"])
        require(identity not in seen_frames, "duplicate frame")
        seen_frames.add(identity)
        frame_indices.setdefault(frame["source_id"], set()).add(frame["index"])
        number(frame["timestamp_ns"], "frame.timestamp_ns")
        require(frame["timestamp_ns"] >= 0, "negative timestamp")
        require(frame["step_id"] is None or isinstance(frame["step_id"], (str, int)),
                "invalid step identity")
        require(isinstance(frame["stage"], str) and frame["stage"] in STAGES, "invalid stage")
        digest(frame["frame_sha256"], "frame.frame_sha256")
        split = sources[frame["source_id"]]["split"]
        prior = frame_splits.setdefault(frame["frame_sha256"], split)
        require(prior == split, "identical frame across splits")
        fields(frame["alignment"], {"state", "uncertainty_frames", "evidence"},
               {"state", "uncertainty_frames", "evidence"}, "frame.alignment")
        alignment = frame["alignment"]
        require(isinstance(alignment["state"], str)
                and alignment["state"] in {"confirmed", "unverified", "failed", "disputed"},
                "invalid alignment state")
        require(alignment["uncertainty_frames"] is None or
                (isinstance(alignment["uncertainty_frames"], int)
                 and not isinstance(alignment["uncertainty_frames"], bool)
                 and alignment["uncertainty_frames"] >= 0), "invalid alignment uncertainty")
        text(alignment["evidence"], "alignment.evidence")
        if alignment["state"] == "confirmed":
            require(frame["step_id"] is not None and alignment["uncertainty_frames"] is not None,
                    "confirmed alignment needs step and uncertainty")
        if "exclusion" in frame:
            text(frame["exclusion"], "frame.exclusion")
        geometry = frame["geometry"]
        fields(geometry, {"canonical_size", "source_size", "scale", "offset", "active_source_box"},
               {"canonical_size", "source_size", "scale", "offset", "active_source_box"}, "geometry")
        for key in ("canonical_size", "source_size", "scale", "offset"):
            require(isinstance(geometry[key], list) and len(geometry[key]) == 2,
                    f"geometry.{key}: pair required")
            for value in geometry[key]:
                number(value, f"geometry.{key}", positive=key != "offset")
        for key in ("canonical_size", "source_size"):
            require(all(isinstance(v, int) and not isinstance(v, bool) for v in geometry[key]),
                    f"geometry.{key}: pixel dimensions must be integers")
        cw, ch = geometry["canonical_size"]
        sw, sh = geometry["source_size"]
        box(geometry["active_source_box"], sw, sh, "active_source_box")
        sx, sy = geometry["scale"]
        ox, oy = geometry["offset"]
        require(0 <= ox and 0 <= oy and ox + cw * sx <= sw + 1e-8
                and oy + ch * sy <= sh + 1e-8, "non-invertible or out-of-source transform")
        active = geometry["active_source_box"]
        require(active[0] <= ox + 1e-8 and active[1] <= oy + 1e-8
                and ox + cw * sx <= active[0] + active[2] + 1e-8
                and oy + ch * sy <= active[1] + active[3] + 1e-8,
                "canonical viewport outside active region")
        fields(frame["coverage"], FAMILIES, FAMILIES, "frame.coverage")
        for family, coverage in frame["coverage"].items():
            fields(coverage, {"state", "reason"}, {"state", "reason"}, "coverage")
            require(isinstance(coverage["state"], str)
                    and coverage["state"] in {"reviewed", "absent", "unreviewed", "excluded"},
                    "invalid family coverage state")
            text(coverage["reason"], f"coverage.{family}.reason")
        require(isinstance(frame["labels"], list), "labels must be list")
        label_ids, occupied = set(), set()
        for label in frame["labels"]:
            fields(label, {"id", "family", "key", "state", "raw", "normalized", "inferred",
                           "annotator", "reviewer", "review", "adjudicated", "rationale"},
                   {"id", "family", "key", "state", "raw", "normalized", "inferred",
                    "annotator", "reviewer", "review", "adjudicated", "rationale",
                    "box", "zone", "order", "attributes", "context_frames"}, "label")
            for key in ("id", "key", "annotator", "reviewer", "rationale"):
                text(label[key], f"label.{key}")
            require(label["annotator"] != label["reviewer"], "review must be independent")
            require(isinstance(label["family"], str) and label["family"] in FAMILIES
                    and isinstance(label["state"], str) and label["state"] in STATES,
                    "invalid label family/state")
            require(frame["coverage"][label["family"]]["state"] == "reviewed",
                    "label family must have reviewed coverage")
            require(isinstance(label["review"], str)
                    and label["review"] in {"agree", "disagree", "excluded"}, "invalid review")
            require(label["id"] not in label_ids, "duplicate label id")
            label_ids.add(label["id"])
            slot = (label["family"], label["key"])
            require(slot not in occupied, "contradictory label slot")
            occupied.add(slot)
            require(isinstance(label["raw"], (str, int, float, bool, dict, list, type(None))),
                    "invalid raw label")
            if label["state"] == "observed":
                require(label["raw"] is not None, "observed label needs raw visual evidence")
            else:
                require(label["raw"] is None and label["normalized"] is None,
                        "unobserved label cannot acquire normalized visual value")
            if label["normalized"] is not None:
                require(label["raw"] is not None, "normalization needs raw value")
            if label["inferred"] is not None:
                fields(label["inferred"], {"value", "method", "evidence"},
                       {"value", "method", "evidence"}, "inference")
                text(label["inferred"]["method"], "inference.method")
                text(label["inferred"]["evidence"], "inference.evidence")
            if label["review"] == "agree":
                require(label["adjudicated"] == label["raw"], "agree review must preserve original")
            elif label["review"] == "disagree":
                require(label["adjudicated"] is not None or label["state"] != "observed",
                        "disagreement needs adjudication or unresolved state")
            else:
                require(label["adjudicated"] is None, "excluded review cannot become truth")
            if "box" in label:
                box(label["box"], cw, ch, "label.box")
                x, y, w, h = label["box"]
                source_box = [ox + x * sx, oy + y * sy, w * sx, h * sy]
                box(source_box, sw, sh, "mapped source box")
                box([source_box[0] - active[0], source_box[1] - active[1],
                     source_box[2], source_box[3]], active[2], active[3], "mapped active box")
            for optional in ("zone", "attributes"):
                if optional in label:
                    require(isinstance(label[optional], (str, dict)) and bool(label[optional]),
                            f"invalid {optional}")
            if "order" in label:
                require(isinstance(label["order"], int) and not isinstance(label["order"], bool)
                        and label["order"] >= 0, "invalid order")
            if label["family"] == "object" and label["state"] == "observed":
                require("box" in label and isinstance(label.get("zone"), str)
                        and bool(label["zone"].strip()) and "order" in label
                        and isinstance(label.get("attributes"), dict)
                        and {"identity", "edition", "seal", "sticker", "modifier"}
                        <= label["attributes"].keys(),
                        "observed object needs box, zone, order and explicit attribute states")
                for attribute in ("identity", "edition", "seal", "sticker", "modifier"):
                    text(label["attributes"][attribute], f"object.{attribute}")
            if label["family"] == "transition":
                require("context_frames" in label and isinstance(label["context_frames"], list)
                        and all(isinstance(i, int) and not isinstance(i, bool) and i >= 0
                                for i in label["context_frames"]), "transition needs context frames")
            elif "context_frames" in label:
                raise AnnotationError("only transitions may use context frames")
        for family in FAMILIES:
            if frame["coverage"][family]["state"] == "reviewed":
                require(any(label["family"] == family for label in frame["labels"]),
                        "reviewed family needs a label or absent coverage")
    for frame in data["frames"]:
        for label in frame["labels"]:
            if label["family"] == "transition":
                require(set(label["context_frames"]) <= frame_indices[frame["source_id"]],
                        "transition context references missing source frames")
    return data


def build(data):
    validate(data)
    sources = sorted(data["sources"], key=lambda s: s["id"])
    frames = []
    counts = Counter()
    coverage_counts = Counter()
    for frame in sorted(data["frames"], key=lambda f: (f["source_id"], f["index"])):
        entry = dict(frame)
        entry["labels"] = []
        geometry = frame["geometry"]
        sx, sy = geometry["scale"]
        ox, oy = geometry["offset"]
        for family, coverage in frame["coverage"].items():
            coverage_counts[(frame["source_id"], frame["stage"], family,
                             coverage["state"])] += 1
        for label in sorted(frame["labels"], key=lambda l: (l["family"], l["key"])):
            item = dict(label)
            if "box" in item:
                x, y, w, h = item["box"]
                item["source_box"] = [ox + x * sx, oy + y * sy, w * sx, h * sy]
            entry["labels"].append(item)
            counts[(frame["source_id"], frame["stage"], label["family"], label["state"], label["review"])] += 1
        frames.append(entry)
    report = [{"source_id": s, "stage": stage, "family": family, "state": state,
               "review": review, "count": count}
              for (s, stage, family, state, review), count in sorted(counts.items())]
    coverage_report = [{"source_id": s, "stage": stage, "family": family,
                        "state": state, "frame_count": count}
                       for (s, stage, family, state), count in sorted(coverage_counts.items())]
    return {"schema": MANIFEST, "protocol": PROTOCOL, "sources": sources,
            "frames": frames, "pilot_counts": report, "coverage_counts": coverage_report,
            "scoring_status": "development_only_unscored"}


def export(input_path, output_path):
    source = Path(input_path).resolve()
    dest = Path(output_path).resolve()
    require(source != dest, "output cannot overwrite source evidence")
    require(dest.parent.is_dir(), "output parent does not exist")
    data = json.loads(source.read_text(encoding="utf-8"), object_pairs_hook=unique_pairs,
                      parse_constant=invalid_constant)
    result = build(data)
    payload = (json.dumps(result, sort_keys=True, ensure_ascii=False, separators=(",", ":"),
                          allow_nan=False) + "\n").encode("utf-8")
    if dest.exists():
        require(dest.is_file() and dest.read_bytes() == payload,
                "output already exists with different bytes; select a new destination")
    else:
        dest.write_bytes(payload)
    return hashlib.sha256(payload).hexdigest()


def main():
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("input", help="caller-authored annotations JSON")
    parser.add_argument("output", help="caller-selected external evaluation manifest path")
    args = parser.parse_args()
    try:
        print(export(args.input, args.output))
    except (AnnotationError, ValueError, OSError) as exc:
        parser.error(str(exc))


if __name__ == "__main__":
    main()
