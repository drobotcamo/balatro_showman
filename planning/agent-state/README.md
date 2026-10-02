# Agent State

Work-thread handoff batons for GitHub-Issue work items. A thread is not an
OpenCode session: multiple sessions may continue one thread, and one session
may work on more than one issue.

## Layout

- `threads/<issue-number-or-tag>-<short-name>.md`: one handoff per work item. Use the
  template in `../agent-workflow.md` → Handoff Protocol; this file does not
  restate it.
- `archive/`: completed or abandoned threads, created when first needed.

Thread files are branch-scoped and become shared through Git; they are not
live locks. Coordinate parallel worktrees with Issue, branch, Git status, and
PR state. Do not assume another worktree sees uncommitted edits. Never use
Markdown as a concurrency lock.
