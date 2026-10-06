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
   Search relevant handoffs/worktrees, documented evidence locations and
   existing tools before declaring an input missing or assigning investigation
   to the user. Absence from this checkout is not proof it does not exist.
   Keep the search bounded to the agreed outcome, not an archive-wide audit.
3. Implement the smallest justified change. Use bounded independent research
   where it resolves uncertainty; keep unknowns explicit.
4. Run relevant checks immediately after meaningful changes. Investigate failures,
   correct narrowly and rerun; do not repeat materially unchanged failures.
   Obtain the tier's approval and fresh review of the current implementation.
5. Integrate when authorized. Verify merge and post completion evidence on the
   same PR/issue; close only when acceptance is addressed or explicitly deferred.
6. If only a genuine human/external blocker remains, or context is exhausted
   after independent acceptance work, leave the factual unfinished-work
   checkpoint specified below. A checkpoint resumes this issue; it is not
   completion.

### `/work` Continuation

The assigned issue's complete `Done When` list is the unit of work. After every
meaningful code, review, or integration slice, re-read the list and classify each
criterion as verified, pending, explicitly deferred with user acceptance, or
blocked by a named external action/decision. Continue every pending criterion that
can be advanced safely within this issue's scope. A focused test, partial PR,
reviewer verdict, progress summary, or ordinary tool/step budget is not completion
and does not by itself justify returning control to the user.

When a check fails or a limitation remains, take the next authorized,
evidence-producing action or materially different diagnostic before reporting
an external blocker. Name the unmet claim, next action and owner. Do not ask
the user to search paths, read files, choose agent-solvable technical defaults,
or repeat `continue` for agent-owned work. Present a visual example and short
factual summary when human judgment is actually required. This does not waive
specific approval, the recording-association checkpoint, or safety boundaries.

For `/work`, ask clarifying questions at most once, then use the narrowest
reasonable assumptions. Do not pause for routine progress or permissions already
granted. Continue through validation, current-diff review, publication, required
checks, blocker resolution, merge, and same-issue completion when authorized. The
session's target is a merged issue or one exact human/external action that blocks
the remaining acceptance. A draft, local diff or ready-to-review state is not
completion. Keep remediation within the assigned issue; do not modify unrelated
PRs to make progress look continuous.

### Blocked PRs

A blocked PR requires diagnosis and the next safe remediation action, not a status-
only handoff. Inspect the current head SHA and compare it with the SHA named by
review and checks; any material commit after review requires a fresh review of the
current diff. Inspect the exact failing check, reviewer finding, intended base and
merge conflict, dependency order, required-check applicability, and relevant
permissions. For an independent PR, target the integration branch; for dependent
work, target its declared parent and preserve merge order. Correct a wrong base or
dependency order using the repository's supported rebase/retarget process; do not
force-push or bypass protection. Fix in-scope code/test/review findings, rerun
affected checks, and obtain fresh review after a material diff change. If the
blocker is a genuinely missing external permission, CI-policy decision, secret,
human evidence, or service access, finish independent acceptance work first and
request only that specific action with evidence. Do not repeatedly retry an
unchanged failure or bypass required gates. When a required check is absent,
inspect workflow path filters and branch protection; report the exact gap and
request approval before changing required-check policy. Once the blocker clears,
resume integration and merge without requiring the user to remind the lead.

If new independently deliverable work is needed to finish or safely defer the
assigned outcome, search existing issues first. Create/update one bounded future
issue with owner, outcome, scope, dependencies and `Done When`; obtain fresh
reviewer critique of duplication, completeness and dependency accuracy before
calling it ready. This is an issue-definition quality check, not a new universal
approval tier. Continue the parent issue's remaining acceptance while the future
item is pending; do not create issues for code slices, testing, review, blockers
or settlement ceremony.

### Human Input And Recording Preparation

Before asking for a new recording, inventory candidates and test the specific
unmet evidence claim using `planning/RUN_BUNDLE_OPERATIONS.md`. An existing
video, source segment or bundle must not be called missing solely because it
is outside the current worktree. Do not treat recorder IDs as gameplay runs or
ask the user to resolve their meaning from filenames.

Before asking the user to perform a live recording action, complete the safe,
agent-owned preparation in the existing `planning/TOOLING.md` and
`planning/BRIDGE_SPIKE.md` procedure. Verify the checked-in and installed producer
hashes/build/schema, supported Balatro/Steamodded/Lovely versions, restart need,
OBS hook settings available from configuration, FPS and destination, IO/output
paths and capacity, audit/alignment commands, and fixture/smoke behavior. Inspect
queue evidence without deleting it. Inspect bridge processes before starting one:
reuse a verified healthy expected process or start the documented bridge when no
conflicting process exists and the action is authorized. Never terminate an
existing process, restart the game, or control OBS without the specific required
authorization. A blocker in preparation is diagnosed before asking the user to
debug it; ask only for the precise human action that remains (such as launching a
restarted game and playing the requested states). Group unavoidable live actions
into one concise request after preparation, and resume the same issue to verify
the resulting evidence.

Use accessible configuration/evidence for OBS FPS, destination, and hook settings.
If any required value is unavailable or ambiguous, do not guess or claim capture
readiness. Finish all other preparation, then include the specific missing value
in the minimal user request and do not begin capture until it is confirmed.

Recording does not itself confirm a separate association operation. Only when
explicitly invoking that operation, follow `planning/RUN_BUNDLE_OPERATIONS.md`:
inspect and present the observed run, marker and required/optional status; wait
for explicit `confirm`, `decline`, or `interrupt`; associate only after explicit
confirmation and valid marker evidence. Automatic run intake does not prompt.
For required recording, any non-confirmed result remains `blocked` with
`recording_required` and must not mutate association provenance (D025). The
terminal checkpoint does not start, stop, inspect, or control OBS.

### Context Exhaustion

Genuine context exhaustion is the continuation boundary referenced in Lead Loop
step 6, not issue completion or a reason to silently omit remaining work. Finish
all independent acceptance that fits the session; inventory the complete remaining
criteria; preserve and publish owned work under D027; checkpoint exact verified
state, blockers, paths and next action; and resume the same issue in a fresh lead
session. If publication is unavailable, report exact D027 blocker state without
claiming a compliant published handoff. Do not create a replacement issue or
restart completed slices.

The production lead has no fixed agentic-iteration ceiling: OpenCode's `steps`
setting forces a text-only response when the maximum is reached. Bounded
read-only explorer/reviewer limits remain configured. Removing the arbitrary lead
ceiling does not override provider/context limits or this checkpoint rule.

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

For final-diff review, supply acceptance/exclusions, base/head SHAs, relevant
contracts, check results, limits and inspectable evidence locations. These are
leads, not proof. Review when the candidate diff is ready; after a fix,
resume the same reviewer on the changed diff/current SHA when possible. Linking
evidence in a PR comment does not change the reviewed revision.

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
contradict T0 self-merge.

### Review Evidence

Review the agreed outcome and introduced material defects. A blocker names the
failed criterion or defect, evidence and smallest fix or required proof. Missing
proof for a required claim blocks; inherited issues, optional improvements and
unclaimed/out-of-scope behavior are limits. Verify supplied evidence independently;
challenge unsound scope without inventing criteria.

Use `refuted` for a disproven required claim, `holds with gaps` for an unverified
material claim or blocker, and `holds` when the scope is verified without blockers,
even with named nonblocking limits. The lead fixes blockers, not optional comments.
An accessible but unlinked artifact does not itself require another review round.

Record once on the current PR: independent reviewer identity/task reference,
reviewed commit SHA, verdict (`holds`, `holds with gaps`, `refuted`), checks and
outputs, material findings/disposition and remaining limits. An owner-posted
comment can preserve an actual independent review. An empty native GitHub reviews
array alone neither proves nor disproves review; the lead's assertion alone is
not independent evidence. Do not paste entire transcripts.

Changing implementation after review requires review of the changed diff/current
SHA. Include intended tracked artifacts before the final reviewed commit.
`holds with gaps` and `refuted` block merge unless gaps are T0-level or explicitly
accepted by the user; record the exception and evidence. The reviewer supplies a
verdict, not policy authority.

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
