# Work Thread
Updated: 2026-09-30
Issue: #6
PR: https://github.com/drobotcamo/balatro_showman/pull/8 (merged)
Owner: opencode Phase 0 lead session
Branch: 0002-phase0-inventory
Worktree: balatro_showman-0002
Objective: Begin Phase 0 by establishing a verified artifact inventory and the boundary for oracle/evaluation work.
Status: complete
Scope: planning/PHASE0_INVENTORY.md, planning/BALATRO_RUNTIME.md, Phase 0 ground-truth and dataset planning
Dependencies: `planning/components/ground-truth.md`, `planning/ARCHITECTURE.md`, Issue #6
Completed:
- Inspected roadmap, architecture, ground-truth/dataset contracts, decisions, learnings, repository state, branch, worktree, and GitHub issue/PR lists.
- Verified that legacy CV/policy artifacts and annotation code exist, but no active provenance records, runnable checked-in Lua bridge, real eval clips, eval manifest, or Phase 0 protocol were found at that time.
- Added `planning/PHASE0_INVENTORY.md` mapping each Phase 0 gate output to its owning component, evidence, and status without promoting legacy artifacts.
- Located and recorded the local Steam installation, `%APPDATA%\Balatro\Mods`, Steamodded source, Lovely runtime data, configs, saves, versions, and launch warnings in `planning/BALATRO_RUNTIME.md`.
- Merged as PR #8 into `master`. Issue #6 was subsequently re-scoped to the Lua producer and completed via PR #9 (see thread 0006).
Next:
- None; this planning inventory is superseded where it claimed no bridge existed. `planning/PHASE0_INVENTORY.md` now records the merged bridge and pending conformance/alignment, owned by Issue #18.
Decisions: No architecture, component contract, or durable policy changed. D001/D002/D005/D009 and Q01-Q03 remain controlling.
Risks: Phase 0 cannot pass from repository-only evidence; external game/mod/footage access and licensing remain unknown. The worktree `balatro_showman-0002` is retained but merged.
Validation: `py -3 planning\check_contracts.py` -> `planning contracts OK`; `git diff --check` -> clean. CI ran green on PR #8.
