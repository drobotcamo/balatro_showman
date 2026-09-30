# Agent Workflow

## Information Layers

- `AGENTS.md`: short, always-applicable operating rules.
- `planning/README.md`, `ROADMAP.md`, and component contracts: current product
  and engineering intent.
- `planning/DECISIONS.md`: durable decisions and open questions.
- `planning/LEARNINGS.md`: reusable findings, failure modes, and techniques.
- `planning/agent-state/threads/<issue-number>-<short-name>.md`: a work-thread baton that can be
  continued by multiple sessions on the same branch/worktree.
- `.opencode/skills/`: procedural knowledge that should be loaded for a trigger.
- Chat: temporary interaction, never the only place a conclusion exists.

## Work Item Model

GitHub is the coordination authority for parallel work:

- An Issue defines the work item, scope, dependencies, and acceptance criteria.
- A branch and dedicated worktree implement the Issue.
- A Pull Request is the review, validation, and merge boundary.
- A thread file supplements the Issue with session-level execution context.
- Agents may create sub-issues and PRs when the work requires them.
- Agents may approve Issues and PRs when the stated acceptance criteria and
  validation are satisfied; approval must state what was checked and any
  remaining uncertainty.
- Agents may merge approved PRs and should do so when integration checks,
  dependencies, and branch targets are correct.
- Major design decisions require user input before implementation. Agents should
  surface alternatives, tradeoffs, and a recommendation rather than silently
  choosing a new architecture or contract.
- When an approach is stuck, try a materially different approach rather than
  repeating the same failed path; record the failed path and new evidence.

Use `planning/agent-state/threads/<issue-number>-<short-name>.md` when a thread
needs a durable handoff. Include links or identifiers for the Issue and PR,
plus the branch and worktree. Do not use local Markdown as a concurrency lock.

The detailed approval policy is tracked in GitHub Issue #1. Until it is
fully defined, agents must not approve their own unreviewed changes solely
because their implementation appears complete; they should request a separate
review agent or human review when no independent validation is available.

Approval and merge are separate checks. Before merging, verify that the PR is
still based on the intended target, required checks pass, dependent PRs are in
the correct order, and no newer conflicting work has changed the acceptance
criteria. Merge approved PRs rather than leaving integration work idle. For
stacked PRs, merge the child into its parent first, then retarget or rebase and
merge the parent into the integration branch.

## Work Item Lifecycle

1. An Issue defines a bounded outcome, scope, dependencies, and `Done When`.
2. The implementing agent creates or uses a dedicated branch and worktree.
3. The agent may create sub-issues when work becomes independently reviewable,
   parallelizable, blocked, or too broad. Dependent sub-issues use stacked PRs.
4. A PR links the Issue, records evidence, and is reviewed against its criteria.
5. An agent approves when the criteria and appropriate evidence are satisfied.
6. An agent merges an approved PR when checks, dependencies, and branch targets
   are correct, then closes or updates the Issue.

An Issue is complete only when its required deliverables are merged or
explicitly deferred, its acceptance criteria are addressed, and remaining
uncertainty is recorded. Abandoned or superseded work is closed with a reason.

Use a dense Issue format:

```markdown
## Goal
One sentence describing the outcome.

## Scope
What this Issue owns, including exclusions.

## Done When
- [ ] Observable result
- [ ] Required evidence

## Context
Dependencies, decisions, risks, or parent Issue.
```

Agents should create sub-issues when work becomes independently reviewable,
parallelizable, blocked, or too broad. A sub-issue links to its parent and states
whether it blocks, supports, or informs it. Do not split work merely for
ceremony.

## Worktrees And Branches

- Use one worktree per active Issue and one branch per worktree.
- Prefer `agent/<issue-number>-<short-name>` for branch names.
- Independent work branches from the integration branch, normally `main`.
- Dependent work branches from the parent branch and its PR targets that parent.
- Merge stacked child PRs before merging the parent PR to the integration branch.
- Inspect `git status`, branch, and PR state before editing or merging.
- Do not commit generated data, credentials, local caches, or machine-only
  artifacts unless the Issue explicitly makes them versioned outputs.
- Clean up merged worktrees when practical, but never delete a worktree to
  resolve uncertainty or discard unreviewed changes.

Worktree files and thread files are not live locks. GitHub Issue, branch, and PR
state are the cross-worktree coordination authority.

## Session Start

1. Identify the GitHub Issue, branch, worktree, and PR, if one exists.
2. Inspect `git status` and identify unrelated work; do not revert it.
3. Read the relevant thread file, roadmap phase, and component contract.
4. Restate the Issue's acceptance criteria as a bounded outcome and identify validation.
5. Use subagents for independent research or review, not for ambiguous ownership.

## Subagent Policy

- A subagent receives a precise question, relevant paths, constraints, and a
  requested output format.
- Prefer read-only exploration/review subagents. Grant editing ownership only
  when the file set and acceptance criteria are explicit.
- Do not duplicate an active subagent's work. Resume its task when follow-up is
  needed rather than starting a competing investigation.
- Treat subagent output as evidence to inspect, not as an automatic decision.
- A subagent must return findings, changed files, checks run, and unresolved
  questions. The parent agent owns integration and final verification.

## Agent Purposes And Evidence

An Issue or sub-issue should make the current purpose clear. Common purposes
include:

- `explore`: findings, sources, and unresolved questions.
- `design`: alternatives, tradeoffs, recommendation, and user input when major.
- `implement`: focused checks and a scoped diff.
- `test`: reproducible commands and results.
- `evaluate`: metrics, comparison protocol, and uncertainty.
- `review`: concrete findings with file or line references.
- `integrate`: branch, dependency, CI, approval, and merge verification.
- `document`: consistency and reference checks.
- `operate`: configuration, outputs, provenance, and failure handling.

Agents do not all need the same proof. They need evidence appropriate to the
work they were asked to perform.

## Handoff Protocol

Write or update `planning/agent-state/threads/<issue-number>-<short-name>.md` before stopping,
compacting, or handing work to another session. A thread represents a bounded
work item, not an OpenCode session. Multiple sessions may continue one thread.
Keep it factual and short:

```markdown
# Work Thread
Updated: YYYY-MM-DD
Issue: #123
PR: #456 or none
Owner: session or agent label
Branch: branch-name
Worktree: worktree-name or path
Objective: one sentence
Status: active | blocked | ready-for-review | complete | abandoned
Scope: files and component
Completed: bullets with evidence
Next: ordered, concrete actions
Decisions: decisions made or links to DECISIONS.md
Risks: uncertainty, failed checks, or conflicting work
Validation: commands and results
```

The next session should be able to act from this file plus the referenced
contracts. Delete stale claims; do not accumulate a diary here. These files are
not live locks: coordinate parallel worktrees with branch names, Git status, and
PR state. Move durable lessons to `planning/LEARNINGS.md` and durable decisions
to `DECISIONS.md`.

## Context Checkpoint

Context pressure is the primary handoff trigger. When the agent can see that a
session is approaching roughly 50% context usage, it should checkpoint rather
than accumulate more conversational history. Exact percentage visibility varies
by OpenCode version, so the first compaction warning or clear loss of earlier
context is the hard trigger.

At a context checkpoint, the agent must:

1. Update the linked Issue and PR with durable progress.
2. Verify the worktree and record its branch and current status.
3. Update the thread file using the handoff template above.
4. Move durable decisions to `DECISIONS.md` and reusable findings to
   `LEARNINGS.md`.
5. Run the narrowest relevant validation, or record why it cannot run.
6. Stop starting new exploratory work and hand off to a fresh session.

Handoff is part of completion. An agent must not declare unfinished work
complete without either finishing it or leaving this verified handoff.

The handoff must tell the next agent to read the thread, inspect the linked
Issue, branch, worktree, and PR, verify the claims against the repository, and
continue from `Next` rather than reconstructing the task from chat history.

## Planning And Contract Updates

- Update the relevant component contract in the same PR when its interface,
  invariants, status, or acceptance criteria change.
- Update `ROADMAP.md` when phase status, gates, or ownership changes.
- Record durable choices and unresolved questions in `DECISIONS.md`.
- Record verified reusable findings in `LEARNINGS.md`.
- Record verified command recipes in `TOOLING.md`.
- Do not silently edit a contract to make an implementation pass; surface the
  conflict in the Issue and request user input for a major design change.
- If two agents discover conflicting assumptions, stop implementation at the
  conflict boundary and create or update an Issue rather than reconciling it in
  chat only.

## Safety And Escalation

- Never commit secrets, credentials, private data, or unreviewed vendored code.
- Do not use destructive commands to resolve ambiguity. Preserve evidence and
  ask for direction when a command could discard work.
- Treat unknown, ambiguous, and low-confidence results as explicit outputs.
- Ask the user before changing architecture, contracts, project direction, or
  durable policy.
- If blocked by missing access, assets, hardware, external behavior, or a
  conflicting Issue, record the blocker in GitHub and the thread file.
- If an approach is stuck, try a materially different approach and record what
  failed, what changed, and what evidence motivated the change.
- Escalate when the next step would broaden scope, invalidate a phase gate, or
  require an unapproved durable decision.

## Learning Rule

Record a learning when it is likely to prevent repeated investigation or change
future implementation. Include context, observation, implication, and source or
verification. Do not record generic advice or unverified speculation.
