# Component Contract: OCR and Numeric State

Status: `planned`

## Purpose

Recover visible text and numeric fields that object detection cannot represent.

## Inputs

- Video frames or frame references.
- Field definitions and coordinate regions.
- OCR engine output.

## Outputs

- Raw OCR records with text, confidence, region, and frame.
- Validated/stabilized field values.
- Field-level quality and unknown reasons.

## Invariants

- Raw OCR is never overwritten by stabilization.
- Each field has its own parser and valid range.
- Carry-forward values retain provenance and age.

## Acceptance Criteria

- Core economy, blind, score, hand, and discard fields have measured accuracy.
- Flicker and transient OCR errors are visible in debug output.
