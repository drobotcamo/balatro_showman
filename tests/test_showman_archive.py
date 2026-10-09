import json
import subprocess
import sys
from pathlib import Path

import pytest

from run_bundle import RunBundle, RunBundleInspector
from ground_truth.file_ipc_bridge import capture_build_identity
from showman.__main__ import main
from showman import archive


def test_staged_capture_is_hash_preserved_and_cataloged(tmp_path, capsys):
    demo = tmp_path / "demo"
    assert main(["demo", "--output-dir", str(demo)]) == 0
    capsys.readouterr()
    root = tmp_path / "archive"
    assert main(["archive", "init", "--root", str(root)]) == 0
    capsys.readouterr()
    source = demo / "captures" / "demo-synthetic"
    original = {p.name: p.read_bytes() for p in source.iterdir() if p.is_file()}
    command = ["archive", "ingest", "--root", str(root), "--source", str(source)]
    assert main(command) == 0
    first = json.loads(capsys.readouterr().out)["data"]
    assert first["import"]["record_count"] == 2
    assert main(command) == 0
    assert json.loads(capsys.readouterr().out)["data"]["import"]["already_imported"]
    assert original == {p.name: (root / "captures" / "demo-synthetic" / p.name).read_bytes()
                        for p in source.iterdir() if p.is_file()}
    assert main(["archive", "list", "--root", str(root)]) == 0
    row = json.loads(capsys.readouterr().out)["data"][0]
    assert row["video_status"] == "unassociated"
    assert row["producer_commit"] == json.loads((source / "session.json").read_text())["capture_build"]["producer_commit"]
    inspector = RunBundleInspector(str(root / "catalog.sqlite"))
    try:
        assert inspector.validate("demo-synthetic", strict=True)["data"]["status"] == "valid"
    finally:
        inspector.close()
    with pytest.raises(ValueError, match="no confirmed video"):
        archive.review(root, "demo-synthetic")


def test_conflict_does_not_replace_staged_evidence(tmp_path, capsys):
    demo = tmp_path / "demo"
    main(["demo", "--output-dir", str(demo)])
    root = tmp_path / "archive"
    main(["archive", "init", "--root", str(root)])
    source = demo / "captures" / "demo-synthetic"
    assert archive.ingest(root, source)["import"]["status"] == "lost"
    staged_before = (root / "captures" / "demo-synthetic" / "session.json").read_bytes()
    payload = json.loads((source / "session.json").read_text())
    payload["new_field"] = "changed"
    (source / "session.json").write_text(json.dumps(payload), encoding="utf-8")
    with pytest.raises(ValueError, match="identity/path conflict"):
        archive.ingest(root, source)
    assert (root / "captures" / "demo-synthetic" / "session.json").read_bytes() == staged_before


def test_verify_rejects_identical_post_import_changes_to_both_copies(tmp_path, capsys):
    demo = tmp_path / "demo"
    main(["demo", "--output-dir", str(demo)])
    root = tmp_path / "archive"
    main(["archive", "init", "--root", str(root)])
    source = demo / "captures" / "demo-synthetic"
    archive.ingest(root, source)
    assert not archive.verify(root)["failures"]
    for location in (source, root / "captures" / "demo-synthetic"):
        session = location / "session.json"
        content = json.loads(session.read_text())
        content["post_import"] = "same new bytes"
        session.write_text(json.dumps(content), encoding="utf-8")
    failure = archive.verify(root)["failures"]
    assert len(failure) == 1
    assert "catalog/imported identity" in failure[0]["error"]


def test_only_confirmed_matching_source_association_transfers(tmp_path, monkeypatch, capsys):
    demo = tmp_path / "demo"
    main(["demo", "--output-dir", str(demo)])
    root = tmp_path / "archive"
    main(["archive", "init", "--root", str(root)])
    archive.ingest(root, demo / "captures" / "demo-synthetic")
    video = tmp_path / "confirmed.mkv"
    video.write_bytes(b"example")
    legacy = RunBundle(str(demo / "bundle.sqlite"))
    try:
        legacy.add_provenance("demo-synthetic", {"recording.association_status": "confirmed",
                                                 "recording.video_ref": str(video),
                                                 "recording.confirmed_by": "human"})
    finally:
        legacy.close()
    assert archive.sync_associations(root, demo / "bundle.sqlite") == ["demo-synthetic"]
    assert archive.sync_associations(root, demo / "bundle.sqlite") == ["demo-synthetic"]
    row = archive.list_entries(root)[0]
    assert row["video_status"] == "confirmed"
    staged = archive.stage_video(root, "demo-synthetic")
    assert Path(staged["video"]).read_bytes() == video.read_bytes()
    assert archive.list_entries(root)[0]["video_path"] == staged["video"]
    assert archive.sync_associations(root, demo / "bundle.sqlite") == ["demo-synthetic"]
    calls = []
    monkeypatch.setattr(archive.subprocess, "call", lambda cmd: calls.append(cmd) or 0)
    assert archive.review(root, "demo-synthetic") == 0
    assert calls[0][calls[0].index("--video") + 1] == staged["video"]
    assert calls[0][calls[0].index("--run") + 1] == row["capture_path"]


def test_inventory_excludes_new_live_root(tmp_path):
    for name in archive.CAPTURE_ROOTS:
        (tmp_path / name).mkdir()
    source = tmp_path / "oracle_runs" / "first"
    source.mkdir()
    (source / "session.json").write_text(json.dumps({"run_id": "first", "n_steps": 1}), encoding="utf-8")
    (source / "steps.ndjson").write_text("{}\n", encoding="utf-8")
    live = tmp_path / "oracle_runs_issue82" / "new"
    live.mkdir(parents=True)
    (live / "session.json").write_text(json.dumps({"run_id": "new", "n_steps": 5}), encoding="utf-8")
    assert archive.inventory(tmp_path)["count"] == 1


def test_archive_help_reaches_the_real_subcommands():
    result = subprocess.run([sys.executable, "-m", "showman", "archive", "--help"],
                            capture_output=True, text=True)
    assert result.returncode == 0
    assert "sync-associations" in result.stdout
    assert "stage-video" in result.stdout


def test_direct_recorder_registers_versioned_capture_without_guessing_installed_commit(
        tmp_path, monkeypatch, capsys):
    root = tmp_path / "archive"
    assert main(["archive", "init", "--root", str(root)]) == 0
    capsys.readouterr()
    installed = tmp_path / "main.lua"
    installed.write_bytes(b"local different = true\n")
    monkeypatch.setenv("SHOWMAN_INSTALLED_PRODUCER", str(installed))
    build = capture_build_identity()
    assert build["producer_commit"] is None
    assert len(build["installed_producer_sha256"]) == 64
    checked_in_producer = Path(__file__).resolve().parents[1] / "ground_truth" / "balatro_mod" / "main.lua"
    monkeypatch.setenv("SHOWMAN_INSTALLED_PRODUCER", str(checked_in_producer))
    assert capture_build_identity()["producer_commit"] is not None
    monkeypatch.setenv("SHOWMAN_INSTALLED_PRODUCER", str(installed))
    io_dir = tmp_path / "io"
    io_dir.mkdir()
    payload = {"schema_version": "producer/1.0.0", "ipc_schema_version": "file-queue/1.0.0",
               "step_id": "live:1", "request_id": 1, "capture_timestamp_ns": 123,
               "page_name": "Blind_Select", "action_taken": "SelectBlind", "state": {},
               "objects": [], "pending_cards": [], "persistent_state": {},
               "meta": {"run_id": "live"}}
    (io_dir / "request_live_000000000001.json").write_text(json.dumps(payload), encoding="utf-8")
    (io_dir / "run_end_live.json").write_text(json.dumps({
        "ipc_schema_version": "file-queue/1.0.0", "run_id": "live",
        "outcome": "win", "last_request_id": 1}), encoding="utf-8")
    assert main(["record", "--once", "--io-dir", str(io_dir),
                 "--out-dir", str(root / "captures"),
                 "--bundle-db", str(root / "catalog.sqlite")]) == 0
    entry = archive.list_entries(root)[0]
    assert entry["run_id"] == "live"
    assert entry["producer_commit"] is None
    assert entry["installed_producer_sha256"] == build["installed_producer_sha256"]
    provenance = RunBundleInspector(str(root / "catalog.sqlite"))
    try:
        assert "capture.build" in {p["key"] for p in provenance.provenance("live")["data"]}
    finally:
        provenance.close()
