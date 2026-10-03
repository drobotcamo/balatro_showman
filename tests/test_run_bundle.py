import pytest
import sqlite3
import json
import hashlib
from alembic import command
from alembic.config import Config
from run_bundle import RunBundle, BundleError, InvalidTransition, FinalizedEvidenceError
from run_bundle import RunBundleInspector

def bundle(tmp_path):
    url = f"sqlite:///{tmp_path / 'run.db'}"
    cfg = Config("alembic.ini"); cfg.set_main_option("sqlalchemy.url", url); command.upgrade(cfg, "head")
    b = RunBundle(url); b.create("r1", producer_version="test"); return b

def test_lifecycle_and_immutable_evidence(tmp_path):
    b = bundle(tmp_path); b.append("r1", 0, "state", {"chips": 1}); b.transition("r1", "won")
    assert b.validate("r1") == {"status": "valid", "record_count": 1, "bad_sequences": []}
    with pytest.raises(FinalizedEvidenceError): b.append("r1", 1, "state", {})

@pytest.mark.parametrize("outcome", ["interrupted", "completed", "won", "lost", "endless", "aborted"])
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
        "usage": {"action_counts": {"PlayHand": 1, "DiscardHand": 1}, "unique_action_count": 2},
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
    with pytest.raises(BundleError, match="already exists"):
        RunBundle(url).import_oracle_directory(source)

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
