# Development Roadmap

## Objective

Build a laptop-developable, scalable game-state reconstruction pipeline for
Balatro video, validated against a Lua ground-truth oracle. The first success
criterion is trustworthy structured data, not an autonomous agent or a winning
strategy.

Gate conventions: each applicable versioned phase/slice protocol names its
criteria, metrics, thresholds, minimum support, uncertainty rules and human
acceptance authority. The owning component proposes criteria; the user approves
them before held-out collection/scoring. Unknown criteria or inadequate support
cannot pass. Q03 remains open for unresolved scopes, not a prerequisite to
unrelated recorder fixtures. Development pilots may inform criteria; held-out
results may not tune them (D028).

## Integrated Delivery Milestones

1. Reliable recorded-run inspection (#81): fixture reliability, agreed runtime/
   capture check, finalized audited run, explicit human recording association,
   measured rendered correspondence and a copy-paste inspection command.
2. Reviewed evaluation slice (#79/#82): versioned development protocol, minimal
   annotation/QA/export and reviewed development pilot; then freeze user-approved
   evaluation criteria before held-out collection/scoring. #82 starts from the
   development protocol, not #79 closure. #80 blocks only use of unresolved
   required artifacts, not every optional legacy candidate.
3. Small measured video-only reconstruction: user-selected pages/fields, oracle-
   isolated inference, timestamped versioned observations/unknowns and inspectable
   report of held-out per-field error, support and abstention.

These cross-component slices do not pass skipped broad gates. Phase 0 stays
`building` and broad phases stay `planned` until their own evidence is accepted.
Capture existence, alignment accuracy, oracle semantics, evaluation readiness
and broad phase completion are separate claims. First-slice success is not
statistical generalization. Exact runtime, targets and thresholds remain decisions.

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
| Cross-cutting | `components/coordinates.md`, `components/run-mechanics.md` |

Run-mechanics reconstruction is an approved design effort tracked by #122 and
specified in `components/run-mechanics.md`. Its v0.1
interface and initial examples are owner-approved. It is cross-cutting across
ontology, tracking, reduction, events, ground truth, and analysis, but does not
renumber the phase sequence or pass any existing phase gate. Later staged
examples and exact order verification remain open.

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
| Q02 | Artifact-consuming Phase 0-1/slice steps | Eligibility blocks use of unresolved required artifacts; optional candidates do not block unrelated work. |
| Q03 | Applicable phase/slice evaluation | Approved criteria, thresholds and support must be fixed before held-out evaluation; future-phase thresholds do not block the first pilot. |
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
- The applicable evaluation protocol is versioned and approved before held-out
  evaluation. Broader phase criteria remain staged obligations, not waived.

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
- Resolution and aspect-ratio diversity meets the applicable approved protocol.

## Phase 3: Object Detection

Status: `planned`

Train and evaluate a broad detector using synthetic data. Models are exported
to the ONNX format with a pinned opset (D017) and executed through ONNX
Runtime execution providers: CPU/DirectML for laptop development and a batch
GPU path executing the same ONNX artifact through ONNX Runtime execution
providers.

Gate (all measured on the applicable approved real evaluation set):

- Per-class-family recall meets the approved protocol threshold; aggregate mAP is
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
scores, and reprocessing support. Operational capture and inspection begin from
the versioned SQLite run bundles established by Issue #34; this phase owns
scale-out exports and partitioning rather than replacing that run boundary.

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
