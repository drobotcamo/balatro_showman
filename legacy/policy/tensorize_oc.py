#!/usr/bin/env python3
"""
tensorize_oc.py
===============
Outcome-conditioned fork of balatro-policy-transformer/tensorize.py.

The only addition: a ``desired_outcome`` float32 scalar is appended to each
step record, broadcast from the run-level win/loss label in outcomes.json.

During training the model sees the true run outcome (0.0 = loss, 1.0 = win).
At inference, always pass 1.0 to elicit winning-run behavior.

All other tensorization logic is unchanged — this file delegates fully to the
upstream module and overrides only the three entry points that need outcome
threading:

  tensorize_step_oc   — adds desired_outcome param, appends field
  _process_run_oc     — adds desired_outcome param, passes through
  main                — loads outcomes.json, routes per-run value

The upstream module is imported from vendor/balatro-policy-transformer via
sys.path injection at the top of this file.

Usage
-----
    python policy/tensorize_oc.py \\
        --outcomes policy/data/outcomes.json \\
        [--src data/granularized] \\
        [--persistent data/persistent_state] \\
        [--out data/tensorized_oc]
"""

from __future__ import annotations

import argparse
import collections
import json
import sys
import time
from datetime import datetime, timezone
from pathlib import Path

import numpy as np

# -- vendor path injection ---------------------------------------------------
_VENDOR = Path(__file__).resolve().parent.parent / "vendor" / "balatro-policy-transformer"
if str(_VENDOR) not in sys.path:
    sys.path.insert(0, str(_VENDOR))

from action_map import compute_action_map  # noqa: E402
from state_reducer import apply_step, default_state, parse_base_action  # noqa: E402
import tensorize as _upstream  # noqa: E402  (for _iter_run_pairs, _stack_step_records)

# Re-export the upstream public API unchanged so callers don't need both imports.
VocabLookup = _upstream.VocabLookup
Normalizer = _upstream.Normalizer
TENSORIZE_SCHEMA_VERSION = _upstream.TENSORIZE_SCHEMA_VERSION
# ---------------------------------------------------------------------------


def tensorize_step_oc(
    step: dict,
    persistent_state: dict,
    action_map: dict,
    vocab: VocabLookup,
    norm: Normalizer,
    feature_config: dict,
    desired_outcome: float = 0.0,
) -> dict[str, np.ndarray]:
    """Encode one step exactly as upstream, then append desired_outcome."""
    out = _upstream.tensorize_step(step, persistent_state, action_map, vocab, norm, feature_config)
    out["desired_outcome"] = np.float32(desired_outcome)
    return out


def _process_run_oc(
    run: dict,
    persistent: dict | None,
    action_map: dict,
    vocab: VocabLookup,
    norm: Normalizer,
    feature_config: dict,
    stats: collections.Counter,
    desired_outcome: float = 0.0,
) -> dict[str, np.ndarray]:
    """Process one run, injecting desired_outcome into every step record."""
    events = run.get("events") or []
    pstates = (persistent or {}).get("states") or []

    if not pstates:
        pstates = []
        s = default_state()
        for ev in events:
            pstates.append(s)
            s = apply_step(s, ev)

    records: list[dict[str, np.ndarray]] = []
    for t, step in enumerate(events):
        ps = _upstream._persistent_state_for_step(pstates, t)
        rec = tensorize_step_oc(step, ps, action_map, vocab, norm, feature_config, desired_outcome)
        records.append(rec)
        if int(rec["target_action_id"]) < 0:
            stats[("target", "unresolved")] += 1
        else:
            stats[("target", "resolved")] += 1
        stats[("event_base", parse_base_action(step.get("action") or ""))] += 1

    return _upstream._stack_step_records(records)


def main() -> None:
    ap = argparse.ArgumentParser(description=__doc__)
    ap.add_argument("--src", type=Path, default=Path("data/granularized"))
    ap.add_argument("--persistent", type=Path, default=Path("data/persistent_state"))
    ap.add_argument("--out", type=Path, default=Path("data/tensorized_oc"))
    ap.add_argument("--outcomes", type=Path, default=Path("policy/data/outcomes.json"),
                    help="Path to outcomes.json from label_outcomes.py")
    ap.add_argument("--vocab", type=Path, default=_VENDOR / "artifacts/vocab.json")
    ap.add_argument("--normalization", type=Path, default=_VENDOR / "artifacts/normalization.json")
    ap.add_argument("--feature-config", type=Path, default=_VENDOR / "artifacts/feature_config.json")
    ap.add_argument("--action-config", type=Path, default=_VENDOR / "data/action_space_config.json")
    ap.add_argument("--report", type=Path, default=Path("policy/data/tensorizer_oc_report.json"))
    args = ap.parse_args()

    vocab = VocabLookup(json.loads(args.vocab.read_text(encoding="utf-8")))
    norm = Normalizer(json.loads(args.normalization.read_text(encoding="utf-8")))
    feature_config = json.loads(args.feature_config.read_text(encoding="utf-8"))
    action_config = json.loads(args.action_config.read_text(encoding="utf-8"))
    action_map = compute_action_map(action_config)

    if not args.outcomes.exists():
        print(f"ERROR: outcomes file not found: {args.outcomes}")
        print("Run policy/label_outcomes.py first.")
        raise SystemExit(1)
    outcomes: dict[str, dict[str, dict]] = json.loads(args.outcomes.read_text(encoding="utf-8"))

    args.out.mkdir(parents=True, exist_ok=True)

    stats: collections.Counter = collections.Counter()
    runs_processed = 0
    steps_processed = 0
    bytes_written = 0
    n_wins = 0
    n_losses = 0
    start = time.time()
    current_video = None

    print(f"N_ACTIONS = {action_map['n_actions']}")
    print(f"outcome conditioning: desired_outcome scalar appended to each step")
    print()

    for video_id, gpath, ppath in _upstream._iter_run_pairs(args.src, args.persistent):
        if video_id != current_video:
            print(f"video_id={video_id}")
            current_video = video_id

        # Look up outcome for this run.
        vid_key = f"video_id={video_id}"
        run_key = gpath.stem  # "run_000"
        outcome_info = outcomes.get(vid_key, {}).get(run_key, {})
        desired_outcome = float(bool(outcome_info.get("won", False)))

        run = json.loads(gpath.read_text(encoding="utf-8"))
        psnap = json.loads(ppath.read_text(encoding="utf-8")) if ppath else None

        record = _process_run_oc(run, psnap, action_map, vocab, norm, feature_config,
                                 stats, desired_outcome=desired_outcome)
        if not record:
            stats[("run", "empty")] += 1
            continue

        dst_dir = args.out / f"video_id={video_id}"
        dst_dir.mkdir(parents=True, exist_ok=True)
        dst_file = dst_dir / gpath.with_suffix(".npz").name
        np.savez_compressed(dst_file, **record)

        runs_processed += 1
        if desired_outcome == 1.0:
            n_wins += 1
        else:
            n_losses += 1
        n_steps = next(iter(record.values())).shape[0]
        steps_processed += n_steps
        sz = dst_file.stat().st_size
        bytes_written += sz
        outcome_tag = "WIN" if desired_outcome == 1.0 else "loss"
        print(f"  {gpath.name} [{outcome_tag}] -> {dst_file.name}  ({n_steps} steps, {sz/1024:.1f} KiB)")

    elapsed = time.time() - start
    print()
    print(f"runs processed:  {runs_processed}  (wins={n_wins}, losses={n_losses})")
    print(f"steps processed: {steps_processed}")
    print(f"bytes written:   {bytes_written/1024/1024:.2f} MiB")
    print(f"elapsed:         {elapsed:.2f}s")
    print()
    print("--- target resolution ---")
    print(f"  resolved:   {stats.get(('target', 'resolved'), 0)}")
    print(f"  unresolved: {stats.get(('target', 'unresolved'), 0)}")

    args.report.parent.mkdir(parents=True, exist_ok=True)
    payload = {
        "schema_version": TENSORIZE_SCHEMA_VERSION,
        "generated_at_utc": datetime.now(timezone.utc).isoformat(),
        "outcome_conditioning": True,
        "src": args.src.as_posix(),
        "out": args.out.as_posix(),
        "n_actions": action_map["n_actions"],
        "runs_processed": runs_processed,
        "n_wins": n_wins,
        "n_losses": n_losses,
        "steps_processed": steps_processed,
        "bytes_written": bytes_written,
        "elapsed_seconds": elapsed,
        "target_resolved": stats.get(("target", "resolved"), 0),
        "target_unresolved": stats.get(("target", "unresolved"), 0),
    }
    args.report.write_text(json.dumps(payload, indent=2, ensure_ascii=False), encoding="utf-8")
    print(f"\nwrote report -> {args.report.as_posix()}")


if __name__ == "__main__":
    main()
