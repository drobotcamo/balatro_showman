"""OBS Python hook for the Issue #35 recording-start handshake."""

from __future__ import annotations

import json
import os
import tempfile
from datetime import datetime, timezone
from pathlib import Path

try:
    import obspython as obs
except ImportError:
    obs = None

io_dir = str(Path(os.environ.get("APPDATA", "")) / "Balatro" / "agent_io")
fps = 60.0
recording_prefix = "issue35"


def recording_start_request(recording_id: str, recording_fps: float) -> dict[str, object]:
    if not recording_id or recording_fps <= 0:
        raise ValueError("recording_id must be non-empty and fps must be positive")
    return {"schema_version": "producer/1.0.0", "recording_id": recording_id, "fps": recording_fps}


def write_request(directory: str, recording_id: str, recording_fps: float) -> Path:
    target = Path(directory) / "recording_start.json"
    target.parent.mkdir(parents=True, exist_ok=True)
    payload = json.dumps(recording_start_request(recording_id, recording_fps), separators=(",", ":"))
    with tempfile.NamedTemporaryFile("w", encoding="utf-8", dir=target.parent, delete=False) as stream:
        stream.write(payload + "\n")
        temporary = Path(stream.name)
    os.replace(temporary, target)
    return target


def on_event(event: int) -> None:
    if obs is None or event != obs.OBS_FRONTEND_EVENT_RECORDING_STARTED:
        return
    recording_id = f"{recording_prefix}-{datetime.now(timezone.utc).strftime('%Y%m%dT%H%M%SZ')}"
    write_request(io_dir, recording_id, fps)
    obs.script_log(obs.LOG_INFO, f"Balatro handshake requested: {recording_id}")


def script_description() -> str:
    return "Writes the Balatro handshake when OBS recording starts."


def script_properties() -> object:
    properties = obs.obs_properties_create()
    obs.obs_properties_add_text(properties, "io_dir", "Balatro agent_io directory", obs.OBS_TEXT_DEFAULT)
    obs.obs_properties_add_float(properties, "fps", "Recording FPS", 0.001, 1000.0, 0.001)
    obs.obs_properties_add_text(properties, "recording_prefix", "Recording ID prefix", obs.OBS_TEXT_DEFAULT)
    return properties


def script_update(settings: object) -> None:
    global io_dir, fps, recording_prefix
    io_dir = obs.obs_data_get_string(settings, "io_dir") or io_dir
    fps = obs.obs_data_get_double(settings, "fps") or fps
    recording_prefix = obs.obs_data_get_string(settings, "recording_prefix") or recording_prefix


def script_load(settings: object) -> None:
    script_update(settings)
    obs.obs_frontend_add_event_callback(on_event)


def script_unload() -> None:
    if obs is not None:
        obs.obs_frontend_remove_event_callback(on_event)
