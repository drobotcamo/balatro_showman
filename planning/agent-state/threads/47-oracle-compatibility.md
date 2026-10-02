# Work Thread
Updated: 2026-10-01
Issue: #47
PR: #57 (https://github.com/drobotcamo/balatro_showman/pull/57), merged at `af32ef7`; retrospective docs PR #65
Owner: project lead
Branch: t3code/7b860ec2
Worktree: C:\Users\camgr\.t3\worktrees\balatro_showman\t3code-7b860ec2
Objective: Add read-only compatibility access to currently available Lua oracle run artifacts.
Status: complete
Scope: run_bundle/compatibility.py, run_bundle/__init__.py, tests/test_run_bundle_compatibility.py, this thread
Dependencies: D024; Issues #44 and #45; no SQLite conversion or source mutation
Completed:
- Added `read_oracle_run` for `session.json` plus `steps.ndjson`, preserving parsed source objects.
- Classifies parseable artifacts as healthy or partial and malformed sources diagnostically; exposes `obs` versus `no-video` provenance.
- Reports source directory, file sizes, and SHA-256 hashes; does not write or repair source artifacts.
- Added healthy, partial, malformed, non-object, provenance, OBS, and immutability tests.
- Retrospective fresh-context review confirmed the core read-only and provenance claims, but found no recorded reviewer verdict on merged PR #57 and identified unspecified behavior for incomplete session metadata and blank NDJSON lines.
Next:
- None for the settled issue. If compatibility validation is expanded, resolve the session-field and blank-line questions in a separately scoped change before adding enforcement.
Decisions: D024 read-only compatibility; no in-place migration or unstable-field promotion.
Risks: Exact downstream compatibility envelope is not separately specified; adapter intentionally returns raw session/step objects and diagnostics. Reviewer found incomplete session metadata classified as healthy and blank lines classified as malformed; neither behavior is changed because the issue is settled and the contract does not specify them. PR #57 has no GitHub review record despite successful CI and merge.
Validation: `python -m pytest -q tests/test_run_bundle_compatibility.py tests/test_run_bundle_inspection.py tests/test_run_bundle.py` -> 32 passed; `python planning/check_contracts.py` -> planning contracts OK; `git diff --check` -> clean; PR #57 CI -> passed; fresh-context reviewer -> holds with gaps (retrospective evidence recorded above); PR #65 CI -> passed.
