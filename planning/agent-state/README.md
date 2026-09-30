# Agent State

This directory stores supplemental handoffs for GitHub-Issue work items. A work
thread is not an OpenCode session: multiple sessions may continue the same
branch/worktree, and one session may work on more than one issue.

## Layout

- `threads/<issue-number>-<short-name>.md`: one handoff per Issue/work item.
- `archive/`: completed or abandoned threads when history is useful.

Each thread should include its ID, owner, branch, worktree, status, objective,
scope, dependencies, completed work, next actions, risks, and validation.

## Parallel Worktrees

GitHub Issues define work and PRs define integration. These files are
branch-scoped and become shared through Git; they are not live locks. Coordinate
parallel worktrees with Issue, branch, Git status, and PR state. Do not assume
another worktree sees uncommitted edits. Never use Markdown as a concurrency
lock.
