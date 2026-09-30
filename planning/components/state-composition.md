# Component Contract: Structured State Composition

Status: `planned`

## Purpose

Turn tracked objects and stabilized OCR into a versioned, inspectable visible
game state.

## Inputs

- Object tracks.
- OCR fields.
- Ontology composition rules.
- Zone and ordering definitions.

## Outputs

- Per-frame state snapshot.
- Object records with attributes, zone, ordering, provenance, and confidence.
- State-quality summary.

## Invariants

- Observed, inferred, missing, and contradictory values are distinguishable.
- Modifier attachment is deterministic and explainable.
- State schema versions are explicit.
- No state field is silently filled from future frames.

## Acceptance Criteria

- A human can inspect a frame and its structured representation together.
- Parent-child composition handles common editions, seals, and stickers.
- State serialization is stable and queryable.
