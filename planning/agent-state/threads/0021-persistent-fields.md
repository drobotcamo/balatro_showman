# Work Thread
Updated: 2026-09-30
Issue: #21
PR: none
Owner: unassigned
Branch: none
Worktree: none
Objective: Emit raw persistent fields and engine legal actions as an independent reducer validation reference.
Status: active
Scope: `ground_truth/balatro_mod/main.lua`, `planning/audit_oracle_runs.py`, tests.
Dependencies: D021/#14 is resolved; #12 and #13 are separate producer concerns.
Completed: Issue #21 was created and scoped by the D021 decision; no implementation evidence exists.
Next: Claim the issue, create its dedicated T2 branch/worktree, implement the versioned raw schema and legal-action coverage.
Decisions: Oracle emits raw engine fields/legal actions; reducer owns canonical `persistent_state` and masks (D020/D021).
Risks: New producer transport schema is a contract surface; Q04 remains unanswered.
Validation: Not run.
