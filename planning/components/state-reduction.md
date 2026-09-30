# Component Contract: Persistent State, Action Space, and Masks

Status: `planned`

## Purpose

Declare and implement the downstream contract the pipeline targets: reduce the
composed state/event stream into persistent state, map actions into a fixed
action space, and emit legality masks. This is the interface learning consumes.

## Inputs

- Composed per-frame state sequence.
- Event/action sequence.
- Ontology and composition rules.
- Declared downstream contract version.

## Outputs

- Persistent state per step (model-visible, per-step observation, and internal
  bookkeeping clearly separated).
- Action-space mapping and `target_action_id` for each step.
- Legality masks per step.
- Explicit schema and contract versions.

## Invariants

- Persistent state, per-step observations, and internal bookkeeping are
  distinguishable and versioned; promotion between them is a version bump.
- No future-frame information leaks into a step's state.
- Masks are deterministic for a fixed input and configuration.
- Unresolved action labels are emitted as unresolved, never guessed.

## Acceptance Criteria

- The reducer reproduces reference persistent state from ground-truth runs.
- Masks agree with oracle legal actions on benchmarked steps.
- A consumer can load a step's state plus mask without pipeline internals.
- The contract is either adopted from the published schemas or explicitly
  superseded, with the deviation recorded.
