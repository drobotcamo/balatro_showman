# Component Contract: Object Detection

Status: `planned`

## Purpose

Detect visible Balatro objects and visible attributes (editions, stickers,
seals) in individual frames.

## Inputs

- Synthetic detection dataset.
- Versioned ontology.
- Canonical-coordinate frames from the coordinates stage.
- Optional real evaluation frames.

## Outputs

- Per-frame detections: video/frame identity, class ID, confidence, box, model
  version, and coordinate-space version.
- Separate visible-attribute outputs for editions/seals/stickers.
- Annotated debug images.
- Evaluation metrics by class and family.

## Invariants

- Coordinates declare their source resolution, normalization, and the canonical
  transform that produced them.
- Model output is contract-compatible across execution devices within the
  pinned numeric tolerance; exact device-independence and byte-identity across
  providers are not required (D012, D017).
- Inference targets the ONNX model format with a pinned opset, executed
  through ONNX Runtime execution providers (D017); switching providers is
  configuration, not pipeline code.
- Unknown and low-confidence detections are retained or rejected by explicit
  policy, never implicitly discarded.
- Base class and visible attribute are separate outputs; modifiers are never
  folded into base class IDs.

## Acceptance Criteria

- CPU/DirectML and batch GPU inference run the same ONNX artifact through
  ONNX Runtime execution providers and produce contract-compatible output
  within a pinned numeric tolerance; byte-identity across providers is not
  expected (D012, D017).
- On the Phase 0 real eval set: per-family recall, small-object recall
  (editions/stickers/seals), and per-family false-positive rate each meet the
  Phase 0 thresholds.
- Aggregate mAP is reported but is not a sufficient gate.
- Inference is resumable for long videos.
