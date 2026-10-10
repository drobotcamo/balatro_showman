# Component Contract: Run Mechanics

Status: `designing`

## Purpose

Define the storage-neutral boundary for reconstructing run-scoped instances,
derived state facts, and derived mechanics effects from versioned observations.
The owner-approved v0.1 structural schema and initial examples are described in
`planning/RUN_MECHANICS_DESIGN.md`. The contract remains `designing` pending the
remaining gates below; it does not claim complete mechanics coverage.

## Inputs

- Versioned observations and source step identities from tracking/composition.
- Ontology definitions and class-map version.
- Canonical observed actions and intervals from event inference.
- Persistent-state facts and temporal boundaries from state reduction.
- Separately labeled Lua engine-reference data for validation only.
- Versioned mechanics rules and source-inspected trigger-order evidence.

## Outputs

- Run-scoped instance identities and lifecycle/property history, with explicit
  association status relative to visual tracks.
- Derived state facts with validity, evidence, status, and reproducible provenance.
- Derived effect occurrences, trigger contexts, participants, contributions,
  causal lineage, and queryable interval-wide deltas.
- Structured and readable diagnostics for missing dependencies, unsupported
  rules, and ambiguous identity/timing.
- Query results reporting evidence, status, uncertainty, coverage, and named
  attribution/denominator policies.

## Invariants

- Definitions, run instances, derived state, and derived effects are distinct.
- Visual track IDs are not game-instance IDs without evidence-backed association.
- Raw observations are append-only; derived results are reproducible under
  pinned input and rule versions.
- Observed, inferred, unknown, ambiguous, and unsupported claims remain distinct.
- Engine-reference data cannot be represented as video-observed evidence.
- STEP actions anchor intervals but do not constitute a complete engine trigger
  stream; exact trigger order requires source inspection and owner verification.
- No future observation appears in pre-action model-visible state.
- Persistent mutation, scoring/money contribution, participation, and net delta
  are separately queryable and cannot be silently conflated.
- Unknown dependencies, input gaps, and ambiguous identities never yield
  fabricated exact results.
- Lineage is not a counterfactual-benefit claim; aggregation policies disclose
  deduplication, overlap, unknown coverage, and denominators.

## Acceptance Criteria

- Owner-approved initial Dagger boundary covers positive growth, zero growth,
  missing dependency, scoring effect, and reset examples with explicit
  input-sufficiency boundaries in `planning/RUN_MECHANICS_DESIGN.md`.
- `python planning/mechanics_contract_check.py` accepts the initial synthetic
  fixtures and rejects malformed references, observed/reference mixing,
  forbidden answer-key use, and ambiguous exact timing.
- Run `python planning/mechanics_contract_check.py` successfully; this checks
  structure/references, not game-rule truth.
- Before #129, review Hermit/Mail-In Rebate uses, participation, multiplicity,
  direct contribution and net-delta semantics.
- Before #130, review Certificate → Death → later Gold Seal property history and
  provenance, plus deduplication, overlapping upstream views, and ambiguous
  identity.
- Applicable trigger order is traced against game/mod source and verified by the
  owner before exact-order behavior is claimed; unsupported paths stay explicit.
- Input sufficiency and sell-value derivation are audited per query; unknowns are
  preserved when a particular recording lacks required evidence.
- A versioned evaluation protocol is approved before held-out measurements.
