---
name: project-memory
description: Maintain project decisions, learnings, and agent handoffs. Use when work changes a contract, reveals a reusable finding, or a session is ending.
---

# Project Memory

Keep knowledge in the correct layer:

- Put current work and next actions in the relevant
  `planning/agent-state/threads/<issue-number>-<short-name>.md`.
- Put durable choices and unresolved questions in `planning/DECISIONS.md`.
- Put verified, reusable findings in `planning/LEARNINGS.md`.
- Put verified command recipes in `planning/TOOLING.md`.
- Put procedures in `.opencode/skills/` only when they are repeatable and have a
  clear trigger.

Before writing a learning, check that it is verified and not already captured.
Before writing a decision, state the alternatives and why the selected choice
fits the project tenets. Keep thread handoffs short enough to read in one pass.
