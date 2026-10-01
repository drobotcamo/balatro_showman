# Agent Operating Contract

This repository is developed by a sequence of human and AI agents. The source
of truth is the checked-in repository, not conversation history.

The project reconstructs Balatro game state from recorded video, validated
against a Lua ground-truth oracle. `planning/README.md` is the planning index.

## Read First

- Resuming work: read the relevant
  `planning/agent-state/threads/<issue-number>-<short-name>.md`.
- Changing a component: read its contract in `planning/components/` first.
- Starting a work item, branching, reviewing, approving, merging, handing off,
  or checkpointing context: follow `planning/agent-workflow.md`. It is the
  single definition of work-item, approval, subagent, and handoff rules; this
  file does not restate them.
- Inspect `git status`, the GitHub Issue, branch, PR, and worktree before
  editing. Preserve changes you did not make.

## Tenets

- Correctness and provenance come before throughput or demos.
- Contracts, schemas, and phase gates are interfaces between agents. Do not
  silently broaden scope, change a contract, or skip a phase gate.
- Major design decisions require user input before implementation.
- Unknown, ambiguous, and low-confidence results are first-class outputs.
- Prefer the smallest change that makes a measurable step toward the current
  gate. When stuck, try a materially different approach, preserve evidence,
  and report the change in direction.
- Validate against the Lua oracle or a declared evaluation protocol;
  inspection alone cannot support claims about reconstruction quality.
- Keep laptop development practical without breaking batch-GPU contracts.
- Record durable decisions in `planning/DECISIONS.md` and verified findings in
  `planning/LEARNINGS.md` — never only in chat.

## Completion Standard

- Run the narrowest relevant tests or checks and report their output.
  Planning documents are mechanically validated by `planning/check_contracts.py`
  (thread naming and handoff fields, decision/learning formats, open-question
  linkage, component sections, roadmap ownership and gates, and reference
  resolution), not for prose quality or gate thresholds.
- Report what changed, what was verified, and what remains uncertain.
- Update the affected contract and work-thread file; capture reusable findings.
- A completion claim requires a runnable check's output or an independent
  fresh-context review (`planning/agent-workflow.md` → Approval).

## Technical Prose

- Apply `.opencode/skill/deslop/SKILL.md` to pull request descriptions, issue
  updates, handoffs, review summaries, and other lengthy technical prose.
- Preserve concrete evidence and uncertainty while removing filler, formulaic
  AI phrasing, and repetitive summaries.
- Submit PR and issue bodies with actual line breaks. Before submission, check
  that literal `\\n` does not appear unless it is intentional code content.
- On PowerShell, avoid nested quoting for substantial multiline GitHub or CLI
  bodies; create a real temporary body file or use a supported heredoc pattern,
  inspect it, and pass it with the command's file option. This prevents shell
  parsing failures and preserves the intended line breaks.

## Safety

- Never commit secrets, credentials, generated data, or unreviewed vendored
  artifacts. Never use destructive git commands to resolve ambiguity.
- Ask the user before changing architecture, contracts, project direction, or
  durable policy.
