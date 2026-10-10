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

The Lua producer writes snapshots to `%APPDATA%\Balatro\agent_io`; the
repository bridge consumes them, acknowledges each action, and writes one run
directory containing `session.json` and `steps.ndjson`.
This recipe exercises oracle delivery, not verified video capture. Before
inviting a user to make a video or associating a run with one, follow the
existing-evidence inventory, live preflight and human checkpoint in
`planning/RUN_BUNDLE_OPERATIONS.md`. Do not treat the dated paths or producer
build in this recipe as current without checking the loaded runtime.

1. Install the producer revision using the reversible, hash-checked procedure
   in `planning/BRIDGE_SPIKE.md` → Installation. It keeps the previous mod tree
   outside `Mods`, avoiding duplicate mod IDs. Restart Balatro completely and
   verify both the source/installed SHA-256 and the loaded build in the latest
   Lovely log before starting a capture.
2. From the repository root, start the recorder before starting a run:

   ```powershell
   py -3 ground_truth\file_ipc_bridge.py `
     --out-dir "F:\OBS_RECORDINGS\oracle_runs"
   ```

   The default IPC directory is `%APPDATA%\Balatro\agent_io`. Use
   `--io-dir` only when the game uses a different directory. Leave this
   process running while playing; stop it with Ctrl+C after the run ends.
3. Start a new Balatro run and play through the states being evaluated. For
   shop/pack offering coverage, enter the shop and open at least one booster
   pack. A clean audit requires the run to end in a win or loss so
   `run_end_<run_id>.json` supplies the terminal request watermark; the bridge
   finalizes `session.json` after every request through that watermark persists.
4. Find the new child directory under the `--out-dir` path. Its name is the
   producer `run_id`, for example `1790821374-5833`.
5. Audit it from the repository root:

   ```powershell
   py -3 planning\audit_oracle_runs.py `
     "F:\OBS_RECORDINGS\oracle_runs\<run_id>"
   ```

   For offering coverage, confirm `oracle run integrity OK`,
   `offering_objects_total > 0`, all expected names in
   `offering_zones_present`, an empty `offering_zones_missing`, and
   `offering_position_missing: 0`.

The bridge records the producer's `action_taken`; it does not choose actions.
If the run is stopped before win/loss, inspect `steps.ndjson` directly for
partial evidence, but expect the integrity audit to reject a null session
outcome. External run directories are evidence only and must not be committed.
When finished testing, restore the backed-up mod file if the staged producer
was not intended to remain installed.

Known machine-specific evidence: the verified capture used Balatro
`1.0.1o-FULL`, Steamodded `26.926.0~dev-a`, Lovely `0.10.0`, and output under
`F:\OBS_RECORDINGS\oracle_runs` on 2026-09-30/2026-10-01.

Add commands here only after they have been run successfully in this repository.
Each recipe must state its working directory, inputs, expected result, and known
failure modes.

## Rules

- Verify every recipe before recording it.
- Label platform- or machine-specific behavior.
- Never record secrets, tokens, passwords, or credential values.
- Prefer portable commands when both portable and local forms are reliable.
- Update or remove recipes when they stop working.
