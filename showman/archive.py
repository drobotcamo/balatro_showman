"""Non-destructive operational capture catalog and archive staging."""

import argparse
from contextlib import closing
import hashlib
import json
import math
import os
import re
import shutil
import sqlite3
import subprocess
import sys
from datetime import datetime, timezone
from pathlib import Path

from sqlalchemy import create_engine, select
from sqlalchemy.exc import SQLAlchemyError
from sqlalchemy.orm import Session

from run_bundle import BundleError, InspectionError, RunBundle, RunBundleInspector
from run_bundle.models import ArchiveEntry, ArchiveMedia, Provenance, Run


CAPTURE_ROOTS = (
    "oracle_runs", "oracle_runs_live3", "oracle_runs_live3b",
    "oracle_runs_issue79", "oracle_runs_issue81", "oracle_runs_issue123",
    "oracle_runs_issue129",
)
SOURCE_FILES = ("session.json", "steps.ndjson", "mechanics_reference.ndjson")
NAME = re.compile(r"[A-Za-z0-9][A-Za-z0-9._-]{0,127}\Z")


def archive_root(value=None):
    root = value or os.environ.get("SHOWMAN_ARCHIVE_ROOT")
    if not root:
        raise ValueError("specify --root or set SHOWMAN_ARCHIVE_ROOT")
    return Path(root).resolve()


def database(root):
    return root / "catalog.sqlite"


def upgrade(root):
    """Explicit Alembic upgrade of an existing catalog (never on inspection)."""
    root = archive_root(root)
    if not database(root).is_file():
        raise ValueError("existing catalog required for explicit upgrade")
    from alembic import command
    from alembic.config import Config
    backup_dir = root / "backups"
    backup_dir.mkdir(exist_ok=True)
    backup = backup_dir / ("catalog-before-upgrade-" + datetime.now(timezone.utc).strftime("%Y%m%dT%H%M%S%fZ") + ".sqlite")
    with backup.open("xb"):
        pass
    with closing(sqlite3.connect("file:" + database(root).as_posix() + "?mode=ro", uri=True)) as source:
        with closing(sqlite3.connect(backup)) as destination:
            source.backup(destination)
    repo = Path(__file__).resolve().parents[1]
    config = Config(str(repo / "alembic.ini"))
    config.set_main_option("script_location", str(repo / "alembic"))
    config.set_main_option("sqlalchemy.url", ("sqlite:///" + database(root).as_posix()).replace("%", "%%"))
    command.upgrade(config, "head")
    return {"database": str(database(root)), "schema": "head", "backup": str(backup)}


def _digest(path):
    h = hashlib.sha256()
    with path.open("rb") as stream:
        for block in iter(lambda: stream.read(1024 * 1024), b""):
            h.update(block)
    return h.hexdigest()


def _components(path):
    for part in (path, *path.parents):
        if part.is_symlink() or (part.exists() and getattr(part, "is_junction", lambda: False)()):
            raise ValueError(f"reparse point in source path: {part}")


def source_fingerprint(source):
    source = Path(source).absolute()
    _components(source)
    if not source.is_dir():
        raise ValueError(f"capture directory missing: {source}")
    files = {}
    for name in SOURCE_FILES:
        path = source / name
        if path.exists():
            _components(path)
            if not path.is_file():
                raise ValueError(f"capture component is not a file: {path}")
            files[name] = _digest(path)
        elif name != "mechanics_reference.ndjson":
            raise ValueError(f"capture component missing: {path}")
    metadata = json.loads((source / "session.json").read_text(encoding="utf-8"))
    run_id = metadata.get("run_id")
    if not isinstance(run_id, str) or not NAME.fullmatch(run_id):
        raise ValueError(f"unsafe or missing run ID: {source}")
    identity = json.dumps({
        "session_sha256": files["session.json"],
        "steps_sha256": files["steps.ndjson"],
        **({"mechanics_reference_sha256": files["mechanics_reference.ndjson"]}
           if "mechanics_reference.ndjson" in files else {}),
    }, sort_keys=True, separators=(",", ":"))
    return {"run_id": run_id, "source": str(source), "files": files,
            "source_identity": identity, "n_steps_declared": metadata.get("n_steps"),
            "outcome": metadata.get("outcome"), "recording_marker": "recording" in metadata}


def inventory(recordings_root):
    root = Path(recordings_root).absolute()
    _components(root)
    if not root.is_dir():
        raise ValueError(f"recordings root missing: {root}")
    entries = []
    for name in CAPTURE_ROOTS:
        base = root / name
        if not base.is_dir():
            raise ValueError(f"approved capture root missing: {base}")
        for child in sorted(base.iterdir()):
            if child.is_dir() and (child / "session.json").exists():
                entries.append(source_fingerprint(child))
    ids = [entry["run_id"] for entry in entries]
    if len(ids) != len(set(ids)):
        raise ValueError("duplicate producer run ID across approved roots")
    return {"capture_roots": list(CAPTURE_ROOTS), "captures": entries,
            "count": len(entries), "declared_steps": sum(item["n_steps_declared"] for item in entries)}


def _engine(root):
    path = database(root)
    if not path.is_file():
        raise ValueError(f"catalog missing: {path}; initialize it explicitly")
    return create_engine("sqlite:///" + path.as_posix(), future=True)


def _build(metadata):
    build = metadata.get("capture_build") or {}
    if not isinstance(build, dict):
        return {}
    return build


def _checked_copy(source, target, expected):
    # Never replace an existing archive member; identical retries are safe.
    if target.exists():
        _components(target)
        if not target.is_file() or _digest(target) != expected:
            raise ValueError(f"archive destination conflicts: {target}")
        return
    with source.open("rb") as input_stream, target.open("xb") as output_stream:
        shutil.copyfileobj(input_stream, output_stream, 1024 * 1024)
        output_stream.flush()
        os.fsync(output_stream.fileno())
    if _digest(target) != expected:
        raise ValueError(f"archive copy failed hash check: {target}")


def ingest(root, source):
    root = archive_root(root)
    info = source_fingerprint(source)
    destination = root / "captures" / info["run_id"]
    if destination.resolve() == Path(source).resolve():
        raise ValueError("source already occupies the archive destination")
    engine = _engine(root)
    try:
        with Session(engine) as s:
            existing = s.get(ArchiveEntry, info["run_id"])
            if existing and (existing.source_identity != info["source_identity"]
                             or existing.original_path != info["source"]):
                raise ValueError(f"catalog source identity/path conflict: {info['run_id']}")
        if destination.exists():
            _components(destination)
            if not destination.is_dir():
                raise ValueError(f"archive destination conflicts: {destination}")
        else:
            destination.mkdir()
        for name, digest in info["files"].items():
            _checked_copy(Path(source) / name, destination / name, digest)
        for extra in Path(source).iterdir():
            if extra.name in info["files"]:
                continue
            _components(extra)
            if not extra.is_file() or not NAME.fullmatch(extra.name):
                raise ValueError(f"unsupported capture member; preserve for manual review: {extra}")
            _checked_copy(extra, destination / extra.name, _digest(extra))
        if source_fingerprint(source)["source_identity"] != info["source_identity"]:
            raise ValueError("capture changed during staging; preserve both copies for diagnosis")
        staged = source_fingerprint(destination)
        if staged["source_identity"] != info["source_identity"]:
            raise ValueError("staged capture differs from source")
        bundle = RunBundle(str(database(root)))
        try:
            imported = bundle.import_oracle_directory(destination)
        finally:
            bundle.close()
        metadata = json.loads((destination / "session.json").read_text(encoding="utf-8"))
        build = _build(metadata)
        with Session(engine) as s, s.begin():
            row = s.get(ArchiveEntry, info["run_id"])
            if row is None:
                s.add(ArchiveEntry(
                    run_id=info["run_id"], original_path=info["source"],
                    capture_path=str(destination), source_identity=info["source_identity"],
                    capture_revision=build.get("producer_commit"),
                    bridge_revision=build.get("bridge_commit"),
                    producer_sha256=build.get("installed_producer_sha256"),
                    video_status="unassociated"))
        return {**info, "capture_path": str(destination), "import": imported}
    finally:
        engine.dispose()


def register_captured_run(root, source):
    """Index a run written directly beneath captures after its successful import."""
    root = archive_root(root)
    source = Path(source).resolve()
    if source.parent != root / "captures":
        raise ValueError("direct capture must live under archive/captures")
    info = source_fingerprint(source)
    metadata = json.loads((source / "session.json").read_text(encoding="utf-8"))
    build = _build(metadata)
    engine = _engine(root)
    try:
        with Session(engine) as s, s.begin():
            row = s.get(ArchiveEntry, info["run_id"])
            if row:
                if row.source_identity != info["source_identity"] or row.capture_path != str(source):
                    raise ValueError(f"existing run conflicts with capture: {info['run_id']}")
            else:
                s.add(ArchiveEntry(run_id=info["run_id"], original_path=str(source),
                                   capture_path=str(source), source_identity=info["source_identity"],
                                   capture_revision=build.get("producer_commit"),
                                   bridge_revision=build.get("bridge_commit"),
                                   producer_sha256=build.get("installed_producer_sha256"),
                                   video_status="unassociated"))
    finally:
        engine.dispose()


def list_entries(root):
    engine = _engine(archive_root(root))
    try:
        with Session(engine) as s:
            result = []
            for row in s.scalars(select(ArchiveEntry).order_by(ArchiveEntry.run_id)):
                run = s.get(Run, row.run_id)
                result.append({"run_id": row.run_id, "status": run.status,
                               "outcome": run.outcome, "original_path": row.original_path,
                               "capture_path": row.capture_path,
                               "producer_commit": row.capture_revision,
                               "bridge_commit": row.bridge_revision,
                               "installed_producer_sha256": row.producer_sha256,
                               "video_status": row.video_status, "video_path": row.video_path,
                               "video_sha256": row.video_sha256})
            return result
    finally:
        engine.dispose()


def verify(root, legacy_databases=()):
    """Read-only reconciliation of staged bytes, hashes and stored records."""
    root = archive_root(root)
    entries = list_entries(root)
    inspector = RunBundleInspector(str(database(root)))
    legacies = [RunBundleInspector(str(path)) for path in legacy_databases]
    try:
        legacy_lists = [{item["id"] for item in db.list_runs()["data"]} for db in legacies]
        failures = []
        total_steps = 0
        for entry in entries:
            run_id = entry["run_id"]
            try:
                original = source_fingerprint(entry["original_path"])
                staged = source_fingerprint(entry["capture_path"])
                if original["source_identity"] != staged["source_identity"]:
                    raise ValueError("source identity differs from archive copy")
                engine = _engine(root)
                try:
                    with Session(engine) as s:
                        catalog_identity = s.get(ArchiveEntry, run_id).source_identity
                finally:
                    engine.dispose()
                imported_identity = dict((p["key"], p["value"]) for p in
                                         inspector.provenance(run_id)["data"]).get("source.identity")
                if original["source_identity"] != catalog_identity or catalog_identity != imported_identity:
                    raise ValueError("current source differs from catalog/imported identity")
                if entry["video_status"] == "confirmed":
                    if not entry["video_sha256"] or not entry["video_path"] or not Path(entry["video_path"]).is_file():
                        raise ValueError("confirmed video file/hash missing")
                    if _digest(Path(entry["video_path"])) != entry["video_sha256"]:
                        raise ValueError("confirmed video bytes changed")
                original_names = {path.name for path in Path(entry["original_path"]).iterdir()}
                staged_names = {path.name for path in Path(entry["capture_path"]).iterdir()}
                if original_names != staged_names:
                    raise ValueError("original/staged directory member set differs")
                for path in Path(entry["original_path"]).iterdir():
                    if not path.is_file() or not (Path(entry["capture_path"]) / path.name).is_file():
                        raise ValueError(f"missing or unsupported original member: {path.name}")
                    if _digest(path) != _digest(Path(entry["capture_path"]) / path.name):
                        raise ValueError(f"archive member differs: {path.name}")
                validation = inspector.validate(run_id, strict=True)["data"]
                total_steps += original["n_steps_declared"]
                for db, ids in zip(legacies, legacy_lists):
                    if run_id not in ids:
                        continue
                    old = db.summary(run_id)["data"]
                    new = inspector.summary(run_id)["data"]
                    if (old["run"]["status"] != new["run"]["status"] or
                            old["record_count"] != new["record_count"] or
                            old["integrity"]["bundle_sha256"] != new["integrity"]["bundle_sha256"]):
                        raise ValueError("legacy bundle record/status comparison failed")
                if validation["status"] != "valid":
                    raise ValueError("catalog integrity invalid")
            except (OSError, ValueError, InspectionError) as error:
                failures.append({"run_id": run_id, "error": str(error)})
        return {"catalog_runs": len(entries), "declared_steps": total_steps,
                "legacy_matches": [len(ids & {e["run_id"] for e in entries}) for ids in legacy_lists],
                "failures": failures}
    finally:
        inspector.close()
        for db in legacies:
            db.close()


def sync_associations(root, legacy_db=None):
    """Transfer only already confirmed associations with matching source identity."""
    root = archive_root(root)
    source_db = Path(legacy_db).resolve() if legacy_db else database(root)
    if not source_db.is_file():
        raise ValueError(f"association source database missing: {source_db}")
    source_engine = create_engine("sqlite:///" + source_db.as_posix(), future=True)
    target_engine = _engine(root)
    transferred = []
    try:
        with Session(source_engine) as source, Session(target_engine) as target:
            for entry in target.scalars(select(ArchiveEntry).order_by(ArchiveEntry.run_id)):
                if not source.get(Run, entry.run_id):
                    continue
                provenance = {p.key: p.value for p in source.scalars(
                    select(Provenance).where(Provenance.run_id == entry.run_id))}
                if provenance.get("source.identity") != entry.source_identity:
                    raise ValueError(f"source identity conflict for association: {entry.run_id}")
                if provenance.get("recording.association_status") != "confirmed":
                    continue
                video = provenance.get("recording.video_ref")
                if not video or not Path(video).is_file():
                    raise ValueError(f"confirmed video reference missing: {entry.run_id}: {video}")
                digest = _digest(Path(video))
                if entry.video_sha256 and entry.video_sha256 != digest:
                    raise ValueError(f"video bytes changed: {entry.run_id}")
                if entry.video_path and entry.video_path != video:
                    staged = Path(entry.video_path)
                    if staged.parent != root / "videos" or not staged.is_file() or _digest(staged) != digest:
                        raise ValueError(f"video reference conflict: {entry.run_id}")
                else:
                    entry.video_path = video
                entry.video_sha256 = digest
                entry.video_status = "confirmed"
                transferred.append(entry.run_id)
            # Copy original confirmation evidence only after all entries have passed.
            if source_db != database(root):
                bundle = RunBundle(str(database(root)))
                try:
                    for run_id in transferred:
                        values = {p.key: p.value for p in source.scalars(select(Provenance).where(
                            Provenance.run_id == run_id, Provenance.key.like("recording.%")))}
                        bundle.add_provenance(run_id, values)
                finally:
                    bundle.close()
            target.commit()
        return transferred
    finally:
        source_engine.dispose()
        target_engine.dispose()


def stage_video(root, run_id):
    """Copy an existing confirmed video without changing its original provenance."""
    root = archive_root(root)
    engine = _engine(root)
    try:
        with Session(engine) as s, s.begin():
            row = s.get(ArchiveEntry, run_id)
            if row is None or row.video_status != "confirmed" or not row.video_path or not row.video_sha256:
                raise ValueError("only an already confirmed, hashed video can be staged")
            original_provenance = {p.key: p.value for p in s.scalars(select(Provenance).where(
                Provenance.run_id == run_id))}
            original = Path(original_provenance.get("recording.video_ref", ""))
            _components(original)
            if not original.is_file() or _digest(original) != row.video_sha256:
                raise ValueError("original video differs from confirmed hash")
            name = original.name
            if not NAME.fullmatch(name):
                # OBS's native timestamp filenames contain spaces; preserve them.
                if not re.fullmatch(r"[0-9]{4}-[0-9]{2}-[0-9]{2} [0-9]{2}-[0-9]{2}-[0-9]{2}\.mkv", name):
                    raise ValueError("video basename is unsafe; inspect before staging")
            target = root / "videos" / name
            if target.resolve() != original.resolve():
                _checked_copy(original, target, row.video_sha256)
            if _digest(original) != row.video_sha256:
                raise ValueError("original video changed while being copied")
            affected = s.scalars(select(ArchiveEntry).where(
                ArchiveEntry.video_status == "confirmed", ArchiveEntry.video_sha256 == row.video_sha256)).all()
            for member in affected:
                member_provenance = {p.key: p.value for p in s.scalars(select(Provenance).where(
                    Provenance.run_id == member.run_id))}
                if member_provenance.get("recording.video_ref") == str(original):
                    member.video_path = str(target)
            return {"video": str(target), "sha256": row.video_sha256,
                    "original": str(original)}
    finally:
        engine.dispose()


def media_inventory(root, recordings_root):
    """List top-level OBS MKVs without interpreting filename as run identity."""
    root = archive_root(root)
    source_root = Path(recordings_root).resolve()
    _components(source_root)
    if (not source_root.is_dir() or source_root == root
            or root not in source_root.parents and source_root not in root.parents):
        raise ValueError("recordings root must contain the archive and exist")
    engine = _engine(root)
    try:
        with Session(engine) as s:
            entries = []
            for source in sorted(source_root.glob("*.mkv")):
                _components(source)
                if not source.is_file():
                    raise ValueError(f"video is not a regular file: {source}")
                row = s.get(ArchiveMedia, str(source))
                stat = source.stat()
                entries.append({"original": str(source), "bytes": stat.st_size,
                                "archive_path": row.archive_path if row else None,
                                "catalog_status": row.catalog_status if row else "not_staged"})
            return entries
    finally:
        engine.dispose()


def stage_media(root, recordings_root, *, exclude=(), only=(), min_age_hours=1):
    """Copy closed top-level recordings, retaining every original and its references."""
    root = archive_root(root)
    if (isinstance(min_age_hours, bool) or not isinstance(min_age_hours, (int, float))
            or not math.isfinite(min_age_hours) or min_age_hours < 0):
        raise ValueError("min_age_hours must be a finite non-negative number")
    names = set(exclude)
    if any(Path(name).name != name or name in {"", ".", ".."} for name in names):
        raise ValueError("--exclude must be a video basename")
    inventory = media_inventory(root, recordings_root)
    only = set(only)
    if any(Path(name).name != name or name in {"", ".", ".."} for name in only):
        raise ValueError("--only must be a video basename")
    engine = _engine(root)
    result = {"staged": [], "skipped": [], "failures": []}
    try:
        for item in inventory:
            original = Path(item["original"])
            if only and original.name not in only:
                continue
            if original.name in names:
                result["skipped"].append({"video": original.name, "reason": "explicitly_excluded"})
                continue
            try:
                before = original.stat()
                age_seconds = datetime.now(timezone.utc).timestamp() - before.st_mtime
                if age_seconds < 0 or age_seconds < min_age_hours * 3600:
                    result["skipped"].append({"video": original.name, "reason": "recently_modified"})
                    continue
                with Session(engine) as s:
                    confirmed = s.scalars(select(ArchiveEntry).where(
                        ArchiveEntry.video_status == "confirmed")).all()
                    matched = [row for row in confirmed if row.video_path and
                               Path(row.video_path).name == original.name and
                               Path(row.video_path).parent == root / "videos"]
                expected = _digest(original)
                if matched and any(row.video_sha256 != expected for row in matched):
                    raise ValueError("confirmed video hash conflicts with original")
                category = "confirmed" if matched else "unlinked"
                destination = (root / "videos" / original.name if matched else
                               root / "videos" / "unlinked" / original.name)
                if not destination.parent.is_dir():
                    if category != "unlinked" or destination.parent.parent != root / "videos":
                        raise ValueError("unexpected video destination parent")
                    destination.parent.mkdir()
                with Session(engine) as s, s.begin():
                    row = s.get(ArchiveMedia, str(original))
                    if row and (row.archive_path != str(destination) or row.sha256 != expected
                                or row.byte_count != before.st_size or row.catalog_status != category):
                        raise ValueError("existing media inventory conflicts with source")
                    _checked_copy(original, destination, expected)
                    after = original.stat()
                    if (after.st_size != before.st_size or after.st_mtime_ns != before.st_mtime_ns
                            or _digest(original) != expected):
                        raise ValueError("source changed during media staging; retain copy for diagnosis")
                    if row is None:
                        s.add(ArchiveMedia(original_path=str(original), archive_path=str(destination),
                                           sha256=expected, byte_count=before.st_size,
                                           catalog_status=category))
                result["staged"].append({"video": original.name, "status": category,
                                         "sha256": expected, "archive_path": str(destination)})
            except (OSError, ValueError, SQLAlchemyError) as error:
                result["failures"].append({"video": original.name, "error": str(error)})
        return result
    finally:
        engine.dispose()


def verify_media(root):
    """Read-only byte reconciliation of all registered media copies."""
    engine = _engine(archive_root(root))
    try:
        with Session(engine) as s:
            rows = s.scalars(select(ArchiveMedia).order_by(ArchiveMedia.original_path)).all()
            failures = []
            for row in rows:
                try:
                    source, staged = Path(row.original_path), Path(row.archive_path)
                    _components(source)
                    _components(staged)
                    if (not source.is_file() or not staged.is_file()
                            or source.stat().st_size != row.byte_count
                            or staged.stat().st_size != row.byte_count
                            or _digest(source) != row.sha256 or _digest(staged) != row.sha256):
                        raise ValueError("original/staged bytes differ from inventory")
                except (OSError, ValueError) as error:
                    failures.append({"video": row.original_path, "error": str(error)})
            return {"media_count": len(rows), "failures": failures}
    finally:
        engine.dispose()


def review(root, run_ids, *, export_root=None, open_browser=False,
           recording_start_ns=None, timing_evidence=None):
    root = archive_root(root)
    if isinstance(run_ids, str):
        run_ids = [run_ids]
    if not run_ids or len(run_ids) != len(set(run_ids)):
        raise ValueError("provide each ordered run exactly once")
    engine = _engine(root)
    try:
        with Session(engine) as s:
            rows = [s.get(ArchiveEntry, run_id) for run_id in run_ids]
            if any(row is None for row in rows):
                raise ValueError("requested run is not in the archive")
            if any(row.video_status != "confirmed" or not row.video_path for row in rows):
                raise ValueError("run has no confirmed video association; supply explicit paths to the viewer")
            if len({row.video_path for row in rows}) != 1:
                raise ValueError("ordered runs must share one confirmed video")
            video = Path(rows[0].video_path)
            if not video.is_file() or any(not Path(row.capture_path).is_dir() for row in rows):
                raise ValueError("catalog video/capture location missing; preserve evidence and repair location mapping")
            siblings = {row.run_id for row in s.scalars(select(ArchiveEntry).where(
                ArchiveEntry.video_path == rows[0].video_path,
                ArchiveEntry.video_status == "confirmed"))}
            if siblings != set(run_ids):
                raise ValueError("video has other confirmed segments; list all --run IDs in explicit order")
            command = [sys.executable, "-m", "ground_truth.qa_viewer", "--video", str(video),
                       "--export-root", str(export_root or root / "reviews")]
            for row in rows:
                command.extend(("--run", row.capture_path))
            if recording_start_ns is not None:
                if not timing_evidence:
                    raise ValueError("diagnostic recording-start override requires timing evidence")
                command.extend(("--recording-start-ns", str(recording_start_ns),
                                "--timing-evidence", timing_evidence))
            if open_browser:
                command.append("--open")
            return subprocess.call(command)
    finally:
        engine.dispose()


def main(argv=None):
    parser = argparse.ArgumentParser(description=__doc__)
    commands = parser.add_subparsers(dest="command", required=True)
    for name in ("init", "upgrade", "ingest", "list", "review", "sync-associations", "verify",
                 "stage-video", "media-inventory", "stage-media", "verify-media"):
        child = commands.add_parser(name)
        child.add_argument("--root", help="archive root; otherwise SHOWMAN_ARCHIVE_ROOT")
        if name == "ingest":
            child.add_argument("--source", required=True, type=Path)
        if name == "review":
            child.add_argument("--run", required=True, action="append", help="ordered segment ID; repeat for one video")
            child.add_argument("--export-root", type=Path)
            child.add_argument("--open", action="store_true")
            child.add_argument("--recording-start-ns", type=int)
            child.add_argument("--timing-evidence")
        if name == "sync-associations":
            child.add_argument("--legacy-db", type=Path,
                               help="existing bundle; omit to refresh catalog associations")
        if name == "verify":
            child.add_argument("--legacy-db", type=Path, action="append", default=[])
        if name == "stage-video":
            child.add_argument("--run", required=True)
        if name in {"media-inventory", "stage-media"}:
            child.add_argument("--recordings-root", type=Path, required=True)
        if name == "stage-media":
            child.add_argument("--exclude", action="append", default=[], help="basename of an in-use video")
            child.add_argument("--only", action="append", default=[], help="stage only this basename (repeatable)")
            child.add_argument("--min-age-hours", type=float, default=1)
    plan = commands.add_parser("inventory", help="read-only inventory of the seven approved capture roots")
    plan.add_argument("--recordings-root", type=Path, required=True)
    args = parser.parse_args(argv)
    try:
        if args.command == "inventory":
            value = inventory(args.recordings_root)
        else:
            root = archive_root(args.root)
            if args.command == "init":
                if not root.parent.is_dir() or root.exists():
                    raise ValueError("archive root must be new, with an existing parent")
                root.mkdir()
                (root / "captures").mkdir()
                (root / "videos").mkdir()
                (root / "reviews").mkdir()
                (root / "backups").mkdir()
                from showman.__main__ import initialize
                initialize(database(root))
                value = {"root": str(root), "database": str(database(root))}
            elif args.command == "upgrade":
                value = upgrade(root)
            elif args.command == "ingest":
                value = ingest(root, args.source)
            elif args.command == "list":
                value = list_entries(root)
            elif args.command == "sync-associations":
                value = {"confirmed_runs": sync_associations(root, args.legacy_db)}
            elif args.command == "verify":
                value = verify(root, args.legacy_db)
                print(json.dumps({"status": "derived" if not value["failures"] else "unknown",
                                  "data": value, "diagnostics": value["failures"]}))
                return 0 if not value["failures"] else 2
            elif args.command == "stage-video":
                value = stage_video(root, args.run)
            elif args.command == "media-inventory":
                value = media_inventory(root, args.recordings_root)
            elif args.command == "stage-media":
                value = stage_media(root, args.recordings_root, exclude=args.exclude,
                                    only=args.only,
                                    min_age_hours=args.min_age_hours)
                print(json.dumps({"status": "observed" if not value["failures"] else "unknown",
                                  "data": value, "diagnostics": value["failures"]}))
                return 0 if not value["failures"] else 2
            elif args.command == "verify-media":
                value = verify_media(root)
                print(json.dumps({"status": "derived" if not value["failures"] else "unknown",
                                  "data": value, "diagnostics": value["failures"]}))
                return 0 if not value["failures"] else 2
            else:
                return review(root, args.run, export_root=args.export_root, open_browser=args.open,
                              recording_start_ns=args.recording_start_ns,
                              timing_evidence=args.timing_evidence)
        print(json.dumps({"status": "observed", "data": value, "diagnostics": []}))
        return 0
    except (OSError, ValueError, BundleError, SQLAlchemyError) as error:
        print(json.dumps({"status": "unknown", "data": None,
                          "diagnostics": [{"code": "archive_error", "message": str(error)}]}))
        return 2


if __name__ == "__main__":
    sys.exit(main())
