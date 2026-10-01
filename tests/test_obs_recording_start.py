import tempfile
import unittest
from pathlib import Path

from ground_truth.obs_recording_start import recording_start_request, write_request


class ObsRecordingStartTests(unittest.TestCase):
    def test_request_shape(self) -> None:
        self.assertEqual(recording_start_request("obs-1", 60), {
            "schema_version": "producer/1.0.0", "recording_id": "obs-1", "fps": 60,
        })

    def test_request_is_written_atomically(self) -> None:
        with tempfile.TemporaryDirectory() as directory:
            target = write_request(directory, "obs-1", 60)
            self.assertTrue(target.is_file())
            self.assertIn('"recording_id":"obs-1"', target.read_text(encoding="utf-8"))
            self.assertEqual(list(Path(directory).glob("*.tmp")), [])

    def test_rejects_invalid_configuration(self) -> None:
        with self.assertRaises(ValueError):
            recording_start_request("", 60)
        with self.assertRaises(ValueError):
            recording_start_request("obs-1", 0)
