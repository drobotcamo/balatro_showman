# Component Contract: Dataset Production

Status: `planned`

## Purpose

Produce large, reproducible, quality-aware datasets from video and intermediate
pipeline artifacts.

## Inputs

- Video manifests.
- Detection, OCR, tracking, state, and event artifacts.
- Pipeline and schema versions.

## Outputs

- Partitioned state and event data.
- Per-video manifests and quality summaries.
- Debug references back to source video/frame.

## Invariants

- Every row is traceable to source video and frame.
- Reprocessing a video is idempotent for the same versions and configuration.
- Partial failures are resumable and visible.
- Dataset splits avoid accidental neighboring-frame leakage.

## Acceptance Criteria

- A small video can run end-to-end locally.
- A larger batch can resume after interruption.
- A consumer can load data without knowing internal pipeline details.
