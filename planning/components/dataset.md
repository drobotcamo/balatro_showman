# Component Contract: Dataset Production

Status: `planned`

## Purpose

Produce large, reproducible, quality-aware datasets from video and intermediate
pipeline artifacts, with a declared storage format and schema versions.

## Inputs

- Video manifests.
- Detection, OCR, tracking, page/zone, state, persistent-state, and event
  artifacts.
- Pipeline and schema versions.
- Ground-truth oracle records (for validation splits and outcome labels).

## Outputs

- Partitioned state and event data in a declared format.
- Per-video manifests and quality summaries.
- Schema-version records and migration notes.
- Debug references back to source video/frame.

## Invariants

- Every row is traceable to source video and frame.
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
