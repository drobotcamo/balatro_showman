"""Evidence-bounded Dagger sell-value and growth reducer.

Engine-reference values are intentionally absent from these input types. They
can be compared with returned effects by a separate validation function.
"""

from __future__ import annotations

from dataclasses import asdict, dataclass
from statistics import fmean
from typing import Iterable

PINNED_STACK = "balatro-1.0.1o-FULL+lovely-0.10.0+steamodded-26.926.0~dev-a"
PINNED_SOURCE_HASHES = {
    "Balatro.exe": "0d75fe164accf3312734d4b37ac98788dd15f0b8e4f9bb8b7f90c4e59de93f47",
    "vanilla/card.lua": "5073d834e08119da9516f1795a8c3d93110669aeb409c29ad1b308e0eb0be453",
    "vanilla/game.lua": "bbc67bd3fbadd1ea3f3f0aba07ef8596118d89ff1e9758718f9e17c07a96e912",
    "lovely/dump/card.lua": "2ba1276c5850ea966733d4144602d866dddbb9cbfff1f588f409114d79584f54",
    "smods-main/lovely/scaling.toml": "ade9f4a7f8b87ea64fe094445354a89710762950e8d9916d3354f779d8ba7666",
    "smods-main/src/game_object.lua": "9b201d810eff0d79e22a1b505668f5c9f23255f5ca6e7d687802b81081db1690",
}


@dataclass(frozen=True)
class EvidenceRecord:
    id: str
    channel: str
    supports: tuple[str, ...]


def _evidence_map(records: tuple[EvidenceRecord, ...]) -> dict[str, EvidenceRecord] | None:
    if not isinstance(records, tuple):
        return None
    mapped: dict[str, EvidenceRecord] = {}
    for record in records:
        if (
            not isinstance(record, EvidenceRecord)
            or not isinstance(record.id, str)
            or not record.id
            or not isinstance(record.channel, str)
            or record.channel not in {"source", "observation", "derived", "reference"}
            or not isinstance(record.supports, tuple)
            or not record.supports
            or any(not isinstance(field, str) or not field for field in record.supports)
            or record.id in mapped
        ):
            return None
        mapped[record.id] = record
    return mapped


def _field_evidence_valid(
    field_evidence: tuple[tuple[str, tuple[str, ...]], ...],
    catalog: dict[str, EvidenceRecord],
    expected_fields: set[str],
    allowed_channels: dict[str, set[str]],
) -> bool:
    if not isinstance(field_evidence, tuple):
        return False
    if any(
        not isinstance(pair, tuple)
        or len(pair) != 2
        or not isinstance(pair[0], str)
        or not pair[0]
        for pair in field_evidence
    ):
        return False
    refs = dict(field_evidence)
    if len(refs) != len(field_evidence) or set(refs) != expected_fields:
        return False
    referenced: set[str] = set()
    for field, ids in refs.items():
        if not isinstance(ids, tuple) or not ids or any(not isinstance(item, str) or not item for item in ids):
            return False
        for evidence_id in ids:
            record = catalog.get(evidence_id)
            if record is None or field not in record.supports or record.channel not in allowed_channels[field]:
                return False
            referenced.add(evidence_id)
    return referenced == set(catalog)


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
    source_hashes: tuple[tuple[str, str], ...] = ()
    input_channels: tuple[tuple[str, str], ...] = ()
    field_evidence: tuple[tuple[str, tuple[str, ...]], ...] = ()
    evidence_catalog: tuple[EvidenceRecord, ...] = ()


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
    field_evidence: tuple[tuple[str, tuple[str, ...]], ...]
    evidence_catalog: tuple[EvidenceRecord, ...]


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
    field_evidence: tuple[tuple[str, tuple[str, ...]], ...]
    evidence_catalog: tuple[EvidenceRecord, ...]


@dataclass(frozen=True)
class DaggerEligibility:
    eligible: bool | None
    victim_instance_id: str | None
    diagnostic: tuple[str, ...]


def resolve_dagger_eligibility(inputs: DaggerEligibilityInputs) -> DaggerEligibility:
    """Apply the pinned immediate-right-neighbor Dagger condition."""
    if not isinstance(inputs, DaggerEligibilityInputs):
        return DaggerEligibility(None, None, ("unsupported:eligibility_input_type",))
    row = inputs.ordered_joker_instance_ids
    provided_fields = set()
    if row is not None:
        provided_fields.add("ordered_joker_instance_ids")
    for field_name, value in (
        ("dagger_getting_sliced", inputs.dagger_getting_sliced),
        ("right_victim_eternal", inputs.right_victim_eternal),
        ("right_victim_getting_sliced", inputs.right_victim_getting_sliced),
    ):
        if value is not None:
            provided_fields.add(field_name)
    catalog = _evidence_map(inputs.evidence_catalog)
    if provided_fields:
        if catalog is None or not catalog:
            return DaggerEligibility(None, None, ("missing:eligibility_evidence_catalog",))
        allowed = {field: {"observation", "derived"} for field in provided_fields}
        if any(record.channel == "reference" for record in catalog.values()):
            return DaggerEligibility(None, None, ("forbidden:reference_eligibility",))
        if not _field_evidence_valid(inputs.field_evidence, catalog, provided_fields, allowed):
            return DaggerEligibility(None, None, ("missing_or_invalid:field_evidence_links",))
    if row is None:
        return DaggerEligibility(None, None, ("missing:ordered_joker_row",))
    if not isinstance(row, tuple) or any(not isinstance(item, str) or not item for item in row):
        return DaggerEligibility(None, None, ("invalid:ordered_joker_row",))
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
    initial_field_evidence: tuple[tuple[str, tuple[str, ...]], ...],
    initial_evidence_catalog: tuple[EvidenceRecord, ...],
) -> ExtraValueState:
    """Apply Egg self-growth and Gift Card's all-owned-card increments."""
    if initial_value is None:
        return ExtraValueState(None, "unknown", ("missing:initial_extra_value",), ())
    if not isinstance(initial_value, int) or isinstance(initial_value, bool):
        return ExtraValueState(None, "unsupported", ("invalid:initial_extra_value",), ())
    catalog = _evidence_map(initial_evidence_catalog)
    if catalog is None or not _field_evidence_valid(
        initial_field_evidence, catalog, {"initial_extra_value"},
        {"initial_extra_value": {"source", "observation", "derived"}},
    ):
        if catalog and any(record.channel == "reference" for record in catalog.values()):
            return ExtraValueState(None, "unsupported", ("forbidden:reference_initial_extra_value",), ())
        return ExtraValueState(None, "unknown", ("missing:initial_extra_value_provenance",), ())
    try:
        event_rows = tuple(events)
    except TypeError:
        return ExtraValueState(None, "unsupported", ("invalid:extra_value_events",), ())
    value: int | None = initial_value
    evidence: list[str] = list(dict(initial_field_evidence)["initial_extra_value"])
    previous_order = -1
    for event in event_rows:
        if not isinstance(event, ExtraValueEvent):
            return ExtraValueState(None, "unsupported", ("invalid:extra_value_event_type",), tuple(evidence))
        if not isinstance(event.order, int) or isinstance(event.order, bool):
            return ExtraValueState(None, "unsupported", ("invalid:extra_value_event_order",), tuple(evidence))
        if event.order <= previous_order:
            return ExtraValueState(None, "ambiguous", ("contradictory:extra_value_event_order",), tuple(evidence))
        previous_order = event.order
        required = {"kind", "actor_instance_id", "increment"}
        if event.kind == "gift_card" and event.affected_instance_ids is not None:
            required.add("affected_instance_ids")
        event_catalog = _evidence_map(event.evidence_catalog)
        if event_catalog is None or not event_catalog:
            return ExtraValueState(None, "unknown", ("missing:extra_value_event_catalog",), tuple(evidence))
        if any(record.channel == "reference" for record in event_catalog.values()):
            return ExtraValueState(None, "unsupported", ("forbidden:reference_extra_value_event",), tuple(evidence))
        if not _field_evidence_valid(
            event.field_evidence,
            event_catalog,
            required,
            {field: {"observation", "derived", "source"} for field in required},
        ):
            return ExtraValueState(None, "unknown", ("missing_or_invalid:extra_value_field_evidence",), tuple(evidence))
        event_evidence = tuple(
            evidence_id for _, evidence_ids in event.field_evidence for evidence_id in evidence_ids
        )
        if event.kind == "egg":
            applies = event.actor_instance_id == instance_id
        elif event.kind == "gift_card":
            if event.affected_instance_ids is None:
                if value is not None:
                    value = None
                evidence.extend(event_evidence)
                continue
            applies = instance_id in event.affected_instance_ids
        else:
            return ExtraValueState(None, "unsupported", ("unsupported:extra_value_rule",), tuple(evidence))
        if applies:
            evidence.extend(event_evidence)
            if event.increment is not None and (
                not isinstance(event.increment, int) or isinstance(event.increment, bool)
            ):
                return ExtraValueState(None, "unsupported", ("invalid:extra_value_increment",), tuple(evidence))
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
    if not isinstance(inputs.source_stack, str) or not inputs.source_stack:
        return SellValue(None, "unknown", ("missing:source_stack",))
    if inputs.source_stack != PINNED_STACK:
        return SellValue(None, "unsupported", ("unsupported:source_stack",))
    if (
        not isinstance(inputs.source_hashes, tuple)
        or any(
            not isinstance(pair, tuple)
            or len(pair) != 2
            or not all(isinstance(value, str) for value in pair)
            for pair in inputs.source_hashes
        )
        or len(dict(inputs.source_hashes)) != len(inputs.source_hashes)
        or dict(inputs.source_hashes) != PINNED_SOURCE_HASHES
    ):
        return SellValue(None, "unknown", ("missing_or_mismatched:source_hashes",))
    if not isinstance(inputs.input_channels, tuple) or any(
        not isinstance(pair, tuple)
        or len(pair) != 2
        or not isinstance(pair[0], str)
        or not isinstance(pair[1], str)
        for pair in inputs.input_channels
    ):
        return SellValue(None, "unknown", ("invalid:input_channel_provenance",))
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
    catalog = _evidence_map(inputs.evidence_catalog)
    if catalog is None or not catalog:
        return SellValue(None, "unknown", ("missing:input_evidence_catalog",))
    if not _field_evidence_valid(inputs.field_evidence, catalog, required_channels, allowed_channels):
        return SellValue(None, "unknown", ("missing_or_invalid:field_evidence_links",))
    field_refs = dict(inputs.field_evidence)
    if any(
        not any(catalog[evidence_id].channel == channels[field] for evidence_id in field_refs[field])
        for field in required_channels
    ):
        return SellValue(None, "unknown", ("evidence_channel_mismatch",))
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
    field_evidence: tuple[tuple[str, tuple[str, ...]], ...] = ()
    evidence_catalog: tuple[EvidenceRecord, ...] = ()
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
    mult_resolution: str
    victim_removal_status: str
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
        if any(not isinstance(value, str) or not value for value in (
            event.run_id, event.round_id, event.interval_id, event.dagger_instance_id,
        )):
            raise ValueError("Dagger event identifiers must be non-empty strings")
        key = (event.run_id, event.interval_id)
        if key in seen_intervals:
            raise ValueError(f"duplicate Dagger interval: {key}")
        seen_intervals.add(key)
        if not isinstance(event.order, int) or isinstance(event.order, bool):
            raise ValueError(f"event order must be an integer: {key}")
        event_catalog = _evidence_map(event.evidence_catalog)
        if event_catalog is None or not event_catalog:
            raise ValueError(f"Dagger interval requires an evidence catalog: {key}")
        if any(record.channel == "reference" for record in event_catalog.values()):
            raise ValueError(f"Dagger reconstruction event cannot use reference evidence: {key}")
        previous = last_order.get(event.run_id)
        if previous is not None and event.order <= previous:
            raise ValueError(f"events are not globally chronological for {event.run_id}")
        last_order[event.run_id] = event.order

        instance_key = (event.run_id, event.dagger_instance_id)
        has_prior_state = instance_key in current_by_instance
        before = current_by_instance[instance_key] if has_prior_state else event.dagger_mult_before
        event_fields = {"run_id", "round_id", "interval_id", "dagger_instance_id"}
        event_channels = {field: {"observation", "derived", "source"} for field in event_fields}
        if event.dagger_mult_before is not None:
            event_fields.add("dagger_mult_before")
            event_channels["dagger_mult_before"] = {"observation", "derived"}
        if event.baseline_after is not None:
            event_fields.add("baseline_after")
            event_channels["baseline_after"] = {"observation"}
        if not _field_evidence_valid(event.field_evidence, event_catalog, event_fields, event_channels):
            raise ValueError(f"Dagger interval evidence does not resolve to its fields: {key}")
        event_evidence = tuple(
            evidence_id for _, evidence_ids in event.field_evidence for evidence_id in evidence_ids
        )
        if (
            not isinstance(event.evidence_ids, tuple)
            or any(not isinstance(value, str) or not value for value in event.evidence_ids)
            or set(event.evidence_ids) != set(event_evidence)
        ):
            raise ValueError(f"Dagger interval evidence IDs disagree with its field references: {key}")
        if event.dagger_mult_before is not None and event.mult_before_channel not in {"observation", "derived"}:
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
                mult_resolution="baseline_observed",
                victim_removal_status="not_applicable",
                opportunity=False,
                confirmed_sacrifice=False,
                victim_sell_value=None,
                growth=None,
                mult_before=before,
                mult_after=event.baseline_after,
                diagnostic=(),
                evidence_ids=event_evidence,
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
            mult_resolution, removal_status = "no_mutation", "not_scheduled"
            status, condition, confirmed, growth, victim_value, diagnostic = "inferred", "not_met", False, 0, None, ()
        elif eligibility.eligible is None:
            after = None
            mult_resolution, removal_status = "unknown", "unknown"
            status, condition, confirmed, growth, victim_value = "unknown", "unknown", None, None, None
            diagnostic = eligibility.diagnostic + ("invalidates:dagger_mult_and_future_growth",)
        elif before is None:
            after = None
            mult_resolution, removal_status = "unknown", "pending"
            status, condition, confirmed, growth, victim_value = "unknown", "unknown", True, None, None
            diagnostic = ("missing:dagger_mult_before", "invalidates:dagger_mult_and_future_growth")
        elif event.sell_inputs is None:
            after = None
            mult_resolution, removal_status = "unknown", "pending"
            status, condition, confirmed, growth, victim_value = "unknown", "unknown", True, None, None
            diagnostic = ("missing:sell_value_inputs", "invalidates:dagger_mult_and_future_growth")
        else:
            sell = construct_sell_value(event.sell_inputs)
            if sell.value is None:
                after = None
                mult_resolution, removal_status = "unknown", "pending"
                status, condition, confirmed, growth, victim_value = sell.status, "unknown", True, None, None
                diagnostic = sell.diagnostics + ("invalidates:dagger_mult_and_future_growth",)
            else:
                victim_value = sell.value
                growth = 2 * victim_value
                after = before + growth
                mult_resolution, removal_status = "resolved", "pending"
                status, condition, confirmed, diagnostic = "inferred", "met", True, ()
        current_by_instance[instance_key] = after
        input_evidence = tuple(
            evidence_id
            for _, evidence_ids in (event.sell_inputs.field_evidence if event.sell_inputs else ())
            for evidence_id in evidence_ids
        )
        eligibility_evidence = tuple(
            evidence_id
            for _, evidence_ids in (event.eligibility_inputs.field_evidence if event.eligibility_inputs else ())
            for evidence_id in evidence_ids
        )
        effects.append(DaggerEffect(
            event.run_id, event.round_id, event.interval_id, event.dagger_instance_id,
            eligibility.victim_instance_id, mult_resolution, removal_status,
            condition, status, True, confirmed,
            victim_value, growth, before, after, diagnostic,
            tuple(dict.fromkeys(event_evidence + eligibility_evidence + input_evidence)),
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


def select_winning_gold_stake_runs(
    run_metadata: Iterable[dict],
    evidence_catalog: tuple[EvidenceRecord, ...],
) -> tuple[set[str], list[dict]]:
    """Select only explicitly owner-confirmed Gold Stake wins with evidence."""
    selected: set[str] = set()
    excluded: list[dict] = []
    seen_ids: set[str] = set()
    ambiguous_ids: set[str] = set()
    catalog = _evidence_map(evidence_catalog)
    if catalog is not None and any(record.channel == "reference" for record in catalog.values()):
        # The selector catalogue is an input allowlist, not the bundle's general
        # evidence store. Do not make engine answers available to its selection.
        catalog = None
    for row in run_metadata:
        if not isinstance(row, dict):
            excluded.append({"run_id": None, "reasons": ["invalid_run_metadata"]})
            continue
        run_id = row.get("run_id")
        reasons = []
        if not isinstance(run_id, str) or not run_id:
            reasons.append("missing_run_id")
        elif run_id in seen_ids:
            ambiguous_ids.add(run_id)
            selected.discard(run_id)
            reasons.append("duplicate_run_metadata")
        if isinstance(run_id, str):
            seen_ids.add(run_id)
        row_field_evidence = row.get("field_evidence", ())
        row_ids = (
            tuple(evidence_id for _, ids in row_field_evidence for evidence_id in ids)
            if isinstance(row_field_evidence, tuple)
            and all(
                isinstance(pair, tuple)
                and len(pair) == 2
                and isinstance(pair[1], tuple)
                and all(isinstance(evidence_id, str) and evidence_id for evidence_id in pair[1])
                for pair in row_field_evidence
            )
            else ()
        )
        row_catalog = (
            {evidence_id: catalog[evidence_id] for evidence_id in row_ids if evidence_id in catalog}
            if catalog is not None else {}
        )
        if not _field_evidence_valid(
            row_field_evidence,
            row_catalog,
            {"stake", "outcome", "owner_confirmed"},
            {field: {"observation", "derived"} for field in ("stake", "outcome", "owner_confirmed")},
        ):
            reasons.append("selection_evidence_invalid")
        if row.get("owner_confirmed") is not True:
            reasons.append("stake_not_owner_confirmed")
        stake = row.get("stake")
        if not ((isinstance(stake, str) and stake in {"Gold", "Gold Stake"}) or (type(stake) is int and stake == 8)):
            reasons.append("not_gold_stake")
        if not isinstance(row.get("outcome"), str) or row["outcome"] not in {"won", "win"}:
            reasons.append("not_a_win")
        if isinstance(run_id, str) and run_id in ambiguous_ids:
            if "duplicate_run_metadata" not in reasons:
                reasons.append("duplicate_run_metadata")
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
    gold_stake_evidence_catalog: tuple[EvidenceRecord, ...] = (),
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
        selected_runs, selection_excluded = select_winning_gold_stake_runs(
            eligible_gold_stake_runs, gold_stake_evidence_catalog
        )
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
