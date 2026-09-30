---
description: Prepare a concise checked-in baton for the next agent session.
agent: build
---

Prepare or update `planning/agent-state/threads/<issue-number>-<short-name>.md` for the next
session. Treat the work item, not the OpenCode session, as the unit of state.
Link the GitHub Issue and PR, if any. Include owner, branch, worktree, objective, status, scope, dependencies,
completed work with evidence, concrete next actions, decisions, risks, and
validation results. Move durable decisions to `planning/DECISIONS.md` and
reusable verified findings to `planning/LEARNINGS.md`. Do not rewrite unrelated
work. Verify every claim against the repository and Git status. Make the next
agent able to continue without chat history: state exactly what to read, what
to verify, and the first action to take. Review the resulting diff and report
it.

User context for this handoff: $ARGUMENTS
