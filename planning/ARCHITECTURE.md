# Active Architecture

## Two Delivery Tracks

Deep run data reconstructs persistent gameplay instances, state and effects from
captured evidence and answers run-dynamics questions now. Visual data generates
synthetic scenes/glyphs and reconstructs observations from video, improving the
same run data. Neither track requires completion of the other. D037 approves this
direction; #122 owns concrete versioned schemas, starting with Dagger.

```text
captured evidence --> explicit allowlisted observation adapter --+
                                                               |
assets/vocabulary --> synthetic scenes/glyphs --> detector/OCR    |
video --> normalize/sample --> detect/page/zone/OCR --> track    |
                                      --> visible composition --+
                                                               v
                        chronological mechanics reduction + event inference
                                  |                         |
                            derived state             derived effects
                                  +----------+--------------+
                                             v
                                evidence-linked queries/reports

engine reference --> isolated evaluator <--- derived outputs / video predictions
                         |
                 discrepancies, coverage, uncertainty
                         --> next capture / synthetic coverage / rule correction
```

## Shared Interfaces

These are semantic boundaries, not an implemented schema or a storage selection.
Every artifact has schema/rule/config revisions and reproducible source identity.

| Artifact / owner | Required meaning and integration point |
| --- | --- |
| Evidence / capture and visual leads | Immutable source bytes, video/frame/step IDs, hashes, time and alignment status. Observation records retain raw/normalized values, origin (capture, human annotation, synthetic or video prediction), visibility and unknown/ambiguous/unsupported status. Captured engine actions are explicit anchors, never labeled video-inferred actions. |
| Observation adapter / #122, implemented by consuming slice | Enumerated permitted fields, evidence links, interval timing, page/zone/order, visible values and identity hypotheses. Capability audit marks visually observed, tooltip-only, historically inferable or hidden. A raw capture dump is not a video-only input. #82 labels enter through an explicit mapping; synthetic labels and reference data remain separate. |
| Derived state / state reduction | Run-scoped gameplay instances, typed persistent values and valid-time attributes. Definition IDs, visual track IDs and game-instance hypotheses differ. Each value cites observations/rules, confidence basis and missing dependencies. This is the single persistent-state authority, not an oracle projection used as inference. |
| Derived effects / mechanics rules and event inference | Deterministic occurrences: source/target, trigger context, action interval, participation/multiplicity, mutation or money/chips/Mult/XMult contribution, rule revision and evidence. STEP anchors do not enumerate queued engine effects. Effects and state can be joined per step without merging their meanings. |
| Independent reference / #123 capture lead | Raw engine values/identity and resolved timing under pinned revisions, with field-specific suitability. Separate answer-key files/store access; evaluator joins after inference. Defaults, omissions and approximate legality are not exact truth. |
| Queries and evaluation / analytics and evaluation leads | Occurrence details behind aggregates, ownership/round denominators, coverage and contradictions. Direct and upstream lineage views may overlap; deduplicate, never sum them as independent contribution or claim counterfactual benefit. |

Chronological processing distinguishes pre-action state, pending effects and
resolved aftermath. Later evidence may resolve an offline effect but cannot rewrite
an earlier model-visible state. No arbitrary action-space/mask completeness is
required for Dagger analytics; D020/D021 retain reducer ownership of action space
and masks and event-inference ownership of observed action labels.

The boundary extends to cards, consumables, vouchers, attributes, blinds and decks
as bounded slices need them. #129 tests uses/participation/contributions; #130 tests
creation and property-copy lineage. Death copies onto an existing target; uncertain
identity or ancestry stays uncertain. Full family implementations are not implied.

## Isolation And Evaluation

Video-only reduction receives an allowlisted observation artifact, not engine
state, engine IDs, actions or hidden reference fields. Reject forbidden inputs;
changing/removing/poisoning answer-key fields must leave inference unchanged.
Captured-anchor tests are labeled separately from video-only tests. Reference
values may score predictions and identify development gaps, never fill inputs.

Diagnostics identify rule/instance, interval, missing dependency or contradiction,
evidence and affected downstream values/queries. Unknown is not zero. Synthetic
round-trip, user-reviewed video-like fixtures, real-video field accuracy and
engine-reference effect agreement are distinct results. Alignment needs rendered
correspondence, not just timestamp arithmetic. Freeze applicable criteria before
held-out evaluation; D034 first-slice thresholds remain unchanged.

## Implementation Boundaries

Current active surfaces are Showman Capture, Inspector, annotation export and the
local video/action viewer. Mechanics, scene/glyph generation and video inference
are planned; see `ROADMAP.md` for owners and acceptance. The viewer inspects
evidence; it does not reconstruct state or establish alignment automatically.

Canonical coordinates (D007), one shared object/OCR stabilization model and
detect → page/zone → OCR → track → compose remain the visual bootstrap order.
Models use pinned ONNX/ONNX Runtime artifacts and provider tolerance (D017), with
laptop development and compatible batch GPU execution. Storage selection follows
semantics; existing SQLite bundles remain immutable capture boundaries.

Active code must not import from `legacy/`. Consumed assets/models need active
versioned provenance (source/revision/license/retrieval/checksum); unresolved
required inputs block their consuming slice only. Private media and generated
large data stay external. This revision adds no dependency, deployment authority,
CI exception or new recording permission.
