"""Evidence-bounded Dagger sell-value and growth reducer.

Engine-reference values are intentionally absent from these input types. They
can be compared with returned effects by a separate validation function.
"""

from __future__ import annotations

from dataclasses import asdict, dataclass
from statistics import fmean
from typing import Iterable

PINNED_STACK = "balatro-1.0.1o-FULL+lovely-0.10.0+steamodded-26.926.0~dev-a"
PINNED_SOURCE_HASHES = frozenset({
    "0d75fe164accf3312734d4b37ac98788dd15f0b8e4f9bb8b7f90c4e59de93f47",
    "5073d834e08119da9516f1795a8c3d93110669aeb409c29ad1b308e0eb0be453",
    "bbc67bd3fbadd1ea3f3f0aba07ef8596118d89ff1e9758718f9e17c07a96e912",
    "2ba1276c5850ea966733d4144602d866dddbb9cbfff1f588f409114d79584f54",
    "ade9f4a7f8b87ea64fe094445354a89710762950e8d9916d3354f779d8ba7666",
    "9b201d810eff0d79e22a1b505668f5c9f23255f5ca6e7d687802b81081db1690",
})


@dataclass(frozen=True)
class SellInputs:
    """Source-backed inputs at the sacrifice interval; None means unavailable."""

    base_cost: int | None
    inflation: int | None
    edition_extra_costs: tuple[int, ...] | None
    discount_percent: int | None
    rental: bool | None
    extra_value: int | None
    source_stack: str | None = None
    source_hashes: tuple[str, ...] = ()
    input_channels: tuple[tuple[str, str], ...] = ()
    field_evidence: tuple[tuple[str, tuple[str, ...]], ...] = ()
    evidence_catalog: tuple[tuple[str, str], ...] = ()


@dataclass(frozen=True)
class SellValue:
    value: int | None
    status: str
    diagnostics: tuple[str, ...]
    current_cost: int | None = None


@dataclass(frozen=True)
class ExtraValueEvent:
    order: int
    kind: str
    actor_instance_id: str
    increment: int | None
    affected_instance_ids: tuple[str, ...] | None
    evidence_ids: tuple[str, ...] = ()
    evidence_channel: str = "observation"


@dataclass(frozen=True)
class ExtraValueState:
    value: int | None
    status: str
    diagnostic: tuple[str, ...]
    evidence_ids: tuple[str, ...]


@dataclass(frozen=True)
class DaggerEligibilityInputs:
    dagger_instance_id: str
    ordered_joker_instance_ids: tuple[str, ...] | None
    dagger_getting_sliced: bool | None
    right_victim_eternal: bool | None
    right_victim_getting_sliced: bool | None
    evidence_ids: tuple[str, ...]
    evidence_channel: str = "observation"


@dataclass(frozen=True)
class DaggerEligibility:
    eligible: bool | None
    victim_instance_id: str | None
    diagnostic: tuple[str, ...]


def resolve_dagger_eligibility(inputs: DaggerEligibilityInputs) -> DaggerEligibility:
    """Apply the pinned immediate-right-neighbor Dagger condition."""
    if inputs.evidence_channel == "reference":
        return DaggerEligibility(None, None, ("forbidden:reference_eligibility",))
    if inputs.evidence_channel not in {"observation", "derived"} or not inputs.evidence_ids:
        return DaggerEligibility(None, None, ("missing:eligibility_provenance",))
    row = inputs.ordered_joker_instance_ids
    if row is None:
        return DaggerEligibility(None, None, ("missing:ordered_joker_row",))
    if any(value is not None and not isinstance(value, bool) for value in (
        inputs.dagger_getting_sliced,
        inputs.right_victim_eternal,
        inputs.right_victim_getting_sliced,
    )):
        return DaggerEligibility(None, None, ("invalid:eligibility_boolean",))
    if len(row) != len(set(row)) or row.count(inputs.dagger_instance_id) != 1:
        return DaggerEligibility(None, None, ("ambiguous:dagger_position",))
    index = row.index(inputs.dagger_instance_id)
    if index + 1 == len(row):
        return DaggerEligibility(False, None, ())
    victim_id = row[index + 1]
    if inputs.dagger_getting_sliced is True:
        return DaggerEligibility(False, victim_id, ())
    if inputs.dagger_getting_sliced is None:
        return DaggerEligibility(None, victim_id, ("missing:dagger_getting_sliced",))
    if inputs.right_victim_eternal is True or inputs.right_victim_getting_sliced is True:
        return DaggerEligibility(False, victim_id, ())
    if inputs.right_victim_eternal is None:
        return DaggerEligibility(None, victim_id, ("missing:victim_eternal",))
    if inputs.right_victim_getting_sliced is None:
        return DaggerEligibility(None, victim_id, ("missing:victim_getting_sliced",))
    return DaggerEligibility(True, victim_id, ())


def reconstruct_extra_value(
    instance_id: str,
    initial_value: int | None,
    events: Iterable[ExtraValueEvent],
    *,
    initial_channel: str,
    initial_evidence_ids: tuple[str, ...],
) -> ExtraValueState:
    """Apply Egg self-growth and Gift Card's all-owned-card increments."""
    if initial_value is None:
        return ExtraValueState(None, "unknown", ("missing:initial_extra_value",), initial_evidence_ids)
    if initial_channel == "reference":
        return ExtraValueState(None, "unsupported", ("forbidden:reference_initial_extra_value",), ())
    if initial_channel not in {"observation", "derived"} or not initial_evidence_ids:
        return ExtraValueState(None, "unknown", ("missing:initial_extra_value_provenance",), ())
    value: int | None = initial_value
    evidence: list[str] = list(initial_evidence_ids)
    previous_order = -1
    for event in events:
        if event.evidence_channel == "reference":
            raise ValueError("engine-reference evidence cannot update reconstructed extra_value")
        if event.evidence_channel not in {"observation", "derived"}:
            raise ValueError("extra_value event needs observation/derived evidence")
        if not event.evidence_ids:
            raise ValueError("extra_value event requires evidence references")
        if event.order <= previous_order:
            raise ValueError("extra-value events must be strictly chronological")
        previous_order = event.order
        if event.kind == "egg":
            applies = event.actor_instance_id == instance_id
        elif event.kind == "gift_card":
            if event.affected_instance_ids is None:
                if value is not None:
                    value = None
                evidence.extend(event.evidence_ids)
                continue
            applies = instance_id in event.affected_instance_ids
        else:
            raise ValueError(f"unsupported extra-value rule: {event.kind}")
        if applies:
            evidence.extend(event.evidence_ids)
            if value is None or event.increment is None:
                value = None
            else:
                value += event.increment
    if value is None:
        return ExtraValueState(
            None,
            "unknown",
            ("missing_or_ambiguous:Egg_or_Gift_Card_increment",),
            tuple(dict.fromkeys(evidence)),
        )
    return ExtraValueState(value, "inferred", (), tuple(dict.fromkeys(evidence)))


def construct_sell_value(inputs: SellInputs) -> SellValue:
    """Implement Card:set_cost / set_sell_value for an already-owned card.

    Couponed shop pricing and booster/tutorial special cases are excluded: this
    is a Joker victim's owned-card sell value. All required inputs are explicit.
    """
    missing = tuple(
        key
        for key, value in (
            ("base_cost", inputs.base_cost),
            ("inflation", inputs.inflation),
            ("edition_extra_costs", inputs.edition_extra_costs),
            ("discount_percent", inputs.discount_percent),
            ("rental", inputs.rental),
            ("extra_value", inputs.extra_value),
        )
        if value is None
    )
    if missing:
        return SellValue(None, "unknown", tuple(f"missing:{key}" for key in missing))
    if inputs.source_stack is None:
        return SellValue(None, "unknown", ("missing:source_stack",))
    if inputs.source_stack != PINNED_STACK:
        return SellValue(None, "unsupported", ("unsupported:source_stack",))
    if len(set(inputs.source_hashes)) != len(inputs.source_hashes) or set(inputs.source_hashes) != PINNED_SOURCE_HASHES:
        return SellValue(None, "unknown", ("missing_or_mismatched:source_hashes",))
    channels = dict(inputs.input_channels)
    required_channels = {
        "base_cost", "inflation", "edition_extra_costs", "discount_percent",
        "rental", "extra_value",
    }
    if len(channels) != len(inputs.input_channels) or set(channels) != required_channels:
        return SellValue(None, "unknown", ("missing:input_channel_provenance",))
    if any(channel == "reference" for channel in channels.values()):
        return SellValue(None, "unsupported", ("forbidden:reference_input",))
    if any(channel not in {"source", "observation", "derived"} for channel in channels.values()):
        return SellValue(None, "unsupported", ("invalid:input_channel",))
    allowed_channels = {
        "base_cost": {"source"},
        "inflation": {"observation", "derived"},
        "edition_extra_costs": {"source"},
        "discount_percent": {"observation", "derived"},
        "rental": {"observation", "derived"},
        "extra_value": {"observation", "derived"},
    }
    if any(channels[key] not in allowed for key, allowed in allowed_channels.items()):
        return SellValue(None, "unsupported", ("invalid:field_provenance",))
    field_evidence = dict(inputs.field_evidence)
    catalog = dict(inputs.evidence_catalog)
    if (
        len(field_evidence) != len(inputs.field_evidence)
        or set(field_evidence) != required_channels
        or len(catalog) != len(inputs.evidence_catalog)
        or not catalog
    ):
        return SellValue(None, "unknown", ("missing:input_evidence_catalog",))
    expected_evidence_channel = {
        "source": "source",
        "observation": "observation",
        "derived": "derived",
    }
    referenced_ids: set[str] = set()
    for field_name, evidence_ids in field_evidence.items():
        if not evidence_ids:
            return SellValue(None, "unknown", (f"missing:evidence:{field_name}",))
        if any(evidence_id not in catalog for evidence_id in evidence_ids):
            return SellValue(None, "unknown", (f"unresolved:evidence:{field_name}",))
        if any(catalog[evidence_id] == "reference" for evidence_id in evidence_ids):
            return SellValue(None, "unsupported", (f"forbidden:reference_evidence:{field_name}",))
        if not any(
            catalog[evidence_id] == expected_evidence_channel[channels[field_name]]
            for evidence_id in evidence_ids
        ):
            return SellValue(None, "unknown", (f"channel_mismatch:evidence:{field_name}",))
        referenced_ids.update(evidence_ids)
    if referenced_ids != set(catalog):
        return SellValue(None, "unsupported", ("unreferenced:evidence_catalog_entries",))
    values = (inputs.base_cost, inputs.inflation, inputs.discount_percent, inputs.extra_value)
    if any(not isinstance(value, int) or isinstance(value, bool) for value in values):
        return SellValue(None, "unsupported", ("non_integer_cost_input",))
    if not isinstance(inputs.rental, bool):
        return SellValue(None, "unsupported", ("rental_not_boolean",))
    if not isinstance(inputs.edition_extra_costs, tuple) or any(
        not isinstance(value, int) or isinstance(value, bool)
        for value in inputs.edition_extra_costs
    ):
        return SellValue(None, "unsupported", ("invalid_edition_extra_costs",))
    assert inputs.base_cost is not None
    assert inputs.inflation is not None
    assert inputs.discount_percent is not None
    assert inputs.extra_value is not None
    if not 0 <= inputs.discount_percent <= 100:
        return SellValue(None, "unsupported", ("discount_percent_out_of_range",))

    if inputs.base_cost < 0 or inputs.inflation < 0 or inputs.extra_value < 0:
        return SellValue(None, "unsupported", ("negative_cost_or_extra_value",))
    if any(value < 0 for value in inputs.edition_extra_costs):
        return SellValue(None, "unsupported", ("negative_edition_surcharge",))
    # Card:set_ability stores center.cost or 1, so a zero-valued center uses 1.
    base_cost = inputs.base_cost or 1
    undiscounted_cost = base_cost + inputs.inflation + sum(inputs.edition_extra_costs)
    # Lua math.floor((x + 0.5) * percent / 100), using exact integer math.
    current_cost = max(
        1,
        ((undiscounted_cost * 2 + 1) * (100 - inputs.discount_percent)) // 200,
    )
    if inputs.rental:
        current_cost = 1
    sell_value = max(1, current_cost // 2) + inputs.extra_value
    return SellValue(sell_value, "inferred", (), current_cost)


@dataclass(frozen=True)
class Sacrifice:
    run_id: str
    round_id: str
    interval_id: str
    order: int
    dagger_instance_id: str
    dagger_mult_before: int | None
    eligibility_inputs: DaggerEligibilityInputs | None
    sell_inputs: SellInputs | None = None
    evidence_ids: tuple[str, ...] = ()
    rule_revision: str = "balatro-1.0.1o-lovely-0.10.0-smods-26.926.0-dev-a:dagger-sell-v1"
    baseline_after: int | None = None
    mult_before_channel: str | None = None
    baseline_channel: str | None = None


@dataclass(frozen=True)
class DaggerEffect:
    run_id: str
    round_id: str
    interval_id: str
    dagger_instance_id: str
    victim_instance_id: str | None
    condition: str
    status: str
    opportunity: bool
    confirmed_sacrifice: bool | None
    victim_sell_value: int | None
    growth: int | None
    mult_before: int | None
    mult_after: int | None
    diagnostic: tuple[str, ...]
    evidence_ids: tuple[str, ...]
    rule_revision: str


def reduce_sacrifices(events: Iterable[Sacrifice]) -> list[DaggerEffect]:
    """Reduce chronological Dagger opportunities, propagating unknown Mult."""
    effects: list[DaggerEffect] = []
    current_by_instance: dict[tuple[str, str], int | None] = {}
    seen_intervals: set[tuple[str, str]] = set()
    last_order: dict[str, int] = {}
    for event in events:
        key = (event.run_id, event.interval_id)
        if key in seen_intervals:
            raise ValueError(f"duplicate Dagger interval: {key}")
        seen_intervals.add(key)
        if not isinstance(event.order, int) or isinstance(event.order, bool):
            raise ValueError(f"event order must be an integer: {key}")
        if not event.evidence_ids:
            raise ValueError(f"Dagger interval requires evidence references: {key}")
        previous = last_order.get(event.run_id)
        if previous is not None and event.order <= previous:
            raise ValueError(f"events are not globally chronological for {event.run_id}")
        last_order[event.run_id] = event.order

        instance_key = (event.run_id, event.dagger_instance_id)
        has_prior_state = instance_key in current_by_instance
        before = current_by_instance[instance_key] if has_prior_state else event.dagger_mult_before
        if before is not None and not has_prior_state and event.mult_before_channel not in {"observation", "derived"}:
            raise ValueError(f"Dagger baseline must be observation/derived, never reference: {key}")
        if event.baseline_after is not None:
            if event.baseline_channel != "observation":
                raise ValueError(f"Dagger baseline re-establishment must be observed: {key}")
            current_by_instance[instance_key] = event.baseline_after
            effects.append(DaggerEffect(
                event.run_id, event.round_id, event.interval_id, event.dagger_instance_id,
                condition="baseline_reestablished",
                status="observed",
                victim_instance_id=None,
                opportunity=False,
                confirmed_sacrifice=False,
                victim_sell_value=None,
                growth=None,
                mult_before=before,
                mult_after=event.baseline_after,
                diagnostic=(),
                evidence_ids=event.evidence_ids,
                rule_revision=event.rule_revision,
            ))
            continue
        eligibility = (
            resolve_dagger_eligibility(event.eligibility_inputs)
            if event.eligibility_inputs is not None
            else DaggerEligibility(None, None, ("missing:eligibility_inputs",))
        )
        if "forbidden:reference_eligibility" in eligibility.diagnostic:
            raise ValueError(f"eligibility cannot use reference evidence: {key}")
        if eligibility.eligible is False:
            after = before
            status, condition, confirmed, growth, victim_value, diagnostic = "inferred", "not_met", False, 0, None, ()
        elif eligibility.eligible is None:
            after = None
            status, condition, confirmed, growth, victim_value = "unknown", "unknown", None, None
            diagnostic = eligibility.diagnostic + ("invalidates:dagger_mult_and_future_growth",)
        elif before is None:
            after = None
            status, condition, confirmed, growth, victim_value = "unknown", "unknown", True, None, None
            diagnostic = ("missing:dagger_mult_before", "invalidates:dagger_mult_and_future_growth")
        elif event.sell_inputs is None:
            after = None
            status, condition, confirmed, growth, victim_value = "unknown", "unknown", True, None, None
            diagnostic = ("missing:sell_value_inputs", "invalidates:dagger_mult_and_future_growth")
        else:
            sell = construct_sell_value(event.sell_inputs)
            if sell.value is None:
                after = None
                status, condition, confirmed, growth, victim_value = sell.status, "unknown", True, None, None
                diagnostic = sell.diagnostics + ("invalidates:dagger_mult_and_future_growth",)
            else:
                victim_value = sell.value
                growth = 2 * victim_value
                after = before + growth
                status, condition, confirmed, diagnostic = "inferred", "met", True, ()
        current_by_instance[instance_key] = after
        input_evidence = tuple(
            evidence_id
            for _, evidence_ids in (event.sell_inputs.field_evidence if event.sell_inputs else ())
            for evidence_id in evidence_ids
        )
        eligibility_evidence = (
            event.eligibility_inputs.evidence_ids if event.eligibility_inputs else ()
        )
        effects.append(DaggerEffect(
            event.run_id, event.round_id, event.interval_id, event.dagger_instance_id,
            eligibility.victim_instance_id, condition, status, True, confirmed,
            victim_value, growth, before, after, diagnostic,
            tuple(dict.fromkeys(event.evidence_ids + eligibility_evidence + input_evidence)),
            event.rule_revision,
        ))
    return effects


def compare_reference(effects: Iterable[DaggerEffect], references: Iterable[dict]) -> list[dict]:
    """Compare independently; reference records never enter reducer inputs."""
    by_interval = {(e.run_id, e.interval_id): e for e in effects}
    comparisons = []
    for ref in references:
        key = (ref["run_id"], ref["interval_id"])
        effect = by_interval.get(key)
        ref_value = ref.get("mult_after")
        comparisons.append({
            "run_id": key[0],
            "interval_id": key[1],
            "status": "not_comparable" if effect is None or effect.mult_after is None or ref_value is None else (
                "match" if effect.mult_after == ref_value else "mismatch"
            ),
            "derived_mult_after": effect.mult_after if effect else None,
            "reference_mult_after": ref.get("mult_after"),
        })
    return comparisons


def select_winning_gold_stake_runs(run_metadata: Iterable[dict]) -> tuple[set[str], list[dict]]:
    """Select only explicitly owner-confirmed Gold Stake wins with evidence."""
    selected: set[str] = set()
    excluded: list[dict] = []
    for row in run_metadata:
        run_id = row.get("run_id")
        reasons = []
        if not isinstance(run_id, str) or not run_id:
            reasons.append("missing_run_id")
        if row.get("owner_confirmed") is not True:
            reasons.append("stake_not_owner_confirmed")
        if row.get("stake") not in {"Gold", "Gold Stake", 8}:
            reasons.append("not_gold_stake")
        if row.get("outcome") not in {"won", "win"}:
            reasons.append("not_a_win")
        if not isinstance(row.get("evidence_id"), str) or not row["evidence_id"]:
            reasons.append("missing_selection_evidence")
        if reasons:
            excluded.append({"run_id": run_id, "reasons": reasons})
        else:
            selected.add(run_id)
    return selected, excluded


def round_growth_report(
    events: Iterable[Sacrifice],
    effects: Iterable[DaggerEffect],
    ownership_rounds: Iterable[tuple[str, str]] | None = None,
    eligible_gold_stake_runs: Iterable[dict] | None = None,
) -> dict:
    """Report known-zero ownership rounds, unknown rounds, and both weightings."""
    event_rows = list(events)
    effect_rows = list(effects)
    grouped: dict[tuple[str, str], list[DaggerEffect]] = {}
    all_owned_rounds = (
        set(ownership_rounds)
        if ownership_rounds is not None
        else {(e.run_id, e.round_id) for e in event_rows}
    )
    selection_excluded: list[dict] = []
    if eligible_gold_stake_runs is None:
        selected_runs = {run_id for run_id, _ in all_owned_rounds}
        population_status = "unverified_input_population"
    else:
        selected_runs, selection_excluded = select_winning_gold_stake_runs(eligible_gold_stake_runs)
        population_status = "owner_confirmed_gold_stake_wins"
    owned_rounds = {(run_id, round_id) for run_id, round_id in all_owned_rounds if run_id in selected_runs}
    selected_effects = [effect for effect in effect_rows if effect.run_id in selected_runs]
    for effect in selected_effects:
        grouped.setdefault((effect.run_id, effect.round_id), []).append(effect)
    rounds = []
    for run_id, round_id in sorted(owned_rounds):
        rows = grouped.get((run_id, round_id), [])
        opportunities = [e for e in rows if e.opportunity]
        known_growth = sum(e.growth for e in opportunities if e.growth is not None)
        unknown_count = sum(e.growth is None for e in opportunities)
        if not opportunities:
            unknown_count = 1
        rounds.append({
            "run_id": run_id,
            "round_id": round_id,
            "ownership_round": True,
            "growth": None if unknown_count else known_growth,
            "status": "unknown" if unknown_count else "known",
            "sacrifice_count": sum(e.confirmed_sacrifice is True for e in opportunities),
            "known_sacrifice_count": sum(e.condition == "met" and e.growth is not None for e in opportunities),
            "unknown_sacrifice_count": sum(e.confirmed_sacrifice is True and e.growth is None for e in opportunities),
            "opportunity_coverage": "unknown" if not opportunities else "observed",
        })

    per_run_means: dict[str, float] = {}
    per_run_round_means: dict[str, float] = {}
    for run_id in sorted({run_id for run_id, _ in owned_rounds}):
        known = [r for r in rounds if r["run_id"] == run_id and r["status"] == "known"]
        sacrifice_n = sum(r["known_sacrifice_count"] for r in known)
        growth_sum = sum(r["growth"] for r in known)
        if sacrifice_n:
            per_run_means[run_id] = growth_sum / sacrifice_n
        if known:
            per_run_round_means[run_id] = sum(r["growth"] for r in known) / len(known)
    opportunities = [e for e in selected_effects if e.opportunity]
    known_growth = sum(e.growth for e in opportunities if e.growth is not None)
    known_sacrifices = sum(e.condition == "met" and e.growth is not None for e in opportunities)
    return {
        "rounds": rounds,
        "growth_graph": [
            {"run_id": r["run_id"], "round_id": r["round_id"], "growth": r["growth"], "status": r["status"]}
            for r in rounds
        ],
        "denominators": {
            "ownership_rounds": len(owned_rounds),
            "sacrifices_confirmed": sum(e.confirmed_sacrifice is True for e in opportunities),
            "sacrifices_known_sell_value": known_sacrifices,
            "sacrifices_unknown_sell_value": sum(
                e.confirmed_sacrifice is True and e.growth is None for e in opportunities
            ),
            "eligibility_unknown": sum(e.confirmed_sacrifice is None for e in opportunities),
            "ownership_rounds_known_growth": sum(r["status"] == "known" for r in rounds),
            "ownership_rounds_unknown_growth": sum(r["status"] == "unknown" for r in rounds),
            "runs_with_owned_rounds": len({run_id for run_id, _ in owned_rounds}),
        },
        "pooled_growth_per_sacrifice_with_known_value": known_growth / known_sacrifices if known_sacrifices else None,
        "equal_run_weighted_growth_per_sacrifice_with_known_value": fmean(per_run_means.values()) if per_run_means else None,
        "per_run_growth_per_known_sacrifice": per_run_means,
        "runs_with_known_sacrifice_mean": len(per_run_means),
        "pooled_growth_per_known_ownership_round": (
            sum(r["growth"] for r in rounds if r["status"] == "known")
            / sum(r["status"] == "known" for r in rounds)
            if any(r["status"] == "known" for r in rounds) else None
        ),
        "equal_run_weighted_growth_per_known_ownership_round": (
            fmean(per_run_round_means.values()) if per_run_round_means else None
        ),
        "per_run_growth_per_known_ownership_round": per_run_round_means,
        "runs_with_known_ownership_round_mean": len(per_run_round_means),
        "population_status": population_status,
        "reportable_as_gold_stake_winners": eligible_gold_stake_runs is not None,
        "selected_run_ids": sorted(selected_runs),
        "excluded_run_selections": selection_excluded,
    }


def report_json(events: Iterable[Sacrifice], effects: Iterable[DaggerEffect]) -> dict:
    """JSON-ready report records for reproducible graph/coverage artifacts."""
    event_rows, effect_rows = list(events), list(effects)
    return {
        "effects": [asdict(effect) for effect in effect_rows],
        "analytics": round_growth_report(event_rows, effect_rows),
    }
