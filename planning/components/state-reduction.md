# Component Contract: Persistent State, Action Space, and Masks

Status: `planned`

## Purpose

Declare and implement the downstream contract the pipeline targets: reduce the
composed state sequence into persistent state and deterministic legality masks
over the declared action space. This is the interface learning consumes.

## Inputs

- Composed per-frame state sequence.
- Ontology and composition rules.
- Declared downstream contract and action-space version.
- Oracle raw engine persistent fields and engine legal actions, used only to
  validate reduction and masks (D021).

## Outputs

- Persistent state per step (model-visible, per-step observation, and internal
  bookkeeping clearly separated).
- The declared action-space index (the coordinate space the masks index).
- Deterministic legality masks per step.
- Explicit schema and contract versions.
- Mechanics-derived state facts may be consumed through the separate interface
  described in `planning/RUN_MECHANICS_DESIGN.md`; this does not give mechanics
  a competing canonical persistent-state authority.

## Invariants

- Persistent state, per-step observations, and internal bookkeeping are
  distinguishable and versioned; promotion between them is a version bump.
- No future-frame information leaks into a step's state.
- Masks are deterministic for a fixed input and configuration.
- The reducer defines the action-space index and the masks; it does not label
  observed actions. Canonical action labels and `target_action_id` are produced
  by event/action inference (Phase 8, D020).
- Unresolved action labels are emitted as unresolved, never guessed.
- The reducer is the only producer of canonical `persistent_state`; oracle raw
  engine fields and engine legality are validation inputs, never inference
  inputs (D021).
- Mechanics-derived effects remain distinct from persistent state and do not
  weaken the no-future-information invariant.

## Acceptance Criteria

- The reducer reproduces reference persistent state from ground-truth runs
  (oracle raw engine fields projected through the documented reducer mapping;
  D021).
- Masks agree with oracle legal actions on benchmarked steps.
- A consumer can load a step's state plus mask without pipeline internals.
- The contract is either adopted from the published schemas or explicitly
  superseded, with the deviation recorded.
