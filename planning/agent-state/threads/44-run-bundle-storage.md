# Work Thread
Updated: 2026-10-01
Issue: #44
PR: none
Owner: project lead
Branch: issue-44-run-bundle-storage
Worktree: C:\Users\camgr\Documents\code_projects\balatro_showman
Objective: Implement the approved SQLAlchemy/Alembic SQLite run-bundle persistence boundary.
Status: active
Scope: run_bundle/, alembic/, pyproject.toml, tests/test_run_bundle.py, planning/RUN_BUNDLE_STORAGE.md
Dependencies: D024; parent #34; downstream #45-#47
Completed:
- Added SQLAlchemy 2.x models for runs, records, provenance, integrity, and schema versions.
- Added repository API for creation, append/append_raw, lifecycle transitions, immutable finalized evidence, and SHA-256 validation.
- Added explicit Alembic initial migration and storage/concurrency documentation.
- Focused lifecycle and migration-backed fixture tests pass: 9 passed.
- planning/check_contracts.py and git diff --check pass.
Next:
- Resolve remaining review blockers (fresh/upgrade migration test and persisted integrity failure assertions), then open T2 PR.
- Obtain fresh-context reviewer verdict on final diff, run full checks, and merge if CI permits.
Decisions: D024; malformed source bytes are preserved through append_raw without repair.
Risks: migration upgrade-from-previous revision is not yet covered; full acceptance suite still needs integrity persistence assertions.
Validation: `python -m pytest tests/test_run_bundle.py -q` => 9 passed; `python planning/check_contracts.py` => planning contracts OK; `git diff --check` => clean.
