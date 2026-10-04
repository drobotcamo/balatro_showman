import json
import tempfile
import unittest
from datetime import datetime
from pathlib import Path

from ground_truth.file_ipc_bridge import FileIpcBridge, read_mechanics_reference


def _queue_request(io_dir: Path, run_id: str, request_id: int) -> Path:
    path = io_dir / f"request_{run_id}_{request_id:012d}.json"
    path.write_text(json.dumps({
        "ipc_schema_version": "file-queue/1.0.0",
        "request_id": request_id,
        "meta": {"run_id": run_id},
        "action_taken": "SkipBlind",
    }), encoding="utf-8")
    return path


class FileIpcBridgeTests(unittest.TestCase):
    def test_mechanics_reference_is_stored_and_read_outside_observation_steps(self) -> None:
        with tempfile.TemporaryDirectory() as directory:
            root = Path(directory)
            io_dir, out_dir = root / "io", root / "runs"
            io_dir.mkdir()
            snapshot = {
                "ipc_schema_version": "file-queue/1.0.0", "request_id": 1,
                "meta": {"run_id": "dagger-reference"}, "action_taken": "SelectBlind",
                "mechanics_reference": {"schema_version": "dagger-reference/1.0",
                    "step_id": "dagger-reference:1", "capture_phase": "pre_action",
                    "capture_timestamp_ns": 123, "producer_revision": "test",
                    "runtime": {"balatro": "1.0.1", "steamodded": "test", "lovely": "test"}, "jokers": [
                    {"role": "joker", "position": 0, "center_key": "j_dagger",
                     "instance_token": "engine-17", "mult": 62, "sell_cost": 8},
                ]},
            }
            request = io_dir / "request_dagger-reference_000000000001.json"
            request.write_text(json.dumps(snapshot), encoding="utf-8")
            resolved_reference = {
                "schema_version": "dagger-reference/1.0", "run_id": "dagger-reference",
                "step_id": "dagger-reference:1", "capture_phase": "resolved",
                "capture_timestamp_ns": 456, "producer_revision": "test",
                "runtime": {"balatro": "1.0.1", "steamodded": "test", "lovely": "test"},
                "jokers": [{"role": "joker", "position": 0, "center_key": "j_dagger",
                    "instance_token": "engine-17", "mult": 70, "sell_cost": 8}],
                "resolved_effects": [{"trigger": "setting_blind", "dagger_instance_token": "engine-17",
                    "victim_instance_token": "engine-18", "victim_sell_cost_pre": 4,
                    "mult_before": 62, "mult_after": 70, "mult_delta": 8,
                    "pre_capture_timestamp_ns": 123, "resolved_capture_timestamp_ns": 456}],
            }
            resolved_path = io_dir / "mechanics_reference_dagger-reference_000000000001_resolved.json"
            resolved_path.write_text(json.dumps(resolved_reference), encoding="utf-8")
            bridge = FileIpcBridge(io_dir, out_dir)
            self.assertTrue(bridge.step_once())

            step = json.loads((out_dir / "dagger-reference" / "steps.ndjson").read_text())
            self.assertNotIn("mechanics_reference", step)
            references = read_mechanics_reference(out_dir / "dagger-reference")
            self.assertEqual(references[0]["jokers"][0]["mult"], 62)
            self.assertEqual(references[0]["step_id"], "dagger-reference:1")
            self.assertEqual(references[1]["capture_phase"], "resolved")
            self.assertEqual(references[1]["resolved_effects"][0]["victim_sell_cost_pre"], 4)
            self.assertFalse(resolved_path.exists())

    def test_mechanics_reference_rejects_nonfinite_values(self) -> None:
        with tempfile.TemporaryDirectory() as directory:
            root = Path(directory)
            io_dir = root / "io"
            io_dir.mkdir()
            request = _queue_request(io_dir, "bad-reference", 1)
            item = json.loads(request.read_text())
            item["mechanics_reference"] = {"schema_version": "dagger-reference/1.0",
                "step_id": "bad-reference:1", "capture_phase": "pre_action",
                "capture_timestamp_ns": 123, "producer_revision": "test",
                "runtime": {"balatro": "1.0.1", "steamodded": "test", "lovely": "test"}, "jokers": [
                {"role": "joker", "position": 0, "mult": float("nan")},
            ]}
            request.write_text(json.dumps(item), encoding="utf-8")
            bridge = FileIpcBridge(io_dir, root / "runs")
            with self.assertRaisesRegex(ValueError, "finite number"):
                bridge.step_once()
            self.assertTrue(request.exists())

    def test_snapshot_action_and_run_end_are_recorded(self) -> None:
        with tempfile.TemporaryDirectory() as directory:
            root = Path(directory)
            io_dir = root / "io"
            out_dir = root / "runs"
            io_dir.mkdir()
            snapshot = {
                "request_id": 7,
                "schema_version": "live/2.0.0",
                "page_name": "Blind_Select",
                "meta": {"run_id": "smoke-1"},
                "legal_actions": ["SelectBlind", "SkipBlind"],
                "action_taken": "SelectBlind",
                "state": {"ante": 1},
            }
            (io_dir / "snapshot.json").write_text(json.dumps(snapshot), encoding="utf-8")
            bridge = FileIpcBridge(io_dir, out_dir)

            self.assertTrue(bridge.step_once())
            self.assertEqual((io_dir / "action.txt").read_text(), "7\tSelectBlind\n")
            step = (out_dir / "smoke-1" / "steps.ndjson").read_text().splitlines()[0]
            self.assertEqual(json.loads(step)["_recorded_action"], "SelectBlind")

            (io_dir / "run_end.json").write_text(
                json.dumps({"run_id": "smoke-1", "outcome": "win"}), encoding="utf-8"
            )
            self.assertTrue(bridge.step_once())
            session = json.loads((out_dir / "smoke-1" / "session.json").read_text())
            self.assertEqual(session["outcome"], "win")
            self.assertEqual(session["n_steps"], 1)
            self.assertEqual(session["usage"]["action_counts"], {"SelectBlind": 1})
            self.assertEqual(session["usage"]["unique_action_count"], 1)
            self.assertIsNotNone(session["usage"]["first_recorded_at"])
            self.assertEqual(session["usage"]["first_recorded_at"], session["usage"]["last_recorded_at"])
            step_record = json.loads((root / "runs" / "smoke-1" / "steps.ndjson").read_text())
            self.assertIsNotNone(datetime.fromisoformat(step_record["_recorded_at"]))
            diagnostics = [json.loads(line) for line in
                           (out_dir / "smoke-1" / "capture_diagnostics.ndjson").read_text().splitlines()]
            self.assertTrue(any(item["code"] == "terminal_watermark_missing" for item in diagnostics))

    def test_action_must_be_legal(self) -> None:
        with tempfile.TemporaryDirectory() as directory:
            root = Path(directory)
            io_dir = root / "io"
            io_dir.mkdir()
            (io_dir / "snapshot.json").write_text(
                json.dumps({
                    "request_id": 1,
                    "meta": {"run_id": "smoke-2"},
                    "legal_actions": ["SkipBlind"],
                }),
                encoding="utf-8",
            )
            with self.assertRaises(ValueError):
                FileIpcBridge(io_dir, root / "runs", action="SelectBlind").step_once()

    def test_recording_marker_is_attached_to_first_run_session(self) -> None:
        with tempfile.TemporaryDirectory() as directory:
            root = Path(directory)
            io_dir = root / "io"
            io_dir.mkdir()
            (io_dir / "recording_start_marker.json").write_text(json.dumps({
                "schema_version": "producer/1.0.0",
                "recording_id": "obs-test-1",
                "fps": 60,
                "capture_timestamp_ns": 123,
            }), encoding="utf-8")
            (io_dir / "snapshot.json").write_text(json.dumps({
                "request_id": 1,
                "meta": {"run_id": "marker-run"},
                "action_taken": "SkipBlind",
            }), encoding="utf-8")

            bridge = FileIpcBridge(io_dir, root / "runs")
            self.assertTrue(bridge.step_once())
            session = json.loads((root / "runs" / "marker-run" / "session.json").read_text())
            self.assertEqual(session["recording"]["recording_id"], "obs-test-1")

    def test_new_recording_marker_does_not_rewrite_prior_run_association(self) -> None:
        with tempfile.TemporaryDirectory() as directory:
            root = Path(directory)
            io_dir, out_dir = root / "io", root / "runs"
            io_dir.mkdir()

            def marker(recording_id, timestamp):
                return {"schema_version": "producer/1.0.0", "recording_id": recording_id,
                        "fps": 60, "capture_timestamp_ns": timestamp}

            marker_path = io_dir / "recording_start_marker.json"
            marker_path.write_text(json.dumps(marker("recording-one", 1)), encoding="utf-8")
            bridge = FileIpcBridge(io_dir, out_dir)
            for request_id, run_id in ((1, "first"), (2, "first")):
                (io_dir / "snapshot.json").write_text(json.dumps({
                    "request_id": request_id, "meta": {"run_id": run_id}, "action_taken": "SkipBlind",
                }), encoding="utf-8")
                bridge.step_once()
            marker_path.write_text(json.dumps(marker("recording-two", 2)), encoding="utf-8")
            (io_dir / "snapshot.json").write_text(json.dumps({
                "request_id": 1, "meta": {"run_id": "second"}, "action_taken": "SkipBlind",
            }), encoding="utf-8")
            bridge.step_once()
            first = json.loads((out_dir / "first" / "session.json").read_text())
            second = json.loads((out_dir / "second" / "session.json").read_text())
            self.assertEqual(first["recording"]["recording_id"], "recording-one")
            self.assertEqual(second["recording"]["recording_id"], "recording-two")

    def test_duplicate_snapshot_replays_ack_without_duplicate_record(self) -> None:
        with tempfile.TemporaryDirectory() as directory:
            root = Path(directory)
            io_dir = root / "io"
            io_dir.mkdir()
            snapshot = {
                "request_id": 2,
                "meta": {"run_id": "smoke-3"},
                "legal_actions": ["SkipBlind"],
                "action_taken": "SkipBlind",
            }
            bridge = FileIpcBridge(io_dir, root / "runs")
            for _ in range(2):
                (io_dir / "snapshot.json").write_text(json.dumps(snapshot), encoding="utf-8")
                self.assertTrue(bridge.step_once())
                self.assertEqual((io_dir / "action.txt").read_text(), "2\tSkipBlind\n")
            self.assertEqual(
                len((root / "runs" / "smoke-3" / "steps.ndjson").read_text().splitlines()),
                1,
            )
            session = json.loads((root / "runs" / "smoke-3" / "session.json").read_text())
            self.assertEqual(session["usage"]["action_counts"], {"SkipBlind": 1})

    def test_usage_metadata_counts_commands_and_survives_restart(self) -> None:
        with tempfile.TemporaryDirectory() as directory:
            root = Path(directory)
            io_dir, out_dir = root / "io", root / "runs"
            io_dir.mkdir()
            bridge = FileIpcBridge(io_dir, out_dir)
            for request_id, action in ((1, "SkipBlind"), (2, "SelectBlind"), (3, "SkipBlind")):
                (io_dir / "snapshot.json").write_text(json.dumps({
                    "request_id": request_id,
                    "meta": {"run_id": "usage-run"},
                    "action_taken": action,
                }), encoding="utf-8")
                self.assertTrue(bridge.step_once())
            original_usage = json.loads((out_dir / "usage-run" / "session.json").read_text())["usage"]
            recovered = FileIpcBridge(io_dir, out_dir)
            usage = recovered.open_sessions()["usage-run"]["usage"]
            self.assertEqual(usage, original_usage)
            self.assertEqual(usage["action_counts"], {"SkipBlind": 2, "SelectBlind": 1})
            self.assertEqual(usage["unique_action_count"], 2)
            self.assertLessEqual(usage["first_recorded_at"], usage["last_recorded_at"])
            persisted = json.loads((out_dir / "usage-run" / "session.json").read_text())["usage"]
            self.assertEqual(persisted, usage)

    def test_duplicate_replay_after_finalization_reacks_without_counting(self) -> None:
        with tempfile.TemporaryDirectory() as directory:
            root = Path(directory)
            io_dir, out_dir = root / "io", root / "runs"
            io_dir.mkdir()
            request = {"request_id": 1, "meta": {"run_id": "final-replay"},
                       "action_taken": "SkipBlind"}
            bridge = FileIpcBridge(io_dir, out_dir)
            (io_dir / "snapshot.json").write_text(json.dumps(request), encoding="utf-8")
            self.assertTrue(bridge.step_once())
            (io_dir / "run_end.json").write_text(
                json.dumps({"run_id": "final-replay", "outcome": "loss"}), encoding="utf-8")
            self.assertTrue(bridge.step_once())
            (io_dir / "snapshot.json").write_text(json.dumps(request), encoding="utf-8")
            self.assertTrue(bridge.step_once())
            recovered = FileIpcBridge(io_dir, out_dir)
            (io_dir / "snapshot.json").write_text(json.dumps(request), encoding="utf-8")
            self.assertTrue(recovered.step_once())
            session = json.loads((out_dir / "final-replay" / "session.json").read_text())
            self.assertEqual(session["n_steps"], 1)
            self.assertEqual(session["usage"]["action_counts"], {"SkipBlind": 1})
            self.assertEqual((io_dir / "action.txt").read_text(), "1\tSkipBlind\n")

    def test_legacy_steps_count_without_inventing_timestamps(self) -> None:
        with tempfile.TemporaryDirectory() as directory:
            root = Path(directory)
            io_dir, out_dir = root / "io", root / "runs"
            io_dir.mkdir()
            run_dir = out_dir / "legacy"
            run_dir.mkdir(parents=True)
            (run_dir / "session.json").write_text(json.dumps({
                "run_id": "legacy", "schema_version": "producer/1.0.0",
                "started_at": "2026-01-01T00:00:00+00:00", "ended_at": None,
                "outcome": "loss", "n_steps": 2,
            }), encoding="utf-8")
            (run_dir / "steps.ndjson").write_text("".join(json.dumps({
                "request_id": i, "_recorded_action": action,
            }) + "\n" for i, action in ((1, "SkipBlind"), (2, "SelectBlind"))), encoding="utf-8")
            bridge = FileIpcBridge(io_dir, out_dir)
            usage = bridge._finalized_session_data["legacy"]["usage"]
            self.assertEqual(usage["action_counts"], {"SkipBlind": 1, "SelectBlind": 1})
            self.assertEqual(usage["unique_action_count"], 2)
            self.assertIsNone(usage["first_recorded_at"])
            self.assertIsNone(usage["last_recorded_at"])

    def test_request_ids_can_restart_after_run_end(self) -> None:
        with tempfile.TemporaryDirectory() as directory:
            root = Path(directory)
            io_dir = root / "io"
            io_dir.mkdir()
            bridge = FileIpcBridge(io_dir, root / "runs")
            for run_id in ("smoke-4", "smoke-5"):
                (io_dir / "snapshot.json").write_text(json.dumps({
                    "request_id": 1,
                    "meta": {"run_id": run_id},
                    "legal_actions": ["SkipBlind"],
                    "action_taken": "SkipBlind",
                }), encoding="utf-8")
                self.assertTrue(bridge.step_once())
                (io_dir / "run_end.json").write_text(json.dumps({
                    "run_id": run_id,
                    "outcome": "loss",
                }), encoding="utf-8")
                self.assertTrue(bridge.step_once())
            self.assertEqual(
                json.loads((root / "runs" / "smoke-5" / "session.json").read_text())["n_steps"],
                1,
            )

    def test_serve_stops_cleanly_on_keyboard_interrupt(self) -> None:
        import contextlib
        import io as io_module

        with tempfile.TemporaryDirectory() as directory:
            root = Path(directory)
            io_dir = root / "io"
            io_dir.mkdir()
            snapshot = {
                "request_id": 1,
                "meta": {"run_id": "smoke-6"},
                "legal_actions": ["SkipBlind"],
                "action_taken": "SkipBlind",
            }
            bridge = FileIpcBridge(io_dir, root / "runs")
            (io_dir / "snapshot.json").write_text(json.dumps(snapshot), encoding="utf-8")

            calls = {"n": 0}
            original_step = bridge.step_once

            def interrupting_step() -> bool:
                calls["n"] += 1
                if calls["n"] >= 3:
                    raise KeyboardInterrupt
                return original_step()

            bridge.step_once = interrupting_step
            captured = io_module.StringIO()
            with contextlib.redirect_stdout(captured):
                bridge.serve()
            output = captured.getvalue()
            self.assertIn("stopped cleanly", output)
            self.assertIn("smoke-6", output)
            self.assertIn("1 steps recorded, outcome unknown", output)
            session = json.loads((root / "runs" / "smoke-6" / "session.json").read_text())
            self.assertEqual(session["lifecycle_status"], "incomplete")
            self.assertIsNone(session["outcome"])
            self.assertEqual(
                json.loads((root / "runs" / "smoke-6" / "session.json").read_text())["n_steps"],
                1,
            )

    def test_open_sessions_reports_unfinalized_runs(self) -> None:
        with tempfile.TemporaryDirectory() as directory:
            root = Path(directory)
            io_dir = root / "io"
            io_dir.mkdir()
            bridge = FileIpcBridge(io_dir, root / "runs")
            self.assertEqual(bridge.open_sessions(), {})

    def test_restart_recovers_session_and_run_scoped_request_identity(self) -> None:
        with tempfile.TemporaryDirectory() as directory:
            root = Path(directory)
            io_dir, out_dir = root / "io", root / "runs"
            io_dir.mkdir()
            snapshot = {"request_id": 1, "meta": {"run_id": "run-a"}, "action_taken": "SkipBlind"}
            (io_dir / "snapshot.json").write_text(json.dumps(snapshot), encoding="utf-8")
            self.assertTrue(FileIpcBridge(io_dir, out_dir).step_once())
            run_a_session = out_dir / "run-a" / "session.json"
            session = json.loads(run_a_session.read_text())
            session["n_steps"] = 8
            run_a_session.write_text(json.dumps(session), encoding="utf-8")
            recovered = FileIpcBridge(io_dir, out_dir)
            self.assertEqual(recovered.open_sessions()["run-a"]["n_steps"], 1)
            diagnostic = json.loads((out_dir / "run-a" / "capture_diagnostics.ndjson").read_text())
            self.assertEqual(diagnostic["code"], "session_step_count_recovered")
            (io_dir / "snapshot.json").write_text(json.dumps(snapshot), encoding="utf-8")
            self.assertTrue(recovered.step_once())
            (io_dir / "snapshot.json").write_text(json.dumps({**snapshot, "meta": {"run_id": "run-b"}}), encoding="utf-8")
            self.assertTrue(recovered.step_once())
            self.assertEqual(json.loads((out_dir / "run-b" / "session.json").read_text())["n_steps"], 1)
            self.assertEqual(len((out_dir / "run-a" / "steps.ndjson").read_text().splitlines()), 1)

    def test_malformed_snapshot_is_quarantined(self) -> None:
        with tempfile.TemporaryDirectory() as directory:
            root = Path(directory)
            io_dir = root / "io"
            io_dir.mkdir()
            (io_dir / "snapshot.json").write_text("{not-json", encoding="utf-8")
            self.assertFalse(FileIpcBridge(io_dir, root / "runs").step_once())
            self.assertTrue((io_dir / "snapshot.json.invalid").exists())

    def test_semantically_invalid_snapshot_is_quarantined(self) -> None:
        with tempfile.TemporaryDirectory() as directory:
            root = Path(directory)
            io_dir = root / "io"
            io_dir.mkdir()
            (io_dir / "snapshot.json").write_text(json.dumps({"request_id": 1}), encoding="utf-8")
            with self.assertRaisesRegex(ValueError, "meta.run_id"):
                FileIpcBridge(io_dir, root / "runs").step_once()
            self.assertTrue((io_dir / "snapshot.json.invalid").exists())

    def test_snapshot_is_processed_before_pending_run_end(self) -> None:
        with tempfile.TemporaryDirectory() as directory:
            root = Path(directory)
            io_dir = root / "io"
            io_dir.mkdir()
            (io_dir / "snapshot.json").write_text(json.dumps({
                "request_id": 1, "meta": {"run_id": "ordered"}, "action_taken": "SkipBlind",
            }), encoding="utf-8")
            (io_dir / "run_end.json").write_text(json.dumps({"run_id": "ordered", "outcome": "win"}), encoding="utf-8")
            bridge = FileIpcBridge(io_dir, root / "runs")
            self.assertTrue(bridge.step_once())
            session = json.loads((root / "runs" / "ordered" / "session.json").read_text())
            self.assertEqual(session["n_steps"], 1)
            self.assertEqual(session["outcome"], "win")

    def test_append_failure_does_not_acknowledge_or_consume_request(self) -> None:
        from unittest.mock import patch

        with tempfile.TemporaryDirectory() as directory:
            root = Path(directory)
            io_dir, out_dir = root / "io", root / "runs"
            io_dir.mkdir()
            (io_dir / "action.txt").write_text("stale\tack\n", encoding="utf-8")
            snapshot = {"request_id": 9, "meta": {"run_id": "failure"}, "action_taken": "SkipBlind"}
            (io_dir / "snapshot.json").write_text(json.dumps(snapshot), encoding="utf-8")
            bridge = FileIpcBridge(io_dir, out_dir)
            original_open = Path.open

            def failing_open(path, *args, **kwargs):
                if path.name == "steps.ndjson" and "a" in args:
                    raise OSError("injected append failure")
                return original_open(path, *args, **kwargs)

            with patch.object(Path, "open", failing_open):
                with self.assertRaisesRegex(OSError, "injected append failure"):
                    bridge.step_once()
            self.assertEqual((io_dir / "action.txt").read_text(), "stale\tack\n")
            self.assertTrue((io_dir / "snapshot.json").exists())
            self.assertEqual(bridge._seen_requests, set())
            self.assertTrue(bridge.step_once())
            self.assertEqual((io_dir / "action.txt").read_text(), "9\tSkipBlind\n")
            self.assertEqual(len((out_dir / "failure" / "steps.ndjson").read_text().splitlines()), 1)

    def test_partial_append_failure_is_quarantined_before_retry(self) -> None:
        from unittest.mock import patch

        with tempfile.TemporaryDirectory() as directory:
            root = Path(directory)
            io_dir, out_dir = root / "io", root / "runs"
            io_dir.mkdir()
            request_path = _queue_request(io_dir, "partial-write", 1)
            bridge = FileIpcBridge(io_dir, out_dir)
            original_open = Path.open

            class PartialWriter:
                def __init__(self, stream):
                    self.stream = stream

                def __enter__(self):
                    return self

                def __exit__(self, exc_type, exc, traceback):
                    self.stream.close()

                def write(self, text):
                    self.stream.write(text[:12])
                    self.stream.flush()
                    raise OSError("injected partial append failure")

                def flush(self):
                    return self.stream.flush()

                def fileno(self):
                    return self.stream.fileno()

            def partial_open(path, *args, **kwargs):
                stream = original_open(path, *args, **kwargs)
                if path.name == "steps.ndjson" and "a" in args:
                    return PartialWriter(stream)
                return stream

            with patch.object(Path, "open", partial_open):
                with self.assertRaisesRegex(OSError, "partial append failure"):
                    bridge.step_once()
            self.assertTrue(request_path.exists())
            self.assertEqual((out_dir / "partial-write" / "steps.ndjson").read_bytes(), b"")
            self.assertEqual(len((out_dir / "partial-write" / "steps.ndjson.corrupt").read_bytes()), 12)
            self.assertTrue(bridge.step_once())
            self.assertFalse(request_path.exists())
            self.assertEqual(len((out_dir / "partial-write" / "steps.ndjson").read_text().splitlines()), 1)

    def test_session_update_failure_retries_without_duplicate_append(self) -> None:
        from unittest.mock import patch

        with tempfile.TemporaryDirectory() as directory:
            root = Path(directory)
            io_dir, out_dir = root / "io", root / "runs"
            io_dir.mkdir()
            (io_dir / "snapshot.json").write_text(json.dumps({
                "request_id": 4, "meta": {"run_id": "session-failure"}, "action_taken": "SkipBlind",
            }), encoding="utf-8")
            bridge = FileIpcBridge(io_dir, out_dir)
            original_write = bridge._write_session
            calls = {"count": 0}

            def fail_after_append(session):
                calls["count"] += 1
                if calls["count"] == 2:
                    raise OSError("injected session failure")
                return original_write(session)

            with patch.object(bridge, "_write_session", fail_after_append):
                with self.assertRaisesRegex(OSError, "injected session failure"):
                    bridge.step_once()
                self.assertTrue((io_dir / "snapshot.json").exists())
                self.assertEqual((io_dir / "action.txt").exists(), False)
                self.assertTrue(bridge.step_once())
            steps = (out_dir / "session-failure" / "steps.ndjson").read_text().splitlines()
            self.assertEqual(len(steps), 1)
            self.assertEqual(json.loads((out_dir / "session-failure" / "session.json").read_text())["n_steps"], 1)

    def test_ack_failure_retries_without_duplicate_append(self) -> None:
        from unittest.mock import patch
        from ground_truth import file_ipc_bridge

        with tempfile.TemporaryDirectory() as directory:
            root = Path(directory)
            io_dir, out_dir = root / "io", root / "runs"
            io_dir.mkdir()
            (io_dir / "snapshot.json").write_text(json.dumps({
                "request_id": 5, "meta": {"run_id": "ack-failure"}, "action_taken": "SkipBlind",
            }), encoding="utf-8")
            bridge = FileIpcBridge(io_dir, out_dir)
            original_atomic_write = file_ipc_bridge._atomic_write
            calls = {"count": 0}

            def fail_ack_once(path, text):
                if path == bridge.action_path:
                    calls["count"] += 1
                    if calls["count"] == 1:
                        raise OSError("injected acknowledgement failure")
                return original_atomic_write(path, text)

            with patch.object(file_ipc_bridge, "_atomic_write", fail_ack_once):
                with self.assertRaisesRegex(OSError, "injected acknowledgement failure"):
                    bridge.step_once()
                self.assertTrue((io_dir / "snapshot.json").exists())
                self.assertTrue(bridge.step_once())
            self.assertEqual(len((out_dir / "ack-failure" / "steps.ndjson").read_text().splitlines()), 1)

    def test_request_unlink_failure_restarts_and_deduplicates_persisted_step(self) -> None:
        from unittest.mock import patch

        with tempfile.TemporaryDirectory() as directory:
            root = Path(directory)
            io_dir, out_dir = root / "io", root / "runs"
            io_dir.mkdir()
            request_path = _queue_request(io_dir, "unlink-failure", 1)
            bridge = FileIpcBridge(io_dir, out_dir)
            original_unlink = Path.unlink

            def fail_request_unlink_once(path, *args, **kwargs):
                if path == request_path:
                    raise OSError("injected request unlink failure")
                return original_unlink(path, *args, **kwargs)

            with patch.object(Path, "unlink", fail_request_unlink_once):
                with self.assertRaisesRegex(OSError, "request unlink failure"):
                    bridge.step_once()

            self.assertTrue(request_path.exists())
            self.assertEqual(len((out_dir / "unlink-failure" / "steps.ndjson").read_text().splitlines()), 1)
            self.assertEqual(json.loads((out_dir / "unlink-failure" / "session.json").read_text())["n_steps"], 1)
            restarted = FileIpcBridge(io_dir, out_dir)
            self.assertTrue(restarted.step_once())
            self.assertFalse(request_path.exists())
            self.assertEqual(len((out_dir / "unlink-failure" / "steps.ndjson").read_text().splitlines()), 1)
            self.assertEqual(json.loads((out_dir / "unlink-failure" / "session.json").read_text())["n_steps"], 1)
            self.assertEqual((io_dir / "action.txt").read_text(), "1\tSkipBlind\n")

    def test_run_end_retries_after_restart_keep_final_outcome(self) -> None:
        with tempfile.TemporaryDirectory() as directory:
            root = Path(directory)
            io_dir, out_dir = root / "io", root / "runs"
            io_dir.mkdir()
            (io_dir / "snapshot.json").write_text(json.dumps({
                "request_id": 1, "meta": {"run_id": "terminal"}, "action_taken": "SkipBlind",
            }), encoding="utf-8")
            bridge = FileIpcBridge(io_dir, out_dir)
            self.assertTrue(bridge.step_once())
            (io_dir / "run_end.json").write_text(json.dumps({"run_id": "terminal", "outcome": "loss"}), encoding="utf-8")
            self.assertTrue(FileIpcBridge(io_dir, out_dir).step_once())
            self.assertFalse((io_dir / "run_end.json").exists())
            self.assertEqual(json.loads((out_dir / "terminal" / "session.json").read_text())["outcome"], "loss")

    def test_run_end_waits_for_snapshot_that_arrives_after_signal(self) -> None:
        with tempfile.TemporaryDirectory() as directory:
            root = Path(directory)
            io_dir, out_dir = root / "io", root / "runs"
            io_dir.mkdir()
            (io_dir / "run_end.json").write_text(json.dumps({"run_id": "late", "outcome": "win"}), encoding="utf-8")
            bridge = FileIpcBridge(io_dir, out_dir)
            self.assertFalse(bridge.step_once())
            self.assertTrue((io_dir / "run_end.json").exists())
            self.assertFalse(FileIpcBridge(io_dir, out_dir).step_once())
            (io_dir / "snapshot.json").write_text(json.dumps({
                "request_id": 1, "meta": {"run_id": "late"}, "action_taken": "SkipBlind",
            }), encoding="utf-8")
            self.assertTrue(bridge.step_once())
            session = json.loads((out_dir / "late" / "session.json").read_text())
            self.assertEqual(session["n_steps"], 1)
            self.assertEqual(session["outcome"], "win")
            self.assertFalse((io_dir / "run_end.json").exists())

    def test_run_end_persistence_failure_recovers_from_retained_signal(self) -> None:
        from unittest.mock import patch

        with tempfile.TemporaryDirectory() as directory:
            root = Path(directory)
            io_dir, out_dir = root / "io", root / "runs"
            io_dir.mkdir()
            (io_dir / "snapshot.json").write_text(json.dumps({
                "request_id": 1, "meta": {"run_id": "end-failure"}, "action_taken": "SkipBlind",
            }), encoding="utf-8")
            bridge = FileIpcBridge(io_dir, out_dir)
            bridge.step_once()
            (io_dir / "run_end.json").write_text(json.dumps({"run_id": "end-failure", "outcome": "loss"}), encoding="utf-8")
            with patch.object(bridge, "_write_session", side_effect=OSError("injected finalization failure")):
                with self.assertRaisesRegex(OSError, "injected finalization failure"):
                    bridge.step_once()
            self.assertTrue((io_dir / "run_end.json").exists())
            self.assertEqual(json.loads((out_dir / "end-failure" / "session.json").read_text())["outcome"], None)
            self.assertTrue(FileIpcBridge(io_dir, out_dir).step_once())
            self.assertEqual(json.loads((out_dir / "end-failure" / "session.json").read_text())["outcome"], "loss")

    def test_late_snapshot_cannot_reset_finalized_run(self) -> None:
        with tempfile.TemporaryDirectory() as directory:
            root = Path(directory)
            io_dir, out_dir = root / "io", root / "runs"
            io_dir.mkdir()
            (io_dir / "snapshot.json").write_text(json.dumps({
                "request_id": 1, "meta": {"run_id": "final"}, "action_taken": "SkipBlind",
            }), encoding="utf-8")
            bridge = FileIpcBridge(io_dir, out_dir)
            bridge.step_once()
            (io_dir / "run_end.json").write_text(json.dumps({"run_id": "final", "outcome": "win"}), encoding="utf-8")
            bridge.step_once()
            (io_dir / "snapshot.json").write_text(json.dumps({
                "request_id": 2, "meta": {"run_id": "final"}, "action_taken": "SkipBlind",
            }), encoding="utf-8")
            with self.assertRaisesRegex(ValueError, "after run .* finalized"):
                FileIpcBridge(io_dir, out_dir).step_once()
            self.assertTrue((io_dir / "snapshot.json.invalid").exists())
            session = json.loads((out_dir / "final" / "session.json").read_text())
            self.assertEqual(session["outcome"], "win")
            self.assertEqual(session["n_steps"], 1)

    def test_delayed_consumer_records_possible_overwrite_gap(self) -> None:
        with tempfile.TemporaryDirectory() as directory:
            root = Path(directory)
            io_dir, out_dir = root / "io", root / "runs"
            io_dir.mkdir()
            bridge = FileIpcBridge(io_dir, out_dir)
            # The single-slot producer overwrites request 1 before the consumer reads.
            for request_id in (1, 2):
                (io_dir / "snapshot.json").write_text(json.dumps({
                    "request_id": request_id,
                    "meta": {"run_id": "delayed"},
                    "action_taken": "SkipBlind",
                }), encoding="utf-8")
            self.assertTrue(bridge.step_once())
            diagnostic = json.loads((out_dir / "delayed" / "capture_diagnostics.ndjson").read_text())
            self.assertEqual(diagnostic["current_request_id"], 2)
            self.assertEqual(diagnostic["missing_count"], 1)
            self.assertEqual(diagnostic["cause"], "unknown_possible_overwrite_or_consumer_delay")

    def test_truncated_steps_record_is_preserved_and_reported(self) -> None:
        with tempfile.TemporaryDirectory() as directory:
            root = Path(directory)
            io_dir, out_dir = root / "io", root / "runs"
            io_dir.mkdir()
            run_dir = out_dir / "truncated"
            run_dir.mkdir(parents=True)
            (run_dir / "session.json").write_text(json.dumps({
                "run_id": "truncated", "n_steps": 1, "outcome": None,
            }), encoding="utf-8")
            valid = json.dumps({"request_id": 1, "_recorded_action": "SkipBlind"})
            raw = (valid + "\n{" + '"request_id":2').encode()
            (run_dir / "steps.ndjson").write_bytes(raw)
            bridge = FileIpcBridge(io_dir, out_dir)
            self.assertEqual((run_dir / "steps.ndjson.corrupt").read_bytes(), b'{"request_id":2')
            self.assertEqual(len((run_dir / "steps.ndjson").read_text().splitlines()), 1)
            self.assertIn("truncated", bridge.open_sessions())
            self.assertTrue((run_dir / "steps.ndjson.corrupt").exists())
            diagnostic = json.loads((run_dir / "capture_diagnostics.ndjson").read_text())
            self.assertEqual(diagnostic["code"], "invalid_ndjson_tail_quarantined")
            self.assertEqual(diagnostic["byte_count"], len(b'{"request_id":2'))

    def test_request_id_gap_is_recorded_without_claiming_a_cause(self) -> None:
        with tempfile.TemporaryDirectory() as directory:
            root = Path(directory)
            io_dir, out_dir = root / "io", root / "runs"
            io_dir.mkdir()
            bridge = FileIpcBridge(io_dir, out_dir)
            for request_id in (1, 3):
                (io_dir / "snapshot.json").write_text(json.dumps({
                    "request_id": request_id,
                    "meta": {"run_id": "gap"},
                    "action_taken": "SkipBlind",
                }), encoding="utf-8")
                self.assertTrue(bridge.step_once())
            diagnostic = json.loads((out_dir / "gap" / "capture_diagnostics.ndjson").read_text())
            self.assertEqual(diagnostic["code"], "request_id_gap")
            self.assertEqual(diagnostic["missing_count"], 1)
            self.assertEqual(diagnostic["cause"], "unknown_possible_overwrite_or_consumer_delay")

    def test_corrupt_diagnostic_tail_does_not_block_session_recovery(self) -> None:
        with tempfile.TemporaryDirectory() as directory:
            root = Path(directory)
            io_dir, out_dir = root / "io", root / "runs"
            io_dir.mkdir()
            run_dir = out_dir / "diagnostic-corrupt"
            run_dir.mkdir(parents=True)
            (run_dir / "session.json").write_text(json.dumps({
                "run_id": "diagnostic-corrupt", "n_steps": 1, "outcome": None,
            }), encoding="utf-8")
            (run_dir / "steps.ndjson").write_text(json.dumps({
                "request_id": 1, "_recorded_action": "SkipBlind",
            }) + "\n", encoding="utf-8")
            valid_diagnostic = json.dumps({"code": "prior_diagnostic"}) + "\n"
            corrupt_tail = b'{"code":"unfinished'
            (run_dir / "capture_diagnostics.ndjson").write_bytes(valid_diagnostic.encode() + corrupt_tail)

            bridge = FileIpcBridge(io_dir, out_dir)

            self.assertIn("diagnostic-corrupt", bridge.open_sessions())
            self.assertEqual((run_dir / "capture_diagnostics.ndjson.corrupt").read_bytes(), corrupt_tail)
            self.assertEqual(json.loads((run_dir / "capture_diagnostics.ndjson").read_text())["code"], "prior_diagnostic")

    def test_queued_requests_are_sorted_and_removed_after_durable_ack(self) -> None:
        with tempfile.TemporaryDirectory() as directory:
            root = Path(directory)
            io_dir, out_dir = root / "io", root / "runs"
            io_dir.mkdir()
            ten = _queue_request(io_dir, "queued", 10)
            two = _queue_request(io_dir, "queued", 2)

            bridge = FileIpcBridge(io_dir, out_dir)
            self.assertTrue(bridge.step_once())

            records = [json.loads(line) for line in (out_dir / "queued" / "steps.ndjson").read_text().splitlines()]
            self.assertEqual([record["request_id"] for record in records], [2, 10])
            self.assertFalse(two.exists())
            self.assertFalse(ten.exists())
            self.assertEqual((io_dir / "action.txt").read_text(), "10\tSkipBlind\n")

    def test_terminal_watermark_waits_for_queued_requests_across_restart(self) -> None:
        with tempfile.TemporaryDirectory() as directory:
            root = Path(directory)
            io_dir, out_dir = root / "io", root / "runs"
            io_dir.mkdir()
            end_path = io_dir / "run_end_watermark.json"
            end_path.write_text(json.dumps({
                "run_id": "watermark", "ipc_schema_version": "file-queue/1.0.0",
                "outcome": "win", "last_request_id": 2,
            }), encoding="utf-8")
            _queue_request(io_dir, "watermark", 1)

            bridge = FileIpcBridge(io_dir, out_dir)
            self.assertTrue(bridge.step_once())
            self.assertTrue(end_path.exists())
            self.assertFalse(bridge.step_once())
            diagnostic = json.loads((out_dir / "watermark" / "capture_diagnostics.ndjson").read_text())
            self.assertEqual(diagnostic["code"], "terminal_requests_pending")
            self.assertEqual(diagnostic["missing_request_ids"], [2])

            restarted = FileIpcBridge(io_dir, out_dir)
            _queue_request(io_dir, "watermark", 2)
            self.assertTrue(restarted.step_once())
            session = json.loads((out_dir / "watermark" / "session.json").read_text())
            self.assertEqual(session["n_steps"], 2)
            self.assertEqual(session["outcome"], "win")
            diagnostics = [json.loads(line) for line in
                           (out_dir / "watermark" / "capture_diagnostics.ndjson").read_text().splitlines()]
            pending = next(item for item in diagnostics if item["code"] == "terminal_requests_pending")
            self.assertTrue(pending["resolved"])
            self.assertFalse(end_path.exists())

    def test_producer_write_failures_mark_final_run_incomplete(self) -> None:
        with tempfile.TemporaryDirectory() as directory:
            root = Path(directory)
            io_dir, out_dir = root / "io", root / "runs"
            io_dir.mkdir()
            _queue_request(io_dir, "producer-errors", 1)
            (io_dir / "run_end_producer-errors.json").write_text(json.dumps({
                "run_id": "producer-errors",
                "ipc_schema_version": "file-queue/1.0.0",
                "outcome": "loss",
                "last_request_id": 1,
                "producer_write_failures": 2,
            }), encoding="utf-8")

            bridge = FileIpcBridge(io_dir, out_dir)
            self.assertTrue(bridge.step_once())
            diagnostics = [json.loads(line) for line in
                           (out_dir / "producer-errors" / "capture_diagnostics.ndjson").read_text().splitlines()]
            self.assertTrue(any(item["code"] == "producer_request_write_failures"
                                and item["capture_completeness"] == "incomplete" for item in diagnostics))

    def test_queued_session_write_failure_keeps_request_for_retry(self) -> None:
        from unittest.mock import patch

        with tempfile.TemporaryDirectory() as directory:
            root = Path(directory)
            io_dir, out_dir = root / "io", root / "runs"
            io_dir.mkdir()
            request_path = _queue_request(io_dir, "queued-retry", 1)
            bridge = FileIpcBridge(io_dir, out_dir)
            original_write = bridge._write_session
            calls = {"count": 0}

            def fail_after_append(session):
                calls["count"] += 1
                if calls["count"] == 2:
                    raise OSError("injected queue session failure")
                return original_write(session)

            with patch.object(bridge, "_write_session", fail_after_append):
                with self.assertRaisesRegex(OSError, "injected queue session failure"):
                    bridge.step_once()
                self.assertTrue(request_path.exists())
                self.assertTrue(bridge.step_once())
            self.assertFalse(request_path.exists())
            self.assertEqual(len((out_dir / "queued-retry" / "steps.ndjson").read_text().splitlines()), 1)

    def test_watermarked_finalization_imports_once_and_survives_restart(self) -> None:
        from alembic import command
        from alembic.config import Config
        from run_bundle import RunBundleInspector

        with tempfile.TemporaryDirectory() as directory:
            root = Path(directory)
            io_dir, out_dir = root / "io", root / "runs"
            io_dir.mkdir()
            db_path = root / "bundle.sqlite"
            url = f"sqlite:///{db_path.as_posix()}"
            cfg = Config("alembic.ini")
            cfg.set_main_option("sqlalchemy.url", url)
            command.upgrade(cfg, "head")
            _queue_request(io_dir, "automatic-import", 1)
            (io_dir / "run_end_automatic-import.json").write_text(json.dumps({
                "ipc_schema_version": "file-queue/1.0.0", "run_id": "automatic-import",
                "last_request_id": 1, "outcome": "win",
            }), encoding="utf-8")

            bridge = FileIpcBridge(io_dir, out_dir, bundle_db=url)
            self.assertTrue(bridge.step_once())
            source_dir = out_dir / "automatic-import"
            source_hash = __import__("hashlib").sha256((source_dir / "steps.ndjson").read_bytes()).hexdigest()
            inspector = RunBundleInspector(url)
            self.assertEqual(inspector.summary("automatic-import")["data"]["record_count"], 1)
            self.assertEqual(len(inspector.find_records("automatic-import", kind="step")["data"]), 1)
            self.assertEqual(inspector.summary("automatic-import")["data"]["run"]["status"], "won")
            self.assertEqual(inspector.validate("automatic-import")["data"]["status"], "valid")
            provenance = {item["key"]: item["value"] for item in inspector.provenance("automatic-import")["data"]}
            self.assertIn("oracle.usage", provenance)
            self.assertIn("oracle.source_session_sha256", provenance)

            restarted = FileIpcBridge(io_dir, out_dir, bundle_db=url)
            self.assertTrue(restarted.step_once())
            self.assertEqual(inspector.summary("automatic-import")["data"]["record_count"], 1)
            self.assertEqual(__import__("hashlib").sha256((source_dir / "steps.ndjson").read_bytes()).hexdigest(), source_hash)
            self.assertTrue((source_dir / "session.json").exists())
            inspector.close()

    def test_database_unavailable_keeps_finalized_source_for_retry(self) -> None:
        from alembic import command
        from alembic.config import Config
        from run_bundle import RunBundleInspector

        with tempfile.TemporaryDirectory() as directory:
            root = Path(directory)
            io_dir, out_dir = root / "io", root / "runs"
            io_dir.mkdir()
            db_path = root / "bundle.sqlite"
            url = f"sqlite:///{db_path.as_posix()}"
            _queue_request(io_dir, "retry-import", 1)
            (io_dir / "run_end_retry-import.json").write_text(json.dumps({
                "ipc_schema_version": "file-queue/1.0.0", "run_id": "retry-import",
                "last_request_id": 1, "outcome": "loss",
            }), encoding="utf-8")
            bridge = FileIpcBridge(io_dir, out_dir, bundle_db=url)
            self.assertTrue(bridge.step_once())
            self.assertTrue((out_dir / "retry-import" / "session.json").exists())
            self.assertTrue((out_dir / "retry-import" / "steps.ndjson").exists())
            self.assertNotIn("retry-import", bridge._imported_sessions)

            cfg = Config("alembic.ini")
            cfg.set_main_option("sqlalchemy.url", url)
            command.upgrade(cfg, "head")
            bridge._import_retry_after["retry-import"] = 0
            self.assertTrue(bridge.step_once())
            inspector = RunBundleInspector(url)
            self.assertEqual(inspector.summary("retry-import")["data"]["run"]["status"], "lost")
            inspector.close()

    def test_clean_stop_imports_incomplete_without_an_outcome(self) -> None:
        import contextlib
        import io as io_module
        from alembic import command
        from alembic.config import Config
        from run_bundle import RunBundleInspector

        with tempfile.TemporaryDirectory() as directory:
            root = Path(directory)
            io_dir, out_dir = root / "io", root / "runs"
            io_dir.mkdir()
            url = f"sqlite:///{(root / 'bundle.sqlite').as_posix()}"
            cfg = Config("alembic.ini")
            cfg.set_main_option("sqlalchemy.url", url)
            command.upgrade(cfg, "head")
            _queue_request(io_dir, "incomplete-stop", 1)
            bridge = FileIpcBridge(io_dir, out_dir, bundle_db=url)
            original_step = bridge.step_once
            calls = {"count": 0}

            def stop_after_recording():
                calls["count"] += 1
                if calls["count"] > 1:
                    raise KeyboardInterrupt
                return original_step()

            bridge.step_once = stop_after_recording
            with contextlib.redirect_stdout(io_module.StringIO()):
                bridge.serve()
            inspector = RunBundleInspector(url)
            summary = inspector.summary("incomplete-stop")["data"]
            self.assertEqual(summary["run"]["status"], "incomplete")
            self.assertIsNone(summary["run"]["outcome"])
            self.assertEqual(summary["record_count"], 1)
            inspector.close()

    def test_import_conflict_is_reported_and_not_retried_as_transient(self) -> None:
        import contextlib
        import io as io_module
        from alembic import command
        from alembic.config import Config
        from run_bundle import RunBundle

        with tempfile.TemporaryDirectory() as directory:
            root = Path(directory)
            io_dir, out_dir = root / "io", root / "runs"
            io_dir.mkdir()
            url = f"sqlite:///{(root / 'bundle.sqlite').as_posix()}"
            cfg = Config("alembic.ini")
            cfg.set_main_option("sqlalchemy.url", url)
            command.upgrade(cfg, "head")
            existing = root / "existing-source"
            existing.mkdir(parents=True)
            (existing / "session.json").write_text(json.dumps({
                "run_id": "source-collision", "schema_version": "producer/1.0.0",
                "started_at": "2026-10-03T03:28:55+00:00", "ended_at": None,
                "outcome": None, "n_steps": 0,
            }), encoding="utf-8")
            (existing / "steps.ndjson").write_text("", encoding="utf-8")
            seeded = RunBundle(url)
            seeded.import_oracle_directory(existing)
            seeded.close()

            _queue_request(io_dir, "source-collision", 1)
            (io_dir / "run_end_source-collision.json").write_text(json.dumps({
                "ipc_schema_version": "file-queue/1.0.0", "run_id": "source-collision",
                "last_request_id": 1, "outcome": "win",
            }), encoding="utf-8")
            bridge = FileIpcBridge(io_dir, out_dir, bundle_db=url)
            errors = io_module.StringIO()
            with contextlib.redirect_stderr(errors):
                bridge.step_once()
                bridge.step_once()
            self.assertIn("import conflict for run source-collision", errors.getvalue())
            self.assertEqual(len(bridge._import_conflicts), 1)
            self.assertTrue((out_dir / "source-collision" / "steps.ndjson").exists())


if __name__ == "__main__":
    unittest.main()
