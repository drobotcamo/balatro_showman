---
name: portfolio-state
description: Assess portfolio state and derive one bounded next work item for the existing orchestrator.
---

# Portfolio State

## Authority and entry point

`.opencode/agents/orchestrator.md` remains the sole portfolio authority. This
skill is a procedure used by `/orchestrate`; it does not create another agent,
portfolio authority, or entry point.

## Modes and write boundary

Start in **audit-only mode** unless the orchestrator explicitly selects default
mode. Audit-only mode performs no repository, GitHub, tag, branch, or worktree
writes. Default mode may perform only authorized T0 baton updates, comments,
bounded issue creation, and issue-tag registration through
`python tools/issue_tags.py register <issue-number>`. Never merge, approve,
delete worktrees, change contracts, architecture, phase gates, CI, permissions,
secrets, or durable policy. Missing API data is `unknown`, not `none`.

## Procedure

1. **State snapshot:** inspect issues, PRs and checks, branch/worktrees, and
   `git status`; record timestamps and the selected mode.
2. **Baton audit:** for each open issue, locate its thread, then compare issue,
   branch, worktree, PR, CI, and status claims with repository/GitHub evidence.
   Mark stale, conflicting, blocked, or unknown claims; never resolve a
   conflict by guessing.
3. **Dependency/readiness derivation:** read `ROADMAP.md` gates and open
   questions, issue dependency comments, and baton audits. Produce an ordered
   table of claimable work with the evidence for each dependency.
4. **Duplicate search:** search open issues and PRs by title, tag, scope, and
   linked dependencies before proposing an issue. A similar item is a duplicate
   unless its boundary and dependency are demonstrably distinct.
5. **Bounded issue creation:** only in default mode, recheck the snapshot,
   allocate a unique tag atomically, and create one issue with purpose, scope,
   dependencies, explicit `Done When`, and the T0 boundary. Do not create
   speculative or duplicate issues.
6. **Final recheck:** repeat status, issue/PR, tag, and dependency checks after
   any write. Report failures and uncertainty instead of inferring success.
   This final verification is mandatory, including in audit-only mode.

## Budget

Set finite token and external-action budgets before inspection. Count every
GitHub write, tag allocation, and issue/PR query. Reserve budget for final
verification and reporting; stop before the reserve is consumed. Budget
exhaustion is a reportable blocker, not permission to skip final checks.

## Fixed report

End with exactly one recommendation: continue an in-progress issue, open one
bounded issue, or wait on a user decision. Include **Snapshot**, **Evidence**,
**Work items**, **Baton audit**, **Readiness derivation**, **Actions**,
**Recommendation**, **Uncertainty**, and **Budget**. Include the worktree rule
and exact next command. Audit-only reports must state that no writes occurred.

## Required scenario coverage

The procedure must be checked against healthy continuation, stale/conflicting
batons, blocked issues, eligible issue creation, duplicate suppression, missing
CI, stale worktrees, unavailable tag allocator, and budget exhaustion. A first
live run records runtime skill resolution and evidence in the active baton or
issue comment.
