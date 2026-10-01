# Work Thread
Updated: 2026-10-01
Issue: #37
PR: none
Owner: primary session
Branch: docs-one-shot-work-completion
Worktree: C:\Users\camgr\Documents\code_projects\balatro_showman
Objective: Add the deslop skill and require it for substantial technical prose.
Status: complete
Scope: .opencode/skill/deslop, AGENTS.md, workflow guidance
Dependencies: none
Completed:
- Created Issue #37.
- Added the project deslop skill with PR-body newline checks.
- Added repository guidance requiring the skill for lengthy technical summaries.
Next:
- Run planning and whitespace checks.
- Review the diff and record the verified literal-newline finding.
Decisions: Use the upstream skill's purpose and checks, with repository-specific PR-body handling.
Risks: The existing working tree contains unrelated user changes; they must remain untouched.
Validation:
- `py -3 planning/check_contracts.py` -> `planning contracts OK`.
- `git diff --check` -> clean apart from existing CRLF warnings.
- `gh issue view 37` -> body contains real section line breaks; `\\n` appears only as intentional documented example text.
