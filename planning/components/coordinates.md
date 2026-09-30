# Component Contract: Coordinates and Stream Layout

Status: `planned`

## Purpose

Define the single canonical coordinate space and stream-layout normalization
that every stage uses, so geometry never drifts between synthetic generation,
detection, OCR, tracking, and composition.

## Inputs

- Raw frames and metadata (resolution, aspect ratio).
- Layout observations (letterboxing, UI scale, stream overlays).
- Field and region definitions from the ontology.

## Outputs

- Normalized frames or frame references in canonical space.
- Per-frame transform records (scale, offset, letterbox, active region).
- Region maps for OCR and zone assignment in canonical coordinates.
- Declared excluded regions (webcam, chat, overlays).

## Invariants

- Every coordinate is stated in canonical space plus the transform that produced
  it; no stage invents its own geometry.
- Letterbox, crop, and overlay regions are declared per video, not assumed.
- OCR regions are derived from canonical space, never hardcoded per resolution.
- Normalization is deterministic for a fixed configuration.

## Acceptance Criteria

- The same logical region resolves consistently across 640x360, 1080p, and
  non-16:9 sources with differing UI scale.
- Stream-overlay regions are excluded without removing gameplay.
- Transform records are inspectable and sufficient to invert to source pixels.
