# Development Roadmap

## Objective

Build a laptop-developable, scalable game-state reconstruction pipeline for
Balatro video, validated against a Lua ground-truth oracle. The first success
criterion is trustworthy structured data, not an autonomous agent or a winning
strategy.

Gate conventions: every gate states a metric and a threshold. Thresholds are
fixed in the Phase 0 evaluation protocol so a gate can pass or fail. Where a
threshold is not yet known, the gate says `threshold: set in Phase 0`. Phases
4-10 currently name their metric and owner and defer the numeric threshold to
Q03.

## Component Ownership

Every active component has an owning phase or an explicit cross-cutting role.
A cross-cutting component is a prerequisite consumed across phases rather than
the deliverable of one phase.

| Phase | Owning components |
| --- | --- |
| 0 | `components/ground-truth.md` |
| 1 | `components/ontology.md` |
| 2 | `components/synthetic-data.md` |
| 3 | `components/detection.md` |
| 4 | `components/page-classification.md` |
| 5 | `components/ocr.md` |
| 6 | `components/tracking.md` |
| 7 | `components/state-composition.md`, `components/state-reduction.md` |
| 8 | `components/events.md` |
| 9 | `components/dataset.md` |
| 10 | `components/learning.md` |
| Cross-cutting | `components/coordinates.md` |

Coordinates and stream-layout normalization (D007) are defined once and
consumed by detection (Phase 3), page classification (4), OCR (5), tracking
(6), and composition (7). They are a foundation, not a phase of their own, so
they are not renumbered into the phase sequence.

## Open Questions And Gates

Questions in `DECISIONS.md` that block a gate are linked here. A question that
blocks a gate must appear in this table.

| Question | Blocks | Why |
| --- | --- | --- |
| Q01 | Phase 1 | The initial Balatro version and mod configuration that define the ontology are unresolved. |
| Q02 | Phase 0-1 | Asset redistribution legality gates the active, provenance-backed asset store. |
| Q03 | Phase 0 | Numeric gate thresholds are fixed in the Phase 0 evaluation protocol; every later gate depends on it. |
| Q04 | Phase 0, 7 | Which visible state is unrecoverable from video alone bounds reduction and the oracle boundary. |
| Q05 | Phase 8 | Event labels are trusted only after a stated oracle agreement rate is met. |
| Q06 | Phase 7-8 | Confidence propagation crosses detection, OCR, composition, reduction, and events. |

## Phase 0: Boundary, Ground Truth, and Evaluation

Status: `building`

Inventory Marco Costa's public artifacts, move required assets into a versioned
active store with provenance, stand up the Lua ground-truth oracle, build the
minimal annotation/QA tool, and define the real-frame evaluation set and
protocol.

Gate:

- Every planned output has a stated meaning and owning component.
- The Lua oracle emits aligned `(state, action, outcome)` for at least one run.
- An evaluation set exists (real clips, disjoint from synthetic backgrounds and
  training video) with a documented annotation protocol.
- Required assets/weights are versioned with provenance and are not gitignored.
- Gate thresholds for Phases 1-10 are recorded.

## Phase 1: Ontology, Class Map, and Typography

Status: `planned`

Define canonical IDs by adopting and extending the existing class-ID map.
Cover cards, jokers, consumables, packs, vouchers, tags, blinds, stakes, deck
types, editions, seals, stickers, visible UI, page/zone vocabulary, and OCR
typography.

Gate:

- Every supported class has stable identity, type, source asset, geometry
  expectations, and composition rules.
- A class-map version translates detector IDs back to canonical metadata.
- Typography assets cover every OCR glyph and modifier state.
- At least one example exists for every composition rule.

## Phase 2: Synthetic Scene and Glyph Generation

Status: `planned`

Generate realistic gameplay scenes by compositing known assets onto backgrounds,
and generate synthetic OCR glyph crops for UI text. Emit images and exact
annotations without manual labeling.

Gate:

- Generated annotations round-trip correctly.
- Coverage reports expose class imbalance and missing combinations.
- Glyph crops match the OCR training format and cover all fields and states.
- Background/seed pools are separated from the Phase 0 evaluation set.
- Resolution and aspect-ratio diversity meets the Phase 0 protocol.

## Phase 3: Object Detection

Status: `planned`

Train and evaluate a broad detector using synthetic data. Models are exported
to the ONNX format with a pinned opset (D017) and executed through ONNX
Runtime execution providers: CPU/DirectML for laptop development and a batch
GPU path executing the same ONNX artifact through ONNX Runtime execution
providers.

Gate (all measured on the Phase 0 real eval set):

- Per-class-family recall meets `threshold: set in Phase 0`; aggregate mAP is
  reported but not sufficient.
- Small-object recall (editions/stickers/seals) meets threshold.
- False-positive rate per family is under threshold.
- CPU/DirectML and batch GPU inference run the same ONNX artifact through
  ONNX Runtime execution providers and produce contract-compatible output
  within a pinned numeric tolerance; byte-identity across providers is not
  expected (D012, D017).
- Inference is resumable for long videos.

## Phase 4: Page Classification and Zone Assignment

Status: `planned`

Identify the current screen/page and assign detected objects to zones with
ordering. This owns `page_name` and zone semantics that all downstream target
resolution depends on.

Gate:

- Page classification accuracy meets threshold on the eval set, including
  modded-UI variants.
- Zone assignment and ordering match ground-truth zones on benchmarked frames.
- Unknown/unrecognized pages are emitted explicitly, never guessed as a known
  page.

## Phase 5: OCR and Numeric State

Status: `planned`

Extract chips, mult, money, blind values, ante, hands, discards, and other text
fields using canonical coordinate regions, a synthetically trained recognizer,
and per-field validation. Temporal stabilization is owned by Phase 6; OCR emits
per-frame raw and validated values only.

Gate:

- Each field has an explicit error policy, valid range, and measured accuracy
  against the oracle.
- Resolution/aspect changes do not require per-video retuning.
- Flicker and transient OCR errors are visible in debug output.

## Phase 6: Tracking and Cleanup

Status: `planned`

Turn frame-level detections and per-frame OCR fields into temporally consistent
observations, handling brief misses, movement, duplicate boxes, and changing
confidence, with one shared stabilization model for objects and OCR fields.

Gate:

- Track identities remain stable through ordinary animations and short gaps.
- Duplicate boxes are handled deterministically.
- Fast transitions do not silently interpolate across incompatible objects.
- OCR and tracking share one stabilization/provenance model with no double-carry.

## Phase 7: Structured State Composition and Persistent Reduction

Status: `planned`

Attach modifiers to parents, assign zones and ordering, emit versioned visible
state, then reduce it into the declared persistent-state contract and
deterministic legality masks over the declared action space. The reducer
defines the action-space index and the masks; observed action labels and
`target_action_id` belong to Phase 8 (D020).

Gate:

- A human can inspect a frame and its structured representation together.
- State can be reconstructed consistently from component outputs by class family
  and region, not only in aggregate.
- The reducer reproduces reference persistent state from ground-truth runs.
- Masks agree with oracle legal actions on benchmarked steps.

## Phase 8: Event and Action Inference

Status: `planned`

Infer transitions such as buying, selling, playing, discarding, rerolling,
selecting blinds, and opening packs from state deltas and temporal context, and
emit each event's canonical action label, target, and `target_action_id` within
the action-space index defined by Phase 7, with confidence propagated from
upstream (D020).

Gate:

- Event precision and recall against the Lua oracle meet threshold.
- Confidence is propagated from detection/OCR/composition, not asserted.
- Low-confidence and ambiguous events remain explicitly `unknown`/`ambiguous`.

## Phase 9: Dataset Production

Status: `planned`

Process large video collections into partitioned, reproducible state and event
datasets with a declared storage format, schema versions, provenance, quality
scores, and reprocessing support.

Gate:

- A small video runs end-to-end locally.
- A larger batch resumes after interruption.
- Schema versions are explicit and migrations are defined.
- Dataset splits avoid neighboring-frame, source-video, and synthetic/eval
  leakage.

## Phase 10: Analysis and Learning

Status: `planned`

Explore descriptive statistics, behavior cloning baselines, representation
learning, and other approaches only after data quality is established.

Gate:

- A simple state-to-action baseline trains and is evaluated by event type
  against the declared contract.
- Downstream claims report dataset coverage, uncertainty, and leakage risks.
- Any imitation-learning claim includes an out-of-distribution or rollout test.
