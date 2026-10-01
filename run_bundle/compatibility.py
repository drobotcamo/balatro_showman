"""Read-only compatibility access to legacy Lua oracle run directories."""

import json
import hashlib
from pathlib import Path

from planning.audit_oracle_runs import REQUIRED_TOP_LEVEL, REQUIRED_BY_SCHEMA


def read_oracle_run(path):
    """Read ``session.json`` and ``steps.ndjson`` without modifying either file.

    The returned dictionary deliberately retains the source objects.  It is an
    adapter for inspection, not a converter to the SQLite bundle.
    """
    root = Path(path)
    diagnostics = []
    session_path, steps_path = root / "session.json", root / "steps.ndjson"
    if not session_path.is_file() or not steps_path.is_file():
        missing = [p.name for p in (session_path, steps_path) if not p.is_file()]
        return _result("malformed", None, [], "unknown", diagnostics + [
            {"code": "missing_file", "field": name, "message": f"missing {name}"}
            for name in missing])
    source = {"directory": str(root), "files": {
        name: {"size": file.stat().st_size, "sha256": _sha256(file)}
        for name, file in (("session.json", session_path), ("steps.ndjson", steps_path))}}
    try:
        session = json.loads(session_path.read_text(encoding="utf-8"))
        if not isinstance(session, dict):
            raise ValueError("session must be an object")
        steps = []
        for number, line in enumerate(steps_path.read_text(encoding="utf-8").splitlines(), 1):
            try:
                value = json.loads(line)
            except (UnicodeDecodeError, json.JSONDecodeError) as exc:
                return _result("malformed", session, steps, "unknown", diagnostics +
                    [{"code": "invalid_step", "field": f"steps.ndjson:{number}", "message": str(exc)}])
            if not isinstance(value, dict):
                return _result("malformed", session, steps, "unknown", diagnostics +
                    [{"code": "invalid_step", "field": f"steps.ndjson:{number}", "message": "step must be an object"}])
            steps.append(value)
    except (OSError, UnicodeDecodeError, json.JSONDecodeError, ValueError) as exc:
        return _result("malformed", None, [], "unknown", [{"code": "invalid_source", "message": str(exc)}])

    missing = []
    required = REQUIRED_BY_SCHEMA.get(session.get("schema_version"), REQUIRED_TOP_LEVEL)
    for index, step in enumerate(steps):
        missing.extend(f"step[{index}].{field}" for field in required if field not in step)
    if session.get("n_steps") != len(steps):
        diagnostics.append({"code": "step_count_mismatch", "field": "n_steps", "message": "session count differs from parsed steps"})
    if missing:
        diagnostics.append({"code": "missing_fields", "field": "steps", "message": ", ".join(missing)})
    recording = session.get("recording") or session.get("recording_metadata") or {}
    meta = steps[0].get("meta", {}) if steps else {}
    if not isinstance(recording, dict) or not isinstance(meta, dict):
        diagnostics.append({"code": "invalid_metadata", "field": "recording/meta", "message": "metadata must be an object"})
        recording = recording if isinstance(recording, dict) else {}
        meta = meta if isinstance(meta, dict) else {}
    video_status = "obs" if isinstance(recording.get("recording_id") or meta.get("recording_id"), str) else "no-video"
    if not steps:
        diagnostics.append({"code": "no_steps", "field": "steps.ndjson", "message": "no steps parsed"})
    return _result("healthy" if not diagnostics else "partial", session, steps, video_status, diagnostics, source)


def _result(classification, session, steps, video_status, diagnostics, source=None):
    result = {"classification": classification, "video_status": video_status,
            "session": session, "steps": steps, "run_id": session.get("run_id") if session else None,
            "step_count": len(steps), "diagnostics": diagnostics}
    if source is not None:
        result["source"] = source
    return result


def _sha256(path):
    return hashlib.sha256(path.read_bytes()).hexdigest()
