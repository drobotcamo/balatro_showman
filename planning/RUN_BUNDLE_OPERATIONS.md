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

## Terminal Checkpoint

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
