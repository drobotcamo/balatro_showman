# Lead launch prompt

Paste the block below into a fresh lead-agent session opened in the existing
checkout. It is a direct assignment; `/work` or `/orchestrate` is unnecessary.
If starting in a different checkout, first bring over the inspected local review
inputs listed in section 3 of the implementation plan; they are not yet committed.

```text
Act as the implementation lead for the production-focused workflow migration.
Execute the plan; do not produce another plan in place of implementation.

Read AGENTS.md, planning/WORKFLOW_MIGRATION_IMPLEMENTATION_PLAN.md,
planning/PRODUCTION_RETROSPECTIVE_2026-10-02.md, D028 in planning/DECISIONS.md,
and planning/agent-state/threads/0000-production-retrospective.md. Then inspect
the relevant current workflow, repository and GitHub state. The user approved
progressive gates, removal of mandatory settlement-only PRs and new issue tags,
and the recorded-run -> evaluation-slice -> video-reconstruction sequence.

Own one bounded migration issue and one implementation PR. Find an existing
equivalent first. You may create/update the issue, create a suitable branch,
commit the intended changes, push, open the PR and merge after the required
checks and independent review, subject to actual host/repository permissions.
Register the implementation PR with the thread. Do not reuse closed WAVE work
or create separate design/test/documentation/settlement issues for this task.

Preserve all existing local work. The approval, retrospective and handoff are
uncommitted inputs; a fresh worktree will not contain them automatically. The
pre-existing untracked does-not-exist.db is unrelated: preserve and exclude it.
Account explicitly for the reviewed input files before moving branches/worktrees.

Summon the bounded subagents in plan section 4: explorer A for instruction and
validator migration; explorer B for roadmap and existing issue reconciliation;
explorer C for production-readiness/diagnostic evidence where useful; and a
fresh reviewer D for the integrated diff at an identified revision. Run A/B in
parallel if supported. Current lead permissions allow read-only explorer and
reviewer agents: use them, keep all tracked edits and GitHub mutations with
yourself, and do not broaden permissions or invent implementation-worker roles.
Run fixture-writing diagnostics yourself; explorers inspect source and supplied
output. Do not duplicate their research. Supply precise scope and require evidence.

Implement the file-level checklist and acceptance scenarios in sections 5-9.
Consolidate the execution loop, remove completion-record recursion, preserve
historical tags/checkpoints, fix validators together with their consumers, define
reviewed-SHA evidence once, and reconcile #79-#82 with progressive delivery.
Use GitHub for live completion state and a compact checkpoint for unfinished work.
Keep independent review, uncertainty, provenance, protected branches and meaningful
validation. Do not replace old phrase-presence tests with new ones and call that
behavioral enforcement. Load customization guidance when editing OpenCode files.

CI triggers/required checks, branch protection, permissions, new dependencies,
transport redesign, asset promotion and substantive product interface changes
still need specific approval. Prepare an exact request where needed; continue
independent approved work. Do not invent thresholds, gate passes, recording
confirmation or clean-checkout test success. No historical cleanup campaign.

Run the relevant tests and planning/tag/diff checks, independently review the
final diff, resolve material findings, and integrate when authorized. Record
post-merge evidence on the same issue/PR; no settlement-only follow-up PR.
If a real permission, evidence or decision blocker remains, leave one verified
checkpoint with exact results, ownership and next action instead of claiming done.
If publication is blocked, inventory unpublished work and request the precise
D027 exception or missing action; D028 alone does not waive its PR requirement.

Finish with implemented changes, validation and review evidence, issue/PR/merge
references, remaining blockers, and the concrete next action for #81. Sections
10-13 preserve the production findings and acceptance cases for that next task;
do not mix recorder rewrites into this migration or lose those findings. Stop
after the migration and actionable production handoff, not after another proposal.
```
