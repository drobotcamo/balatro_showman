# Work Thread
Updated: 2026-09-30
Issue: #21
PR: none yet
Owner: opencode Phase 0 lead session (issue-21)
Branch: issue-21-raw-persistent-fields
Worktree: `C:\Users\camgr\.t3\worktrees\balatro_showman\t3code-bd4f320d`
Objective: Emit engine-truth raw persistent fields and the engine's legal actions/mask basis from the Lua producer under a transport version distinct from the granularized `3.0.0`, and report their coverage in the audit tool (D021).
Status: ready-for-review
Scope: `ground_truth/balatro_mod/main.lua`, `planning/audit_oracle_runs.py`, `tests/test_audit_oracle_runs.py`, `planning/BRIDGE_SPIKE.md`, `planning/LEARNINGS.md`
Dependencies: Parent #10; D021 (option c), D009, D020; `mask_schema.md` §2-3; `state_schema.md` §3.
Completed:
- `main.lua` emits `live/3.0.0` snapshots with `raw_persistent` (deck center_key/class_id from `G.GAME.selected_back_key`; stake level/center_key resolved via `G.P_CENTERS.stake_level` scan; `starting_params.no_faces`; verbatim `G.GAME.modifiers`; `tracked_deck_cards` from `G.playing_cards` with modifier/edition/seal/stickers; per-hand level/played/played_this_round; sorted voucher keys; `bosses_used` count dict; `blind_states`/`blind_choices`/`blind_tags`; `boss_rerolled`; `skips`/`hands_played`/`unused_discards`/`ecto_minus`/`last_tarot_planet`), `legal_actions` (mask_schema §2 page gating + §3 availability; action about to run always included because the file-IPC client rejects snapshots without it), and `mask_basis` (`reroll_cost`, `free_rerolls`, selection counts). All engine reads failure-isolated; unavailable → explicit null. `persistent_state` stays `{}` (reducer owns canonical shape).
- Executed verification: external lupa (Lua 5.1) harness (temp dir, not checked in) runs `main.lua` against a stub `G`: raw fields, legality across blind/shop/pack/unaffordable/untagged/unknown pages, and file-IPC client acceptance all pass (`HARNESS OK`). Engine field names verified against `%APPDATA%\Balatro\Mods\lovely\dump\` (recorded in `LEARNINGS.md`).
- `planning/audit_oracle_runs.py`: schema-aware required fields (`live/3.0.0` requires `raw_persistent`/`legal_actions`/`mask_basis`; `live/2.0.0` known-legacy), raw leaf-field presence counts, mask-basis coverage, `legal_actions_nonempty`/`action_in_legal_actions`/`legal_action_labels`, and non-fatal findings for legacy runs, null counters, missing legality, and client-contract violations. Integrity exit semantics unchanged.
- Tests: 5 new audit tests (full coverage, integrity on missing raw fields, legacy finding, client violation, null counters); 17 tests pass.
- Extended audit of the two persisted `live/2.0.0` runs reports integrity OK plus the new raw-field/legality findings (legacy schema finding, legality absent on 43/43, client violation on 43/43).
Next:
- Open PR, paste test + harness + audit outputs, obtain `@reviewer` fresh-context verdict, verify CI, merge (T2).
- Fresh pinned-revision capture through the audit remains deferred to #16/#11 (manual game capture); the Done-When "fresh run emits" bullet is evidence-backed by the harness but not yet by a persisted run.
Decisions: Transport label chosen as `live/3.0.0` within D021's boundary (documented in `BRIDGE_SPIKE.md`: `live/X.Y.Z` is the producer snapshot contract, never the granularized `3.0.0`). No contract or decision file changes; raw-field key named `raw_persistent` to avoid the canonical `persistent_state` shape (D021).
Risks: No persisted run at `live/3.0.0` yet (P6 capture pending). Lua verified by harness execution against a stub, not the installed game; Steamodded stake-center resolution assumed uniform for SMODS stake mods. `bosses_used` increments on boss selection, so counts may exceed "defeated" semantics; raw dict is emitted verbatim and the reducer derives the canonical list. Vendored tree required locally for `tests.test_class_ids` (populated from main checkout, not committed).
Validation: `py -3 -m unittest tests.test_balatro_mod tests.test_file_ipc_bridge tests.test_class_ids tests.test_audit_oracle_runs -v` → 17 OK; lupa harness → `HARNESS OK`; `py -3 planning\audit_oracle_runs.py <two persisted runs>` → `oracle run integrity OK` with new findings; `py -3 planning\check_contracts.py` → `planning contracts OK`; `git diff --check` → clean.