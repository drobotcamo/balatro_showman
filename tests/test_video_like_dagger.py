from __future__ import annotations

import copy
import json
from dataclasses import asdict, replace
from pathlib import Path

import pytest

from run_mechanics.dagger import EvidenceRecord, PINNED_SOURCE_HASHES, PINNED_STACK, SellInputs, reduce_sacrifices
from run_mechanics.video_like import adapt_video_like_record, run_video_like_record, run_video_like_records


DATASET = Path(__file__).parent / "fixtures" / "video_like" / "dagger_v1.json"


@pytest.fixture(scope="module")
def cases():
    payload = json.loads(DATASET.read_text(encoding="utf-8"))
    assert payload["dataset_status"] == "synthetic_video_like_not_actual_video"
    return {row["case_id"]: row for row in payload["cases"]}


def test_tooltip_observation_reaches_same_dagger_reducer(cases):
    result = run_video_like_record(cases["tooltip_observed_positive"])
    effect = result["effect"]
    assert result["status"] == "consistent"
    assert (effect.mult_before, effect.growth, effect.mult_after) == (6, 8, 14)
    assert effect.victim_sell_value == 4
    assert effect.victim_instance_id == "track-victim-a"
    assert effect.victim_removal_status == "pending"
    assert result["observed_mult_delta"] == 8
    assert "positive-1:visual:observed_victim_sell_value" in effect.evidence_ids


@pytest.mark.parametrize(
    ("case_id", "diagnostic", "status"),
    [
        ("tooltip_missing", "missing:sell_value_inputs", "unknown"),
        ("action_missing", "missing:eligibility_inputs", "unknown"),
        ("identity_ambiguous", "missing:eligibility_inputs", "ambiguous"),
        ("timing_ambiguous", "missing:eligibility_inputs", "ambiguous"),
    ],
)
def test_missing_or_ambiguous_video_observations_abstain(cases, case_id, diagnostic, status):
    result = run_video_like_record(cases[case_id])
    assert result["status"] == status
    assert result["effect"].mult_after is None
    assert result["effect"].status == status
    assert diagnostic in result["diagnostics"]
    assert result["effect"].interval_id == cases[case_id]["observation"]["interval_id"]


def test_contradictory_visible_aftermath_invalidates_exact_result(cases):
    result = run_video_like_record(cases["contradictory_aftermath"])
    assert result["status"] == "ambiguous"
    assert result["effect"].status == "ambiguous"
    assert result["effect"].mult_after is None
    assert result["effect"].growth is None
    assert "contradictory:visible_post_mult" in result["diagnostics"]
    assert result["effect"].interval_id == "contradictory-1"
    assert result["observed_mult_delta"] == 7


def test_reference_answers_ids_and_fields_do_not_change_video_inference(cases):
    base = cases["tooltip_observed_positive"]
    variants = [copy.deepcopy(base) for _ in range(3)]
    variants[0]["engine_reference"] = {"answer": 14, "engine_id": 123, "victim_sell": 4}
    variants[1]["engine_reference"] = {"answer": -900, "engine_id": "poison", "victim_sell": None}
    # The comparison/reference side channel may be absent altogether.
    variants[2].pop("engine_reference", None)
    outcomes = [run_video_like_record(row) for row in variants]
    assert [asdict(row["effect"]) for row in outcomes] == [asdict(outcomes[0]["effect"])] * 3
    assert [row["status"] for row in outcomes] == ["consistent"] * 3


@pytest.mark.parametrize(
    "mutation",
    [
        lambda row: row["observation"].update(engine_id="privileged"),
        lambda row: row.update(engine_answer={"mult_after": 14}),
    ],
)
def test_reference_only_fields_inside_input_projection_are_rejected(cases, mutation):
    row = copy.deepcopy(cases["tooltip_observed_positive"])
    mutation(row)
    with pytest.raises(ValueError, match="unsupported|reference-only"):
        run_video_like_record(row)


def test_visual_timing_order_does_not_claim_verified_frame_alignment(cases):
    result = run_video_like_record(cases["tooltip_observed_positive"])
    assert result["status"] == "consistent"
    # This is an ordered synthetic interval, not a measured video/oracle match.
    assert cases["tooltip_observed_positive"]["observation"]["timing_status"] == "ordered_visual_sequence"


def test_invalid_tooltip_value_is_rejected(cases):
    row = copy.deepcopy(cases["tooltip_observed_positive"])
    row["observation"]["victim_sell_value_tooltip"] = 0
    with pytest.raises(ValueError, match="positive sell value"):
        run_video_like_record(row)


def _source_pricing_inputs(base_cost: int) -> SellInputs:
    values = {
        "base_cost": base_cost,
        "inflation": 0,
        "edition_extra_costs": (),
        "discount_percent": 0,
        "rental": False,
        "extra_value": 0,
    }
    channels = {
        "base_cost": "source",
        "inflation": "observation",
        "edition_extra_costs": "source",
        "discount_percent": "observation",
        "rental": "observation",
        "extra_value": "derived",
    }
    field_evidence = tuple((field, (f"price:{field}",)) for field in channels)
    evidence_catalog = tuple(
        EvidenceRecord(ids[0], channels[field], (field,)) for field, ids in field_evidence
    )
    return SellInputs(
        **values,
        source_stack=PINNED_STACK,
        source_hashes=tuple(PINNED_SOURCE_HASHES.items()),
        input_channels=tuple(channels.items()),
        field_evidence=field_evidence,
        evidence_catalog=evidence_catalog,
    )


def test_visible_tooltip_cross_checks_complete_source_price_or_stands_alone(cases):
    adapted = adapt_video_like_record(cases["tooltip_observed_positive"])
    matching = replace(adapted.event, sell_inputs=_source_pricing_inputs(8))
    mismatch = replace(adapted.event, sell_inputs=_source_pricing_inputs(10))
    match_effect = reduce_sacrifices((matching,))[0]
    mismatch_effect = reduce_sacrifices((mismatch,))[0]
    assert (match_effect.victim_sell_value, match_effect.mult_after) == (4, 14)
    assert mismatch_effect.status == "ambiguous"
    assert mismatch_effect.mult_after is None
    assert "contradictory:observed_and_derived_sell_value" in mismatch_effect.diagnostic


def test_missing_price_keeps_effect_unknown_but_observed_post_state_reestablishes_baseline(cases):
    missing_price = copy.deepcopy(cases["tooltip_missing"])
    missing_price["observation"].update(
        run_id="sequence-run",
        interval_id="sequence-1",
        order=1,
        dagger_track_id="track-dagger-sequence",
        mult_before=0,
        ordered_joker_tracks=["track-dagger-sequence", "track-victim-1"],
        victim_sell_value_tooltip=None,
        post_mult=6,
    )
    observed_price = copy.deepcopy(cases["tooltip_observed_positive"])
    observed_price["observation"].update(
        run_id="sequence-run",
        interval_id="sequence-2",
        order=2,
        dagger_track_id="track-dagger-sequence",
        mult_before=6,
        ordered_joker_tracks=["track-dagger-sequence", "track-victim-2"],
        post_mult=14,
    )
    first, second = run_video_like_records([missing_price, observed_price])
    assert first["effect"].status == "unknown"
    assert first["effect"].mult_after is None
    assert first["observed_mult_delta"] == 6
    assert second["effect"].mult_before == 6
    assert second["effect"].mult_after == 14
    assert second["observed_mult_delta"] == 8


def test_unobserved_post_state_does_not_turn_missing_growth_into_zero(cases):
    first = copy.deepcopy(cases["tooltip_missing"])
    first["observation"].update(
        run_id="unknown-sequence",
        interval_id="unknown-1",
        order=1,
        dagger_track_id="track-unknown",
        mult_before=0,
        ordered_joker_tracks=["track-unknown", "victim-1"],
        post_mult=None,
        victim_absent_after=None,
    )
    second = copy.deepcopy(cases["tooltip_observed_positive"])
    second["observation"].update(
        run_id="unknown-sequence",
        interval_id="unknown-2",
        order=2,
        dagger_track_id="track-unknown",
        mult_before=6,
        ordered_joker_tracks=["track-unknown", "victim-2"],
    )
    effects = run_video_like_records([first, second])
    assert all(row["effect"].mult_after is None for row in effects)
    assert "missing:dagger_mult_before" in effects[1]["diagnostics"]
