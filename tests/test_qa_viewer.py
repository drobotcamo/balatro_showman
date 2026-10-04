import http.client
import contextlib
import io
import json
import shutil
import tempfile
import threading
import unittest
from pathlib import Path
from unittest.mock import patch

from ground_truth.qa_viewer import Review, byte_range, digest, launch_group, make_server, probe, run_ffmpeg


def source(root, name, n=23, marker=True):
    folder = root / name
    folder.mkdir()
    session = {"run_id": name, "n_steps": n, "schema_version": "producer/1.0.0", "outcome": None}
    if marker:
        session["recording"] = {"capture_timestamp_ns": 0, "fps": 10, "recording_id": "fixture"}
    (folder / "session.json").write_text(json.dumps(session))
    rows = [{"request_id": i + 1, "step_id": f"{name}:{i+1}", "capture_timestamp_ns": (i + 1) * 100000000,
             "meta": {"run_id": name}, "state": {}, "objects": [], "page_name": "In_Shop",
             "action_taken": "UseConsumable", "_recorded_action": "UseConsumable", "selected_object": None}
            for i in range(n)]
    (folder / "steps.ndjson").write_text("".join(json.dumps(row) + "\n" for row in rows))
    return folder


class ViewerTests(unittest.TestCase):
    def setUp(self):
        self.temp = tempfile.TemporaryDirectory()
        self.addCleanup(self.temp.cleanup)
        self.root = Path(self.temp.name)
        self.video = self.root / "recording.mkv"
        self.video.write_bytes(b"original video fixture")
        self.runs = [source(self.root, "a"), source(self.root, "b", 7, marker=False)]
        self.export_root = self.root / "exports"
        self.probe = patch("ground_truth.qa_viewer.probe", return_value={
            "duration": 10.0, "fps": 10, "codec_name": "h264", "constant_fps": True, "frame_count": 100,
            "presentation_origin": 0.0, "frame_timestamps": [i / 10 for i in range(100)]})
        self.probe.start()
        self.addCleanup(self.probe.stop)

    def review(self, **kwargs):
        return Review(self.video, self.runs, self.export_root, **kwargs)

    def test_next_windows_and_fragment_transition_preserve_identity(self):
        review = self.review(start_ns=0, timing_evidence="user confirmed shared video")
        first = review.window()
        second = review.window(**first["next"])
        third = review.window(**second["next"])
        fourth = review.window(**third["next"])
        self.assertEqual([len(w["rows"]) for w in (first, second, third, fourth)], [10, 10, 3, 7])
        self.assertEqual([r["original"]["request_id"] for w in (first, second, third) for r in w["rows"]], list(range(1, 24)))
        self.assertEqual(fourth["rows"][0]["original"]["step_id"], "b:1")
        self.assertIsNone(fourth["next"])
        self.assertFalse(fourth["timing"]["original_marker"])
        self.assertEqual(fourth["timing"]["alignment_status"], "unverified")

    def test_seed_replay_and_window_count_validation(self):
        a, b = self.review(seed="fixed"), self.review(seed="fixed")
        for _ in range(5):
            left, right = a.window(count=5, randomize=True), b.window(count=5, randomize=True)
            self.assertEqual((left["source_id"], left["start"], left["draw"]),
                             (right["source_id"], right["start"], right["draw"]))
        for count in (0, -1, 201, True, 1.5):
            with self.subTest(count=count), self.assertRaises(ValueError):
                a.window(count=count)
        with self.assertRaises(ValueError):
            a.window(start=23)

    def test_missing_marker_disables_clip_without_repair(self):
        before = digest(self.runs[1] / "session.json")
        window = self.review().window(source=1)
        self.assertIsNone(window["clip_start"])
        self.assertTrue(all(row["seconds"] is None for row in window["rows"]))
        with self.assertRaises(ValueError):
            self.review().export(1, 0, 10, "")
        self.assertEqual(before, digest(self.runs[1] / "session.json"))

    def test_eligibility_review_preserves_sources_and_rejects_unmeasured_confirmation(self):
        review = self.review()
        selection = review.window(source=0, start=0, count=2)
        original = digest(self.runs[0] / "steps.ndjson")
        payload = {"selection_id": selection["selection_id"], "source": 0, "index": 0, "stage": "start", "frame": 1,
                   "frame_seconds": 0.1, "alignment": "confirmed", "offset_frames": None,
                   "evidence": "rendered button visible at candidate", "visual_observation": "New Run",
                   "missingness": "", "registry_audit": "external registry not yet checked",
                   "reviewer": "human"}
        with self.assertRaisesRegex(ValueError, "measured offset"):
            review.save_eligibility(payload)
        with self.assertRaisesRegex(ValueError, "measured offset"):
            review.save_eligibility({**payload, "offset_frames": 4})
        with self.assertRaisesRegex(ValueError, "server-issued"):
            review.save_eligibility({**payload, "source": 1, "offset_frames": 0})
        with self.assertRaisesRegex(ValueError, "server-issued"):
            review.save_eligibility({**payload, "index": 2, "offset_frames": 0})
        with self.assertRaisesRegex(ValueError, "disagrees with the candidate"):
            review.save_eligibility({**payload, "offset_frames": -2})
        saved = review.save_eligibility({**payload, "offset_frames": 0})
        packet = json.loads(Path(saved["file"]).read_text())
        self.assertEqual((packet["status"], packet["offset_frames"], packet["source_run_id"]),
                         ("unscored", 0, "a"))
        self.assertEqual(packet["video_sha256"], digest(self.video))
        self.assertEqual(original, digest(self.runs[0] / "steps.ndjson"))
        self.assertNotEqual(saved["file"], review.save_eligibility({**payload, "offset_frames": 0})["file"])

    def test_eligibility_review_rejects_frame_time_mismatch_and_out_of_range(self):
        review = self.review()
        selection = review.window(source=0, start=0, count=1)
        payload = {"source": 0, "index": 0, "stage": "start", "frame": 100,
                   "selection_id": selection["selection_id"],
                   "frame_seconds": 1.0, "alignment": "unverified", "offset_frames": None,
                   "evidence": "candidate state inspected", "visual_observation": "",
                   "missingness": "", "registry_audit": "not checked", "reviewer": "human"}
        with self.assertRaisesRegex(ValueError, "outside the video duration"):
            review.save_eligibility({**payload, "frame": 100})
        with self.assertRaisesRegex(ValueError, "disagree"):
            review.save_eligibility({**payload, "frame": 10, "frame_seconds": 2.0})

    def test_viewer_rejects_variable_frame_rate_metadata(self):
        self.probe.stop()
        with patch("ground_truth.qa_viewer.probe", return_value={"duration": 10.0, "fps": 10,
                                                                 "codec_name": "h264", "constant_fps": False}):
            with self.assertRaisesRegex(ValueError, "constant-FPS"):
                Review(self.video, self.runs, self.export_root)

    def test_probe_checks_all_video_packet_presentation_timestamps(self):
        stream = {"streams": [{"codec_name": "h264", "avg_frame_rate": "10/1", "r_frame_rate": "10/1"}],
                  "format": {"duration": "0.3"}}
        def result(packet_times):
            return [type("Result", (), {"stdout": json.dumps(stream)})(),
                    type("Result", (), {"stdout": json.dumps({"packets": packet_times})})()]
        with patch("ground_truth.qa_viewer.subprocess.run", side_effect=result([
                {"pts_time": "0.000"}, {"pts_time": "0.100"}, {"pts_time": "0.200"}])):
            measured = probe(self.video)
        self.assertTrue(measured["constant_fps"])
        self.assertEqual(measured["frame_timestamps"], [0.0, 0.1, 0.2])
        with patch("ground_truth.qa_viewer.subprocess.run", side_effect=result([
                {"pts_time": "0.000"}, {"pts_time": "0.100"}, {"pts_time": "0.220"}])):
            measured = probe(self.video)
        self.assertFalse(measured["constant_fps"])
        with patch("ground_truth.qa_viewer.subprocess.run", side_effect=result([
                {"pts_time": "0.000"}, {}, {"pts_time": "0.200"}])):
            with self.assertRaisesRegex(ValueError, "lacks a presentation timestamp"):
                probe(self.video)

    def test_group_launcher_preserves_spaced_paths_and_run_grouping(self):
        output_parent = self.root / "external output"
        output_parent.mkdir()
        second_video = self.root / "recording two.mkv"
        second_video.write_bytes(b"second fixture video")
        config = {"export_root": "external output/reviews", "viewers": [
            {"video": str(self.video), "runs": [str(self.runs[0])], "export_name": "first"},
            {"video": str(second_video), "runs": [str(self.runs[0]), str(self.runs[1])]}
        ]}
        config_path = self.root / "review config.json"
        config_path.write_text(json.dumps(config), encoding="utf-8")
        launched = []

        class Process:
            pid = 42
            def poll(self):
                return None

        def popen(command, cwd, stdout, stderr, text):
            launched.append(command)
            export = command[command.index("--export-root") + 1]
            stdout.write(json.dumps({"url": f"http://127.0.0.1:{64000 + len(launched)}",
                                     "export_root": export, "seed": "fixed"}) + "\n")
            stdout.flush()
            return Process()

        with patch("sys.argv", ["qa_viewer_launch", "--config", str(config_path)]), \
                patch("ground_truth.qa_viewer.subprocess.Popen", side_effect=popen), \
                patch("urllib.request.urlopen", return_value=contextlib.nullcontext(type("Response", (), {"status": 200})())), \
                contextlib.redirect_stdout(io.StringIO()) as captured:
            launch_group()
        response = json.loads(captured.getvalue())
        self.assertEqual(len(response["viewers"]), 2)
        self.assertIn(str(self.video), launched[0])
        self.assertEqual(launched[1].count("--run"), 2)
        self.assertTrue((output_parent / "reviews" / "first").is_dir())
        self.assertTrue((output_parent / "reviews" / "02-recording-two").is_dir())

    def test_group_launcher_rejects_child_that_exits_during_readiness_probe(self):
        output_parent = self.root / "external output"
        output_parent.mkdir()
        config_path = self.root / "review config.json"
        config_path.write_text(json.dumps({"export_root": "external output/reviews", "viewers": [
            {"video": str(self.video), "runs": [str(self.runs[0])]}
        ]}), encoding="utf-8")

        class ExitingProcess:
            pid = 43
            calls = 0
            alive = True
            def poll(self):
                self.calls += 1
                return None if self.alive else 1

        process = ExitingProcess()
        def popen(command, cwd, stdout, stderr, text):
            stdout.write(json.dumps({"url": "http://127.0.0.1:64001",
                                     "export_root": "external", "seed": "fixed"}) + "\n")
            stdout.flush()
            return process

        def urlopen(*args, **kwargs):
            process.alive = False
            return contextlib.nullcontext(type("Response", (), {"status": 200})())

        with patch("sys.argv", ["qa_viewer_launch", "--config", str(config_path)]), \
                patch("ground_truth.qa_viewer.subprocess.Popen", side_effect=popen), \
                patch("urllib.request.urlopen", side_effect=urlopen), \
                contextlib.redirect_stderr(io.StringIO()) as errors:
            with self.assertRaises(SystemExit):
                launch_group()
        self.assertIn("exited during readiness probe", errors.getvalue())

    def test_export_rejects_changed_sources_and_overlapping_destinations(self):
        with self.assertRaises(ValueError):
            Review(self.video, self.runs, self.runs[0] / "exports")
        with self.assertRaises(ValueError):
            Review(self.video, self.runs, self.root)
        with self.assertRaises(ValueError):
            self.review(start_ns=0)
        review = self.review()
        review.media = self.video
        review.media_hash = digest(self.video)
        (self.runs[0] / "session.json").write_text("changed")
        with self.assertRaisesRegex(ValueError, "source changed"):
            review.export(0, 0, 10, "")

    def test_ranges_and_http_boundaries(self):
        for header, expected in ((None, (0, 9, False)), ("bytes=2-5", (2, 5, True)),
                                 ("bytes=6-", (6, 9, True)), ("bytes=-3", (7, 9, True))):
            self.assertEqual(byte_range(header, 10), expected)
        for header in ("bytes=20-", "bytes=4-2", "bytes=-0", "bytes=0-1,4-5", "bytes=-"):
            with self.assertRaises(ValueError):
                byte_range(header, 10)
        review = self.review()
        review.media = self.video
        server = make_server(review)
        thread = threading.Thread(target=server.serve_forever, daemon=True)
        thread.start()
        try:
            conn = http.client.HTTPConnection("127.0.0.1", server.server_port)
            conn.request("GET", "/media", headers={"Range": "bytes=0-7"})
            response = conn.getresponse()
            self.assertEqual(response.status, 206)
            self.assertEqual(response.read(), b"original")
            conn.request("HEAD", "/media", headers={"Range": "bytes=-5"})
            response = conn.getresponse()
            self.assertEqual(response.status, 206)
            self.assertEqual(response.getheader("Content-Length"), "5")
            self.assertEqual(response.read(), b"")
            conn.request("GET", "/media", headers={"Range": "bytes=999-"})
            response = conn.getresponse()
            self.assertEqual(response.status, 416)
            response.read()
            conn.request("GET", "/api/init")
            response = conn.getresponse()
            token = json.loads(response.read())["token"]
            for headers in ({}, {"X-Review-Token": token, "Origin": "https://example.com"}):
                conn.request("POST", "/api/export", "{}", headers=headers)
                response = conn.getresponse()
                self.assertEqual(response.status, 403)
                response.read()
            conn.request("GET", "/../../recording.mkv")
            response = conn.getresponse()
            self.assertEqual(response.status, 404)
            response.read()
            conn.request("GET", "/", headers={"Host": "example.com"})
            response = conn.getresponse()
            self.assertEqual(response.status, 403)
            response.read()
            conn.close()
        finally:
            server.shutdown()
            server.server_close()
            thread.join()

    def test_partial_metadata_is_diagnosed_and_source_change_during_export_fails(self):
        path = self.runs[0] / "steps.ndjson"
        rows = [json.loads(line) for line in path.read_text().splitlines()]
        rows[0].pop("capture_timestamp_ns")
        rows[0]["meta"] = [1]
        path.write_text("".join(json.dumps(row) + "\n" for row in rows))
        review = self.review()
        self.assertIsNone(review.window()["rows"][0]["seconds"])
        self.assertTrue(review.window()["timing"]["diagnostics"])
        review.media, review.media_hash = self.video, digest(self.video)
        self.export_root.mkdir()

        def mutate_during_extraction(arguments):
            Path(arguments[-1]).write_bytes(b"derived clip")
            path.write_bytes(path.read_bytes() + b"\n")

        with patch("ground_truth.qa_viewer.run_ffmpeg", side_effect=mutate_during_extraction):
            with self.assertRaisesRegex(ValueError, "source changed"):
                review.export(0, 1, 5, "")
        incomplete = list(self.export_root.glob("review-*/INCOMPLETE.txt"))
        self.assertEqual(len(incomplete), 1)
        self.assertFalse(incomplete[0].with_name("manifest.json").exists())

    @unittest.skipUnless(shutil.which("ffmpeg") and shutil.which("ffprobe"), "existing ffmpeg required")
    def test_real_media_export_preserves_original_lines_and_hashes(self):
        self.probe.stop()
        self.video = self.root / "real.mp4"
        run_ffmpeg(["-f", "lavfi", "-i", "color=c=green:s=160x90:r=10", "-t", "4",
                    "-c:v", "libx264", "-pix_fmt", "yuv420p", str(self.video)])
        before = {path: digest(path) for folder in self.runs for path in folder.iterdir()}
        before[self.video] = digest(self.video)
        review = self.review()
        review.prepare_media()
        media = review.media
        with patch("ground_truth.qa_viewer.run_ffmpeg", side_effect=AssertionError("verified cache should be reused")):
            review.prepare_media()
        self.assertEqual(review.media, media)
        selection = review.window(0, 1, 5)
        review.window(count=1, randomize=True)
        result = review.export(0, 1, 5, "literal </script> note", selection["selection_id"])
        folder = Path(result["folder"])
        packet = json.loads((folder / "manifest.json").read_text())
        self.assertEqual(packet["status"], "unscored")
        self.assertEqual(packet["notes"], "literal </script> note")
        self.assertEqual(packet["window"]["draw"], 0)
        self.assertFalse((folder / "INCOMPLETE.txt").exists())
        original_lines = (self.runs[0] / "steps.ndjson").read_bytes().splitlines(keepends=True)
        self.assertEqual((folder / "actions.ndjson").read_bytes(), b"".join(original_lines[1:6]))
        for name, expected in packet["files"].items():
            self.assertEqual(digest(folder / name), expected)
        self.assertEqual(before, {path: digest(path) for path in before})
        self.assertNotIn('literal </script> note', (folder / "index.html").read_text(encoding="utf-8"))


if __name__ == "__main__":
    unittest.main()
