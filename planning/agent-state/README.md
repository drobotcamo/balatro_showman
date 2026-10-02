# Agent State

Unfinished-work checkpoints for GitHub-Issue work items. A thread is not an
OpenCode session: multiple sessions may continue one thread, and one session
may work on more than one issue.

## Layout

- `threads/<issue-number-or-tag>-<short-name>.md`: optional unfinished-work checkpoint. Use the
  template in `../agent-workflow.md` → Handoff Protocol; this file does not
  restate it.
- `archive/`: completed or abandoned threads, created when first needed.

Thread files are branch-scoped and become shared through Git; they are not
live locks. Coordinate parallel worktrees with Issue, branch, Git status, and
PR state. Do not assume another worktree sees uncommitted edits. Never use
Markdown as a concurrency lock.

GitHub owns live completion. Historical full-format records and new compact
checkpoints are valid as-of context. A pre-merge record need not be rewritten
when GitHub completes later; no normal completion requires a settlement PR.
