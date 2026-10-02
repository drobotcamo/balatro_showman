# Agent Workflow

Canonical work-item, review, integration and checkpoint rules. `AGENTS.md`
contains the always-applicable tenets; role adapters and commands link here.
D028 supersedes conflicting completion-mirror and mandatory-tag requirements.

## Information Layers

| Information | Authority |
| --- | --- |
| Outcome, acceptance, owner, priority and actual blocker | GitHub issue |
| Diff, validation, reviewed revision, verdict, CI and merge | PR and CI |
| Interfaces, protocols, evidence references and durable decisions | Repository |
| Extra context needed to resume unfinished work | Compact repository checkpoint |

Chat is not the only home for durable evidence. Checkpoints are as-of records,
not live locks or a second task ledger. GitHub completion can supersede a
pre-merge checkpoint without requiring a repair PR. Completed work normally
needs no checkpoint and no post-merge repository edit.

## Work Item Model

An issue owns one observable action/artifact, acceptance command or protocol,
scope boundary, owner and actual prerequisite. Find equivalents before creating
one. Numeric issues and checkpoint filenames are normal; historical four-letter
aliases in `planning/issue-tags.json` remain valid. Allocation is optional.

Use one accountable lead for an agreed outcome. Split only independently useful,
reviewable work or a real external blocker, not design/test/review/settlement
ceremony. One active production outcome is the default; research and review can
run in parallel. Independent implementations need distinct ownership and tests.

Verify the integration branch (currently `master`) rather than assuming `main`.
Use a dedicated branch; planning work may run in-place if ownership and the base
are clear. T2 implementation uses a dedicated worktree. Dependent PRs target the
parent branch and record ordering; verify the intended order before merging.
Do not delete unfamiliar worktrees or discard changes to resolve uncertainty.

## Lead Loop

1. Inspect the agreed issue, PR, branch/worktree and `git status`; read relevant
   checkpoint if present, roadmap gate and component contracts. Preserve unrelated
   work. A ready issue does not require reconstructing the closed portfolio.
2. State observable acceptance, files in scope and narrowest verification.
3. Implement the smallest justified change. Use bounded independent research
   where it resolves uncertainty; keep unknowns explicit.
4. Run relevant checks immediately after meaningful changes. Investigate failures,
   correct narrowly and rerun; do not repeat materially unchanged failures.
   Obtain the tier's approval and fresh review of the current implementation.
5. Integrate when authorized. Verify merge and post completion evidence on the
   same PR/issue; close only when acceptance is addressed or explicitly deferred.
6. If blocked or context-limited, leave one factual unfinished-work checkpoint
   with exact results, ownership exclusions and the requested next action.

For `/work`, ask clarifying questions at most once, then use the narrowest
reasonable assumptions. Do not pause for routine progress or permissions already
granted. Continue through review/publication/integration when in scope and allowed.
A draft, local diff or ready-to-review state is not completion. Report external
blockers instead of inventing success or manufacturing a handoff boundary.

## Orchestrator

Use `/orchestrate` when priority, ownership or dependencies are unresolved, not as
a prerequisite to a ready task. The orchestrator assesses live issue/PR/CI/git
state, reads applicable checkpoints as historical context, derives readiness from
actual prerequisites and recommends one next action/worktree/command.

Its authority remains read-mostly/T0: authorized unfinished-work checkpoints,
issue/PR comments and bounded issue creation. It does not implement pipeline code,
change contracts, merge PRs, adopt policy or waive required review. Missing or
pre-merge checkpoints alone are not corruption or repair work. Do not reopen
accepted historical process gaps without new substantive evidence.

## Subagent Policy

The current lead and orchestrator delegate only to read-only `@explorer` and
`@reviewer`, at depth one. Give a precise question, paths, allowed actions,
excluded data/files, expected evidence and stopping condition. Never delegate
ambiguous integration ownership or reinterpret read-only permissions to allow
fixture writing. The lead executes diagnostics and owns all edits/GitHub writes.

Do not duplicate delegated research; resume the task for follow-up. Returns
include findings/references, changed files (none), checks/output and unresolved
questions. Suggestions are evidence, not decisions. Pause speculative portfolio
or gate-skill expansion during the first two production milestones.

## Approval And Merging

Approval cost scales with blast radius:

- T0: planning/process artifacts, role adapters and templates. PR, local planning
  and diff checks, and required CI; self-merge is allowed without independent review.
- T1: `AGENTS.md`, this workflow, durable decisions, roadmap and component contracts.
  Routine evidence-backed status/sync edits are agent-safe. Substantive interface,
  invariant, gate or policy changes require user approval before implementation.
- T2: code affecting reconstruction output. Dedicated branch/worktree, PR, relevant
  test output, fresh independent reviewer verdict and required CI before merge.
- T3: destructive operations, new dependencies/model weights, CI/required-check,
  branch-protection, permission, credential or deployment changes, or claims with
  no runnable protocol. Specific user decision required; no silent exceptions.

The independent-review rule applies where the tier requires it; it does not
contradict T0 self-merge. This cross-cutting D028 migration requires fresh review.

### Review Evidence

Record once on the current PR: independent reviewer identity/task reference,
reviewed commit SHA, verdict (`holds`, `holds with gaps`, `refuted`), checks and
outputs, material findings/disposition and remaining limits. An owner-posted
comment can preserve an actual independent review. An empty native GitHub reviews
array alone neither proves nor disproves review; the lead's assertion alone is
not independent evidence. Do not paste entire transcripts.

Changing implementation after review requires review of the changed diff/current
SHA. Include intended tracked artifacts before the final reviewed commit, rather
than invalidating review with last-minute checkpoint edits. `holds with gaps` and
`refuted` block merge unless gaps are T0-level or explicitly accepted by the user;
record the exception and evidence. The reviewer supplies a verdict, not policy
authority.

### Integration Evidence

Before merging, verify separately: required CI green for current head, intended
base/current diff, dependency order and current acceptance. No applicable/required
CI result is not a pass: inspect configuration and protection, report the exact
gap and request any policy decision. Never change CI to evade the gate.

After merging, verify the merged commit and record artifact, validation, reviewed
SHA/verdict, merge identity, limits and next production action on the same PR/issue.
No settlement-only follow-up or thread-closing commit is required. Do not infer
approval from merge/green CI; report newly established missing required evidence
without starting a historical cleanup campaign.

## Handoff Protocol

For unfinished work needing fresh context, write
`planning/agent-state/threads/<issue-number-or-tag>-<short-name>.md`:

```markdown
# Work Checkpoint
Updated: YYYY-MM-DD
Issue: #123 or none
PR: #456 or none
Branch: branch-name
Worktree: absolute path
Objective: bounded outcome
Validation: checked revision and exact commands/results
Risks: blocker, uncertainty, ownership exclusions
Next: concrete action and owner
```

Historical full-format records (Owner, Status, Scope, Dependencies, Completed,
Decisions and other fields) remain readable and valid. New compact checkpoints
need a title and every field above; extra historical fields are allowed.
Use `none` for absent issue/PR, not invented identifiers.

Before handoff, inventory `git status`. D027 still requires every owned change,
including the checkpoint, in the PR; remove owned temporary/generated leftovers.
Preserve and identify unrelated pre-existing work. If commit/push/PR publication
is unavailable, preserve work and record exact denied operation, last committed
revision, modified/untracked paths, staged/committed/pushed state and recovery
location. Request the precise D027 exception or missing publication action;
D028 does not waive publication. An unpublished checkpoint is a blocker report,
not a compliant completed handoff.

The next lead rechecks live issue/PR/git state before continuing `Next`. A merged
PR can make a historical checkpoint's next action obsolete without a repair.

## Execution Budgets

Prefer narrow validation and avoid redundant calls. Budgets constrain methods,
not acceptance. At context pressure/compaction warning, stop new exploration,
run the narrow relevant checks, update issue/PR and checkpoint with verified
state, and hand off. Do not silently reduce scope to fit a budget.

## Planning And Contract Updates

Update affected contracts with interface/invariant/status/acceptance changes,
roadmap with gate/ownership changes, durable decisions in `planning/DECISIONS.md`
and reusable verified findings in `planning/LEARNINGS.md` using its format.
Keep unfinished next actions in the checkpoint, live completion in GitHub.

## Safety And Escalation

Do not commit secrets, private/generated data or unreviewed vendored artifacts.
Do not use destructive commands to resolve ambiguity. Stop at scope, permission,
evidence or major-decision conflicts and record the precise blocker; continue
independent approved work. Never relax a contract to make a check pass or guess
human recording confirmation, held-out thresholds or deployment behavior.
