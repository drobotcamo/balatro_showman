# Work Thread
Updated: 2026-10-02
Issue: #48
PR: none
Owner: project lead
Branch: issue-48-phase9-handoff (shared checkout; unrelated pre-existing changes preserved)
Worktree: C:\Users\camgr\Documents\code_projects\balatro_showman
Objective: Integrate the run-bundle boundary and document the Phase 9 dataset handoff.
Status: active
Scope: planning/components/dataset.md, tests/test_run_bundle_phase9_integration.py, this thread
Dependencies: #34, #44, #45, #46, #47; D024-D025; ground-truth and dataset contracts
Completed:
- Defined the Phase 9 input boundary: SQLite bundles through read-only inspection
  or legacy oracle directories through read-only compatibility access.
- Documented explicit no-video, confirmed-marker, missing/invalid-marker,
  partial-run, source-preservation, and resumability semantics.
- Added integration coverage for partial/no-video legacy input with source
  preservation and confirmed recording association remaining additive to a
  validated SQLite bundle.
- Explorer verified the existing focused behavior. Real oracle runs were found
  under `%TEMP%\balatro_showman_runs\1790831717-5749` and read successfully as
  healthy, one step, `producer/1.0.0`, `no-video`, with source hashes; additional
  32-, 43-, 381-, and 433-step partial runs were also classified diagnostically.
Next:
1. Obtain or identify an available oracle run artifact and run the required
   compatibility/read-only inspection evidence for Issue #48.
2. Review this diff in a dedicated Issue #48 branch/worktree before opening the
   T0 PR; do not include existing unrelated baton edits or does-not-exist.db.
3. Post validation and reviewer evidence to the PR, merge, then settle #48 and
   update parent #34.
Decisions: Preserve D024 read-only compatibility and D025 human-confirmed additive association; no new export schema or video-existence claim.
Risks: The discovered real run is a one-step smoke subset and has no recording association; it does not prove full-run or export-resume behavior. Current checkout also has unrelated modified thread files and untracked does-not-exist.db. Fresh reviewer verdict: holds with gaps; the real-run gap is now closed, but export-resume remains unverified.
Validation: `python -m pytest -q` => 83 passed; `python planning/check_contracts.py` => planning contracts OK; `git diff --check` => clean; `read_oracle_run(%TEMP%\balatro_showman_runs\1790831717-5749)` => healthy, 1 step, no-video, no diagnostics.
