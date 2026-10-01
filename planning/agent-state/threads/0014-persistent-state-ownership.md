# Work Thread

Updated: 2026-09-30
Issue: #14
PR: #20 and #22 (both merged; #22 = 045c743)
Owner: project-lead session
Branch: issue-14-persistent-state-ownership
Worktree: ../balatro_showman-issue-14
Objective: Record a durable decision on whether the Lua oracle or the pipeline reducer owns canonical persistent state, and where the producer schema/version boundary sits.
Status: complete
Scope: planning/PERSISTENT_STATE_OWNERSHIP.md, planning/DECISIONS.md, planning/components/{ground-truth,state-reduction}.md, producer issue annotations (#12/#13/#16), new issue #21
Dependencies: T1 user choice obtained (option c, D021); ORACLE_DATA_REVIEW.md §7 P3; D009; D020; Q04
Completed:
- Design note written with options (a)/(b)/(c), tradeoffs, and recommendation (c); merged via PR #20; posted to Issue #14 (issuecomment-5921912152).
- User selected option (c) on 2026-09-30; recorded as D021 in DECISIONS.md (PR #22, merge 045c743).
- ground-truth.md and state-reduction.md updated for the D021 boundary (raw fields + engine legality are validation-only; reducer owns canonical state).
- Producer issues annotated with the chosen boundary: #13 (depends), #12/#16 (independent).
- New sub-issue #21 tracks the raw persistent-field schema + engine legal actions, which no existing producer issue owned.
- Issue #14 closed as completed with the evidence comment (issuecomment-5922012218).
Next:
1. None for this thread. Follow-on producer work continues in #21 (raw fields/legal actions), with #13/#12/#16/#15/#11 per their own threads.
Decisions: D021 — oracle emits raw engine fields and legal actions; the pipeline reducer owns canonical persistent_state
Risks: Option (c) makes the oracle's raw-field transport a new contract surface (#21); the engine-truth vs video-recoverable gap must be measured to answer Q04
Validation: py -3 planning\check_contracts.py -> `planning contracts OK` (exit 0), worktree root; `git diff --check` clean; PR #20 and #22 `check` green
