# Component Contract: Dataset Production

Status: `planned` (Phase 9 handoff boundary defined)

## Purpose

Produce large, reproducible, quality-aware datasets from versioned run bundles,
video, and intermediate pipeline artifacts, with a declared storage format and
schema versions. Operational run-bundle storage and inspection are established
earlier by Issue #34; this component owns scale-out dataset production.
Early D028 slice manifests/export do not pass the broad Phase 9 scale-out gate.
Their applicable protocol is approved before held-out evaluation, with source-
level splits and the same provenance/leakage protections below.

## Inputs

- Video manifests.
- Detection, OCR, tracking, page/zone, state, persistent-state, and event
  artifacts.
- Pipeline and schema versions.
- Ground-truth oracle records (for validation splits and outcome labels).
- Versioned run bundles produced by the ground-truth storage boundary.

## Phase 9 Handoff Boundary

Run-bundle storage is the operational capture boundary, not the Phase 9 export
format. Dataset production accepts either a versioned SQLite bundle through its
read-only inspection interface or a legacy oracle directory through the
read-only compatibility reader. The latter preserves `session.json` and
`steps.ndjson` objects and reports source hashes; it never repairs or rewrites
the source.

- `no-video` means no recording association was supplied. It is not a claim
  that no video exists.
- `obs` means a recording marker was present in the source or a recording was
  associated after explicit human confirmation. It is not independent proof
  that the video file exists.
- Missing or invalid markers remain explicit diagnostics. Required recording
  coordination may block capture; optional coordination produces a non-video
  result rather than silently fabricating provenance.
- Partial and malformed oracle inputs remain inspectable diagnostics. A
  partial run may be resumed or reprocessed; malformed source bytes are
  preserved for diagnosis and are never silently converted into dataset rows.
- The future export job must checkpoint its input identity,
  schema/configuration versions, and completed partitions so interruption is
  resumable without mutating the source bundle.

## Outputs

- Partitioned state and event data in a declared format.
- Per-video manifests and quality summaries.
- Schema-version records and migration notes.
- Debug references back to source video/frame.

## Invariants

- Every row is traceable to source video and frame.
- Dataset production does not mutate the source run bundle.
- Reprocessing a video is idempotent for the same versions and configuration.
- Partial failures are resumable and visible.
- Dataset splits avoid neighboring-frame, source-video, and synthetic/eval
  leakage.
- The storage format and schema versions are explicit; a version bump has a
  migration path.

## Acceptance Criteria

- A small video can run end-to-end locally.
- A larger batch can resume after interruption.
- Schema versions are recorded and migrations are defined.
- A consumer can load data without knowing internal pipeline details.
