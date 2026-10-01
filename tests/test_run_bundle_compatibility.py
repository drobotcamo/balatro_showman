import json

from run_bundle import read_oracle_run


def write_run(tmp_path, session, steps):
    (tmp_path / "session.json").write_text(json.dumps(session), encoding="utf-8")
    (tmp_path / "steps.ndjson").write_text("".join(json.dumps(s) + "\n" for s in steps), encoding="utf-8")


def step(schema="live/2.0.0"):
    return {"schema_version": schema, "step_id": 1, "capture_timestamp_ns": 1,
            "request_id": "r1", "page_name": "In_Shop", "state": {}, "objects": [],
            "pending_cards": [], "persistent_state": {}, "action_taken": None, "meta": {}}


def test_reads_legacy_run_and_preserves_fields(tmp_path):
    write_run(tmp_path, {"run_id": "r", "schema_version": "live/2.0.0", "n_steps": 1}, [step()])
    result = read_oracle_run(tmp_path)
    assert result["classification"] == "healthy"
    assert result["video_status"] == "no-video"
    assert result["steps"][0]["page_name"] == "In_Shop"
    assert result["source"]["files"]["session.json"]["sha256"]


def test_partial_and_obs_metadata_are_explicit(tmp_path):
    item = step("live/3.0.0")
    write_run(tmp_path, {"run_id": "r", "schema_version": "live/3.0.0", "n_steps": 2,
                         "recording": {"recording_id": "obs-1"}}, [item])
    result = read_oracle_run(tmp_path)
    assert result["classification"] == "partial"
    assert result["video_status"] == "obs"
    assert any(d["code"] == "step_count_mismatch" for d in result["diagnostics"])


def test_malformed_source_is_diagnostic_and_missing_files_do_not_get_created(tmp_path):
    result = read_oracle_run(tmp_path)
    assert result["classification"] == "malformed"
    assert not (tmp_path / "session.json").exists()


def test_malformed_json_and_non_object_steps_are_reported_without_mutation(tmp_path):
    session = tmp_path / "session.json"
    steps = tmp_path / "steps.ndjson"
    session.write_text("{bad", encoding="utf-8")
    steps.write_text("[]\n", encoding="utf-8")
    before = (session.read_bytes(), steps.read_bytes())
    assert read_oracle_run(tmp_path)["classification"] == "malformed"
    assert (session.read_bytes(), steps.read_bytes()) == before

    session.write_text(json.dumps({"n_steps": 1}), encoding="utf-8")
    steps.write_text("[]\n", encoding="utf-8")
    result = read_oracle_run(tmp_path)
    assert result["classification"] == "malformed"
    assert any(d["code"] == "invalid_step" for d in result["diagnostics"])


def test_non_string_recording_id_is_not_obs(tmp_path):
    write_run(tmp_path, {"run_id": "r", "n_steps": 1, "recording": {"recording_id": 7}}, [step()])
    assert read_oracle_run(tmp_path)["video_status"] == "no-video"


def test_malformed_metadata_is_partial_not_an_exception(tmp_path):
    item = step()
    item["meta"] = []
    write_run(tmp_path, {"run_id": "r", "n_steps": 1}, [item])
    result = read_oracle_run(tmp_path)
    assert result["classification"] == "partial"
    assert any(d["code"] == "invalid_metadata" for d in result["diagnostics"])
