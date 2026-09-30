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
Completed: policy designed with user via tiered-evidence proposal; all four knobs answered (T0 direct commits, user approves substantive T1, agents merge green T2, planning-check required); written into agent-workflow.md → Approval And Merging; D015 recorded; PR template tier line added; branch protection to be configured with required check context `check`.
Next: owner decides branch-protection blocker: public repo (free protection), GitHub Pro, or advisory-only CI; then close Issue #1. First Phase 0 issue exercises T2.
Decisions: D015.
Risks: branch protection PUT returned 403 (private repo needs GitHub Pro or public visibility); required-check backstop is not active — advisory CI + policy text only. Required check context when enabled must match job id `check`.
Validation: py -3 planning/check_contracts.py → OK; CI run 36693707889 green on push 5b6563d; blocker recorded on Issue #1.