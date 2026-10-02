---
description: Checkpoint unfinished work for a fresh lead session.
agent: lead
---
Prepare or update `planning/agent-state/threads/<issue-number-or-tag>-<short-name>.md`
following `planning/agent-workflow.md` → Handoff Protocol. Treat the work
item, not the session, as the unit of state. Link the GitHub Issue and PR, if
any. Verify every claim against the repository and git status. Move durable
decisions to `planning/DECISIONS.md` and verified findings to
`planning/LEARNINGS.md`. Do not rewrite unrelated work. Run
`python planning/check_contracts.py`, review the resulting diff, and report
both.

Use the compact unfinished-work format. Record live completion on the existing
PR/issue; historical pre-merge checkpoints do not need settlement repairs.

Handoff context: $ARGUMENTS
