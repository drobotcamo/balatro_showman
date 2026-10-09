"""Strict adapter from video-like Dagger observations to the shared reducer.

The adapter accepts only the observation envelope. A sibling engine-reference
payload is tolerated for comparison plumbing but is never read or copied into
the reducer event. Track keys identify observations within this interval only;
they are not asserted to be persistent game-instance IDs.
"""

from __future__ import annotations

import argparse
from dataclasses import asdict, dataclass
import json
from pathlib import Path
from typing import Any

from .dagger import (
    DaggerEligibilityInputs,
    EvidenceRecord,
    Sacrifice,
    reduce_sacrifices,
)

_RECORD_KEYS = {"case_id", "source", "observation", "engine_reference"}
_OBSERVATION_KEYS = {
    "run_id",
    "round_id",
    "interval_id",
    "order",
    "timing_status",
    "identity_status",
    "dagger_track_id",
    "mult_before",
    "ordered_joker_tracks",
    "dagger_getting_sliced",
    "victim_eternal",
    "victim_getting_sliced",
    "victim_sell_value_tooltip",
    "action_visible",
    "post_mult",
    "victim_absent_after",
}


@dataclass(frozen=True)
class AdaptedVideoLikeInterval:
    event: Sacrifice
    post_mult: int | None
    victim_absent_after: bool | None
    identity_status: str
    action_visible: str | None
    timing_status: str


def adapt_video_like_record(record: dict[str, Any]) -> AdaptedVideoLikeInterval:
    """Project allowlisted visual facts into the existing Dagger reducer input.

    Unknown keys inside the observation are rejected. Reference values may be
    present beside the observation for later comparison, but are intentionally
    not accessed here.
    """
    if not isinstance(record, dict) or set(record) - _RECORD_KEYS:
        raise ValueError("record contains unsupported or forbidden fields")
    observation = record.get("observation")
    if not isinstance(observation, dict) or set(observation) - _OBSERVATION_KEYS:
        raise ValueError("observation contains unsupported or reference-only fields")
    required = {"run_id", "round_id", "interval_id", "order", "timing_status", "identity_status", "dagger_track_id"}
    if not required.issubset(observation):
        raise ValueError(f"observation missing required fields: {sorted(required - set(observation))}")
    for field in ("run_id", "round_id", "interval_id", "dagger_track_id"):
        if not isinstance(observation[field], str) or not observation[field]:
            raise ValueError(f"invalid observation field: {field}")
    if type(observation["order"]) is not int:
        raise ValueError("order must be an integer visual-sequence order")
    if observation["identity_status"] not in {"unambiguous", "ambiguous", "unknown"}:
        raise ValueError("identity_status must preserve visual identity uncertainty")
    if observation["timing_status"] not in {"ordered_visual_sequence", "ambiguous", "unknown"}:
        raise ValueError("timing_status must distinguish visual ordering from verified alignment")
    for field in ("mult_before", "victim_sell_value_tooltip", "post_mult"):
        value = observation.get(field)
        if value is not None and (type(value) is not int or value < 0):
            raise ValueError(f"{field} must be a non-negative visible integer or null")
    if observation.get("victim_sell_value_tooltip") == 0:
        raise ValueError("victim_sell_value_tooltip must be a positive sell value or null")
    for field in ("dagger_getting_sliced", "victim_eternal", "victim_getting_sliced", "victim_absent_after"):
        value = observation.get(field)
        if value is not None and type(value) is not bool:
            raise ValueError(f"{field} must be a visible boolean or null")

    run_id = observation["run_id"]
    round_id = observation["round_id"]
    interval_id = observation["interval_id"]
    dagger_track = observation["dagger_track_id"]
    raw_row = observation.get("ordered_joker_tracks")
    if raw_row is not None and (
        not isinstance(raw_row, list)
        or any(not isinstance(item, str) or not item for item in raw_row)
    ):
        raise ValueError("ordered_joker_tracks must be a list of non-empty visual track keys or null")
    row = tuple(raw_row) if raw_row is not None else None
    fields: list[tuple[str, tuple[str, ...]]] = []
    catalog: list[EvidenceRecord] = []

    def add(field: str, channel: str = "observation") -> str:
        evidence_id = f"{interval_id}:visual:{field}"
        fields.append((field, (evidence_id,)))
        catalog.append(EvidenceRecord(evidence_id, channel, (field,)))
        return evidence_id

    event_fields = ("run_id", "round_id", "interval_id", "dagger_instance_id")
    for field in event_fields:
        add(field, "derived" if field == "dagger_instance_id" else "observation")
    add("observed_timing_status")
    add("observed_identity_status")
    mult_before = observation.get("mult_before")
    if mult_before is not None:
        add("dagger_mult_before")

    eligibility: DaggerEligibilityInputs | None = None
    action_visible = observation.get("action_visible")
    if action_visible is not None and not isinstance(action_visible, str):
        raise ValueError("action_visible must be a visible action label or null")
    if action_visible not in {None, "select_blind"}:
        raise ValueError("unsupported Dagger trigger action; only visible select_blind is in this fixture contract")
    if (
        observation["identity_status"] == "unambiguous"
        and observation["timing_status"] == "ordered_visual_sequence"
        and row is not None
        and action_visible
    ):
        eligibility_values = {
            "ordered_joker_instance_ids": row,
            "dagger_getting_sliced": observation.get("dagger_getting_sliced"),
            "right_victim_eternal": observation.get("victim_eternal"),
            "right_victim_getting_sliced": observation.get("victim_getting_sliced"),
        }
        eligibility_fields: list[tuple[str, tuple[str, ...]]] = []
        eligibility_catalog: list[EvidenceRecord] = []
        for field, value in eligibility_values.items():
            if value is not None:
                evidence_id = f"{interval_id}:visual:{field}"
                eligibility_fields.append((field, (evidence_id,)))
                eligibility_catalog.append(EvidenceRecord(evidence_id, "observation", (field,)))
        eligibility = DaggerEligibilityInputs(
            dagger_track,
            **eligibility_values,
            field_evidence=tuple(eligibility_fields),
            evidence_catalog=tuple(eligibility_catalog),
        )

    observed_sell = observation.get("victim_sell_value_tooltip")
    if observed_sell is not None:
        add("observed_victim_sell_value")
    observed_post_mult = observation.get("post_mult")
    if observed_post_mult is not None:
        add("observed_post_mult")
    if action_visible:
        add("observed_action")
    event = Sacrifice(
        run_id=run_id,
        round_id=round_id,
        interval_id=interval_id,
        order=observation["order"],
        dagger_instance_id=dagger_track,
        dagger_mult_before=mult_before,
        eligibility_inputs=eligibility,
        evidence_ids=tuple(evidence_id for _, ids in fields for evidence_id in ids),
        field_evidence=tuple(fields),
        evidence_catalog=tuple(catalog),
        mult_before_channel="observation" if mult_before is not None else None,
        observed_victim_sell_value=observed_sell,
        observed_action=action_visible,
        observed_timing_status=observation["timing_status"],
        observed_identity_status=observation["identity_status"],
        observed_post_mult=observed_post_mult,
    )
    return AdaptedVideoLikeInterval(
        event=event,
        post_mult=observation.get("post_mult"),
        victim_absent_after=observation.get("victim_absent_after"),
        identity_status=observation["identity_status"],
        action_visible=observation.get("action_visible"),
        timing_status=observation["timing_status"],
    )


def _reconcile_video_like(
    adapted: AdaptedVideoLikeInterval, effect: Any
) -> dict[str, Any]:
    conflicts: list[str] = []
    if adapted.action_visible is None:
        conflicts.append("missing:visible_action")
    if adapted.identity_status != "unambiguous":
        conflicts.append(f"{adapted.identity_status}:visual_identity")
    if adapted.timing_status != "ordered_visual_sequence":
        conflicts.append(f"{adapted.timing_status}:visual_timing")
    if adapted.post_mult is not None and effect.mult_after is not None and adapted.post_mult != effect.mult_after:
        conflicts.append("contradictory:visible_post_mult")
    if adapted.victim_absent_after is True and effect.condition == "not_met":
        conflicts.append("contradictory:victim_absent_without_eligible_target")
    contradiction_conflicts = tuple(
        token for token in conflicts if token.startswith("contradictory:")
    )
    input_uncertainties = tuple(
        token for token in conflicts if token.startswith(("missing:", "unknown:", "ambiguous:"))
    )
    if contradiction_conflicts or input_uncertainties:
        from dataclasses import replace

        effect = replace(
            effect,
            status=("ambiguous" if contradiction_conflicts or any(
                token.startswith("ambiguous:") for token in input_uncertainties
            ) else "unknown"),
            condition=("contradictory_aftermath" if contradiction_conflicts else "unknown_observation"),
            mult_resolution="unknown",
            growth=None,
            mult_after=None,
            diagnostic=tuple(dict.fromkeys(effect.diagnostic + input_uncertainties + contradiction_conflicts)),
        )
    status = "ambiguous" if any(token.startswith(("ambiguous:", "contradictory:")) for token in conflicts) else (
        "unknown" if effect.mult_after is None or adapted.post_mult is None else "consistent"
    )
    readable = []
    for code in effect.diagnostic:
        if code.startswith("invalidates:") or code.startswith("contradictory:"):
            continue
        dependency = code.split(":", 1)[-1]
        if "sell_value" in dependency:
            reason = "the victim sell-value tooltip or a complete independently evidenced pricing derivation is unavailable"
            affected = "victim sell value, Dagger growth, Dagger Mult, and downstream growth queries"
        elif "eligibility" in dependency or "identity" in dependency or "dagger_position" in dependency:
            reason = "the action, ordered Joker row, or unambiguous Dagger/neighbor identity needed to resolve eligibility is unavailable"
            affected = "sacrifice eligibility, victim attribution, Dagger growth, and downstream growth queries"
        else:
            reason = "the visual evidence is insufficient or contradictory"
            affected = "the affected Dagger state/effect and dependent queries"
        readable.append(
            f"interval={effect.interval_id}; rule={effect.rule_revision}; instance={effect.dagger_instance_id}; "
            f"dependency={dependency}; affected={affected}; reason={reason}"
        )
    for conflict in conflicts:
        if conflict.startswith("missing:") or conflict.startswith("unknown:"):
            dependency = conflict.split(":", 1)[-1]
            readable.append(
                f"interval={effect.interval_id}; rule={effect.rule_revision}; instance={effect.dagger_instance_id}; "
                f"dependency={dependency}; affected=sacrifice eligibility, Dagger growth/Mult, and dependent queries; "
                f"reason=the action/identity/timing observation required for this interval is unavailable or ambiguous"
            )
            continue
        if conflict.startswith("ambiguous:"):
            dependency = conflict.split(":", 1)[-1]
            reason = (
                "the visual identity cannot be uniquely associated in this interval"
                if dependency == "visual_identity"
                else "the action-to-aftermath order cannot be determined from these observations"
            )
            readable.append(
                f"interval={effect.interval_id}; rule={effect.rule_revision}; instance={effect.dagger_instance_id}; "
                f"dependency={dependency}; affected=victim attribution, Dagger growth/Mult, and dependent queries; "
                f"reason={reason}"
            )
            continue
        readable.append(
            f"interval={effect.interval_id}; rule={effect.rule_revision}; instance={effect.dagger_instance_id}; "
            f"dependency=visible_aftermath; affected=Dagger Mult and growth queries; "
            f"reason=the observed post-state contradicts the reducer result ({conflict})"
        )
    return {
        "effect": effect,
        "status": status,
        "diagnostics": tuple(dict.fromkeys(effect.diagnostic + tuple(conflicts))),
        "readable_diagnostics": tuple(readable),
        "observed_mult_delta": (
            adapted.post_mult - effect.mult_before
            if adapted.post_mult is not None
            and effect.mult_before is not None
            and adapted.identity_status == "unambiguous"
            and adapted.timing_status == "ordered_visual_sequence"
            and adapted.action_visible == "select_blind"
            else None
        ),
    }


def run_video_like_records(records: list[dict[str, Any]]) -> list[dict[str, Any]]:
    """Reduce ordered observations together so unknowns and observed baselines propagate."""
    adapted = [adapt_video_like_record(record) for record in records]
    effects = reduce_sacrifices(tuple(item.event for item in adapted))
    return [_reconcile_video_like(item, effect) for item, effect in zip(adapted, effects, strict=True)]


def run_video_like_record(record: dict[str, Any]) -> dict[str, Any]:
    """Run one adapted interval and compare any separately visible aftermath."""
    return run_video_like_records([record])[0]


def main(argv: list[str] | None = None) -> int:
    parser = argparse.ArgumentParser(description="Run the Dagger video-like observation fixture")
    parser.add_argument(
        "dataset",
        nargs="?",
        type=Path,
        default=Path(__file__).resolve().parents[1] / "tests" / "fixtures" / "video_like" / "dagger_v1.json",
    )
    args = parser.parse_args(argv)
    payload = json.loads(args.dataset.read_text(encoding="utf-8"))
    adapted_results = run_video_like_records(payload["cases"])
    for row, result in zip(payload["cases"], adapted_results, strict=True):
        print(json.dumps({
            "case_id": row["case_id"],
            "status": result["status"],
            "effect": asdict(result["effect"]),
            "diagnostics": result["diagnostics"],
            "readable_diagnostics": result["readable_diagnostics"],
            "observed_mult_delta": result["observed_mult_delta"],
        }, sort_keys=True))
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
