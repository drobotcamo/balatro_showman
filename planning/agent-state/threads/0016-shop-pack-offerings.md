# Work Thread
Updated: 2026-09-30
Issue: #16
PR: https://github.com/drobotcamo/balatro_showman/pull/28 (open)
Owner: opencode Phase 0 lead session (issue-16)
Branch: issue-16-shop-pack-offerings
Worktree: C:\Users\camgr\.t3\worktrees\balatro_showman\t3code-0f4343a0
Objective: Snapshot the shop and opened-pack offering zones in the Lua producer and report offering-zone coverage in the oracle audit.
Status: active
Scope: `ground_truth/balatro_mod/main.lua`, `planning/audit_oracle_runs.py`, `tests/test_balatro_mod.py`, `tests/test_audit_oracle_runs.py`, `planning/LEARNINGS.md`, `planning/ORACLE_DATA_REVIEW.md`
Dependencies: Parent #10 (proposal P5). Adopted live/2.0 zone vocabulary (D009). Independent of the #14/D021 persistent-state decision.
Completed:
- Emitted `TopShelfShopOfferings` (`G.shop_jokers`), `VoucherShopOfferings` (`G.shop_vouchers`), `PackShopOfferings` (`G.shop_booster`), and `PackOfferings` (`G.pack_cards`) with `position_in_zone` in `build_objects`; offering cards use a new `encode_offer_object` (playing card vs inventory) and `inventory_type` (joker/voucher/pack/tarot/planet/spectral).
- Bare `ShopOfferings` is intentionally not emitted: it is a deprecated offline-extractor alias with no distinct live CardArea; the user confirmed the four canonical zones on 2026-09-30 (recorded as an Issue #16 comment).
- Extended `planning/audit_oracle_runs.py`: `offering_objects_total`, `offering_zone_counts`, `offering_zones_present`, `offering_zones_missing`, a non-fatal finding for offering objects missing `position_in_zone`, and `pack` in the inventory class-ID check.
- Tests: producer zone/area assertions in `tests/test_balatro_mod.py`; audit coverage assertions in `tests/test_audit_oracle_runs.py`.
- Addressed the `@reviewer` "holds with gaps" verdict: corrected the `ShopOfferings` provenance wording and the smods `game_object.lua` citation in `LEARNINGS.md`, updated the P5 disposition in `ORACLE_DATA_REVIEW.md`, added `pack` to the audit inventory-type set, and refreshed this thread's PR field.
Next:
- Merge PR #28 once the fresh re-review and required CI are green; then set `Status: complete` and record the merged PR.
- Run the merged producer through a pinned-revision live shop+pack capture and the audit to demonstrate populated offering zones (Done-When bullet 1); that manual capture is owned by #11/P6 and cannot be verified in this environment.
- User decision if desired: whether to extend CI beyond `check_contracts.py` to run the unit tests (gap 8; out of scope here).
Decisions: Emit the four canonical live/2.0 offering zones only; treat bare `ShopOfferings` as a deprecated alias (user-confirmed, Issue #16 comment). The emitted zones follow D009, so no new durable decision record is required.
Risks: No Lua interpreter is available in-repo, so `main.lua` is verified by static reasoning against the installed game dump (`%APPDATA%\Balatro\Mods\lovely\game-dump`), not executed. Offering-zone correctness off-page relies on `CardArea:remove()` niling `.cards` (verified in `cardarea.lua`/`engine/ui.lua` but not in a live session). `class_id` for booster packs is null because booster center keys are suffixed (`p_arcana_normal_1`) and absent from the vendored class map; `center_key` is retained, matching `live/smoke_test.py`. The vendored class map is a gitlink with no `.gitmodules`, so `tests/test_class_ids.py` needs the main checkout's vendor tree; CI runs only `check_contracts.py`.
Validation: `py -3 -m unittest tests.test_balatro_mod tests.test_file_ipc_bridge tests.test_class_ids tests.test_audit_oracle_runs` -> 17 tests OK (class-map test run with the main checkout's vendored `class_map.csv` copied in, then removed); `py -3 ground_truth\generate_class_ids.py --check` -> `class ID table is up to date`; `py -3 planning\check_contracts.py` -> `planning contracts OK`; `git diff --check` -> exit 0; audit on the two persisted pre-fix runs reports `offering_objects_total: 0`, all four zones missing, `oracle run integrity OK`. Reviewer: fresh-context `@reviewer`, task `ses_f0ac91e6fffeNFQbzGEbsKEdPI`, verdict **holds with gaps** on commit 01040cc; core behavior confirmed, gaps (1) live capture (deferred to #11), (2)-(4) provenance/citation/planning-artifact inaccuracies, (5) stale-area assumption, (6) audit blind spot, (7) stale thread field, (8) CI does not run unit tests. Gaps (2)-(6) addressed in follow-up commits; (1), (5), (8) recorded above.
