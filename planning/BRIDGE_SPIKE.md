# File-IPC Bridge Spike

This spike exercises the existing file-IPC oracle contract:

```
Lua producer (game)                 Python client (repo)
snapshot.json  ───────────────▶     record aligned step
action.txt     ◀───────────────     acknowledgement (not consumed by observe producer)
run_end.json   ───────────────▶     finalize outcome
```

## Contract

- Input: the Lua-side `snapshot.json` in the shared `agent_io` directory.
- Acknowledgement: `<request_id>\t<action>\n` in `action.txt`, written by the
  client. The observe-mode producer records the player's real action and does
  not read or dispatch `action.txt`; the acknowledgement is advisory.
- Record: `<out-dir>/<run_id>/steps.ndjson`, with `_recorded_action` added.
- Outcome: a Lua-side `run_end.json` containing `run_id` and `outcome`
  (`win` or `loss`) finalizes `session.json`.

## Lua producer

`ground_truth/balatro_mod/` is a minimal Steamodded mod (`manifest.json` +
`main.lua`) that emits the contract's Lua side. It hooks the game's own action
callbacks and writes a snapshot *before* the action runs, so the captured state
is the decision state and `action_taken` is the player's real action. On game
over it writes `run_end.json` with the real outcome.

Transport revisions (the `live/X.Y.Z` label is the producer snapshot
contract only; it is never the granularized step schema `3.0.0`):

- `live/2.0.0` (Issue #6 smoke test): real `state`, `page_name`,
  hand/pending/joker/consumable `objects`, `request_id`, runtime metadata;
  `persistent_state` empty and no legality, action labels coarse. Two runs
  persisted at this revision (see Status).
- `live/3.0.0` (Issue #21, D021): adds `raw_persistent` (engine-truth raw
  persistent fields: deck center/class id (via
  `G.GAME.selected_back.effect.center.key` on this Steamodded runtime),
  stake level/center key (via `G.P_CENTER_POOLS.Stake[level].key`),
  `starting_params.no_faces`, raw `G.GAME.modifiers`, the run's full
  playing-card deck with modifier/edition/seal/stickers, per-hand
  level/played/played_this_round, redeemed voucher keys, `bosses_used`
  counts (nested `{boss/small/big: {blind_key: count}}` on this runtime),
  `round_resets.blind_states/blind_choices/blind_tags`,
  `boss_rerolled`, and the `skips`/`hands_played`/`unused_discards`/
  `ecto_minus`/`last_tarot_planet` counters), `legal_actions` (coarse base
  labels legal per `mask_schema.md` §2-3 gating, always including the action
  about to run), and `mask_basis` (`reroll_cost`, `free_rerolls`, selection
  counts). `persistent_state` stays `{}` — the canonical shape is owned by
  the pipeline reducer (D021). Unavailable engine reads are emitted as
  explicit nulls, never guessed.

## Repository check

```text
py -3 -m unittest tests.test_file_ipc_bridge tests.test_balatro_mod
```

## Installation (reversible)

1. Stop every existing bridge process before starting a capture. A single
   consumer must own the shared `agent_io` directory:

   ```powershell
   Get-CimInstance Win32_Process |
     Where-Object { $_.CommandLine -like '*ground_truth.file_ipc_bridge*' } |
     Select-Object ProcessId, CommandLine
   ```

   Stop any listed process, and verify that the command returns no bridge
   process before continuing.

2. Copy the mod folder into the Steamodded mod root, preserving a backup of
   the previous installation:

   ```powershell
   $target = "$env:APPDATA\Balatro\Mods\balatro_showman_bridge"
   if (Test-Path $target) {
     Rename-Item $target "$target.pre-capture-backup"
   }
   Copy-Item -Recurse -Force `
     "ground_truth\balatro_mod" `
     $target
   Get-FileHash "ground_truth\balatro_mod\main.lua", "$target\main.lua"
   ```

   The two hashes must match. To remove it, delete
   `$env:APPDATA\Balatro\Mods\balatro_showman_bridge` and restore the backup.
   Nothing is written outside that folder, `agent_io`, and the Python output
   directory.

3. Launch Balatro and confirm the Lovely log reports the mod loaded:
   search `$env:APPDATA\Balatro\Mods\lovely\log\` for
   `[balatro_showman_bridge] loaded; io_dir=...`.
   Before recording, trigger one snapshot and inspect it. It must contain
   `"schema_version":"producer/1.0.0"`, `step_id`, and
   `capture_timestamp_ns`; abort if it contains `live/2.0.0` or `live/3.0.0`.

## Smoke test

1. With no other bridge process running, start the repository client, writing
   outside the repository:

   ```powershell
   py -3 -m ground_truth.file_ipc_bridge `
     --io-dir "$env:APPDATA\Balatro\agent_io" `
     --out-dir "$env:TEMP\balatro_showman_runs"
   ```

2. Start a run. `SelectBlind`, play/discard, and shop actions each write one
   `snapshot.json`; the client records it to `steps.ndjson`.
3. End the run for real (failing the first blind is a quick `loss`). The
   producer writes `run_end.json`; the client finalizes `session.json`.
4. Report the field values from `steps.ndjson` and `session.json` in Issue #6.
   Keep saves, logs, dumps, and game assets local.

## Video alignment procedure

Before pressing OBS Record, write a start request so the Lua producer samples
its own monotonic clock. The bridge persists the resulting marker in
`session.json`:

```powershell
@{schema_version='producer/1.0.0'; recording_id='obs-2026-09-30-001'; fps=60} |
  ConvertTo-Json -Compress |
  Set-Content "$env:APPDATA\Balatro\agent_io\recording_start.json" -Encoding utf8
```

Verify `session.json` contains the resulting `recording` object after the
first snapshot is persisted. Never use the wall-clock filename timestamp as a
substitute.

For an automatic event hook, load `ground_truth/obs_recording_start.py` from
OBS **Tools > Scripts**. Configure the `agent_io` directory and recording FPS.
The script writes the request on `OBS_FRONTEND_EVENT_RECORDING_STARTED`; use
this hook, rather than the manual command above, for Issue #35 evidence.

At the instant OBS recording starts, capture the producer monotonic clock value
(`capture_timestamp_ns`) from a fresh snapshot or the bridge diagnostic. Pass
that value as `--recording-start-ns`; do not substitute the wall-clock filename
timestamp. For a persisted `steps.ndjson`, map each step to a zero-based frame:

```powershell
py -3 planning\align_oracle_video.py runs\<run>\steps.ndjson
```

The utility reads the persisted marker from the sibling `session.json`; the
optional flags override it for diagnostics only.

The utility emits `step_id` and nearest `frame_idx`. Negative indices indicate
that the producer timestamp predates the recorded start and require capture
review; they are not silently clamped.

## Status

The producer is verified against the installed runtime (Balatro `1.0.1o-FULL`,
Steamodded `26.926.0~dev-a`, Lovely `0.10.0`) by a real capture (50 steps
across two sessions; legality, mask basis, counters, hand levels, and blind
statuses present on every step) and by an external, not-checked-in lupa
(Lua 5.1) harness that executes `main.lua` against a stub `G` and validates
the emitted snapshot JSON (raw fields, legality across blind/shop/pack/unknown
pages, client acceptance). The client stops cleanly on Ctrl+C and reports
unfinalized sessions. Known runtime divergences from the vanilla game dump
(deck/stake/bosses_used reads) are recorded in `planning/LEARNINGS.md`. The
persisted runs below are `live/2.0.0` revisions; `planning/audit_oracle_runs.py`
reports their raw-field/legality coverage as findings. Provenance of the
persisted runs:

- `win`, 433 steps: `F:\OBS_RECORDINGS\oracle_runs\2026-09-30_14-50-37_1790805058-5327\`
  with video `F:\OBS_RECORDINGS\2026-09-30 14-50-37.mkv`. Captured before the
  Steamodded page-map fix, so it contains 38 `Unknown_999` pack steps.
- `loss`, 43 steps: `F:\OBS_RECORDINGS\oracle_runs\2026-09-30_15-31_verify_1790807319-8546\`.
  Captured with the mapping fix; zero `Unknown_*` pages, packs resolved
  `Buffoon`/`Celestial`/`Standard`, but an intermediate revision (the diagnostic
  `pack_kind` was not yet gated to state 999).

Both runs have one `run_id`, unique `request_id`s, `action_taken` on every step,
and real per-step runtime metadata. Steamodded patches `G.STATES` with
`SMODS_BOOSTER_OPENED = 999` and `SMODS_REDEEM_VOUCHER = 998`; the producer maps
999 to a pack page via `SMODS.OPENED_BOOSTER.config.center.kind` (unknown kinds
are emitted as an explicit `Unknown_PackKind_*`, never guessed) and 998 to
`In_Shop`.

A capture from the installed `live/3.0.0` producer exists
(`F:\OBS_RECORDINGS\oracle_runs_live3\`, 50 steps, one session unfinalized
after a mid-run exit to the main menu — the producer only finalizes on game
over); it validated legality/mask-basis/counter emission but pre-dates the
deck/stake/bosses_used runtime fixes, so a fresh capture with the re-copied
mod is the remaining validation. Steamodded's debug socket is not used as a
transport.
