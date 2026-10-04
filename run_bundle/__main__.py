import argparse, json, sys
from sqlalchemy.exc import SQLAlchemyError
from .inspection import InspectionError, RunBundleInspector
from .repository import BundleError, ImportConflict, RunBundle

def build_parser(*, add_help=True, include_import=True, prog=None):
    p = argparse.ArgumentParser(add_help=add_help, prog=prog); sub = p.add_subparsers(dest="command", required=True)
    for name in ("list", "capabilities"):
        x = sub.add_parser(name); x.add_argument("--db", required=True); x.add_argument("--run")
    for name in ("summary", "step", "find", "provenance", "evidence", "validate", "outcome", "transitions", "diff"):
        x = sub.add_parser(name); x.add_argument("--db", required=True); x.add_argument("--run", required=True)
        if name in ("step",): x.add_argument("--sequence", type=int, required=True)
        if name in ("find", "evidence"): x.add_argument("--kind"); x.add_argument("--from", dest="sequence_from", type=int); x.add_argument("--to", dest="sequence_to", type=int)
        if name == "validate": x.add_argument("--strict", action="store_true")
        if name == "diff": x.add_argument("--from-sequence", type=int, required=True); x.add_argument("--to-sequence", type=int, required=True)
    if include_import:
        x = sub.add_parser("import-oracle", help="import one file-IPC run directory into the SQLite bundle")
        x.add_argument("--db", required=True); x.add_argument("--source", required=True)
    return p

def main(argv=None):
    p = build_parser()
    try:
        a = p.parse_args(argv)
        if a.command == "import-oracle":
            out = {"status": "observed", "data": RunBundle(a.db).import_oracle_directory(a.source), "diagnostics": []}
        else:
            i = RunBundleInspector(a.db)
            if a.command == "list": out = i.list_runs()
            elif a.command == "capabilities": out = i.capabilities(a.run)
            elif a.command == "summary": out = i.summary(a.run)
            elif a.command == "step": out = i.get_record(a.run, a.sequence)
            elif a.command == "find": out = i.find_records(a.run, kind=a.kind, sequence_from=a.sequence_from, sequence_to=a.sequence_to)
            elif a.command == "evidence": out = i.evidence(a.run, kind=a.kind, sequence_from=a.sequence_from, sequence_to=a.sequence_to)
            elif a.command == "diff": out = i.diff(a.run, a.from_sequence, a.to_sequence)
            elif a.command == "validate": out = i.validate(a.run, strict=a.strict)
            else: out = getattr(i, a.command)(a.run)
    except InspectionError as e:
        out = {"status": "unknown", "data": None, "diagnostics": [{"code": e.code, "message": e.message}]}; print(json.dumps(out), file=sys.stdout); return 2
    except ImportConflict as e:
        out = {"status": "unknown", "data": None, "diagnostics": [{"code": "run_identity_conflict", "message": str(e)}]}; print(json.dumps(out), file=sys.stdout); return 2
    except BundleError as e:
        out = {"status": "unknown", "data": None, "diagnostics": [{"code": "import_failed", "message": str(e)}]}; print(json.dumps(out), file=sys.stdout); return 2
    except (SQLAlchemyError, OSError) as e:
        out = {"status": "unknown", "data": None, "diagnostics": [{"code": "storage_error", "message": str(e)}]}; print(json.dumps(out), file=sys.stdout); return 2
    print(json.dumps(out, ensure_ascii=False)); return 0
if __name__ == "__main__": sys.exit(main())
