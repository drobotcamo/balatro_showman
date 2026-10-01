# Work Thread
Updated: 2026-09-30
Issue: #12
PR: https://github.com/drobotcamo/balatro_showman/pull/24
Owner: opencode Phase 0 lead session (issue-12)
Branch: issue-12-canonical-object-ids
Worktree: `C:\Users\camgr\Documents\code_projects\balatro_showman` (in-place; vendored class map is a gitlink absent from linked worktrees)
Objective: Emit canonical `class_id`s for inventory objects and modifier/edition/seal/sticker attributes for card and inventory objects, and make the oracle audit report those conformance gaps.
Status: ready-for-review
Scope: `ground_truth/balatro_mod/main.lua`, `ground_truth/generate_class_ids.py`, `planning/audit_oracle_runs.py`, `tests/test_class_ids.py`, `tests/test_audit_oracle_runs.py`, `planning/LEARNINGS.md`
Dependencies: Parent #10; D003 (class map), D004 (composition labels), D009/D021 (raw fields, reducer owns persistent state). Not blocked by #14.
Completed:
- Embedded the vendored `center_key` -> `class_id` table in `main.lua` (348 non-card entries) generated from `legacy/vendor/balatro-policy-transformer/data/class_map.csv` by `ground_truth/generate_class_ids.py`; `--check` is deterministic.
- Inventory objects now emit a real `class_id`; an unmapped `center_key` keeps `class_id:null` and is retained verbatim (never guessed). Playing, pending, and inventory objects emit `modifier`/`edition`/`seal` (null when absent) and list-valued `stickers`, per `state_schema.md` §3.
- Field semantics verified read-only against the installed dump (`card.config.center.key`, `card.edition.type`, `card.seal`, `card.ability.rental/perishable/eternal`); recorded in `LEARNINGS.md`.
- Extended `planning/audit_oracle_runs.py`: `inventory_class_id_present/null`, per-attribute presence, `object_attribute_all_null`, `object_stickers_not_list`, pending-card conformance, and non-fatal `FINDING:` output; integrity exit semantics unchanged.
- Tests: class-map embedding matches the CSV exactly; audit conformance logic covered. 12 tests pass.
- Extended audit run on the two existing persisted (pre-fix) runs detects 2138/2138 and 57/57 inventory `class_id:null` plus all-null attribute columns, confirming the reporting.
Next:
- Record the reviewer verdict on PR #24 and merge once required CI is green and residual gaps are accepted.
- Fresh pinned-revision capture (owned by #16/#11) must be run through the audit to demonstrate zero `class_id:null` and zero all-null attribute columns on a live run; this issue's Done-When cannot be fully demonstrated without it.
Decisions: No contract, decision, or architecture change. Object shape follows the adopted vendored schema. Vouchers are in the mapping but still not emitted (P5/#16).
Reviewer: fresh-context `@reviewer`, task `ses_f0b1a7e11ffexXb5W7k7PXTPwL`, verdict **holds with gaps**. Independently confirmed the embedded table equals the CSV (348/348, exact), null-vs-string JSON discipline, audit exit semantics, 12 tests, `check_contracts.py`, and generator `--check`. Gaps: (A) `voucher` is mapped but not emitted (claim wording); (B) stone cards may be dropped by the pre-existing `card_fields` path, so `modifier="m_stone"` may never be emitted (not a regression, out of scope); (C) CI runs only `check_contracts.py`, not the new tests; (D) the new test/generator require the untracked vendored class map locally; (F) vendored consumers inspected but not executed. Gap (E) missing thread file is fixed by this file.
Risks: No Lua interpreter is available in-repo, so `main.lua` was verified by static reasoning against the game dump, not executed. All-null attribute columns are data-dependent; a run lacking an attribute type will legitimately report it. The vendored class map is a gitlink with no `.gitmodules`, so tests are reproducible only where the vendor tree is populated.
Validation: `py -3 -m unittest tests.test_balatro_mod tests.test_file_ipc_bridge tests.test_class_ids tests.test_audit_oracle_runs -v` -> 12 tests OK; `py -3 planning\check_contracts.py` -> `planning contracts OK`; `py -3 ground_truth\generate_class_ids.py --check` -> `class ID table is up to date`; `git diff --check` -> exit 0 (LF/CRLF warning only); extended audit on the two persisted runs -> integrity OK with the new FINDING lines.
