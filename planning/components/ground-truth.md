# Component Contract: Ground Truth and Evaluation

Status: `building`

## Purpose

Produce exact `(state, action, outcome)` records from the game engine via the
Lua live bridge, maintain the aligned real-frame evaluation set, and provide the
minimal annotation/QA tooling the other phase gates depend on.

D028 stages this broad contract through recorded-run inspection, a reviewed
evaluation slice and measured reconstruction. Engine-reference suitability is
field/revision-specific; current defaults/coarse legality are limitations, not
independent proof of engine truth. Broad acceptance below remains an obligation.

## Inputs

- Modded game client and the Lua bridge (Steamodded).
- Human or scripted play sessions.
- Recorded video with timestamps for frame alignment.
- Annotation/QA tool output.

## Outputs

- Ground-truth run records: per-step state, action label, and run outcome.
- Versioned run bundles with active, interrupted, and finalized lifecycle
  states, provenance, integrity metadata, and read-only inspection access
  (Issue #34).
- Raw engine persistent fields and the game's own legal actions/mask basis, as
  the reducer validation reference (D021).
- Aligned video frames for benchmarked steps.
- Evaluation-set manifests with an annotation protocol.
- A minimal annotation/QA tool for real-frame boxes and text fields.

## Invariants

- Ground truth is never synthesized into observed state; it is a separate
  channel used only for validation and outcome labeling.
- The oracle emits raw engine fields and engine legality; it does not compute
  canonical `persistent_state` — the pipeline reducer owns that shape (D021).
- Video-to-engine alignment is explicit and auditable (timestamps, offsets).
- Recording coordination is human-confirmed: a tool may request OBS recording
  and associate its marker, but it never assumes video exists without evidence.
- The run-bundle storage boundary does not own the low-level OBS hook or the
  timestamp-to-frame alignment algorithm.
- Evaluation clips are disjoint from synthetic backgrounds and from training
  video.
- The oracle scores page classification, zone assignment, persistent reduction,
  and event inference; it does not replace them.

## Acceptance Criteria

- The oracle emits aligned steps for at least one full run.
- The eval set has action and field-level ground truth sufficient to compute
  Phase 3-8 metrics.
- The annotation/QA tool can label boxes and text fields on real frames and
  export to the eval manifest format.
- Bounded slices use named criteria in the applicable approved versioned protocol,
  fixed before held-out evaluation. Development pilots may inform that protocol;
  they do not pass the broad Phase 3-8 sufficiency criterion.
