# Showman Capture interfaces

The product entrypoint is `python -m showman`, from the repository root.
`--help` works at each command level. Python APIs remain in their original
packages; the product CLI delegates to them rather than defining another store
or schema. There is no HTTP service.

## CLI reference

| Command | Arguments | Effect and output |
| --- | --- | --- |
| `demo` | `--output-dir NEW_DIR` | Writes labeled synthetic queue/capture/SQLite files under a new directory; returns a JSON result with summary, validation, and next command. Parent must exist. |
| `store init` | `--db NEW_SQLITE_FILE` | Runs Alembic for a new database only; JSON result. Parent must exist. |
| `store import` | `--db DB --source CAPTURE_DIR` | Mutates the existing migrated bundle in one import transaction; source files unchanged; JSON envelope. |
| `record` | `--out-dir ROOT`, optional `--io-dir IO`, `--bundle-db DB`, `--action LABEL`, `--timeout SECONDS`, `--once` | Writable queue consumption/recovery, capture files, optional automatic terminal-run import; human-readable recorder logs. IO defaults to the platform's Balatro `agent_io` directory. `--action` is a smoke-test fallback only. |
| `capture summary` | `CAPTURE_DIR` | Read-only compatibility result wrapped in JSON; returns source objects/hashes, classification, video status, and diagnostics. |
| `capture audit` | `CAPTURE_DIR` | Read-only finalized-run audit; JSON summaries plus text findings/failures and final verdict. |
| `associate` | `--db DB --run ID --marker JSON --confirmed-by HUMAN`, optional `--video FILE`, `--required` | Observed summary and explicit terminal input on stderr/stdin; JSON result on stdout. Confirmed association adds provenance; existing evidence/outcome untouched. A supplied video must be a present file. |
| `align` | `STEPS_NDJSON`, optional `--recording-start-ns NS`, `--fps FPS` | Read-only candidate mapping from sibling `session.json` marker; one JSON object per step (`step_id`, `frame_idx`). Overrides are diagnostic inputs, not confirmed provenance. |
| `annotations export` | `INPUT_JSON OUTPUT_JSON` | Deterministic development manifest; JSON result with output hash/path and `development_only_unscored`. Existing identical output accepted, differing output refused. |

All inspection commands accept `--db DB`; all except `list` require `--run ID`,
with `capabilities` allowing an optional run. DB may be a SQLite filename or a
SQLAlchemy URL supported by the underlying API. `store init` takes a filename.

| `inspect` operation | Additional arguments | Result |
| --- | --- | --- |
| `list` | none | Runs ordered by creation time and ID. |
| `capabilities` | optional `--run ID` | Declares the read-only API operations; listing an operation does not prove its data schema is implemented. |
| `summary` | none | Run lifecycle/outcome/version/timestamps, record count, stored integrity metadata. |
| `step` | `--sequence N` | One record including kind, payload/encoding, hash, and integrity status. N is zero-based store sequence. |
| `find`, `evidence` | optional `--kind KIND --from N --to N` | Matching records in sequence order; inclusive bounds. `evidence` uses the same filters. |
| `provenance` | none | Ordered key/value records. Imported JSON metadata values are stored as strings. |
| `validate` | optional `--strict` | Recomputes payload and aggregate hash/count checks without writing. Strict invalidity is a query failure. |
| `outcome` | none | Stored outcome, or `missing` with null data. |
| `transitions` | none | `unsupported`; transition schema is undefined. |
| `diff` | `--from-sequence N --to-sequence N` | `unsupported`; state-delta schema is undefined. |

Inspection is an application-level read-only API. It does not promise a
filesystem/database permission sandbox. A summary displays stored integrity;
use `validate` when you need a fresh hash check.

### Results and exits

Store/inspection/product results use:

```json
{"status":"observed","data":{},"diagnostics":[]}
```

`observed` is retained data; `derived` is computed from evidence; `missing`
means absent requested information; `unknown` reports an unresolved/error
result; `unsupported` means no declared implementation. Diagnostics can include
objects or strings according to the delegated API. Do not assume one diagnostic
shape across all operations.

- Exit 0: request handled. Still examine status, diagnostics, and inner data.
  `unsupported`, a missing outcome, or optional association `declined` can exit 0.
  Non-strict validation also exits 0 when its inner integrity status is invalid.
- Exit 2: argument/query/operation failure or unsuccessful required association.
  Parser errors use argparse text on stderr, not a JSON envelope.
- `capture audit` uses exit 1 for integrity failures and exit 0 for integrity
  success even with conformance findings.
- `record` returns after its polling mode ends; pending imports appear in logs.
  Its exit 0 does not establish that every capture was imported. Read the store.

Demo recorder logs and association summaries/prompts go to stderr. Normal demo,
store, inspection, association, and annotation success results are JSON on stdout.
`record` and `capture audit` retain their existing mixed/log output formats;
`align` is NDJSON. The CLI is task-unified, not one interchangeable result schema.

## Python API reference

### Run Store: `from run_bundle import RunBundle`

Initialize/upgrade the database with Alembic before using the writer. The API
accepts a SQLite filename or SQLAlchemy URL and owns its sessions/transactions.
Call `close()` after use.

| Method | Meaning |
| --- | --- |
| `create(run_id, *, producer_version, provenance=None)` | Create an active run; duplicate ID rejected. |
| `import_oracle_directory(source_dir)` | Validate/import capture files, retaining canonical record JSON and original file hashes. Identical source identity is idempotent; differing identity raises `ImportConflict`. Active snapshots are not refreshed by later imports under the same ID. |
| `ingest_run(envelope, records)` | Source-neutral intake. Envelope requires `run_id`, `source_type`, `source_identity`, `producer_version`, `status`; supports outcome/timestamps/provenance. Provenance must include matching `source.type` and `source.identity`. Ordered records require `kind` and JSON `payload`; store sequences are assigned from zero. |
| `append(run_id, sequence, kind, payload)` | Append canonical JSON evidence; duplicate sequence and finalized runs rejected. |
| `append_raw(run_id, sequence, kind, raw_payload, *, integrity_status="invalid")` | Retain malformed/partial bytes without repairing them. |
| `add_provenance(run_id, values)` | Add metadata without changing evidence hash. Identical key/value is a no-op; conflicting values rejected. Available even after finalization. |
| `transition(run_id, status)` | Apply the declared lifecycle graph; terminal runs do not resume or accept evidence. |
| `validate(run_id, *, strict=False)` | Writer-side validation: updates stored integrity metadata; strict failure raises `BundleError`. Different from Inspector validation. |
| `close()` | Dispose the database engine. |

Errors exported by `run_bundle` include `BundleError`, `ImportConflict`,
`InvalidTransition`, and `FinalizedEvidenceError`.

### Inspector: `from run_bundle import RunBundleInspector`

Methods return the inspection envelope; `InspectionError` has `code` and
`message`. A missing SQLite filename is rejected without creating the file.

```python
from run_bundle import RunBundleInspector

inspector = RunBundleInspector("C:/external/bundle.sqlite")
try:
    summary = inspector.summary("run-id")
    check = inspector.validate("run-id", strict=True)
    first = inspector.get_record("run-id", 0)
finally:
    inspector.close()
```

Other methods: `list_runs()`, `find_records(run_id, *, kind=None,
sequence_from=None, sequence_to=None)`, `evidence(...)` with the same filters,
`provenance(run_id)`, `capabilities(run_id=None)`, `outcome(run_id)`,
`transitions(run_id)`, `diff(run_id, from_sequence, to_sequence)`. Unsupported
operations still check that the run exists. Non-JSON stored bytes are returned
as base64 with `encoding="base64"`; do not interpret them as repaired JSON.

### Capture reader and Recorder

- `run_bundle.read_oracle_run(path)` is read-only and returns classification
  (`healthy`, `partial`, `malformed`), original session/steps, hashes, video status,
  and diagnostics. It neither migrates nor imports a bundle.
- `ground_truth.file_ipc_bridge.FileIpcBridge(io_dir, out_dir, action=None,
  bundle_db=None)` reconstructs durable consumer state on construction. This is
  a **writer**, not an inspection API: recovery may reconcile counts and
  quarantine corrupt tails. `step_once()` processes available marker/queue/end
  inputs and retries terminal imports; `serve(timeout=None)` polls;
  `open_sessions()` reports unfinalized sessions.

### Recording and evaluation helpers

- `ground_truth.obs_recording_start` is loaded by OBS, not executed as a
  product CLI command. Its recording-start callback writes the game-clock
  handshake request. `write_request(directory, recording_id, recording_fps)`
  supports the same request for diagnostics.
- `ground_truth.recording_association.associate_recording(bundle, run_id, *,
  confirmed, marker, observed_at_ns=None, max_age_ns=None, video_ref=None,
  confirmed_by="human", interrupted=False)` validates/associates provenance.
  Freshness checks require observation time in the same producer clock domain.
  `AssociationResult.as_dict()` exposes status/code/diagnostic/recording/video
  status. `associate_after_confirmation` and `coordinate_recording` connect
  callback-based confirmation flows. The CLI implements the full terminal
  summary/correction checkpoint and offers no unattended confirmation option.
- `planning.align_oracle_video.frame_index(step_timestamp_ns,
  recording_start_ns, fps)` computes the rounded candidate frame number. It
  does not inspect video.
- `ground_truth.eval_manifest.validate(data)`, `build(data)`, and
  `export(input_path, output_path)` validate the development annotation contract,
  build deterministic output/counts, and return the output SHA-256 on export.
  `AnnotationError` is a `ValueError`. Source hash declarations are not a check
  of actual media bytes. See the annotation specification before authoring input.

## Existing entrypoints

| Showman surface | Existing implementation |
| --- | --- |
| `record` | `python -m ground_truth.file_ipc_bridge` |
| `store init` | Alembic migration API using the checked-in configuration |
| `store import` | `python -m run_bundle import-oracle` |
| `inspect OP` | `python -m run_bundle OP` |
| `capture summary` | `run_bundle.read_oracle_run` |
| `capture audit` | `python planning/audit_oracle_runs.py` |
| `associate` | `ground_truth.recording_association` plus the documented terminal checkpoint |
| `align` | `python planning/align_oracle_video.py` |
| `annotations export` | `python -m ground_truth.eval_manifest` (legacy CLI prints only the hash) |

The original entrypoints remain usable. New product commands do not change
schema versions, source identity, lifecycle meanings, or oracle/video separation.
