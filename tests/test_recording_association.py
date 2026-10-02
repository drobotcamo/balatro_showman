import sqlite3
import pytest

from ground_truth.recording_association import (associate_after_confirmation, associate_recording,
                                                confirm_interactive, confirm_terminal, coordinate_recording)
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
    assert associate_recording(b, "r1", confirmed=True, marker=marker(), video_ref="capture.mkv").status == "confirmed"
    assert b.validate("r1") == before
    assert associate_recording(b, "r1", confirmed=False, marker=marker()).status == "declined"
    with sqlite3.connect(url.replace("sqlite:///", "")) as db:
        assert "recording.recording_id" in {row[0] for row in db.execute("select key from provenance")}


def test_missing_invalid_stale_and_interrupted_are_machine_readable(tmp_path):
    b, _ = bundle(tmp_path)
    assert associate_recording(b, "r1", confirmed=True, marker=None).status == "missing"
    assert associate_recording(b, "r1", confirmed=True, marker={}).status == "invalid"
    assert associate_recording(b, "r1", confirmed=True, marker=marker(), observed_at_ns=200, max_age_ns=50).status == "stale"
    assert associate_recording(b, "missing", confirmed=True, marker=marker()).status == "interrupted"


def test_association_after_finalization_preserves_evidence(tmp_path):
    b, _ = bundle(tmp_path); b.append("r1", 0, "state", {"x": 1}); b.transition("r1", "won")
    before = b.validate("r1")
    assert associate_recording(b, "r1", confirmed=True, marker=marker()).status == "confirmed"
    assert b.validate("r1") == before


def test_boolean_and_negative_marker_values_are_invalid(tmp_path):
    b, _ = bundle(tmp_path); bad = marker(); bad["fps"] = True
    assert associate_recording(b, "r1", confirmed=True, marker=bad).status == "invalid"
    assert associate_recording(b, "r1", confirmed=True, marker=marker(-1)).status == "invalid"


def test_confirmation_workflows_require_explicit_yes(tmp_path):
    b, _ = bundle(tmp_path); notices = []
    assert confirm_interactive(lambda _: "yes", notices.append)
    assert notices
    assert not confirm_terminal(lambda _: "no")
    result = associate_after_confirmation(b, "r1", marker=marker(), confirm=lambda: True, confirmed_by="terminal")
    assert result.status == "confirmed"


def test_confirmation_eof_and_interrupt_are_not_confirmation():
    def eof(_):
        raise EOFError

    def interrupted(_):
        raise KeyboardInterrupt

    with pytest.raises(EOFError):
        confirm_interactive(eof, lambda _: None)
    with pytest.raises(KeyboardInterrupt):
        confirm_terminal(interrupted)


def test_callback_interrupt_is_explicitly_interrupted(tmp_path):
    b, _ = bundle(tmp_path)

    def interrupted():
        raise KeyboardInterrupt

    result = associate_after_confirmation(b, "r1", marker=marker(), confirm=interrupted,
                                          confirmed_by="terminal")
    assert result.status == "interrupted"
    assert result.code == "coordination_interrupted"


def test_callback_failure_is_explicitly_interrupted(tmp_path):
    b, _ = bundle(tmp_path)

    def failed():
        raise RuntimeError("prompt failed")

    result = associate_after_confirmation(b, "r1", marker=marker(), confirm=failed,
                                          confirmed_by="terminal")
    assert result.status == "interrupted"
    assert result.code == "coordination_interrupted"


def test_required_callback_failure_is_blocked(tmp_path):
    b, _ = bundle(tmp_path)

    def failed(_):
        raise RuntimeError("prompt failed")

    result = coordinate_recording(b, "r1", marker=marker(), prompt=failed, required=True)
    assert result.status == "blocked"
    assert result.code == "recording_required"


def test_conflicting_association_is_rejected(tmp_path):
    b, _ = bundle(tmp_path)
    assert associate_recording(b, "r1", confirmed=True, marker=marker()).status == "confirmed"
    other = marker(); other["recording_id"] = "obs-2"
    result = associate_recording(b, "r1", confirmed=True, marker=other)
    assert result.status == "rejected"
    assert result.code == "association_conflict"


def test_interactive_policy_and_direct_confirmation_validation(tmp_path):
    messages = []
    assert confirm_interactive(lambda _: "y", messages.append, required=True)
    assert "recording is required" in messages[0]
    assert not confirm_interactive(lambda _: "n", messages.append)
    assert "recording is optional" in messages[1]

    b, _ = bundle(tmp_path)
    assert associate_recording(b, "r1", confirmed=1, marker=marker()).code == "confirmation_invalid"
    assert associate_recording(b, "r1", confirmed=True, marker=marker(), observed_at_ns="now").code == "observation_time_invalid"


def test_terminal_confirmation_states_recording_policy():
    prompts = []
    assert confirm_terminal(lambda message: prompts.append(message) or "y", required=True)
    assert "recording is required" in prompts[0]
    assert not confirm_terminal(lambda message: prompts.append(message) or "n")
    assert "recording is optional" in prompts[1]


def test_terminal_confirmation_is_wired_to_association(tmp_path):
    b, _ = bundle(tmp_path)
    result = associate_after_confirmation(
        b,
        "r1",
        marker=marker(),
        confirm=lambda: confirm_terminal(lambda _: "yes", required=True),
        confirmed_by="terminal",
    )
    assert result.status == "confirmed"


def test_coordinate_recording_is_the_user_facing_boundary(tmp_path):
    b, _ = bundle(tmp_path); notices = []
    result = coordinate_recording(b, "r1", marker=marker(), prompt=lambda _: "yes",
                                  notify=notices.append, interactive=True, required=True)
    assert result.status == "confirmed"
    assert "recording is required" in notices[0]


def test_required_recording_failure_blocks_coordination(tmp_path):
    b, _ = bundle(tmp_path)
    result = coordinate_recording(b, "r1", marker=marker(), prompt=lambda _: "no", required=True)
    assert result.status == "blocked"
    assert result.code == "recording_required"

    result = coordinate_recording(b, "r1", marker=marker(), prompt=lambda _: "yes",
                                  interactive=True, required=True)
    assert result.status == "blocked"
    assert result.code == "recording_required"

    result = coordinate_recording(b, "r1", marker=None, prompt=lambda _: "yes", required=True)
    assert result.status == "blocked"
    assert result.code == "recording_required"


def test_optional_recording_failure_remains_explicit(tmp_path):
    b, _ = bundle(tmp_path)
    result = coordinate_recording(b, "r1", marker=None, prompt=lambda _: "yes")
    assert result.status == "missing"
    assert result.code == "marker_missing"


def test_missing_marker_notification_does_not_claim_evidence():
    notices = []
    assert not confirm_interactive(lambda _: "n", notices.append, marker_found=False)
    assert "No OBS recording marker is available" in notices[0]


def test_result_serializes_explicit_video_status(tmp_path):
    b, _ = bundle(tmp_path)
    result = associate_recording(b, "r1", confirmed=True, marker=None)
    assert result.as_dict()["video_status"] == "unknown"
