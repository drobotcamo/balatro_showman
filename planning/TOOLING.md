# Tooling Reference

Verified commands and environment-specific procedures for this repository.
This is a maintained runbook, not a log of every command ever attempted.

## Environment

- Platform: Windows
- Shell: PowerShell 7+
- Repository root: `C:\Users\camgr\Documents\code_projects\balatro_showman`
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

Add commands here only after they have been run successfully in this repository.
Each recipe must state its working directory, inputs, expected result, and known
failure modes.

## Rules

- Verify every recipe before recording it.
- Label platform- or machine-specific behavior.
- Never record secrets, tokens, passwords, or credential values.
- Prefer portable commands when both portable and local forms are reliable.
- Update or remove recipes when they stop working.
