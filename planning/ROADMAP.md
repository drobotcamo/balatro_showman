# Delivery Roadmap

## Objective

Deliver two complementary products (D037): evidence-linked deep run data and
video-only observations that improve and broaden it. Dagger is the first mechanics
result; analysis does not wait for a complete detector, registry or video pipeline.
`ARCHITECTURE.md` defines the shared boundary. GitHub owns live scope and blockers.

## Delivery Sequence

@drobotcamo is accountable for the portfolio and human decisions. The lead taking
each issue owns implementation and its runnable evidence; unassigned work is not
active. One production outcome remains the default, with independent research or
review alongside it. The following are outcomes, not whole-issue closure chains.

| Outcome / owner | Actual prerequisites | Runnable acceptance and product advance |
| --- | --- | --- |
| Dagger input/output contract: #122 mechanics lead | Captured evidence and current reducer/event contracts; no full registry | Publish versioned Dagger examples and contract checker for evidence/reference isolation, timing, identities and unknowns. User reviews concrete schema. Establishes the shared deep/visual interface. |
| Dagger reference: #123 capture lead | Approved Dagger schema; #115 accepted interface only for resumed live scenarios | Producer/reader tests and authorized capture show pre-Mult, actual victim sell value and resolved post-Mult. Answer-key adapter isolation is checked. Supplies independent validation, not reconstruction inputs. |
| Dagger state, sacrifice effects and growth report: #124 mechanics lead | #122 Dagger interface; reference work can overlap; #123 required to claim engine validation | Deterministic chronological positive/zero/incomplete scenarios, reference comparison, evidence-linked per-round graph and denominator/coverage report. First useful deep-data product. |
| Video-like Dagger challenge: #127 integration lead with user | Runnable Dagger, approved deliberately restricted observations | Same reducer; forbidden-input/reference-perturbation checks, unknown propagation and readable diagnostics. Establishes video-only input sufficiency without waiting for a model. |
| Small scene/glyph pack: #132 visual lead | Only required slice vocabulary/assets with provenance, seed/split manifest; new dependencies need approval | Reproducible scene/glyph command, label/transform round-trip, coverage and source/background split checks. Targets Dagger's measured observation gaps, not every asset. |
| Selected real-video observations: visual lead; #82 retains annotation/evaluation ownership | Available slice detector/OCR/page/track adapter, aligned evidence and applicable frozen protocol | Export timestamped observations; score selected fields, support, abstention and downstream Dagger effects separately. Feed the same reducer. Synthetic/video-like success is not real-video accuracy. |
| Uses and contributions, then lineage: #129 and #130 mechanics leads | Reusable Dagger boundary; slice-specific #122 semantics and #123 references; #130 consumes #129 occurrences | Runnable Hermit/Mail-In Rebate queries, then Certificate → Death → Gold Seal history. Report direct versus overlapping upstream views and unknown coverage. Broadens deep data and identifies new visual requirements. |
| Definition review and registry coverage: #126 UI lead, #125 registry lead | Representative approved definitions; Dagger findings for expansion | Browser persistence/revision-invalidation smoke, then bounded family tests and individual user dispositions. Exhaustive inventory is its own outcome, not a prerequisite above or a Phase 0 gate. |

#122 starts with Dagger plus an extensible entity/effect boundary; later contribution
and lineage examples are reviewed before their consuming slices, not before Dagger.
#121 coordinates staged delivery, while #125 owns eventual exhaustive Joker coverage.
Do not duplicate #82 annotation or #115 producer lifecycle work.

## Current Evidence And Next Action

As of master `33338ea`: Showman Capture, durable queue/run bundles, Inspector,
development annotation export and local video/action viewer exist. #79 has frozen
first-slice criteria; #82 has a user-reviewed seven-frame development pilot with
unverified alignment and no predictions. #115/PR #117 owns Continue identity;
its bounded live smoke passed review, with post-capture association still pending
as of the issue's current acceptance report. Further held-out collection is paused there.
Existing evidence inspection and fixture-backed design can continue.

There is no active scene/glyph generator, video reconstructor or mechanics reducer.
Legacy compositing/detection are references, not active dependencies. Historical
Dagger footage shows +62 → +70 but captured records omit stored Mult and actual
sell value; it motivates #123, not a validated mechanics claim.

Exact next production action: the #122 lead inventories Dagger's permitted inputs,
publishes pre/action/resolved examples and an isolation/timing checker, and requests
review of that concrete schema. #82 and #115 leads continue their existing scopes.

Existing baseline checks (run from the repository root):

```text
python planning/check_contracts.py
python -m pytest -q tests/test_eval_manifest.py tests/test_qa_viewer.py
```

New slice issues must publish their actual runnable command before completion;
commands for unimplemented stages are not claimed to exist.

## Component Ownership

Tracks replace phase numbers as delivery sequencing. Historical phase IDs remain
evaluation references, not prerequisites for starting useful bounded slices.

| Track / role | Owning components |
| --- | --- |
| Shared evidence and evaluation (Phase 0) | `components/ground-truth.md`, `components/dataset.md` |
| Shared vocabulary and geometry (Phase 1 / cross-cutting) | `components/ontology.md`, `components/coordinates.md` |
| Visual observations (Phases 2–6) | `components/synthetic-data.md`, `components/detection.md`, `components/page-classification.md`, `components/ocr.md`, `components/tracking.md` |
| Shared visible-state boundary (Phase 7) | `components/state-composition.md` |
| Deep state and effects (Phases 7–8) | `components/state-reduction.md`, `components/events.md` |
| Deep analytics / optional learning (Phase 10) | `components/learning.md` |

## Open Questions And Gates

| Question | Blocks | Why |
| --- | --- | --- |
| Q01 | New slice vocabulary/inventory | Pin the consumed game/mod revision, not every future asset. |
| Q02 | Use of a required unresolved asset | Existing user-supplied disposition is not redistribution permission. |
| Q03 | Applicable held-out evaluation | First-slice D034 remains frozen; new mechanics/visual protocols need approved criteria and support. |
| Q04 | Claims for a field/condition | Visibility in principle is not sufficient observed evidence. |
| Q05 | Action/effect inference claims | STEP anchors are not a complete trigger stream; agreement must be measured. |
| Q06 | Cross-stage confidence claims | Propagate source uncertainty into state, effects and aggregate coverage. |

## Phase 0: Evidence And Evaluation

Status: `building`

Gate (unchanged): stated output meanings/owners; Lua oracle aligned
`(state, action, outcome)` for at least one run; disjoint real evaluation clips and
annotation protocol; required assets/weights versioned with provenance; applicable
evaluation protocol approved before held-out scoring. An exhaustive Joker registry
is not part of this gate. No slice alone passes it.

## Retained Broad Evaluation Obligations

Phases 1–10 remain `planned`; none is passed by this revision. Component contracts
retain their interfaces and broad acceptance. The old eleven-step implementation
queue and duplicate gate prose are retired. When claiming broad coverage, supply:

| Historical scope | Required evidence |
| --- | --- |
| 1: vocabulary | Stable class IDs, composition examples, asset provenance and typography coverage. |
| 2: generation | Exact label round-trip, coverage, glyph-format compatibility and split/geometry checks. |
| 3–5: detector/page/OCR | Approved per-family/field accuracy, small-attribute recall, false positives, zones/order, unknown pages and resolution transfer; same pinned ONNX artifact with provider tolerance. |
| 6: tracking | Stable identities through gaps, deterministic duplicate handling, no incompatible interpolation or double stabilization. |
| 7–8: state/actions | Inspectable composition; persistent-state and legality agreement; event precision/recall and propagated ambiguity under the applicable protocol. |
| 9: scale-out | Local end-to-end run, interruption/resume, version/migration and leakage-safe partitions. Small deep-data exports need not wait for scale-out. |
| 10: learning | Event-type baseline evaluation and OOD/rollout evidence for imitation claims. Descriptive mechanics analytics require validated slice data, not an action model. |

Thresholds, minimum support, held-out separation, permissions and dependencies are
not changed. Under-supported results stay descriptive/inconclusive. Learning and
scale-out are consumers of useful data, not barriers to producing it.
