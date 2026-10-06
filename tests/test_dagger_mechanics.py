from __future__ import annotations

import copy
from dataclasses import replace

import pytest

from run_mechanics.dagger import (
    ExtraValueEvent,
    EvidenceRecord,
    DaggerEligibilityInputs,
    PINNED_SOURCE_HASHES,
    PINNED_STACK,
    Sacrifice,
    SellInputs,
    compare_reference,
    construct_sell_value,
    reduce_sacrifices,
    reconstruct_extra_value,
    round_growth_report,
    select_winning_gold_stake_runs,
)


def price(*, evidence_prefix="synthetic", state_channel="observation", **overrides):
    values = {
        "base_cost": 8,
        "inflation": 0,
        "edition_extra_costs": (),
        "discount_percent": 0,
        "rental": False,
        "extra_value": 0,
    }
    values.update(overrides)
    channels = {
        "base_cost": "source",
        "inflation": state_channel,
        "edition_extra_costs": "source",
        "discount_percent": state_channel,
        "rental": state_channel,
        "extra_value": "derived",
    }
    field_evidence = tuple(
        (field, (f"{evidence_prefix}:{field}",)) for field in channels
    )
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


def opportunity(
    round_id, interval_id, order, before, eligible, sell_inputs=None,
    *, run_id="r", state_channel="observation", eligibility_channel="observation",
    dagger_getting_sliced=False, victim_eternal=False, victim_getting_sliced=False,
    mult_before_channel=None, **extra
):
    evidence = (f"{interval_id}:joker-row",)
    position_inputs = None
    if eligible is True:
        eligibility_values = {
            "ordered_joker_instance_ids": ("dagger", "victim"),
            "dagger_getting_sliced": dagger_getting_sliced,
            "right_victim_eternal": victim_eternal,
            "right_victim_getting_sliced": victim_getting_sliced,
        }
        field_evidence = tuple(
            (field, (f"{interval_id}:{field}",)) for field in eligibility_values
        )
        catalog = tuple(
            EvidenceRecord(ids[0], eligibility_channel, (field,))
            for field, ids in field_evidence
        )
        position_inputs = DaggerEligibilityInputs(
            "dagger", **eligibility_values, field_evidence=field_evidence,
            evidence_catalog=catalog,
        )
    elif eligible is False:
        field_evidence = (("ordered_joker_instance_ids", (f"{interval_id}:joker-row",)),)
        position_inputs = DaggerEligibilityInputs(
            "dagger", ("dagger",), None, None, None, field_evidence,
            (EvidenceRecord(field_evidence[0][1][0], eligibility_channel,
                            ("ordered_joker_instance_ids",)),),
        )
    elif eligible is None:
        position_inputs = DaggerEligibilityInputs(
            "dagger", None, None, None, None, (), (),
        )
    event_field_evidence = [
        ("run_id", (f"{run_id}:run",)),
        ("round_id", (f"{interval_id}:round",)),
        ("interval_id", (f"{interval_id}:interval",)),
        ("dagger_instance_id", (f"{interval_id}:dagger",)),
    ]
    if before is not None:
        event_field_evidence.append(("dagger_mult_before", (f"{interval_id}:mult-before",)))
    baseline_after = extra.get("baseline_after")
    if baseline_after is not None:
        event_field_evidence.append(("baseline_after", (f"{interval_id}:baseline-after",)))
    event_evidence_catalog = tuple(
        EvidenceRecord(
            ids[0],
            (
                extra.get("baseline_channel", "observation")
                if field == "baseline_after"
                else (mult_before_channel or state_channel)
                if field == "dagger_mult_before"
                else "derived"
            ),
            (field,),
        )
        for field, ids in event_field_evidence
    )
    event_evidence = tuple(ids[0] for _, ids in event_field_evidence)
    return Sacrifice(
        run_id, round_id, interval_id, order, "dagger", before, position_inputs,
        sell_inputs, event_evidence,
        field_evidence=tuple(event_field_evidence),
        evidence_catalog=event_evidence_catalog,
        mult_before_channel=mult_before_channel or (state_channel if before is not None else None),
        **extra,
    )


def value_event(order, kind, actor, increment, affected_ids, *, channel="observation"):
    fields = {
        "kind": (f"value-{order}:kind",),
        "actor_instance_id": (f"value-{order}:actor",),
        "increment": (f"value-{order}:increment",),
    }
    if kind == "gift_card" and affected_ids is not None:
        fields["affected_instance_ids"] = (f"value-{order}:targets",)
    catalog = tuple(
        EvidenceRecord(evidence_ids[0], channel, (field,))
        for field, evidence_ids in fields.items()
    )
    return ExtraValueEvent(order, kind, actor, increment, affected_ids, tuple(fields.items()), catalog)


def run_selection(run_id, stake, outcome, owner_confirmed):
    fields = tuple(
        (field, (f"{run_id}:{field}",))
        for field in ("stake", "outcome", "owner_confirmed")
    )
    records = tuple(EvidenceRecord(ids[0], "observation", (field,)) for field, ids in fields)
    return {
        "run_id": run_id,
        "stake": stake,
        "outcome": outcome,
        "owner_confirmed": owner_confirmed,
        "field_evidence": fields,
    }, records


def test_sell_value_follows_lua_order_rounding_and_modifiers():
    assert construct_sell_value(price()).value == 4
    # (base 8 + foil 2 + inflation 1 + .5) * 75%, floor = 8; sell = 4.
    discounted = construct_sell_value(price(
        inflation=1,
        edition_extra_costs=(2,),
        discount_percent=25,
    ))
    assert (discounted.current_cost, discounted.value) == (8, 4)
    assert construct_sell_value(price(rental=True, extra_value=3)).value == 4
    assert construct_sell_value(price(base_cost=1, discount_percent=50)).value == 1
    assert construct_sell_value(price(extra_value=3)).value == 7
    assert construct_sell_value(price(base_cost=5, extra_value=2)).value == 4
    # Photograph's base $5 plus the Holographic purchase surcharge $3 sells for $4.
    assert construct_sell_value(price(base_cost=5, edition_extra_costs=(3,))).value == 4
    # Dagger's base $6 plus the Negative surcharge $5 sells for $5.
    assert construct_sell_value(price(base_cost=6, edition_extra_costs=(5,))).value == 5
    assert construct_sell_value(price(base_cost=8, discount_percent=50)).value == 2
    assert construct_sell_value(price(base_cost=8, edition_extra_costs=(2, 3, 5))).value == 9


def test_missing_sell_dependency_stays_unknown():
    result = construct_sell_value(price(discount_percent=None))
    assert result.value is None
    assert result.status == "unknown"
    assert result.diagnostics == ("missing:discount_percent",)
    reference_sourced = replace(
        price(),
        input_channels=tuple(
            (key, "reference" if key == "extra_value" else channel)
            for key, channel in price().input_channels
        ),
    )
    assert construct_sell_value(reference_sourced).diagnostics == ("forbidden:reference_input",)
    unresolved = replace(
        price(),
        field_evidence=tuple((field, ("missing-id",)) if field == "base_cost" else (field, ids)
                             for field, ids in price().field_evidence),
    )
    assert construct_sell_value(unresolved).diagnostics == ("missing_or_invalid:field_evidence_links",)
    wrong_source = replace(price(), source_hashes=(("vanilla/game.lua", "bad-hash"),))
    assert construct_sell_value(wrong_source).diagnostics == ("missing_or_mismatched:source_hashes",)
    malformed_source = replace(price(), source_hashes=(([], "bad-hash"),))
    assert construct_sell_value(malformed_source).diagnostics == ("missing_or_mismatched:source_hashes",)
    channel_mismatch = replace(
        price(),
        input_channels=tuple(
            (field, "observation" if field == "inflation" else channel)
            for field, channel in price().input_channels
        ),
        evidence_catalog=tuple(
            replace(record, channel="derived")
            if "inflation" in record.supports else record
            for record in price().evidence_catalog
        ),
    )
    assert construct_sell_value(channel_mismatch).diagnostics == ("evidence_channel_mismatch",)


def test_egg_and_gift_card_reconstruct_persistent_extra_value():
    state = reconstruct_extra_value(
        "victim",
        0,
        [
            value_event(1, "egg", "other-egg", 3, ("other-egg",)),
            value_event(2, "gift_card", "gift", 1, ("victim", "gift")),
            value_event(3, "egg", "victim", 3, ("victim",)),
        ],
        initial_field_evidence=(("initial_extra_value", ("initial-value",)),),
        initial_evidence_catalog=(EvidenceRecord("initial-value", "observation", ("initial_extra_value",)),),
    )
    assert (state.value, state.evidence_ids) == (
        4,
        ("initial-value", "value-2:kind", "value-2:actor", "value-2:increment", "value-2:targets",
         "value-3:kind", "value-3:actor", "value-3:increment"),
    )
    ambiguous = reconstruct_extra_value(
        "victim", 0, [value_event(1, "gift_card", "gift", 1, None)],
        initial_field_evidence=(("initial_extra_value", ("initial",)),),
        initial_evidence_catalog=(EvidenceRecord("initial", "observation", ("initial_extra_value",)),),
    )
    assert ambiguous.value is None
    leaked = reconstruct_extra_value(
        "victim", 9, [],
        initial_field_evidence=(("initial_extra_value", ("oracle",)),),
        initial_evidence_catalog=(EvidenceRecord("oracle", "reference", ("initial_extra_value",)),),
    )
    assert leaked.status == "unsupported"
    leaked_event = value_event(1, "gift_card", "gift", 1, ("victim",), channel="reference")
    leaked_state = reconstruct_extra_value(
        "victim", 0, [leaked_event],
        initial_field_evidence=(("initial_extra_value", ("initial",)),),
        initial_evidence_catalog=(EvidenceRecord("initial", "source", ("initial_extra_value",)),),
    )
    assert leaked_state.status == "unsupported"
    unlinked = value_event(1, "gift_card", "gift", 1, ("victim",))
    unlinked = replace(unlinked, field_evidence=tuple(
        item for item in unlinked.field_evidence if item[0] != "affected_instance_ids"
    ))
    unlinked_state = reconstruct_extra_value(
        "victim", 0, [unlinked],
        initial_field_evidence=(("initial_extra_value", ("initial",)),),
        initial_evidence_catalog=(EvidenceRecord("initial", "source", ("initial_extra_value",)),),
    )
    assert unlinked_state.status == "unknown"
    malformed_event = reconstruct_extra_value(
        "victim", 0, [object()],
        initial_field_evidence=(("initial_extra_value", ("initial",)),),
        initial_evidence_catalog=(EvidenceRecord("initial", "source", ("initial_extra_value",)),),
    )
    assert malformed_event.status == "unsupported"
    invalid_collection = reconstruct_extra_value(
        "victim", 0, None,
        initial_field_evidence=(("initial_extra_value", ("initial",)),),
        initial_evidence_catalog=(EvidenceRecord("initial", "source", ("initial_extra_value",)),),
    )
    assert invalid_collection.status == "unsupported"


def test_unknown_growth_propagates_until_independent_baseline():
    inputs = price(base_cost=6)
    events = [
        opportunity("1", "i1", 1, 0, True, inputs),
        opportunity("2", "i2", 2, None, True, price(discount_percent=None)),
        opportunity("3", "i3", 3, 99, True, inputs),
        opportunity("4", "i4", 4, 99, False),
        opportunity("5", "i5", 5, None, None, baseline_after=20, baseline_channel="observation"),
        opportunity("6", "i6", 6, 20, False),
    ]
    effects = reduce_sacrifices(events)
    assert [e.mult_after for e in effects] == [6, None, None, None, 20, 20]
    assert effects[1].diagnostic[-1] == "invalidates:dagger_mult_and_future_growth"
    assert effects[3].growth == 0


def test_reference_channel_cannot_change_reconstruction():
    events = [opportunity("1", "i1", 1, 0, True, price(base_cost=6))]
    inferred = reduce_sacrifices(events)
    reference_a = [{"run_id": "r", "interval_id": "i1", "mult_after": 6, "victim_id": "oracle-a"}]
    reference_b = [{"run_id": "r", "interval_id": "i1", "mult_after": 999, "victim_id": "oracle-b"}]
    before = copy.deepcopy(inferred)
    assert reduce_sacrifices(events) == before
    assert compare_reference(inferred, reference_a)[0]["status"] == "match"
    assert compare_reference(inferred, reference_b)[0]["status"] == "mismatch"
    assert reduce_sacrifices(events) == before


def test_issue123_engine_steps_reconstruct_prices_and_match_separate_reference():
    """Engine-step fields drive the test; sidecar answers are compare-only."""
    run_id = "1662755302000-5667"
    events = [
        opportunity("1", "12", 12, 0, True,
                    price(base_cost=6, evidence_prefix="step12-castle", state_channel="derived"),
                    run_id=run_id, state_channel="derived", eligibility_channel="derived"),
        opportunity("2", "26", 26, 6, True,
                    price(base_cost=8, evidence_prefix="step26-burnt", state_channel="derived"),
                    run_id=run_id, state_channel="derived", eligibility_channel="derived"),
        opportunity("3", "36", 36, 14, True,
                    price(base_cost=5, edition_extra_costs=(3,), evidence_prefix="step36-holo", state_channel="derived"),
                    run_id=run_id, state_channel="derived", eligibility_channel="derived"),
    ]
    effects = reduce_sacrifices(events)
    refs = [
        {"run_id": run_id, "interval_id": "12", "mult_after": 6, "victim_sell_cost_pre": 3},
        {"run_id": run_id, "interval_id": "26", "mult_after": 14, "victim_sell_cost_pre": 4},
        {"run_id": run_id, "interval_id": "36", "mult_after": 22, "victim_sell_cost_pre": 4},
    ]
    assert [(e.victim_sell_value, e.growth, e.mult_after) for e in effects] == [
        (3, 6, 6), (4, 8, 14), (4, 8, 22)
    ]
    assert [e.mult_resolution for e in effects] == ["resolved"] * 3
    assert [e.victim_removal_status for e in effects] == ["pending"] * 3
    assert [row["status"] for row in compare_reference(effects, refs)] == ["match"] * 3
    # Perturbed answers can alter only the comparison results, not reducer output.
    assert reduce_sacrifices(events) == effects
    perturbed = [dict(ref, mult_after=-1, victim_sell_cost_pre=999) for ref in refs]
    assert [row["status"] for row in compare_reference(effects, perturbed)] == ["mismatch"] * 3
    assert reduce_sacrifices(events) == effects
    report = round_growth_report(events, effects)
    assert [row["growth"] for row in report["rounds"]] == [6, 8, 8]
    assert report["denominators"]["ownership_rounds"] == 3
    assert report["pooled_growth_per_sacrifice_with_known_value"] == pytest.approx(22 / 3)


def test_reference_channel_cannot_reestablish_dagger_baseline():
    event = opportunity(
        "1", "i1", 1, None, None, baseline_after=40,
        baseline_channel="reference",
    )
    with pytest.raises(ValueError, match="reference evidence"):
        reduce_sacrifices([event])


def test_eligibility_and_baseline_fields_require_linked_evidence():
    positive = opportunity("1", "i1", 1, 0, True, price(base_cost=6))
    bad_eligibility = replace(
        positive.eligibility_inputs,
        field_evidence=tuple(
            item for item in positive.eligibility_inputs.field_evidence
            if item[0] != "right_victim_eternal"
        ),
    )
    unknown = reduce_sacrifices([replace(positive, eligibility_inputs=bad_eligibility)])[0]
    assert unknown.growth is None
    assert "missing_or_invalid:field_evidence_links" in unknown.diagnostic

    baseline = opportunity(
        "1", "i1", 1, None, None, baseline_after=20, baseline_channel="observation"
    )
    baseline = replace(baseline, field_evidence=tuple(
        item for item in baseline.field_evidence if item[0] != "baseline_after"
    ))
    with pytest.raises(ValueError, match="evidence does not resolve"):
        reduce_sacrifices([baseline])


def test_rightmost_eternal_and_already_sliced_targets_are_known_zero():
    eternal = opportunity("1", "i1", 1, 0, True, victim_eternal=True)
    sliced = opportunity("2", "i2", 2, 0, True, victim_getting_sliced=True)
    dagger_sliced = opportunity("3", "i3", 3, 0, True, dagger_getting_sliced=True)
    rightmost = opportunity("4", "i4", 4, 0, False)
    effects = reduce_sacrifices([eternal, sliced, dagger_sliced, rightmost])
    assert [(e.growth, e.victim_instance_id) for e in effects] == [
        (0, "victim"), (0, "victim"), (0, "victim"), (0, None)
    ]


def test_analytics_include_zero_and_unknown_ownership_rounds():
    events = [
        opportunity("1", "i1", 1, 0, False),
        opportunity("2", "i2", 2, 0, True, price(base_cost=6)),
        opportunity("3", "i3", 3, 6, True, price(discount_percent=None)),
    ]
    effects = reduce_sacrifices(events)
    report = round_growth_report(events, effects)
    assert [row["growth"] for row in report["rounds"]] == [0, 6, None]
    assert report["denominators"] == {
        "ownership_rounds": 3,
        "sacrifices_confirmed": 2,
        "sacrifices_known_sell_value": 1,
        "sacrifices_unknown_sell_value": 1,
        "eligibility_unknown": 0,
        "ownership_rounds_known_growth": 2,
        "ownership_rounds_unknown_growth": 1,
        "runs_with_owned_rounds": 1,
    }
    assert report["pooled_growth_per_sacrifice_with_known_value"] == 6
    assert report["equal_run_weighted_growth_per_sacrifice_with_known_value"] == 6
    assert report["growth_graph"][-1]["status"] == "unknown"
    uncovered = round_growth_report(events, effects, ownership_rounds=[("r", "1"), ("r", "2"), ("r", "3"), ("r", "4")])
    assert uncovered["rounds"][-1]["growth"] is None
    assert uncovered["denominators"]["ownership_rounds_unknown_growth"] == 2


def test_gold_stake_winner_selection_requires_confirmation_and_evidence():
    metadata = [
        run_selection("gold-win", "Gold Stake", "won", True),
        run_selection("white-win", "White", "won", True),
        run_selection("gold-loss", "Gold", "lost", True),
        run_selection("gold-unconfirmed", "Gold", "won", False),
    ]
    rows = [item[0] for item in metadata]
    catalog = tuple(record for item in metadata for record in item[1])
    selected, excluded = select_winning_gold_stake_runs(rows, catalog)
    assert selected == {"gold-win"}
    assert len(excluded) == 3
    leaked_catalog = tuple(
        replace(record, channel="reference") if record.id == "gold-win:stake" else record
        for record in catalog
    )
    assert select_winning_gold_stake_runs([rows[0]], leaked_catalog)[0] == set()
    unreferenced_oracle = catalog + (EvidenceRecord("unused-oracle", "reference", ("oracle_field",)),)
    assert select_winning_gold_stake_runs([rows[0]], unreferenced_oracle)[0] == set()
    unlinked_row = {
        **rows[0],
        "field_evidence": (("stake", ("missing",)),) + rows[0]["field_evidence"][1:],
    }
    assert select_winning_gold_stake_runs([unlinked_row], catalog)[0] == set()


def test_gold_stake_report_uses_one_consistent_population():
    gold = opportunity("1", "gold-i", 1, 0, True, price(base_cost=6))
    white = replace(opportunity("1", "white-i", 1, 0, True, price(base_cost=8)), run_id="white")
    events = [replace(gold, run_id="gold"), white]
    effects = reduce_sacrifices(events)
    selected_metadata, selected_catalog = run_selection("gold", "Gold", "won", True)
    report = round_growth_report(
        events,
        effects,
        eligible_gold_stake_runs=[selected_metadata],
        gold_stake_evidence_catalog=selected_catalog,
    )
    assert report["selected_run_ids"] == ["gold"]
    assert [row["run_id"] for row in report["rounds"]] == ["gold"]
    assert report["pooled_growth_per_sacrifice_with_known_value"] == 6
    assert report["reportable_as_gold_stake_winners"] is True


def test_unselected_population_is_marked_nonreportable_gold_stake_data():
    event = opportunity("1", "i1", 1, 0, True, price(base_cost=6))
    report = round_growth_report([event], reduce_sacrifices([event]))
    assert report["population_status"] == "unverified_input_population"
    assert report["reportable_as_gold_stake_winners"] is False


def test_reject_duplicate_or_nonchronological_intervals():
    first = opportunity("1", "i1", 1, 0, False)
    with pytest.raises(ValueError, match="duplicate"):
        reduce_sacrifices([first, first])
    later = opportunity("2", "i2", 2, 0, False)
    earlier = opportunity("1", "i3", 1, 0, False)
    with pytest.raises(ValueError, match="chronological"):
        reduce_sacrifices([later, earlier])
