# Work Thread
Updated: 2026-10-02
Issue: #34
PR: #50, #53, #55, #56, #57, #67
Owner: lead
Branch: issue-34-run-bundle-boundary
Worktree: none (branch is not checked out; current checkout is issue-48-phase9-handoff)
Objective: Break Issue #34 into a user-approved run-bundle design gate and bounded implementation work.
Status: complete
Scope: run-bundle storage, read-only inspection, human-confirmed recording association, oracle compatibility, and Phase 9 handoff.
Dependencies: #13, #15, #21, #35; `planning/components/ground-truth.md`; `planning/components/dataset.md`; design co-sign #43.
Completed:
- Reviewed Issue #34, workflow rules, roadmap, architecture, adjacent issues, and component contracts.
- Created design co-sign issue #43 with alternatives and six decisions requiring user input.
- Created implementation/integration sub-issues #44-#48, each blocked by #43.
- Expanded the parent scope with documentation and created #54 for operator and
  agent instructions, blocked by #43.
- Commented the decomposition and ownership boundaries on Issue #34.
- User approved the revised boundary: #34 owns versioned run-bundle storage,
  lifecycle, inspection, and human-confirmed OBS association; low-level OBS
  hooks/alignment and Phase 9 scale-out remain separately owned.
- User co-signed SQLite storage and the explicit `endless` lifecycle outcome;
  D024 records the complete compatibility, integrity, query, and ownership
  decisions. PR #50 carries the design update.
- PRs #50, #53, #55, #56, and #57 are merged with green required CI. PR #67
  merged the Phase 9 handoff and integration evidence. Children #44-#48 and
  documentation child #54 are closed; the implementation and parent acceptance
  criteria are satisfied by the merged changes.
Next:
1. None for Issue #34. PR #68 is a stale T0 settlement PR for already-closed
   Issue #48; its merge is blocked by a non-clean base/diff and is not needed
   for the parent implementation acceptance.
Decisions: D021, D023, and D024 govern the ownership and implementation boundary.
Risks: PR #68 remains open because its branch no longer merges cleanly into
master; this is a separate baton-settlement process issue for closed Issue #48,
not an Issue #34 implementation dependency. Phase 9 export format remains intentionally separate. The
  current checkout has unrelated uncommitted changes (this baton,
  `planning/agent-state/threads/44-run-bundle-storage.md`,
  `planning/agent-state/threads/47-oracle-compatibility.md`, and
  `does-not-exist.db`) and must not be used for implementation.
Validation: `py -3 planning\check_contracts.py` => planning contracts OK;
`git diff --check` => clean; merged PRs #50, #53, #55, #56, #57, and #67 all
report required CI green. Full-suite validation is recorded in the child
batons; no implementation files changed in this settlement.
