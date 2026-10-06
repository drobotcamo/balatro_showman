from __future__ import annotations

import copy
from dataclasses import replace

import pytest

from run_mechanics.dagger import (
    ExtraValueEvent,
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


def price(**overrides):
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
        "inflation": "observation",
        "edition_extra_costs": "source",
        "discount_percent": "observation",
        "rental": "observation",
        "extra_value": "derived",
    }
    field_evidence = tuple(
        (field, (f"{field}-evidence",)) for field in channels
    )
    evidence_catalog = tuple(
        (ids[0], channels[field]) for field, ids in field_evidence
    )
    return SellInputs(
        **values,
        source_stack=PINNED_STACK,
        source_hashes=tuple(PINNED_SOURCE_HASHES),
        input_channels=tuple(channels.items()),
        field_evidence=field_evidence,
        evidence_catalog=evidence_catalog,
    )


def opportunity(
    round_id, interval_id, order, before, eligible, sell_inputs=None,
    *, dagger_getting_sliced=False, victim_eternal=False, victim_getting_sliced=False, **extra
):
    evidence = (f"evidence-{interval_id}",)
    position_inputs = None
    if eligible is True:
        position_inputs = DaggerEligibilityInputs(
            "dagger", ("dagger", "victim"), dagger_getting_sliced, victim_eternal,
            victim_getting_sliced, evidence,
        )
    elif eligible is False:
        position_inputs = DaggerEligibilityInputs(
            "dagger", ("dagger",), False, None, None, evidence,
        )
    elif eligible is None:
        position_inputs = DaggerEligibilityInputs(
            "dagger", None, None, None, None, evidence,
        )
    return Sacrifice(
        "r", round_id, interval_id, order, "dagger", before, position_inputs,
        sell_inputs, evidence,
        mult_before_channel="observation" if before is not None else None,
        **extra,
    )


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
    assert construct_sell_value(unresolved).diagnostics == ("unresolved:evidence:base_cost",)


def test_egg_and_gift_card_reconstruct_persistent_extra_value():
    state = reconstruct_extra_value(
        "victim",
        0,
        [
            ExtraValueEvent(1, "egg", "other-egg", 3, ("other-egg",), ("e1",)),
            ExtraValueEvent(2, "gift_card", "gift", 1, ("victim", "gift"), ("e2",)),
            ExtraValueEvent(3, "egg", "victim", 3, ("victim",), ("e3",)),
        ],
        initial_channel="observation",
        initial_evidence_ids=("initial-value",),
    )
    assert (state.value, state.evidence_ids) == (4, ("initial-value", "e2", "e3"))
    ambiguous = reconstruct_extra_value(
        "victim", 0, [ExtraValueEvent(1, "gift_card", "gift", 1, None, ("e4",))],
        initial_channel="observation", initial_evidence_ids=("initial",),
    )
    assert ambiguous.value is None
    leaked = reconstruct_extra_value(
        "victim", 9, [], initial_channel="reference", initial_evidence_ids=("oracle",)
    )
    assert leaked.status == "unsupported"


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


def test_reference_channel_cannot_reestablish_dagger_baseline():
    event = opportunity(
        "1", "i1", 1, None, None, baseline_after=40,
        baseline_channel="reference",
    )
    with pytest.raises(ValueError, match="must be observed"):
        reduce_sacrifices([event])


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
    selected, excluded = select_winning_gold_stake_runs([
        {"run_id": "gold-win", "stake": "Gold Stake", "outcome": "won", "owner_confirmed": True, "evidence_id": "owner-note"},
        {"run_id": "white-win", "stake": "White", "outcome": "won", "owner_confirmed": True, "evidence_id": "owner-note"},
        {"run_id": "gold-loss", "stake": "Gold", "outcome": "lost", "owner_confirmed": True, "evidence_id": "owner-note"},
        {"run_id": "gold-unconfirmed", "stake": "Gold", "outcome": "won", "owner_confirmed": False, "evidence_id": ""},
    ])
    assert selected == {"gold-win"}
    assert len(excluded) == 3


def test_gold_stake_report_uses_one_consistent_population():
    gold = opportunity("1", "gold-i", 1, 0, True, price(base_cost=6))
    white = replace(opportunity("1", "white-i", 1, 0, True, price(base_cost=8)), run_id="white")
    events = [replace(gold, run_id="gold"), white]
    effects = reduce_sacrifices(events)
    report = round_growth_report(
        events,
        effects,
        eligible_gold_stake_runs=[{
            "run_id": "gold", "stake": "Gold", "outcome": "won",
            "owner_confirmed": True, "evidence_id": "owner-approval",
        }],
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
