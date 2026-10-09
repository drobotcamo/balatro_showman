"""Evidence-bounded Hermit and Mail-In Rebate occurrence reducers.

Reference answers are intentionally kept out of reconstruction inputs. The
comparators at the bottom accept a separate reference channel after reduction.
"""

from __future__ import annotations

from collections import Counter, defaultdict
from dataclasses import asdict, dataclass
import json
from typing import Iterable

PINNED_RULE_REVISION = "balatro-1.0.1o-FULL:exe-sha256-0d75fe164accf3312734d4b37ac98788dd15f0b8e4f9bb8b7f90c4e59de93f47"


@dataclass(frozen=True)
class EvidenceRecord:
    id: str
    channel: str
    supports: tuple[str, ...]


@dataclass(frozen=True)
class CoverageWindow:
    """Evidence-backed completeness claim for a run or an ownership window."""

    run_id: str
    scope_kind: str
    scope_id: str
    source_instance_ids: tuple[str, ...]
    interval_ids: tuple[str, ...]
    complete: bool
    field_evidence: tuple[tuple[str, tuple[str, ...]], ...]
    evidence_catalog: tuple[EvidenceRecord, ...]


def _catalog(records: tuple[EvidenceRecord, ...]) -> dict[str, EvidenceRecord] | None:
    if not isinstance(records, tuple):
        return None
    result: dict[str, EvidenceRecord] = {}
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
            or record.id in result
        ):
            return None
        result[record.id] = record
    return result


def _valid_evidence(
    field_evidence: tuple[tuple[str, tuple[str, ...]], ...],
    catalog: dict[str, EvidenceRecord] | None,
    fields: set[str],
) -> bool:
    if catalog is None or not catalog or not isinstance(field_evidence, tuple):
        return False
    try:
        links = dict(field_evidence)
    except (TypeError, ValueError):
        return False
    if len(links) != len(field_evidence) or set(links) != fields:
        return False
    used: set[str] = set()
    for field, evidence_ids in links.items():
        if not isinstance(evidence_ids, tuple) or not evidence_ids:
            return False
        for evidence_id in evidence_ids:
            record = catalog.get(evidence_id)
            if record is None or field not in record.supports or record.channel == "reference":
                return False
            used.add(evidence_id)
    return used == set(catalog)


def _coverage_result(
    coverage: CoverageWindow,
    expected_scope: str,
    run_ids: set[str],
    source_ids: set[str],
    interval_ids: set[str],
) -> tuple[bool, tuple[str, ...], tuple[str, ...]]:
    if not isinstance(coverage, CoverageWindow):
        return False, ("missing:coverage_window",), ()
    fields = {
        "run_id", "scope_kind", "scope_id", "source_instance_ids", "interval_ids", "complete",
    }
    catalog = _catalog(coverage.evidence_catalog)
    if not _valid_evidence(coverage.field_evidence, catalog, fields):
        return False, ("missing_or_invalid:coverage_evidence",), ()
    refs = dict(coverage.field_evidence)
    evidence_ids = tuple(dict.fromkeys(eid for ids in refs.values() for eid in ids))
    if any(record.channel == "reference" for record in catalog.values()):
        return False, ("forbidden:reference_coverage_evidence",), evidence_ids
    if (
        not coverage.run_id or not coverage.scope_id
        or coverage.scope_kind != expected_scope
        or type(coverage.complete) is not bool
        or not isinstance(coverage.source_instance_ids, tuple)
        or not isinstance(coverage.interval_ids, tuple)
        or any(not isinstance(value, str) or not value for value in (
            *coverage.source_instance_ids, *coverage.interval_ids,
        ))
    ):
        return False, ("invalid:coverage_window",), evidence_ids
    if run_ids and run_ids != {coverage.run_id}:
        return False, ("contradictory:coverage_run_id",), evidence_ids
    if not source_ids.issubset(set(coverage.source_instance_ids)):
        return False, ("incomplete:coverage_source_instances",), evidence_ids
    if not interval_ids.issubset(set(coverage.interval_ids)):
        return False, ("incomplete:coverage_intervals",), evidence_ids
    if not coverage.complete:
        return False, ("incomplete:coverage_window",), evidence_ids
    return True, (), evidence_ids


def _stable_key(namespace: str, parts: tuple[str, ...]) -> str:
    # Length framing is deterministic and lets the Lua reference producer emit
    # the same identity without a nonstandard cryptographic dependency.
    return namespace + ":" + "".join(f"{len(part)}#{part}" for part in parts)


def _rank_label(rank_id: int | None, label: str | None) -> str | None:
    if label is not None:
        return label
    if rank_id is None:
        return None
    if rank_id == 1 or rank_id == 14:
        return "Ace"
    if rank_id == 11:
        return "Jack"
    if rank_id == 12:
        return "Queen"
    if rank_id == 13:
        return "King"
    return str(rank_id) if 2 <= rank_id <= 10 else f"id:{rank_id}"


def _rank_label_consistent(rank_id: int | None, label: str | None) -> bool:
    if rank_id is None or label is None:
        return True
    expected = _rank_label(rank_id, None)
    return label == expected


def hermit_occurrence_id(run_id: str, interval_id: str, source_instance_id: str) -> str:
    """Stable key for the one use by a source instance in a source action."""
    return _stable_key("hermit-use-v1", (run_id, interval_id, source_instance_id))


def rebate_occurrence_id(
    run_id: str, interval_id: str, rebate_instance_id: str, discarded_instance_id: str,
) -> str:
    """Stable key preserves each discarded card and each Rebate source."""
    return _stable_key(
        "rebate-discard-v1", (run_id, interval_id, rebate_instance_id, discarded_instance_id)
    )


@dataclass(frozen=True)
class HermitUse:
    run_id: str
    round_id: str
    interval_id: str
    occurrence_id: str
    source_instance_id: str
    order: int
    dollars_before: int | None
    dollars_after: int | None
    ability_extra: int | None
    interval_money_delta: int | None
    field_evidence: tuple[tuple[str, tuple[str, ...]], ...]
    evidence_catalog: tuple[EvidenceRecord, ...]
    rule_revision: str = PINNED_RULE_REVISION + ":hermit-use-v1"


@dataclass(frozen=True)
class HermitEffect:
    run_id: str
    round_id: str
    interval_id: str
    occurrence_id: str
    source_instance_id: str
    order: int
    dollars_before: int | None
    dollars_after: int | None
    direct_contribution: int | None
    interval_money_delta: int | None
    status: str
    evidence_ids: tuple[str, ...]
    diagnostics: tuple[str, ...]
    rule_revision: str


def reduce_hermit_uses(events: Iterable[HermitUse]) -> list[HermitEffect]:
    """Compute Hermit's direct capped contribution, not the interval net change."""
    effects: list[HermitEffect] = []
    seen: set[tuple[str, str]] = set()
    last_order: dict[str, int] = {}
    for event in events:
        if not isinstance(event, HermitUse):
            raise ValueError("unsupported Hermit event")
        key = (event.run_id, event.occurrence_id)
        if any(not isinstance(value, str) or not value for value in key + (
            event.round_id, event.interval_id, event.source_instance_id,
        )):
            raise ValueError("Hermit occurrence identifiers must be non-empty")
        if event.occurrence_id != hermit_occurrence_id(
            event.run_id, event.interval_id, event.source_instance_id
        ):
            raise ValueError(f"non-deterministic Hermit occurrence identity: {key}")
        if key in seen:
            raise ValueError(f"duplicate Hermit occurrence: {key}")
        seen.add(key)
        if type(event.order) is not int or event.order <= last_order.get(event.run_id, -1):
            raise ValueError(f"Hermit uses are not strictly chronological: {key}")
        last_order[event.run_id] = event.order

        fields = {"run_id", "round_id", "interval_id", "occurrence_id", "source_instance_id"}
        if event.dollars_before is not None:
            fields.add("dollars_before")
        if event.dollars_after is not None:
            fields.add("dollars_after")
        if event.ability_extra is not None:
            fields.add("ability_extra")
        if event.interval_money_delta is not None:
            fields.add("interval_money_delta")
        catalog = _catalog(event.evidence_catalog)
        valid = _valid_evidence(event.field_evidence, catalog, fields)
        if not valid:
            diagnostic = (
                ("forbidden:reference_evidence",)
                if catalog is not None and any(row.channel == "reference" for row in catalog.values())
                else ("missing_or_invalid:field_evidence",)
            )
            effects.append(HermitEffect(
                event.run_id, event.round_id, event.interval_id, event.occurrence_id,
                event.source_instance_id, event.order, event.dollars_before, event.dollars_after,
                None, event.interval_money_delta,
                "unknown", (), diagnostic, event.rule_revision,
            ))
            continue
        links = dict(event.field_evidence)
        evidence = tuple(dict.fromkeys(eid for ids in links.values() for eid in ids))
        if event.rule_revision != PINNED_RULE_REVISION + ":hermit-use-v1":
            contribution, status, diagnostics = None, "unsupported", ("unsupported:rule_revision",)
        elif event.interval_money_delta is not None and type(event.interval_money_delta) is not int:
            contribution, status, diagnostics = None, "unsupported", ("invalid:interval_money_delta",)
        elif event.dollars_before is None or event.dollars_after is None or event.ability_extra is None:
            contribution, status, diagnostics = None, "unknown", ("missing:hermit_formula_input",)
        elif (type(event.dollars_before) is not int or type(event.dollars_after) is not int
              or type(event.ability_extra) is not int):
            contribution, status, diagnostics = None, "unsupported", ("invalid:hermit_formula_input",)
        else:
            # card.lua:1389: max(0, min(current dollars, Hermit's configured amount)).
            contribution = max(0, min(event.dollars_before, event.ability_extra))
            if event.dollars_after != event.dollars_before + contribution:
                contribution, status, diagnostics = None, "ambiguous", ("contradictory:hermit_money_after",)
            else:
                status, diagnostics = "inferred", ()
        effects.append(HermitEffect(
            event.run_id, event.round_id, event.interval_id, event.occurrence_id,
            event.source_instance_id, event.order, event.dollars_before, event.dollars_after,
            contribution,
            event.interval_money_delta, status, evidence, diagnostics, event.rule_revision,
        ))
    return effects


@dataclass(frozen=True)
class RebateDiscard:
    """One discarded-card participation row for one owned Rebate instance.

    Rows include nonqualifying/debuffed cards and zero-contribution cases. The
    specific discarded card identity is retained so distinct matching cards do
    not collapse into one rank-only event.
    """

    run_id: str
    round_id: str
    interval_id: str
    occurrence_id: str
    rebate_instance_id: str
    discarded_instance_id: str
    order: int
    target_rank_id: int | None
    target_rank: str | None
    discarded_rank_id: int | None
    discarded_rank: str | None
    debuffed: bool | None
    bonus_per_trigger: int | None
    trigger_multiplicity: int | None
    interval_money_delta: int | None
    field_evidence: tuple[tuple[str, tuple[str, ...]], ...]
    evidence_catalog: tuple[EvidenceRecord, ...]
    rule_revision: str = PINNED_RULE_REVISION + ":mail-in-rebate-v1"


@dataclass(frozen=True)
class RebateEffect:
    run_id: str
    round_id: str
    interval_id: str
    occurrence_id: str
    rebate_instance_id: str
    discarded_instance_id: str
    target_rank_id: int | None
    target_rank: str | None
    discarded_rank_id: int | None
    discarded_rank: str | None
    qualifying: bool | None
    direct_contribution: int | None
    trigger_multiplicity: int | None
    interval_money_delta: int | None
    status: str
    evidence_ids: tuple[str, ...]
    diagnostics: tuple[str, ...]
    rule_revision: str


def reduce_rebate_discards(events: Iterable[RebateDiscard]) -> list[RebateEffect]:
    """Reduce per-Joker/per-card trigger participation under the pinned rule."""
    effects: list[RebateEffect] = []
    seen: set[tuple[str, str]] = set()
    last_order: dict[str, int] = {}
    for event in events:
        if not isinstance(event, RebateDiscard):
            raise ValueError("unsupported Mail-In Rebate event")
        key = (event.run_id, event.occurrence_id)
        if any(not isinstance(value, str) or not value for value in key + (
            event.round_id, event.interval_id, event.rebate_instance_id,
            event.discarded_instance_id,
        )):
            raise ValueError("Mail-In Rebate occurrence identifiers must be non-empty")
        if event.occurrence_id != rebate_occurrence_id(
            event.run_id, event.interval_id, event.rebate_instance_id,
            event.discarded_instance_id,
        ):
            raise ValueError(f"non-deterministic Mail-In Rebate occurrence identity: {key}")
        if key in seen:
            raise ValueError(f"duplicate Mail-In Rebate occurrence: {key}")
        seen.add(key)
        if type(event.order) is not int or event.order <= last_order.get(event.run_id, -1):
            raise ValueError(f"Mail-In Rebate events are not strictly chronological: {key}")
        last_order[event.run_id] = event.order

        fields = {"run_id", "round_id", "interval_id", "occurrence_id", "rebate_instance_id",
                  "discarded_instance_id"}
        for name in ("target_rank_id", "target_rank", "discarded_rank_id", "discarded_rank",
                     "debuffed", "bonus_per_trigger", "trigger_multiplicity", "interval_money_delta"):
            if getattr(event, name) is not None:
                fields.add(name)
        catalog = _catalog(event.evidence_catalog)
        valid = _valid_evidence(event.field_evidence, catalog, fields)
        links = dict(event.field_evidence) if isinstance(event.field_evidence, tuple) else {}
        evidence = tuple(dict.fromkeys(eid for ids in links.values() for eid in ids))
        missing = [name for name in ("target_rank_id", "discarded_rank_id", "debuffed",
                                      "bonus_per_trigger", "trigger_multiplicity")
                   if getattr(event, name) is None]
        if not valid:
            qualifying, contribution, status = None, None, "unknown"
            diagnostics = (
                ("forbidden:reference_evidence",)
                if catalog is not None and any(row.channel == "reference" for row in catalog.values())
                else ("missing_or_invalid:field_evidence",)
            )
        elif missing:
            qualifying, contribution, status = None, None, "unknown"
            diagnostics = tuple(f"missing:{field}" for field in missing)
        elif not _rank_label_consistent(event.target_rank_id, event.target_rank) or not _rank_label_consistent(
            event.discarded_rank_id, event.discarded_rank
        ):
            qualifying, contribution, status = None, None, "ambiguous"
            diagnostics = ("contradictory:rank_id_and_label",)
        elif event.rule_revision != PINNED_RULE_REVISION + ":mail-in-rebate-v1":
            qualifying, contribution, status = None, None, "unsupported"
            diagnostics = ("unsupported:rule_revision",)
        elif event.interval_money_delta is not None and type(event.interval_money_delta) is not int:
            qualifying, contribution, status = None, None, "unsupported"
            diagnostics = ("invalid:interval_money_delta",)
        elif (
            type(event.target_rank_id) is not int
            or type(event.discarded_rank_id) is not int
            or type(event.debuffed) is not bool
            or type(event.bonus_per_trigger) is not int
            or type(event.trigger_multiplicity) is not int
            or event.bonus_per_trigger < 0
            or event.trigger_multiplicity < 0
        ):
            qualifying, contribution, status = None, None, "unsupported"
            diagnostics = ("invalid:rebate_rule_input",)
        else:
            qualifying = event.discarded_rank_id == event.target_rank_id and not event.debuffed
            contribution = (
                event.bonus_per_trigger * event.trigger_multiplicity if qualifying else 0
            )
            status, diagnostics = "inferred", ()
        effects.append(RebateEffect(
            event.run_id, event.round_id, event.interval_id, event.occurrence_id,
            event.rebate_instance_id, event.discarded_instance_id,
            event.target_rank_id, event.target_rank, event.discarded_rank_id,
            event.discarded_rank, qualifying, contribution, event.trigger_multiplicity,
            event.interval_money_delta, status, evidence, diagnostics, event.rule_revision,
        ))
    return effects


def hermit_money_report(effects: Iterable[HermitEffect], coverage: CoverageWindow) -> dict:
    """Return exact run sum only when every supplied occurrence is known."""
    rows = list(effects)
    unknown = [row for row in rows if row.status != "inferred" or row.direct_contribution is None]
    coverage_ok, coverage_diagnostics, coverage_evidence_ids = _coverage_result(
        coverage, "full_run", {row.run_id for row in rows},
        {row.source_instance_id for row in rows}, {row.interval_id for row in rows},
    )
    known = coverage_ok and not unknown
    return {
        "run_id": coverage.run_id if isinstance(coverage, CoverageWindow) else None,
        "money": sum(row.direct_contribution for row in rows) if known else None,
        "status": "known" if known else "unknown",
        "coverage": "complete" if coverage_ok else "incomplete",
        "coverage_evidence_ids": list(coverage_evidence_ids),
        "diagnostics": list(coverage_diagnostics),
        "occurrence_count": len(rows),
        "unknown_occurrence_ids": [row.occurrence_id for row in unknown],
        "occurrences": [asdict(row) for row in rows],
        "attribution": "direct_hermit_contribution",
    }


def rebate_report(effects: Iterable[RebateEffect], coverage: CoverageWindow) -> dict:
    """Aggregate target-rank earnings, qualifying ranks and all owned discards.

    Rank frequencies count each card-instance participation once, not trigger
    multiplicity. Earnings count direct contributions and remain unknown for any
    rank/round bucket touched by an unresolved participation.
    """
    rows = list(effects)
    coverage_ok, coverage_diagnostics, coverage_evidence_ids = _coverage_result(
        coverage, "joker_ownership", {row.run_id for row in rows},
        {row.rebate_instance_id for row in rows}, {row.interval_id for row in rows},
    )
    if not isinstance(coverage, CoverageWindow):
        coverage_run_id = None
    else:
        coverage_run_id = coverage.run_id
    qualifying_cards: dict[tuple[str, str, str], str] = {}
    discarded_cards: dict[tuple[str, str, str], str] = {}
    contradictory_card_ranks = False
    earnings: dict[tuple[str, str], list[RebateEffect]] = defaultdict(list)
    for row in rows:
        rank_label = _rank_label(row.discarded_rank_id, row.discarded_rank)
        if row.discarded_rank is not None:
            card_key = (row.run_id, row.interval_id, row.discarded_instance_id)
            prior = discarded_cards.setdefault(card_key, rank_label)
            contradictory_card_ranks |= prior != row.discarded_rank
        elif rank_label is not None:
            card_key = (row.run_id, row.interval_id, row.discarded_instance_id)
            prior = discarded_cards.setdefault(card_key, rank_label)
            contradictory_card_ranks |= prior != rank_label
        if row.qualifying is True and rank_label is not None:
            card_key = (row.run_id, row.interval_id, row.discarded_instance_id)
            prior = qualifying_cards.setdefault(card_key, rank_label)
            contradictory_card_ranks |= prior != rank_label
        target_label = _rank_label(row.target_rank_id, row.target_rank)
        if target_label is not None:
            earnings[(row.round_id, target_label)].append(row)

    def winners(counts: Counter[str]) -> list[str]:
        if not counts:
            return []
        maximum = max(counts.values())
        return sorted(rank for rank, count in counts.items() if count == maximum)

    buckets = []
    for (round_id, rank), bucket in sorted(earnings.items()):
        unknown = [row for row in bucket if (
            not coverage_ok or row.status != "inferred" or row.direct_contribution is None
        )]
        buckets.append({
            "round_id": round_id,
            "target_rank": rank,
            "earnings": None if unknown else sum(row.direct_contribution for row in bucket),
            "status": "unknown" if unknown else "known",
            "participation_count": len(bucket),
            "unknown_occurrence_ids": [row.occurrence_id for row in unknown],
            "occurrences": [asdict(row) for row in bucket],
        })
    qualifying_ranks = Counter(qualifying_cards.values())
    discarded_ranks = Counter(discarded_cards.values())
    coverage_complete = coverage_ok
    unknown_coverage = (
        not coverage_complete or not rows or contradictory_card_ranks
        or any(row.status != "inferred" for row in rows)
    )
    unknown_occurrences = [
        row.occurrence_id for row in rows
        if row.status != "inferred" or row.direct_contribution is None
        or row.target_rank_id is None or row.discarded_rank_id is None
    ]
    return {
        "earnings_by_round_and_target_rank": buckets,
        "qualifying_discard_count_by_rank": dict(sorted(qualifying_ranks.items())),
        "discarded_card_count_by_rank_while_owned": dict(sorted(discarded_ranks.items())),
        "most_frequent_qualifying_rank": None if unknown_coverage else winners(qualifying_ranks),
        "most_frequent_discarded_rank_while_owned": None if unknown_coverage else winners(discarded_ranks),
        "coverage": "complete" if coverage_complete else "incomplete",
        "coverage_evidence_ids": list(coverage_evidence_ids),
        "diagnostics": list(coverage_diagnostics) + (
            ["unknown:no_participation_occurrences"] if not rows else []
        ),
        "occurrence_diagnostics": [
            {"occurrence_id": row.occurrence_id, "diagnostics": list(row.diagnostics)}
            for row in rows if row.diagnostics
        ],
        "run_id": coverage_run_id,
        "status": "unknown" if unknown_coverage else "known",
        "participation_count": len(rows),
        "unknown_occurrence_ids": unknown_occurrences,
        "occurrences": [asdict(row) for row in rows],
        "attribution": "direct_rebate_contribution",
    }


def compare_reference(effects: Iterable[HermitEffect | RebateEffect], references: Iterable[dict]) -> list[dict]:
    """Compare already-reduced outputs to separate independent reference rows."""
    derived = {row.occurrence_id: row for row in effects}
    comparisons = []
    for reference in references:
        occurrence_id = reference.get("occurrence_id")
        row = derived.get(occurrence_id)
        expected = reference.get("direct_contribution")
        actual = row.direct_contribution if row is not None else None
        comparisons.append({
            "occurrence_id": occurrence_id,
            "status": "not_comparable" if row is None or expected is None or actual is None else (
                "match" if actual == expected else "mismatch"
            ),
            "derived_contribution": actual,
            "reference_contribution": expected,
            "reference_card_instance_ids": reference.get("discarded_instance_ids", []),
        })
    return comparisons


def synthetic_demo_report() -> dict:
    """Small printable example; values are illustrative, not oracle evidence."""
    def event_evidence(values: dict) -> tuple[tuple[tuple[str, tuple[str, ...]], ...], tuple[EvidenceRecord, ...]]:
        links = tuple((name, (f"synthetic:{name}:{index}",)) for index, name in enumerate(values))
        catalog = tuple(
            EvidenceRecord(ids[0], "observation", (field,)) for field, ids in links
        )
        return links, catalog

    hermit_data = {
        "run_id": "demo-run", "round_id": "demo-round", "interval_id": "hermit-use-1",
        "occurrence_id": hermit_occurrence_id("demo-run", "hermit-use-1", "hermit-instance-1"),
        "source_instance_id": "hermit-instance-1", "dollars_before": 9, "dollars_after": 18,
        "ability_extra": 20,
        "interval_money_delta": 13,
    }
    hermit_links, hermit_catalog = event_evidence(hermit_data)
    hermit_effects = reduce_hermit_uses([HermitUse(
        **hermit_data, order=1, field_evidence=hermit_links,
        evidence_catalog=hermit_catalog,
    )])

    rebate_rows = []
    for order, (card_id, rank_id, rank) in enumerate((
        ("discarded-card-1", 8, "8"), ("discarded-card-2", 7, "7"),
    ), start=1):
        values = {
            "run_id": "demo-run", "round_id": "demo-round", "interval_id": f"discard-{order}",
            "occurrence_id": rebate_occurrence_id(
                "demo-run", f"discard-{order}", "rebate-instance-1", card_id
            ),
            "rebate_instance_id": "rebate-instance-1", "discarded_instance_id": card_id,
            "target_rank_id": 8, "target_rank": "8", "discarded_rank_id": rank_id,
            "discarded_rank": rank, "debuffed": False, "bonus_per_trigger": 5,
            "trigger_multiplicity": 1 if rank_id == 8 else 0, "interval_money_delta": 5 if rank_id == 8 else 0,
        }
        links, catalog = event_evidence(values)
        rebate_rows.append(RebateDiscard(
            **values, order=order, field_evidence=links, evidence_catalog=catalog,
        ))
    rebate_effects = reduce_rebate_discards(rebate_rows)

    def demo_coverage(scope_kind: str, source_ids: tuple[str, ...], intervals: tuple[str, ...]) -> CoverageWindow:
        values = {
            "run_id": "demo-run", "scope_kind": scope_kind, "scope_id": f"demo-run:{scope_kind}",
            "source_instance_ids": source_ids, "interval_ids": intervals, "complete": True,
        }
        links = tuple((name, (f"synthetic:coverage:{name}",)) for name in values)
        catalog = tuple(
            EvidenceRecord(ids[0], "observation", (name,)) for name, ids in links
        )
        return CoverageWindow(**values, field_evidence=links, evidence_catalog=catalog)

    return {
        "fixture": "synthetic-hermit-rebate-v1",
        "synthetic": True,
        "reference_verification": "not_run",
        "hermit": hermit_money_report(hermit_effects, demo_coverage(
            "full_run", ("hermit-instance-1",), ("hermit-use-1",)
        )),
        "mail_in_rebate": rebate_report(rebate_effects, demo_coverage(
            "joker_ownership", ("rebate-instance-1",), ("discard-1", "discard-2")
        )),
    }


if __name__ == "__main__":
    print(json.dumps(synthetic_demo_report(), indent=2, sort_keys=True))
