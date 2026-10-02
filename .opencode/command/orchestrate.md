---
description: Orchestrate the portfolio: assess state, audit handoffs, recommend the next work item.
agent: orchestrator
skill: portfolio-state
---
Act as the orchestrator for this session: $ARGUMENTS

Follow the orchestrator procedure in your agent instructions: state
assessment, handoff audit, readiness table, then a recommendation ending with
which issue to continue or `/work` next, the worktree decision with its
applicable rule, and the exact command to run. Follow `planning/agent-workflow.md`.
Use this assessment when selection/ownership/dependencies are unresolved.
Checkpoints are historical context, not completion mirrors; do not repair closed
batons solely because GitHub completed later. Keep authorized writes T0-only.
