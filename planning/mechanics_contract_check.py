"""Validate versioned run-mechanics evidence envelopes.

Run from the repository root:
    python planning/mechanics_contract_check.py

This validates evidence/reference separation, references, and timing completeness
for the v0.1 contract envelope. It does not execute game rules or establish the
correctness of any mechanic.
"""

from __future__ import annotations

from dataclasses import dataclass
import json
from pathlib import Path
from typing import Any


class ContractError(ValueError):
    """A record violates the mechanics v0.1 envelope."""


@dataclass(frozen=True)
class Finding:
    code: str
    path: str
    message: str


def validate_envelope(record: dict[str, Any]) -> list[Finding]:
    """Return all envelope violations without interpreting mechanics values."""
    findings: list[Finding] = []
    if not isinstance(record, dict):
        return [Finding("record_type", "$", "record must be an object")]

    record_id = record.get("id")
    if not isinstance(record_id, str) or not record_id.strip():
        findings.append(Finding("record_id", "id", "non-empty string required"))

    status = record.get("status")
    if status not in {"observed", "inferred", "unknown", "ambiguous", "unsupported"}:
        findings.append(Finding("status", "status", "unsupported status value"))

    channel = record.get("channel")
    if channel not in {"observation", "derived", "reference"}:
        findings.append(Finding("channel", "channel", "invalid evidence channel"))

    known_ids = record.get("known_ids")
    if not isinstance(known_ids, list) or any(not isinstance(item, str) or not item.strip() for item in known_ids):
        findings.append(Finding("known_ids_type", "known_ids", "required list of non-empty string identifiers"))
        known_ids = []

    evidence = record.get("evidence")
    if not isinstance(evidence, list):
        findings.append(Finding("evidence_type", "evidence", "required list"))
        evidence = []
    for index, item in enumerate(evidence):
        if not isinstance(item, dict) or not isinstance(item.get("id"), str) or not item["id"]:
            findings.append(Finding("evidence_ref", f"evidence[{index}]", "non-empty evidence id required"))
            continue
        evidence_channel = item.get("channel")
        if evidence_channel not in {"observation", "reference"}:
            findings.append(Finding("evidence_channel", f"evidence[{index}].channel", "must be observation or reference"))
        if item["id"] not in known_ids:
            findings.append(Finding("evidence_missing", f"evidence[{index}].id", f"unresolved evidence id: {item['id']}"))
        if channel in {"observation", "derived"} and evidence_channel == "reference":
            findings.append(Finding("reference_channel_leak", f"evidence[{index}]", "reference evidence cannot support reconstruction output"))
        if channel == "reference" and evidence_channel != "reference":
            findings.append(Finding("observation_as_reference", f"evidence[{index}]", "reference records require reference evidence"))

    references = record.get("references")
    if not isinstance(references, list):
        findings.append(Finding("references_type", "references", "required list"))
        references = []
    for index, ref in enumerate(references):
        if not isinstance(ref, str) or not ref.strip():
            findings.append(Finding("reference_format", f"references[{index}]", "non-empty reference id required"))
        elif ref not in known_ids:
            findings.append(Finding("reference_missing", f"references[{index}]", f"unresolved reference: {ref}"))

    purpose = record.get("purpose")
    if purpose == "reconstruction":
        if record.get("uses_answer_key") is not False:
            findings.append(Finding("answer_key_leak", "uses_answer_key", "reconstruction must explicitly set uses_answer_key to false"))
        if record.get("answer_key_refs") not in (None, []):
            findings.append(Finding("answer_key_leak", "answer_key_refs", "reconstruction cannot cite answer-key/reference values"))

    timing = record.get("timing")
    if not isinstance(timing, dict):
        findings.append(Finding("timing_missing", "timing", "timing object required"))
    else:
        ambiguous = timing.get("ambiguous")
        requires_exact = timing.get("requires_exact_order")
        if not isinstance(ambiguous, bool):
            findings.append(Finding("timing_ambiguous_type", "timing.ambiguous", "boolean required"))
        if not isinstance(requires_exact, bool):
            findings.append(Finding("timing_exact_type", "timing.requires_exact_order", "boolean required"))
        if ambiguous is True and requires_exact is True:
            findings.append(Finding("timing_ambiguous", "timing", "exact ordering required but timing is ambiguous"))
        order_evidence = timing.get("order_evidence")
        if requires_exact is True and (not isinstance(order_evidence, str) or not order_evidence.strip()):
            findings.append(Finding("timing_evidence", "timing.order_evidence", "source/order evidence required for exact timing"))
    return findings


def validate_document(document: dict[str, Any]) -> list[Finding]:
    """Validate v0.1 structure and cross-record references."""
    findings: list[Finding] = []
    if not isinstance(document, dict):
        return [Finding("document_type", "$", "document must be an object")]
    if document.get("schema_version") != "0.1":
        findings.append(Finding("schema_version", "schema_version", "must be 0.1"))
    if not isinstance(document.get("run_id"), str) or not document["run_id"].strip():
        findings.append(Finding("run_id", "run_id", "non-empty string required"))
    if document.get("uses_answer_key") not in (None, False) or document.get("answer_key_refs") not in (None, []):
        findings.append(Finding("answer_key_leak", "answer_key_refs", "v0.1 reconstruction documents cannot consume answer-key values"))

    collections = ("definitions", "instances", "facts", "effects", "evidence", "source_revisions")
    maps: dict[str, dict[str, dict[str, Any]]] = {}
    for collection in collections:
        rows = document.get(collection)
        if not isinstance(rows, list):
            findings.append(Finding("collection_type", collection, "required array"))
            maps[collection] = {}
            continue
        keyed: dict[str, dict[str, Any]] = {}
        for index, row in enumerate(rows):
            path = f"{collection}[{index}]"
            if not isinstance(row, dict):
                findings.append(Finding("record_type", path, "record must be an object"))
                continue
            rid = row.get("id")
            if not isinstance(rid, str) or not rid.strip():
                findings.append(Finding("record_id", f"{path}.id", "non-empty string required"))
                continue
            if rid in keyed:
                findings.append(Finding("duplicate_id", f"{path}.id", f"duplicate id {rid}"))
            keyed[rid] = row
        maps[collection] = keyed

    ids = {collection: set(rows) for collection, rows in maps.items()}
    step_ids = {row.get("step_id") for row in maps["evidence"].values() if isinstance(row.get("step_id"), str)}
    def check_ref(value: Any, target: str, path: str, required: bool = True) -> None:
        if value is None and not required:
            return
        if not isinstance(value, str) or value not in ids[target]:
            findings.append(Finding("reference_missing", path, f"must reference {target} record"))

    for iid, instance in maps["instances"].items():
        check_ref(instance.get("definition_id"), "definitions", f"instances.{iid}.definition_id")
        for n, track in enumerate(instance.get("track_ids", [])):
            if not isinstance(track, str) or not track:
                findings.append(Finding("track_id", f"instances.{iid}.track_ids[{n}]", "non-empty visual track id required"))
        for n, life in enumerate(instance.get("lifecycle", [])):
            if isinstance(life, dict):
                if life.get("step_id") not in step_ids:
                    findings.append(Finding("step_missing", f"instances.{iid}.lifecycle[{n}].step_id", "must reference an evidence source step"))
                for j, eid in enumerate(life.get("evidence_ids", [])):
                    check_ref(eid, "evidence", f"instances.{iid}.lifecycle[{n}].evidence_ids[{j}]")
                check_ref(life.get("target_instance_id"), "instances", f"instances.{iid}.lifecycle[{n}].target_instance_id", required=False)

    for fid, fact in maps["facts"].items():
        check_ref(fact.get("subject_id"), "instances", f"facts.{fid}.subject_id")
        fact_channel = fact.get("channel")
        if fact_channel not in {"observation", "derived", "reference"}:
            findings.append(Finding("fact_channel", f"facts.{fid}.channel", "invalid evidence channel"))
        if fact.get("valid_from") not in step_ids:
            findings.append(Finding("step_missing", f"facts.{fid}.valid_from", "must reference an evidence source step"))
        if fact.get("valid_until") is not None and fact.get("valid_until") not in step_ids:
            findings.append(Finding("step_missing", f"facts.{fid}.valid_until", "must reference an evidence source step"))
        for n, eid in enumerate(fact.get("evidence_ids", [])):
            check_ref(eid, "evidence", f"facts.{fid}.evidence_ids[{n}]")
            evidence = maps["evidence"].get(eid, {})
            if fact_channel in {"observation", "derived"} and evidence.get("channel") == "reference":
                findings.append(Finding("reference_channel_leak", f"facts.{fid}.evidence_ids[{n}]", "observation/derived fact cannot use reference evidence"))
            if fact_channel == "reference" and evidence.get("channel") != "reference":
                findings.append(Finding("reference_kind", f"facts.{fid}.evidence_ids[{n}]", "reference fact must use reference evidence"))

    for eid, evidence in maps["evidence"].items():
        if not isinstance(evidence.get("step_id"), str) or not evidence["step_id"].strip():
            findings.append(Finding("step_id", f"evidence.{eid}.step_id", "non-empty source step identity required"))
        channel, kind = evidence.get("channel"), evidence.get("kind")
        if channel == "observation" and kind == "oracle_reference":
            findings.append(Finding("reference_channel_leak", f"evidence.{eid}.channel", "oracle reference cannot be observation"))
        if channel == "reference" and kind != "oracle_reference":
            findings.append(Finding("reference_kind", f"evidence.{eid}.kind", "reference channel must identify oracle reference"))
        if channel == "observation" and kind not in {"video_observation", "human_annotation", "source_code"}:
            findings.append(Finding("observation_kind", f"evidence.{eid}.kind", "invalid observation evidence kind"))

    occurrences: set[str] = set()
    for effid, effect in maps["effects"].items():
        check_ref(effect.get("source_instance_id"), "instances", f"effects.{effid}.source_instance_id")
        for n, target in enumerate(effect.get("target_ids", [])):
            check_ref(target, "instances", f"effects.{effid}.target_ids[{n}]")
        interval = effect.get("interval", {})
        if isinstance(interval, dict):
            if interval.get("start_step_id") not in step_ids:
                findings.append(Finding("step_missing", f"effects.{effid}.interval.start_step_id", "must reference an evidence source step"))
            if interval.get("end_step_id") not in step_ids:
                findings.append(Finding("step_missing", f"effects.{effid}.interval.end_step_id", "must reference an evidence source step"))
        order = effect.get("order", {})
        if isinstance(order, dict):
            if order.get("ambiguous") is True and order.get("requires_exact_order") is True:
                findings.append(Finding("timing_ambiguous", f"effects.{effid}.order", "exact order required but order is ambiguous"))
            if order.get("requires_exact_order") is True:
                source_id = order.get("source_revision_id")
                check_ref(source_id, "source_revisions", f"effects.{effid}.order.source_revision_id")
                if not order.get("order_evidence_ids"):
                    findings.append(Finding("timing_evidence", f"effects.{effid}.order.order_evidence_ids", "exact order requires source evidence"))
                for n, evidence_id in enumerate(order.get("order_evidence_ids", [])):
                    check_ref(evidence_id, "evidence", f"effects.{effid}.order.order_evidence_ids[{n}]")
        for n, dep in enumerate(effect.get("dependency_fact_ids", [])):
            check_ref(dep, "facts", f"effects.{effid}.dependency_fact_ids[{n}]")
            if maps["facts"].get(dep, {}).get("channel") == "reference":
                findings.append(Finding("reference_channel_leak", f"effects.{effid}.dependency_fact_ids[{n}]", "derived effect cannot depend on reference fact"))
        for n, evidence_id in enumerate(effect.get("evidence_ids", [])):
            check_ref(evidence_id, "evidence", f"effects.{effid}.evidence_ids[{n}]")
            evidence = maps["evidence"].get(evidence_id, {})
            if evidence.get("channel") == "reference":
                findings.append(Finding("reference_channel_leak", f"effects.{effid}.evidence_ids[{n}]", "derived effect cannot use reference evidence"))
        check_ref(effect.get("supersedes_effect_id"), "effects", f"effects.{effid}.supersedes_effect_id", required=False)
        for n, part in enumerate(effect.get("participation", [])):
            if isinstance(part, dict):
                check_ref(part.get("instance_id"), "instances", f"effects.{effid}.participation[{n}].instance_id")
        for n, contribution in enumerate(effect.get("contributions", [])):
            if isinstance(contribution, dict):
                occurrence = contribution.get("occurrence_key")
                path = f"effects.{effid}.contributions[{n}].occurrence_key"
                if not isinstance(occurrence, str) or not occurrence:
                    findings.append(Finding("occurrence_key", path, "non-empty deterministic key required"))
                elif occurrence in occurrences:
                    findings.append(Finding("duplicate_occurrence", path, f"duplicate occurrence {occurrence}"))
                else:
                    occurrences.add(occurrence)
    return findings


def load_example() -> dict[str, Any]:
    path = Path(__file__).resolve().parent / "examples" / "mechanics_v0_1_dagger_positive.json"
    return json.loads(path.read_text(encoding="utf-8"))


def validate_schema_envelope(document: dict[str, Any]) -> list[Finding]:
    """Check the document against the checked-in schema's top-level envelope."""
    schema_path = Path(__file__).resolve().parent / "schemas" / "run_mechanics_v0_1.schema.json"
    schema = json.loads(schema_path.read_text(encoding="utf-8"))
    findings: list[Finding] = []
    if document.get("schema_version") != schema["properties"]["schema_version"]["const"]:
        findings.append(Finding("schema_version", "schema_version", "does not match checked-in schema"))
    for field in schema["required"]:
        if field not in document:
            findings.append(Finding("schema_required", field, "required by checked-in schema"))
    for field in document:
        if field not in schema["properties"]:
            findings.append(Finding("schema_property", field, "not allowed by checked-in schema"))
    return findings


def initial_examples() -> dict[str, dict[str, Any]]:
    """Return synthetic v0.1 fixtures for each owner-approved initial case."""
    import copy

    positive = load_example()
    zero = copy.deepcopy(positive)
    zero["run_id"] = "example-run-dagger-zero"
    zero["effects"] = []
    zero["instances"] = [zero["instances"][0]]
    zero["facts"] = [fact for fact in zero["facts"] if fact["id"] != "fact-victim-sell-value"]
    zero["evidence"] = [e for e in zero["evidence"] if e["id"] not in {"ev-victim-visible", "ev-victim-price", "ev-victim-removed"}]
    zero_fact = next(f for f in zero["facts"] if f["id"] == "fact-dagger-mult-after")
    zero_fact["value"] = 6
    zero_fact["rule_revision"] = "example-rule-dagger-scale-2"
    zero["facts"].append({
        "id": "fact-no-right-joker",
        "subject_id": "inst-dagger",
        "property": "right_neighbor_present",
        "value": False,
        "valid_from": "step-before",
        "status": "observed",
        "channel": "observation",
        "visibility": "visual",
        "evidence_ids": ["ev-dagger-visible"],
        "rule_revision": "video-annotation-v1",
        "confidence_basis": "ordered Joker row visibly has no card to Dagger's right",
    })

    ineligible = copy.deepcopy(positive)
    ineligible["run_id"] = "example-run-dagger-ineligible-right"
    ineligible["effects"] = []
    ineligible["instances"] = [ineligible["instances"][0]]
    ineligible["facts"] = [fact for fact in ineligible["facts"] if fact["id"] != "fact-victim-sell-value"]
    ineligible["evidence"] = [e for e in ineligible["evidence"] if e["id"] not in {"ev-victim-visible", "ev-victim-price", "ev-victim-removed"}]
    ineligible["facts"].append({
        "id": "fact-right-joker-ineligible",
        "subject_id": "inst-dagger",
        "property": "right_neighbor_destructible",
        "value": False,
        "valid_from": "step-before",
        "status": "observed",
        "channel": "observation",
        "visibility": "visual",
        "evidence_ids": ["ev-dagger-visible"],
        "rule_revision": "video-annotation-v1",
        "confidence_basis": "right-hand Joker is visibly present but not destructible",
    })

    missing = copy.deepcopy(positive)
    missing["run_id"] = "example-run-dagger-unknown"
    missing["effects"][0]["id"] = "effect-dagger-unknown-1"
    missing["effects"][0]["status"] = "unknown"
    missing["effects"][0]["condition"] = "unknown"
    missing["effects"][0]["contributions"] = []
    missing["effects"][0]["dependency_fact_ids"] = []
    missing["effects"][0]["target_ids"] = ["inst-victim"]
    missing["facts"] = [f for f in missing["facts"] if f["id"] != "fact-victim-sell-value"]
    missing["facts"] = [f for f in missing["facts"] if f["id"] != "fact-dagger-mult-after"]

    scoring = copy.deepcopy(positive)
    scoring["run_id"] = "example-run-scoring"
    scoring["definitions"] = [{"id": "def-base-joker", "family": "joker", "class_key": "j_joker", "revision": "source-inspected-class-map"}]
    scoring["instances"][0]["definition_id"] = "def-base-joker"
    scoring["instances"] = [scoring["instances"][0]]
    scoring["facts"] = []
    scoring["effects"][0].update({"id": "effect-scoring-1", "kind": "joker_scoring", "context": "scoring", "target_ids": [], "condition": "met"})
    scoring["effects"][0]["contributions"] = [{"kind": "mult", "value": 4, "unit": "mult", "occurrence_key": "effect-scoring-1:mult"}]
    scoring["effects"][0]["dependency_fact_ids"] = []
    scoring["effects"][0]["participation"] = [{"instance_id": "inst-dagger", "role": "joker-contributor", "contributed": True}]

    reset = copy.deepcopy(positive)
    reset["run_id"] = "example-run-reset"
    reset["effects"][0].update({"id": "effect-round-reset-1", "kind": "round_reset", "context": "reset", "target_ids": [], "condition": "met"})
    reset["effects"][0]["contributions"] = []
    reset["effects"][0]["dependency_fact_ids"] = []
    reset["effects"][0]["participation"] = []
    return {"dagger-positive": positive, "dagger-zero": zero, "dagger-ineligible-right": ineligible, "dagger-missing-dependency": missing, "scoring": scoring, "reset": reset}


def _record(**overrides: Any) -> dict[str, Any]:
    base: dict[str, Any] = {
        "id": "effect-1",
        "status": "inferred",
        "channel": "derived",
        "evidence": [{"id": "step-1", "channel": "observation"}],
        "known_ids": ["step-1", "oracle"],
        "references": ["step-1"],
        "purpose": "reconstruction",
        "uses_answer_key": False,
        "timing": {"ambiguous": False, "requires_exact_order": True, "order_evidence": "source-trace-1"},
    }
    base.update(overrides)
    return base


def _check_rejected(name: str, record: dict[str, Any], expected_code: str) -> None:
    findings = validate_envelope(record)
    if expected_code not in {finding.code for finding in findings}:
        raise ContractError(f"{name}: expected rejection {expected_code}; got {[f.code for f in findings]}")
    print(f"REJECT {name}: {expected_code}")


def main() -> int:
    valid = validate_envelope(_record())
    if valid:
        raise ContractError(f"valid fixture rejected: {valid}")
    print("ACCEPT valid inferred effect envelope")
    _check_rejected("malformed-reference", _record(references=["missing-id"]), "reference_missing")
    _check_rejected(
        "reference-mixed-into-reconstruction",
        _record(channel="derived", evidence=[{"id": "oracle", "channel": "reference"}]),
        "reference_channel_leak",
    )
    _check_rejected("answer-key-leak", _record(answer_key_refs=["oracle"]), "answer_key_leak")
    _check_rejected(
        "ambiguous-required-order",
        _record(timing={"ambiguous": True, "requires_exact_order": True, "order_evidence": None}),
        "timing_ambiguous",
    )
    _check_rejected("malformed-known-ids", _record(known_ids=None), "known_ids_type")
    _check_rejected("missing-reference-inventory", _record(references=None), "references_type")
    _check_rejected("missing-evidence", _record(evidence=None), "evidence_type")
    examples = initial_examples()
    example = examples["dagger-positive"]
    schema_findings = validate_schema_envelope(example)
    if schema_findings:
        raise ContractError(f"approved Dagger example violates schema envelope: {schema_findings}")
    for name, fixture in examples.items():
        schema_findings = validate_schema_envelope(fixture)
        if schema_findings:
            raise ContractError(f"approved {name} example violates schema envelope: {schema_findings}")
        fixture_findings = validate_document(fixture)
        if fixture_findings:
            raise ContractError(f"approved {name} example invalid: {fixture_findings}")
        print(f"ACCEPT mechanics-v0.1-{name}")
    bad_example = json.loads(json.dumps(example))
    bad_example["effects"][0]["source_instance_id"] = "missing-instance"
    bad_findings = validate_document(bad_example)
    if not any(f.code == "reference_missing" and f.path.endswith("source_instance_id") for f in bad_findings):
        raise ContractError("malformed concrete effect source reference was not rejected")
    print("REJECT concrete-effect-missing-instance: reference_missing")
    bad_answer_key = json.loads(json.dumps(example))
    bad_answer_key["answer_key_refs"] = ["oracle-answer"]
    if not any(f.code == "answer_key_leak" for f in validate_document(bad_answer_key)):
        raise ContractError("answer-key reference was not rejected in a mechanics document")
    print("REJECT concrete-document-answer-key: answer_key_leak")
    print("MECHANICS CONTRACT CHECKS OK (schema/reference envelope; no game-rule simulation)")
    return 0


if __name__ == "__main__":
    try:
        raise SystemExit(main())
    except ContractError as exc:
        print(f"FAIL: {exc}")
        raise SystemExit(1) from exc
