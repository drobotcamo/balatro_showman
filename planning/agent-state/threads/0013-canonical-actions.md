# Work Thread
Updated: 2026-09-30
Issue: #13
PR: none
Owner: project-lead
Branch: issue-13-canonical-actions
Worktree: C:\Users\camgr\Documents\code_projects\balatro_showman
Objective: Emit canonical zoned action labels and resolved targets from the oracle.
Status: blocked
Scope: `ground_truth/balatro_mod/main.lua`, audit/tests.
Dependencies: #14 is resolved (D021); #16 supplies related offering-zone observations but is not a repository branch dependency.
Completed: Incorporated the merged #16 offering-zone producer (`TopShelfShopOfferings`, `VoucherShopOfferings`, `PackShopOfferings`, `PackOfferings`) and canonical class-map support. Added action target resolution/subtypes for consumable, sell, shop purchase, and pack selection. Added a pack-only `select_card` hook; hand-card selection remains downstream evidence for `SelectCard` decomposition. Extended the audit for unresolved pack selections. Live run `1790827471-3221` recorded `BuyShopItem_TopShelfShopOfferings_0` with subtype `buytopshelfjoker` and populated offering zones.
Next: Resolve sell-selection source semantics and obtain a completed live run outcome if needed. Keep `SelectCard`/`SWAP` generation in Python granularization per the agreed raw-evidence decision.
Decisions: Reducer owns action-space index/masks (D020); oracle emits engine legality basis/raw evidence (D021).
Risks: Possible sell-target ambiguity when multiple areas are highlighted. The live run ended before `run_end.json`, so audit reports `session.outcome` missing; all action/target assertions passed. Lua syntax/runtime is now exercised by the live run, though `luac` remains unavailable.
Validation: `python planning/check_contracts.py` → `planning contracts OK`; `python -m unittest discover -s tests -q` → 17 passed; `git diff --check` → clean; live run `1790827471-3221` → 7 steps, buy target resolved, offering zones present; audit only failed because the run was not finalized.
