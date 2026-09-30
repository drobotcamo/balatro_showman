# Work Thread
Updated: 2026-09-30
Issue: #1
PR: none
Owner: opencode agent-setup session
Branch: master
Worktree: main checkout
Objective: Define the full approval policy (Issue #1) and make its checks required.
Status: complete
Scope: planning/agent-workflow.md, planning/DECISIONS.md, .github/PULL_REQUEST_TEMPLATE.md, branch protection
Dependencies: D015; enforcement layer from commit c076cbd
Completed: policy designed with user via tiered-evidence proposal; all four knobs answered (T0 direct commits, user approves substantive T1, agents merge green T2, planning-check required); written into agent-workflow.md → Approval And Merging; D015 recorded; PR template tier line added; repo made public (owner decision) and branch protection configured (required check `check`, enforce_admins, no force-push/delete); pre-public audit clean (no secret patterns in 15.6 MB full-history scan, no tracked binaries/assets, submodules public upstream); Issue #1 closed.
Next: none. First Phase 0 issue exercises T2.
Decisions: D015, D016.
Risks: enforce_admins=true means emergency fixes require temporarily disabling protection; required check binds only PR merges, direct pushes to master are still possible (by design for T0).
Validation: py -3 planning/check_contracts.py → OK; protection GET confirms required_checks=[check], enforce_admins=true, force_pushes=false, deletions=false; CI runs green on every push.