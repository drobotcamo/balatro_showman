# Component Contract: Synthetic Data

Status: `planned`

## Purpose

Generate realistic training scenes and exact labels without manual bounding-box
annotation, and generate synthetic OCR glyph crops for UI text.

## Inputs

- Ontology, typography, and asset metadata.
- Transparent or extracted asset sprites.
- Real gameplay backgrounds and/or programmatic scene layouts.
- Randomization configuration and seed.

## Outputs

- Images or image shards.
- Exact object annotations with class IDs and boxes.
- Synthetic OCR glyph crops in the recognizer's training format, labeled across
  all fields and visual states.
- Scene manifest containing seed, assets, transforms, background, and generator
  version.

## Invariants

- Every annotation is generated from the same transform as its visual asset.
- Seeds make scenes reproducible.
- Train/validation/test backgrounds, seeds, and source videos are separated.
- Background pools used for training are disjoint from the applicable evaluation
  set; eval failure surfaces are never trained on.
- Synthetic-only metadata never masquerades as observed game state.

## Acceptance Criteria

- Annotation round-trip visualization is correct.
- Coverage reports expose class imbalance and missing combinations.
- The generator can create difficult small, occluded, modified, and overlapping
  objects.
- Glyph crops match the OCR training format and cover all fields and states.
- Resolution and aspect-ratio diversity meets the applicable approved protocol,
  fixed before held-out evaluation (D028/Q03).
- A real-frame smoke set shows transfer beyond synthetic imagery.
