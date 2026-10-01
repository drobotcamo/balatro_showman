# Work Thread

Updated: 2026-09-30
Issue: #14
PR: #20 (merged 7150720); decision follow-up PR open on this branch
Owner: project-lead session
Branch: issue-14-persistent-state-ownership
Worktree: ../balatro_showman-issue-14
Objective: Record a durable decision on whether the Lua oracle or the pipeline reducer owns canonical persistent state, and where the producer schema/version boundary sits.
Status: ready-for-review
Scope: planning/PERSISTENT_STATE_OWNERSHIP.md, planning/DECISIONS.md, planning/components/{ground-truth,state-reduction}.md, producer issue annotations (#12/#13/#16), new issue #21
Dependencies: T1 user choice obtained (option c); ORACLE_DATA_REVIEW.md §7 P3; D009; D020; Q04
Completed:
- Design note written with options (a)/(b)/(c), tradeoffs, and recommendation (c); merged via PR #20; posted to Issue #14 (issuecomment-5921912152).
- User selected option (c) on 2026-09-30; recorded as D021 in DECISIONS.md.
- ground-truth.md and state-reduction.md updated for the D021 boundary (raw fields + engine legality are validation-only; reducer owns canonical state).
- Producer issues annotated with the chosen boundary: #13 (depends), #12/#16 (independent).
- New sub-issue #21 tracks the raw persistent-field schema + engine legal actions, which no existing producer issue owned.
Next:
1. Merge the decision PR, then close #14 with the evidence recorded there.
Decisions: D021 — oracle emits raw engine fields and legal actions; the pipeline reducer owns canonical persistent_state
Risks: Option (c) makes the oracle's raw-field transport a new contract surface (#21); the engine-truth vs video-recoverable gap must be measured to answer Q04
Validation: py -3 planning\check_contracts.py -> `planning contracts OK` (exit 0), worktree root; `git diff --check` clean; PR #20 `check` green
