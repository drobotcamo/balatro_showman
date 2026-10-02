import json

from ground_truth.recording_association import associate_recording
from run_bundle import RunBundle, RunBundleInspector, read_oracle_run


def _step():
    return {"schema_version": "live/2.0.0", "step_id": 1,
            "capture_timestamp_ns": 1, "request_id": "r1",
            "page_name": "In_Shop", "state": {}, "objects": [],
            "pending_cards": [], "persistent_state": {},
            "action_taken": None, "meta": {}}


def _oracle_run(path, *, recording=None, n_steps=1):
    session = {"run_id": "r1", "schema_version": "live/2.0.0", "n_steps": n_steps}
    if recording is not None:
        session["recording"] = recording
    (path / "session.json").write_text(json.dumps(session), encoding="utf-8")
    (path / "steps.ndjson").write_text(json.dumps(_step()) + "\n", encoding="utf-8")


def test_phase9_boundary_covers_legacy_cases_without_source_mutation(tmp_path):
    _oracle_run(tmp_path, n_steps=2)
    before = (tmp_path / "session.json").read_bytes(), (tmp_path / "steps.ndjson").read_bytes()

    result = read_oracle_run(tmp_path)

    assert result["classification"] == "partial"
    assert result["video_status"] == "no-video"
    assert any(d["code"] == "step_count_mismatch" for d in result["diagnostics"])
    assert ((tmp_path / "session.json").read_bytes(),
            (tmp_path / "steps.ndjson").read_bytes()) == before


def test_phase9_boundary_keeps_confirmed_recording_additive(tmp_path):
    from alembic import command
    from alembic.config import Config

    url = f"sqlite:///{tmp_path / 'run.db'}"
    config = Config("alembic.ini")
    config.set_main_option("sqlalchemy.url", url)
    command.upgrade(config, "head")
    bundle = RunBundle(url)
    bundle.create("r1", producer_version="test")
    bundle.append("r1", 0, "state", {"chips": 1})
    before = bundle.validate("r1")

    marker = {"schema_version": "producer/1.0.0", "recording_id": "obs-1",
              "fps": 60, "capture_timestamp_ns": 100}
    result = associate_recording(bundle, "r1", confirmed=True, marker=marker,
                                video_ref="capture.mkv")

    assert result.status == "confirmed"
    assert bundle.validate("r1") == before
    inspected = RunBundleInspector(url)
    assert inspected.capabilities("r1")["data"]["read_only"] is True
    provenance = inspected.provenance("r1")
    assert provenance["status"] == "observed"
    assert any(item["key"] == "recording.recording_id" and item["value"] == "obs-1"
               for item in provenance["data"])
