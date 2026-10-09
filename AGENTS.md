# Agent Operating Contract

This repository is developed by a sequence of human and AI agents. The source
of truth is the checked-in repository, not conversation history.

The project reconstructs Balatro game state from recorded video, validated
against a Lua ground-truth oracle. `planning/README.md` is the planning index.

## Read First

- Using capture/storage/inspection: start with `docs/capture/README.md` for
  Showman Capture's vocabulary, task commands, and API/result meanings.
- For the F-drive recording catalog, read `docs/capture/archive.md` before
  selecting paths or invoking archive commands. Use the configured
  `SHOWMAN_ARCHIVE_ROOT`; a producer session is not necessarily a whole play,
  and an OBS marker is not a confirmed video association. Never retarget an
  active recorder/OBS or move its evidence. Inventory, hash-check and preserve
  historical originals when staging into the catalog.
- For a new run, follow `docs/capture/README.md` → “Record a new session” →
  `docs/capture/archive.md` → “Capture going forward” →
  `planning/RUN_BUNDLE_OPERATIONS.md` → “Existing Evidence And Capture
  Preflight.” Use `planning/BRIDGE_SPIKE.md` for installation/loaded-build
  checks, `planning/BALATRO_RUNTIME.md` for dated machine evidence, and
  `docs/capture/video-review.md` for video QA. The copy-paste recorder command
  is in the capture README; dated issue-specific roots in older runbooks are
  evidence locations, not new destinations.
- Resuming work: read the relevant
  `planning/agent-state/threads/<issue-number-or-tag>-<short-name>.md`.
- Changing a component: read its contract in `planning/components/` first.
- Starting a work item, branching, reviewing, approving, merging, handing off,
  or checkpointing context: follow `planning/agent-workflow.md`. It is the
  single definition of work-item, approval, subagent, and handoff rules; this
  file does not restate them.
- Inspect `git status`, the GitHub Issue, branch, PR, and worktree before
  editing. Preserve changes you did not make.
- For run-bundle operations, read `planning/RUN_BUNDLE_OPERATIONS.md`. Use
  `python -m run_bundle ...` for read-only inspection; pause at the documented
  terminal checkpoint before recording association and request user input when
  the summary is incomplete or disputed.
- For video capture or association, inventory existing evidence and use the
  staged live preflight in `planning/RUN_BUNDLE_OPERATIONS.md` before asking for
  a new recording. Do not ask the user to inspect files or identify opaque run
  IDs; prepare a visual example and plain-language pairing for confirmation.

## Local Balatro Source

On Cam's Windows machine, the Steam installation is at
`C:\Program Files (x86)\Steam\steamapps\common\Balatro`. The game's Lua source
is inside `Balatro.exe` as an embedded ZIP archive; Python's `zipfile` can read
it directly without extracting files or changing the installation.

Verified on 2026-10-03: the archive contains 47 Lua files, including `main.lua`,
`game.lua`, `card.lua`, `blind.lua`, and `globals.lua`. To inspect a source file:

```powershell
python -c "import zipfile; p=r'C:\Program Files (x86)\Steam\steamapps\common\Balatro\Balatro.exe'; z=zipfile.ZipFile(p); print(z.read('game.lua').decode('utf-8'))"
```

## Tenets

- Correctness and provenance come before throughput or demos.
- Contracts, schemas, and phase gates are interfaces between agents. Do not
  silently broaden scope, change a contract, or skip a phase gate.
- Major design decisions require user input before implementation.
- Unknown, ambiguous, and low-confidence results are first-class outputs.
- Prefer the smallest change that makes a measurable step toward the current
  gate. When stuck, try a materially different approach, preserve evidence,
  and report the change in direction.
- Validate against the Lua oracle or a declared evaluation protocol;
  inspection alone cannot support claims about reconstruction quality.
- Keep laptop development practical without breaking batch-GPU contracts.
- Record durable decisions in `planning/DECISIONS.md` and verified findings in
  `planning/LEARNINGS.md` — never only in chat.

## Completion Standard

- Run the narrowest relevant tests or checks and report their output.
  Planning documents are mechanically validated by `planning/check_contracts.py`
  (thread naming and handoff fields, decision/learning formats, open-question
  linkage, component sections, roadmap ownership and gates, and reference
  resolution), not for prose quality or gate thresholds.
- Report what changed, what was verified, and what remains uncertain.
- Update affected contracts; checkpoint unfinished work when fresh context is
  needed. Capture reusable findings; record live completion on the PR/issue.
- A completion claim requires a runnable check's output or an independent
  fresh-context review (`planning/agent-workflow.md` → Approval).

## Technical Prose

- Apply `.opencode/skill/deslop/SKILL.md` to pull request descriptions, issue
  updates, handoffs, review summaries, and other lengthy technical prose.
- Preserve concrete evidence and uncertainty while removing filler, formulaic
  AI phrasing, and repetitive summaries.
- Submit PR and issue bodies with actual line breaks. Before submission, check
  that literal `\\n` does not appear unless it is intentional code content.
- On PowerShell, avoid nested quoting for substantial multiline GitHub or CLI
  bodies; create a real temporary body file or use a supported heredoc pattern,
  inspect it, and pass it with the command's file option. This prevents shell
  parsing failures and preserves the intended line breaks.

## Safety

- Never commit secrets, credentials, generated data, or unreviewed vendored
  artifacts. Never use destructive git commands to resolve ambiguity.
- Ask the user before changing architecture, contracts, project direction, or
  durable policy.
