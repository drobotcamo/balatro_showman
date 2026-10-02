---
description: Execute one bounded work item with evidence, review, and handoff discipline.
agent: lead
---
Act as the project lead for this bounded work item: $ARGUMENTS

Use the lead loop in your agent instructions. First inspect the repository and
the relevant planning artifacts; then make progress without waiting for
permission on routine work. Delegate only independent research or fresh-context
review. Stop and ask the user before changing architecture, contracts,
project direction, or durable policy. Finish with verified changes, checks run,
remaining uncertainty, and an updated thread baton.

For T2 work, the lead must record a fresh-context `@reviewer` verdict of
`holds` and its evidence on the PR before merge. `holds with gaps` or `refuted`
blocks merge unless the permitted exception is explicitly recorded. Verify
review, CI, base/diff, dependency, merge, and settlement gates separately; a
merged PR without review evidence is a process violation, not completion.

Before handoff or completion, workers must leave no owned worktree leftovers:
run `git status`, commit all worker-owned changes and the baton in the PR, and
remove worker-created temporary or generated artifacts. Never delete unrelated
pre-existing user or worker changes; identify and exclude them instead.
