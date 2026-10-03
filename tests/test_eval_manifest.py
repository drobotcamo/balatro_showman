import copy
import json

import pytest

from ground_truth.eval_manifest import AnnotationError, build, export


H = "a" * 64


def sample():
    return {
        "schema": "first-slice-annotations/1", "protocol": "FIRST_SLICE_PROTOCOL_V1",
        "sources": [{"id": "video-1", "run_id": "run-1", "group": "play-1",
                     "split": "development", "origin": "real", "video_sha256": H,
                     "session_sha256": "b" * 64, "steps_sha256": "c" * 64,
                     "alignment": {"method": "marker", "version": "1", "marker": "marker-1",
                                   "offset_ns": 0, "fps": 60}}],
        "frames": [{"source_id": "video-1", "index": 42, "timestamp_ns": 700000000,
                    "step_id": "step-1", "stage": "small_blind_select", "frame_sha256": "d" * 64,
                    "alignment": {"state": "confirmed", "uncertainty_frames": 3,
                                  "evidence": "independent rendered pre-action check"},
                    "geometry": {"canonical_size": [960, 540], "source_size": [1920, 1080],
                                 "scale": [2, 2], "offset": [0, 0],
                                 "active_source_box": [0, 0, 1920, 1080]},
                    "coverage": {family: {"state": "reviewed" if family == "page" else "absent",
                                          "reason": "visible heading" if family == "page" else "not sampled"}
                                 for family in ("page", "control", "object", "ocr", "transition")},
                    "labels": [{"id": "page-1", "family": "page", "key": "page_name",
                                "state": "observed", "raw": "blind select", "normalized": "blind_select",
                                "inferred": None, "annotator": "first", "reviewer": "second",
                                "review": "agree", "adjudicated": "blind select",
                                "rationale": "visible heading", "box": [10, 20, 30, 40]}]}],
    }


def test_deterministic_order_and_source_mapping(tmp_path):
    first = sample()
    other = copy.deepcopy(first["frames"][0])
    other["index"] = 5
    other["frame_sha256"] = "e" * 64
    first["frames"].append(other)
    second = copy.deepcopy(first)
    second["frames"].reverse()
    assert build(first) == build(second)
    label = build(first)["frames"][1]["labels"][0]
    assert label["source_box"] == [20, 40, 60, 80]
    input_file, output = tmp_path / "input.json", tmp_path / "output.json"
    input_file.write_text(json.dumps(first), encoding="utf-8")
    digest = export(input_file, output)
    assert digest == export(input_file, output)
    assert output.read_bytes().endswith(b"\n")
    changed = sample()
    input_file.write_text(json.dumps(changed), encoding="utf-8")
    with pytest.raises(AnnotationError, match="different bytes"):
        export(input_file, output)


@pytest.mark.parametrize("mutate", [
    lambda d: d.update(schema="first-slice-annotations/2"),
    lambda d: d["frames"].append(copy.deepcopy(d["frames"][0])),
    lambda d: d["frames"][0]["geometry"].update(scale=[0, 2]),
    lambda d: d["frames"][0]["geometry"].update(active_source_box=[0, 0, 100, 100]),
    lambda d: d["frames"][0]["labels"][0].update(box=[950, 20, 30, 40]),
    lambda d: d["frames"][0]["labels"][0].update(review="agree", adjudicated="shop"),
    lambda d: d["frames"][0]["labels"][0].update(reviewer="first"),
    lambda d: d["frames"][0]["labels"][0].update(state="unknown", raw="blind select"),
    lambda d: d["frames"][0]["labels"][0].update(family="transition"),
    lambda d: d["frames"][0]["alignment"].update(uncertainty_frames=None),
    lambda d: d["sources"][0].update(video_sha256="not a hash"),
    lambda d: d["frames"][0].update(source_id="missing"),
])
def test_invalid_evidence_rejected(mutate):
    data = sample()
    mutate(data)
    with pytest.raises(AnnotationError):
        build(data)


def test_source_split_and_synthetic_isolation():
    data = sample()
    duplicate = copy.deepcopy(data["sources"][0])
    duplicate.update(id="other", split="held_out")
    data["sources"].append(duplicate)
    with pytest.raises(AnnotationError, match="leakage"):
        build(data)
    data = sample()
    data["sources"][0]["origin"] = "synthetic"
    with pytest.raises(AnnotationError, match="isolated"):
        build(data)


def test_object_and_transition_require_inspectable_context():
    data = sample()
    label = data["frames"][0]["labels"][0]
    data["frames"][0]["coverage"]["page"]["state"] = "absent"
    data["frames"][0]["coverage"]["object"]["state"] = "reviewed"
    label.update(family="object", zone="hand", order=0,
                 attributes={key: "unknown" for key in
                             ("identity", "edition", "seal", "sticker", "modifier")})
    build(data)
    label.pop("attributes")
    with pytest.raises(AnnotationError, match="attribute states"):
        build(data)
    data["frames"][0]["coverage"]["object"]["state"] = "absent"
    data["frames"][0]["coverage"]["transition"]["state"] = "reviewed"
    label.update(family="transition", context_frames=[999])
    with pytest.raises(AnnotationError, match="missing source frames"):
        build(data)


def test_unknown_review_and_unverified_alignment_remain_visible():
    data = sample()
    frame = data["frames"][0]
    frame["alignment"] = {"state": "disputed", "uncertainty_frames": None,
                          "evidence": "timestamp mapping not visually confirmed"}
    frame["exclusion"] = "oracle comparison unscored"
    frame["labels"][0].update(state="ambiguous", raw=None, normalized=None,
                              review="disagree", adjudicated=None)
    result = build(data)
    assert result["scoring_status"] == "development_only_unscored"
    assert result["frames"][0]["labels"][0]["state"] == "ambiguous"
    assert result["pilot_counts"][0]["count"] == 1


def test_cross_split_frame_leak_and_omitted_family_rejected():
    data = sample()
    second = copy.deepcopy(data["sources"][0])
    second.update(id="independent", group="play-2", run_id="run-2", split="held_out",
                  video_sha256="e" * 64)
    data["sources"].append(second)
    frame = copy.deepcopy(data["frames"][0])
    frame["source_id"] = "independent"
    data["frames"].append(frame)
    with pytest.raises(AnnotationError, match="identical frame"):
        build(data)
    data = sample()
    data["frames"][0]["labels"] = []
    with pytest.raises(AnnotationError, match="reviewed family"):
        build(data)
