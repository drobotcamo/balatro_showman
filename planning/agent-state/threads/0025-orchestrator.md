# Work Thread
Updated: 2026-09-30
Issue: #25
PR: none yet
Owner: opencode orchestrator bootstrap session (issue-25)
Branch: issue-25-orchestrator
Worktree: `C:\Users\camgr\Documents\code_projects\balatro_showman-orchestrator`
Objective: Add the orchestrator agent and `/orchestrate` command with T0 write authority, primary issue-creation role, codified worktree policy, and mechanical contract validation.
Status: active
Scope: `.opencode/agent/orchestrator.md`, `.opencode/command/orchestrate.md`, `planning/agent-workflow.md`, `planning/README.md`, `planning/DECISIONS.md`, `planning/check_contracts.py`, `planning/LEARNINGS.md`, `planning/agent-state/threads/0025-orchestrator.md`. No producer or pipeline code.
Dependencies: None blocking; builds on Issue #18 reconciliation and D019-D021. Independent of open producer issues #11-#16 and #21.
Completed:
- User-approved design conversation (T1) on 2026-09-30 established: orchestrator procedure (assess, audit handoffs, readiness table, recommend), T0-only write authority, primary issue-creation role, codified worktree rule (T0/planning in-place, T2 dedicated worktree), checker validation.
- Research basis: Anthropic orchestrator-workers and Claude Code session/verification patterns; beads-style computed readiness (see D022 alternatives).
- Created Issue #25 with Work item template; set up dedicated worktree (exercising the T2-style rule even though this item is T0/T1, because the main checkout was occupied by Issue #12).
- Added `.opencode/agent/orchestrator.md` (Procedure, Write Authority, Report Format, Boundaries) and `.opencode/command/orchestrate.md`.
- `planning/agent-workflow.md`: new Orchestrator section; information-layers line updated. `planning/README.md`: `/orchestrate` added to command list.
- `planning/DECISIONS.md`: D022 recorded (accepted) with alternatives.
- `planning/check_contracts.py`: `check_orchestrator()` validates agent sections and command wiring; docstring updated.
- `planning/LEARNINGS.md`: glob tools skipping dot-directories recorded as a reusable failure mode (caused a false missing-`/work` claim earlier this session).
Next:
- Run `py -3 planning/check_contracts.py` and `git diff --check`; open PR; obtain fresh-context `@reviewer` verdict; record it on the PR; merge (T0 auto-PR policy with user-approved T1 content); close Issue #25.
Decisions: D022 added this branch. No other durable changes.
Risks: Orchestrator procedure is untested in a live second session; first real `/orchestrate` run may reveal missing inputs (e.g. CI query recipe) — record follow-ups in LEARNINGS or a new issue rather than editing D022 silently. The `agent/` directory previously held only subagents; a second primary-mode agent is new but matches OpenCode multi-agent config.
Validation: pending (see Next).