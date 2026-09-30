---
name: project-memory
description: Maintain project decisions, learnings, and agent handoffs. Use when work changes a contract, reveals a reusable finding, or a session is ending.
---

# Project Memory

Route knowledge to the correct layer; do not duplicate it. Procedures go in
`.opencode/skills/` only when repeatable with a clear trigger.

- Current work and next actions →
  `planning/agent-state/threads/<issue-number>-<short-name>.md` (template in
  `planning/agent-workflow.md` → Handoff Protocol).
- Durable choices and open questions → `planning/DECISIONS.md` (ADR-lite
  entries; state alternatives when material).
- Verified reusable findings → `planning/LEARNINGS.md` (use its entry format;
  check the finding is verified and not already captured).

Before writing, run `python planning/check_contracts.py`. Keep batons short
enough to read in one pass.