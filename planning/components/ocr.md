# Component Contract: OCR and Numeric State

Status: `planned`

## Purpose

Recover visible text and numeric fields that object detection cannot represent,
using a recognizer trained on synthetic glyph crops and canonical regions.

## Inputs

- Canonical-coordinate frames or frame references.
- Page/zone assignment for field-region context (Phase 4).
- Field definitions and canonical-space regions.
- Synthetic OCR glyph training crops.
- Synthetically trained recognizer output.

## Outputs

- Raw OCR records with text, confidence, region, and frame.
- Validated field values (parser and range checks; temporal stabilization is
  not applied here).
- Field-level quality and unknown reasons.

## Invariants

- Raw OCR is never overwritten; any downstream stabilization is attributed,
  not in-place.
- Each field has its own parser, valid range, and `X/Y` handling where relevant.
- Regions come from the coordinates stage; no per-video hardcoded pixels.
- Tracking (Phase 6) owns the single shared stabilization/provenance model and
  is the only stage that carries values forward. OCR emits per-frame raw and
  validated values and neither consumes the stabilized record nor carries
  values forward itself. The two stages never double-carry.

## Acceptance Criteria

- Core economy, blind, score, hand, and discard fields have measured accuracy
  against the ground-truth oracle.
- Accuracy holds across resolutions and aspect ratios without retuning.
- Flicker and transient OCR errors are visible in debug output.
