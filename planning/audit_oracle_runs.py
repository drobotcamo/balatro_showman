"""Read-only integrity audit for persisted Lua-oracle runs.

A "run directory" is a directory containing `session.json` and `steps.ndjson`
as written by `ground_truth/file_ipc_bridge.py`. This tool never writes to the
run directory and never modifies repository state.

Usage (from the repository root):

    py -3 planning\\audit_oracle_runs.py RUN_DIR [RUN_DIR ...]

Exit code 0 means every integrity invariant held for every run. Coverage and
conformance gaps (coarse actions, empty persistent_state, missing fields) are
printed as findings but do not fail the audit: they are contract questions
tracked in `planning/ORACLE_DATA_REVIEW.md`, not data corruption.

Stdlib only.
"""

from __future__ import annotations

import json
import sys
from collections import Counter
from pathlib import Path

STATE_KEYS = (
    "hands_left",
    "discards_left",
    "dollars",
    "ante",
    "round",
    "deck_remaining",
    "deck_total",
    "round_score",
    "hand_size_current",
    "hand_size_total",
    "jokers_current",
    "jokers_total",
    "consumables_current",
    "consumables_total",
)

REQUIRED_TOP_LEVEL = (
    "schema_version",
    "request_id",
    "page_name",
    "state",
    "objects",
    "pending_cards",
    "persistent_state",
    "action_taken",
    "meta",
)

# Canonical live/2.0 shop and opened-pack offering zones (D009). Bare
# `ShopOfferings` is a deprecated offline-extractor alias with no distinct live
# area, so it is not part of this set (Issue #16).
OFFERING_ZONES = (
    "TopShelfShopOfferings",
    "VoucherShopOfferings",
    "PackShopOfferings",
    "PackOfferings",
)

INTEGRITY_FAILURES: list[str] = []


def fail(message: str) -> None:
    INTEGRITY_FAILURES.append(message)


# Object attribute columns in the adopted object schema. `stickers` is
# list-valued (empty list when none); modifier/edition/seal are null when absent.
ATTRIBUTE_COLUMNS = ("modifier", "edition", "seal", "stickers")
# Playing cards cannot carry rental/perishable/eternal stickers (those attach to
# jokers/consumables), so `pending_cards.stickers` is structurally empty and is
# not part of the pending all-null check.
PENDING_ATTRIBUTE_COLUMNS = ("modifier", "edition", "seal")


def _present(value: object) -> bool:
    if value is None:
        return False
    if isinstance(value, (list, dict)) and len(value) == 0:
        return False
    return True


def _attribute_present_counts(
    rows: list[dict], columns: tuple[str, ...] = ATTRIBUTE_COLUMNS
) -> dict:
    return {
        column: sum(1 for row in rows if _present(row.get(column)))
        for column in columns
    }


def _all_null_columns(
    rows: list[dict], columns: tuple[str, ...] = ATTRIBUTE_COLUMNS
) -> list[str]:
    if not rows:
        return []
    counts = _attribute_present_counts(rows, columns)
    return [column for column in columns if counts[column] == 0]


def conformance_findings(summary: dict) -> list[str]:
    """Non-fatal conformance notes for one run summary."""
    findings: list[str] = []
    if summary.get("offering_position_missing"):
        findings.append(
            f"{summary['run']}: {summary['offering_position_missing']} "
            "shop/pack offering object(s) missing an integer position_in_zone"
        )
    inventory = summary.get("inventory_objects", 0)
    if inventory and summary.get("inventory_class_id_null"):
        findings.append(
            f"{summary['run']}: {summary['inventory_class_id_null']}/{inventory} "
            "inventory object(s) have class_id:null (unmapped center_key)"
        )
    for column in summary.get("object_attribute_all_null", []):
        findings.append(
            f"{summary['run']}: object.{column} is null/empty on all "
            f"{summary.get('objects_total', 0)} objects"
        )
    if summary.get("object_stickers_not_list"):
        findings.append(
            f"{summary['run']}: object.stickers is not a list on "
            f"{summary['object_stickers_not_list']} object(s)"
        )
    for column in summary.get("pending_attribute_all_null", []):
        findings.append(
            f"{summary['run']}: pending_cards.{column} is null/empty on all "
            f"{summary.get('pending_cards_total', 0)} pending card(s)"
        )
    return findings


def load_run(run_dir: Path) -> tuple[dict, list[dict]]:
    session = json.loads((run_dir / "session.json").read_text(encoding="utf-8"))
    lines = [
        line
        for line in (run_dir / "steps.ndjson").read_text(encoding="utf-8").splitlines()
        if line.strip()
    ]
    records = [json.loads(line) for line in lines]
    return session, records


def audit(run_dir: Path) -> dict:
    label = run_dir.name
    session, records = load_run(run_dir)
    n = len(records)
    rid = [r.get("request_id") for r in records]
    run_ids = Counter(r.get("meta", {}).get("run_id") for r in records)

    summary: dict = {
        "run": label,
        "session_n_steps": session.get("n_steps"),
        "step_lines": n,
        "session_run_id": session.get("run_id"),
        "step_run_ids": dict(run_ids),
        "session_schema_version": session.get("schema_version"),
        "session_outcome": session.get("outcome"),
        "request_id_unique": len(set(rid)),
        "request_id_none": sum(1 for x in rid if x is None),
        "action_taken_missing": sum(1 for r in records if not r.get("action_taken")),
        "page_name_missing": sum(1 for r in records if not r.get("page_name")),
        "persistent_state_empty": sum(
            1 for r in records if r.get("persistent_state") in ({}, None)
        ),
        "legal_actions_present": sum(1 for r in records if r.get("legal_actions") is not None),
        "frame_idx_present": sum(1 for r in records if r.get("frame_idx") is not None),
        "pages": dict(Counter(r.get("page_name") for r in records)),
        "actions": dict(Counter(r.get("action_taken") for r in records)),
        "objects_total": sum(len(r.get("objects") or []) for r in records),
        "pending_cards_total": sum(len(r.get("pending_cards") or []) for r in records),
    }

    # --- integrity invariants (fatal) ---
    if session.get("n_steps") != n:
        fail(f"{label}: session.n_steps={session.get('n_steps')} != step lines={n}")
    if len(set(rid)) != n or any(x is None for x in rid):
        fail(f"{label}: request_id is not unique/non-null on every step")
    if len(run_ids) != 1 or session.get("run_id") not in run_ids:
        fail(f"{label}: step run_id does not match session run_id ({dict(run_ids)})")
    if session.get("outcome") not in {"win", "loss"}:
        fail(f"{label}: session.outcome is not win/loss ({session.get('outcome')!r})")
    for field in REQUIRED_TOP_LEVEL:
        missing = sum(1 for r in records if field not in r)
        if missing:
            fail(f"{label}: {field!r} absent on {missing}/{n} steps")
    for key in STATE_KEYS:
        missing = sum(1 for r in records if key not in (r.get("state") or {}))
        summary[f"state_missing_{key}"] = missing
        if missing:
            fail(f"{label}: state.{key} absent on {missing}/{n} steps")

    # --- conformance gaps (non-fatal, reported) ---
    summary["source_kind_distinct"] = sorted(
        {r.get("source_kind") for r in records}, key=str
    )
    summary["action_subtype_distinct"] = sorted(
        {r.get("action_subtype") for r in records}, key=str
    )
    summary["target_zone_distinct"] = sorted(
        {r.get("target_zone") for r in records}, key=str
    )
    summary["schema_versions"] = dict(Counter(r.get("schema_version") for r in records))
    summary["runtime_distinct"] = sorted(
        {json.dumps(r.get("meta", {}).get("runtime"), sort_keys=True) for r in records}
    )
    obj = [
        o
        for r in records
        for o in (r.get("objects") or [])
        if isinstance(o, dict)
    ]
    summary["object_types"] = dict(Counter(o.get("object_type") for o in obj))
    summary["object_zones"] = dict(Counter(o.get("zone") for o in obj))
    offering = [o for o in obj if o.get("zone") in OFFERING_ZONES]
    summary["offering_objects_total"] = len(offering)
    summary["offering_zone_counts"] = {
        zone: summary["object_zones"].get(zone, 0) for zone in OFFERING_ZONES
    }
    summary["offering_zones_present"] = [
        zone for zone in OFFERING_ZONES if summary["object_zones"].get(zone)
    ]
    summary["offering_zones_missing"] = [
        zone for zone in OFFERING_ZONES if not summary["object_zones"].get(zone)
    ]
    summary["offering_position_missing"] = sum(
        1 for o in offering if not isinstance(o.get("position_in_zone"), int)
    )
    summary["object_modifier_null"] = sum(1 for o in obj if o.get("modifier") is None)
    summary["object_edition_null"] = sum(1 for o in obj if o.get("edition") is None)
    summary["object_seal_null"] = sum(1 for o in obj if o.get("seal") is None)
    summary["object_class_id_null"] = sum(1 for o in obj if o.get("class_id") is None)
    summary["object_attribute_present"] = _attribute_present_counts(obj)
    summary["object_attribute_all_null"] = _all_null_columns(obj)
    summary["object_stickers_not_list"] = sum(
        1 for o in obj if o.get("stickers") is not None and not isinstance(o.get("stickers"), list)
    )
    inv_types = {"joker", "tarot", "planet", "spectral", "consumable", "voucher"}
    inv = [o for o in obj if o.get("object_type") in inv_types]
    summary["inventory_objects"] = len(inv)
    summary["inventory_class_id_present"] = sum(
        1 for o in inv if o.get("class_id") is not None
    )
    summary["inventory_class_id_null"] = sum(1 for o in inv if o.get("class_id") is None)
    summary["inventory_center_key_only"] = sum(
        1 for o in inv if o.get("center_key") and o.get("class_id") is None
    )

    pending = [
        c
        for r in records
        for c in (r.get("pending_cards") or [])
        if isinstance(c, dict)
    ]
    summary["pending_cards_total_attrs"] = len(pending)
    summary["pending_class_id_null"] = sum(1 for c in pending if c.get("class_id") is None)
    summary["pending_attribute_present"] = _attribute_present_counts(
        pending, PENDING_ATTRIBUTE_COLUMNS
    )
    summary["pending_attribute_all_null"] = _all_null_columns(
        pending, PENDING_ATTRIBUTE_COLUMNS
    )
    return summary


def main(argv: list[str]) -> int:
    if len(argv) < 2:
        print(__doc__)
        return 2
    for raw in argv[1:]:
        run_dir = Path(raw)
        if not (run_dir / "session.json").is_file() or not (
            run_dir / "steps.ndjson"
        ).is_file():
            fail(f"{run_dir}: missing session.json or steps.ndjson")
            continue
        summary = audit(run_dir)
        print(json.dumps(summary, indent=2, sort_keys=True))
        for finding in conformance_findings(summary):
            print(f"FINDING: {finding}")
        print()

    if INTEGRITY_FAILURES:
        for message in INTEGRITY_FAILURES:
            print(f"FAIL: {message}")
        print(f"\n{len(INTEGRITY_FAILURES)} integrity failure(s)")
        return 1
    print("oracle run integrity OK")
    return 0


if __name__ == "__main__":
    sys.exit(main(sys.argv))
