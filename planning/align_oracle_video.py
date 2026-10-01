"""Map producer timestamps to video frames.

Recording start and step timestamps must use the producer's monotonic clock.
Capture the producer clock at recording start (not the wall-clock video
timestamp). The result is a zero-based nearest frame index.
"""

from __future__ import annotations

import argparse
import json
from pathlib import Path


def frame_index(step_timestamp_ns: int, recording_start_ns: int, fps: float) -> int:
    if fps <= 0:
        raise ValueError("fps must be positive")
    return round((step_timestamp_ns - recording_start_ns) / 1_000_000_000 * fps)


def main() -> int:
    parser = argparse.ArgumentParser()
    parser.add_argument("steps", type=Path)
    parser.add_argument("--recording-start-ns", type=int)
    parser.add_argument("--fps", type=float)
    args = parser.parse_args()
    session = json.loads((args.steps.parent / "session.json").read_text(encoding="utf-8"))
    recording = session.get("recording") or {}
    recording_start_ns = args.recording_start_ns or recording.get("capture_timestamp_ns")
    recording_fps = args.fps or recording.get("fps")
    if recording_start_ns is None or recording_fps is None:
        raise SystemExit("steps directory session.json lacks recording marker metadata")
    for line in args.steps.read_text(encoding="utf-8").splitlines():
        if line.strip():
            step = json.loads(line)
            meta = step.get("meta", {})
            print(json.dumps({"step_id": step["step_id"], "frame_idx": frame_index(
                meta["video_timestamp_ns"], recording_start_ns, recording_fps
            )}))
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
