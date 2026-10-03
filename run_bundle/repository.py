import hashlib, json
from collections import Counter
from datetime import datetime, timezone
from pathlib import Path
from sqlalchemy import create_engine, select
from sqlalchemy.engine import make_url
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
        if "://" not in url:
            if url == ":memory:":
                url = "sqlite:///:memory:"
            else:
                database = Path(url).resolve().as_posix()
                url = f"sqlite:///{database}"
        make_url(url)
        self._engine = create_engine(url, future=True)

    def create(self, run_id, *, producer_version, provenance=None):
        now = datetime.now(timezone.utc).replace(tzinfo=None)
        with Session(self._engine) as s, s.begin():
            if s.get(Run, run_id): raise BundleError("run already exists")
            s.add(Run(id=run_id, status="active", producer_version=producer_version,
                      schema_version=self.schema_version, created_at=now))
            for key, value in (provenance or {}).items(): s.add(Provenance(run_id=run_id, key=key, value=str(value)))

    def import_oracle_directory(self, source_dir):
        """Import one file-IPC oracle run, retaining source file hashes as provenance."""
        source = Path(source_dir)
        session_path, steps_path = source / "session.json", source / "steps.ndjson"
        try:
            session_raw = session_path.read_bytes()
            steps_raw = steps_path.read_bytes()
            metadata = json.loads(session_raw.decode("utf-8"))
            if not isinstance(metadata, dict):
                raise ValueError("session.json must contain an object")
            records = [json.loads(line) for line in steps_raw.splitlines() if line.strip()]
        except (OSError, UnicodeDecodeError, json.JSONDecodeError) as exc:
            raise BundleError(f"invalid oracle run source: {exc}") from exc
        if not isinstance(metadata.get("run_id"), str) or not metadata["run_id"]:
            raise BundleError("oracle session requires run_id")
        if not isinstance(records, list) or any(not isinstance(record, dict) for record in records):
            raise BundleError("oracle steps must be JSON objects")
        declared_steps = metadata.get("n_steps")
        if (not isinstance(declared_steps, int) or isinstance(declared_steps, bool)
                or declared_steps != len(records)):
            raise BundleError("oracle session n_steps does not match steps.ndjson")
        if any(not isinstance(record.get("_recorded_action"), str) or not record["_recorded_action"]
               for record in records):
            raise BundleError("every oracle step requires _recorded_action")
        usage = metadata.get("usage")
        if usage is not None:
            counts = usage.get("action_counts") if isinstance(usage, dict) else None
            unique_count = usage.get("unique_action_count") if isinstance(usage, dict) else None
            actual_counts = Counter(record["_recorded_action"] for record in records)
            if (not isinstance(counts, dict)
                    or any(not isinstance(name, str) or not isinstance(count, int)
                           or isinstance(count, bool) or count < 0 for name, count in counts.items())
                    or counts != dict(actual_counts)
                    or sum(counts.values()) != len(records)
                    or ("unique_action_count" in usage
                        and (not isinstance(unique_count, int) or isinstance(unique_count, bool)
                             or unique_count != len(actual_counts)))):
                raise BundleError("oracle usage action_counts must be non-negative and sum to n_steps")
        outcome = metadata.get("outcome")
        target_status = {"win": "won", "loss": "lost"}.get(outcome)
        if outcome is not None and target_status is None:
            raise BundleError(f"unsupported oracle outcome: {outcome}")
        try:
            created_at = datetime.fromisoformat(metadata["started_at"])
            if created_at.tzinfo is not None:
                created_at = created_at.astimezone(timezone.utc).replace(tzinfo=None)
        except (KeyError, TypeError, ValueError) as exc:
            raise BundleError("oracle session requires a valid started_at timestamp") from exc
        finalized_at = None
        if target_status is not None:
            try:
                finalized_at = datetime.fromisoformat(metadata["ended_at"])
                if finalized_at.tzinfo is not None:
                    finalized_at = finalized_at.astimezone(timezone.utc).replace(tzinfo=None)
            except (KeyError, TypeError, ValueError) as exc:
                raise BundleError("finalized oracle session requires a valid ended_at timestamp") from exc
        producer_version = str(metadata.get("schema_version", "unknown"))
        provenance = {
            "oracle.source_directory": str(source.resolve()),
            "oracle.source_session_sha256": hashlib.sha256(session_raw).hexdigest(),
            "oracle.source_steps_sha256": hashlib.sha256(steps_raw).hexdigest(),
            "oracle.outcome": "unknown" if outcome is None else outcome,
        }
        if "usage" in metadata:
            provenance["oracle.usage"] = json.dumps(metadata["usage"], sort_keys=True, separators=(",", ":"))
        if "recording" in metadata:
            provenance["oracle.recording"] = json.dumps(metadata["recording"], sort_keys=True, separators=(",", ":"))
        run_id = metadata["run_id"]
        with Session(self._engine) as s, s.begin():
            if s.get(Run, run_id):
                raise BundleError("run already exists")
            run = Run(id=run_id, status=target_status or "active", producer_version=producer_version,
                      schema_version=self.schema_version, created_at=created_at,
                      finalized_at=finalized_at, outcome=target_status, integrity_status="valid")
            s.add(run)
            s.flush()
            for key, value in provenance.items():
                s.add(Provenance(run_id=run_id, key=key, value=value))
            for sequence, record in enumerate(records):
                encoded = json.dumps(record, sort_keys=True, separators=(",", ":"),
                                     ensure_ascii=False).encode("utf-8")
                digest = hashlib.sha256(encoded).hexdigest()
                s.add(Record(run_id=run_id, sequence=sequence, kind="step", payload=encoded,
                             sha256=digest, integrity_status="valid"))
            digest = hashlib.sha256("".join(
                hashlib.sha256(json.dumps(record, sort_keys=True, separators=(",", ":"),
                                        ensure_ascii=False).encode("utf-8")).hexdigest()
                for record in records).encode()).hexdigest()
            s.add(Integrity(run_id=run_id, record_count=len(records), bundle_sha256=digest,
                            result="valid"))
        return {"run_id": run_id, "record_count": len(records), "status": target_status or "active"}

    def add_provenance(self, run_id, values):
        """Add audit metadata without changing evidence or its integrity hash."""
        with Session(self._engine) as s, s.begin():
            if not s.get(Run, run_id):
                raise BundleError("unknown run")
            for key, value in values.items():
                existing = s.scalars(select(Provenance).where(Provenance.run_id == run_id,
                                                              Provenance.key == key)).all()
                text = str(value)
                if any(row.value != text for row in existing):
                    raise BundleError(f"conflicting provenance: {key}")
                if existing:
                    continue
                s.add(Provenance(run_id=run_id, key=key, value=text))

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
            expected_results = {"invalid"} if bad or bad_status else {"unknown", "valid"}
            aggregate_bad = (not aggregate or aggregate.record_count != len(records)
                             or aggregate.bundle_sha256 != aggregate_digest
                             or aggregate.result not in expected_results)
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
