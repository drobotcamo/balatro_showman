# Component Contract: Synthetic Data

Status: `planned`

## Purpose

Generate realistic training scenes and exact labels without manual bounding-box
annotation, and generate synthetic OCR glyph crops for UI text.
Start with fields/objects needed by a bounded mechanics slice, not complete asset
coverage. `planning/ARCHITECTURE.md` defines how predictions enter deep run data.

## Inputs

- Ontology, typography, and asset metadata.
- Transparent or extracted asset sprites.
- Real gameplay backgrounds and/or programmatic scene layouts.
- Randomization configuration and seed.

## Outputs

- Images or image shards.
- Exact object annotations with class IDs and boxes.
- Synthetic OCR glyph crops in the recognizer's training format, labeled for the
  declared supported fields and visual states; missing coverage is reported.
- Scene manifest containing seed, assets, transforms, background, and generator
  version.

## Invariants

- Every annotation is generated from the same transform as its visual asset.
- Seeds make scenes reproducible.
- Train/validation/test backgrounds, seeds, and source videos are separated.
- Background pools used for training are disjoint from the applicable evaluation
  set; eval failure surfaces are never trained on.
- Synthetic-only metadata never masquerades as observed game state.
- Evaluation gaps guide new development generation without reusing held-out
  imagery/backgrounds or tuning to held-out answers. Metadata/labels are not inputs
  to a claimed video-only inference run.

## Acceptance Criteria

- Annotation round-trip visualization is correct.
- Coverage reports expose class imbalance and missing combinations.
- The generator can create difficult small, occluded, modified, and overlapping
  objects.
- A reproducible small scene/glyph pack round-trips labels/transforms and reports
  unsupported combinations. Full glyph coverage is a later broad-scope claim.
- Resolution and aspect-ratio diversity meets the applicable approved protocol,
  fixed before held-out evaluation (D028/Q03).
- A real-frame smoke set shows transfer beyond synthetic imagery.
