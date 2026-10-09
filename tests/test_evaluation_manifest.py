import json
from pathlib import Path

import pytest

from planning.evaluation_manifest import export_manifest, pilot_report, validate_manifest, validate_split_assignments


def manifest():
    frame = lambda fid, index, annotations: {"frame_id": fid, "frame_index": index, "mapping": {"x": 0, "y": 0, "width": 10, "height": 10}, "canonical_to_source": [1, 0, 0, 0, 1, 0], "annotations": annotations, "review": {"reviewers": ["qa1", "qa2"], "status": "reviewed"}}
    return {"schema_version": "evaluation-slice-1.0", "protocol": "v1", "source": {"video_sha256": "a" * 64, "run_sha256": "b" * 64, "alignment_sha256": "c" * 64, "split": "development", "width": 1920, "height": 1080}, "frames": [frame("f2", 2, {"page": {"status": "unknown"}}), frame("f1", 1, {})]}

def test_export_is_sorted_and_stable(tmp_path: Path):
    first, second = tmp_path / "a.json", tmp_path / "b.json"
    export_manifest(manifest(), first); export_manifest(manifest(), second)
    assert first.read_bytes() == second.read_bytes()
    assert [f["frame_id"] for f in json.loads(first.read_text())["frames"]] == ["f1", "f2"]

def test_rejects_unreviewed_and_duplicate():
    value = manifest(); value["frames"][1]["frame_id"] = "f2"; value["frames"][1]["review"]["status"] = "incomplete"
    errors = validate_manifest(value)
    assert any("duplicate" in e for e in errors)
    assert any("not independently reviewed" in e for e in errors)

def test_unhashable_reviewer_is_a_validation_error():
    value = manifest(); value["frames"][0]["review"]["reviewers"] = [{}]
    assert any("not independently reviewed" in e for e in validate_manifest(value))
    value["frames"][0]["review"]["reviewers"] = [["qa1"], ["qa2"]]
    assert any("not independently reviewed" in e for e in validate_manifest(value))

def test_invalid_mapping_is_not_repaired(tmp_path: Path):
    value = manifest(); value["frames"][0]["mapping"]["width"] = 0
    with pytest.raises(ValueError, match="mapping"):
        export_manifest(value, tmp_path / "out.json")

def test_report_counts_review_and_missingness():
    value = manifest(); value["frames"][0]["review"]["disagreement"] = True
    assert pilot_report(value) == {"frames": 2, "reviewed": 2, "review_status_is_self_reported": True, "coverage": 1.0, "disagreements": 1, "missing_or_unavailable_values": 1, "exclusions": 0}

def test_rejects_oracle_promotion_and_boolean_dimensions():
    value = manifest(); value["source"]["width"] = True
    value["frames"][0]["annotations"]["page"] = {"status": "observed", "raw": "shop", "oracle": "shop"}
    errors = validate_manifest(value)
    assert any("source.width" in e for e in errors)
    assert any("oracle/reference" in e for e in errors)

def test_rejects_nested_nonfinite_annotation_values():
    value = manifest(); value["frames"][0]["annotations"]["page"] = {"status": "observed", "raw": {"score": float("nan")}}
    assert any("non-finite" in e for e in validate_manifest(value))

def test_malformed_manifest_shapes_return_diagnostics():
    value = manifest(); value["frames"][0]["review"] = None
    assert any("review must be an object" in e for e in validate_manifest(value))
    assert validate_manifest(None) == ["manifest must be an object"]
    value["frames"] = None
    assert any("frames must be an array" in e for e in validate_manifest(value))
    assert pilot_report({"frames": None})["frames"] == 0
    value = manifest(); value["frames"][0]["annotations"] = {1: {"status": "unknown"}}
    assert any("field names must be strings" in e for e in validate_manifest(value))
    value["frames"][0]["annotations"] = {"page": {"status": []}}
    assert any("invalid status" in e for e in validate_manifest(value))

def test_split_validation_blocks_source_and_neighbor_leakage():
    first = manifest(); second = manifest()
    first["source"]["split"] = "development"
    second["source"]["split"] = "held_out"
    second["frames"] = [{**second["frames"][0], "frame_index": 3}]
    errors = validate_split_assignments([first, second])
    assert any("source video assigned" in e for e in errors)
    assert any("neighboring source frames cross splits" in e for e in errors)

def test_split_validation_allows_distant_frames_only_if_same_source_split():
    first = manifest(); second = manifest()
    first["frames"] = [{**first["frames"][0], "frame_index": 1}]
    second["frames"] = [{**second["frames"][1], "frame_index": 100}]
    assert validate_split_assignments([first, second]) == []

def test_schema_enums_match_runtime_contract():
    from planning.evaluation_manifest import SCHEMA_VERSION, STATUSES, SUPPORTED_FIELDS

    schema_path = Path(__file__).resolve().parents[1] / "planning" / "evaluation_manifest.schema.json"
    schema = json.loads(schema_path.read_text(encoding="utf-8"))
    assert schema["properties"]["schema_version"]["const"] == SCHEMA_VERSION
    frame_properties = schema["properties"]["frames"]["items"]["properties"]
    assert set(frame_properties["annotations"]["propertyNames"]["enum"]) == SUPPORTED_FIELDS
    assert set(frame_properties["annotations"]["additionalProperties"]["properties"]["status"]["enum"]) == STATUSES
    assert set(schema["properties"]["source"]["properties"]["split"]["enum"]) == {"development", "held_out"}

def test_held_out_export_requires_and_checks_development_split_context(tmp_path: Path):
    development = manifest()
    held_out = manifest()
    held_out["source"]["split"] = "held_out"
    with pytest.raises(ValueError, match="requires at least one development"):
        export_manifest(held_out, tmp_path / "held-out.json")
    with pytest.raises(ValueError, match="requires at least one development"):
        export_manifest(held_out, tmp_path / "held-out.json", split_context=[])

    held_out["source"]["video_sha256"] = "d" * 64
    held_out["source"]["run_sha256"] = "e" * 64
    export_manifest(held_out, tmp_path / "held-out.json", split_context=[development])

    held_out["source"]["video_sha256"] = development["source"]["video_sha256"]
    with pytest.raises(ValueError, match="video assigned to multiple splits"):
        export_manifest(held_out, tmp_path / "leaky.json", split_context=[development])

    held_out["source"]["video_sha256"] = "d" * 64
    held_out["source"]["run_sha256"] = development["source"]["run_sha256"]
    with pytest.raises(ValueError, match="run assigned to multiple splits"):
        export_manifest(held_out, tmp_path / "leaky-run.json", split_context=[development])
