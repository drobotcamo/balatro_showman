"""Minimal repository-side client for the Balatro file-IPC bridge contract."""

from __future__ import annotations

import argparse
import json
import os
import sys
import time
from datetime import datetime, timezone
from pathlib import Path
from typing import Any


OUTCOMES = {"win", "loss"}


def _atomic_write(path: Path, text: str) -> None:
    temporary = path.with_name(path.name + ".tmp")
    temporary.write_text(text, encoding="utf-8")
    last_error: OSError | None = None
    for attempt in range(10):
        try:
            os.replace(temporary, path)
            return
        except OSError as error:
            last_error = error
            time.sleep(0.01 * (attempt + 1))
    temporary.unlink(missing_ok=True)
    if last_error is not None:
        raise last_error


class FileIpcBridge:
    """Record snapshots while acknowledging each one through action.txt."""

    def __init__(self, io_dir: Path, out_dir: Path, action: str | None = None) -> None:
        self.io_dir = io_dir
        self.out_dir = out_dir
        self.action = action
        self.snapshot_path = io_dir / "snapshot.json"
        self.action_path = io_dir / "action.txt"
        self.run_end_path = io_dir / "run_end.json"
        self._seen_requests: set[str] = set()
        self._request_actions: dict[str, str] = {}
        self._request_runs: dict[str, str] = {}
        self._sessions: dict[str, dict[str, Any]] = {}

    def _read_json(self, path: Path) -> dict[str, Any] | None:
        if not path.exists():
            return None
        try:
            text = path.read_text(encoding="utf-8")
            value = json.loads(text)
        except (OSError, UnicodeDecodeError, json.JSONDecodeError):
            path.unlink(missing_ok=True)
            return None
        path.unlink()
        if not isinstance(value, dict):
            raise ValueError(f"{path.name} must contain a JSON object")
        return value

    def _session(self, run_id: str) -> dict[str, Any]:
        session = self._sessions.get(run_id)
        if session is None:
            session_dir = self.out_dir / run_id
            session_dir.mkdir(parents=True, exist_ok=True)
            session = {
                "run_id": run_id,
                "schema_version": "record/1.0.0",
                "started_at": datetime.now(timezone.utc).isoformat(),
                "ended_at": None,
                "outcome": None,
                "n_steps": 0,
                "session_dir": session_dir,
            }
            self._sessions[run_id] = session
            self._write_session(session)
        return session

    def _write_session(self, session: dict[str, Any]) -> None:
        public = {key: value for key, value in session.items() if key != "session_dir"}
        _atomic_write(
            session["session_dir"] / "session.json",
            json.dumps(public, indent=2) + "\n",
        )

    def _handle_snapshot(self) -> bool:
        snapshot = self._read_json(self.snapshot_path)
        if snapshot is None:
            return False
        request_id = snapshot.get("request_id")
        if request_id is None:
            raise ValueError("snapshot.json requires request_id")
        request_key = str(request_id)
        if request_key in self._seen_requests:
            _atomic_write(self.action_path, f"{request_id}\t{self._request_actions[request_key]}\n")
            return True

        meta = snapshot.get("meta")
        if not isinstance(meta, dict) or meta.get("run_id") is None:
            raise ValueError("snapshot.json requires meta.run_id")
        run_id = str(meta["run_id"])
        action = snapshot.get("action_taken") or self.action
        legal_actions = snapshot.get("legal_actions")
        if not isinstance(action, str) or not action:
            raise ValueError("an action is required via snapshot.action_taken or --action")
        if isinstance(legal_actions, list) and legal_actions and action not in legal_actions:
            raise ValueError(f"action {action!r} is not in legal_actions")
        self._seen_requests.add(request_key)
        self._request_actions[request_key] = action
        self._request_runs[request_key] = run_id

        session = self._session(run_id)
        record = {**snapshot, "_recorded_action": action}
        with (session["session_dir"] / "steps.ndjson").open("a", encoding="utf-8") as stream:
            stream.write(json.dumps(record, separators=(",", ":")) + "\n")
        session["n_steps"] += 1
        self._write_session(session)
        _atomic_write(self.action_path, f"{request_id}\t{action}\n")
        return True

    def _handle_run_end(self) -> bool:
        signal = self._read_json(self.run_end_path)
        if signal is None:
            return False
        outcome = signal.get("outcome")
        if outcome not in OUTCOMES:
            raise ValueError("run_end.json outcome must be 'win' or 'loss'")
        run_id = signal.get("run_id")
        targets = [str(run_id)] if run_id is not None else list(self._sessions)
        for target in targets:
            session = self._sessions.get(target)
            if session is None:
                continue
            session["outcome"] = outcome
            session["ended_at"] = datetime.now(timezone.utc).isoformat()
            self._write_session(session)
            del self._sessions[target]
            request_ids = [request for request, owner in self._request_runs.items() if owner == target]
            for request in request_ids:
                self._seen_requests.remove(request)
                del self._request_actions[request]
                del self._request_runs[request]
        return True

    def step_once(self) -> bool:
        did_work = self._handle_run_end()
        return self._handle_snapshot() or did_work

    def serve(self, timeout: float | None = None) -> None:
        self.io_dir.mkdir(parents=True, exist_ok=True)
        self.out_dir.mkdir(parents=True, exist_ok=True)
        deadline = None if timeout is None else time.monotonic() + timeout
        while deadline is None or time.monotonic() < deadline:
            if not self.step_once():
                time.sleep(0.02)


def _default_io_dir() -> Path:
    if sys.platform == "win32":
        return Path(os.environ.get("APPDATA", "")) / "Balatro" / "agent_io"
    return Path.home() / ".local" / "share" / "love" / "Balatro" / "agent_io"


def main() -> None:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--io-dir", type=Path, default=_default_io_dir())
    parser.add_argument("--out-dir", type=Path, required=True)
    parser.add_argument("--action", help="Safe smoke-test action when the snapshot has no action_taken")
    parser.add_argument("--timeout", type=float)
    parser.add_argument("--once", action="store_true")
    args = parser.parse_args()
    bridge = FileIpcBridge(args.io_dir, args.out_dir, args.action)
    if args.once:
        bridge.io_dir.mkdir(parents=True, exist_ok=True)
        bridge.out_dir.mkdir(parents=True, exist_ok=True)
        bridge.step_once()
    else:
        bridge.serve(args.timeout)


if __name__ == "__main__":
    main()
