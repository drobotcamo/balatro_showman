"""Minimal repository-side client for the Balatro file-IPC bridge contract."""

from __future__ import annotations

import argparse
import hashlib
import json
import math
import os
import sys
import time
from datetime import datetime, timezone
from pathlib import Path
from typing import Any


OUTCOMES = {"win", "loss"}


def _atomic_write(path: Path, text: str) -> None:
    temporary = path.with_name(path.name + ".tmp")
    with temporary.open("w", encoding="utf-8", newline="") as stream:
        stream.write(text)
        stream.flush()
        os.fsync(stream.fileno())
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
    """Persist queued snapshots before acknowledging them by request removal."""

    def __init__(self, io_dir: Path, out_dir: Path, action: str | None = None,
                 bundle_db: str | None = None) -> None:
        self.io_dir = io_dir
        self.out_dir = out_dir
        self.action = action
        self._bundle_db = bundle_db
        self.snapshot_path = io_dir / "snapshot.json"
        self.action_path = io_dir / "action.txt"
        self.run_end_path = io_dir / "run_end.json"
        self.recording_marker_path = io_dir / "recording_start_marker.json"
        self._seen_requests: set[str] = set()
        self._request_actions: dict[str, str] = {}
        self._request_runs: dict[str, str] = {}
        self._sessions: dict[str, dict[str, Any]] = {}
        self._finalized_sessions: set[str] = set()
        self._finalized_session_data: dict[str, dict[str, Any]] = {}
        self._attached_recording_ids: set[str] = set()
        self._recording_marker: dict[str, Any] | None = None
        self._capture_diagnostics: dict[str, list[dict[str, Any]]] = {}
        self._imported_sessions: set[str] = set()
        self._import_conflicts: dict[str, str] = {}
        self._import_retry_after: dict[str, float] = {}
        self._recover_sessions()

    def _recover_sessions(self) -> None:
        """Rebuild deduplication state from durable session/step files."""
        if not self.out_dir.exists():
            return
        for session_path in self.out_dir.glob("*/session.json"):
            try:
                session = json.loads(session_path.read_text(encoding="utf-8"))
                run_id = str(session["run_id"])
                session["session_dir"] = session_path.parent
                session["usage"] = {
                    "action_counts": {},
                    "unique_action_count": 0,
                    "first_recorded_at": None,
                    "last_recorded_at": None,
                }
                if session.get("outcome") is None and session.get("lifecycle_status") != "incomplete":
                    self._sessions[run_id] = session
                else:
                    self._finalized_sessions.add(run_id)
                    self._finalized_session_data[run_id] = session
                recording = session.get("recording")
                if isinstance(recording, dict) and isinstance(recording.get("recording_id"), str):
                    self._attached_recording_ids.add(recording["recording_id"])
                diagnostics_path = session_path.parent / "capture_diagnostics.ndjson"
                if diagnostics_path.exists():
                    self._load_capture_diagnostics(run_id, diagnostics_path)
                steps_path = session_path.parent / "steps.ndjson"
                raw = steps_path.read_bytes() if steps_path.exists() else b""
                valid_records: list[bytes] = []
                bad_tail: bytes | None = None
                previous_request_id = 0
                for line in raw.splitlines(keepends=True):
                    try:
                        record = json.loads(line.decode("utf-8"))
                        if not line.endswith(b"\n"):
                            raise ValueError("truncated NDJSON record")
                        if not isinstance(record, dict):
                            raise ValueError("NDJSON record must be an object")
                        if "request_id" not in record or "_recorded_action" not in record:
                            raise ValueError("NDJSON record lacks request_id or recorded action")
                    except (UnicodeDecodeError, json.JSONDecodeError, ValueError):
                        bad_tail = b"".join(raw[len(b"".join(valid_records)):].splitlines(keepends=True))
                        break
                    valid_records.append(line)
                    request_id = str(record["request_id"])
                    try:
                        numeric_id = int(request_id)
                    except ValueError:
                        numeric_id = None
                    if numeric_id is not None and numeric_id > previous_request_id + 1:
                        self._add_capture_diagnostic(run_id, {
                            "code": "request_id_gap",
                            "previous_request_id": previous_request_id,
                            "current_request_id": numeric_id,
                            "missing_count": numeric_id - previous_request_id - 1,
                            "cause": "unknown_possible_overwrite_or_consumer_delay",
                        })
                    if numeric_id is not None:
                        previous_request_id = numeric_id
                    key = f"{run_id}\x00{request_id}"
                    self._seen_requests.add(key)
                    self._request_actions[key] = record["_recorded_action"]
                    self._request_runs[key] = run_id
                    recorded_at = record.get("_recorded_at")
                    if isinstance(recorded_at, str):
                        self._record_usage(session, str(record["_recorded_action"]), recorded_at)
                    else:
                        # Older step files still receive action counts, but do
                        # not get invented timestamps.
                        counts = session["usage"]["action_counts"]
                        action = str(record["_recorded_action"])
                        if action not in counts:
                            counts[action] = 0
                            session["usage"]["unique_action_count"] += 1
                        counts[action] += 1
                if bad_tail is not None:
                    corrupt_path = steps_path.with_name("steps.ndjson.corrupt")
                    suffix = 1
                    while corrupt_path.exists():
                        corrupt_path = steps_path.with_name(f"steps.ndjson.corrupt.{suffix}")
                        suffix += 1
                    self._write_bytes_durable(corrupt_path, bad_tail)
                    self._add_capture_diagnostic(run_id, {
                        "code": "invalid_ndjson_tail_quarantined",
                        "path": corrupt_path.name,
                        "byte_count": len(bad_tail),
                        "sha256": hashlib.sha256(bad_tail).hexdigest(),
                        "cause": "unknown_incomplete_or_malformed_record",
                    })
                    _atomic_write(steps_path, b"".join(valid_records).decode("utf-8"))
                actual_steps = len(valid_records)
                if session.get("n_steps") != actual_steps:
                    self._add_capture_diagnostic(run_id, {
                        "code": "session_step_count_recovered",
                        "declared_count": session.get("n_steps"),
                        "recovered_count": actual_steps,
                        "cause": "session_count_reconciled_to_valid_persisted_records",
                    })
                    session["n_steps"] = actual_steps
                    self._write_session(session)
                else:
                    self._write_session(session)
                if self._capture_diagnostics.get(run_id):
                    self._write_capture_diagnostics(session["session_dir"], run_id)
            except (OSError, UnicodeDecodeError, json.JSONDecodeError, KeyError, TypeError):
                # Do not start consuming queued requests when durable state
                # could not be reconstructed; that could duplicate evidence.
                raise

    def _load_capture_diagnostics(self, run_id: str, path: Path) -> None:
        raw = path.read_bytes()
        valid_lines: list[bytes] = []
        corrupt_tail: bytes | None = None
        for line in raw.splitlines(keepends=True):
            try:
                item = json.loads(line.decode("utf-8"))
                if not isinstance(item, dict) or not line.endswith(b"\n"):
                    raise ValueError("invalid diagnostic record")
            except (UnicodeDecodeError, json.JSONDecodeError, ValueError):
                corrupt_tail = raw[len(b"".join(valid_lines)):]
                break
            valid_lines.append(line)
            self._add_capture_diagnostic(run_id, item)
        if corrupt_tail is not None:
            corrupt_path = path.with_name(path.name + ".corrupt")
            suffix = 1
            while corrupt_path.exists():
                corrupt_path = path.with_name(f"{path.name}.corrupt.{suffix}")
                suffix += 1
            self._write_bytes_durable(corrupt_path, corrupt_tail)
            _atomic_write(path, b"".join(valid_lines).decode("utf-8"))

    @staticmethod
    def _write_bytes_durable(path: Path, raw: bytes) -> None:
        with path.open("xb") as stream:
            stream.write(raw)
            stream.flush()
            os.fsync(stream.fileno())

    def _append_step_durable(self, steps_path: Path, record: dict[str, Any], session: dict[str, Any]) -> None:
        original_size = steps_path.stat().st_size if steps_path.exists() else 0
        try:
            with steps_path.open("a", encoding="utf-8") as stream:
                stream.write(json.dumps(record, separators=(",", ":")) + "\n")
                stream.flush()
                os.fsync(stream.fileno())
        except OSError:
            try:
                partial = steps_path.read_bytes()[original_size:] if steps_path.exists() else b""
                if partial:
                    corrupt_path = steps_path.with_name("steps.ndjson.corrupt")
                    suffix = 1
                    while corrupt_path.exists():
                        corrupt_path = steps_path.with_name(f"steps.ndjson.corrupt.{suffix}")
                        suffix += 1
                    self._write_bytes_durable(corrupt_path, partial)
                    with steps_path.open("r+b") as stream:
                        stream.truncate(original_size)
                        stream.flush()
                        os.fsync(stream.fileno())
                    self._add_capture_diagnostic(str(session["run_id"]), {
                        "code": "failed_append_bytes_quarantined",
                        "path": corrupt_path.name,
                        "byte_count": len(partial),
                        "sha256": hashlib.sha256(partial).hexdigest(),
                    })
                    self._write_capture_diagnostics(session["session_dir"], str(session["run_id"]))
            except OSError:
                # The queued source remains unacknowledged; startup recovery
                # will retain and diagnose any incomplete steps tail.
                pass
            raise

    def _attach_recording_marker(self) -> None:
        marker = self._recording_marker
        if self.recording_marker_path.exists():
            try:
                marker = json.loads(self.recording_marker_path.read_text(encoding="utf-8"))
            except (OSError, UnicodeDecodeError, json.JSONDecodeError):
                try:
                    os.replace(self.recording_marker_path, self._quarantine_path(self.recording_marker_path))
                except OSError:
                    pass
                return
            if (
                not isinstance(marker, dict)
                or marker.get("schema_version") != "producer/1.0.0"
                or not isinstance(marker.get("recording_id"), str)
                or not marker["recording_id"]
                or not isinstance(marker.get("fps"), (int, float))
                or isinstance(marker.get("fps"), bool)
                or not math.isfinite(marker["fps"])
                or marker["fps"] <= 0
                or not isinstance(marker.get("capture_timestamp_ns"), int)
                or isinstance(marker.get("capture_timestamp_ns"), bool)
                or marker["capture_timestamp_ns"] <= 0
            ):
                self._invalid_input(self.recording_marker_path, "invalid recording_start_marker.json")
            self._recording_marker = marker

    def _read_json(self, path: Path) -> dict[str, Any] | None:
        if not path.exists():
            return None
        try:
            text = path.read_text(encoding="utf-8")
            value = json.loads(text)
        except (OSError, UnicodeDecodeError, json.JSONDecodeError):
            quarantine = self._quarantine_path(path)
            os.replace(path, quarantine)
            return None
        if not isinstance(value, dict):
            os.replace(path, self._quarantine_path(path))
            raise ValueError(f"{path.name} must contain a JSON object")
        return value

    @staticmethod
    def _quarantine_path(path: Path) -> Path:
        candidate = path.with_name(path.name + ".invalid")
        suffix = 1
        while candidate.exists():
            candidate = path.with_name(f"{path.name}.invalid.{suffix}")
            suffix += 1
        return candidate

    def _invalid_input(self, path: Path, message: str) -> None:
        """Retain semantically invalid input for diagnosis before failing."""
        os.replace(path, self._quarantine_path(path))
        raise ValueError(message)

    def _session(self, run_id: str) -> dict[str, Any]:
        session = self._sessions.get(run_id)
        if session is None:
            session_dir = self.out_dir / run_id
            session_dir.mkdir(parents=True, exist_ok=True)
            session = {
                "run_id": run_id,
                "schema_version": "producer/1.0.0",
                "started_at": datetime.now(timezone.utc).isoformat(),
                "ended_at": None,
                "outcome": None,
                "n_steps": 0,
                "usage": {
                    "action_counts": {},
                    "unique_action_count": 0,
                    "first_recorded_at": None,
                    "last_recorded_at": None,
                },
                "session_dir": session_dir,
            }
            if self._recording_marker is not None:
                recording_id = self._recording_marker["recording_id"]
                if recording_id not in self._attached_recording_ids:
                    session["recording"] = self._recording_marker
                    self._attached_recording_ids.add(recording_id)
            self._sessions[run_id] = session
            self._write_session(session)
        return session

    @staticmethod
    def _record_usage(session: dict[str, Any], action: str, recorded_at: str) -> None:
        usage = session.setdefault("usage", {
            "action_counts": {},
            "unique_action_count": 0,
            "first_recorded_at": None,
            "last_recorded_at": None,
        })
        counts = usage.setdefault("action_counts", {})
        if action not in counts:
            usage["unique_action_count"] = int(usage.get("unique_action_count", 0)) + 1
            counts[action] = 0
        counts[action] += 1
        if usage.get("first_recorded_at") is None:
            usage["first_recorded_at"] = recorded_at
        usage["last_recorded_at"] = recorded_at

    def _write_session(self, session: dict[str, Any]) -> None:
        public = {key: value for key, value in session.items() if key != "session_dir"}
        _atomic_write(
            session["session_dir"] / "session.json",
            json.dumps(public, indent=2) + "\n",
        )

    def _write_capture_diagnostics(self, session_dir: Path, run_id: str) -> None:
        diagnostics = self._capture_diagnostics.get(run_id, [])
        if diagnostics:
            _atomic_write(
                session_dir / "capture_diagnostics.ndjson",
                "".join(json.dumps(item, sort_keys=True, separators=(",", ":")) + "\n" for item in diagnostics),
            )

    def _add_capture_diagnostic(self, run_id: str, diagnostic: dict[str, Any]) -> None:
        diagnostics = self._capture_diagnostics.setdefault(run_id, [])
        if diagnostic not in diagnostics:
            diagnostics.append(diagnostic)

    def _diagnose_request_gap(self, session: dict[str, Any], request_id: Any) -> None:
        try:
            current_id = int(request_id)
        except (TypeError, ValueError):
            return
        run_id = str(session["run_id"])
        prior_ids = [
            int(key.split("\x00", 1)[1])
            for key in self._seen_requests
            if key.startswith(run_id + "\x00")
            and key != f"{run_id}\x00{request_id}"
            and key.split("\x00", 1)[1].isdigit()
        ]
        previous_id = max(prior_ids, default=0)
        if current_id > previous_id + 1:
            self._add_capture_diagnostic(run_id, {
                "code": "request_id_gap",
                "previous_request_id": previous_id,
                "current_request_id": current_id,
                "missing_count": current_id - previous_id - 1,
                "cause": "unknown_possible_overwrite_or_consumer_delay",
            })
        self._write_capture_diagnostics(session["session_dir"], run_id)

    def _handle_snapshot(self) -> bool:
        paths = sorted(self.io_dir.glob("request_*.json"))
        if self.snapshot_path.exists():
            paths.append(self.snapshot_path)
        snapshots: list[tuple[Path, dict[str, Any]]] = []
        for path in paths:
            snapshot = self._read_json(path)
            if snapshot is not None:
                snapshots.append((path, snapshot))
        def sort_key(item: tuple[Path, dict[str, Any]]) -> tuple[str, int, Any]:
            meta = item[1].get("meta")
            run_id = str(meta.get("run_id", "")) if isinstance(meta, dict) else ""
            request_id = item[1].get("request_id")
            try:
                return run_id, 0, int(request_id)
            except (TypeError, ValueError):
                return run_id, 1, str(request_id)

        snapshots.sort(key=sort_key)
        did_work = False
        for path, snapshot in snapshots:
            self._process_snapshot(path, snapshot)
            did_work = True
        return did_work

    def _process_snapshot(self, input_path: Path, snapshot: dict[str, Any]) -> None:
        if input_path.name.startswith("request_") and snapshot.get("ipc_schema_version") != "file-queue/1.0.0":
            self._invalid_input(input_path, f"{input_path.name} requires ipc_schema_version file-queue/1.0.0")
        request_id = snapshot.get("request_id")
        if (isinstance(request_id, bool)
                or not isinstance(request_id, (int, str))
                or not str(request_id).isdigit()
                or int(request_id) < 1):
            self._invalid_input(input_path, f"{input_path.name} requires a positive integer request_id")
        request_id = int(request_id)
        meta = snapshot.get("meta")
        if not isinstance(meta, dict) or not isinstance(meta.get("run_id"), str) or not meta["run_id"]:
            self._invalid_input(input_path, f"{input_path.name} requires meta.run_id")
        run_id = str(meta["run_id"])
        request_key = f"{run_id}\x00{request_id}"
        if request_key in self._seen_requests:
            session = self._sessions.get(run_id) or self._finalized_session_data[run_id]
            self._write_session(session)
            self._write_capture_diagnostics(session["session_dir"], run_id)
            _atomic_write(self.action_path, f"{request_id}\t{self._request_actions[request_key]}\n")
            input_path.unlink(missing_ok=True)
            return
        if run_id in self._finalized_sessions:
            self._invalid_input(
                input_path,
                f"snapshot received after run {run_id!r} was finalized; evidence retained in quarantine",
            )

        action = snapshot.get("action_taken") or self.action
        legal_actions = snapshot.get("legal_actions")
        if not isinstance(action, str) or not action:
            self._invalid_input(input_path, f"an action is required via {input_path.name}.action_taken or --action")
        if isinstance(legal_actions, list) and legal_actions and action not in legal_actions:
            self._invalid_input(input_path, f"action {action!r} is not in legal_actions")
        session = self._session(run_id)
        recorded_at = datetime.now(timezone.utc).isoformat()
        record = {**snapshot, "_recorded_action": action, "_recorded_at": recorded_at}
        self._append_step_durable(session["session_dir"] / "steps.ndjson", record, session)
        self._seen_requests.add(request_key)
        self._request_actions[request_key] = action
        self._request_runs[request_key] = run_id
        session["n_steps"] += 1
        self._record_usage(session, action, recorded_at)
        self._diagnose_request_gap(session, request_id)
        self._write_session(session)
        _atomic_write(self.action_path, f"{request_id}\t{action}\n")
        input_path.unlink(missing_ok=True)

    def _has_complete_requests(self, run_id: str, last_request_id: int) -> bool:
        request_ids = {
            int(key.split("\x00", 1)[1]) for key in self._seen_requests
            if key.startswith(run_id + "\x00") and key.split("\x00", 1)[1].isdigit()
            and 1 <= int(key.split("\x00", 1)[1]) <= last_request_id
        }
        if last_request_id == 0:
            return True
        return len(request_ids) == last_request_id and min(request_ids, default=0) == 1 and max(request_ids, default=0) == last_request_id

    def _handle_run_end(self) -> bool:
        paths = sorted(self.io_dir.glob("run_end_*.json"))
        if self.run_end_path.exists():
            paths.append(self.run_end_path)
        did_work = False
        for path in paths:
            signal = self._read_json(path)
            if signal is None:
                continue
            did_work = self._process_run_end(path, signal) or did_work
        return did_work

    def _process_run_end(self, signal_path: Path, signal: dict[str, Any]) -> bool:
        if signal_path != self.run_end_path and signal.get("ipc_schema_version") != "file-queue/1.0.0":
            self._invalid_input(signal_path, f"{signal_path.name} requires ipc_schema_version file-queue/1.0.0")
        outcome = signal.get("outcome")
        if outcome not in OUTCOMES:
            self._invalid_input(signal_path, f"{signal_path.name} outcome must be 'win' or 'loss'")
        run_id = signal.get("run_id")
        if signal_path != self.run_end_path and not isinstance(run_id, str):
            self._invalid_input(signal_path, f"{signal_path.name} requires run_id")
        targets = [str(run_id)] if run_id is not None else list(self._sessions)
        watermark = signal.get("last_request_id")
        if watermark is not None and (
            not isinstance(watermark, int) or isinstance(watermark, bool) or watermark < 0
        ):
            self._invalid_input(signal_path, f"{signal_path.name} has invalid last_request_id")
        if watermark is not None and run_id is not None:
            run_id = str(run_id)
            targets = [run_id]
            if run_id not in self._sessions and run_id not in self._finalized_sessions and watermark == 0:
                self._session(run_id)
            if run_id not in self._finalized_sessions and not self._has_complete_requests(run_id, watermark):
                session = self._sessions.get(run_id)
                if session is not None:
                    present = {
                        int(key.split("\x00", 1)[1]) for key in self._seen_requests
                        if key.startswith(run_id + "\x00") and key.split("\x00", 1)[1].isdigit()
                        and 1 <= int(key.split("\x00", 1)[1]) <= watermark
                    }
                    missing = []
                    candidate = 1
                    while candidate <= watermark and len(missing) < 32:
                        if candidate not in present:
                            missing.append(candidate)
                        candidate += 1
                    self._add_capture_diagnostic(run_id, {
                        "code": "terminal_requests_pending",
                        "last_request_id": watermark,
                        "missing_count": watermark - len(present),
                        "missing_request_ids": missing,
                    })
                    self._write_capture_diagnostics(session["session_dir"], run_id)
                return False
            session = self._sessions.get(run_id)
            if session is not None:
                changed = False
                for diagnostic in self._capture_diagnostics.get(run_id, []):
                    if (diagnostic.get("code") == "terminal_requests_pending"
                            and diagnostic.get("last_request_id") == watermark
                            and not diagnostic.get("resolved", False)):
                        diagnostic["resolved"] = True
                        changed = True
                if changed:
                    self._write_capture_diagnostics(session["session_dir"], run_id)
        if not any(target in self._sessions for target in targets):
            if targets and all(target in self._finalized_sessions for target in targets):
                signal_path.unlink(missing_ok=True)
                return True
            return False
        for target in targets:
            session = self._sessions.get(target)
            if session is None:
                continue
            if watermark is None:
                self._add_capture_diagnostic(target, {
                    "code": "terminal_watermark_missing",
                    "cause": "legacy_run_end_cannot_prove_queue_completeness",
                })
                self._write_capture_diagnostics(session["session_dir"], target)
            producer_errors = signal.get("producer_write_failures", 0)
            if isinstance(producer_errors, int) and producer_errors > 0:
                self._add_capture_diagnostic(target, {
                    "code": "producer_request_write_failures",
                    "count": producer_errors,
                    "capture_completeness": "incomplete",
                })
                self._write_capture_diagnostics(session["session_dir"], target)
            session["outcome"] = outcome
            session["lifecycle_status"] = {"win": "won", "loss": "lost"}[outcome]
            session["ended_at"] = datetime.now(timezone.utc).isoformat()
            self._write_session(session)
            del self._sessions[target]
            self._finalized_sessions.add(target)
            self._finalized_session_data[target] = session
        signal_path.unlink(missing_ok=True)
        return True

    def step_once(self) -> bool:
        self._attach_recording_marker()
        did_work = self._handle_snapshot()
        did_work = self._handle_run_end() or did_work
        return self._retry_pending_imports() or did_work

    def _retry_pending_imports(self) -> bool:
        if self._bundle_db is None:
            return False
        from sqlalchemy.exc import SQLAlchemyError
        from run_bundle.repository import BundleError, ImportConflict, RunBundle

        now = time.monotonic()
        did_work = False
        for run_id, session in sorted(self._finalized_session_data.items()):
            if (run_id in self._imported_sessions or run_id in self._import_conflicts
                    or now < self._import_retry_after.get(run_id, 0)):
                continue
            source = Path(session["session_dir"])
            bundle = None
            try:
                bundle = RunBundle(self._bundle_db)
                result = bundle.import_oracle_directory(source)
            except ImportConflict as error:
                self._import_conflicts[run_id] = str(error)
                print(f"[file_ipc_bridge] import conflict for run {run_id}: {error}", file=sys.stderr)
                continue
            except (OSError, ValueError, BundleError, SQLAlchemyError) as error:
                self._import_retry_after[run_id] = now + 5.0
                print(f"[file_ipc_bridge] import pending for run {run_id}: {error}", file=sys.stderr)
                continue
            finally:
                if bundle is not None:
                    bundle.close()
            self._imported_sessions.add(run_id)
            self._import_retry_after.pop(run_id, None)
            print(f"[file_ipc_bridge] imported run {run_id} into RunBundle ({result['record_count']} records)")
            did_work = True
        return did_work

    def open_sessions(self) -> dict[str, dict[str, Any]]:
        """Sessions recorded but not yet finalized by a run_end signal."""
        return dict(self._sessions)

    def _report(self) -> None:
        for run_id, session in sorted(self.open_sessions().items()):
            print(
                f"[file_ipc_bridge] run {run_id} interrupted before run_end "
                f"({session['n_steps']} steps recorded, outcome pending)"
            )
        for run_id, session in sorted(self._finalized_session_data.items()):
            if session.get("lifecycle_status") == "incomplete":
                print(f"[file_ipc_bridge] run {run_id} marked incomplete ({session['n_steps']} steps recorded, outcome unknown)")
        for run_id, message in sorted(self._import_conflicts.items()):
            print(f"[file_ipc_bridge] import conflict for run {run_id}: {message}", file=sys.stderr)
        print("[file_ipc_bridge] stopped cleanly (Ctrl+C)")

    def _mark_open_sessions_incomplete(self) -> None:
        for run_id, session in list(self._sessions.items()):
            # Leave queued work recoverable if either a producer request or a
            # terminal signal is still waiting to be consumed.
            pending_paths = list(self.io_dir.glob("request_*.json"))
            if self.snapshot_path.exists():
                pending_paths.append(self.snapshot_path)
            pending_paths.extend(self.io_dir.glob("run_end_*.json"))
            if self.run_end_path.exists():
                pending_paths.append(self.run_end_path)
            pending = False
            for path in pending_paths:
                try:
                    item = json.loads(path.read_text(encoding="utf-8"))
                except (OSError, UnicodeDecodeError, json.JSONDecodeError):
                    continue
                if path.name.startswith("run_end"):
                    if item.get("run_id") in (None, run_id):
                        pending = True
                        break
                else:
                    meta = item.get("meta")
                    if isinstance(meta, dict) and meta.get("run_id") == run_id:
                        request_id = str(item.get("request_id", ""))
                        if f"{run_id}\x00{request_id}" not in self._seen_requests:
                            pending = True
                            break
            if pending:
                continue
            session["lifecycle_status"] = "incomplete"
            session["ended_at"] = datetime.now(timezone.utc).isoformat()
            self._write_session(session)
            del self._sessions[run_id]
            self._finalized_sessions.add(run_id)
            self._finalized_session_data[run_id] = session

    def serve(self, timeout: float | None = None) -> None:
        self.io_dir.mkdir(parents=True, exist_ok=True)
        self.out_dir.mkdir(parents=True, exist_ok=True)
        deadline = None if timeout is None else time.monotonic() + timeout
        try:
            while deadline is None or time.monotonic() < deadline:
                if not self.step_once():
                    time.sleep(0.02)
        except KeyboardInterrupt:
            self._mark_open_sessions_incomplete()
            self._retry_pending_imports()
        self._report()


def _default_io_dir() -> Path:
    if sys.platform == "win32":
        return Path(os.environ.get("APPDATA", "")) / "Balatro" / "agent_io"
    return Path.home() / ".local" / "share" / "love" / "Balatro" / "agent_io"


def build_parser(*, add_help=True):
    parser = argparse.ArgumentParser(description=__doc__, add_help=add_help)
    parser.add_argument("--io-dir", type=Path, default=_default_io_dir())
    parser.add_argument("--out-dir", type=Path, required=True)
    parser.add_argument("--bundle-db", help="migrated SQLite RunBundle database for automatic import")
    parser.add_argument("--action", help="Safe smoke-test action when the snapshot has no action_taken")
    parser.add_argument("--timeout", type=float)
    parser.add_argument("--once", action="store_true")
    return parser


def main(argv=None) -> None:
    args = build_parser().parse_args(argv)
    bridge = FileIpcBridge(args.io_dir, args.out_dir, args.action, args.bundle_db)
    if args.once:
        bridge.io_dir.mkdir(parents=True, exist_ok=True)
        bridge.out_dir.mkdir(parents=True, exist_ok=True)
        bridge.step_once()
    else:
        bridge.serve(args.timeout)


if __name__ == "__main__":
    main()
