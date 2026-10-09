# Local Balatro Runtime Reference

Updated: 2026-10-02

This file records verified paths on the current development machine. Paths are
machine-specific and are references for agents, not repository dependencies.
Do not copy saves, logs, dumps, mods, or game assets into this repository.

## Verified paths

| Purpose | Path | Evidence |
| --- | --- | --- |
| Steam game install | `C:\\Program Files (x86)\\Steam\\steamapps\\common\\Balatro` | `Balatro.exe`, `love.dll`, `lua51.dll`, `steam_appid.txt` present |
| Active mod root | `C:\\Users\\camgr\\AppData\\Roaming\\Balatro\\Mods` | Lovely log reports this as the mod directory |
| Steamodded source | `C:\\Users\\camgr\\AppData\\Roaming\\Balatro\\Mods\\smods-main` | `manifest.json`, `version.lua`, `src/`, `lovely/` present |
| Lovely runtime data | `C:\\Users\\camgr\\AppData\\Roaming\\Balatro\\Mods\\lovely` | `log/`, `dump/`, `game-dump/` present |
| Steamodded config | `C:\\Users\\camgr\\AppData\\Roaming\\Balatro\\config\\Steamodded.jkr` | Config file present |
| Profiles and saves | `C:\\Users\\camgr\\AppData\\Roaming\\Balatro\\1` | `profile.jkr`, `save.jkr`, `meta.jkr` present |

## Current runtime and recording configuration

- Game version in the latest generated Lovely game dump: `1.0.1o-FULL`
- The installed `Balatro.exe` reports file/product version `11.5 r1`/`11.5`; this
  is the bundled LÖVE runtime version, not the Balatro content version.
- Lovely: `0.10.0`, reported by the 2026-10-02 18:08:28 launch log.
- Steamodded runtime: `26.926.0~dev-a`, reported by the launch log and
  `smods-main/version.lua`. Its `manifest.json` still says `26.829.0`; use the
  runtime log/version file for the loaded runtime and retain the discrepancy.
- OBS profile `Untitled` currently configures `C:\\Users\\camgr\\Videos`,
  MKV recording, and common FPS `60` in
  `%APPDATA%\\obs-studio\\basic\\profiles\\Untitled\\basic.ini`.
- The project OBS hook is `ground_truth/obs_recording_start.py`; the OBS log
  dated 2026-10-01 confirms it loaded and emitted a `Balatro handshake
  requested` event. The OBS profile inventory inspected on 2026-10-02 contains
  no copy of the script, so verify it is still loaded in OBS before capture.
- User-selected #81 alignment tolerance: **within ±3 frames**. At 60 FPS this
  is a nominal ±50 ms. Record actual video FPS/presentation timing and measured
  rendered pre-action correspondence; this setting is a criterion, not evidence
  that the capture meets it.

## Mod inventory and latest launch evidence

Mod root: `%APPDATA%\\Balatro\\Mods`.

| Directory | Local metadata/version | Latest launch evidence |
| --- | --- | --- |
| `smods-main` | `version.lua`: `26.926.0~dev-a`; manifest says `26.829.0` | Steamodded runtime `26.926.0~dev-a` loaded |
| `balatro_showman_bridge` | manifest `0.1.0` | Loaded as `issue35-poll-diagnostic-3`; old singleton snapshot producer |
| `HandyBalatro` | manifest `2.0.6` | Steamodded rejected manifest metadata because required `id` is missing; Lovely patches from Handy still applied |
| `JokerDisplay-2.0.4` | manifest `2.0.4` | Steamodded rejected manifest metadata because required `id` is missing; Lovely patches from JokerDisplay still applied |
| `WhatsInMyFool-main` | `wimf.json`: `1.0.0` | Present in mod root; load status not established from the inspected log |
| `BalatroMultiplayer-0.5.5` | `Multiplayer.json`: `0.5.5` | Blacklisted; skipped by Lovely |
| `Brainstorm-2.0.0-alpha-1` | version in directory name | Blacklisted; skipped by Lovely |
| `balatro_showman_bridge.pre-issue15-20261001-verified` | backup directory | Blacklisted; skipped by Lovely |
| `balatro_showman_bridge.pre-issue35-backup` | backup directory | Blacklisted; skipped by Lovely |

The 2026-10-02 18:08:28 launch log also reports a Handy atlas key collision and
several Lovely pattern warnings. Do not silently change the mod set for capture;
record the selected configuration and any observed warnings as provenance.

## Capture readiness

The checked-in queue producer is build `issue81-file-queue-1`, manifest
`0.2.0`, SHA-256
`C3165AAEC74B6E9FEB71ADAFB5175D6BFCB7CF976E22FDA197AC2C228F2DE5EB`. On
2026-10-02, the installed `balatro_showman_bridge/main.lua` was replaced with
this checked-in copy after the old `issue35-poll-diagnostic-3` build
(manifest `0.1.0`, SHA-256
`B0C607999E7A41D50C3BB51A0E9F1C3DBDB4B2CAAB5650D6FF4B525993D5A787`) was
preserved at
`%APPDATA%\\Balatro\\bridge-backups\\balatro_showman_bridge-20261002-185452`.
The pre-existing `snapshot.json`, `run_end.json`,
`recording_start_marker.json`, and `action.txt` were preserved at
`%APPDATA%\\Balatro\\agent_io-pre-issue81-20261002-185452`; no queued request
files were present. Source and installed hashes match. After restarting Balatro,
the fresh Lovely log `lovely-2026.10.02-19.01.15.log` reported
`build=issue81-file-queue-1` and the expected `agent_io` path. This verifies
the loaded producer. The log also retains the previously documented Handy and
JokerDisplay manifest warnings.

`ground_truth.file_ipc_bridge` writes `session.json`/`steps.ndjson` directories.
They can be inspected directly with `run_bundle.read_oracle_run` or imported
into SQLite with `python -m run_bundle import-oracle`; subsequent queries use
the read-only RunBundle inspector. `planning/audit_oracle_runs.py` checks source
integrity and `planning/align_oracle_video.py` maps timestamps to frame indices.
These remain separate steps; the producer does not write SQLite directly.

The OBS log `2026-10-02 19-09-19.txt` shows the script loaded, but its recording-
start event failed because the configured `io_dir` included the unexpanded
`%APPDATA%` variable. OBS script properties do not expand Windows environment
variables. Set the `agent_io` field to the fully expanded path
`C:\Users\camgr\AppData\Roaming\Balatro\agent_io` and its recording prefix
to an Issue 81 label. The existing OBS profile settings were inspected and left
unchanged. Only the active bridge mod was updated; the previous mod tree and
stale IPC files were preserved in the backup locations above. The queue producer
is loaded after restart; the OBS event handshake still needs to succeed before
starting the game run.

Evidence: latest producer startup log `lovely-2026.10.02-19.01.15.log`, failed
OBS event log `2026-10-02 19-09-19.txt`, mod manifests/version files, generated
`lovely/game-dump/globals.lua`, OBS profile `Untitled`, installed/check-in
producer hashes, and the timestamped installation/archive records above.

## Issue #123 Dagger-reference deployment (2026-10-04)

The Issue #123 producer (`manifest` 0.3.0, build
`issue123-dagger-reference-1`) was installed reversibly at
`%APPDATA%\Balatro\Mods\balatro_showman_bridge`. Its `main.lua` SHA-256 is
`C29A3370E8C8222891383FF0834EDA19F43D2FA6200214B1267044F39AAB049A`, matching
the worktree. The prior active source SHA-256
`F2D784516511D2F9F427A275871B3ED555F4965732921167DAC0F6FA888C94E6` is preserved
as `bridge-backups\balatro_showman_bridge-issue123-pre-build-label-20261004-main.lua`;
the previous full mod is preserved at
`bridge-backups\balatro_showman_bridge-issue123-20261004`.

The first launch log used the old startup label. After correcting it and
recopying `main.lua`, `lovely-2026.10.04-16.52.58.log` reported
`build=issue123-dagger-reference-1` and that action hooks were installed. It
shows normal mod startup and existing Handy/JokerDisplay metadata/pattern
warnings, then ends during startup. No gameplay, OBS recording, or reference
request occurred. Windows recorded Kernel-Power event 41 at 16:53:44 and the
previous shutdown as unexpected (event 6008); its event-41 bugcheck code is 0.
No Balatro application-error/Windows Error Reporting record or minidump was
found. Additional unexpected reboots were recorded earlier at 12:43 and 16:44
that day. The logs do not establish the cause or rule out the latest game launch
as a trigger.
The prior IPC directory (three preserved marker/action files, including its
`.invalid` marker) is archived at
`%APPDATA%\Balatro\agent_io-issue123-pre-capture-20261004`; a fresh empty
`agent_io` directory is active. The F: recording volume was absent after the
restart and remains unavailable, so the new Issue #123 bundle/output paths on
that volume are not currently available. No capture was made; do not relaunch
the game or recorder until the system is stable and the intended storage volume
is available.

## Issue #129 mechanics-reference capture (2026-10-09)

After owner authorization, producer build `issue129-hermit-rebate-reference-1`
(manifest 0.4.0) was installed reversibly. Backup:
`%APPDATA%\Balatro\bridge-backups\balatro_showman_bridge-issue129-20261009`.
The installed `main.lua` SHA-256 at launch was
`444041AE20E1096B2611AF34BEBBE7C45D93545BD2478A3894FD7477A817EBF5`; the
producer stayed loaded in Balatro `1.0.1o-FULL`, Lovely `0.10.0`, and Steamodded
`26.926.0~dev-a`.

Live run `923049899800-1565` completed as a win with 514 steps. OBS recording
`F:\OBS_RECORDINGS\2026-10-09 05-12-21.mkv` used the saved `Untitled` profile
(MKV, 60 FPS); its marker is in `session.json`. Strict capture integrity passed,
and the v2 sidecar imported into `F:\OBS_RECORDINGS\issue123_dagger_reference.sqlite`
with 1,117 valid records, including 603 mechanics-reference records (89 resolved
mechanics sidecars). These are engine references, not reconstruction inputs.

This installed build emitted the earlier v2 representation in which
`discarded_rank_id` holds `Card:get_id()` and `discarded_rank` holds the actual
base label. No-rank cards can therefore carry a negative `discarded_rank_id`.
The updated reader preserves that legacy shape; the current PR producer also
emits a separate `discarded_effective_rank_id` alongside the actual base rank ID.
The run has 15 Hermit uses and 315 Rebate/card participations from one Rebate
instance. It lacks a zero-balance Hermit use and a second Rebate source. Visual
reducer comparison and user inspection of the query report remain open. The video
has not been explicitly associated or frame-aligned.

## Issue #82 held-out capture preflight (2026-10-09)

After user authorization, the checked-in producer from `master` `ab90a1d` was
installed reversibly. Its `main.lua` SHA-256 is
`8450805261FD37DD7CF3C7EA381CBAA7C5F2189EE3216FBC2F7DAB03D6E79ADB`, matching
the installed file. The previous active mod is preserved at
`%APPDATA%\Balatro\bridge-backups\balatro_showman_bridge-issue82-preflight-20261009-132159`.
Balatro was restarted and the fresh Lovely log reports
`build=issue129-hermit-rebate-reference-1` with the fully expanded
`%APPDATA%\Balatro\agent_io` path. Runtime versions remain Balatro `1.0.1o-FULL`,
Lovely `0.10.0`, and Steamodded `26.926.0~dev-a`.

OBS profile `Untitled` is MKV, 1920×1080, 60 FPS, AMD H.264 hardware encoding,
and `F:\OBS_RECORDINGS` (about 854 GB free on the inspected fixed volume). Its
loaded `obs_recording_start.py` has SHA-256
`61813AD32CAEE4A1CB85709C892F2D63A4C50DB76D4D39E8D174B0FE1E82DA63`, matching
the configured script path. The script settings use the fully expanded IPC path,
60 FPS and prefix `issue82`. The manually started OBS instance loaded the hook;
no new start event has been emitted, so the current-prefix handshake remains
unverified. Keep the game at the menu until OBS recording has started and the
new marker is observed; the preserved `recording_start_marker.json` still holds
the prior Issue #81 marker until then.

One `python -m showman record --io-dir "%APPDATA%\Balatro\agent_io" --out-dir
"F:\OBS_RECORDINGS\oracle_runs_issue82"` consumer is running, with no bundle DB
configured. Its output root was absent before startup and is now created. No
queued request files were present when inspected. A future new run must first
receive the current OBS marker; do not use Continue for a new independent source.
It belongs to predeclared group `first-slice-heldout-20261003-A`. The Issue #129
recorder run was finalized, audited (`oracle run integrity OK`) and valid in its
bundle before that consumer was stopped.

Validation at `ab90a1d`: `python -m unittest tests.test_balatro_mod
tests.test_file_ipc_bridge` → 50 tests passed; `python planning/check_contracts.py`
→ `planning contracts OK`; `git diff --check` → clean. These checks do not
verify the next OBS event or any held-out recording.

## External references

- Steamodded repository/source metadata is available in `smods-main/README.md`,
  `manifest.json`, and `version.lua`.
- Lovely patch and game-dump output is under `lovely/game-dump/`; it is generated
  runtime material and must not be treated as stable source without recording
  the originating versions.
- The repository's checked-in legacy policy bridge references are under
  `legacy/vendor/balatro-policy-transformer/live/`; they are reference-only
  until the bridge audit establishes compatibility with this runtime.

## Access notes for future agents

1. Read this file before asking for installation paths.
2. Inspect logs and metadata read-only first.
3. Do not alter the installed game, mod blacklist, saves, or configs without
   explicit user direction and a reversible backup plan.
4. Do not commit private saves, generated dumps, logs, or proprietary game
   assets.
