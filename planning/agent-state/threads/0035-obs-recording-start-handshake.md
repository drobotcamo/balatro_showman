# Work Thread
Updated: 2026-10-01
Issue: #35
PR: none
Owner: project lead
Branch: docs-one-shot-work-completion
Worktree: C:\Users\camgr\Documents\code_projects\balatro_showman
Objective: Persist an exact producer-clock marker for each OBS recording and use it for oracle-to-frame alignment.
Status: ready-for-review
Scope: ground_truth/balatro_mod/main.lua, ground_truth/file_ipc_bridge.py, planning/BRIDGE_SPIKE.md, planning/align_oracle_video.py
Dependencies: Issue #11 live capture; Issue #15 producer identity/alignment
Completed:
- Added a `recording_start.json` request consumed by Lua using the same `love.timer` monotonic clock as step timestamps.
- Added persisted marker metadata (`recording_id`, FPS, schema, producer timestamp) to `session.json`.
- Documented the OBS start procedure and existing offline frame mapper.
- Added `ground_truth/obs_recording_start.py`, an OBS frontend-event hook that emits the request automatically.
- Fixed the Lua coalescing clock to keep seconds-based throttling separate from nanosecond capture timestamps.
- Updated alignment to consume the persisted marker from the run's sibling `session.json` by default.
- Installed Python 3.11.16 through `uv` at `C:\Users\camgr\AppData\Roaming\uv\python\cpython-3.11-windows-x86_64-none`; OBS 32.1.1 accepted it and logged `Balatro handshake requested: issue35-...`, proving the OBS hook executes.
- Installed the repository mod at `C:\Users\camgr\AppData\Roaming\Balatro\Mods\balatro_showman_bridge`; source and installed `main.lua` hashes matched after the final polling changes.
- Started the bridge with `--io-dir C:\Users\camgr\AppData\Roaming\Balatro\agent_io --out-dir artifacts\issue35-live` and captured one real run (`1790835302-4718`) with one step.
- Repeated live attempts left `C:\Users\camgr\AppData\Roaming\Balatro\agent_io\recording_start.json` present while no `recording_start_marker.json` was produced. The OBS request file is valid and has timestamps newer than the last snapshot; `session.json` has no `recording` object.
- Fresh-context review refuted completion: the live handshake, persisted session marker, and alignment demonstration remain unverified. The reviewer also confirmed that Lua removes the request before validating or confirming marker creation (`main.lua:922-934`), so the current failure can be silent.
- Required repository checks still pass: `py -3 -m unittest tests.test_file_ipc_bridge tests.test_balatro_mod` (9 tests, OK), `py -3 planning\\check_contracts.py` (planning contracts OK), and `git diff --check` (clean).
- Updated Lua polling to validate the schema, log request discovery and marker-write outcome, and remove the request only after a successful marker write. This preserves diagnostic evidence across failed polls.
- Staged the revised `main.lua` into `C:\Users\camgr\AppData\Roaming\Balatro\Mods\balatro_showman_bridge`; source and installed SHA-256 hashes match (`DD57194089E422AC0432F7CC7A5C90885ADB3D37C2B1193CDDE381AE34F81275`).
- Restarted Balatro (PID 33372, started 23:53:06) and confirmed the new process logged the mod load. A fresh atomic request (`issue35-retry-20261001T235400Z`) remains in `agent_io` after three seconds; no marker or new handshake diagnostic was logged. This shows the poll is not executing in the current menu state, or the running process is not reaching the hooked update path.
- After an actual short play session, the producer emitted a fresh snapshot for run `1790837704-1952` (`capture_timestamp_ns=460646912`), proving the action hook is live, but the pending recording request still remained untouched and no marker was produced. The corresponding Lovely log contains only load/hook messages, not the new diagnostics.
- Hardened the request read and replaced blind `pcall(Bridge.emit, ...)` calls with error logging for the two action-hook paths. Staged the file and verified matching SHA-256 (`DC1B60575ADE530955F9D584BF8F1007243A411E98066F2E05060915B470B224`), then restarted Balatro.
- After the restart and another played action, a fresh snapshot exists for run `1790837912-6914` (`capture_timestamp_ns=1210607036`), but the pending request still remains and the new log still has neither handshake diagnostics nor emit errors. The action path is definitely live, so the request-poll path is not being reached despite its call sites.
- Added a one-time diagnostic that logs the exact `RECORDING_START_PATH` whenever the Lua poll cannot open it. Staged and hash-verified the mod (`2A59230BF93F2A3F7405082E7DB8533CDFFB3DA4AE5A53DD0F6A697936963AAE`), passed the targeted checks, and restarted Balatro.
- The restarted process produced another fresh snapshot for run `1790838130-4512` (`capture_timestamp_ns=847362136`), but still emitted no poll-path diagnostic, marker, or error while the request remained present. The source and installed file both contain the diagnostic, so the runtime is apparently executing a different callback/version path than the checked-in `build_snapshot` flow; this remains unresolved.
- Root cause found: the preserved `balatro_showman_bridge.pre-issue35-backup` directory had an active manifest with the same mod ID. Lovely blacklisted the intended directory but loaded the stale backup. Blacklisting the backup and unblocking the active directory made the log identify `build=issue35-poll-diagnostic-3` and produce the marker.
- The bridge persisted the marker into `artifacts/issue35-live-fixed/1790838130-4512/session.json`, but the only available step predates the marker (`frame_idx` would be negative). This is diagnostic success, not yet valid live alignment evidence.
- After a fresh action, the bridge persisted run `161086442600-9098` with the same marker; alignment produced frame 69. Fresh review verdict: `holds with gaps`; unique marker, completed session, video, and visual frame evidence remain missing.
- Current checks pass: 11 targeted tests, `planning\\check_contracts.py`, and `git diff --check`.
- Final live capture completed: recording `issue35-20261001T071843Z`, video `F:\\OBS_RECORDINGS\\2026-10-01 00-18-39.mkv`, run `161086442600-9098`, 17 steps, outcome `loss`, and finalized `session.json` with the unique marker. Alignment produced post-marker frames 29, 44, and 28; extracted `artifacts/issue35-live-final/frame-29.png` visually shows the Balatro blind screen.
Next:
- Open the PR, attach the live artifact paths and command output, obtain required review/CI, and merge under the work-item policy.
Decisions: The OBS hook writes a request; Lua samples the producer clock, avoiding cross-process clock conversion. Storage remains the existing JSON run bundle.
Risks: Alignment correctly reports negative indices for pre-recording steps; post-marker steps are non-negative. The final video is external at `F:\\OBS_RECORDINGS`; the extracted frame is local evidence. Final review should confirm artifact provenance before merge.
Validation: `py -3 -m unittest tests.test_file_ipc_bridge tests.test_obs_recording_start tests.test_align_oracle_video` passed (11 tests); `py -3 planning\\check_contracts.py` passed; `git diff --check` passed. Independent reviewer returned `holds with gaps` before the final live capture.
