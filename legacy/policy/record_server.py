#!/usr/bin/env python3
"""
record_server.py
================
Records live (state, action_taken) pairs for outcome-conditioned training.

Two modes:

  assist (default)
    Load a checkpoint, run inference, write action.txt — AI drives the game.
    Every (snapshot, model_action) pair is saved to disk.
    No Lua bridge changes needed; works with the existing agent_bridge.lua.

  observe
    Do NOT load a model. Expect each snapshot to include an "action_taken"
    field — the human player's choice. Echo the action back in action.txt
    so the Lua bridge advances, and save the (snapshot, action_taken) pair.
    Requires a modified Lua bridge that sets snapshot.action_taken before
    writing snapshot.json. See "Lua bridge notes" below.

Output per run:
  data/live_sessions/<run_id>/steps.ndjson   -- one JSON line per step
  data/live_sessions/<run_id>/session.json   -- run metadata and outcome

After recording, convert to training format:
  python policy/granularize_live.py

Then tensorize and train:
  python policy/tensorize_oc.py --outcomes policy/data/outcomes.json ...
  python policy/train_oc.py ...

Usage
-----
  # AI-driven (needs a trained checkpoint):
  python policy/record_server.py --mode assist --checkpoint path/to/best.pt

  # Human observation (needs modified Lua bridge):
  python policy/record_server.py --mode observe

  # Override Balatro IPC directory:
  python policy/record_server.py --io-dir "C:/custom/path/agent_io"

Lua bridge notes (observe mode)
--------------------------------
In agent_bridge.lua, before writing snapshot.json, add:

    snapshot.action_taken = action_label  -- e.g. "BuyShopItem_TopShelfShopOfferings_0"

The label must match the granularized action format used in legal_actions.

To signal run outcome, write <io_dir>/run_end.json after the run ends:

    { "run_id": <number>, "outcome": "win" }   -- or "loss"

The server finalizes session.json with the outcome on receiving this file.
"""

from __future__ import annotations

import argparse
import json
import os
import sys
import time
from datetime import datetime, timezone
from pathlib import Path
from typing import Any

import torch

_HERE = Path(__file__).resolve().parent
_REPO = _HERE.parent
_VENDOR = _REPO / "vendor" / "balatro-policy-transformer"
for _p in (str(_VENDOR), str(_VENDOR / "live")):
    if _p not in sys.path:
        sys.path.insert(0, _p)

RECORD_SCHEMA_VERSION = "record/1.0.0"


def _default_io_dir() -> Path:
    if sys.platform == "win32":
        return Path(os.environ.get("APPDATA", "")) / "Balatro" / "agent_io"
    if sys.platform == "darwin":
        return Path.home() / "Library" / "Application Support" / "Balatro" / "agent_io"
    return Path.home() / ".local" / "share" / "love" / "Balatro" / "agent_io"


def _default_checkpoint() -> Path:
    for candidate in (
        _REPO / "artifacts" / "checkpoints" / "best.pt",
        _VENDOR / "artifacts" / "checkpoints" / "best.pt",
    ):
        if candidate.exists():
            return candidate
    return _REPO / "artifacts" / "checkpoints" / "best.pt"


def _atomic_write(path: Path, contents: str) -> None:
    tmp = path.with_suffix(path.suffix + ".tmp")
    tmp.write_text(contents, encoding="utf-8")
    last_err: OSError | None = None
    for attempt in range(10):
        if path.exists():
            try:
                path.unlink()
            except OSError as e:
                last_err = e
        try:
            os.replace(tmp, path)
            return
        except OSError as e:
            last_err = e
            time.sleep(0.01 * (attempt + 1))
    try:
        path.write_text(contents, encoding="utf-8")
        tmp.unlink(missing_ok=True)
        return
    except OSError:
        tmp.unlink(missing_ok=True)
        if last_err:
            raise last_err
        raise


# ---------------------------------------------------------------------------
# Session writer
# ---------------------------------------------------------------------------

class SessionWriter:
    """Appends recorded steps to data/live_sessions/<run_id>/steps.ndjson."""

    def __init__(self, run_id: str, out_root: Path) -> None:
        self.run_id = run_id
        self.session_dir = out_root / run_id
        self.session_dir.mkdir(parents=True, exist_ok=True)
        self.steps_path = self.session_dir / "steps.ndjson"
        self.meta_path = self.session_dir / "session.json"
        self._n_steps = 0
        self._fh = self.steps_path.open("a", encoding="utf-8")
        self._meta: dict[str, Any] = {
            "run_id": run_id,
            "schema_version": RECORD_SCHEMA_VERSION,
            "started_at": datetime.now(timezone.utc).isoformat(),
            "ended_at": None,
            "outcome": None,
            "n_steps": 0,
        }
        self._flush_meta()

    def write_step(self, snapshot: dict[str, Any], action_taken: str) -> None:
        record = {**snapshot, "_recorded_action": action_taken}
        self._fh.write(json.dumps(record, ensure_ascii=False) + "\n")
        self._n_steps += 1

    def finalize(self, outcome: str | None = None) -> None:
        self._fh.close()
        self._meta["ended_at"] = datetime.now(timezone.utc).isoformat()
        self._meta["outcome"] = outcome
        self._meta["n_steps"] = self._n_steps
        self._flush_meta()

    def _flush_meta(self) -> None:
        self._meta["n_steps"] = self._n_steps
        self.meta_path.write_text(
            json.dumps(self._meta, indent=2, ensure_ascii=False),
            encoding="utf-8",
        )


# ---------------------------------------------------------------------------
# Record server
# ---------------------------------------------------------------------------

class RecordServer:
    def __init__(
        self,
        mode: str,
        io_dir: Path,
        out_dir: Path,
        checkpoint: Path | None,
        device: torch.device,
        poll_interval_s: float = 0.02,
    ) -> None:
        self.mode = mode
        self.io_dir = io_dir
        self.out_dir = out_dir
        self.snapshot_path = io_dir / "snapshot.json"
        self.action_path = io_dir / "action.txt"
        self.run_end_path = io_dir / "run_end.json"
        self.poll_interval = poll_interval_s
        self.device = device

        self._encoder = None
        self._model = None
        if mode == "assist":
            if checkpoint is None or not checkpoint.exists():
                raise FileNotFoundError(
                    f"assist mode requires a valid checkpoint; not found: {checkpoint}"
                )
            # Lazy import so observe mode doesn't need torch model deps
            from live_encoder import LiveEncoder
            from model import ModelConfig, PolicyTransformer
            self._encoder = LiveEncoder()
            ckpt = torch.load(checkpoint, map_location=device, weights_only=False)
            cfg_dict = ckpt["model_config"]
            cfg = ModelConfig(**{k: v for k, v in cfg_dict.items()
                                 if k in ModelConfig.__dataclass_fields__})
            self._model = PolicyTransformer(cfg).to(device)
            self._model.load_state_dict(ckpt["model_state_dict"])
            self._model.eval()
            print(
                f"[record] loaded {checkpoint.name}  "
                f"epoch={ckpt.get('epoch')} val_top1={ckpt.get('val_top1')}"
            )

        self._sessions: dict[str, SessionWriter] = {}
        self._last_request_id: int | None = None
        self._n_total = 0

    # -- model inference -------------------------------------------------------

    @torch.no_grad()
    def _decide(self, snapshot: dict[str, Any]) -> str:
        import numpy as np
        batch, legal_mask = self._encoder.encode(snapshot, device=self.device)
        logits = self._model(batch)
        probs = torch.softmax(logits, dim=-1).squeeze(0).detach().cpu().numpy()
        idx = int(probs.argmax())
        return self._encoder.label_for_index(idx)

    # -- IPC -------------------------------------------------------------------

    def _read_snapshot(self) -> dict[str, Any] | None:
        if not self.snapshot_path.exists():
            return None
        try:
            text = self.snapshot_path.read_text(encoding="utf-8")
        except (OSError, UnicodeDecodeError):
            return None
        try:
            self.snapshot_path.unlink()
        except OSError:
            pass
        try:
            return json.loads(text)
        except json.JSONDecodeError as e:
            print(f"[record] snapshot parse error: {e}")
            return None

    def _read_run_end(self) -> dict[str, Any] | None:
        if not self.run_end_path.exists():
            return None
        try:
            text = self.run_end_path.read_text(encoding="utf-8")
            self.run_end_path.unlink(missing_ok=True)
            return json.loads(text)
        except Exception:
            return None

    # -- session management ----------------------------------------------------

    def _session_for(self, snapshot: dict[str, Any]) -> SessionWriter:
        meta = snapshot.get("meta") or {}
        raw_id = meta.get("run_id")
        run_id = (
            str(raw_id)
            if raw_id is not None
            else datetime.now(timezone.utc).strftime("%Y%m%d_%H%M%S")
        )
        if run_id not in self._sessions:
            self._sessions[run_id] = SessionWriter(run_id, self.out_dir)
            print(f"[record] new session  run_id={run_id}  dir={self._sessions[run_id].session_dir}")
        return self._sessions[run_id]

    def _handle_run_end(self) -> None:
        signal = self._read_run_end()
        if signal is None:
            return
        raw_id = signal.get("run_id")
        run_id = str(raw_id) if raw_id is not None else None
        outcome = signal.get("outcome")
        targets = (
            {run_id: self._sessions[run_id]}
            if run_id and run_id in self._sessions
            else dict(self._sessions)
        )
        for sid, sess in list(targets.items()):
            sess.finalize(outcome=outcome)
            del self._sessions[sid]
            print(f"[record] run {sid} finalized  outcome={outcome}  steps={sess._n_steps}")

    # -- step ------------------------------------------------------------------

    def step_once(self) -> bool:
        self._handle_run_end()

        snapshot = self._read_snapshot()
        if snapshot is None:
            return False

        req_id = snapshot.get("request_id")
        if req_id is not None and req_id == self._last_request_id:
            return False
        self._last_request_id = req_id

        if self.mode == "assist":
            try:
                action_taken = self._decide(snapshot)
            except Exception as e:
                legal = snapshot.get("legal_actions") or []
                action_taken = legal[0] if legal else "LeaveShop"
                print(f"[record] model error: {e!r} — fallback={action_taken!r}")
        else:  # observe
            action_taken = snapshot.get("action_taken")
            if not action_taken:
                # Bridge hasn't set action_taken yet — skip quietly
                return True

        # Echo action back so the Lua bridge can advance
        _atomic_write(self.action_path, f"{req_id if req_id is not None else 0}\t{action_taken}\n")

        sess = self._session_for(snapshot)
        sess.write_step(snapshot, action_taken)
        self._n_total += 1

        page = snapshot.get("page_name", "?")
        print(f"[record] req={req_id} page={page} -> {action_taken}  (total={self._n_total})")
        return True

    # -- main loop -------------------------------------------------------------

    def serve_forever(self) -> None:
        self.io_dir.mkdir(parents=True, exist_ok=True)
        self.out_dir.mkdir(parents=True, exist_ok=True)
        print(f"[record] mode={self.mode}")
        print(f"[record] watching  {self.snapshot_path}")
        print(f"[record] sessions→ {self.out_dir}")
        print("[record] Press Ctrl+C to stop and finalize sessions.")
        try:
            while True:
                if not self.step_once():
                    time.sleep(self.poll_interval)
        except KeyboardInterrupt:
            print("\n[record] interrupted — finalizing open sessions")
        finally:
            for run_id, sess in list(self._sessions.items()):
                sess.finalize(outcome=None)
                print(f"[record] session {run_id} saved ({sess._n_steps} steps, outcome=unlabeled)")


# ---------------------------------------------------------------------------
# CLI
# ---------------------------------------------------------------------------

def main(argv: list[str] | None = None) -> None:
    ap = argparse.ArgumentParser(
        description=__doc__,
        formatter_class=argparse.RawDescriptionHelpFormatter,
    )
    ap.add_argument(
        "--mode",
        choices=["assist", "observe"],
        default="assist",
        help="assist: AI plays and records; observe: human plays, Lua reports action_taken",
    )
    ap.add_argument(
        "--checkpoint",
        type=Path,
        default=None,
        help="Path to .pt checkpoint (required for assist mode)",
    )
    ap.add_argument(
        "--io-dir",
        type=Path,
        default=None,
        help="Balatro agent_io directory (default: Balatro AppData/agent_io)",
    )
    ap.add_argument(
        "--out-dir",
        type=Path,
        default=_REPO / "data" / "live_sessions",
        help="Where to write session files (default: data/live_sessions)",
    )
    ap.add_argument("--device", default="auto", help="cpu | cuda | directml | auto")
    ap.add_argument("--poll-interval", type=float, default=0.02)
    args = ap.parse_args(argv)

    io_dir = args.io_dir or _default_io_dir()
    checkpoint = args.checkpoint or (_default_checkpoint() if args.mode == "assist" else None)

    if args.device == "auto":
        device = torch.device("cuda" if torch.cuda.is_available() else "cpu")
    else:
        device = torch.device(args.device)

    server = RecordServer(
        mode=args.mode,
        io_dir=io_dir,
        out_dir=args.out_dir,
        checkpoint=checkpoint,
        device=device,
        poll_interval_s=args.poll_interval,
    )
    server.serve_forever()


if __name__ == "__main__":
    main()
