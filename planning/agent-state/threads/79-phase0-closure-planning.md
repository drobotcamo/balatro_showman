# Work Thread
Updated: 2026-10-02
Issue: GAIT (#79), YOYO (#80), LAMP (#81), MINT (#82), NOVA (#83), WAVE (#84)
PR: pending T0 registry/baton PR
Owner: project lead
Branch: master
Worktree: C:\Users\camgr\Documents\code_projects\balatro_showman
Objective: Prepare the dependency-ordered issue set and workflow skills needed to complete Phase 0.
Status: active
Scope: GitHub issue planning, planning/issue-tags.json, this baton
Dependencies: Phase 0 roadmap and contracts; completed #76 provenance boundary; D022, D026, D027.
Completed:
- Independent research reviewed the roadmap, Phase 0 inventory, oracle findings, historical producer/run-bundle/workflow issues, and current orchestrator policy.
- Created GAIT (#79) for Q03/Q04 evaluation protocol and thresholds.
- Created YOYO (#80) for Q02 asset eligibility and active-store policy.
- Created LAMP (#81) for current producer/video capture and alignment evidence.
- Created MINT (#82) for active annotation/QA tooling and deterministic real-frame export.
- Created NOVA (#83) for a portfolio-state skill layered onto the existing orchestrator.
- Created WAVE (#84) for a read-only, human-confirmed Phase 0 gate-facilitator skill.
- Added dependency/tag comments; issue tags are registered in `planning/issue-tags.json`.
Next:
- Commit the tag registry and this baton through a T0 PR.
- Work GAIT and YOYO in parallel where user decisions permit; then LAMP and MINT; finally run WAVE after the protocol and evidence exist.
- Keep NOVA independent and do not create a second portfolio authority.
Decisions: No architecture, contract, threshold, licensing disposition, or gate status was changed. The six issues preserve those as explicit decision boundaries.
Risks: External video, runtime confirmation, licensing, Q03 thresholds, and Q04 recoverability require user evidence or approval. Current worktree has an unrelated untracked `does-not-exist.db`, excluded from this work.
Validation: `python tools/issue_tags.py check` -> valid: 8 issue tag(s); six issue URLs created; dependency comments posted; temporary issue-body files removed. Final T0 validation remains pending after registry/baton PR.
