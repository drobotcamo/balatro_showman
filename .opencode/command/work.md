---
description: Execute one bounded outcome through validation, review and authorized integration.
agent: lead
---
Own this work item: $ARGUMENTS

Follow `AGENTS.md` and `planning/agent-workflow.md` → Lead Loop and Approval And
Merging. Start relevant inspection and implementation directly. Use Handoff
Protocol only for unfinished work needing fresh context, not a completion mirror.

Treat all issue acceptance criteria as the outcome. After each implementation,
test or review slice, recheck what remains and continue in this same issue/branch
while any criterion can proceed without new user input. Do not stop at a focused
green test, one reviewed PR slice, or a success summary. If a genuine external
decision/evidence checkpoint is reached, finish independent approved work first,
ask for the exact missing input, and state the remaining acceptance items.
Finish every independently executable acceptance item and verify the blocker
first. Context exhaustion means checkpoint/resume this issue, not completion.
