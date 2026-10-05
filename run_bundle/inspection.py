"""Read-only, JSON-friendly inspection of a persisted run bundle."""

import base64
import hashlib
import json
from pathlib import Path
from sqlalchemy import create_engine, select
from sqlalchemy.engine import make_url
from sqlalchemy.orm import Session

from .models import Integrity, Provenance, Record, Run

STATUSES = {"observed", "derived", "missing", "unknown", "unsupported"}


class InspectionError(Exception):
    def __init__(self, code, message):
        super().__init__(message)
        self.code, self.message = code, message


class RunBundleInspector:
    def __init__(self, url: str):
        # The documented CLI accepts a SQLite filename as well as a SQLAlchemy
        # URL. Normalize paths here so library and CLI behavior stay identical.
        if "://" not in url:
            if url == ":memory:":
                url = "sqlite:///:memory:"
            else:
                database = Path(url).resolve().as_posix()
                url = f"sqlite:///{database}"
        parsed = make_url(url)
        if parsed.drivername.startswith("sqlite") and parsed.database not in (None, ":memory:"):
            if not Path(parsed.database).exists():
                raise InspectionError("storage_not_found", f"database does not exist: {parsed.database}")
        self._engine = create_engine(url, future=True)

    def close(self):
        self._engine.dispose()

    @staticmethod
    def envelope(status, data=None, diagnostics=None):
        return {"status": status, "data": data, "diagnostics": diagnostics or []}

    def list_runs(self):
        with Session(self._engine) as s:
            rows = s.scalars(select(Run).order_by(Run.created_at, Run.id)).all()
            return self.envelope("observed", [self._run(r) for r in rows])

    def summary(self, run_id):
        run, records, integrity = self._load(run_id)
        return self.envelope("observed", {"run": self._run(run),
            "record_count": len(records), "integrity": self._integrity(integrity)})

    def get_record(self, run_id, sequence):
        _, records, _ = self._load(run_id)
        record = next((r for r in records if r.sequence == sequence and r.kind != "mechanics_reference"), None)
        if record is None:
            raise InspectionError("record_not_found", f"record {sequence} not found")
        return self.envelope("observed", self._record(record))

    def find_records(self, run_id, *, kind=None, sequence_from=None, sequence_to=None):
        _, records, _ = self._load(run_id)
        selected = [r for r in records if r.kind != "mechanics_reference"
                    and (kind is None or r.kind == kind)
                    and (sequence_from is None or r.sequence >= sequence_from)
                    and (sequence_to is None or r.sequence <= sequence_to)]
        return self.envelope("observed", [self._record(r) for r in selected])

    def provenance(self, run_id):
        self._load(run_id)
        with Session(self._engine) as s:
            rows = s.scalars(select(Provenance).where(Provenance.run_id == run_id).order_by(Provenance.key)).all()
            return self.envelope("observed", [{"key": r.key, "value": r.value} for r in rows])

    def validate(self, run_id, *, strict=False):
        run, records, integrity = self._load(run_id)
        bad = [r.sequence for r in records if hashlib.sha256(r.payload).hexdigest() != r.sha256 or r.integrity_status == "invalid"]
        actual = hashlib.sha256("".join(r.sha256 for r in records).encode()).hexdigest()
        aggregate_bad = (not integrity or integrity.record_count != len(records)
                         or integrity.bundle_sha256 != actual or integrity.result == "invalid")
        diagnostics = (["aggregate integrity metadata mismatch"] if aggregate_bad else [])
        result = self.envelope("derived", {"status": "invalid" if bad or aggregate_bad else "valid",
            "record_count": len(records), "bad_sequences": bad}, diagnostics)
        if strict and result["data"]["status"] == "invalid":
            raise InspectionError("integrity_failure", "bundle integrity validation failed")
        return result

    def capabilities(self, run_id=None):
        if run_id is not None:
            self._load(run_id)
        return self.envelope("derived", {"read_only": True, "operations": ["list", "summary", "step", "find", "provenance", "validate", "evidence", "mechanics-reference", "outcome", "transitions", "diff"]})

    def outcome(self, run_id):
        run, _, _ = self._load(run_id)
        return self.envelope("observed" if run.outcome else "missing", run.outcome)

    def evidence(self, run_id, *, kind=None, sequence_from=None, sequence_to=None):
        return self.find_records(run_id, kind=kind, sequence_from=sequence_from, sequence_to=sequence_to)

    def mechanics_reference(self, run_id, *, step_id=None):
        """Read engine mechanics answers through an explicitly separate channel."""
        _, records, _ = self._load(run_id)
        values = []
        for record in records:
            if record.kind != "mechanics_reference":
                continue
            try:
                payload = json.loads(record.payload.decode("utf-8"))
            except (UnicodeDecodeError, json.JSONDecodeError) as error:
                raise InspectionError("invalid_mechanics_reference", "mechanics reference record is not valid JSON") from error
            if step_id is None or payload.get("step_id") == step_id:
                values.append(self._record(record))
        return self.envelope("observed" if values else "missing", values)

    def transitions(self, run_id):
        self._load(run_id)
        return self.envelope("unsupported", None, ["transition schema is not defined"])

    def diff(self, run_id, from_sequence, to_sequence):
        self._load(run_id)
        return self.envelope("unsupported", None, ["state delta schema is not defined"])

    def _load(self, run_id):
        with Session(self._engine) as s:
            run = s.get(Run, run_id)
            if not run:
                raise InspectionError("run_not_found", f"unknown run: {run_id}")
            records = s.scalars(select(Record).where(Record.run_id == run_id).order_by(Record.sequence)).all()
            return run, records, s.get(Integrity, run_id)

    def _run(self, r):
        return {"id": r.id, "status": r.status, "producer_version": r.producer_version, "schema_version": r.schema_version,
                "created_at": r.created_at.isoformat(), "finalized_at": r.finalized_at.isoformat() if r.finalized_at else None,
                "outcome": r.outcome, "integrity_status": r.integrity_status}

    def _record(self, r):
        try:
            payload = json.loads(r.payload.decode("utf-8")); encoding = "json"
        except (UnicodeDecodeError, json.JSONDecodeError):
            payload = base64.b64encode(r.payload).decode("ascii"); encoding = "base64"
        return {"sequence": r.sequence, "kind": r.kind, "payload": payload, "encoding": encoding,
                "sha256": r.sha256, "integrity_status": r.integrity_status}

    def _integrity(self, i):
        return None if i is None else {"record_count": i.record_count, "bundle_sha256": i.bundle_sha256, "result": i.result}
