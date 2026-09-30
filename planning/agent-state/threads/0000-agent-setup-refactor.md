# Work Thread
Updated: 2026-09-30
Issue: none
PR: none
Owner: opencode agent-setup session
Branch: master
Worktree: main checkout
Objective: Compact and enforce the agent setup; make agent-workflow.md the single process definition.
Status: ready-for-review
Scope: AGENTS.md, planning/README.md, planning/agent-workflow.md, planning/DECISIONS.md, planning/LEARNINGS.md, planning/TOOLING.md, planning/check_contracts.py, planning/agent-state/, .opencode/, opencode.json, CLAUDE.md, .github/, .gitignore, .claude/settings.local.json
Dependencies: D014 (Markdown planning), GitHub Issue #1 (full approval policy still open)
Completed:
- Committed as c076cbd (not yet pushed; master is 5 commits ahead of origin).
- AGENTS.md reduced to always-load-bearing tenets + Read First pointers (72→45 lines); workflow detail moved to planning/agent-workflow.md, which is now the single definition; duplicated approval/safety/handoff/sub-issue rules deduplicated (231→~200 lines, one section per rule).
- Approval contradiction resolved: AGENTS.md previously allowed unconditional self-approval; single policy now requires a runnable check's output or independent fresh-context review (agent-workflow.md → Approval And Merging).
- Thread naming unified to <issue-number>-<short-name>.md across all 8 referencing files.
- DECISIONS.md reformatted to ADR-lite (D001-D014 + Q01-Q06), all content preserved; LEARNINGS.md template fenced so its example is not parsed as an entry.
- Enforcement added: opencode.json permission rules (deny force-push/hard-reset; ask push/clean/restore/merge/rm -rf), .opencode/agents/explorer.md + reviewer.md (read-only subagents encoding the writer/reviewer pattern), .github work-item issue template + PR template checklist, .github/workflows/planning-check.yml running planning/check_contracts.py.
- Cleanup: stray .opencode/node_modules + package files deleted; .claude/settings.local.json untracked (git rm --cached, gitignored); broken .venv recorded in TOOLING.md with py -3 fallback.
Next:
- Push master and confirm the planning-check workflow runs green on GitHub.
- Comment on Issue #1 pointing at the temp approval rule location; close it when the full policy is decided.
- File first Phase 0 work issues using the new Work item template to exercise the workflow.
Decisions: enforcement design (permissions + CI + templates) follows this session's audit references; recorded here, promote to DECISIONS.md if made durable.
Risks: opencode.json permission schema verified against docs 2026-09-30 but not exercised end-to-end; CI unrun until pushed to GitHub.
Validation: py -3 planning\check_contracts.py → "planning contracts OK"; git diff --check clean; opencode.json parses (json.load OK).