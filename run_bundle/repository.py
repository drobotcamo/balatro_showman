import hashlib, json
from collections import Counter
from datetime import datetime, timezone
from pathlib import Path
from sqlalchemy import create_engine, select
from sqlalchemy.engine import make_url
from sqlalchemy.orm import Session
from .models import Base, Run, Record, Provenance, Integrity

STATUSES = {"active", "interrupted", "incomplete", "completed", "won", "lost", "aborted", "endless"}
FINAL = STATUSES - {"active", "interrupted"}
ALLOWED = {"active": STATUSES - {"active"}, "interrupted": STATUSES - {"active", "interrupted"}}

class BundleError(Exception): pass
class ImportConflict(BundleError): pass
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

    def close(self):
        self._engine.dispose()

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
        actual_counts = Counter(record["_recorded_action"] for record in records)
        if usage is not None:
            counts = usage.get("action_counts") if isinstance(usage, dict) else None
            unique_count = usage.get("unique_action_count") if isinstance(usage, dict) else None
            if (not isinstance(counts, dict)
                    or any(not isinstance(name, str) or not isinstance(count, int)
                           or isinstance(count, bool) or count < 0 for name, count in counts.items())
                    or counts != dict(actual_counts)
                    or sum(counts.values()) != len(records)
                    or ("unique_action_count" in usage
                        and (not isinstance(unique_count, int) or isinstance(unique_count, bool)
                             or unique_count != len(actual_counts)))):
                raise BundleError("oracle usage action_counts must be non-negative and sum to n_steps")
            first_recorded_at = usage.get("first_recorded_at")
            last_recorded_at = usage.get("last_recorded_at")
            if (first_recorded_at is None) != (last_recorded_at is None):
                raise BundleError("oracle usage first/last timestamps must both be present or both be null")
            try:
                if first_recorded_at is not None:
                    for value in (first_recorded_at, last_recorded_at):
                        parsed = datetime.fromisoformat(value) if isinstance(value, str) else None
                        if parsed is None or parsed.utcoffset() != timezone.utc.utcoffset(parsed):
                            raise ValueError("timestamp must be ISO-8601 UTC")
            except ValueError as exc:
                raise BundleError("oracle usage timestamps must be valid ISO-8601 UTC values") from exc
            step_times = [record.get("_recorded_at") for record in records]
            for value in step_times:
                if value is None:
                    continue
                try:
                    parsed = datetime.fromisoformat(value) if isinstance(value, str) else None
                except ValueError:
                    parsed = None
                if parsed is None or parsed.utcoffset() != timezone.utc.utcoffset(parsed):
                    raise BundleError("oracle step timestamps must be valid ISO-8601 UTC values")
            if step_times:
                if (step_times[0] is not None and first_recorded_at != step_times[0]
                        or step_times[-1] is not None and last_recorded_at != step_times[-1]):
                    raise BundleError("oracle usage timestamps do not match available boundary steps")
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
        lifecycle_status = metadata.get("lifecycle_status")
        if lifecycle_status is None:
            lifecycle_status = target_status or "active"
        if lifecycle_status not in STATUSES:
            raise BundleError(f"unsupported oracle lifecycle status: {lifecycle_status}")
        if target_status is not None and lifecycle_status != target_status:
            raise BundleError("oracle outcome conflicts with lifecycle_status")
        finalized_at = None
        if lifecycle_status in FINAL:
            try:
                finalized_at = datetime.fromisoformat(metadata["ended_at"])
                if finalized_at.tzinfo is not None:
                    finalized_at = finalized_at.astimezone(timezone.utc).replace(tzinfo=None)
            except (KeyError, TypeError, ValueError) as exc:
                raise BundleError("finalized oracle session requires a valid ended_at timestamp") from exc
        producer_version = str(metadata.get("schema_version", "unknown"))
        source_identity = json.dumps({
            "session_sha256": hashlib.sha256(session_raw).hexdigest(),
            "steps_sha256": hashlib.sha256(steps_raw).hexdigest(),
        }, sort_keys=True, separators=(",", ":"))
        provenance = {
            "oracle.source_directory": str(source.resolve()),
            "oracle.source_session_sha256": hashlib.sha256(session_raw).hexdigest(),
            "oracle.source_steps_sha256": hashlib.sha256(steps_raw).hexdigest(),
            "oracle.outcome": "unknown" if outcome is None else outcome,
        }
        if usage is None:
            step_times = [record.get("_recorded_at") for record in records]
            if step_times and all(isinstance(value, str) for value in step_times):
                try:
                    for value in step_times:
                        datetime.fromisoformat(value)
                except ValueError:
                    first_recorded_at = last_recorded_at = None
                else:
                    first_recorded_at, last_recorded_at = step_times[0], step_times[-1]
            else:
                first_recorded_at = last_recorded_at = None
            usage = {
                "action_counts": dict(actual_counts),
                "unique_action_count": len(actual_counts),
                "first_recorded_at": first_recorded_at,
                "last_recorded_at": last_recorded_at,
            }
        provenance["oracle.usage"] = json.dumps(usage, sort_keys=True, separators=(",", ":"))
        if "recording" in metadata:
            provenance["oracle.recording"] = json.dumps(metadata["recording"], sort_keys=True, separators=(",", ":"))
        mechanics_reference_path = source / "mechanics_reference.ndjson"
        mechanics_reference_raw = mechanics_reference_path.read_bytes() if mechanics_reference_path.exists() else None
        if mechanics_reference_raw is not None:
            identity_fields = json.loads(source_identity)
            identity_fields["mechanics_reference_sha256"] = hashlib.sha256(mechanics_reference_raw).hexdigest()
            source_identity = json.dumps(identity_fields, sort_keys=True, separators=(",", ":"))
            provenance["oracle.mechanics_reference_sha256"] = identity_fields["mechanics_reference_sha256"]
        provenance.update({"source.type": "file-ipc-oracle", "source.identity": source_identity})
        envelope = {
            "run_id": metadata["run_id"],
            "source_type": "file-ipc-oracle",
            "source_identity": source_identity,
            "producer_version": producer_version,
            "status": lifecycle_status,
            "outcome": target_status,
            "created_at": created_at,
            "finalized_at": finalized_at,
            "provenance": provenance,
        }
        bundle_records = [{"kind": "step", "payload": record} for record in records]
        if mechanics_reference_raw is not None:
            from ground_truth.file_ipc_bridge import (
                MECHANICS_REFERENCE_VERSION,
                MECHANICS_REFERENCE_VERSION_V2,
                _validate_mechanics_reference,
            )

            valid_step_ids = {record.get("step_id", f"{metadata['run_id']}:{record['request_id']}")
                              for record in records}
            reference_keys = set()
            try:
                mechanics_lines = mechanics_reference_raw.decode("utf-8").splitlines()
            except UnicodeDecodeError as exc:
                raise BundleError("mechanics reference file must be UTF-8") from exc
            for line_number, line in enumerate(mechanics_lines, start=1):
                try:
                    reference = json.loads(line)
                except json.JSONDecodeError as exc:
                    raise BundleError(f"invalid mechanics reference JSON on line {line_number}") from exc
                if (not isinstance(reference, dict)
                        or reference.get("schema_version") not in {
                            MECHANICS_REFERENCE_VERSION, MECHANICS_REFERENCE_VERSION_V2
                        }
                        or reference.get("run_id") != metadata["run_id"]
                        or not isinstance(reference.get("step_id"), str)
                        or reference["step_id"] not in valid_step_ids):
                    raise BundleError(f"invalid mechanics reference envelope on line {line_number}")
                key = reference["step_id"], reference.get("capture_phase")
                if key in reference_keys:
                    raise BundleError(f"duplicate mechanics reference phase on line {line_number}")
                reference_keys.add(key)
                try:
                    _validate_mechanics_reference({"mechanics_reference": reference})
                except ValueError as exc:
                    raise BundleError(f"invalid mechanics reference on line {line_number}: {exc}") from exc
                bundle_records.append({"kind": "mechanics_reference", "payload": reference})
        return self.ingest_run(envelope, bundle_records)

    def ingest_run(self, envelope, records):
        """Persist a source-neutral run envelope and ordered typed records atomically."""
        required = ("run_id", "source_type", "source_identity", "producer_version", "status")
        if not isinstance(envelope, dict) or any(not envelope.get(key) for key in required):
            raise BundleError("run envelope requires run_id, source_type, source_identity, producer_version, and status")
        if any(not isinstance(envelope[key], str) for key in required[:4]):
            raise BundleError("run_id, source_type, source_identity, and producer_version must be strings")
        status = envelope["status"]
        if not isinstance(status, str) or status not in STATUSES:
            raise BundleError(f"unsupported run status: {status}")
        outcome = envelope.get("outcome")
        valid_outcomes = (STATUSES - {"active", "interrupted", "incomplete"}) | {"unknown"}
        if outcome is not None and (not isinstance(outcome, str) or outcome not in valid_outcomes):
            raise BundleError(f"unsupported run outcome: {outcome}")
        if status == "incomplete" and outcome is not None:
            raise BundleError("incomplete runs must not declare an outcome")
        if status in FINAL - {"incomplete"} and outcome != status:
            raise BundleError(f"terminal lifecycle status {status!r} requires the matching outcome")
        if status in {"active", "interrupted"} and outcome not in (None, "unknown"):
            raise BundleError(f"run outcome {outcome!r} conflicts with lifecycle status {status!r}")
        if not isinstance(records, (list, tuple)):
            raise BundleError("records must be an ordered list")
        provenance = envelope.get("provenance", {})
        if not isinstance(provenance, dict):
            raise BundleError("provenance must be an object")
        if (provenance.get("source.type") != envelope["source_type"]
                or provenance.get("source.identity") != envelope["source_identity"]):
            raise BundleError("provenance source type and identity must match the run envelope")
        normalized_records = []
        for record in records:
            if not isinstance(record, dict) or not isinstance(record.get("kind"), str) or not record["kind"] or "payload" not in record:
                raise BundleError("each record requires a non-empty kind and payload")
            try:
                encoded = json.dumps(record["payload"], sort_keys=True, separators=(",", ":"), ensure_ascii=False).encode("utf-8")
            except (TypeError, ValueError) as exc:
                raise BundleError("record payload must be JSON-serializable") from exc
            normalized_records.append((record["kind"], encoded))
        run_id = envelope["run_id"]
        with Session(self._engine) as s, s.begin():
            existing = s.get(Run, run_id)
            if existing:
                existing_provenance = {
                    row.key: row.value for row in s.scalars(select(Provenance).where(Provenance.run_id == run_id)).all()
                }
                if (existing_provenance.get("source.type") == envelope["source_type"]
                        and existing_provenance.get("source.identity") == envelope["source_identity"]):
                    return {"run_id": run_id, "record_count": len(normalized_records),
                            "status": existing.status, "already_imported": True}
                raise ImportConflict(f"run ID {run_id!r} exists with different source identity")
            created_at = envelope.get("created_at") or datetime.now(timezone.utc).replace(tzinfo=None)
            finalized_at = envelope.get("finalized_at")
            run = Run(id=run_id, status=status, producer_version=str(envelope["producer_version"]),
                      schema_version=self.schema_version, created_at=created_at,
                      finalized_at=finalized_at, outcome=outcome, integrity_status="valid")
            s.add(run)
            s.flush()
            for key, value in provenance.items():
                s.add(Provenance(run_id=run_id, key=str(key), value=str(value)))
            hashes = []
            for sequence, (kind, encoded) in enumerate(normalized_records):
                digest = hashlib.sha256(encoded).hexdigest()
                hashes.append(digest)
                s.add(Record(run_id=run_id, sequence=sequence, kind=kind, payload=encoded,
                             sha256=digest, integrity_status="valid"))
            digest = hashlib.sha256("".join(hashes).encode()).hexdigest()
            s.add(Integrity(run_id=run_id, record_count=len(normalized_records), bundle_sha256=digest, result="valid"))
        return {"run_id": run_id, "record_count": len(normalized_records), "status": status}

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
