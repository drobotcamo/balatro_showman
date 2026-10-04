# Component Contract: Event and Action Inference

Status: `planned`

## Purpose

Infer actions and mechanics occurrences without treating uncertain transitions as
known. #122 defines shared derived-effect semantics; #124 starts with Dagger.
`planning/ARCHITECTURE.md` separates observations, effects, state and reference;
`planning/RUN_MECHANICS_DESIGN.md` specifies the approved initial mechanics interface.

## Inputs

- Versioned observations and persistent state from the shared reducer.
- State deltas over the composed and reduced state.
- Page/zone transitions.
- The declared action-space index and legality masks (Phase 7).
- Temporal thresholds and event rules.
- Captured action anchors in explicitly labeled capture tests; visual action
  hypotheses in video-only tests. Reference actions/effects go only to evaluation.

## Outputs

- Event type, frame interval, targets, before/after state references, confidence,
  and inference explanation.
- The canonical action label, target, and `target_action_id` for each inferred
  action, indexed within the Phase 7 action space (D020).
- Explicit `unknown` or `ambiguous` events.
- Oracle-agreement reports per event family.
- Derived effect occurrences with source/target/context, participation,
  multiplicity, state mutation or contribution, evidence and deterministic IDs.

## Invariants

- Events reference source frames and state versions.
- STEP anchors are not a complete trigger stream. Queued resolution has an
  explicit interval; stored Mult growth is not scoring Mult contribution.
- #129 extends uses/contributions; #130 adds temporal lineage before those slices
  claim support. Direct/upstream views overlap and do not imply counterfactual gain.
- Rules are deterministic for a fixed input and configuration.
- Event confidence is propagated from detection/OCR/composition confidence, not
  asserted independently.
- No action is inferred solely because it is strategically plausible.
- Cascading error is acknowledged: an event requiring two unreliable state
  deltas cannot be high confidence when either is low confidence.

## Acceptance Criteria

- Bounded mechanics: deterministic occurrences and evidence-linked unknowns;
  missing anchors/aftermath produce actionable diagnostics, not invented effects.
- Broad action scope retains the criteria below; no all-action requirement for
  a validated Dagger mechanics result.
- Event precision and recall against the Lua oracle meet the Phase 8 threshold
  for buy, sell, skip, reroll, blind, pack, play, and discard.
- Confidence propagation is documented and testable.
- Ambiguous transitions are preserved for later review.
