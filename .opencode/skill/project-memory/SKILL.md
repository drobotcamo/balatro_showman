---
name: project-memory
description: Maintain project decisions, learnings, and agent handoffs. Use when work changes a contract, reveals a reusable finding, or a session is ending.
---

# Project Memory

Route knowledge to the correct layer; do not duplicate it. Procedures go in
`.opencode/skill/` only when repeatable with a clear trigger.

- Live outcome, acceptance, blocker and completion → GitHub issue/PR.
- Extra context to resume unfinished work →
  `planning/agent-state/threads/<issue-number-or-tag>-<short-name>.md` (template in
  `planning/agent-workflow.md` → Handoff Protocol).
- Durable choices and open questions → `planning/DECISIONS.md` (ADR-lite
  entries; state alternatives when material).
- Verified reusable findings → `planning/LEARNINGS.md` (use its entry format;
  check the finding is verified and not already captured).

Run `python planning/check_contracts.py` after writing. Keep checkpoints short.
Historical full-format and new compact checkpoints remain compatible; no normal
completion needs a new checkpoint or a settlement-only PR.
