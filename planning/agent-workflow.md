# Agent Workflow

Single definition of session, work-item, subagent, approval, and handoff
rules. `AGENTS.md` holds the always-applicable tenets and points here; no
other document restates these rules — they link to this one.

## Information Layers

- `AGENTS.md`: short, always-applicable operating rules.
- `planning/README.md`, `ROADMAP.md`, and component contracts: current product
  and engineering intent.
- `planning/DECISIONS.md`: durable decisions and open questions.
- `planning/LEARNINGS.md`: reusable findings, failure modes, and techniques.
- `planning/TOOLING.md`: verified project and machine-specific command recipes.
- `planning/agent-state/threads/<issue-number-or-tag>-<short-name>.md`: a work-thread
  baton that can be continued by multiple sessions on the same branch/worktree.
- `.opencode/agents/`: configured agents, including the orchestrator and the
  per-work-item lead; `.opencode/command/`: workflow commands; `.opencode/skill/`:
  triggered procedures.
- Chat: temporary interaction, never the only place a conclusion exists.

## Work Item Model

GitHub is the coordination authority for parallel work:

- An Issue defines a bounded outcome, scope, dependencies, and `Done When`,
  using the Work item issue template. An Issue is complete only when its
  deliverables are merged or explicitly deferred, its acceptance criteria are
  addressed, and remaining uncertainty is recorded. Abandoned or superseded
  work is closed with a reason.
- New issues receive a unique immutable four-letter tag recorded in
  `planning/issue-tags.json`. Use `TAG (#N)` in new references; numeric issue
  references and historical numeric thread filenames remain valid.
- A dedicated branch and worktree implement the Issue; one or more agent
  sessions may continue the same branch and worktree.
- A Pull Request is the review, validation, and merge boundary for all work:
  T0 auto-PRs merge without review once required CI is green; T1–T2 require
  the evidence in Approval And Merging.
- Thread files supplement the Issue with session-level execution context; they
  are not live locks. GitHub Issue, branch, and PR state are the cross-worktree
  coordination authority. Never use Markdown as a concurrency lock.
- Agents may create sub-issues when work becomes independently reviewable,
  parallelizable, blocked, or too broad — never for ceremony. A sub-issue
  links to its parent and states whether it blocks, supports, or informs it.
- Independent work branches from the integration branch, normally `main`.
  Dependent work branches from the parent branch and its PR targets that
  parent. For stacked PRs, merge the child into its parent first, then
  retarget or rebase and merge the parent.
- Clean up merged worktrees when practical, but never delete a worktree to
  resolve uncertainty or discard unreviewed changes.
- Major design decisions require user input before implementation. Surface
  alternatives, tradeoffs, and a recommendation rather than silently choosing
  a new architecture or contract.

## Orchestrator

The orchestrator (`../.opencode/agents/orchestrator.md`, invoked via
`/orchestrate`) owns portfolio state, not a single work item:

- Its procedure is fixed: state assessment (issues, PRs, CI, git, worktrees),
  handoff audit (verify thread-baton claims against repository evidence),
  readiness table (derived from issue dependencies and the ROADMAP open
  questions and gates), and a recommendation ending in continue/open Issue
  #N, a worktree decision, and the exact command to run.
- Its write authority is T0 only: thread batons, closing stale threads, issue
  and PR comments, and creating issues or sub-issues. It is the primary issue
  creator; workers may still propose sub-issues per the Work Item Model. It
  never edits pipeline code, never merges PRs, and is never the sole approver
  of its own changes.
- Worktree selection is codified, not judged: T0/planning issues may run
  in-place when the main checkout is free (precedent: Issue #18); T2 pipeline
  issues get a dedicated worktree branched from the integration branch. The
  orchestrator reports which rule applies and flags stale merged worktrees
  without deleting them.
- Its agent file and command are mechanically validated by
  `planning/check_contracts.py`.

## Session Start

1. Identify the GitHub Issue, branch, worktree, and PR, if one exists.
2. Inspect `git status` and identify unrelated work; do not revert it.
3. Read the relevant thread file, roadmap phase, and component contract.
4. Restate the Issue's acceptance criteria as a bounded outcome and identify
   validation.
5. Use subagents for independent research or review, not for ambiguous
   ownership.

## `/work` Execution Rule

- Ask the user clarifying questions at most once per `/work` invocation. If the
  user does not answer, or ambiguity remains after that question, make the
  narrowest reasonable assumptions, record them, and attempt the task in one
  continuous pass.
- Do not stop at a draft, local diff, or proposed PR when the task is
  actionable. Carry the work through validation, an approved PR, merge, and
  settled/closed work-item state whenever repository and GitHub permissions
  allow it. Report any permission or external blocker explicitly rather than
  treating it as completion.
- Conclude every `/work` invocation with exactly one of two explicit outcomes:
  (1) a verified handoff intended for another agent because the session has
  continued long enough to warrant a fresh context, or (2) a completed thread,
  meaning the PR has been opened, required checks are green, the required review
  or approval evidence is present, and the PR and work item are merged and
  settled.
  A local diff, draft PR, or "ready" status is not a third outcome.
- Record verified findings that are likely to save a future agent time,
  repeated investigation, or avoidable frustration in `planning/LEARNINGS.md`.
  Include the context, observation, implication, and verification/source; do
  not record generic advice or unverified speculation. Keep session-specific
  next actions in the thread baton instead.

## Subagent Policy

- A subagent receives a precise question, relevant paths, constraints, and a
  requested output format.
- Prefer read-only exploration/review subagents (`@explorer`, `@reviewer`).
  Grant editing ownership only when the file set and acceptance criteria are
  explicit.
- Do not duplicate an active subagent's work. Resume its task when follow-up
  is needed rather than starting a competing investigation.
- Treat subagent output as evidence to inspect, not as an automatic decision.
- A subagent must return findings, changed files, checks run, and unresolved
  questions. The parent agent owns integration and final verification.

## Agent Purposes And Evidence

An Issue or sub-issue should make its purpose clear. Common purposes:
`explore` (findings, sources, unresolved questions), `design` (alternatives,
tradeoffs, recommendation), `implement` (scoped diff), `test` (reproducible
commands and results), `evaluate` (metrics, protocol, uncertainty), `review`
(findings with file/line references), `integrate` (branch, CI, approval,
merge verification), `document` (consistency and reference checks), `operate`
(configuration, provenance, failure handling).

Agents do not all need the same proof: they need evidence appropriate to the
work they were asked to perform.

## Approval And Merging

Approval cost scales with blast radius. Tiers:

- **T0 — planning/process artifacts**: thread files, `LEARNINGS.md`,
  `TOOLING.md`, `.opencode/` configs and agents, `.github/` templates, and
  planning prose that is not listed under T1. The agent opens a PR and merges
  it itself once required CI is green (no review required). Required
  evidence: `planning/check_contracts.py` passes locally, `git diff --check`
  is clean, and the PR's required CI check passes. Required status checks
  mechanically block direct pushes to protected branches (GH006), so T0
  always travels as an auto-PR.
- **T1 — contracts and durable decisions**: `AGENTS.md`,
  `planning/agent-workflow.md`, `planning/DECISIONS.md`, `ROADMAP.md`, and
  `planning/components/*`. Agent-safe only for routine status flips backed by
  gate evidence and formatting/sync edits. Substantive edits (interfaces,
  invariants, acceptance criteria, new durable decisions) require user
  approval; propose with alternatives and a recommendation.
- **T2 — pipeline code**: anything affecting reconstruction output. Branch
  and worktree per Issue, PR, pasted output of the narrowest relevant tests,
  an `@reviewer` fresh-context verdict recorded on the PR, and required CI
  green. The agent merges when all are satisfied.
- **T3 — irreversible or unverifiable**: destructive operations, dependency
  and model-weight additions, CI/permission changes, claims without a runnable
  protocol. Explicit user decision, no exceptions.

Rules common to all tiers:

- An agent must not be the sole approver of its own changes. Approval is a
  derived state backed by the tier's evidence; the acting agent records it on
  the PR or issue: what was checked, check outputs, reviewer verdict, and
  remaining uncertainty. Never chat-only.
- `@reviewer` returns a verdict (`holds` | `holds with gaps` | `refuted`); it
  does not approve. `refuted` or `holds with gaps` blocks merge unless the
  gaps are T0-level or the user accepts them explicitly.
- Approval and merge are separate checks. Before merging, verify the PR still
  targets the intended branch, required checks pass, dependent PRs are in the
  correct order, and no newer conflicting work changed the acceptance
  criteria. Merge approved PRs rather than leaving integration work idle.

## Handoff Protocol

Write or update `planning/agent-state/threads/<issue-number>-<short-name>.md`
before stopping, compacting, or handing work to another session. A thread
represents a bounded work item, not an OpenCode session. Multiple sessions may
continue one thread. Keep it factual and short; delete stale claims — it is a
baton, not a diary:

```markdown
# Work Thread
Updated: YYYY-MM-DD
Issue: #123 or none
PR: #456 or none
Owner: session or agent label
Branch: branch-name
Worktree: worktree-name or path
Objective: one sentence
Status: active | blocked | ready-for-review | complete | abandoned
Scope: files and component
Dependencies: blocking issues, contracts, decisions
Completed: bullets with evidence
Next: ordered, concrete actions
Decisions: decisions made or links to DECISIONS.md
Risks: uncertainty, failed checks, or conflicting work
Validation: commands and results
```

The next session acts from this file plus the referenced contracts: read the
thread, inspect the Issue, branch, worktree, and PR, verify the claims against
the repository, and continue from `Next` rather than reconstructing the task
from chat history. Move durable lessons to `LEARNINGS.md` and durable
decisions to `DECISIONS.md`.

## Context Checkpoint

Context pressure is the primary handoff trigger. When the agent can see a
session is approaching roughly 50% context usage, checkpoint rather than
accumulate history; the first compaction warning or clear loss of earlier
context is the hard trigger (percentage visibility varies by harness).

At a checkpoint, the agent must:

1. Update the linked Issue and PR with durable progress.
2. Verify the worktree and record its branch and current status.
3. Update the thread file using the handoff template.
4. Move durable decisions to `DECISIONS.md` and reusable findings to
   `LEARNINGS.md`.
5. Run the narrowest relevant validation, or record why it cannot run.
6. Stop starting new exploratory work and hand off to a fresh session.

Handoff is part of completion. Do not declare unfinished work complete without
either finishing it or leaving this verified handoff.

## Planning And Contract Updates

- Update the affected component contract in the same PR when its interface,
  invariants, status, or acceptance criteria change.
- Update `ROADMAP.md` when phase status, gates, or ownership change.
- Record durable choices and open questions in `DECISIONS.md`; verified
  findings in `LEARNINGS.md`; verified command recipes in `TOOLING.md`.
- Do not silently edit a contract to make an implementation pass; surface the
  conflict in the Issue and request user input for a major design change.
- If two agents discover conflicting assumptions, stop implementation at the
  conflict boundary and create or update an Issue rather than reconciling it
  in chat only.

## Safety And Escalation

- Never commit secrets, credentials, private data, generated data, or
  unreviewed vendored artifacts unless the Issue explicitly makes them
  versioned outputs.
- Do not use destructive commands to resolve ambiguity; preserve evidence.
- If blocked by missing access, assets, hardware, external behavior, or a
  conflicting Issue, record the blocker in GitHub and the thread file.
- When an approach is stuck, try a materially different approach rather than
  repeating the same failed path; record what failed, what changed, and the
  evidence that motivated the change.
- Escalate when the next step would broaden scope, invalidate a phase gate, or
  require an unapproved durable decision.

## Learning Rule

Record a learning when it is likely to prevent repeated investigation or
change future implementation. Include context, observation, implication, and
source or verification. Do not record generic advice or unverified
speculation.
