# Work Thread
Updated: 2026-10-01
Issue: #47
PR: none
Owner: project lead
Branch: t3code/7b860ec2
Worktree: C:\Users\camgr\.t3\worktrees\balatro_showman\t3code-7b860ec2
Objective: Add read-only compatibility access to currently available Lua oracle run artifacts.
Status: active
Scope: run_bundle/compatibility.py, run_bundle/__init__.py, tests/test_run_bundle_compatibility.py, this thread
Dependencies: D024; Issues #44 and #45; no SQLite conversion or source mutation
Completed:
- Added `read_oracle_run` for `session.json` plus `steps.ndjson`, preserving parsed source objects.
- Classifies parseable artifacts as healthy or partial and malformed sources diagnostically; exposes `obs` versus `no-video` provenance.
- Reports source directory, file sizes, and SHA-256 hashes; does not write or repair source artifacts.
- Added healthy, partial, malformed, non-object, provenance, OBS, and immutability tests.
Next:
- Commit changes, open PR, and obtain required CI plus fresh reviewer verdict before merge.
Decisions: D024 read-only compatibility; no in-place migration or unstable-field promotion.
Risks: Exact downstream compatibility envelope is not separately specified; adapter intentionally returns raw session/step objects and diagnostics.
Validation: `python -m pytest -q tests/test_run_bundle_compatibility.py tests/test_run_bundle_inspection.py tests/test_run_bundle.py` -> 31 passed; `python planning/check_contracts.py` -> planning contracts OK; `git diff --check` -> clean.
