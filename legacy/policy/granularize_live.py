#!/usr/bin/env python3
"""
granularize_live.py
===================
Convert recorded live sessions to granularized training format.

Reads:
  data/live_sessions/<run_id>/steps.ndjson   (written by policy/record_server.py)
  data/live_sessions/<run_id>/session.json

Writes:
  data/granularized/video_id=live_<run_id>/run_000.json
  data/persistent_state/video_id=live_<run_id>/run_000.json

The granularized format matches vendor/balatro-policy-transformer/granularize.py
schema 3.0.0, making live sessions directly consumable by the rest of the
outcome-conditioned pipeline:

  python policy/tensorize_oc.py \\
      --outcomes policy/data/outcomes.json \\
      --src data/granularized \\
      --persistent data/persistent_state \\
      --out data/tensorized_oc

Outcomes (win/loss) come from session.json. If outcome is null (not yet
labeled), the run is still written — label_outcomes.py can fill it in later,
or pass --skip-unlabeled to skip such runs.

SWAP synthesis
--------------
Joker-order SWAP steps are inserted between events when the CurrentJokers
zone order changes between consecutive steps. Adjacent transpositions
(bubble-sort style) produce the minimum number of SWAPs needed.

Usage
-----
  python policy/granularize_live.py                      # all sessions
  python policy/granularize_live.py --run-id 20260519_143022
  python policy/granularize_live.py --skip-unlabeled     # only labeled runs
"""

from __future__ import annotations

import argparse
import json
import sys
from pathlib import Path
from typing import Any

_HERE = Path(__file__).resolve().parent
_REPO = _HERE.parent
_VENDOR = _REPO / "vendor" / "balatro-policy-transformer"
if str(_VENDOR) not in sys.path:
    sys.path.insert(0, str(_VENDOR))

from state_reducer import (
    INTERNAL_KEYS,
    MODEL_VISIBLE_KEYS,
    apply_step,
    default_state,
)

GRANULARIZE_SCHEMA_VERSION = "3.0.0"
PERSISTENT_STATE_SCHEMA_VERSION = "2.0.0"
STATE_REDUCER_VERSION = "2.0.0"

# ---------------------------------------------------------------------------
# Action label parsing
# ---------------------------------------------------------------------------

# (base, zone) pairs from action_map.INDEXED_FAMILIES — used to parse labels.
_INDEXED_FAMILIES: list[tuple[str, str]] = [
    ("UseConsumable", "CurrentConsumables"),
    ("SelectCard", "CurrentHand"),
    ("SelectCard", "TarotSpectralHand"),
    ("SelectPackItem", "PackOfferings"),
    ("BuyAndUseShopConsumable", "TopShelfShopOfferings"),
    ("BuyShopItem", "VoucherShopOfferings"),
    ("BuyShopItem", "PackShopOfferings"),
    ("BuyShopItem", "TopShelfShopOfferings"),
    ("SellItem", "CurrentJokers"),
    ("SellItem", "CurrentConsumables"),
]
_FAMILY_KEY: dict[str, tuple[str, str]] = {
    f"{base}_{zone}": (base, zone) for base, zone in _INDEXED_FAMILIES
}


def parse_action_label(
    label: str,
) -> tuple[str, str | None, int | None, list[int] | None]:
    """Return (base, zone, position, swap_pair) for an action label.

    Examples:
      "BuyShopItem_TopShelfShopOfferings_0"  -> ("BuyShopItem", "TopShelfShopOfferings", 0, None)
      "SWAP_0_1"                             -> ("SWAP", None, None, [0, 1])
      "PlayHand"                             -> ("PlayHand", None, None, None)
    """
    if label.startswith("SWAP_"):
        parts = label.split("_")
        if len(parts) == 3:
            try:
                return "SWAP", None, None, [int(parts[1]), int(parts[2])]
            except ValueError:
                pass
        return "SWAP", None, None, None

    head, _, tail = label.rpartition("_")
    if tail.isdigit() and head in _FAMILY_KEY:
        base, zone = _FAMILY_KEY[head]
        return base, zone, int(tail), None

    return label, None, None, None


# ---------------------------------------------------------------------------
# SWAP synthesis helpers
# ---------------------------------------------------------------------------

def _joker_class_ids(objects: list[dict]) -> list[int]:
    """Return class_ids of CurrentJokers ordered by position_in_zone."""
    jokers = [o for o in objects if o.get("zone") == "CurrentJokers"]
    jokers.sort(key=lambda o: o.get("position_in_zone") or 0)
    return [o.get("class_id") for o in jokers]


def _adjacent_swaps_needed(
    old_order: list[int], new_order: list[int]
) -> list[tuple[int, int]]:
    """Return (i, j) adjacent transpositions that transform old_order → new_order.

    Uses a bubble-sort-style approach. Returns [] if orders are equal or if
    the sets differ (e.g. a joker was added or removed — not a pure reorder).
    """
    if old_order == new_order:
        return []
    if len(old_order) != len(new_order) or set(old_order) != set(new_order):
        return []
    arr = list(old_order)
    swaps: list[tuple[int, int]] = []
    for target_pos in range(len(arr)):
        if arr[target_pos] == new_order[target_pos]:
            continue
        src = arr.index(new_order[target_pos], target_pos + 1)
        while src > target_pos:
            arr[src], arr[src - 1] = arr[src - 1], arr[src]
            swaps.append((src - 1, src))
            src -= 1
    return swaps


# ---------------------------------------------------------------------------
# Granularized step builder
# ---------------------------------------------------------------------------

def _make_step(
    step_id: int,
    page_name: str,
    source_event_index: int,
    source_action: str | None,
    action: str,
    target_zone: str | None,
    target_position: int | None,
    swap_pair: list[int] | None,
    state: dict,
    objects: list,
    pending_cards: list,
) -> dict[str, Any]:
    return {
        "step_id": step_id,
        "frame_idx": step_id,
        "page_name": page_name,
        "source_event_index": source_event_index,
        "micro_index": 0,
        "source_kind": None,
        "source_action": source_action,
        "source_action_subtype": None,
        "action": action,
        "action_subtype": None,
        "target_zone": target_zone,
        "target_position": target_position,
        "swap_pair": swap_pair,
        "selected_object": None,
        "pending_cards": pending_cards or [],
        "state": state or {},
        "objects": objects or [],
    }


# ---------------------------------------------------------------------------
# Session converter
# ---------------------------------------------------------------------------

def convert_session(
    session_dir: Path,
    gran_root: Path,
    pstate_root: Path,
    skip_unlabeled: bool = False,
) -> bool:
    """Convert one session directory. Returns True on success."""
    steps_path = session_dir / "steps.ndjson"
    meta_path = session_dir / "session.json"
    run_id = session_dir.name

    if not steps_path.exists():
        print(f"  [skip] {run_id}: steps.ndjson missing")
        return False

    meta: dict[str, Any] = {}
    if meta_path.exists():
        try:
            meta = json.loads(meta_path.read_text(encoding="utf-8"))
        except Exception:
            pass

    outcome = meta.get("outcome")
    if skip_unlabeled and outcome is None:
        print(f"  [skip] {run_id}: outcome not labeled (pass --skip-unlabeled to suppress)")
        return False

    # Read recorded steps
    raw_steps: list[dict[str, Any]] = []
    with steps_path.open(encoding="utf-8") as fh:
        for line in fh:
            line = line.strip()
            if line:
                try:
                    raw_steps.append(json.loads(line))
                except json.JSONDecodeError:
                    pass

    if not raw_steps:
        print(f"  [skip] {run_id}: no steps")
        return False

    # Build granularized steps with SWAP synthesis
    gran_steps: list[dict[str, Any]] = []
    step_id = 0
    prev_joker_order: list[int] | None = None
    prev_action: str | None = None

    for event_idx, raw in enumerate(raw_steps):
        action_label: str = raw.get("_recorded_action") or ""
        page_name: str = raw.get("page_name") or "Unknown"
        state: dict = raw.get("state") or {}
        objects: list = raw.get("objects") or []
        pending_cards: list = raw.get("pending_cards") or []

        base, zone, pos, _swap = parse_action_label(action_label)

        # SWAP synthesis: insert adjacent transpositions if joker order changed
        cur_joker_order = _joker_class_ids(objects)
        if (
            prev_joker_order is not None
            and base not in {"SWAP", "StartNewRun"}
        ):
            for i, j in _adjacent_swaps_needed(prev_joker_order, cur_joker_order):
                gran_steps.append(_make_step(
                    step_id=step_id,
                    page_name=page_name,
                    source_event_index=event_idx,
                    source_action=prev_action,
                    action=f"SWAP_{i}_{j}",
                    target_zone=None,
                    target_position=None,
                    swap_pair=[i, j],
                    state=state,
                    objects=objects,
                    pending_cards=pending_cards,
                ))
                step_id += 1

        gran_steps.append(_make_step(
            step_id=step_id,
            page_name=page_name,
            source_event_index=event_idx,
            source_action=prev_action,
            action=action_label,
            target_zone=zone,
            target_position=pos,
            swap_pair=None,
            state=state,
            objects=objects,
            pending_cards=pending_cards,
        ))
        step_id += 1
        prev_joker_order = cur_joker_order
        prev_action = action_label

    # Compute persistent_state (state BEFORE each step) using state_reducer
    ps_states: list[dict] = []
    running_state = default_state()
    for step in gran_steps:
        ps_states.append(dict(running_state))
        running_state = apply_step(running_state, step)

    video_id = f"live_{run_id}"

    # Write granularized run
    gran_dir = gran_root / f"video_id={video_id}"
    gran_dir.mkdir(parents=True, exist_ok=True)
    gran_path = gran_dir / "run_000.json"
    gran_doc: dict[str, Any] = {
        "schema_version": GRANULARIZE_SCHEMA_VERSION,
        "video_id": video_id,
        "run_index": 0,
        "source": "live_recording",
        "run_id": run_id,
        "outcome": outcome,
        "events": gran_steps,
    }
    gran_path.write_text(json.dumps(gran_doc, ensure_ascii=False), encoding="utf-8")

    # Write persistent_state
    ps_dir = pstate_root / f"video_id={video_id}"
    ps_dir.mkdir(parents=True, exist_ok=True)
    ps_path = ps_dir / "run_000.json"
    ps_doc: dict[str, Any] = {
        "video_id": video_id,
        "run_index": 0,
        "schema_version": PERSISTENT_STATE_SCHEMA_VERSION,
        "state_reducer_version": STATE_REDUCER_VERSION,
        "n_steps": len(gran_steps),
        "model_visible_keys": sorted(MODEL_VISIBLE_KEYS),
        "internal_keys": sorted(INTERNAL_KEYS),
        "states": ps_states,
    }
    ps_path.write_text(json.dumps(ps_doc, ensure_ascii=False), encoding="utf-8")

    n_swaps = len(gran_steps) - len(raw_steps)
    print(
        f"  {run_id}: {len(raw_steps)} events -> {len(gran_steps)} steps "
        f"(+{n_swaps} SWAPs)  outcome={outcome}"
    )
    return True


# ---------------------------------------------------------------------------
# CLI
# ---------------------------------------------------------------------------

def main(argv: list[str] | None = None) -> None:
    ap = argparse.ArgumentParser(
        description=__doc__,
        formatter_class=argparse.RawDescriptionHelpFormatter,
    )
    ap.add_argument(
        "--sessions",
        type=Path,
        default=_REPO / "data" / "live_sessions",
        help="Root directory containing <run_id>/ session directories",
    )
    ap.add_argument(
        "--out-prefix",
        type=Path,
        default=_REPO / "data",
        help=(
            "Root prefix for output directories "
            "(granularized → <prefix>/granularized, "
            "persistent_state → <prefix>/persistent_state)"
        ),
    )
    ap.add_argument(
        "--run-id",
        default=None,
        help="Process only this run_id (default: all sessions under --sessions)",
    )
    ap.add_argument(
        "--skip-unlabeled",
        action="store_true",
        help="Skip sessions whose session.json has outcome=null",
    )
    args = ap.parse_args(argv)

    gran_root = args.out_prefix / "granularized"
    pstate_root = args.out_prefix / "persistent_state"
    sessions_root: Path = args.sessions

    if not sessions_root.exists():
        print(f"Sessions directory not found: {sessions_root}")
        return

    if args.run_id:
        dirs = [sessions_root / args.run_id]
    else:
        dirs = sorted(p for p in sessions_root.iterdir() if p.is_dir())

    if not dirs:
        print("No session directories found.")
        return

    print(f"Converting {len(dirs)} session(s)...")
    n_ok = sum(
        convert_session(d, gran_root, pstate_root, skip_unlabeled=args.skip_unlabeled)
        for d in dirs
    )
    print(f"Done: {n_ok}/{len(dirs)} sessions written.")
    if n_ok:
        print(f"\nNext steps:")
        print(f"  python policy/label_outcomes.py --summary")
        print(f"  python policy/tensorize_oc.py --outcomes policy/data/outcomes.json \\")
        print(f"      --src data/granularized --persistent data/persistent_state \\")
        print(f"      --out data/tensorized_oc")


if __name__ == "__main__":
    main()
