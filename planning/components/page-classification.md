# Component Contract: Page Classification and Zone Assignment

Status: `planned`

## Purpose

Identify the current screen/page and assign detected objects to zones with
ordering. This owns `page_name` and zone semantics that target resolution and
event inference depend on.

## Inputs

- Canonical-coordinate detections.
- Ontology page/zone vocabulary.
- Coordinate region map.
- Raw OCR records only as optional supporting evidence, never a prerequisite.

## Outputs

- Page/screen identity with confidence and an explicit `unknown` value.
- Zone assignment and position-in-zone for each object.
- Page-transition markers between frames.

## Invariants

- Page and zones are inferred outputs, not assumptions encoded from a known
  sequence.
- Page identity depends only on detections, the coordinate region map, and the
  ontology. Raw OCR may support it; stabilized OCR is never a prerequisite
  because stabilization is owned by tracking (Phase 6).
- Unrecognized pages are emitted as `unknown`; an unknown page never resolves
  to a known page by default.
- Assignment is deterministic for a fixed input and configuration.
- Modded-UI variants are first-class, not exceptions.

## Acceptance Criteria

- Page accuracy meets the Phase 4 gate on the eval set, including modded UI.
- Zone assignment and ordering match ground-truth zones on benchmarked frames.
- Zone assignment provenance is retained for state composition.
