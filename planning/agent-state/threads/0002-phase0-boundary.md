# Work Thread
Updated: 2026-09-30
Issue: #6
PR: PR #8 (planning checkpoint; PR #7 closed as incomplete)
Owner: opencode Phase 0 lead session
Branch: 0002-phase0-inventory
Worktree: balatro_showman-0002
Objective: Begin Phase 0 by establishing a verified artifact inventory and the boundary for oracle/evaluation work.
Status: ready-for-restart
Scope: planning/PHASE0_INVENTORY.md, Phase 0 ground-truth and dataset planning
Dependencies: `planning/components/ground-truth.md`, `planning/ARCHITECTURE.md`, Issue #6, external modded-game bridge, timestamped real footage
Completed:
- Inspected roadmap, architecture, ground-truth/dataset contracts, decisions, learnings, repository state, branch, worktree, and GitHub issue/PR lists.
- Read-only exploration verified that legacy CV/policy artifacts and annotation code exist, but no active provenance records, runnable checked-in Lua bridge, real eval clips, eval manifest, or Phase 0 protocol were found.
- Added `planning/PHASE0_INVENTORY.md` mapping each Phase 0 gate output to its owning component, evidence, and current status without promoting legacy artifacts.
- Located and recorded the local Steam installation, `%APPDATA%\\Balatro\\Mods`, Steamodded source, Lovely runtime data, configs, saves, versions, and launch warnings in `planning/BALATRO_RUNTIME.md`.
- Opened Issue #6 for the runtime bridge work and delegated a read-only audit. The audit verified legacy file IPC (`snapshot.json` → `action.txt`), canonical `live/2.0.0` snapshots, and separate `run_end.json` outcome capture; no `agent_bridge.lua` was found.
- Closed PR #7 as incomplete rather than merging its Python consumer/tests; Issue #6 was rewritten so the immediate deliverable is the Lua producer and one real end-to-end oracle sample.
Next:
1. On Issue #6, confirm the intended Steamodded dev build and decide whether warning-producing mods should be disabled for oracle capture.
2. Implement the minimal Lua producer using the existing file-IPC contract; user must run the game smoke test.
3. Define the provenance-manifest fields and candidate artifact inventory without copying unverified assets.
4. Resolve the annotation/export format and collect a disjoint real-frame pilot before setting numeric thresholds.
Decisions: No architecture, component contract, or durable policy was changed. Existing D001/D002/D005/D009 and Q01–Q03 remain controlling.
Risks: Phase 0 cannot pass from repository-only evidence; external game/mod/footage access and licensing remain unknown. The installed Steamodded build is development version `26.926.0~dev-a`; Lovely reports blacklisted mods and invalid metadata warnings. Branch is ahead/behind remote and has no open PR; do not merge or push as part of this bounded research step.
Validation: `py -3 planning\\check_contracts.py` → `planning contracts OK`; `git diff --check` → clean. External CI not run.
