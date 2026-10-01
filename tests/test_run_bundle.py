import pytest
from alembic import command
from alembic.config import Config
from run_bundle import RunBundle, InvalidTransition, FinalizedEvidenceError

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

def test_raw_malformed_and_duplicate(tmp_path):
    b = bundle(tmp_path); b.append_raw("r1", 0, "partial", b"{not-json")
    with pytest.raises(Exception): b.append("r1", 0, "state", {})
