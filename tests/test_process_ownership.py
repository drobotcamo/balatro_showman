import json
import os
import subprocess
import sys
import tempfile
import time
import unittest
import contextlib
import io
from pathlib import Path

from ground_truth.process_ownership import OwnershipConflict, OwnershipLock, active_owner, process_matches
from ground_truth.file_ipc_bridge import main as recorder_main
from ground_truth.file_ipc_bridge import FileIpcBridge
from unittest.mock import patch


class OwnershipTests(unittest.TestCase):
    def test_live_owner_conflicts_and_releases_only_its_metadata(self):
        with tempfile.TemporaryDirectory() as temporary:
            root = Path(temporary) / "output"
            owner = OwnershipLock(root, "test", {"path": str(root)})
            owner.acquire()
            record = json.loads(owner.path.read_text(encoding="utf-8"))
            self.assertEqual(record["pid"], os.getpid())
            self.assertTrue(record["token"])
            self.assertEqual(active_owner(root, "test"), record)
            with self.assertRaises(OwnershipConflict):
                OwnershipLock(root, "test", {}).acquire()
            owner.close()
            self.assertFalse(owner.path.exists())
            self.assertIsNone(active_owner(root, "test"))

    def test_lock_excludes_an_independent_process(self):
        with tempfile.TemporaryDirectory() as temporary:
            root = Path(temporary) / "output"
            owner = OwnershipLock(root, "test", {"path": str(root)})
            owner.acquire()
            code = ("from pathlib import Path; from ground_truth.process_ownership import "
                    "OwnershipLock; OwnershipLock(Path(r'" + str(root) + "'), 'test', {}).acquire()")
            result = subprocess.run([sys.executable, "-c", code], capture_output=True, text=True)
            owner.close()
            self.assertNotEqual(result.returncode, 0)
            self.assertIn("owned by another", result.stderr)

    def test_process_command_identity_matches_the_current_test_process(self):
        self.assertTrue(process_matches(os.getpid(), ["-m", "unittest"]))
        self.assertFalse(process_matches(os.getpid(), ["-m", "unrelated-command"]))

    def test_process_command_match_uses_exact_argument_tokens(self):
        result = subprocess.CompletedProcess([], 0,
            '"C:\\Python\\python.exe" -m showman record --diagnostic ground_truth.qa_viewer', "")
        with patch("ground_truth.process_ownership.os.name", "nt"), \
                patch("ground_truth.process_ownership.shutil.which", return_value="powershell.exe"), \
                patch("ground_truth.process_ownership.subprocess.run", return_value=result):
            self.assertTrue(process_matches(99999, ["-m", "showman", "record"]))
            self.assertFalse(process_matches(99999, ["-m", "ground_truth.qa_viewer"]))

    def test_close_does_not_remove_replaced_owner_metadata(self):
        with tempfile.TemporaryDirectory() as temporary:
            owner = OwnershipLock(Path(temporary), "test", {})
            owner.acquire()
            owner.path.write_text('{"pid": -1, "token": "other"}\n', encoding="utf-8")
            owner.close()
            self.assertTrue(owner.path.exists())

    def test_recorder_reuses_matching_recent_healthy_owner(self):
        with tempfile.TemporaryDirectory() as temporary:
            io_dir, out_dir = Path(temporary) / "io", Path(temporary) / "out"
            consumer_identity = {"command": "python -m showman record",
                                 "command_args": ["-m", "showman", "record"],
                                 "io_dir": str(io_dir.resolve()), "out_dir": str(out_dir.resolve()),
                                 "bundle_db": None}
            output_identity = consumer_identity
            consumer = OwnershipLock(io_dir, "showman-consumer", consumer_identity).acquire()
            output = OwnershipLock(out_dir, "showman-recorder", output_identity).acquire()
            now = time.time_ns()
            consumer.update(ready=True, heartbeat_ns=now)
            output.update(ready=True, heartbeat_ns=now)
            try:
                with patch("ground_truth.process_ownership.process_matches", return_value=True), \
                        contextlib.redirect_stderr(io.StringIO()) as messages:
                    recorder_main(["--io-dir", str(io_dir), "--out-dir", str(out_dir)])
                self.assertIn("Reusing healthy matching recorder", messages.getvalue())
            finally:
                output.close()
                consumer.close()

    def test_recorder_reports_mismatched_consumer_without_overwriting_owner(self):
        with tempfile.TemporaryDirectory() as temporary:
            io_dir, out_dir = Path(temporary) / "io", Path(temporary) / "out"
            owner = OwnershipLock(io_dir, "showman-consumer", {"io_dir": "different"}).acquire()
            record_before = owner.path.read_text(encoding="utf-8")
            try:
                with self.assertRaises(OwnershipConflict):
                    recorder_main(["--io-dir", str(io_dir), "--out-dir", str(out_dir)])
                self.assertEqual(owner.path.read_text(encoding="utf-8"), record_before)
                self.assertEqual(active_owner(io_dir, "showman-consumer")["pid"], os.getpid())
            finally:
                owner.close()

    def test_recorder_readiness_callback_follows_a_successful_consumer_poll(self):
        with tempfile.TemporaryDirectory() as temporary:
            root = Path(temporary)
            bridge = FileIpcBridge(root / "io", root / "out")
            calls = []
            bridge.serve(timeout=0.03, on_ready=lambda: calls.append("ready"))
            self.assertEqual(calls, ["ready"])

    def test_recorder_reports_deadline_without_stopping_a_late_ready_consumer(self):
        with tempfile.TemporaryDirectory() as temporary:
            io_dir, out_dir = Path(temporary) / "io", Path(temporary) / "out"
            original_init = FileIpcBridge.__init__
            def delayed_init(instance, *args, **kwargs):
                time.sleep(0.15)
                original_init(instance, *args, **kwargs)
            with patch.object(FileIpcBridge, "__init__", delayed_init), \
                    patch("ground_truth.file_ipc_bridge.RECORDER_STATUS_INTERVAL_SECONDS", 0.02), \
                    patch("ground_truth.file_ipc_bridge.RECORDER_READINESS_DEADLINE_SECONDS", 0.04), \
                    contextlib.redirect_stderr(io.StringIO()) as messages:
                recorder_main(["--io-dir", str(io_dir), "--out-dir", str(out_dir), "--timeout", "0.1"])
            text = messages.getvalue()
            self.assertIn("readiness deadline failed at 0.04s", text)
            self.assertIn("Recorder ready: consumer loop healthy", text)

    def test_recorder_short_timeout_reports_unready_and_releases_both_locks(self):
        with tempfile.TemporaryDirectory() as temporary:
            io_dir, out_dir = Path(temporary) / "io", Path(temporary) / "out"
            with self.assertRaisesRegex(ValueError, "readiness was not verified"):
                recorder_main(["--io-dir", str(io_dir), "--out-dir", str(out_dir), "--timeout", "0"])
            self.assertIsNone(active_owner(io_dir, "showman-consumer"))
            self.assertIsNone(active_owner(out_dir, "showman-recorder"))
            self.assertFalse((io_dir / ".showman-consumer.owner.json").exists())
            self.assertFalse((out_dir / ".showman-recorder.owner.json").exists())

    def test_recorder_early_exception_releases_both_locks(self):
        with tempfile.TemporaryDirectory() as temporary:
            io_dir, out_dir = Path(temporary) / "io", Path(temporary) / "out"
            with patch.object(FileIpcBridge, "serve", side_effect=RuntimeError("fixture exit")):
                with self.assertRaisesRegex(RuntimeError, "fixture exit"):
                    recorder_main(["--io-dir", str(io_dir), "--out-dir", str(out_dir)])
            self.assertIsNone(active_owner(io_dir, "showman-consumer"))
            self.assertIsNone(active_owner(out_dir, "showman-recorder"))


if __name__ == "__main__":
    unittest.main()
