import json
import tempfile
import unittest
from pathlib import Path

from ground_truth.file_ipc_bridge import FileIpcBridge


class FileIpcBridgeTests(unittest.TestCase):
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


if __name__ == "__main__":
    unittest.main()
