# Work Thread
Updated: 2026-09-30
Issue: #10 (closed)
PR: https://github.com/drobotcamo/balatro_showman/pull/17 (merged)
Owner: opencode Phase 0 lead session (issue-10)
Branch: issue-10-oracle-data-review
Worktree: `C:\Users\camgr\Documents\code_projects\balatro_showman` (in-place)
Objective: Audit the two persisted Lua-oracle runs for integrity and storage-contract conformance; record conformant fields, gaps, a Phase 0 gate verdict, and unapplied proposals.
Status: complete
Scope: `planning/ORACLE_DATA_REVIEW.md`, `planning/audit_oracle_runs.py`, `planning/TOOLING.md`, `planning/BRIDGE_SPIKE.md`, `planning/LEARNINGS.md`, this thread. No contract or producer code changed.
Dependencies: PR #9 merged; `planning/components/{ground-truth,state-composition,state-reduction,dataset}.md`; D009, D016; Q03, Q04. External evidence on `F:\`.
Completed:
- Merged as PR #17; Issue #10 closed. Fresh-context reviewer verdict `holds with gaps`; the four citation/label errors it found were corrected before merge.
- Added `planning/audit_oracle_runs.py` (read-only, stdlib): validates per-run integrity invariants and reports conformance gaps; exit 0 on the two runs.
- Audited win run (433 steps, `win`) and loss/verify run (43 steps, `loss`). Integrity passed: step counts match `session.n_steps`; one `run_id` per run; `request_id` unique/contiguous; `action_taken` on every step; `_recorded_action` equals it; `outcome` valid.
- Recorded conformance gaps with counts: `persistent_state` empty on 100% of steps; `source_kind`/`action_subtype`/`target_zone`/`target_position` always null; no `frame_idx`; no masks; inventory objects carry only `center_key`; `modifier`/`edition`/`seal` null everywhere; no shop/pack offering zones; coarse base-only action labels.
- Flagged provenance: neither run is from the merged revision; win run has 38 `Unknown_999` steps; loss run's `pack_kind`/`pack_key` are ungated to state 999.
- Verdict: transport liveness and internal state/action/outcome alignment hold, but the Phase 0 gate should not be claimed because video-to-engine alignment is absent and the state/action channel cannot support Phase 7-8 metrics.
- Proposed P1-P6 (unapplied): step identity + frame alignment, canonical zoned actions, producer-vs-reducer persistent-state ownership (P3, user decision), inventory class IDs, shop/pack zones, pinned-revision capture.
Next:
- None for this thread. The proposals now map to Issues #15 (P1), #13 (P2), #14 (P3, blocking decision), #12 (P4), #16 (P5), #11 (P6). Issue #18 owns sequencing them behind the #14 decision.
Decisions: None applied here. P3 is a proposed durable decision needing user input; no contract or `DECISIONS.md` edit made.
Risks: Evidence is pre-merged-revision; loss run pack diagnostics partially unreliable; `page_name` is producer-derived (not independently annotated); no live `In_TarotSpectral_Pack` or voucher state; Phase 0 thresholds (Q03) still open.
Reviewer: fresh-context `@reviewer`, task `ses_f0b7b2ac5ffeFJoKmFWT3jdYtA`, verdict `holds with gaps`; independently re-derived every count and confirmed §4.1-4.4, §4.6, §5, and the §6 verdict reasoning.
Validation: `py -3 planning\audit_oracle_runs.py "F:\OBS_RECORDINGS\oracle_runs\2026-09-30_14-50-37_1790805058-5327" "F:\OBS_RECORDINGS\oracle_runs\2026-09-30_15-31_verify_1790807319-8546"` -> `oracle run integrity OK` (exit 0); `py -3 planning\check_contracts.py` -> `planning contracts OK`; `git diff --check` -> clean. PR #17 `planning-check` SUCCESS.
