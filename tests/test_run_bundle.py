import pytest
import sqlite3
import json
import hashlib
from alembic import command
from alembic.config import Config
from run_bundle import RunBundle, BundleError, ImportConflict, InvalidTransition, FinalizedEvidenceError
from run_bundle import RunBundleInspector

def bundle(tmp_path):
    url = f"sqlite:///{tmp_path / 'run.db'}"
    cfg = Config("alembic.ini"); cfg.set_main_option("sqlalchemy.url", url); command.upgrade(cfg, "head")
    b = RunBundle(url); b.create("r1", producer_version="test"); return b

def test_lifecycle_and_immutable_evidence(tmp_path):
    b = bundle(tmp_path); b.append("r1", 0, "state", {"chips": 1}); b.transition("r1", "won")
    assert b.validate("r1") == {"status": "valid", "record_count": 1, "bad_sequences": []}
    with pytest.raises(FinalizedEvidenceError): b.append("r1", 1, "state", {})

@pytest.mark.parametrize("outcome", ["interrupted", "incomplete", "completed", "won", "lost", "endless", "aborted"])
def test_all_outcomes(tmp_path, outcome):
    b = bundle(tmp_path); b.transition("r1", outcome)

def test_invalid_transition(tmp_path):
    b = bundle(tmp_path); b.transition("r1", "won")
    with pytest.raises(InvalidTransition): b.transition("r1", "lost")

def test_interrupted_must_resume_or_finish(tmp_path):
    b = bundle(tmp_path); b.transition("r1", "interrupted")
    with pytest.raises(InvalidTransition): b.transition("r1", "interrupted")

def test_raw_malformed_and_duplicate(tmp_path):
    b = bundle(tmp_path); b.append_raw("r1", 0, "partial", b"{not-json")
    with pytest.raises(BundleError): b.append("r1", 0, "state", {})

def test_upgrade_from_previous_revision(tmp_path):
    url = f"sqlite:///{tmp_path / 'upgrade.db'}"
    cfg = Config("alembic.ini"); cfg.set_main_option("sqlalchemy.url", url)
    command.upgrade(cfg, "0001_run_bundle")
    with sqlite3.connect(tmp_path / "upgrade.db") as db:
        db.execute("insert into runs values ('legacy', 'active', 'old', '1.0', CURRENT_TIMESTAMP, NULL, NULL, 'unknown')")
        db.execute("insert into records values (1, 'legacy', 0, 'state', ?, ?, 'valid')", ('{\"chips\":1}', 'x' * 64))
        db.execute("insert into records values (2, 'legacy', 1, 'state', ?, ?, 'valid')", ('{\"label\":\"é\"}', 'y' * 64))
        db.commit()
    command.upgrade(cfg, "head")
    with sqlite3.connect(tmp_path / "upgrade.db") as db:
        assert db.execute("select version_num from alembic_version").fetchone()[0] == "0003_binary_evidence"
        assert db.execute("select payload from records where run_id = 'legacy'").fetchone()[0] == b'{"chips":1}'
        assert db.execute("select payload from records where sequence = 1").fetchone()[0] == '{"label":"é"}'.encode()

def test_integrity_failure_is_persisted_and_strict_validation_reports(tmp_path):
    b = bundle(tmp_path); b.append("r1", 0, "state", {"chips": 1})
    with sqlite3.connect(tmp_path / "run.db") as db:
        db.execute("update records set payload = '{\"chips\":2}' where run_id = 'r1'"); db.commit()
    with pytest.raises(BundleError, match="integrity failure"):
        b.validate("r1", strict=True)
    assert b.validate("r1")["status"] == "invalid"
    with sqlite3.connect(tmp_path / "run.db") as db:
        assert db.execute("select result from integrity where run_id = 'r1'").fetchone()[0] == "invalid"

def test_raw_bytes_are_preserved(tmp_path):
    b = bundle(tmp_path); raw = b"\xff\xfe{partial"
    b.append_raw("r1", 0, "partial", raw)
    assert b.validate("r1")["status"] == "invalid"
    with sqlite3.connect(tmp_path / "run.db") as db:
        assert db.execute("select payload from records").fetchone()[0] == raw

def test_invalid_raw_integrity_survives_finalization(tmp_path):
    b = bundle(tmp_path); b.append_raw("r1", 0, "partial", b"bad")
    with sqlite3.connect(tmp_path / "run.db") as db:
        assert db.execute("select integrity_status from runs").fetchone()[0] == "invalid"
    b.transition("r1", "aborted")
    with sqlite3.connect(tmp_path / "run.db") as db:
        assert db.execute("select integrity_status from runs").fetchone()[0] == "invalid"
        assert db.execute("select result from integrity").fetchone()[0] == "invalid"

def test_valid_append_does_not_mask_invalid_record(tmp_path):
    b = bundle(tmp_path); b.append_raw("r1", 0, "partial", b"bad")
    b.append("r1", 1, "state", {"ok": True})
    assert b.validate("r1")["status"] == "invalid"

def test_tampered_aggregate_is_reported(tmp_path):
    b = bundle(tmp_path); b.append("r1", 0, "state", {"ok": True})
    with sqlite3.connect(tmp_path / "run.db") as db:
        db.execute("update integrity set bundle_sha256 = ?", ("0" * 64,)); db.commit()
    with pytest.raises(BundleError, match="integrity failure"):
        b.validate("r1", strict=True)

@pytest.mark.parametrize("column,value", [("record_count", "99"), ("result", "invalid")])
def test_tampered_aggregate_metadata_is_reported(tmp_path, column, value):
    b = bundle(tmp_path); b.append("r1", 0, "state", {"ok": True})
    with sqlite3.connect(tmp_path / "run.db") as db:
        db.execute(f"update integrity set {column} = ?", (value,)); db.commit()
    with pytest.raises(BundleError, match="integrity failure"):
        b.validate("r1", strict=True)

def test_healthy_active_run_validates(tmp_path):
    b = bundle(tmp_path); b.append("r1", 0, "state", {"ok": True})
    assert b.validate("r1") == {"status": "valid", "record_count": 1, "bad_sequences": []}

def test_explicit_invalid_status_is_strict_failure(tmp_path):
    b = bundle(tmp_path); b.append_raw("r1", 0, "partial", b"bad")
    with pytest.raises(BundleError, match="integrity failure"):
        b.validate("r1", strict=True)

def test_file_ipc_oracle_import_is_queryable_with_usage_and_source_provenance(tmp_path):
    url = f"sqlite:///{tmp_path / 'import.db'}"
    cfg = Config("alembic.ini"); cfg.set_main_option("sqlalchemy.url", url); command.upgrade(cfg, "head")
    source = tmp_path / "oracle" / "live-run"
    source.mkdir(parents=True)
    session = {
        "run_id": "live-run", "schema_version": "producer/1.0.0",
        "started_at": "2026-10-03T03:28:55.076059+00:00",
        "ended_at": "2026-10-03T03:29:37.964304+00:00", "outcome": "loss", "n_steps": 2,
        "usage": {
            "action_counts": {"PlayHand": 1, "DiscardHand": 1}, "unique_action_count": 2,
            "first_recorded_at": "2026-10-03T03:28:55.079178+00:00",
            "last_recorded_at": "2026-10-03T03:29:35.473195+00:00",
        },
        "recording": {"recording_id": "obs-1", "fps": 60.0},
    }
    steps = [
        {"request_id": 1, "_recorded_action": "PlayHand", "_recorded_at": "2026-10-03T03:28:55.079178+00:00"},
        {"request_id": 2, "_recorded_action": "DiscardHand", "_recorded_at": "2026-10-03T03:29:35.473195+00:00"},
    ]
    session_path = source / "session.json"
    steps_path = source / "steps.ndjson"
    session_path.write_text(json.dumps(session), encoding="utf-8")
    steps_path.write_text("".join(json.dumps(step) + "\n" for step in steps), encoding="utf-8")

    result = RunBundle(url).import_oracle_directory(source)
    assert result == {"run_id": "live-run", "record_count": 2, "status": "lost"}
    inspector = RunBundleInspector(url)
    summary = inspector.summary("live-run")["data"]
    assert summary["run"]["status"] == "lost"
    assert summary["run"]["outcome"] == "lost"
    assert summary["run"]["integrity_status"] == "valid"
    assert summary["run"]["created_at"] == "2026-10-03T03:28:55.076059"
    assert summary["run"]["finalized_at"] == "2026-10-03T03:29:37.964304"
    assert summary["integrity"]["result"] == "valid"
    assert inspector.find_records("live-run", kind="step")["data"][0]["payload"] == steps[0]
    provenance = {item["key"]: item["value"] for item in inspector.provenance("live-run")["data"]}
    assert json.loads(provenance["oracle.usage"]) == session["usage"]
    assert json.loads(provenance["oracle.recording"]) == session["recording"]
    assert provenance["oracle.source_session_sha256"] == hashlib.sha256(session_path.read_bytes()).hexdigest()
    assert provenance["oracle.source_steps_sha256"] == hashlib.sha256(steps_path.read_bytes()).hexdigest()
    assert RunBundle(url).import_oracle_directory(source)["already_imported"] is True

def test_mechanics_reference_import_and_read_are_separate_from_steps(tmp_path):
    url = f"sqlite:///{tmp_path / 'reference.db'}"
    cfg = Config("alembic.ini"); cfg.set_main_option("sqlalchemy.url", url); command.upgrade(cfg, "head")
    source = tmp_path / "oracle" / "dagger"
    source.mkdir(parents=True)
    (source / "session.json").write_text(json.dumps({
        "run_id": "dagger", "schema_version": "producer/1.0.0",
        "started_at": "2026-10-04T00:00:00+00:00", "ended_at": "2026-10-04T00:00:01+00:00",
        "outcome": "loss", "n_steps": 1,
    }), encoding="utf-8")
    step = {"request_id": 1, "_recorded_action": "SelectBlind", "action": "SelectBlind"}
    (source / "steps.ndjson").write_text(json.dumps(step) + "\n", encoding="utf-8")
    reference = {
        "schema_version": "dagger-reference/1.0", "run_id": "dagger", "step_id": "dagger:1",
        "capture_phase": "pre_action", "capture_timestamp_ns": 123,
        "producer_revision": "test", "runtime": {"balatro": "1.0.1", "steamodded": "test", "lovely": "test"},
        "jokers": [{"role": "joker", "position": 0,
            "center_key": "j_dagger", "instance_token": "engine-7", "mult": 62, "sell_cost": 8}],
    }
    (source / "mechanics_reference.ndjson").write_text(json.dumps(reference) + "\n", encoding="utf-8")

    assert RunBundle(url).import_oracle_directory(source)["record_count"] == 2
    inspector = RunBundleInspector(url)
    assert inspector.find_records("dagger", kind="step")["data"][0]["payload"] == step
    assert all(item["kind"] != "mechanics_reference" for item in inspector.find_records("dagger")["data"])
    assert all(item["kind"] != "mechanics_reference" for item in inspector.evidence("dagger")["data"])
    result = inspector.mechanics_reference("dagger", step_id="dagger:1")
    assert result["data"][0]["payload"] == reference
    assert inspector.mechanics_reference("dagger", step_id="dagger:missing")["status"] == "missing"
    (source / "mechanics_reference.ndjson").write_text(
        json.dumps({**reference, "capture_timestamp_ns": 124}) + "\n", encoding="utf-8")
    with pytest.raises(ImportConflict, match="different source identity"):
        RunBundle(url).import_oracle_directory(source)

def test_file_ipc_retry_conflicts_when_same_run_id_has_different_source(tmp_path):
    url = f"sqlite:///{tmp_path / 'conflict.db'}"
    cfg = Config("alembic.ini"); cfg.set_main_option("sqlalchemy.url", url); command.upgrade(cfg, "head")
    sources = [tmp_path / "source-a", tmp_path / "source-b"]
    for source, action in zip(sources, ("PlayHand", "DiscardHand")):
        source.mkdir()
        (source / "session.json").write_text(json.dumps({
            "run_id": "same-id", "started_at": "2026-10-03T03:28:55+00:00",
            "outcome": None, "n_steps": 1,
        }), encoding="utf-8")
        (source / "steps.ndjson").write_text(json.dumps({"_recorded_action": action}) + "\n", encoding="utf-8")
    bundle = RunBundle(url)
    bundle.import_oracle_directory(sources[0])
    with pytest.raises(BundleError, match="different source identity"):
        bundle.import_oracle_directory(sources[1])
    assert sources[0].joinpath("steps.ndjson").exists()
    assert sources[1].joinpath("steps.ndjson").exists()

def test_source_neutral_video_envelope_is_queryable(tmp_path):
    url = f"sqlite:///{tmp_path / 'video-envelope.db'}"
    cfg = Config("alembic.ini"); cfg.set_main_option("sqlalchemy.url", url); command.upgrade(cfg, "head")
    RunBundle(url).ingest_run({
        "run_id": "video-derived-1", "source_type": "video-reconstruction",
        "source_identity": "video:sha256:abc123/revision:7", "producer_version": "reconstructor/0.1",
        "status": "completed", "outcome": "completed",
        "provenance": {
            "source.type": "video-reconstruction", "source.identity": "video:sha256:abc123/revision:7",
            "video.sha256": "abc123", "processing.revision": "7", "frame_refs": "unknown",
        },
    }, [{"kind": "frame-observation", "payload": {"frame": 12, "state": "unknown", "confidence": None}}])
    inspector = RunBundleInspector(url)
    assert inspector.summary("video-derived-1")["data"]["run"]["status"] == "completed"
    assert inspector.find_records("video-derived-1")["data"][0]["payload"]["state"] == "unknown"
    provenance = {item["key"]: item["value"] for item in inspector.provenance("video-derived-1")["data"]}
    assert provenance["video.sha256"] == "abc123"

@pytest.mark.parametrize("status,outcome", [("won", None), ("won", "loss"), ("lost", "not-a-real-outcome"), ("completed", {"value": "won"})])
def test_source_neutral_api_rejects_invalid_or_conflicting_outcome(tmp_path, status, outcome):
    url = f"sqlite:///{tmp_path / 'invalid-outcome.db'}"
    cfg = Config("alembic.ini"); cfg.set_main_option("sqlalchemy.url", url); command.upgrade(cfg, "head")
    envelope = {
        "run_id": "bad-envelope", "source_type": "video-reconstruction",
        "source_identity": "video:abc", "producer_version": "reconstructor/0.1",
        "status": status, "outcome": outcome,
        "provenance": {"source.type": "video-reconstruction", "source.identity": "video:abc"},
    }
    with pytest.raises(BundleError):
        RunBundle(url).ingest_run(envelope, [])

def test_incomplete_import_has_no_invented_outcome(tmp_path):
    url = f"sqlite:///{tmp_path / 'incomplete.db'}"
    cfg = Config("alembic.ini"); cfg.set_main_option("sqlalchemy.url", url); command.upgrade(cfg, "head")
    source = tmp_path / "incomplete"
    source.mkdir()
    (source / "session.json").write_text(json.dumps({
        "run_id": "incomplete-run", "schema_version": "producer/1.0.0",
        "started_at": "2026-10-03T03:28:55+00:00", "ended_at": "2026-10-03T03:29:01+00:00",
        "outcome": None, "lifecycle_status": "incomplete", "n_steps": 0,
    }), encoding="utf-8")
    (source / "steps.ndjson").write_text("", encoding="utf-8")
    RunBundle(url).import_oracle_directory(source)
    run = RunBundleInspector(url).summary("incomplete-run")["data"]["run"]
    assert run["status"] == "incomplete"
    assert run["outcome"] is None

def test_file_ipc_oracle_import_keeps_unfinalized_source_active(tmp_path):
    url = f"sqlite:///{tmp_path / 'active-import.db'}"
    cfg = Config("alembic.ini"); cfg.set_main_option("sqlalchemy.url", url); command.upgrade(cfg, "head")
    source = tmp_path / "oracle" / "active-run"
    source.mkdir(parents=True)
    (source / "session.json").write_text(json.dumps({
        "run_id": "active-run", "schema_version": "producer/1.0.0",
        "started_at": "2026-10-03T03:28:55+00:00", "ended_at": None,
        "outcome": None, "n_steps": 0,
    }), encoding="utf-8")
    (source / "steps.ndjson").write_text("", encoding="utf-8")
    RunBundle(url).import_oracle_directory(source)
    assert RunBundleInspector(url).summary("active-run")["data"]["run"]["status"] == "active"

def test_file_ipc_oracle_import_derives_legacy_usage_without_timestamps(tmp_path):
    url = f"sqlite:///{tmp_path / 'legacy-import.db'}"
    cfg = Config("alembic.ini"); cfg.set_main_option("sqlalchemy.url", url); command.upgrade(cfg, "head")
    source = tmp_path / "oracle" / "legacy-run"
    source.mkdir(parents=True)
    (source / "session.json").write_text(json.dumps({
        "run_id": "legacy-run", "started_at": "2026-10-03T03:28:55+00:00",
        "outcome": None, "n_steps": 2,
    }), encoding="utf-8")
    (source / "steps.ndjson").write_text("".join(json.dumps({
        "request_id": index, "_recorded_action": action,
    }) + "\n" for index, action in ((1, "PlayHand"), (2, "DiscardHand"))), encoding="utf-8")
    RunBundle(url).import_oracle_directory(source)
    provenance = {item["key"]: item["value"]
                  for item in RunBundleInspector(url).provenance("legacy-run")["data"]}
    assert json.loads(provenance["oracle.usage"]) == {
        "action_counts": {"DiscardHand": 1, "PlayHand": 1},
        "first_recorded_at": None,
        "last_recorded_at": None,
        "unique_action_count": 2,
    }

def test_file_ipc_oracle_import_omits_legacy_timestamp_summary_when_any_timestamp_is_invalid(tmp_path):
    url = f"sqlite:///{tmp_path / 'malformed-time-import.db'}"
    cfg = Config("alembic.ini"); cfg.set_main_option("sqlalchemy.url", url); command.upgrade(cfg, "head")
    source = tmp_path / "oracle" / "malformed-time"
    source.mkdir(parents=True)
    (source / "session.json").write_text(json.dumps({
        "run_id": "malformed-time", "started_at": "2026-10-03T03:28:55+00:00",
        "outcome": None, "n_steps": 2,
    }), encoding="utf-8")
    (source / "steps.ndjson").write_text("".join(json.dumps({
        "request_id": index, "_recorded_action": action, "_recorded_at": recorded_at,
    }) + "\n" for index, action, recorded_at in (
        (1, "PlayHand", "2026-10-03T03:28:55+00:00"), (2, "DiscardHand", "not-a-time"))), encoding="utf-8")
    RunBundle(url).import_oracle_directory(source)
    provenance = {item["key"]: item["value"]
                  for item in RunBundleInspector(url).provenance("malformed-time")["data"]}
    usage = json.loads(provenance["oracle.usage"])
    assert usage["action_counts"] == {"DiscardHand": 1, "PlayHand": 1}
    assert usage["first_recorded_at"] is None
    assert usage["last_recorded_at"] is None

def test_file_ipc_oracle_import_rejects_count_mismatch_before_creating_run(tmp_path):
    url = f"sqlite:///{tmp_path / 'bad-import.db'}"
    cfg = Config("alembic.ini"); cfg.set_main_option("sqlalchemy.url", url); command.upgrade(cfg, "head")
    source = tmp_path / "oracle" / "bad-run"
    source.mkdir(parents=True)
    (source / "session.json").write_text(json.dumps({
        "run_id": "bad-run", "started_at": "2026-10-03T03:28:55+00:00", "n_steps": 1,
    }), encoding="utf-8")
    (source / "steps.ndjson").write_text("", encoding="utf-8")
    with pytest.raises(BundleError, match="n_steps"):
        RunBundle(url).import_oracle_directory(source)
    assert RunBundleInspector(url).list_runs()["data"] == []

def test_file_ipc_oracle_import_rejects_inconsistent_usage(tmp_path):
    url = f"sqlite:///{tmp_path / 'bad-usage-import.db'}"
    cfg = Config("alembic.ini"); cfg.set_main_option("sqlalchemy.url", url); command.upgrade(cfg, "head")
    source = tmp_path / "oracle" / "bad-usage"
    source.mkdir(parents=True)
    (source / "session.json").write_text(json.dumps({
        "run_id": "bad-usage", "started_at": "2026-10-03T03:28:55+00:00",
        "outcome": None, "n_steps": 1, "usage": {"action_counts": {"PlayHand": 0}},
    }), encoding="utf-8")
    (source / "steps.ndjson").write_text(json.dumps({"_recorded_action": "PlayHand"}) + "\n", encoding="utf-8")
    with pytest.raises(BundleError, match="action_counts"):
        RunBundle(url).import_oracle_directory(source)
    assert RunBundleInspector(url).list_runs()["data"] == []

def test_file_ipc_oracle_import_rejects_usage_for_different_action_with_same_total(tmp_path):
    url = f"sqlite:///{tmp_path / 'wrong-action-import.db'}"
    cfg = Config("alembic.ini"); cfg.set_main_option("sqlalchemy.url", url); command.upgrade(cfg, "head")
    source = tmp_path / "oracle" / "wrong-action"
    source.mkdir(parents=True)
    (source / "session.json").write_text(json.dumps({
        "run_id": "wrong-action", "started_at": "2026-10-03T03:28:55+00:00",
        "outcome": None, "n_steps": 1,
        "usage": {"action_counts": {"PlayHand": 1}, "unique_action_count": 1},
    }), encoding="utf-8")
    (source / "steps.ndjson").write_text(json.dumps({"_recorded_action": "DiscardHand"}) + "\n", encoding="utf-8")
    with pytest.raises(BundleError, match="action_counts"):
        RunBundle(url).import_oracle_directory(source)
    assert RunBundleInspector(url).list_runs()["data"] == []

def test_file_ipc_oracle_import_rejects_invalid_usage_timestamps(tmp_path):
    url = f"sqlite:///{tmp_path / 'bad-usage-time.db'}"
    cfg = Config("alembic.ini"); cfg.set_main_option("sqlalchemy.url", url); command.upgrade(cfg, "head")
    source = tmp_path / "oracle" / "bad-usage-time"
    source.mkdir(parents=True)
    (source / "session.json").write_text(json.dumps({
        "run_id": "bad-usage-time", "started_at": "2026-10-03T03:28:55+00:00",
        "outcome": None, "n_steps": 1, "usage": {
            "action_counts": {"PlayHand": 1}, "unique_action_count": 1,
            "first_recorded_at": "not-a-time", "last_recorded_at": "2026-10-03T03:28:55+00:00",
        },
    }), encoding="utf-8")
    (source / "steps.ndjson").write_text(json.dumps({
        "_recorded_action": "PlayHand", "_recorded_at": "2026-10-03T03:28:55+00:00",
    }) + "\n", encoding="utf-8")
    with pytest.raises(BundleError, match="usage timestamps"):
        RunBundle(url).import_oracle_directory(source)
    assert RunBundleInspector(url).list_runs()["data"] == []

def test_file_ipc_oracle_import_rejects_invalid_step_timestamp_when_usage_is_present(tmp_path):
    url = f"sqlite:///{tmp_path / 'bad-step-time.db'}"
    cfg = Config("alembic.ini"); cfg.set_main_option("sqlalchemy.url", url); command.upgrade(cfg, "head")
    source = tmp_path / "oracle" / "bad-step-time"
    source.mkdir(parents=True)
    (source / "session.json").write_text(json.dumps({
        "run_id": "bad-step-time", "started_at": "2026-10-03T03:28:55+00:00",
        "outcome": None, "n_steps": 1, "usage": {
            "action_counts": {"PlayHand": 1}, "unique_action_count": 1,
            "first_recorded_at": "2026-10-03T03:28:55+00:00",
            "last_recorded_at": "2026-10-03T03:28:55+00:00",
        },
    }), encoding="utf-8")
    (source / "steps.ndjson").write_text(json.dumps({
        "_recorded_action": "PlayHand", "_recorded_at": "not-a-time",
    }) + "\n", encoding="utf-8")
    with pytest.raises(BundleError, match="step timestamps"):
        RunBundle(url).import_oracle_directory(source)
    assert RunBundleInspector(url).list_runs()["data"] == []

def test_file_ipc_oracle_import_checks_available_boundary_timestamp(tmp_path):
    url = f"sqlite:///{tmp_path / 'partial-boundary-import.db'}"
    cfg = Config("alembic.ini"); cfg.set_main_option("sqlalchemy.url", url); command.upgrade(cfg, "head")
    source = tmp_path / "oracle" / "partial-boundary"
    source.mkdir(parents=True)
    (source / "session.json").write_text(json.dumps({
        "run_id": "partial-boundary", "started_at": "2026-10-03T03:28:55+00:00",
        "outcome": None, "n_steps": 2, "usage": {
            "action_counts": {"PlayHand": 1, "DiscardHand": 1}, "unique_action_count": 2,
            "first_recorded_at": "2026-10-03T03:29:00+00:00",
            "last_recorded_at": "2026-10-03T03:29:10+00:00",
        },
    }), encoding="utf-8")
    (source / "steps.ndjson").write_text("".join(json.dumps(step) + "\n" for step in (
        {"_recorded_action": "PlayHand", "_recorded_at": "2026-10-03T03:28:55+00:00"},
        {"_recorded_action": "DiscardHand"},
    )), encoding="utf-8")
    with pytest.raises(BundleError, match="available boundary steps"):
        RunBundle(url).import_oracle_directory(source)
    assert RunBundleInspector(url).list_runs()["data"] == []
