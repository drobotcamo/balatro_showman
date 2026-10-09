# Tooling Reference

Verified commands and environment-specific procedures for this repository.
This is a maintained runbook, not a log of every command ever attempted.

## Environment

- Platform: Windows
- Shell: PowerShell 7+
- Repository root: the active checkout/worktree (`git rev-parse --show-toplevel`);
  `C:\Users\camgr\Documents\code_projects\balatro_showman` is one historical
  checkout, not necessarily the current worktree.
- Python environment: repository `.venv` when available; `py -3` as fallback

### Python interpreter

```powershell
.venv\Scripts\python.exe --version
py -3 --version
```

Known failure modes: the checked-in `.venv` can point at a missing base
interpreter (verified 2026-09-30: it referenced `C:\Python311\python.exe`,
which does not exist) and then fail for any command. When `.venv` is broken,
use `py -3`. Plain `python` is not on PATH in this shell.

## Git And GitHub

Commands below are run from the repository root unless stated otherwise.

### Inspect worktree

```powershell
git status --short
git branch --show-current
```

Success: current branch and uncommitted paths are visible before editing.

### Inspect open Issues

```powershell
gh issue list --state open
```

Requires authenticated GitHub CLI access to the repository.

### Check documentation whitespace

```powershell
git diff --check
```

Success: no whitespace errors are reported.

## Project Checks

### Validate planning documents

```powershell
py -3 planning\check_contracts.py
```

Working directory: repository root. Stdlib only, no inputs. Success:
`planning contracts OK`, exit code 0. Failure: one `FAIL:` line per problem
and exit code 1; CI runs the same script (`.github/workflows/planning-check.yml`).

### Audit a persisted oracle run

```powershell
py -3 planning\audit_oracle_runs.py RUN_DIR [RUN_DIR ...]
```

Working directory: repository root. Inputs: one or more run directories, each
containing `session.json` and `steps.ndjson` as written by
`ground_truth/file_ipc_bridge.py`. Success: per-run JSON summaries followed by
`oracle run integrity OK`, exit code 0. Failure: `FAIL:` lines and exit code 1
when an integrity invariant breaks (step-count mismatch, duplicate/missing
`request_id`, run-id mismatch, invalid outcome, missing required field).
Conformance gaps (coarse actions, empty `persistent_state`, missing
`frame_idx`) are reported as findings but do not fail the audit. Verified
2026-09-30 against the two `F:\OBS_RECORDINGS\oracle_runs\` runs from Issue #6.

### Record a live oracle run

The current command and default location are in `docs/capture/README.md` →
“Record a new session” and `docs/capture/archive.md` → “Capture going
forward.” Use `planning/RUN_BUNDLE_OPERATIONS.md` for the staged live preflight
and recording-association checkpoint. These guides require the installed and
loaded producer checks, one IPC consumer, an already migrated catalog and
paired `captures`/`catalog.sqlite` paths. Never infer that a run was imported
because a directory exists.

The `F:\OBS_RECORDINGS\oracle_runs` root and the standalone bridge command in
older Issue #6 procedures describe historical evidence. They are not the
destination for a new operational catalog capture. The 2026-09-30/2026-10-01
captures used Balatro `1.0.1o-FULL`, Steamodded `26.926.0~dev-a` and Lovely
`0.10.0`; recheck the loaded runtime before any new capture.

Add commands here only after they have been run successfully in this repository.
Each recipe must state its working directory, inputs, expected result, and known
failure modes.

## Rules

- Verify every recipe before recording it.
- Label platform- or machine-specific behavior.
- Never record secrets, tokens, passwords, or credential values.
- Prefer portable commands when both portable and local forms are reliable.
- Update or remove recipes when they stop working.
