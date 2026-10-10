import json
import os
import tempfile
import shutil
import subprocess
import sys
import time
from pathlib import Path

import pytest

from run_bundle import RunBundle, RunBundleInspector
from ground_truth.file_ipc_bridge import capture_build_identity
from showman.__main__ import main
from showman import archive


def test_archive_root_requires_flag_or_environment(monkeypatch):
    monkeypatch.delenv("SHOWMAN_ARCHIVE_ROOT", raising=False)
    with pytest.raises(ValueError, match="specify --root or set SHOWMAN_ARCHIVE_ROOT"):
        archive.archive_root()


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


def test_unlinked_media_staging_is_non_associating_and_hash_verified(tmp_path, capsys):
    recordings = tmp_path / "recordings"
    recordings.mkdir()
    root = recordings / "archive"
    assert main(["archive", "init", "--root", str(root)]) == 0
    capsys.readouterr()
    closed = recordings / "2026-04-02 17-10-58.mkv"
    closed.write_bytes(b"closed source bytes")
    stale = time.time() - 7200
    os.utime(closed, (stale, stale))
    active = recordings / "2026-10-09 13-38-25.mkv"
    active.write_bytes(b"not closed")
    assert len(archive.media_inventory(root, recordings)) == 2
    result = archive.stage_media(root, recordings, exclude=[active.name], only=[closed.name])
    assert not result["failures"]
    assert [item["video"] for item in result["staged"]] == [closed.name]
    assert active.name not in {item["video"] for item in result["staged"]}
    assert (root / "videos" / "unlinked" / closed.name).read_bytes() == closed.read_bytes()
    assert not archive.verify_media(root)["failures"]
    assert archive.list_entries(root) == []  # No video/run association was created.
    assert len(archive.stage_media(root, recordings, exclude=[active.name], only=[closed.name])["staged"]) == 1
    (root / "videos" / "unlinked" / closed.name).write_bytes(b"changed")
    assert len(archive.verify_media(root)["failures"]) == 1


def test_root_relocation_keeps_hidden_absolute_path_aliases_and_is_resumable(tmp_path, monkeypatch):
    recordings = tmp_path / "recordings"
    recordings.mkdir()
    root = recordings / "archive"
    main(["archive", "init", "--root", str(root)])
    media = recordings / "legacy.mkv"
    media.write_bytes(b"video bytes")
    source_dir = recordings / "oracle_runs"
    run_dir = source_dir / "run-x"
    run_dir.mkdir(parents=True)
    (run_dir / "session.json").write_text('{"run_id":"run-x","n_steps":0}', encoding="utf-8")
    (run_dir / "steps.ndjson").write_text("", encoding="utf-8")
    eval_dir = recordings / "evaluation_slices"
    eval_dir.mkdir()
    (eval_dir / "manifest.json").write_text('{"video":"F:/OBS_RECORDINGS/legacy.mkv"}', encoding="utf-8")
    log = recordings / "capture.log"
    log.write_text("diagnostic", encoding="utf-8")
    assert archive.stage_media(root, recordings, min_age_hours=0)["staged"][0]["video"] == media.name
    monkeypatch.setattr(archive, "_require_quiescent_runtime", lambda: None)
    assert archive.relocate_root(root, recordings, apply=False)["count"] == 4
    result = archive.relocate_root(root, recordings, apply=True, io_dir=tmp_path / "empty-io")
    assert result["count"] == 4
    assert source_dir.is_symlink()
    assert eval_dir.is_symlink()
    assert media.is_symlink()
    assert log.is_symlink()
    assert (source_dir / "run-x" / "session.json").is_file()
    assert (media.read_bytes() == b"video bytes")
    assert (root / "source-originals" / "oracle_runs" / "run-x" / "session.json").is_file()
    assert not archive.verify_relocation(root)["failures"]
    assert not archive.verify_media(root)["failures"]
    assert archive.relocate_root(root, recordings, apply=True, io_dir=tmp_path / "empty-io")["count"] == 0
    shutil.rmtree(tmp_path / "empty-io", ignore_errors=True)


def test_hidden_reparse_link_marks_the_alias_not_its_target():
    if os.name != "nt":
        pytest.skip("Windows compatibility-link attributes")
    with tempfile.TemporaryDirectory() as temp:
        parent = Path(temp)
        target = parent / "target.txt"
        link = parent / "legacy.txt"
        target.write_text("archive bytes", encoding="utf-8")
        os.symlink(target, link)
        hidden = archive._hide_reparse_link(link)
        assert archive._link_target(link) == target.resolve()
        if hidden:
            attrs_target = int(__import__("ctypes").windll.kernel32.GetFileAttributesW(str(target)))
            attrs_link = int(__import__("ctypes").windll.kernel32.GetFileAttributesW(str(link)))
            assert not (attrs_target & 0x2)
            assert attrs_link & 0x2


def test_relocation_recovers_verified_target_when_source_was_moved(tmp_path):
    source = tmp_path / "old-path.mkv"
    target = tmp_path / "archive" / "videos" / "old-path.mkv"
    target.parent.mkdir(parents=True)
    target.write_bytes(b"verified bytes")
    expected = archive._digest(target)

    try:
        archive._relocate_item(source, target, "file", expected, 1, target.stat().st_size)
    except OSError as error:
        if os.name == "nt":
            pytest.skip(f"Windows symlink permission unavailable: {error}")
        raise

    assert source.is_symlink()
    assert source.resolve() == target.resolve()
    assert target.read_bytes() == b"verified bytes"


def test_directory_recovery_link_failure_preserves_retryable_target(tmp_path, monkeypatch):
    source = tmp_path / "old-captures"
    target = tmp_path / "archive" / "source-originals" / "oracle_runs"
    target.mkdir(parents=True)
    (target / "session.json").write_bytes(b"session")
    (target / "steps.ndjson").write_bytes(b"steps")
    expected, count, size = archive._tree_fingerprint(target)

    def fail_link(*args, **kwargs):
        raise OSError("symlink privilege unavailable")

    monkeypatch.setattr(archive.os, "symlink", fail_link)
    with pytest.raises(OSError, match="symlink privilege unavailable"):
        archive._relocate_item(source, target, "directory", expected, count, size)

    assert not source.exists()
    assert archive._tree_fingerprint(target) == (expected, count, size)
    monkeypatch.undo()
    archive._relocate_item(source, target, "directory", expected, count, size)
    assert source.is_symlink()
    assert source.resolve() == target.resolve()
    assert archive._tree_fingerprint(source) == (expected, count, size)


def test_directory_recovery_link_points_to_verified_target(tmp_path):
    source = tmp_path / "old-captures"
    target = tmp_path / "archive" / "source-originals" / "oracle_runs"
    target.mkdir(parents=True)
    (target / "session.json").write_bytes(b"session")
    expected, count, size = archive._tree_fingerprint(target)

    try:
        archive._relocate_item(source, target, "directory", expected, count, size)
    except OSError as error:
        if os.name == "nt":
            pytest.skip(f"Windows directory-symlink permission unavailable: {error}")
        raise

    assert source.is_symlink()
    assert source.resolve() == target.resolve()
    assert archive._tree_fingerprint(source) == (expected, count, size)


def test_relocate_root_resumes_after_move_when_link_creation_fails(tmp_path, monkeypatch, capsys):
    recordings = tmp_path / "recordings"
    recordings.mkdir()
    root = recordings / "showman-archive"
    assert main(["archive", "init", "--root", str(root)]) == 0
    capsys.readouterr()
    source = recordings / "oracle_runs"
    source.mkdir()
    (source / "evidence.txt").write_bytes(b"archive bytes")
    plan = archive.relocate_root(root, recordings)
    item = plan["plan"][0]
    receipt = root / "backups" / "root-relocation-plan.json"
    receipt.write_text(json.dumps({"recordings_root": str(recordings), "items": plan["plan"]}),
                       encoding="utf-8")
    target = Path(item["target"])
    target.parent.mkdir(parents=True, exist_ok=True)
    os.replace(source, target)  # Simulate interruption after move, before alias creation.
    monkeypatch.setattr(archive, "_require_quiescent_runtime", lambda: None)

    def fail_link(*args, **kwargs):
        raise OSError("symlink privilege unavailable")

    monkeypatch.setattr(archive.os, "symlink", fail_link)
    with pytest.raises(OSError, match="symlink privilege unavailable"):
        archive.relocate_root(root, recordings, apply=True, io_dir=tmp_path / "empty-io")
    assert not source.exists()
    assert (target / "evidence.txt").read_bytes() == b"archive bytes"

    monkeypatch.undo()
    monkeypatch.setattr(archive, "_require_quiescent_runtime", lambda: None)
    result = archive.relocate_root(root, recordings, apply=True, io_dir=tmp_path / "empty-io")
    assert result["applied"]
    assert source.is_symlink()
    assert source.resolve() == target.resolve()
    assert not archive.verify_relocation(root)["failures"]


@pytest.mark.parametrize("min_age_hours", [-1, float("nan"), float("inf"), -float("inf"), True])
def test_media_staging_rejects_invalid_closure_threshold(tmp_path, min_age_hours):
    recordings = tmp_path / "recordings"
    recordings.mkdir()
    root = recordings / "archive"
    main(["archive", "init", "--root", str(root)])
    with pytest.raises(ValueError, match="finite non-negative"):
        archive.stage_media(root, recordings, min_age_hours=min_age_hours)


def test_media_staging_skips_future_dated_file(tmp_path):
    recordings = tmp_path / "recordings"
    recordings.mkdir()
    root = recordings / "archive"
    main(["archive", "init", "--root", str(root)])
    video = recordings / "future.mkv"
    video.write_bytes(b"possibly active recording")
    future = time.time() + 3600
    os.utime(video, (future, future))
    result = archive.stage_media(root, recordings, min_age_hours=0)
    assert result["staged"] == []
    assert result["skipped"] == [{"video": video.name, "reason": "recently_modified"}]


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
