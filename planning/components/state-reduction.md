# Component Contract: Derived Run State, Action Space, and Masks

Status: `planned`

## Purpose

Reduce permitted observations into evidence-linked persistent gameplay state for
mechanics analytics now and video reconstruction later. Dagger (#124) is the first
slice under #122; `planning/ARCHITECTURE.md` defines the shared boundary. The full
action-space/mask interface remains a consumer target, not a Dagger prerequisite.

## Inputs

- Allowlisted captured or video-derived observations, with origins and evidence;
  composed per-frame state is the visual adapter's source.
- Ontology and composition rules.
- Declared downstream contract and action-space version.
- Independent engine persistent fields and legal actions go to the isolated
  evaluator only, not the reducer (D021).

## Outputs

- Persistent state per step (model-visible, per-step observation, and internal
  bookkeeping clearly separated).
- The declared action-space index (the coordinate space the masks index).
- Deterministic legality masks per step.
- Explicit schema and contract versions.
- Run-scoped instance hypotheses, valid-time values/attributes and unknowns;
  state links to derived effect occurrences without becoming a second effect store.

## Invariants

- Persistent state, per-step observations, and internal bookkeeping are
  distinguishable and versioned; promotion between them is a version bump.
- No future-frame information leaks into a step's state.
- Pre-action, pending and resolved state differ. Definition, visual track and
  gameplay instance identity are distinct; engine IDs cannot seed video inference.
- Masks are deterministic for a fixed input and configuration.
- The reducer defines the action-space index and the masks; it does not label
  observed actions. Canonical action labels and `target_action_id` are produced
  by event/action inference (Phase 8, D020).
- Unresolved action labels are emitted as unresolved, never guessed.
- The reducer is the only producer of canonical `persistent_state`; oracle raw
  engine fields and engine legality are validation inputs, never inference
  inputs (D021).

## Acceptance Criteria

- First slice: deterministic Dagger positive/zero/incomplete scenarios, separate
  stored Mult and sacrifice effects, isolated reference comparison and diagnostics
  identifying missing dependencies and downstream invalidation. #127 checks the
  same reducer with restricted inputs and reference perturbation.
- Broader action/mask acceptance below applies when that scope is implemented;
  neither exhaustive Joker coverage nor full video inference blocks slice delivery.
- The reducer reproduces reference persistent state from ground-truth runs
  (oracle raw engine fields projected through the documented reducer mapping;
  D021).
- Masks agree with oracle legal actions on benchmarked steps.
- A consumer can load a step's state plus mask without pipeline internals.
- The contract is either adopted from the published schemas or explicitly
  superseded, with the deviation recorded.
