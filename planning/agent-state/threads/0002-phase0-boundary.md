# Work Thread
Updated: 2026-09-30
Issue: #6
PR: https://github.com/drobotcamo/balatro_showman/pull/7 (closed, superseded by the new producer PR)
Owner: opencode Phase 0 lead session
Branch: issue-6-bridge-spike
Worktree: `C:\Users\camgr\Documents\code_projects\balatro_showman-issue-6`
Objective: Ship the smallest runtime-compatible Lua producer for the file-IPC oracle contract and prove one real aligned (state, action, outcome) run.
Status: blocked
Scope: `ground_truth/balatro_mod/` (Lua producer), its manifest test, `planning/BRIDGE_SPIKE.md`
Dependencies: user-run game smoke test; no contract, architecture, or policy change
Completed:
- Verified PR #7 is repository-only: it adds a stdlib client for `snapshot.json -> action.txt` and explicit `run_end.json` finalization, but no Lua producer. It is reference material, not oracle evidence.
- Confirmed the installed runtime is suitable in principle: Balatro `1.0.1o-FULL`, Lovely `0.10.0`, Steamodded `26.926.0~dev-a`, mod root `%APPDATA%\Balatro\Mods`. Only `BalatroMultiplayer-0.5.5` and `Brainstorm-2.0.0-alpha-1` are blacklisted; `HandyBalatro`/`JokerDisplay` emit metadata/patch warnings but load. No `agent_bridge.lua` exists in repo or runtime.
- Derived verified game facts read-only from `Mods\lovely\game-dump\`: action callbacks `G.FUNCS.{play_cards_from_highlighted, discard_cards_from_highlighted, select_blind, skip_blind, cash_out, reroll_shop, buy_from_shop, sell_card, use_card, skip_booster, toggle_shop}`; `G.STATES`/`G.STAGES`; `G.GAME.won` set true on win and false at `Game:start_run`; card base suit/value and `Card.highlighted`.
- Added `ground_truth/balatro_mod/` (Steamodded `manifest.json` + `main.lua`) that emits `snapshot.json` (real state/objects/page/action_taken/request_id/runtime meta) and `run_end.json` (win/loss). It does not read saves or copy runtime files.
- Added `tests/test_balatro_mod.py` guarding the manifest shape and the single-JSON-metadata loader invariant.
- Validation: `main.lua` parses (luaparser) and executes against a synthetic game state (lupa) producing valid, aligned `snapshot.json` + `run_end.json`; `py -3 -m unittest tests.test_file_ipc_bridge tests.test_balatro_mod` and `py -3 planning\check_contracts.py` pass; `git diff --check` clean.
Next:
1. User installs the mod with the `planning/BRIDGE_SPIKE.md` procedure, runs the Python client, and plays one run to a real win or loss.
2. Return the `steps.ndjson`/`session.json` field values so the producer can be corrected if the runtime differs from the dump.
3. Open a new Issue #6 PR for the producer and run a fresh-context `@reviewer` (T2).
Decisions: No architecture, component contract, or durable policy changed.
Risks: The producer is validated only against a synthetic state; real-game load order, field names, and file locking are unverified. Action labels are coarse by design. No Phase 0 gate is claimed.
Validation: luaparser syntax OK; lupa harness produced aligned `snapshot.json`/`run_end.json`; `py -3 -m unittest tests.test_file_ipc_bridge tests.test_balatro_mod` -> OK; `py -3 planning\check_contracts.py` -> `planning contracts OK`; `git diff --check` -> clean.
Changed files: `ground_truth/balatro_mod/manifest.json`, `ground_truth/balatro_mod/main.lua`, `tests/test_balatro_mod.py`, `planning/BRIDGE_SPIKE.md`, this thread file.
