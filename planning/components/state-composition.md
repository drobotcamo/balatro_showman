# Component Contract: Structured State Composition

Status: `planned`

## Purpose

Turn tracked objects and stabilized OCR into a versioned, inspectable visible
game state, ready for persistent reduction.

## Inputs

- Object tracks and shared stabilization records.
- OCR fields.
- Page/zone assignment.
- Ontology composition rules.
- Zone and ordering definitions.
- Canonical coordinate transforms.

## Outputs

- Per-frame state snapshot.
- Object records with attributes, zone, ordering, provenance, and confidence.
- State-quality summary.
- A handoff to persistent reduction (the composed state sequence).

## Invariants

- Observed, inferred, missing, and contradictory values are distinguishable.
- Modifier attachment is deterministic and explainable.
- State schema versions are explicit.
- No state field is silently filled from future frames.
- Zone and ordering come from page/zone assignment, not from assumptions about
  the sequence.

## Acceptance Criteria

- A human can inspect a frame and its structured representation together.
- Parent-child composition handles common editions, seals, and stickers.
- Reconstruction is consistent by class family and region, not only in aggregate.
- State serialization is stable and queryable.
