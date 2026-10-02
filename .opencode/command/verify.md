---
description: Independently verify the current work item and report a verdict without editing.
agent: reviewer
subtask: true
---
Review the current work item as a fresh-context adversary. Read the issue,
applicable checkpoint, relevant contracts, current diff, and repository state. Re-run the
narrowest relevant checks. Return exactly: claimed outcome, verdict (`refuted`,
`holds with gaps`, or `holds`), reviewed commit SHA/revision, changed files (none), evidence with file and
line references, checks and outputs, and remaining uncertainty. Do not edit
files or approve a claim you could not verify.
