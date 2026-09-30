# Tooling Reference

Verified commands and environment-specific procedures for this repository.
This is a maintained runbook, not a log of every command ever attempted.

## Environment

- Platform: Windows
- Shell: PowerShell 7+
- Repository root: `C:\Users\camgr\Documents\code_projects\balatro_showman`
- Python environment: repository `.venv` when available

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

Add commands here only after they have been run successfully in this repository.
Each recipe must state its working directory, inputs, expected result, and known
failure modes.

## Rules

- Verify every recipe before recording it.
- Label platform- or machine-specific behavior.
- Never record secrets, tokens, passwords, or credential values.
- Prefer portable commands when both portable and local forms are reliable.
- Update or remove recipes when they stop working.
