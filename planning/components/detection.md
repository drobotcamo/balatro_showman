# Component Contract: Object Detection

Status: `planned`

## Purpose

Detect visible Balatro objects and visual attributes in individual frames.

## Inputs

- Synthetic detection dataset.
- Versioned ontology.
- Optional real evaluation frames.

## Outputs

- Per-frame detections: video/frame identity, class ID, confidence, box, model
  version, and coordinate-space version.
- Annotated debug images.
- Evaluation metrics by class and family.

## Invariants

- Coordinates declare their source resolution and normalization.
- Model output is independent of execution device.
- Unknown and low-confidence detections are retained or rejected by explicit
  policy, never implicitly discarded.

## Acceptance Criteria

- CPU/DirectML and batch-GPU inference produce contract-compatible output.
- Evaluation includes small-object recall, modifier recall, and false positives.
- Inference is resumable for long videos.
