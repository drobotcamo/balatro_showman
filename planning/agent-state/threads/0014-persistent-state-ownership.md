# Work Thread

Updated: 2026-09-30
Issue: #14
PR: none
Owner: project-lead session
Branch: issue-14-persistent-state-ownership
Worktree: ../balatro_showman-issue-14
Objective: Record a durable decision on whether the Lua oracle or the pipeline reducer owns canonical persistent state, and where the producer schema/version boundary sits.
Status: blocked
Scope: planning/PERSISTENT_STATE_OWNERSHIP.md, planning/DECISIONS.md, planning/components/{ground-truth,state-reduction}.md, producer issue annotations (#12/#13/#16)
Dependencies: T1 user decision required before DECISIONS.md/component edits; ORACLE_DATA_REVIEW.md §7 P3; D009; D020; Q04
Completed: Design note written with options (a)/(b)/(c), tradeoffs, and recommendation (c); pending review and merge
Next:
1. Run planning/check_contracts.py; open and merge the T0 auto-PR for the note.
2. Post the recommendation to Issue #14 and obtain the user's choice (T1).
3. Record the accepted decision in DECISIONS.md (next D-number) and update ground-truth/state-reduction contracts if the choice changes their invariants.
4. Annotate #13 (depends), #12/#16 (independent) with the chosen boundary; close #14 with evidence.
Decisions: Recommendation (c) proposed, not yet accepted; no DECISIONS.md entry until user chooses
Risks: An oracle-side reducer (option a) risks a second divergent reducer and a self-shaped mask oracle; option (b) leaves the Phase 7 gate unscorable
Validation: python planning/check_contracts.py (run at the root of this worktree)
