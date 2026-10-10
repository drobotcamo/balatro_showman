# Run-Bundle Operations

This guide documents the Issue #34 run-bundle boundary and the separate Issue
#46 recording-association operation. The Issue #107 automatic file-intake path
does not call recording association and does not pause for user input.

## Entrypoint

Showman Capture provides the task-oriented entrypoint `python -m showman`.
See `docs/capture/README.md` and `docs/capture/reference.md` for onboarding,
capture/import/inspection commands, and the terminal association surface.
`python -m showman inspect ...` delegates to the same read-only inspector;
`store init`, `store import`, `record`, and confirmed `associate` are mutating.
For the default F-drive location, the single operational catalog, source
staging and location/association rules are in `docs/capture/archive.md`.
`showman archive inventory/list/verify/media-inventory/verify-media` are
read-only; `archive init/upgrade/ingest/sync-associations/stage-video/stage-media`
are explicit writes. The catalog does
not migrate older bundles or redirect an already-running recorder.

Use the package module rather than a second standalone launcher:

```text
python -m run_bundle <command> --db <bundle.sqlite> ...
```

`run_bundle/__main__.py` emits JSON envelopes and uses the read-only
`RunBundleInspector`. Inspection commands include `list`, `summary`, `step`,
`find`, `provenance`, `evidence`, `mechanics-reference`, `validate`, `outcome`,
`transitions`, and `diff`. `mechanics-reference` is the only reader for the
separate engine-answer channel. `validate --strict` requests strict diagnostics; inspection never
repairs evidence or changes lifecycle state.

Database setup is separate and mutating. For an **explicitly approved** upgrade
of the existing catalog, the archive command backs it up before invoking
Alembic:

```powershell
py -3 -m showman archive upgrade --root 'F:\OBS_RECORDINGS\showman-archive'
```

Do not run a bare `alembic upgrade head`: `alembic.ini` contains a generic
relative filename that is not the F-drive catalog. For a standalone bundle,
set its `sqlalchemy.url` deliberately under the storage procedure in
`planning/RUN_BUNDLE_STORAGE.md`. Do not migrate during inspection or merely
to start a recording; the catalog was already initialized and migrated.

## Automatic File-IPC Intake

For a new operational capture, use `docs/capture/README.md` → “Record a new
session” and the paired `showman-archive/captures` and `catalog.sqlite` paths.
The generic bridge command below describes the lower-level interface and does
not itself register a new session in the archive catalog when pointed elsewhere.
Do not start it alongside a running `showman record` consumer.

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
declared step count and recorded action on every step. Optional
`mechanics_reference.ndjson` records are imported as typed `mechanics_reference`
entries; they are not merged into step payloads and are queried only with the
explicit mechanics-reference reader. A repeat import with the same run
ID and source-file hashes is a no-op success; a different source under that run
ID is reported as a conflict. For Dagger-capable terminal signals, the consumer
waits for all declared resolved reference records before automatic import;
unresolved watches leave an explicit diagnostic and do not imply completion.
If session usage metadata is present, its action
counts must match the steps. For legacy sessions without usage metadata, the importer derives action counts from
the step records and leaves summary timestamps null when step timestamps are
not consistently available. Present usage timestamps must be valid UTC ISO-8601
values and must match the first/last step timestamp when that boundary is
available. Invalid step timestamps alongside usage metadata are rejected;
legacy records without session usage keep the original step payload and receive
null summary timestamps if timestamp coverage is missing or malformed.
It maps `win`/`loss` to `won`/`lost`, preserves usage and recording metadata, and
stores source type, source identity and SHA-256 hashes of `session.json`,
`steps.ndjson`, and optional `mechanics_reference.ndjson` as provenance. Reference
records are separate from steps and only appear through
`mechanics-reference`. Evidence records are canonicalized JSON objects. Import is one
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

This existing checkpoint applies only to callers that explicitly invoke the
recording-association operation. It controls whether a validated recording
marker is associated with a run. `FileIpcBridge --bundle-db` does not invoke
this operation; it does not prompt, wait for a response, or gate RunBundle
import on confirmation. Run intake above remains automatic.

Before proposing a new capture or explicit association, the agent does the
read-only inventory below; a new capture also needs the staged live preflight.
Include `showman archive list` and `showman archive verify` when the F-drive
catalog is available. Historical sources and the issue82 live output remain
separate until their exact state is inspected; never classify a run by root name.
An unassociated marker does not prove that no video exists; a matching filename,
marker or nearby timestamp does not prove that pixels correspond to the run.

Before calling the recording-association operation, present a concise terminal
summary:

- run ID and current lifecycle status;
- whether a producer marker was found, and its validation summary;
- whether recording is required or optional;
- the proposed list of present items or evidence relevant to the operation;
- the choices `confirm`, `decline`, or `interrupt`.

For video association, translate IDs into an intelligible proposal: show the
candidate video's location, duration and available frame/screenshot (or state
why a preview could not be produced); the proposed gameplay run and its source
segment IDs, step count, outcome and time window; the OBS marker and validation
result; and any competing or missing candidates. Include source hashes when
available. The agent gathers this information; the user should not have to open
files or infer which opaque ID means which game. Ask a focused question only
about a pairing or correction that evidence cannot settle. Label each claim
separately: video identified, marker associated, oracle integrity audited,
timestamps mapped, rendered frames checked, reconstruction scored. None
implies the next.

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
`planning/PHASE0_INVENTORY.md`. Use `docs/capture/README.md` for current task
commands. Verify the current OBS destination rather than assuming any dated
location is still active. Inventory candidate videos, oracle directories,
bundle summaries, markers and existing viewer/alignment artifacts read-only;
compare run/segment identities, time windows, outcomes, hashes and known
Continue boundaries. A producer session ID is not necessarily a gameplay run,
and one video need not imply one source segment. Preserve ambiguous candidates;
do not pair by filename alone. Test the specific unmet claim against existing
material before requesting another capture.

If a fresh live video is needed, prepare the setup before inviting the user to
play: verify checked-in versus installed producer hash and the *loaded* build
in the newest game log after restart; verify one active consumer writing to the
intended external output root; verify the OBS started-event hook, fully expanded
IPC directory and actual recording destination/FPS. Report these static checks
promptly as *setup readiness*, not proof of capture. If a start event can safely
be tested, observe the request and producer response; otherwise label the
handshake unverified until the real OBS event. A configured path, old log or
request without a response is not a passed handshake.

At the intended capture, check whether its producer run already has a consumer
session: the current bridge attaches a marker only on new session creation.
After the OBS event and first persisted gameplay action, inspect that run's
`session.json` for the expected marker. A marker in the IPC directory or on a
different session is not proof of association. Even on the intended session,
earlier queued actions may predate OBS start: compare action timestamps with
independently observed video timing and label uncovered steps rather than
calling the whole run recorded. If the session already existed before OBS
started or the marker is absent, do not claim the pairing; preserve evidence
and use the explicit association checkpoint only with a validated marker and
a human-confirmed, evidence-supported proposal. Do not demand session
persistence before any action can create it.

If a check fails, diagnose or repair only within authorized scope and recheck;
do not invite a potentially invalid recording. Distinguish verified setup from
user-controlled OBS/game actions and in-capture checks. Do not change installed
mods, saves, OBS configuration or live processes without applicable permission
and a reversible procedure. Keep source files and uncertain fragments intact.

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
2. Inventory existing evidence. For new video perform static setup checks before
   inviting play, then event/session checks when the capture makes them possible.
   Inspect bundles with `python -m run_bundle ...`; preserve JSON envelopes and
   diagnostics in any report.
3. For an explicit association operation, build the terminal summary and visual
   pairing proposal from observed data; label unknowns explicitly.
4. Pause for the user to correct that proposal and choose an outcome. Identity
   confirmation does not silently confirm a separate association operation;
   record the explicit outcome for that operation. Automatic intake does not
   invoke this checkpoint or require a per-run prompt.
5. Associate only after explicit `confirm` and successful marker validation.
6. Run the narrowest relevant tests plus `python planning/check_contracts.py`
   and `git diff --check`.
7. Ask the user before changing lifecycle, schema, hash, provenance, OBS, or
   CLI contracts.

## Boundaries

The bundle lifecycle includes `active`, `interrupted`, `incomplete`,
`completed`, `endless`, `won`, `lost`, and `aborted`. Evidence remains append-only
at the application boundary, and terminal outcomes remain immutable.
Compatibility adapters remain read-only. This guide does not define Phase 9
export storage or deterministic replay.
