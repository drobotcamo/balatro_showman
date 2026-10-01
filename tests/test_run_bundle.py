import pytest
import sqlite3
from alembic import command
from alembic.config import Config
from run_bundle import RunBundle, BundleError, InvalidTransition, FinalizedEvidenceError

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
