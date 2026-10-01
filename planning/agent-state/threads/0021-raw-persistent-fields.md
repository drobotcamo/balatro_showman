# Work Thread
Updated: 2026-09-30
Issue: #21
PR: https://github.com/drobotcamo/balatro_showman/pull/29 (open, held for user review)
Owner: opencode Phase 0 lead session (issue-21)
Branch: issue-21-raw-persistent-fields
Worktree: `C:\Users\camgr\.t3\worktrees\balatro_showman\t3code-bd4f320d`
Objective: Emit engine-truth raw persistent fields and the engine's legal actions/mask basis from the Lua producer under a transport version distinct from the granularized `3.0.0`, and report their coverage in the audit tool (D021).
Status: ready-for-review (held: user chose to inspect before merge)
Scope: `ground_truth/balatro_mod/main.lua`, `ground_truth/file_ipc_bridge.py`, `planning/audit_oracle_runs.py`, `tests/test_audit_oracle_runs.py`, `tests/test_file_ipc_bridge.py`, `planning/BRIDGE_SPIKE.md`, `planning/LEARNINGS.md`
Dependencies: Parent #10; D021 (option c), D009, D020; `mask_schema.md` §2-3; `state_schema.md` §3.
Completed:
- `main.lua` emits `live/3.0.0` snapshots with `raw_persistent`, `legal_actions` (mask_schema §2 page gating + §3 availability; action about to run always included because the file-IPC client rejects snapshots without it), and `mask_basis`; `persistent_state` stays `{}` (reducer owns canonical shape). All reads failure-isolated; unavailable → explicit null.
- External lupa (Lua 5.1) harness (temp dir) executes `main.lua` against a stub `G`: raw fields, legality across blind/shop/pack/unaffordable/untagged/unknown pages, client acceptance — `HARNESS OK` (stub updated to runtime shapes after the real capture).
- Real capture validated (user-provided, 50 steps, `F:\OBS_RECORDINGS\oracle_runs_live3\`): legality/mask_basis/counters/hand_levels/blind_states on 50/50 steps, `action_in_legal_actions` 50/50, `raw_field_schema: true`; 52 tracked deck cards per step. It exposed three Steamodded-runtime divergences from the vanilla dump (recorded in `LEARNINGS.md`): deck key at `G.GAME.selected_back.effect.center.key`, stake key at `G.P_CENTER_POOLS.Stake[level].key`, `bosses_used` nested `{boss/small/big: {blind_key: count}}`, plus a fifth `blind_states` value `'Current'`. Producer fixed accordingly (deck/stake runtime paths with vanilla fallbacks; recursive depth-capped table serializer). These fixes post-date the capture, so a fresh capture with the re-copied mod is the remaining validation.
- `file_ipc_bridge.py` now stops cleanly on Ctrl+C and reports unfinalized sessions (user request); 2 new tests.
- `planning/audit_oracle_runs.py`: schema-aware required fields, raw-field/mask-basis/legality coverage, non-fatal findings; 5 new tests. Integrity exit semantics unchanged.
- Reviewer verdict on PR #29: **holds with gaps** (task ses_f0abcf275ffemk51kOv7M40Hx4); fixed its actionable gaps (explicit nulls, deterministic stake scan, strict `last_tarot_planet` type) in 669ca68; verdict + disposition recorded on the PR.
- Real-capture session observations: first session (40 steps) has `outcome: null` because the user exited to the main menu mid-run (producer only finalizes on game over) — 1 integrity failure, expected behavior; second session (10 steps, resumed save) ends in `loss`. Menu-exit abandonment semantics are unresolved (not decided here).
Next:
- User reviews PR #29 diff; on acceptance, merge (T2: CI green, verdict recorded).
- After merge: re-copy mod to `$env:APPDATA\Balatro\Mods\balatro_showman_bridge`, fresh capture, audit to confirm deck/stake center keys and nested `bosses_used` resolve on the real runtime (closes the reviewer's gap A).
- Menu-exit/abandonment finalize semantics: open question, not decided in this thread.
Decisions: Transport label `live/3.0.0` within D021's boundary (documented in `BRIDGE_SPIKE.md`). Raw-field key `raw_persistent` avoids the canonical `persistent_state` shape (D021). No contract or `DECISIONS.md` changes.
Risks: Runtime-verified reads come from one machine/runtime; deck/stake fix not yet validated by a persisted run. `bosses_used` nested shape is Steamodded-specific; vanilla fallback serializer handles both. Vendored tree required locally for `tests.test_class_ids` (populated from main checkout, not committed). Menu-exit leaves sessions unfinalized by design.
Validation: `py -3 -m unittest tests.test_balatro_mod tests.test_file_ipc_bridge tests.test_class_ids tests.test_audit_oracle_runs -v` → 19 OK; lupa harness → `HARNESS OK`; `py -3 planning\audit_oracle_runs.py <2 legacy runs>` → `oracle run integrity OK` + new findings; `py -3 planning\audit_oracle_runs.py <2 live3 capture runs>` → `raw_field_schema: true`, legality 50/50, deck/stake findings; `py -3 planning\check_contracts.py` → `planning contracts OK`; `git diff --check` → clean; CI check green on PR #29.