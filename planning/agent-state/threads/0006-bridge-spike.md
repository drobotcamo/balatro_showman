# Work Thread
Updated: 2026-09-30
Issue: #6
PR: https://github.com/drobotcamo/balatro_showman/pull/9
Owner: opencode Phase 0 lead session
Branch: issue-6-bridge-spike
Worktree: `C:\Users\camgr\Documents\code_projects\balatro_showman-issue-6`
Objective: Ship the smallest runtime-compatible Lua producer for the file-IPC oracle contract and prove one real aligned (state, action, outcome) run.
Status: ready-for-review
Scope: `ground_truth/balatro_mod/` (Lua producer), its manifest test, `planning/BRIDGE_SPIKE.md`
Dependencies: T2 fresh-context review; follow-up Issue #10 owns data/storage-conformance review
Completed:
- Verified PR #7 is repository-only: it adds a stdlib client for `snapshot.json -> action.txt` and explicit `run_end.json` finalization, but no Lua producer. It is reference material, not oracle evidence.
- Confirmed the installed runtime is suitable in principle: Balatro `1.0.1o-FULL`, Lovely `0.10.0`, Steamodded `26.926.0~dev-a`, mod root `%APPDATA%\Balatro\Mods`. Only `BalatroMultiplayer-0.5.5` and `Brainstorm-2.0.0-alpha-1` are blacklisted; `HandyBalatro`/`JokerDisplay` emit metadata/patch warnings but load. No `agent_bridge.lua` exists in repo or runtime.
- Derived verified game facts read-only from `Mods\lovely\game-dump\`: action callbacks `G.FUNCS.{play_cards_from_highlighted, discard_cards_from_highlighted, select_blind, skip_blind, cash_out, reroll_shop, buy_from_shop, sell_card, use_card, skip_booster, toggle_shop}`; `G.STATES`/`G.STAGES`; `G.GAME.won` set true on win and false at `Game:start_run`; card base suit/value and `Card.highlighted`.
- Added `ground_truth/balatro_mod/` (Steamodded `manifest.json` + `main.lua`) that emits `snapshot.json` (real state/objects/page/action_taken/request_id/runtime meta) and `run_end.json` (win/loss). It does not read saves or copy runtime files.
- Added `tests/test_balatro_mod.py` guarding the manifest shape and the single-JSON-metadata loader invariant.
- Validation: `main.lua` parses (luaparser) and executes against a synthetic game state (lupa) producing valid, aligned `snapshot.json` + `run_end.json`; `py -3 -m unittest tests.test_file_ipc_bridge tests.test_balatro_mod` and `py -3 planning\check_contracts.py` pass; `git diff --check` clean.
Next:
1. Commit the 999/998 page-mapping fix and this doc update to PR #9.
2. Run the prescribed T2 fresh-context `@reviewer`; record the verdict on PR #9.
3. Merge PR #9 once CI is green and the reviewer verdict holds, then close Issue #6.
4. Hand off evidence + storage-contract review to Issue #10 in a new session.
Decisions: No architecture, component contract, or durable policy changed.
Risks: Real-run coverage is two sessions (one win, one loss); `In_TarotSpectral_Pack` and voucher 998 are verified synthetically but not live. Action labels are coarse and `persistent_state` is empty by design; Issue #10 must decide whether that satisfies the Phase 0 gate or requires canonical action space. No Phase 0 gate is claimed yet.
Validation: luaparser syntax OK; lupa harness produced aligned `snapshot.json`/`run_end.json`; `py -3 -m unittest tests.test_file_ipc_bridge tests.test_balatro_mod` -> OK; `py -3 planning\check_contracts.py` -> `planning contracts OK`; `git diff --check` -> clean.
Evidence (2026-09-30, real run, outcome `win`):
- Recording (external, do not commit): `F:\OBS_RECORDINGS\2026-09-30 14-50-37.mkv` (2.36 GB).
- Persisted run output: `F:\OBS_RECORDINGS\oracle_runs\2026-09-30_14-50-37_1790805058-5327\` (`steps.ndjson`, `session.json`, `NOTE.txt`); copied from `%TEMP%\balatro_showman_runs\1790805058-5327\` before temp cleanup.
- Per-step runtime metadata: Balatro `1.0.1o-FULL`, Steamodded `26.926.0~dev-a`, Lovely `0.10.0`.
- Page/action coverage: In_Shop 191, In_Blind 149, Unknown_999 38, Blind_Select 28, Cash_Out 27; actions PlayHand/DiscardHand/SelectBlind/SkipBlind/CashOut/LeaveShop/RerollShop/BuyShopItem/SellItem/UseConsumable/SkipPack.
- Known gap (fixed): Steamodded patches `G.STATES` with `SMODS_BOOSTER_OPENED = 999` and `SMODS_REDEEM_VOUCHER = 998` (`smods-main/lovely/booster.toml`). The producer now maps 999 to a pack page via `SMODS.OPENED_BOOSTER.config.center.kind` (Arcana/Spectral -> `In_TarotSpectral_Pack`, else `In_JokerStandardPlanet_Pack`) and 998 -> `In_Shop`, and records raw `meta.game_state`/`pack_kind`.
- Verification run (2026-09-30, 43 steps, outcome `loss`, persisted at `F:\OBS_RECORDINGS\oracle_runs\2026-09-30_15-31_verify_1790807319-8546\`): raw states 7/1/8/5/999 all mapped, zero `Unknown_*` pages, packs resolved `Buffoon`/`Celestial`/`Standard`. Unexercised live: `In_TarotSpectral_Pack` (no Arcana/Spectral pack seen) and 998 voucher redeem; both covered by the synthetic harness only.
- 433 unique request IDs, one run_id, `action_taken` present on every step; `persistent_state` empty and action labels coarse by design.

Changed files: `ground_truth/balatro_mod/manifest.json`, `ground_truth/balatro_mod/main.lua`, `tests/test_balatro_mod.py`, `planning/BRIDGE_SPIKE.md`, this thread file.
Follow-up: Issue #10 (oracle data integrity and storage-contract conformance) in a new session.
