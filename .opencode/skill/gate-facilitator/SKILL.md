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
   and dataset contracts, applicable unfinished-work checkpoints, and the
   versioned protocol for the actual gate/slice and evidence revision.
2. Refuse to conclude `pass` when the protocol is absent, incomplete,
   contradictory, unversioned, or does not identify criteria, thresholds,
   evidence schema, statuses, authority, report location, and sendback rules.
   Record `blocked` or `unknown` and the missing protocol fields instead.
3. Pin repository revision, protocol revision, evidence identities, and the
   report destination before collecting rows. Missing identity is a gap, not a
   pass.
4. Verify the protocol identifies the requested gate/slice, supported scope and
   applicable evidence revision. A valid protocol for another slice/revision is
   inapplicable, not a pass. Criteria must be approved before held-out evaluation.

## Evidence collection

Walk one row at a time. Ask for the evidence location, revision/hash/run
identity, timestamp, verification command and output, owner, status, gaps,
sendback owner, recheck, and the required human decision. Do not infer labels
from filenames, repository presence, oracle output, or a prior report.

Derive named required rows from that applicable approved protocol. Record its
identity and each criterion ID rather than unexplained positional rows. Retain
applicable ownership, alignment, disjoint evaluation, required-artifact provenance
and integrity obligations; future Phase 1-10 thresholds are not unconditional
prerequisites for a bounded slice (D028). Deferred broader criteria remain open.

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
runs with identical inputs should produce identical conclusions and row content
apart from explicitly declared report metadata. `fixtures/cases.json` and
`tests/test_gate_fixtures.py` check a declared classification model and fixture
identities/refusal cases, not actual agent execution or determinism. Independently
review the tabletop/live report before claiming gate acceptance.
