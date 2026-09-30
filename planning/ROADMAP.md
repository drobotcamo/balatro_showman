# Development Roadmap

## Objective

Build a laptop-developable, scalable game-state reconstruction pipeline for
Balatro video. The first success criterion is trustworthy structured data, not
an autonomous agent or a winning strategy.

## Phase 0: Boundary and Evidence

Status: `building`

Inventory Marco Costa's public artifacts, preserve reusable local assets, define
the ontology, and establish representative real-video evaluation clips.

Gate: the team can state what every planned output means and has a small,
manually inspectable evaluation set.

## Phase 1: Asset Ontology and Metadata

Status: `planned`

Define canonical IDs for cards, jokers, consumables, packs, vouchers, tags,
blinds, stakes, deck types, editions, seals, stickers, and visible UI elements.

Gate: every supported class has stable identity, type, source asset, geometry
expectations, and composition rules.

## Phase 2: Synthetic Scene Generation

Status: `planned`

Generate realistic gameplay scenes by compositing known assets onto gameplay
backgrounds or programmatic layouts. Emit images and exact annotations without
manual bounding-box labeling.

Gate: generated annotations round-trip correctly, class coverage is measurable,
and a held-out real-frame smoke set shows useful detections.

## Phase 3: Object Detection

Status: `planned`

Train and evaluate a broad detector using synthetic data, with laptop-friendly
CPU/DirectML inference and a batch GPU path that uses the same model contract.

Gate: real-frame performance is measured by class family and small-object recall,
not only aggregate mAP.

## Phase 4: OCR and Numeric State

Status: `planned`

Extract chips, mult, money, blind values, ante, hands, discards, and other text
fields using fixed regions, OCR, validation, and temporal stabilization.

Gate: each field has an explicit error policy and stable output on representative
clips.

## Phase 5: Tracking and Cleanup

Status: `planned`

Turn frame-level detections into temporally consistent object tracks, handling
brief misses, movement, duplicate boxes, and changing confidence.

Gate: track identities remain stable through ordinary animations and short gaps.

## Phase 6: Structured State Composition

Status: `planned`

Attach modifiers to parent objects, assign objects to zones, preserve ordering,
and emit a versioned full visible-state representation.

Gate: state can be inspected frame-by-frame and reconstructed consistently from
the component outputs.

## Phase 7: Event and Action Inference

Status: `planned`

Infer transitions such as buying, selling, playing, discarding, rerolling,
selecting blinds, and opening packs from state deltas and temporal context.

Gate: high-confidence events are validated manually; ambiguous events remain
explicitly unknown instead of being silently guessed.

## Phase 8: Dataset Production

Status: `planned`

Process large video collections into partitioned, reproducible state and event
datasets with provenance, quality scores, and reprocessing support.

Gate: a new video can be processed end-to-end with resumability and traceable
outputs.

## Phase 9: Analysis and Learning

Status: `planned`

Explore descriptive statistics, behavior cloning baselines, representation
learning, and other approaches only after data quality is established.

Gate: downstream claims report dataset coverage, uncertainty, and leakage risks.
