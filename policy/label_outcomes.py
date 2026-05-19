#!/usr/bin/env python3
"""
label_outcomes.py
=================
Infer win/loss outcome for each granularized run and write policy/data/outcomes.json.

Win condition: a CashOut action occurs when OCR ante >= 8. This is only possible
after defeating the final boss blind — the sole Gold Stake win condition.

Runs with fewer than MIN_STEPS steps are flagged as possibly_incomplete. They are
treated as losses but marked so you can exclude them from training if desired.

Usage
-----
    python policy/label_outcomes.py
    python policy/label_outcomes.py --src data/granularized --out policy/data/outcomes.json
    python policy/label_outcomes.py --summary   # print per-video outcome table and exit

Output schema
-------------
{
  "video_id=1": {
    "run_000": {
      "won": false,
      "max_ante": 5,
      "n_steps": 312,
      "possibly_incomplete": false
    },
    ...
  },
  ...
}
"""

from __future__ import annotations

import argparse
import json
from pathlib import Path

MIN_STEPS = 50  # runs shorter than this are flagged as possibly incomplete


def classify_run(events: list[dict]) -> dict:
    """Infer outcome from a list of granularized step dicts."""
    max_ante = 0
    won = False
    for step in events:
        state = step.get("state") or {}
        ante = state.get("ante")
        if isinstance(ante, (int, float)) and not isinstance(ante, bool):
            ante_int = int(ante)
            if ante_int > max_ante:
                max_ante = ante_int
            if ante_int >= 8 and "CashOut" in (step.get("action") or ""):
                won = True
    return {
        "won": won,
        "max_ante": max_ante,
        "n_steps": len(events),
        "possibly_incomplete": len(events) < MIN_STEPS,
    }


def _load_run(path: Path) -> list[dict]:
    payload = json.loads(path.read_text(encoding="utf-8"))
    # granularize.py wraps steps in {"events": [...]}
    if isinstance(payload, dict) and "events" in payload:
        return list(payload["events"])
    # fallback: flat list
    if isinstance(payload, list):
        return payload
    return []


def build_outcomes(granularized_root: Path) -> dict[str, dict[str, dict]]:
    outcomes: dict[str, dict[str, dict]] = {}
    for partition in sorted(granularized_root.iterdir()):
        if not partition.is_dir() or not partition.name.startswith("video_id="):
            continue
        vid_key = partition.name
        outcomes[vid_key] = {}
        for run_file in sorted(partition.glob("run_*.json")):
            run_key = run_file.stem  # "run_000", "run_001", ...
            events = _load_run(run_file)
            outcomes[vid_key][run_key] = classify_run(events)
    return outcomes


def print_summary(outcomes: dict[str, dict[str, dict]]) -> None:
    total_runs = 0
    total_wins = 0
    total_incomplete = 0
    print(f"{'video':<14}  {'run':<10}  {'won':<5}  {'max_ante':<9}  {'steps':<7}  {'incomplete'}")
    print("-" * 65)
    for vid_key in sorted(outcomes):
        for run_key, info in sorted(outcomes[vid_key].items()):
            won_str = "WIN" if info["won"] else "loss"
            inc_str = "!" if info["possibly_incomplete"] else ""
            print(
                f"{vid_key:<14}  {run_key:<10}  {won_str:<5}  "
                f"{info['max_ante']:<9}  {info['n_steps']:<7}  {inc_str}"
            )
            total_runs += 1
            if info["won"]:
                total_wins += 1
            if info["possibly_incomplete"]:
                total_incomplete += 1
    print("-" * 65)
    win_pct = 100 * total_wins / max(total_runs, 1)
    print(f"total runs: {total_runs}  wins: {total_wins} ({win_pct:.1f}%)  incomplete: {total_incomplete}")


def main() -> None:
    ap = argparse.ArgumentParser(description=__doc__)
    ap.add_argument("--src", type=Path, default=Path("data/granularized"),
                    help="Root of granularized data (default: data/granularized)")
    ap.add_argument("--out", type=Path, default=Path("policy/data/outcomes.json"),
                    help="Output path (default: policy/data/outcomes.json)")
    ap.add_argument("--summary", action="store_true",
                    help="Print outcome table to stdout and exit without writing file")
    args = ap.parse_args()

    if not args.src.exists():
        print(f"ERROR: granularized root not found: {args.src}")
        print("Run granularize.py first to generate data/granularized/.")
        raise SystemExit(1)

    outcomes = build_outcomes(args.src)

    if not outcomes:
        print(f"No video_id= partitions found under {args.src}")
        raise SystemExit(1)

    print_summary(outcomes)

    if args.summary:
        return

    args.out.parent.mkdir(parents=True, exist_ok=True)
    args.out.write_text(json.dumps(outcomes, indent=2, ensure_ascii=False), encoding="utf-8")
    print(f"\nwrote {args.out}")


if __name__ == "__main__":
    main()
