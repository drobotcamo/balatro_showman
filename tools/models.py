"""
Trained model registry.

Scans runs/detect/ for trained YOLO26 runs and manages an active-model pointer
stored in .model at the project root.

Usage:
    python main.py models               # list all trained models
    python main.py models use <name>    # set active model
"""

import sys
from pathlib import Path

import yaml

RUNS_DIR = Path("runs/detect")
MODEL_CONFIG = Path(".model")  # stores the active run name


# ── Data helpers ──────────────────────────────────────────────────────────────

def _read_map(run_dir):
    """Read final mAP50 from ultralytics results.csv, or None if unavailable."""
    csv = run_dir / "results.csv"
    if not csv.exists():
        return None
    try:
        lines = csv.read_text().strip().splitlines()
        if len(lines) < 2:
            return None
        headers = [h.strip() for h in lines[0].split(",")]
        values  = [v.strip() for v in lines[-1].split(",")]
        row = dict(zip(headers, values))
        for key in ("metrics/mAP50(B)", "metrics/mAP_0.5", "mAP_0.5"):
            if key in row:
                return float(row[key])
    except Exception:
        pass
    return None


def _read_base_model(run_dir):
    """Read base model name from ultralytics args.yaml."""
    args_path = run_dir / "args.yaml"
    if not args_path.exists():
        return "?"
    try:
        data = yaml.safe_load(args_path.read_text())
        return Path(data.get("model", "?")).name
    except Exception:
        return "?"


def list_models():
    """Return [(name, best_pt, base_model, mAP50), ...] for all trained runs."""
    if not RUNS_DIR.exists():
        return []
    results = []
    for best_pt in sorted(RUNS_DIR.glob("*/weights/best.pt")):
        run_dir = best_pt.parent.parent
        results.append((
            run_dir.name,
            best_pt,
            _read_base_model(run_dir),
            _read_map(run_dir),
        ))
    return results


def get_active():
    """Return the active run name, or None if not set."""
    if MODEL_CONFIG.exists():
        name = MODEL_CONFIG.read_text().strip()
        return name or None
    return None


def set_active(name):
    MODEL_CONFIG.write_text(name)


def resolve_model(model_arg):
    """
    Resolve a --model argument to a Path.

    Accepts:
      - empty string / None  → read from .model config
      - a run name           → runs/detect/<name>/weights/best.pt
      - a .pt file path      → use as-is
    """
    if not model_arg:
        model_arg = get_active()
        if not model_arg:
            return None

    p = Path(model_arg)
    if p.suffix == ".pt":
        return p
    return RUNS_DIR / model_arg / "weights" / "best.pt"


# ── CLI commands ──────────────────────────────────────────────────────────────

def cmd_list():
    models = list_models()
    active = get_active()

    if not models:
        print("No trained models found in runs/detect/")
        print("Train one:  python main.py train --name <name>")
        return

    col = max(len(n) for n, *_ in models) + 2
    header = f"{'NAME':<{col}} {'BASE':<16} {'mAP50':>6}  "
    print(header)
    print("-" * (len(header) + 10))
    for name, _, base, mAP in models:
        mAP_str = f"{mAP:.3f}" if mAP is not None else "  n/a"
        marker = "  <-- active" if name == active else ""
        print(f"{name:<{col}} {base:<16} {mAP_str:>6}{marker}")

    if not active:
        print(f"\nNo active model set. Run: python main.py models use <name>")


def cmd_use(name):
    models = list_models()
    available = [m[0] for m in models]
    if name not in available:
        opts = ", ".join(available) if available else "none trained yet"
        print(f"Model '{name}' not found. Available: {opts}")
        sys.exit(1)
    set_active(name)
    print(f"Active model: {name}")
    print(f"  Path: {resolve_model(name)}")
