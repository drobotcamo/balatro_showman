from __future__ import annotations

from dataclasses import replace

import pytest

from run_mechanics.hermit_rebate import (
    CoverageWindow,
    EvidenceRecord,
    HermitUse,
    RebateDiscard,
    compare_reference,
    hermit_occurrence_id,
    hermit_money_report,
    rebate_occurrence_id,
    rebate_report,
    reduce_hermit_uses,
    reduce_rebate_discards,
    synthetic_demo_report,
)


def coverage(run_id, scope_kind, source_ids, interval_ids, *, complete=True):
    values = {
        "run_id": run_id, "scope_kind": scope_kind, "scope_id": f"{run_id}:{scope_kind}",
        "source_instance_ids": tuple(sorted(set(source_ids))),
        "interval_ids": tuple(sorted(set(interval_ids))), "complete": complete,
    }
    links = tuple((field, (f"coverage:{field}",)) for field in values)
    records = tuple(EvidenceRecord(ids[0], "observation", (field,)) for field, ids in links)
    return CoverageWindow(**values, field_evidence=links, evidence_catalog=records)


def hermit(occurrence, order, dollars, cap, interval_delta):
    values = {
        "run_id": "run-1", "round_id": "round-1", "interval_id": f"interval-{order}",
        "occurrence_id": hermit_occurrence_id("run-1", f"interval-{order}", "hermit-1"),
        "source_instance_id": "hermit-1",
        "dollars_before": dollars, "ability_extra": cap,
        "dollars_after": None if dollars is None else dollars + max(0, min(dollars, cap)),
        "interval_money_delta": interval_delta,
    }
    fields = tuple(field for field, value in values.items() if value is not None)
    links = tuple((field, (f"{occurrence}:{field}",)) for field in fields)
    catalog = tuple(EvidenceRecord(ids[0], "observation", (field,)) for field, ids in links)
    return HermitUse(
        **values, order=order, field_evidence=links, evidence_catalog=catalog,
    )


def rebate(occurrence, order, *, rebate_id="rebate-1", card_id, target_id=8,
           target="8", rank_id=8, effective_rank_id=None, rank="8", debuffed=False, bonus=5,
           multiplicity=1, interval_delta=5, interval_id=None, round_id=None):
    values = {
        "run_id": "run-1", "round_id": round_id or f"round-{order}",
        "interval_id": interval_id or f"discard-{order}",
        "occurrence_id": rebate_occurrence_id(
            "run-1", interval_id or f"discard-{order}", rebate_id, card_id
        ), "rebate_instance_id": rebate_id,
        "discarded_instance_id": card_id, "target_rank_id": target_id,
        "target_rank": target, "discarded_rank_id": rank_id,
        "discarded_effective_rank_id": rank_id if effective_rank_id is None else effective_rank_id,
        "discarded_rank": rank,
        "debuffed": debuffed, "bonus_per_trigger": bonus,
        "trigger_multiplicity": multiplicity, "interval_money_delta": interval_delta,
    }
    fields = tuple(field for field, value in values.items() if value is not None)
    links = tuple((field, (f"{occurrence}:{field}",)) for field in fields)
    catalog = tuple(EvidenceRecord(ids[0], "observation", (field,)) for field, ids in links)
    return RebateDiscard(
        **values, order=order, field_evidence=links, evidence_catalog=catalog,
    )


def test_hermit_direct_contribution_is_capped_and_separate_from_interval_delta():
    effects = reduce_hermit_uses([
        hermit("use-1", 1, 12, 20, 25),
        hermit("use-2", 2, 3, 20, -4),
        hermit("use-3", 3, 12, 0, 0),
    ])
    assert [row.direct_contribution for row in effects] == [12, 3, 0]
    assert [(row.dollars_before, row.dollars_after) for row in effects] == [(12, 24), (3, 6), (12, 12)]
    assert [row.interval_money_delta for row in effects] == [25, -4, 0]
    report = hermit_money_report(effects, coverage(
        "run-1", "full_run", ["hermit-1"], ["interval-1", "interval-2", "interval-3"]
    ))
    assert (report["money"], report["status"], report["occurrence_count"]) == (15, "known", 3)
    assert report["attribution"] == "direct_hermit_contribution"


def test_hermit_repeated_uses_unknowns_and_deduplication():
    first = hermit("same-card-use-a", 1, 4, 20, 4)
    second = hermit("same-card-use-b", 2, 4, 20, 20)
    assert len(reduce_hermit_uses([first, second])) == 2
    with pytest.raises(ValueError, match="duplicate"):
        reduce_hermit_uses([first, first])
    missing = replace(hermit("use-unknown", 1, None, 20, None),
                      field_evidence=tuple((k, v) for k, v in hermit("use-unknown", 1, None, 20, None).field_evidence
                                           if k != "dollars_before"))
    effect = reduce_hermit_uses([missing])[0]
    assert effect.direct_contribution is None
    assert hermit_money_report([effect], coverage(
        "run-1", "full_run", ["hermit-1"], ["interval-1"]
    ))["money"] is None

    contradictory = replace(hermit("use-conflict", 1, 4, 20, 4), dollars_after=99)
    conflicted = reduce_hermit_uses([contradictory])[0]
    assert conflicted.status == "ambiguous"
    assert conflicted.direct_contribution is None
    assert conflicted.diagnostics == ("contradictory:hermit_money_after",)


def test_rebate_preserves_each_card_and_multiplies_only_qualifying_triggers():
    events = [
        rebate("one", 1, card_id="card-a", multiplicity=2, interval_delta=10),
        rebate("two", 2, card_id="card-b", multiplicity=1, interval_delta=5),
        rebate("three", 3, card_id="card-c", rank_id=7, rank="7", interval_delta=0),
        rebate("four", 4, card_id="card-d", debuffed=True, interval_delta=0),
        rebate("five", 5, card_id="card-e", rebate_id="rebate-2", interval_delta=5),
    ]
    effects = reduce_rebate_discards(events)
    assert [row.direct_contribution for row in effects] == [10, 5, 0, 0, 5]
    assert [row.discarded_instance_id for row in effects] == ["card-a", "card-b", "card-c", "card-d", "card-e"]
    assert effects[2].qualifying is False and effects[3].qualifying is False
    report = rebate_report(effects, coverage(
        "run-1", "joker_ownership", ["rebate-1", "rebate-2"],
        [f"discard-{index}" for index in range(1, 6)],
    ))
    assert [(row["round_id"], row["target_rank"], row["earnings"])
            for row in report["earnings_by_round_and_target_rank"]] == [
                ("round-1", "8", 10), ("round-2", "8", 5), ("round-3", "8", 0),
                ("round-4", "8", 0), ("round-5", "8", 5),
            ]
    assert report["most_frequent_qualifying_rank"] == ["8"]
    assert report["most_frequent_discarded_rank_while_owned"] == ["8"]


def test_rebate_rank_snapshot_and_target_rank_changes_are_distinct():
    first = rebate("first", 1, card_id="card-1", target_id=8, target="8", rank_id=8, rank="8")
    second = rebate("second", 2, card_id="card-2", target_id=9, target="9", rank_id=9, rank="9")
    effects = reduce_rebate_discards([first, second])
    assert [(row.target_rank, row.discarded_rank, row.direct_contribution) for row in effects] == [
        ("8", "8", 5), ("9", "9", 5)
    ]


def test_rebate_no_rank_get_id_sentinel_is_zero_not_a_rank_match():
    event = rebate(
        "stone-card", 1, card_id="stone", target_id=3, target="3",
        rank_id=3, effective_rank_id=-37134, rank="3", multiplicity=0, interval_delta=0,
    )
    effect = reduce_rebate_discards([event])[0]
    assert effect.discarded_rank_id == 3
    assert effect.discarded_effective_rank_id == -37134
    assert effect.qualifying is False
    assert effect.direct_contribution == 0
    assert effect.status == "inferred"


def test_multiple_rebate_instances_earn_independently_but_frequency_counts_card_once():
    first = rebate("one", 1, card_id="same-card", rebate_id="rebate-1")
    second = rebate(
        "two", 2, card_id="same-card", rebate_id="rebate-2",
        interval_id=first.interval_id, round_id=first.round_id,
    )
    effects = reduce_rebate_discards([first, second])
    report = rebate_report(effects, coverage(
        "run-1", "joker_ownership", ["rebate-1", "rebate-2"], ["discard-1"]
    ))
    assert [row.direct_contribution for row in effects] == [5, 5]
    assert report["earnings_by_round_and_target_rank"][0]["earnings"] == 10
    assert report["qualifying_discard_count_by_rank"] == {"8": 1}
    assert report["discarded_card_count_by_rank_while_owned"] == {"8": 1}
    assert report["most_frequent_qualifying_rank"] == ["8"]
    assert report["most_frequent_discarded_rank_while_owned"] == ["8"]


def test_rebate_ties_include_all_winners_and_incomplete_coverage_is_unknown():
    effects = reduce_rebate_discards([
        rebate("one", 1, card_id="card-1", target_id=8, target="8", rank_id=8, rank="8"),
        rebate("two", 2, card_id="card-2", target_id=9, target="9", rank_id=9, rank="9"),
    ])
    coverage_proof = coverage(
        "run-1", "joker_ownership", ["rebate-1"], ["discard-1", "discard-2"]
    )
    report = rebate_report(effects, coverage_proof)
    assert report["most_frequent_qualifying_rank"] == ["8", "9"]
    assert report["most_frequent_discarded_rank_while_owned"] == ["8", "9"]
    incomplete = rebate_report(effects, replace(coverage_proof, complete=False))
    assert incomplete["status"] == "unknown"
    assert incomplete["most_frequent_qualifying_rank"] is None
    assert incomplete["most_frequent_discarded_rank_while_owned"] is None


def test_missing_rebate_inputs_and_reference_leak_stay_unknown_or_rejected():
    event = rebate("unknown", 1, card_id="card-1", target_id=None, target=None)
    effect = reduce_rebate_discards([event])[0]
    assert effect.direct_contribution is None and effect.status == "unknown"
    report = rebate_report([effect], coverage("run-1", "joker_ownership", ["rebate-1"], ["discard-1"]))
    assert report["status"] == "unknown"
    assert report["earnings_by_round_and_target_rank"] == []
    assert report["unknown_occurrence_ids"] == [effect.occurrence_id]
    assert tuple(report["occurrences"][0]["evidence_ids"]) == effect.evidence_ids
    assert report["discarded_rank_frequency_status"] == "known"
    assert report["most_frequent_discarded_rank_while_owned"] == ["8"]
    assert report["most_frequent_qualifying_rank"] is None

    leaked = hermit("leaked", 1, 10, 20, 10)
    ref_catalog = tuple(replace(record, channel="reference") for record in leaked.evidence_catalog)
    blocked = reduce_hermit_uses([replace(leaked, evidence_catalog=ref_catalog)])[0]
    assert blocked.direct_contribution is None
    assert blocked.status == "unknown"
    assert blocked.diagnostics == ("forbidden:reference_evidence",)


def test_separate_reference_comparison_does_not_change_reconstruction():
    event = hermit("use-1", 1, 10, 20, 10)
    effects = reduce_hermit_uses([event])
    reference = [{"occurrence_id": effects[0].occurrence_id, "direct_contribution": 10,
                  "discarded_instance_ids": []}]
    assert compare_reference(effects, reference)[0]["status"] == "match"
    assert reduce_hermit_uses([event]) == effects


def test_empty_windows_are_unknown_and_incomplete_coverage_hides_subtotals():
    assert hermit_money_report([], coverage("run-1", "full_run", [], []))["money"] == 0
    empty_rebate = rebate_report([], coverage("run-1", "joker_ownership", [], []))
    assert empty_rebate["status"] == "unknown"
    assert empty_rebate["most_frequent_qualifying_rank"] is None
    assert empty_rebate["most_frequent_discarded_rank_while_owned"] is None
    event = rebate("one", 1, card_id="card-1")
    effect = reduce_rebate_discards([event])[0]
    report = rebate_report([effect], coverage(
        "run-1", "joker_ownership", ["rebate-1"], ["discard-1"], complete=False
    ))
    assert report["earnings_by_round_and_target_rank"][0]["earnings"] is None
    assert report["earnings_by_round_and_target_rank"][0]["status"] == "unknown"


def test_coverage_proof_must_cover_observed_sources_and_intervals():
    event = rebate("one", 1, card_id="card-1")
    effect = reduce_rebate_discards([event])[0]
    proof = coverage("run-1", "joker_ownership", ["other-rebate"], ["other-discard"])
    report = rebate_report([effect], proof)
    assert report["coverage"] == "incomplete"
    assert report["status"] == "unknown"
    assert report["diagnostics"] == ["incomplete:coverage_source_instances"]


def test_synthetic_report_is_explicit_and_answers_named_queries():
    report = synthetic_demo_report()
    assert report["synthetic"] is True
    assert report["reference_verification"] == "not_run"
    assert report["hermit"]["money"] == 9
    assert report["mail_in_rebate"]["earnings_by_round_and_target_rank"][0]["earnings"] == 5
    assert report["mail_in_rebate"]["most_frequent_qualifying_rank"] == ["8"]
    assert report["mail_in_rebate"]["most_frequent_discarded_rank_while_owned"] == ["7", "8"]
