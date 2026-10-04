"""Record and inspect the evidence used to validate Balatro reconstruction."""

import argparse
from contextlib import redirect_stdout
import json
import sys
from pathlib import Path

from alembic import command as migrations
from alembic.config import Config
from sqlalchemy.exc import SQLAlchemyError

from ground_truth import file_ipc_bridge, eval_manifest
from ground_truth.recording_association import AssociationResult, associate_recording
from planning import align_oracle_video, audit_oracle_runs
from run_bundle import BundleError, InspectionError, RunBundle, RunBundleInspector, read_oracle_run
from run_bundle import __main__ as bundle_cli


ROOT = Path(__file__).resolve().parents[1]


def emit(data, *, status="observed", diagnostics=None):
    print(json.dumps({"status": status, "data": data, "diagnostics": diagnostics or []},
                     ensure_ascii=False))


def initialize(database):
    """Create a new SQLite bundle through the existing Alembic migrations."""
    path = Path(database).resolve()
    if not path.parent.is_dir():
        raise ValueError("database parent does not exist")
    # Exclusive reservation prevents accidental upgrades/overwrites of existing evidence.
    with path.open("xb"):
        pass
    config = Config(str(ROOT / "alembic.ini"))
    config.set_main_option("script_location", str(ROOT / "alembic"))
    config.set_main_option("sqlalchemy.url", ("sqlite:///" + path.as_posix()).replace("%", "%%"))
    migrations.upgrade(config, "head")
    return str(path)


def check_bundle(database):
    inspector = RunBundleInspector(database)
    try:
        inspector.list_runs()
    finally:
        inspector.close()


def associate(args):
    inspector = RunBundleInspector(args.db)
    try:
        summary = inspector.summary(args.run)["data"]
    finally:
        inspector.close()
    marker_error = None
    try:
        marker = json.loads(args.marker.read_text(encoding="utf-8"))
    except (OSError, ValueError) as error:
        marker = None
        marker_error = str(error)
    # The existing boundary validates without writing when passed an inert sink.
    class Preview:
        def add_provenance(self, run_id, values):
            pass
    validation = associate_recording(Preview(), args.run, confirmed=True, marker=marker,
                                     confirmed_by=args.confirmed_by,
                                     video_ref=str(args.video) if args.video else None)
    checkpoint = {
        "run_id": args.run, "lifecycle_status": summary["run"]["status"],
        "recording_policy": "required" if args.required else "optional",
        "marker_file": str(args.marker), "marker_found": marker_error is None,
        "marker_source_error": marker_error,
        "marker_validation": validation.as_dict(),
        "present_items": {"bundle": args.db, "marker": marker,
                          "video_reference": str(args.video) if args.video else None,
                          "video_file_present": args.video.is_file() if args.video else None},
        "choices": ["confirm", "decline", "interrupt"],
    }
    print(json.dumps(checkpoint, ensure_ascii=False), file=sys.stderr)
    print("Correct an item by typing the correction; this stops association for review.", file=sys.stderr)
    try:
        print("Choose confirm, decline, or interrupt: ", end="", file=sys.stderr, flush=True)
        choice = input().strip().lower()
    except (Exception, KeyboardInterrupt):
        choice = "interrupt"
    if choice not in {"confirm", "decline", "interrupt"}:
        result = AssociationResult("interrupted", "summary_disputed",
                                   "summary was corrected or no explicit choice was supplied; inspect and retry")
    elif choice == "confirm" and args.video is not None and not args.video.is_file():
        result = AssociationResult("invalid", "video_missing", "proposed video file is not present")
    else:
        bundle = RunBundle(args.db)
        try:
            result = associate_recording(bundle, args.run, confirmed=choice == "confirm",
                                         interrupted=choice == "interrupt", marker=marker,
                                         confirmed_by=args.confirmed_by,
                                         video_ref=str(args.video.resolve()) if args.video else None)
        finally:
            bundle.close()
    if args.required and result.status != "confirmed":
        result = AssociationResult("blocked", "recording_required",
                                   f"required recording coordination failed: {result.code}",
                                   result.recording_id, result.video_status)
    emit(result.as_dict(), status="observed" if result.status == "confirmed" else "unknown")
    return 0 if result.status in {"confirmed", "declined"} else 2


def demo(destination):
    """Exercise the real queue consumer and automatic intake with synthetic input."""
    root = destination.resolve()
    if not root.parent.is_dir():
        raise ValueError("demo parent does not exist")
    root.mkdir()  # Refuse existing destinations, even empty ones.
    io_dir = root / "synthetic_io"
    io_dir.mkdir()
    database = initialize(root / "bundle.sqlite")
    run_id = "demo-synthetic"
    for sequence, (page, action) in enumerate([
            ("Blind_Select", "SelectBlind"), ("In_Blind", "PlayHand")], 1):
        snapshot = {
            "schema_version": "producer/1.0.0", "ipc_schema_version": "file-queue/1.0.0",
            "step_id": f"{run_id}:{sequence}", "request_id": sequence,
            "capture_timestamp_ns": sequence * 1_000_000_000,
            "page_name": page, "action_taken": action, "state": {}, "objects": [],
            "pending_cards": [], "persistent_state": {},
            "meta": {"run_id": run_id, "producer": "showman-synthetic-demo",
                     "synthetic": True, "video_timestamp_ns": sequence * 1_000_000_000},
        }
        (io_dir / f"request_{run_id}_{sequence:012d}.json").write_text(
            json.dumps(snapshot), encoding="utf-8")
    (io_dir / f"run_end_{run_id}.json").write_text(json.dumps({
        "ipc_schema_version": "file-queue/1.0.0", "run_id": run_id,
        "outcome": "loss", "last_request_id": 2}), encoding="utf-8")
    bridge = file_ipc_bridge.FileIpcBridge(io_dir, root / "captures", bundle_db=database)
    with redirect_stdout(sys.stderr):
        bridge.step_once()
    inspector = RunBundleInspector(database)
    try:
        summary = inspector.summary(run_id)["data"]
        validation = inspector.validate(run_id, strict=True)["data"]
    finally:
        inspector.close()
    emit({"synthetic": True, "run_id": run_id, "database": database,
          "capture_directory": str(root / "captures" / run_id),
          "summary": summary, "validation": validation,
          "next_command": f'python -m showman inspect step --db "{database}" --run {run_id} --sequence 0'},
         status="derived")
    return 0


def build_parser():
    parser = argparse.ArgumentParser(prog="python -m showman", description=__doc__,
                                     epilog="Start with demo. See docs/capture/README.md for the agent guide.")
    surfaces = parser.add_subparsers(dest="surface", required=True)
    surfaces.add_parser("record", parents=[file_ipc_bridge.build_parser(add_help=False)],
                        help="consume game messages; optionally import terminal runs automatically")
    surfaces.add_parser("inspect", parents=[bundle_cli.build_parser(
        add_help=False, include_import=False, prog="python -m showman inspect")],
                        help="read SQLite evidence without changing it")
    store = surfaces.add_parser("store", help="create a bundle or import a capture")
    operations = store.add_subparsers(dest="operation", required=True)
    init = operations.add_parser("init", help="create a NEW SQLite bundle through Alembic")
    init.add_argument("--db", required=True, help="new SQLite filename; parent must exist")
    ingest = operations.add_parser("import", help="import session.json and steps.ndjson without modifying them")
    ingest.add_argument("--db", required=True)
    ingest.add_argument("--source", required=True)
    capture = surfaces.add_parser("capture", help="read or audit a file capture directory")
    operations = capture.add_subparsers(dest="operation", required=True)
    for name, help_text in [("summary", "read source objects and diagnostics"),
                            ("audit", "audit finalized capture integrity and report conformance gaps")]:
        child = operations.add_parser(name, help=help_text)
        child.add_argument("source", type=Path)
    surfaces.add_parser("align", parents=[align_oracle_video.build_parser(add_help=False)],
                        help="compute candidate frame indices; does not confirm visual alignment")
    association = surfaces.add_parser("associate", help="ask a human to confirm recording provenance")
    association.add_argument("--db", required=True)
    association.add_argument("--run", required=True)
    association.add_argument("--marker", type=Path, required=True, help="producer recording marker JSON")
    association.add_argument("--video", type=Path, help="existing local video file; never embedded in SQLite")
    association.add_argument("--confirmed-by", required=True, help="identity of the human making this decision")
    association.add_argument("--required", action="store_true", help="return blocked unless association is confirmed")
    annotations = surfaces.add_parser("annotations", help="export independently reviewed development labels")
    operations = annotations.add_subparsers(dest="operation", required=True)
    export = operations.add_parser("export", help="write deterministic first-slice development manifest")
    export.add_argument("input", type=Path)
    export.add_argument("output", type=Path)
    example = surfaces.add_parser("demo", help="run synthetic capture-to-inspection onboarding without Balatro/OBS")
    example.add_argument("--output-dir", type=Path, required=True, help="new directory beneath an existing parent")
    return parser


def main(argv=None):
    argv = list(sys.argv[1:] if argv is None else argv)
    args = build_parser().parse_args(argv)
    try:
        if args.surface == "inspect":
            return bundle_cli.main(argv[1:])
        if args.surface == "record":
            if args.bundle_db:
                check_bundle(args.bundle_db)
            file_ipc_bridge.main(argv[1:])
            return 0
        if args.surface == "store":
            if args.operation == "init":
                emit({"database": initialize(args.db)})
                return 0
            check_bundle(args.db)
            return bundle_cli.main(["import-oracle", "--db", args.db, "--source", args.source])
        if args.surface == "capture":
            if args.operation == "summary":
                result = read_oracle_run(args.source)
                emit(result, status="observed" if result["classification"] == "healthy" else "unknown")
                return 0 if result["classification"] == "healthy" else 2
            audit_oracle_runs.INTEGRITY_FAILURES.clear()
            return audit_oracle_runs.main(["showman capture audit", str(args.source)])
        if args.surface == "align":
            return align_oracle_video.main(argv[1:])
        if args.surface == "associate":
            return associate(args)
        if args.surface == "annotations":
            emit({"sha256": eval_manifest.export(args.input, args.output),
                  "output": str(args.output), "scoring_status": "development_only_unscored"}, status="derived")
            return 0
        return demo(args.output_dir)
    except InspectionError as error:
        emit(None, status="unknown", diagnostics=[{"code": error.code, "message": error.message}])
    except (BundleError, SQLAlchemyError, OSError, ValueError, KeyError, TypeError) as error:
        emit(None, status="unknown", diagnostics=[{"code": "operation_failed", "message": str(error)}])
    except SystemExit as error:
        # The legacy alignment utility exits with a text diagnostic when its marker is absent.
        emit(None, status="unknown", diagnostics=[{"code": "operation_failed", "message": str(error)}])
    return 2


if __name__ == "__main__":
    sys.exit(main())
