import unittest

from planning.align_oracle_video import frame_index


class AlignmentTests(unittest.TestCase):
    def test_maps_timestamp_to_nearest_zero_based_frame(self) -> None:
        self.assertEqual(frame_index(1_016_666_667, 1_000_000_000, 60), 1)

    def test_supports_steps_before_recording_start_for_diagnostics(self) -> None:
        self.assertEqual(frame_index(900_000_000, 1_000_000_000, 30), -3)

    def test_rejects_non_positive_fps(self) -> None:
        with self.assertRaises(ValueError):
            frame_index(1, 1, 0)
