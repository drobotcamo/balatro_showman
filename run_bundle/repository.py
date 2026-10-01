import hashlib, json
from datetime import datetime, timezone
from sqlalchemy import create_engine, select
from sqlalchemy.orm import Session
from .models import Base, Run, Record, Provenance, Integrity

STATUSES = {"active", "interrupted", "completed", "won", "lost", "aborted", "endless"}
FINAL = STATUSES - {"active", "interrupted"}
ALLOWED = {"active": STATUSES - {"active"}, "interrupted": {"active", "completed", "won", "lost", "aborted", "endless"}}

class BundleError(Exception): pass
class InvalidTransition(BundleError): pass
class FinalizedEvidenceError(BundleError): pass

class RunBundle:
    """Public repository API; callers never receive ORM sessions."""
    schema_version = "1.0"
    def __init__(self, url: str):
        self._engine = create_engine(url, future=True)

    def create(self, run_id, *, producer_version, provenance=None):
        now = datetime.now(timezone.utc).replace(tzinfo=None)
        with Session(self._engine) as s, s.begin():
            if s.get(Run, run_id): raise BundleError("run already exists")
            s.add(Run(id=run_id, status="active", producer_version=producer_version,
                      schema_version=self.schema_version, created_at=now))
            for key, value in (provenance or {}).items(): s.add(Provenance(run_id=run_id, key=key, value=str(value)))

    def append(self, run_id, sequence, kind, payload):
        try: encoded = json.dumps(payload, sort_keys=True, separators=(",", ":"), ensure_ascii=False).encode("utf-8")
        except (TypeError, ValueError) as exc:
            raise BundleError("payload is not JSON-serializable; preserve raw input via append_raw") from exc
        digest = hashlib.sha256(encoded).hexdigest()
        with Session(self._engine) as s, s.begin():
            run = s.get(Run, run_id)
            if not run: raise BundleError("unknown run")
            if run.status in FINAL: raise FinalizedEvidenceError("finalized evidence is immutable")
            if s.scalar(select(Record).where(Record.run_id == run_id, Record.sequence == sequence)): raise BundleError("duplicate record")
            s.add(Record(run_id=run_id, sequence=sequence, kind=kind, payload=encoded, sha256=digest))
            prior_invalid = s.scalar(select(Record).where(Record.run_id == run_id, Record.integrity_status == "invalid"))
            run.integrity_status = "invalid" if prior_invalid else "unknown"
            self._integrity(s, run_id, run.integrity_status)

    def append_raw(self, run_id, sequence, kind, raw_payload: bytes, *, integrity_status="invalid"):
        """Preserve malformed/partial source bytes without repairing them."""
        digest = hashlib.sha256(raw_payload).hexdigest()
        with Session(self._engine) as s, s.begin():
            run = s.get(Run, run_id)
            if not run: raise BundleError("unknown run")
            if run.status in FINAL: raise FinalizedEvidenceError("finalized evidence is immutable")
            if s.scalar(select(Record).where(Record.run_id == run_id, Record.sequence == sequence)): raise BundleError("duplicate record")
            s.add(Record(run_id=run_id, sequence=sequence, kind=kind, payload=raw_payload, sha256=digest, integrity_status=integrity_status))
            run.integrity_status = "invalid" if integrity_status == "invalid" else "unknown"
            self._integrity(s, run_id, run.integrity_status)

    def transition(self, run_id, status):
        if status not in STATUSES: raise InvalidTransition(status)
        should_raise = False
        with Session(self._engine) as s, s.begin():
            run = s.get(Run, run_id)
            if not run or status not in ALLOWED.get(run.status, set()): raise InvalidTransition(f"{run and run.status}->{status}")
            run.status = status
            if status in FINAL: run.outcome, run.finalized_at = status, datetime.now(timezone.utc).replace(tzinfo=None)
            result = "invalid" if s.scalar(select(Record).where(Record.run_id == run_id, Record.integrity_status == "invalid")) else "valid"
            run.integrity_status = result
            self._integrity(s, run_id, result)

    def validate(self, run_id, *, strict=False):
        with Session(self._engine) as s, s.begin():
            run = s.get(Run, run_id)
            if not run: raise BundleError("unknown run")
            records = s.scalars(select(Record).where(Record.run_id == run_id).order_by(Record.sequence)).all()
            bad = [r.sequence for r in records if hashlib.sha256(r.payload if isinstance(r.payload, bytes) else r.payload.encode()).hexdigest() != r.sha256]
            bad_status = [r.sequence for r in records if r.integrity_status == "invalid"]
            aggregate = s.get(Integrity, run_id)
            aggregate_digest = hashlib.sha256("".join(r.sha256 for r in records).encode()).hexdigest()
            expected_result = "invalid" if bad or bad_status else "valid"
            aggregate_bad = (not aggregate or aggregate.record_count != len(records)
                             or aggregate.bundle_sha256 != aggregate_digest
                             or aggregate.result != expected_result)
            result = "invalid" if bad or bad_status or aggregate_bad else "valid"
            run.integrity_status = result
            self._integrity(s, run_id, result)
            should_raise = strict and bool(bad or bad_status or aggregate_bad)
            report = {"status": result, "record_count": len(records), "bad_sequences": sorted(set(bad + bad_status))}
        if should_raise: raise BundleError(f"integrity failure: {report['bad_sequences']}")
        return report

    def _integrity(self, s, run_id, result):
        rows = s.scalars(select(Record).where(Record.run_id == run_id).order_by(Record.sequence)).all()
        digest = hashlib.sha256("".join(r.sha256 for r in rows).encode()).hexdigest()
        s.merge(Integrity(run_id=run_id, record_count=len(rows), bundle_sha256=digest, result=result))
