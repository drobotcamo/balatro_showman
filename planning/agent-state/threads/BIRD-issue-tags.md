Updated: 2026-10-01
Issue: BIRD (#58)
PR: none
Owner: agent
Branch: pending
Worktree: current checkout
Objective: Adopt immutable four-letter tags for new issue references.
Status: implementing
Scope: Registry, deterministic allocator, planning conventions, and validation.
Dependencies: GitHub issue #58.
Next: Validate the allocator and planning checker, then open the PR.
Validation: `python tools/issue_tags.py check`; `python planning/check_contracts.py`.
