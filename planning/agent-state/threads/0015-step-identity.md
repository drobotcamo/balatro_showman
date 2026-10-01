# Work Thread
Updated: 2026-10-01
Issue: #15
PR: #36 (merged)
Owner: project-lead
Branch: docs-one-shot-work-completion
Worktree: C:\Users\camgr\Documents\code_projects\balatro_showman
Objective: Add step identity, timestamps, and offline video-frame alignment to oracle output.
Status: complete
Scope: `ground_truth/balatro_mod/main.lua`, `ground_truth/file_ipc_bridge.py`, `planning/audit_oracle_runs.py`, `planning/align_oracle_video.py`, audit/tests/procedure.
Dependencies: #11 live-capture validation and recording-start handshake completed by PR #36.
Completed: Added producer/1.0.0 step_id and strictly increasing high-resolution timestamps, bridge persistence, fatal audit checks, offline frame-index utility, explicit OBS-start procedure, alignment boundary tests, monotonic-clock run IDs, and the OBS recording-start marker handshake. PR #36 merged. Fresh run `35151992300-2982` has 15 steps, finalized loss outcome, marker `issue35-20261001T072540Z`, and valid post-marker alignment frames 94-2343; frame 94 visually verifies `DiscardHand`.
Next: Close Issue #15 and continue with its dependent Phase 0 work.
Decisions: No new decision.
Risks: The superseded run `161086442600-9098` had a Lua `%d` overflow and must not be used as evidence. PR #36 corrected serialization to `%.0f`; the fresh run is the authoritative evidence.
Validation: PR #36 merged with CI green. Its targeted tests passed (11), `py -3 planning\\check_contracts.py` passed, and `git diff --check` passed. Fresh run audit and visual frame verification were recorded on Issue #35.
