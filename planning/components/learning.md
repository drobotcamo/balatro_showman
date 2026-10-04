# Component Contract: Analysis and Learning

Status: `planned`

## Purpose

Consume reconstructed state and events for exploration, prediction, and future
agent experiments without making strategy assumptions part of data collection.
Deep mechanics analytics is an early product (#124/#129/#130), not postponed until
action modeling or full video reconstruction. See `planning/ARCHITECTURE.md` and
`planning/RUN_MECHANICS_DESIGN.md`.

## Inputs

- Versioned state and event datasets.
- The declared persistent-state / action-space / mask contract.
- Optional outcome/run metadata, including oracle outcomes.
- Explicit train/validation/test split manifests.
- Derived state/effect occurrences and evidence-linked coverage; isolated
  reference comparisons validate inputs but cannot be counted as inferred results.

## Outputs

- Descriptive analyses.
- Baseline action models.
- Evaluation reports with coverage and uncertainty.

## Invariants

- Outcomes are optional metadata, not a filter on collection.
- Offline action accuracy is not treated as gameplay competence.
- Reports identify missing state, inferred state, and label leakage.
- Unknown rounds/amounts are not zero; state growth, scoring contribution and net
  interval delta differ. Reports state ownership/round denominators and weighting.
- Direct versus upstream lineage views are deduplicated and never claimed as
  counterfactual benefit; occurrence evidence is accessible behind aggregates.
- Outcome-conditioned consumers (e.g. a policy transformer) are optional; the
  pipeline does not require them.

## Acceptance Criteria

- Dagger: evidence-linked per-round stored-Mult growth graph and reproducible
  average/coverage calculation, including zero-gain and unresolved ownership rounds.
- Later bounded queries: Hermit/Rebate contributions and Certificate/Death/Gold
  Seal lineage under their approved protocols, without a full registry prerequisite.
- For optional learning scope, a state-to-action baseline is evaluated by event
  type against the declared contract.
- Analyses can compare behavior without requiring win/loss conditioning.
- Any imitation-learning claim includes an out-of-distribution or rollout test.
