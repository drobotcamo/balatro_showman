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
files were present. Source and installed hashes now match. Balatro was not
restarted after this copy, so the loaded build is not yet runtime-verified.
Follow the reversible update procedure in `planning/BRIDGE_SPIKE.md`, restart
Balatro, and verify the fresh Lovely log reports
`build=issue81-file-queue-1` before starting the consumer or recording.

The capture components exist, but there is not yet one command that runs the
whole capture-to-inspection-and-association path. `ground_truth.file_ipc_bridge`
writes the legacy `session.json`/`steps.ndjson` directory;
`planning/audit_oracle_runs.py` checks integrity and
`planning/align_oracle_video.py` maps timestamps to frame indices.
`run_bundle.read_oracle_run` is a read-only compatibility API, not a CLI or
converter. `ground_truth.recording_association` accepts a SQLite `RunBundle`,
while the file-IPC producer does not write that bundle. Use the current tools
as separate steps only after the producer is updated; do not describe that as
a verified end-to-end tool yet.

The OBS script previously loaded successfully and emitted a handshake, but its
current loaded state is unverified. Its defaults use prefix `issue35`; set the
OBS script's recording prefix to an Issue 81 label for the new capture. The
existing OBS profile settings were inspected and left unchanged. Only the active
bridge mod was updated; the previous mod tree and stale IPC files were preserved
in the backup locations above. The new producer must still be loaded by a fresh
Balatro startup before capture readiness is confirmed.

Evidence inspected read-only: latest Lovely log
`lovely-2026.10.02-18.08.28.log`, mod manifests/version files, generated
`lovely/game-dump/globals.lua`, OBS profile `Untitled`, and installed/check-in
producer hashes. The latest Balatro runtime configuration is not asserted from
older captures where the current log does not establish it.

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
