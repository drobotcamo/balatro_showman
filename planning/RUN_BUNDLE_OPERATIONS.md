# Run-Bundle Operations

This guide is the human and agent entrypoint for the Issue #34 run-bundle
boundary. It describes the current Python module entrypoint and the terminal
interaction required before associating recording evidence.

## Entrypoint

Use the package module rather than a second standalone launcher:

```text
python -m run_bundle <command> --db <bundle.sqlite> ...
```

`run_bundle/__main__.py` emits JSON envelopes and uses the read-only
`RunBundleInspector`. Inspection commands include `list`, `summary`, `step`,
`find`, `provenance`, `evidence`, `validate`, `outcome`, `transitions`, and
`diff`. `validate --strict` requests strict diagnostics; inspection never
repairs evidence or changes lifecycle state.

Database setup is separate and mutating:

```text
alembic upgrade head
```

Run it only when creating or upgrading a bundle under the storage procedure in
`planning/RUN_BUNDLE_STORAGE.md`. Do not run migrations as part of inspection.

## Automatic File-IPC Intake

After migrating the destination once, configure the recorder with the existing
file source and bundle. The bridge never runs migrations:

```text
python -m ground_truth.file_ipc_bridge --out-dir <oracle-runs> --bundle-db <bundle.sqlite>
```

The bridge imports automatically only after it has durably stored the terminal
session and accepted every request through the producer watermark. It does not
prompt for per-run review or confirmation. A human-reviewed live smoke run is a
one-time acceptance check for this integration, not a runtime step.

The file-source adapter requires `session.json` and `steps.ndjson`, verifies the
declared step count and recorded action on every step. A repeat import with the same run
ID and source-file hashes is a no-op success; a different source under that run
ID is reported as a conflict. If session usage metadata is present, its action
counts must match the steps. For
legacy sessions without usage metadata, the importer derives action counts from
the step records and leaves summary timestamps null when step timestamps are
not consistently available. Present usage timestamps must be valid UTC ISO-8601
values and must match the first/last step timestamp when that boundary is
available. Invalid step timestamps alongside usage metadata are rejected;
legacy records without session usage keep the original step payload and receive
null summary timestamps if timestamp coverage is missing or malformed.
It maps `win`/`loss` to `won`/`lost`, preserves usage and recording metadata, and
stores source type, source identity and SHA-256 hashes of both source files as
provenance. Evidence records are canonicalized JSON objects. Import is one
database transaction, and it never deletes or rewrites source run files. If the
database is unavailable or import validation fails, the bridge reports a pending
import and retries while running or after restart. Re-running the manual
`import-oracle` command is also safe. The destination database must already be
migrated; the import command does not create or upgrade its schema.

If the bridge is stopped cleanly with Ctrl+C while a run has no producer
terminal signal, it stores lifecycle status `incomplete`, keeps outcome unknown,
and imports that run. This is distinct from a process crash: on restart, an
active durable session is recovered and remains eligible to resume. A run with
an incomplete producer watermark is not finalized or imported as a completed
win/loss; the bridge waits for the missing requests. Source files and queued
requests remain available for recovery.

## Source-Neutral Intake

Source adapters call `RunBundle.ingest_run(envelope, records)`. The envelope
contains run ID, source type and identity, producer version, status, outcome,
timestamps and provenance; each ordered record has a `kind` and source-specific
JSON payload. For example, a future video adapter can submit frame references,
confidence or explicit unknown values with video hash and processing revision
provenance. No video reconstruction is implemented by this boundary.

Run summaries and imported records remain available through the normal
inspection API/CLI:

```text
python -m run_bundle summary --db <bundle.sqlite> --run <run-id>
python -m run_bundle find --db <bundle.sqlite> --run <run-id> --kind step
python -m run_bundle provenance --db <bundle.sqlite> --run <run-id>
python -m run_bundle validate --db <bundle.sqlite> --run <run-id> --strict
```

## Recording-Association Checkpoint (Separate from Run Intake)

This existing checkpoint controls only whether a validated recording marker is
associated with a run. It is not a per-run RunBundle import or verification
step. Run intake above remains automatic.

Recording association is the one user-facing pause in this bounded workflow.
Before calling the association operation, present a concise terminal summary:

- run ID and current lifecycle status;
- whether a producer marker was found, and its validation summary;
- whether recording is required or optional;
- the proposed list of present items or evidence relevant to the operation;
- the choices `confirm`, `decline`, or `interrupt`.

The user may correct the proposed present-item list before choosing an outcome.
Those corrections are input to the current operation and must not be silently
represented as new evidence, a new lifecycle state, or a changed evidence
hash. If the corrected list changes what the operation can safely claim, stop
and report the discrepancy instead of inferring a value.

The terminal flow must wait for an explicit response. A default or blank
response is not confirmation. EOF, keyboard interruption, or another prompt
failure is `interrupt` and must become the existing machine-readable
`interrupted` result. For required recording, any non-confirmed result is
returned as `blocked` with code `recording_required`.

The checkpoint ends before additive provenance mutation. It does not start,
stop, inspect, or control OBS. Low-level recording hooks and video alignment
remain owned by Issues #15 and #35.

## Outcome Handling

- `confirm`: associate the validated marker through the existing additive
  provenance path.
- `decline`: do not associate the marker; preserve an explicit declined result.
- `interrupt`: do not associate the marker; preserve an explicit interrupted
  result.
- `blocked` / `recording_required`: required coordination did not produce a
  confirmed association.

No `paused` lifecycle status is added. A process-level pause is not a
resumable database state. If the process exits, the next run must inspect the
bundle and repeat the checkpoint rather than assume that prior intent was
confirmed.

## Agent Procedure

1. Read the Issue, run-bundle contracts and applicable unfinished-work checkpoint.
2. Inspect with `python -m run_bundle ...`; preserve the JSON envelope and
   diagnostics in any report.
3. Build the terminal summary from observed data and label unknown or missing
   values explicitly.
4. Pause for the user to correct present items and choose an outcome.
5. Associate only after explicit `confirm` and successful marker validation.
6. Run the narrowest relevant tests plus `python planning/check_contracts.py`
   and `git diff --check`.
7. Ask the user before changing lifecycle, schema, hash, provenance, OBS, or
   CLI contracts.

## Boundaries

The bundle lifecycle remains `active`, `interrupted`, `completed`, `endless`,
`won`, `lost`, or `aborted`. Evidence remains append-only at the application
boundary and terminal outcomes remain immutable. Compatibility adapters remain
read-only. This guide does not define Phase 9 export storage or deterministic
replay.
