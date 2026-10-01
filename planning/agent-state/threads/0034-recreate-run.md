# Work Thread
Updated: 2026-10-01
Issue: #34
PR: pending
Owner: lead
Branch: issue-34-run-bundle-boundary
Worktree: C:\Users\camgr\Documents\code_projects\balatro_showman
Objective: Break Issue #34 into a user-approved run-bundle design gate and bounded implementation work.
Status: blocked
Scope: run-bundle storage, read-only inspection, human-confirmed recording association, oracle compatibility, and Phase 9 handoff.
Dependencies: #13, #15, #21, #35; `planning/components/ground-truth.md`; `planning/components/dataset.md`; design co-sign #43.
Completed:
- Reviewed Issue #34, workflow rules, roadmap, architecture, adjacent issues, and component contracts.
- Created design co-sign issue #43 with alternatives and six decisions requiring user input.
- Created implementation/integration sub-issues #44-#48, each blocked by #43.
- Commented the decomposition and ownership boundaries on Issue #34.
- User approved the revised boundary: #34 owns versioned run-bundle storage,
  lifecycle, inspection, and human-confirmed OBS association; low-level OBS
  hooks/alignment and Phase 9 scale-out remain separately owned.
Next:
1. User co-signs or revises the decisions in #43.
2. Record accepted decisions in `planning/DECISIONS.md` or a linked decision note.
3. Unblock the smallest implementation issue, beginning with #44.
4. Keep #48 as the integration and validation boundary for Issue #34.
Decisions: D021 and D023 govern the ownership boundary. The six physical/API/
lifecycle details in #43 remain an implementation design gate and are not yet
accepted as durable choices.
Risks: Physical encoding, lifecycle terminal-state semantics, integrity strictness, query envelope, confirmation UX, and compatibility policy remain unresolved until #43 is answered.
Validation: `py -3 planning\\check_contracts.py` passed before this thread
update; rerun before commit.
