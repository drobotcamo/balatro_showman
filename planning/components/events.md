# Component Contract: Event and Action Inference

Status: `planned`

## Purpose

Infer meaningful transitions from sequences of reconstructed states without
pretending uncertain actions are known, and validate them against the
ground-truth oracle.

## Inputs

- Versioned state sequence and persistent state (Phase 7).
- State deltas over the composed and reduced state.
- Page/zone transitions.
- The declared action-space index and legality masks (Phase 7).
- Temporal thresholds and event rules.
- Ground-truth oracle records for validation.

## Outputs

- Event type, frame interval, targets, before/after state references, confidence,
  and inference explanation.
- The canonical action label, target, and `target_action_id` for each inferred
  action, indexed within the Phase 7 action space (D020).
- Explicit `unknown` or `ambiguous` events.
- Oracle-agreement reports per event family.
- Action-anchored intervals consumed by mechanics derivation; they do not claim
  to be the complete engine trigger stream. See
  `planning/RUN_MECHANICS_DESIGN.md`.

## Invariants

- Events reference source frames and state versions.
- Rules are deterministic for a fixed input and configuration.
- Event confidence is propagated from detection/OCR/composition confidence, not
  asserted independently.
- No action is inferred solely because it is strategically plausible.
- Cascading error is acknowledged: an event requiring two unreliable state
  deltas cannot be high confidence when either is low confidence.
- Observed action order is distinct from internal trigger order; exact mechanics
  order requires source inspection and owner verification.

## Acceptance Criteria

- Event precision and recall against the Lua oracle meet the Phase 8 threshold
  for buy, sell, skip, reroll, blind, pack, play, and discard.
- Confidence propagation is documented and testable.
- Ambiguous transitions are preserved for later review.
