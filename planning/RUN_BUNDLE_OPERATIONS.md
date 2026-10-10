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

## Importing File-IPC Oracle Runs

After database setup, import one finalized or active oracle directory without
modifying its source files:

```text
python -m run_bundle import-oracle --db <bundle.sqlite> --source <run-directory>
python -m run_bundle summary --db <bundle.sqlite> --run <run-id>
python -m run_bundle find --db <bundle.sqlite> --run <run-id> --kind step
```

The importer requires `session.json` and `steps.ndjson`, verifies the declared
step count and recorded action on every step, and rejects an existing run ID.
If session usage metadata is present, its action counts must match the steps. For
legacy sessions without usage metadata, the importer derives action counts from
the step records and leaves summary timestamps null when step timestamps are
not consistently available. Present usage timestamps must be valid UTC ISO-8601
values and must match the first/last step timestamp when that boundary is
available. Invalid step timestamps alongside usage metadata are rejected;
legacy records without session usage keep the original step payload and receive
null summary timestamps if timestamp coverage is missing or malformed.
It maps `win`/`loss` to `won`/`lost`, keeps an unfinished source active, and
stores usage and recording metadata plus SHA-256 hashes of both source files as
provenance. Evidence records are canonicalized JSON objects; the source files
remain untouched and their hashes identify the imported source. Import is one
database transaction. The destination database must already be migrated; the
import command does not create or upgrade its schema.

## Terminal Checkpoint

Recording association is the one user-facing pause in this bounded workflow.
Before proposing a new capture or association, the agent does the read-only
inventory below; a new capture also needs the staged live preflight. An
unassociated marker does not prove that no video exists; a matching filename,
marker or nearby timestamp does not prove that pixels correspond to the run.
Before calling the association operation, present a concise terminal summary:

- run ID and current lifecycle status;
- whether a producer marker was found, and its validation summary;
- whether recording is required or optional;
- the proposed list of present items or evidence relevant to the operation;
- the choices `confirm`, `decline`, or `interrupt`.

For video association, translate the IDs into an intelligible proposal: show
the candidate video's location, duration and available frame/screenshot (or
state why a preview could not be produced); the proposed gameplay run and its
source segment IDs, step count, outcome and time window; the OBS marker and
its validation result; and any competing or missing candidates. Include source
hashes when available. The agent gathers this information; the user should not
need to open files or infer which opaque ID means which game. Ask a focused
question only about a pairing or correction that the evidence cannot settle.
Label each claim separately: video file identified, marker associated, oracle
integrity audited, timestamps mapped, rendered frames checked, and reconstruction
scored. None implies the next.

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

## Existing Evidence And Capture Preflight

For capture or evaluation work, first inspect the agreed issue and handoff,
`planning/BALATRO_RUNTIME.md` (machine-specific, dated), the example external
recording root in `planning/TOOLING.md`, and candidate provenance in
`planning/PHASE0_INVENTORY.md`. Verify the current OBS destination rather than
assuming any dated location is still active. Inventory
candidate videos, oracle directories, bundle summaries, markers and existing
viewer/alignment artifacts read-only; compare run/segment identities, time
windows, outcomes, hashes and any known Continue boundary. A producer session
ID is not necessarily a gameplay run, and one video need not imply one source
segment. Preserve ambiguous candidates; do not pair by filename alone. Check
the specific claim against existing material before requesting another capture.

If a fresh live video really is needed, the agent prepares the setup before
inviting the user to play: verify the checked-in versus installed producer hash
and the *loaded* build in the newest game log after restart; verify one active
consumer writing to the intended external output root; verify the OBS started-
event hook, fully expanded IPC directory and actual recording destination/FPS.
Report these static checks promptly as *setup readiness*, not as proof of a
successful capture. If a start event can safely be tested, observe the request
and producer response; otherwise label the handshake unverified until the real
OBS event. A configured path, an old log or a request without a response is not
a passed handshake. At the intended capture, check whether its producer run
already has a consumer session: the current bridge attaches a marker only on
new session creation. After the OBS event and first persisted gameplay action,
inspect that run's `session.json` for the expected recording marker. A marker in
the IPC directory or on a different session is not proof of association. Even
on the intended session, earlier queued actions may predate OBS start: compare
the first and last action times with the video window and label uncovered steps
rather than calling the whole run recorded. If the session already existed
before OBS started or the marker is absent, do not
claim the pairing; preserve evidence and use the explicit association checkpoint
only with a validated marker and a human-confirmed, evidence-supported proposal.
Do not demand session persistence before any action can create it.

If a check fails, diagnose or repair only within authorized scope, then
recheck; do not invite a potentially invalid recording. Distinguish verified
setup from user-controlled OBS/game actions and in-capture checks. Do not
change installed mods, saves, OBS configuration or live processes without the
applicable permission and reversible procedure. Keep source files and uncertain
fragments intact.

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
2. Inventory existing evidence; for new video perform static setup checks before
   inviting play, then event/session checks when the capture makes them possible.
   Inspect bundles with `python -m run_bundle ...`; preserve JSON envelopes and
   diagnostics in any report.
3. Build the terminal summary and visual pairing proposal from observed data;
   label unknown or missing values explicitly.
4. Pause for the user to correct the proposal and choose an outcome. A user
   confirming the video/run identity does not silently confirm a separate
   association operation; record the explicit outcome for that operation.
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
