import json
from pathlib import Path

from planning.mechanics_contract_check import initial_examples, load_example, validate_document, validate_schema_envelope


def test_positive_dagger_fixture_has_resolved_run_references():
    assert validate_document(load_example()) == []


def test_all_initial_review_examples_have_resolved_references():
    assert set(initial_examples()) == {"dagger-positive", "dagger-zero", "dagger-ineligible-right", "dagger-missing-dependency", "scoring", "reset"}
    for example in initial_examples().values():
        assert validate_document(example) == []


def test_dagger_without_right_neighbor_is_known_no_destruction_no_growth():
    example = initial_examples()["dagger-zero"]
    neighbor_fact = next(f for f in example["facts"] if f["property"] == "right_neighbor_present")
    dagger_after = next(f for f in example["facts"] if f["id"] == "fact-dagger-mult-after")

    assert neighbor_fact["value"] is False
    assert example["effects"] == []
    assert dagger_after["value"] == 6


def test_dagger_with_ineligible_right_neighbor_is_known_no_destruction_no_growth():
    example = initial_examples()["dagger-ineligible-right"]

    assert example["effects"] == []
    assert next(f for f in example["facts"] if f["id"] == "fact-dagger-mult-after")["value"] == 14


def test_examples_use_the_checked_in_schema_envelope():
    for example in initial_examples().values():
        assert validate_schema_envelope(example) == []


def test_effect_with_missing_instance_reference_is_rejected():
    document = load_example()
    document["effects"][0]["source_instance_id"] = "absent-instance"

    findings = validate_document(document)

    assert any(f.code == "reference_missing" and f.path.endswith("source_instance_id") for f in findings)


def test_reference_oracle_evidence_cannot_support_derived_effect():
    document = load_example()
    document["evidence"][0]["channel"] = "reference"
    document["evidence"][0]["kind"] = "oracle_reference"
    document["effects"][0]["evidence_ids"] = [document["evidence"][0]["id"]]

    findings = validate_document(document)

    assert any(f.code == "reference_channel_leak" for f in findings)


def test_reference_fact_cannot_be_used_as_inference_dependency():
    document = load_example()
    fact = document["facts"][1]
    fact["channel"] = "reference"
    document["evidence"].append({
        "id": "ev-oracle-sell-value",
        "channel": "reference",
        "kind": "oracle_reference",
        "step_id": "step-before",
        "visibility": "hidden",
        "source_ref": "oracle-step",
    })
    fact["evidence_ids"] = ["ev-oracle-sell-value"]
    document["effects"][0]["dependency_fact_ids"] = [fact["id"]]

    findings = validate_document(document)

    assert any(f.code == "reference_channel_leak" and "dependency_fact_ids" in f.path for f in findings)


def test_ambiguous_exact_order_is_rejected():
    document = load_example()
    document["effects"][0]["order"].update({"ambiguous": True, "requires_exact_order": True})

    findings = validate_document(document)

    assert any(f.code == "timing_ambiguous" for f in findings)


def test_answer_key_reference_in_mechanics_document_is_rejected():
    document = load_example()
    document["answer_key_refs"] = ["oracle-answer"]

    findings = validate_document(document)

    assert any(f.code == "answer_key_leak" for f in findings)


def test_schema_file_is_valid_json_and_declares_versioned_envelope():
    root = Path(__file__).resolve().parents[1]
    schema = json.loads((root / "planning/schemas/run_mechanics_v0_1.schema.json").read_text(encoding="utf-8"))

    assert schema["$schema"].endswith("2020-12/schema")
    assert schema["properties"]["schema_version"]["const"] == "0.1"
