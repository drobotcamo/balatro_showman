## Issue

Tag:

Closes #

Tier: T0 planning/process | T1 contract (user approval required) | T2 code (agent merges when green)

## What changed

Scope, files, and components touched.

## Validation

Commands run and their results (paste output; inspection alone is not evidence
for reconstruction-quality claims).

## Remaining uncertainty

What could not be verified, and why it is acceptable.

## Planning updates

- [ ] Component contract updated if its interface, invariants, or status changed
- [ ] Thread file updated (`planning/agent-state/threads/`)
- [ ] Durable decisions in `DECISIONS.md` / findings in `LEARNINGS.md`
- [ ] `python planning/check_contracts.py` passes

## Review notes

What a reviewer should check first; what cannot be verified automatically.

## T2 Merge Evidence

- [ ] Fresh-context `@reviewer` verdict is `holds` for the current diff
- [ ] Reviewer task and evidence are recorded on this PR
- [ ] CI is green and the PR base, current diff, and dependency order were checked separately
- [ ] Merge commit and Issue/thread settlement were verified after merge
- [ ] If already merged without review evidence, this is recorded as a process violation
- [ ] `git status` was inspected and no worker-owned leftovers remain outside this PR
