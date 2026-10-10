# Component Contract: Analysis and Learning

Status: `planned`

## Purpose

Consume reconstructed state and events for exploration, prediction, and future
agent experiments without making strategy assumptions part of data collection.

## Inputs

- Versioned state and event datasets.
- The declared persistent-state / action-space / mask contract.
- Optional outcome/run metadata, including oracle outcomes.
- Explicit train/validation/test split manifests.
- Mechanics-derived state/effects with status, evidence, provenance, and query
  coverage as specified in `planning/RUN_MECHANICS_DESIGN.md`.

## Outputs

- Descriptive analyses.
- Baseline action models.
- Evaluation reports with coverage and uncertainty.

## Invariants

- Outcomes are optional metadata, not a filter on collection.
- Offline action accuracy is not treated as gameplay competence.
- Reports identify missing state, inferred state, and label leakage.
- Mechanics queries report unknown coverage and the attribution/denominator
  policy; lineage is not presented as counterfactual benefit.
- Outcome-conditioned consumers (e.g. a policy transformer) are optional; the
  pipeline does not require them.

## Acceptance Criteria

- A simple state-to-action baseline can be trained and evaluated by event type
  against the declared contract.
- Analyses can compare behavior without requiring win/loss conditioning.
- Any imitation-learning claim includes an out-of-distribution or rollout test.
