# Component Contract: Synthetic Data

Status: `planned`

## Purpose

Generate realistic training scenes and exact labels without manual bounding-box
annotation.

## Inputs

- Ontology and asset metadata.
- Transparent or extracted asset sprites.
- Real gameplay backgrounds and/or programmatic scene layouts.
- Randomization configuration and seed.

## Outputs

- Images or image shards.
- Exact object annotations with class IDs and boxes.
- Scene manifest containing seed, assets, transforms, background, and generator
  version.

## Invariants

- Every annotation is generated from the same transform as its visual asset.
- Seeds make scenes reproducible.
- Train/validation/test backgrounds and seeds are separated.
- Synthetic-only metadata never masquerades as observed game state.

## Acceptance Criteria

- Annotation round-trip visualization is correct.
- Coverage reports expose class imbalance and missing combinations.
- The generator can create difficult small, occluded, modified, and overlapping
  objects.
- A real-frame smoke set shows transfer beyond synthetic imagery.
