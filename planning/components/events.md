# Component Contract: Event and Action Inference

Status: `planned`

## Purpose

Infer meaningful transitions from sequences of reconstructed states without
pretending uncertain actions are known, and validate them against the
ground-truth oracle.

## Inputs

- Versioned state sequence.
- Page/zone transitions.
- Temporal thresholds and event rules.
- Ground-truth oracle records for validation.

## Outputs

- Event type, frame interval, targets, before/after state references, confidence,
  and inference explanation.
- Explicit `unknown` or `ambiguous` events.
- Oracle-agreement reports per event family.

## Invariants

- Events reference source frames and state versions.
- Rules are deterministic for a fixed input and configuration.
- Event confidence is propagated from detection/OCR/composition confidence, not
  asserted independently.
- No action is inferred solely because it is strategically plausible.
- Cascading error is acknowledged: an event requiring two unreliable state
  deltas cannot be high confidence when either is low confidence.

## Acceptance Criteria

- Event precision and recall against the Lua oracle meet the Phase 8 threshold
  for buy, sell, skip, reroll, blind, pack, play, and discard.
- Confidence propagation is documented and testable.
- Ambiguous transitions are preserved for later review.
