# Work Thread
Updated: 2026-10-01
Issue: #21
PR: https://github.com/drobotcamo/balatro_showman/pull/29 (open, held for user review)
Owner: opencode Phase 0 lead session (issue-21)
Branch: issue-21-raw-persistent-fields
Worktree: `C:\Users\camgr\.t3\worktrees\balatro_showman\t3code-bd4f320d`
Objective: Emit engine-truth raw persistent fields and the engine's legal actions/mask basis from the Lua producer under a transport version distinct from the granularized `3.0.0`, and report their coverage in the audit tool (D021).
Status: ready-for-review (handoff; PR open, merge/review continuation required)
Scope: `ground_truth/balatro_mod/main.lua`, `ground_truth/file_ipc_bridge.py`, `planning/audit_oracle_runs.py`, `tests/test_audit_oracle_runs.py`, `tests/test_file_ipc_bridge.py`, `planning/BRIDGE_SPIKE.md`, `planning/LEARNINGS.md`
Dependencies: Parent #10; D021 (option c), D009, D020; `mask_schema.md` §2-3; `state_schema.md` §3.
Completed:
- `main.lua` emits `live/3.0.0` snapshots with `raw_persistent`, `legal_actions` (mask_schema §2 page gating + §3 availability; action about to run always included because the file-IPC client rejects snapshots without it), and `mask_basis`; `persistent_state` stays `{}` (reducer owns canonical shape). All reads failure-isolated; unavailable → explicit null.
- External lupa (Lua 5.1) harness (temp dir) executes `main.lua` against a stub `G`: raw fields, legality across blind/shop/pack/unaffordable/untagged/unknown pages, client acceptance — `HARNESS OK` (stub updated to runtime shapes after the real capture).
- Real capture validated (user-provided, 47 steps, `F:\OBS_RECORDINGS\oracle_runs_live3b\1790823405-3642`, loss): legality/mask_basis/counters/hand_levels/blind_states, deck/stake center keys, nested `bosses_used`, vouchers, and `action_in_legal_actions` all present 47/47; 52 tracked deck cards per step. It confirmed the Steamodded runtime paths and recursive serializer fixes on a real run.
- `file_ipc_bridge.py` now stops cleanly on Ctrl+C and reports unfinalized sessions (user request); 2 new tests.
- `planning/audit_oracle_runs.py`: schema-aware required fields, raw-field/mask-basis/legality coverage, non-fatal findings; 5 new tests. Integrity exit semantics unchanged.
- Reviewer verdict on PR #29: **holds with gaps** (task ses_f0abcf275ffemk51kOv7M40Hx4); fixed its actionable gaps (explicit nulls, deterministic stake scan, strict `last_tarot_planet` type) in 669ca68; verdict + disposition recorded on the PR.
- Real-capture session observation: the earlier 40-step session had `outcome: null` after a menu exit; user clarified this is correct because only win/loss ends a run. The validated fresh run ended in `loss` with no integrity failures. Resume run-id continuity remains outside this issue.
- Current `master` was merged into the branch to resolve PR conflicts; the combined suite now includes Issue #16 offering-zone tests.
 - Additional user capture at `%TEMP%\balatro_showman_runs\issue13-live\1790825946-6121` contains 381 `live/3.0.0` steps. The strongest scored hand was Flush Five (44,710); Five of a Kind became the dominant late-run hand-level progression (level 14). Immolate destroyed five cards. Two Wheel of Fortune uses were observed with no observed edition change (0/2). Ouija was followed by rank-3 dominance and a non-normal 52-card rank distribution. Purchased-card identity and per-joker money contribution are not exposed directly, so money attribution remains cautious. The recording ends mid-blind with one hand remaining and no `run_end`; it does not establish a loss. Its session metadata is stale (`n_steps=59`, outcome null).
Next:
 - Resolve any current PR base-conflict state, rerun CI, then merge only after the T2 fresh-review requirement is satisfied or the user explicitly accepts the review gap.
- Fresh-context reviewer attempt failed because the provider credit limit was exceeded; prior verdict is `holds with gaps`, with actionable gaps fixed and fresh real-run evidence posted.
- Menu-exit does not end a run; only win/loss finalizes it. Resume run-id continuity may need a future bounded issue.
Decisions: Transport label `live/3.0.0` within D021's boundary (documented in `BRIDGE_SPIKE.md`). Raw-field key `raw_persistent` avoids the canonical `persistent_state` shape (D021). No contract or `DECISIONS.md` changes.
Risks: Runtime-verified reads come from one machine/runtime; `bosses_used` nested shape is Steamodded-specific; recursive serializer handles nested and flat forms. Vendored tree required locally for `tests.test_class_ids` (populated from main checkout, not committed). Menu-exit leaves sessions unfinalized by design; resume run-id continuity is not addressed.
 Validation: `py -3 -m unittest tests.test_balatro_mod tests.test_file_ipc_bridge tests.test_class_ids tests.test_audit_oracle_runs -v` → 24 OK; lupa harness → `HARNESS OK`; `py -3 planning\audit_oracle_runs.py F:\OBS_RECORDINGS\oracle_runs_live3b\1790823405-3642` → `raw_field_schema: true`, all raw-field/legality coverage 47/47, `oracle run integrity OK`; second capture audit → raw schema and legality coverage 381/381, with integrity failures only for stale `session.n_steps` and null outcome; `py -3 planning\check_contracts.py` → `planning contracts OK`; `git diff --check` → clean before current-master integration; CI is pending refresh.
