import sqlite3

from ground_truth.recording_association import (
    associate_after_confirmation,
    associate_recording,
    confirm_interactive,
)
from run_bundle import RunBundle


def bundle(tmp_path):
    from alembic import command
    from alembic.config import Config
    url = f"sqlite:///{tmp_path / 'run.db'}"
    cfg = Config("alembic.ini"); cfg.set_main_option("sqlalchemy.url", url); command.upgrade(cfg, "head")
    b = RunBundle(url); b.create("r1", producer_version="test"); return b, url


def marker(timestamp=100):
    return {"schema_version": "producer/1.0.0", "recording_id": "obs-1", "fps": 60,
            "capture_timestamp_ns": timestamp}


def test_confirmed_is_additive_and_declined_is_explicit(tmp_path):
    b, url = bundle(tmp_path); b.append("r1", 0, "state", {"x": 1})
    before = b.validate("r1")
    result = associate_recording(b, "r1", confirmed=True, marker=marker(), video_ref="capture.mkv")
    assert result.status == "confirmed"
    assert b.validate("r1") == before
    assert associate_recording(b, "r1", confirmed=False, marker=marker()).status == "declined"
    with sqlite3.connect(url.replace("sqlite:///", "")) as db:
        keys = {row[0] for row in db.execute("select key from provenance")}
    assert "recording.recording_id" in keys


def test_missing_invalid_stale_and_interrupted_are_machine_readable(tmp_path):
    b, _ = bundle(tmp_path)
    assert associate_recording(b, "r1", confirmed=True, marker=None).status == "missing"
    assert associate_recording(b, "r1", confirmed=True, marker={}).status == "invalid"
    assert associate_recording(b, "r1", confirmed=True, marker=marker(), observed_at_ns=200,
                               max_age_ns=50).status == "stale"
    assert associate_recording(b, "missing", confirmed=True, marker=marker()).status == "interrupted"


def test_association_after_finalization_preserves_evidence(tmp_path):
    b, _ = bundle(tmp_path); b.append("r1", 0, "state", {"x": 1}); b.transition("r1", "won")
    before = b.validate("r1")
    assert associate_recording(b, "r1", confirmed=True, marker=marker()).status == "confirmed"
    assert b.validate("r1") == before


def test_boolean_and_negative_marker_values_are_invalid(tmp_path):
    b, _ = bundle(tmp_path)
    bad = marker(); bad["fps"] = True
    assert associate_recording(b, "r1", confirmed=True, marker=bad).status == "invalid"
    bad = marker(-1)
    assert associate_recording(b, "r1", confirmed=True, marker=bad).status == "invalid"


def test_interactive_notification_states_recording_policy():
    messages = []
    assert confirm_interactive(lambda _: "y", messages.append, required=True)
    assert "recording is required" in messages[0]

    messages.clear()
    assert not confirm_interactive(lambda _: "n", messages.append)
    assert "recording is optional" in messages[0]


def test_confirmation_boundary_preserves_interruption(tmp_path):
    b, _ = bundle(tmp_path)

    def interrupted():
        raise KeyboardInterrupt

    result = associate_after_confirmation(
        b, "r1", marker=marker(), confirm=interrupted
    )
    assert result.status == "interrupted"
    assert result.code == "coordination_interrupted"


def test_confirmation_boundary_associates_only_explicit_true(tmp_path):
    b, _ = bundle(tmp_path)
    result = associate_after_confirmation(
        b, "r1", marker=marker(), confirm=lambda: 1
    )
    assert result.status == "declined"


def test_direct_association_rejects_non_boolean_confirmation_and_times(tmp_path):
    b, _ = bundle(tmp_path)
    assert associate_recording(b, "r1", confirmed=1, marker=marker()).code == "confirmation_invalid"
    assert associate_recording(b, "r1", confirmed=True, marker=marker(), max_age_ns=-1).code == "max_age_invalid"
    assert associate_recording(b, "r1", confirmed=True, marker=marker(), observed_at_ns="now").code == "observation_time_invalid"
