# Work Thread
Updated: 2026-09-30
Issue: #16
PR: none yet
Owner: opencode Phase 0 lead session (issue-16)
Branch: issue-16-shop-pack-offerings
Worktree: C:\Users\camgr\.t3\worktrees\balatro_showman\t3code-0f4343a0
Objective: Snapshot the shop and opened-pack offering zones in the Lua producer and report offering-zone coverage in the oracle audit.
Status: active
Scope: `ground_truth/balatro_mod/main.lua`, `planning/audit_oracle_runs.py`, `tests/test_balatro_mod.py`, `tests/test_audit_oracle_runs.py`, `planning/LEARNINGS.md`
Dependencies: Parent #10 (proposal P5). Adopted live/2.0 zone vocabulary (D009). Independent of the #14/D021 persistent-state decision.
Completed:
- Emitted `TopShelfShopOfferings` (`G.shop_jokers`), `VoucherShopOfferings` (`G.shop_vouchers`), `PackShopOfferings` (`G.shop_booster`), and `PackOfferings` (`G.pack_cards`) with `position_in_zone` in `build_objects`; offering cards use a new `encode_offer_object` (playing card vs inventory) and `inventory_type` (joker/voucher/pack/tarot/planet/spectral).
- Bare `ShopOfferings` is intentionally not emitted: it is a deprecated offline-extractor alias with no distinct live CardArea; the user confirmed the four canonical zones on 2026-09-30.
- Extended `planning/audit_oracle_runs.py`: `offering_objects_total`, `offering_zone_counts`, `offering_zones_present`, `offering_zones_missing`, and a non-fatal finding for offering objects missing `position_in_zone`.
- Tests: producer zone/area assertions in `tests/test_balatro_mod.py`; audit coverage assertions in `tests/test_audit_oracle_runs.py`.
Next:
- Open the T2 PR, link it to this thread, and record a fresh-context `@reviewer` verdict.
- Merge once required CI is green; then set `Status: complete` and record the merged PR.
- Run the merged producer through a pinned-revision live shop+pack capture and the audit to demonstrate populated offering zones (Done-When bullet 1); that manual capture is owned by #11/P6 and cannot be verified in this environment.
Decisions: Emit the four canonical live/2.0 offering zones only; treat bare `ShopOfferings` as a deprecated alias (user-confirmed). No durable decision record needed.
Risks: No Lua interpreter is available in-repo, so `main.lua` is verified by static reasoning against the installed game dump (`%APPDATA%\Balatro\Mods\lovely\game-dump`), not executed. `class_id` for booster packs is null because booster center keys are suffixed (`p_arcana_normal_1`) and absent from the vendored class map; `center_key` is retained, which matches `live/smoke_test.py`. The vendored class map is a gitlink with no `.gitmodules`, so `tests/test_class_ids.py` needs the main checkout's vendor tree.
Validation: `py -3 -m unittest tests.test_balatro_mod tests.test_file_ipc_bridge tests.test_class_ids tests.test_audit_oracle_runs` -> 17 tests OK (class-map test run with the main checkout's vendored `class_map.csv` copied in, then removed); `py -3 ground_truth\generate_class_ids.py --check` -> `class ID table is up to date`; `py -3 planning\check_contracts.py` -> `planning contracts OK`; `git diff --check` -> exit 0.
