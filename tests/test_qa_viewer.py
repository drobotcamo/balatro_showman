import http.client
import json
import shutil
import tempfile
import threading
import unittest
from pathlib import Path
from unittest.mock import patch

from ground_truth.qa_viewer import Review, byte_range, digest, make_server, run_ffmpeg


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
        self.probe = patch("ground_truth.qa_viewer.probe", return_value={"duration": 10.0, "fps": 10, "constant_fps": True})
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
        original = digest(self.runs[0] / "steps.ndjson")
        payload = {"source": 0, "index": 0, "stage": "start", "frame": 1,
                   "frame_seconds": 0.1, "alignment": "confirmed", "offset_frames": None,
                   "evidence": "rendered button visible at candidate", "visual_observation": "New Run",
                   "missingness": "", "registry_audit": "external registry not yet checked",
                   "reviewer": "human"}
        with self.assertRaisesRegex(ValueError, "measured offset"):
            review.save_eligibility(payload)
        with self.assertRaisesRegex(ValueError, "measured offset"):
            review.save_eligibility({**payload, "offset_frames": 4})
        with self.assertRaisesRegex(ValueError, "in-range candidate"):
            review.save_eligibility({**payload, "source": 1, "offset_frames": 0})
        saved = review.save_eligibility({**payload, "offset_frames": -2})
        packet = json.loads(Path(saved["file"]).read_text())
        self.assertEqual((packet["status"], packet["offset_frames"], packet["source_run_id"]),
                         ("unscored", -2, "a"))
        self.assertEqual(packet["video_sha256"], digest(self.video))
        self.assertEqual(original, digest(self.runs[0] / "steps.ndjson"))
        self.assertNotEqual(saved["file"], review.save_eligibility({**payload, "offset_frames": 0})["file"])

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
