# Agent Operating Contract

This repository is developed by a sequence of human and AI agents. The source
of truth is the checked-in repository, not conversation history.

## First Read

1. Read the relevant `planning/agent-state/threads/<issue-number>-<short-name>.md`
   if present.
2. Read `planning/README.md` and `planning/ROADMAP.md`.
3. Read `planning/DECISIONS.md` and the contract for the component being changed.
4. Read `planning/agent-workflow.md` for session and handoff rules.
5. Inspect the current GitHub Issue, branch, PR, and worktree before editing.
   Preserve changes you did not make.

## Repository Map

- `planning/README.md`: planning index and document map.
- `planning/ROADMAP.md`: phases, statuses, and measurable gates.
- `planning/DECISIONS.md`: durable decisions and open questions.
- `planning/agent-workflow.md`: session, subagent, and handoff procedures.
- `planning/LEARNINGS.md`: verified reusable findings.
- `planning/TOOLING.md`: verified project and machine-specific command recipes.
- `planning/agent-state/`: branch/worktree-scoped work-thread handoffs.
- `.opencode/skills/`: reusable procedures loaded by trigger.
- `.opencode/command/`: workflow commands such as `/resume` and `/handoff`.

## Standard Delivery Workflow

- A GitHub Issue defines each work item, scope, dependencies, and acceptance criteria.
- A dedicated branch and worktree implement the issue.
- One or more agent sessions may continue the same branch and worktree.
- A Pull Request is the review, validation, and integration boundary.
- Local thread files preserve execution context but do not replace Issues or PRs.
- Do not use Markdown files as live locks or as the source of cross-worktree status.
- Agents may create sub-issues and PRs when needed to split work.
- Agents may approve Issues and PRs after checking acceptance criteria and validation;
  the approval must summarize what was checked and remaining uncertainty.
- Agents may merge approved PRs and are encouraged to do so when checks,
  dependencies, and branch targets are correct.

## Project Tenets

- Correctness and provenance come before throughput or impressive demos.
- Contracts, schemas, and phase gates are interfaces between agents.
- Major design decisions require user input before implementation; this includes
  changes to architecture, contracts, project direction, or durable policy.
- Unknown, ambiguous, and low-confidence results are first-class outputs.
- Prefer the smallest change that makes a measurable step toward the current gate.
- Be unafraid to try a different approach when the current approach is stuck,
  while preserving evidence and reporting the change in direction.
- Validate against the Lua oracle or a declared evaluation protocol; inspection
  alone is not sufficient for claims about reconstruction quality.
- Keep laptop development practical while preserving batch-GPU compatibility.
- Record durable decisions in `planning/DECISIONS.md`, not in chat transcripts.
- Do not silently broaden scope, change a contract, or skip a phase gate.

## Completion Standard

Before declaring work complete:

- Run the narrowest relevant tests or checks.
- Report what was changed, what was verified, and what remains uncertain.
- Update the affected planning contract and status when the work changes them.
- Update the relevant work-thread file if another session could need to continue.
- Capture reusable discoveries in `planning/LEARNINGS.md`.

## Safety

Do not commit secrets, generated data, credentials, or unreviewed vendored
artifacts. Do not use destructive git commands to resolve ambiguity. Ask when a
decision changes project direction or invalidates an existing contract.
