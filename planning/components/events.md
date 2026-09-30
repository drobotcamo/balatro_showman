# Component Contract: Event and Action Inference

Status: `planned`

## Purpose

Infer meaningful transitions from sequences of reconstructed states without
pretending uncertain actions are known.

## Inputs

- Versioned state sequence.
- Temporal thresholds and event rules.
- Optional human annotations or input logs.

## Outputs

- Event type, frame interval, targets, before/after state references, confidence,
  and inference explanation.
- Explicit `unknown` or `ambiguous` events.

## Invariants

- Events reference source frames and state versions.
- Rules are deterministic for a fixed input and configuration.
- Event confidence is separate from object confidence.
- No action is inferred solely because it is strategically plausible.

## Acceptance Criteria

- High-confidence buy, sell, skip, reroll, blind, pack, play, and discard cases
  are evaluated on real clips.
- Ambiguous transitions are preserved for later review.
