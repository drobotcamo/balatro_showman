# Local Balatro Runtime Reference

Updated: 2026-09-30

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

## Installed mod directories

- `BalatroMultiplayer-0.5.5`
- `Brainstorm-2.0.0-alpha-1`
- `HandyBalatro`
- `JokerDisplay-2.0.4`
- `WhatsInMyFool-main`
- `smods-main` (Steamodded)

Lovely's 2026-09-28 log reports Lovely `0.10.0`, Steamodded
`26.926.0~dev-a`, and the game directory above. It also reports that
`BalatroMultiplayer-0.5.5` and `Brainstorm-2.0.0-alpha-1` were blacklisted for
that launch, and that Steamodded's debug socket started. The log contains
warnings and errors about invalid metadata for HandyBalatro and JokerDisplay;
these must be investigated before treating the runtime as a clean oracle
environment.

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
