# Component Contract: Ground Truth and Evaluation

Status: `building`

## Purpose

Produce exact `(state, action, outcome)` records from the game engine via the
Lua live bridge, maintain the aligned real-frame evaluation set, and provide the
minimal annotation/QA tooling the other phase gates depend on.

## Inputs

- Modded game client and the Lua bridge (Steamodded).
- Human or scripted play sessions.
- Recorded video with timestamps for frame alignment.
- Annotation/QA tool output.

## Outputs

- Ground-truth run records: per-step state, action label, and run outcome.
- Aligned video frames for benchmarked steps.
- Evaluation-set manifests with an annotation protocol.
- A minimal annotation/QA tool for real-frame boxes and text fields.

## Invariants

- Ground truth is never synthesized into observed state; it is a separate
  channel used only for validation and outcome labeling.
- Video-to-engine alignment is explicit and auditable (timestamps, offsets).
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
