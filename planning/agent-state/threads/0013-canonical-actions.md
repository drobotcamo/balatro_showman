# Work Thread
Updated: 2026-10-01
Issue: #13
PR: #32 (merged 2026-10-01); follow-up changes in current worktree
Owner: project-lead
Branch: issue-13-canonical-actions
Worktree: C:\Users\camgr\Documents\code_projects\balatro_showman
Objective: Emit canonical zoned action labels and resolved targets from the oracle.
Status: complete
Scope: `ground_truth/balatro_mod/main.lua`, audit/tests.
Dependencies: #14 is resolved (D021); #16 supplies related offering-zone observations but is not a repository branch dependency.
Completed: PR #32 is merged. The follow-up diff adds `selljoker`, `sellconsumable`, and `BuyAndUseShopConsumable` target metadata; rejects unknown buy/use object types; validates subtype zones, object types, and canonical label target fields in the audit; and adds synthetic regression fixtures. Fixed ordinary shop Tarot/Planet/Spectral purchases being mislabeled as joker purchases, and guarded unknown pack-offering types. Runtime evidence established that Buy & Use arrives as adjacent `BuyShopItem` plus `UseConsumable` callbacks; D024 now assigns their derived-action coalescing to Python granularization, preserving raw provenance.
Next: Validate the live granularizer against the captured bundle and downstream consumers; no further Lua callback hunt is required unless a future runtime changes the raw sequence.
Decisions: Reducer owns action-space index/masks (D020); oracle emits engine legality basis/raw evidence (D021); Python granularization synthesizes `SWAP_i_j` from observed ordering changes (D023).
Risks: The completed live bundle `F:\OBS_RECORDINGS\oracle_runs\122174123700-6680` covers `SellItem_CurrentJokers_0` but contains no `BuyAndUseShopConsumable` action. The installed producer hash differs from the repository producer and still contains the pre-follow-up `return "consumable"` and `inventory_type(selected) == "consumable"` logic. Therefore this run cannot establish whether the current producer or the game callback semantics are at fault. Fresh reviewer verdict: `holds with gaps`, with runtime evidence still incomplete.
Validation: `python planning/check_contracts.py` → `planning contracts OK`; `python -m unittest tests.test_balatro_mod tests.test_audit_oracle_runs -q` → 19 passed; `python -m unittest discover -s tests -q` → 35 passed; `git diff --check` → clean. Runtime audit: `py -3 planning\\audit_oracle_runs.py F:\\OBS_RECORDINGS\\oracle_runs\\122174123700-6680` → `oracle run integrity OK`, 28 steps, loss; action counts include one `SellItem`, zero `BuyAndUseShopConsumable`. D023 assigns `SWAP_i_j` synthesis to Python; direct Lua SWAP emission is not required.
