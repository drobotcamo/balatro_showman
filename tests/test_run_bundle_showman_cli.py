"""Product entrypoint integration: real persistence, source preservation, and human decisions."""

import json
import subprocess
import sys

import pytest

from run_bundle import RunBundleInspector
from showman.__main__ import main


@pytest.fixture
def example(tmp_path, capsys):
    destination = tmp_path / "demo"
    assert main(["demo", "--output-dir", str(destination)]) == 0
    result = json.loads(capsys.readouterr().out)
    assert result["data"]["synthetic"] is True
    return destination


def query(example, *operation):
    return ["inspect", *operation, "--db", str(example / "bundle.sqlite"), "--run", "demo-synthetic"]


def test_demo_uses_real_queue_and_automatic_import(example, capsys):
    assert not list((example / "synthetic_io").glob("request_*.json"))
    source = example / "captures" / "demo-synthetic"
    before = [(source / name).read_bytes() for name in ("session.json", "steps.ndjson")]
    assert main(query(example, "summary")) == 0
    summary = json.loads(capsys.readouterr().out)["data"]
    assert summary["record_count"] == 2
    assert summary["run"]["status"] == "lost"
    assert main(query(example, "step", "--sequence", "0")) == 0
    record = json.loads(capsys.readouterr().out)["data"]
    assert record["payload"]["meta"]["synthetic"] is True
    assert record["payload"]["_recorded_action"] == "SelectBlind"
    assert main(["store", "import", "--db", str(example / "bundle.sqlite"), "--source", str(source)]) == 0
    assert json.loads(capsys.readouterr().out)["data"]["already_imported"] is True
    assert before == [(source / name).read_bytes() for name in ("session.json", "steps.ndjson")]


def test_inspection_is_read_only_and_matches_existing_api(example, capsys):
    database = example / "bundle.sqlite"
    before = database.read_bytes()
    inspector = RunBundleInspector(str(database))
    try:
        expected = inspector.validate("demo-synthetic", strict=True)
    finally:
        inspector.close()
    assert main(query(example, "validate", "--strict")) == 0
    assert json.loads(capsys.readouterr().out) == expected
    assert database.read_bytes() == before


def test_inspection_cannot_import_or_create_a_missing_database(tmp_path, capsys):
    missing = tmp_path / "missing.sqlite"
    assert main(["inspect", "list", "--db", str(missing)]) == 2
    assert json.loads(capsys.readouterr().out)["diagnostics"][0]["code"] == "storage_not_found"
    assert not missing.exists()
    with pytest.raises(SystemExit) as error:
        main(["inspect", "import-oracle", "--db", str(missing), "--source", str(tmp_path)])
    assert error.value.code == 2


def test_initialization_and_demo_refuse_existing_destinations(example, capsys):
    database = example / "bundle.sqlite"
    before = database.read_bytes()
    assert main(["store", "init", "--db", str(database)]) == 2
    assert main(["demo", "--output-dir", str(example)]) == 2
    assert database.read_bytes() == before
    outputs = [json.loads(line) for line in capsys.readouterr().out.splitlines()]
    assert len(outputs) == 2
    message = outputs[1]["diagnostics"][0]["message"]
    assert "Choose a NEW output directory" in message
    assert "not the project/worktree folder" in message


def test_nested_help_and_module_execution(example):
    help_result = subprocess.run([sys.executable, "-m", "showman", "inspect", "summary", "--help"],
                                 capture_output=True, text=True)
    assert help_result.returncode == 0
    assert "showman inspect summary" in help_result.stdout
    result = subprocess.run([sys.executable, "-m", "showman", *query(example, "outcome")],
                            capture_output=True, text=True)
    assert result.returncode == 0, result.stderr
    assert json.loads(result.stdout)["data"] == "lost"


def test_record_command_consumes_a_queue_and_imports_terminal_capture(example, capsys):
    io_dir = example / "new_io"
    io_dir.mkdir()
    record = json.loads((example / "captures" / "demo-synthetic" / "steps.ndjson").read_text().splitlines()[0])
    record["meta"]["run_id"] = "record-command"
    record["step_id"] = "record-command:1"
    (io_dir / "request_record-command_000000000001.json").write_text(json.dumps(record), encoding="utf-8")
    (io_dir / "run_end_record-command.json").write_text(json.dumps({
        "ipc_schema_version": "file-queue/1.0.0", "run_id": "record-command",
        "outcome": "win", "last_request_id": 1}), encoding="utf-8")
    assert main(["record", "--once", "--io-dir", str(io_dir), "--out-dir", str(example / "new_captures"),
                 "--bundle-db", str(example / "bundle.sqlite")]) == 0
    capsys.readouterr()
    assert main(["inspect", "summary", "--db", str(example / "bundle.sqlite"), "--run", "record-command"]) == 0
    result = json.loads(capsys.readouterr().out)["data"]
    assert result["record_count"] == 1
    assert result["run"]["status"] == "won"


def test_mutating_commands_require_an_existing_migrated_bundle(tmp_path, capsys):
    missing = tmp_path / "missing.sqlite"
    assert main(["store", "import", "--db", str(missing), "--source", str(tmp_path)]) == 2
    assert main(["record", "--bundle-db", str(missing), "--out-dir", str(tmp_path / "out"),
                 "--io-dir", str(tmp_path / "io"), "--once"]) == 2
    assert not missing.exists()
    assert not (tmp_path / "out").exists()


def test_alignment_without_marker_is_machine_readable(example, capsys):
    assert main(["align", str(example / "captures" / "demo-synthetic" / "steps.ndjson")]) == 2
    assert "lacks recording marker" in json.loads(capsys.readouterr().out)["diagnostics"][0]["message"]


def test_capture_summary_and_alignment_preserve_sources(example, tmp_path, capsys):
    source = example / "captures" / "demo-synthetic"
    assert main(["capture", "summary", str(source)]) == 0
    assert json.loads(capsys.readouterr().out)["data"]["step_count"] == 2
    session = source / "session.json"
    data = json.loads(session.read_text())
    data["recording"] = {"capture_timestamp_ns": 0, "fps": 60}
    session.write_text(json.dumps(data), encoding="utf-8")
    before = session.read_bytes(), (source / "steps.ndjson").read_bytes()
    assert main(["align", str(source / "steps.ndjson")]) == 0
    rows = [json.loads(line) for line in capsys.readouterr().out.splitlines()]
    assert [row["frame_idx"] for row in rows] == [60, 120]
    assert before == (session.read_bytes(), (source / "steps.ndjson").read_bytes())
    assert main(["capture", "summary", str(tmp_path / "missing")]) == 2
    assert json.loads(capsys.readouterr().out)["data"]["classification"] == "malformed"


@pytest.fixture
def association_args(example):
    marker = example / "marker.json"
    marker.write_text(json.dumps({"schema_version": "producer/1.0.0", "recording_id": "synthetic-marker",
                                  "capture_timestamp_ns": 100, "fps": 60}), encoding="utf-8")
    return ["associate", "--db", str(example / "bundle.sqlite"), "--run", "demo-synthetic",
            "--marker", str(marker), "--confirmed-by", "test-human"]


@pytest.mark.parametrize("choice,required,status", [
    ("confirm", False, "confirmed"), ("decline", False, "declined"),
    ("interrupt", False, "interrupted"), ("", False, "interrupted"),
    ("wrong recording", False, "interrupted"), ("decline", True, "blocked"),
])
def test_association_requires_explicit_confirm_and_preserves_evidence(
        example, association_args, monkeypatch, capsys, choice, required, status):
    observed_summary = []
    def prompt():
        observed_summary.append(capsys.readouterr().err)
        return choice
    monkeypatch.setattr("builtins.input", prompt)
    source = example / "captures" / "demo-synthetic"
    evidence_before = (source / "steps.ndjson").read_bytes()
    assert main(association_args + (["--required"] if required else [])) == (0 if status in {"confirmed", "declined"} else 2)
    assert '"lifecycle_status": "lost"' in observed_summary[0]
    assert '"choices": ["confirm", "decline", "interrupt"]' in observed_summary[0]
    result = json.loads(capsys.readouterr().out)
    assert result["data"]["status"] == status
    assert main(query(example, "provenance")) == 0
    provenance = json.loads(capsys.readouterr().out)["data"]
    associated = any(row["key"] == "recording.association_status" for row in provenance)
    assert associated == (status == "confirmed")
    assert (source / "steps.ndjson").read_bytes() == evidence_before
    assert main(query(example, "validate", "--strict")) == 0


@pytest.mark.parametrize("failure", [EOFError, KeyboardInterrupt, OSError, RuntimeError])
def test_prompt_failure_becomes_interrupted(association_args, monkeypatch, capsys, failure):
    def prompt():
        raise failure()
    monkeypatch.setattr("builtins.input", prompt)
    assert main(association_args) == 2
    assert json.loads(capsys.readouterr().out)["data"]["status"] == "interrupted"


def test_missing_marker_and_video_cannot_be_confirmed(association_args, monkeypatch, capsys, example):
    monkeypatch.setattr("builtins.input", lambda: "confirm")
    assert main(association_args + ["--video", str(example / "missing.mkv")]) == 2
    assert json.loads(capsys.readouterr().out)["data"]["code"] == "video_missing"
    (example / "marker.json").unlink()
    assert main(association_args + ["--required"]) == 2
    result = json.loads(capsys.readouterr().out)
    assert result["data"]["status"] == "blocked"
    assert "marker_missing" in result["data"]["diagnostic"]


def test_required_association_storage_failure_is_blocked_and_preserves_evidence(
        association_args, monkeypatch, capsys, example):
    from sqlalchemy.exc import OperationalError
    from run_bundle import RunBundle
    database = example / "bundle.sqlite"
    before = database.read_bytes()
    def fail_write(*args, **kwargs):
        raise OperationalError("INSERT provenance", {}, Exception("database is locked"))
    monkeypatch.setattr("builtins.input", lambda: "confirm")
    monkeypatch.setattr(RunBundle, "add_provenance", fail_write)
    assert main(association_args + ["--required"]) == 2
    result = json.loads(capsys.readouterr().out)["data"]
    assert result["status"] == "blocked"
    assert result["code"] == "recording_required"
    assert "database is locked" in result["diagnostic"]
    assert database.read_bytes() == before
    assert main(query(example, "validate", "--strict")) == 0


def test_required_association_missing_bundle_is_blocked_without_creation(tmp_path, capsys):
    database = tmp_path / "missing.sqlite"
    assert main(["associate", "--db", str(database), "--run", "unknown", "--marker", str(tmp_path / "marker.json"),
                 "--confirmed-by", "human", "--required"]) == 2
    result = json.loads(capsys.readouterr().out)["data"]
    assert result["status"] == "blocked"
    assert result["code"] == "recording_required"
    assert "storage_not_found" in result["diagnostic"]
    assert not database.exists()


def test_annotations_export_delegates_and_does_not_overwrite_source(tmp_path, capsys):
    from test_eval_manifest import sample
    source = tmp_path / "annotations.json"
    target = tmp_path / "manifest.json"
    source.write_text(json.dumps(sample()), encoding="utf-8")
    before = source.read_bytes()
    assert main(["annotations", "export", str(source), str(target)]) == 0
    digest = json.loads(capsys.readouterr().out)["data"]["sha256"]
    assert json.loads(target.read_text())["scoring_status"] == "development_only_unscored"
    assert main(["annotations", "export", str(source), str(target)]) == 0
    assert json.loads(capsys.readouterr().out)["data"]["sha256"] == digest
    assert main(["annotations", "export", str(source), str(source)]) == 2
    assert source.read_bytes() == before
