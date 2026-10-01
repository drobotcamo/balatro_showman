# Work Thread
Updated: 2026-10-01
Issue: #34
PR: #50
Owner: lead
Branch: issue-34-run-bundle-boundary
Worktree: C:\Users\camgr\Documents\code_projects\balatro_showman
Objective: Break Issue #34 into a user-approved run-bundle design gate and bounded implementation work.
Status: ready-for-review
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
- User co-signed SQLite storage and the explicit `endless` lifecycle outcome;
  D024 records the complete compatibility, integrity, query, and ownership
  decisions. PR #50 carries the design update.
Next:
1. Unblock the smallest implementation issue, beginning with #44.
2. Keep #48 as the integration and validation boundary for Issue #34.
Decisions: D021, D023, and D024 govern the ownership and implementation boundary.
Risks: SQLite schema and migration details remain to be specified by #44; Phase 9 export format remains intentionally separate.
Validation: `py -3 planning\\check_contracts.py` and `git diff --check` passed before PR #50; rerun after this update.
