---
name: gate-facilitator
description: Facilitate a human-confirmed Phase 0 gate decision from versioned evidence without mutating evidence or approving the gate.
---

# Phase 0 Gate Facilitator

Use this skill only for a bounded, read-only review of the Phase 0 gate. The
orchestrator remains portfolio authority and the named human gate authority
owns acceptance. This skill never edits source evidence, contracts, roadmap,
decisions, run bundles, issues, or gate status.

## Preflight

1. Read `planning/ROADMAP.md`, `planning/PHASE0_INVENTORY.md`, the ground-truth
   and dataset contracts, the active dependency batons, and the versioned Phase
   0 protocol.
2. Refuse to conclude `pass` when the protocol is absent, incomplete,
   contradictory, unversioned, or does not identify criteria, thresholds,
   evidence schema, statuses, authority, report location, and sendback rules.
   Record `blocked` or `unknown` and the missing protocol fields instead.
3. Pin repository revision, protocol revision, evidence identities, and the
   report destination before collecting rows. Missing identity is a gap, not a
   pass.

## Evidence collection

Walk one row at a time. Ask for the evidence location, revision/hash/run
identity, timestamp, verification command and output, owner, status, gaps,
sendback owner, recheck, and the required human decision. Do not infer labels
from filenames, repository presence, oracle output, or a prior report.

The matrix must contain separate rows for:

- output ownership and meaning;
- an aligned oracle run;
- a disjoint real-frame evaluation set;
- active asset and weight provenance;
- Phase 1–10 thresholds; and
- cross-cutting evidence integrity.

Allowed row results are `pass`, `sendback`, `blocked`, and `unknown`. Preserve
`missing`, `unsupported`, `occluded`, and `ambiguous` evidence states where
provided. A stale hash, conflicting evidence, absent verification output, or
insufficient support is not a pass.

## Classification and report

Produce a versioned report at the protocol-defined location containing:

- repository and protocol revisions;
- the complete row-level matrix and exact evidence references;
- commands and captured outputs, owners, timestamps, and identity hashes;
- explicit human decisions, unresolved uncertainty, sendbacks, blockers, and
  next actions; and
- the final classification.

`pass` requires every required row to pass, reproducible evidence, explicit
decisions, and recorded acceptance by the named human authority. `sendback`
means an actionable nonconformance without an external blocker. `blocked`
means missing authority, access, evidence, or a policy decision. `unknown`
means evidence is insufficient, stale, contradictory, or unverifiable.
Missing human acceptance is `decision_pending`, never approval. Any unresolved
`blocked`, `unknown`, or `decision_pending` state prevents `pass`.

Threshold, contract, licensing, or policy changes are requests for the owning
human/issue; do not edit the governing document to make a row pass.

## Safety and determinism

Do not capture, annotate, train, promote assets, mutate run bundles, or create,
close, or update issues. Do not approve this skill or close Phase 0. Repeated
runs with identical inputs must produce identical conclusions and row content
apart from explicitly declared report metadata. Use the fixtures in
`fixtures/` to exercise the refusal and classification paths before using real
evidence.
