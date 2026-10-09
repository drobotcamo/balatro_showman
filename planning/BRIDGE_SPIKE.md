# File-IPC Bridge Spike

This spike exercises the existing file-IPC oracle contract:

```
Lua producer (game)                 Python client (repo)
request_<run>_<id>.json ──────────▶  record aligned step
                       ◀──────────  remove request after durable persistence (ack)
run_end_<run>.json ──────────────▶  drain through last_request_id, finalize outcome
mechanics_reference_<run>_<id>_resolved.json ─▶ isolated Dagger answer-key record
```

## Contract

- Input: one immutable `request_<run_id>_<request_id>.json` file per captured
  request in the shared `agent_io` directory. IDs restart within each run and
  are only meaningful with the run ID.
- Acknowledgement: after the step and session count are durable, the client
  removes the request file. If it crashes before removal, restart replays the
  request using `(run_id, request_id)` deduplication. `action.txt` remains a
  legacy/advisory response and is not the queue acknowledgement.
- Record: `<out-dir>/<run_id>/steps.ndjson`, with `_recorded_action` added.
- Outcome: a Lua-side `run_end_<run_id>.json` containing `run_id`, `outcome`
  (`win` or `loss`), and `last_request_id`. The client retains it until every
  request ID through the watermark is persisted, then finalizes `session.json`.
  Missing requests leave the run incomplete and diagnosed; an empty queue alone
  is not evidence that the producer is drained. Legacy `snapshot.json` and
  `run_end.json` remain readable but have no terminal watermark and are not
  proof of complete delivery.
- Mechanics reference: the producer includes a pre-action Dagger snapshot in the
  queued request and may later emit a separate
  `mechanics_reference_<run_id>_<request_id>_resolved.json` after the game update
  observes queued Dagger Mult growth. Producer revision
  `issue129-hermit-rebate-reference-1` also emits
  `mechanics_reference_<run_id>_<request_id>_mechanics.json` after observing
  direct Hermit use resolution and Mail-In Rebate Joker/card invocations. The
  versioned `dagger-reference/2.0` envelope keeps those records in the isolated
  sidecar. The client stores all phases in `mechanics_reference.ndjson`, outside
  `steps.ndjson`; generic observation adapters never receive these records.
  Records are keyed by the original step and phase, so delayed aftermath needs
  no intervening player action. The run-end signal declares resolved and pending
  counts for Dagger and mechanics references. The consumer waits for declared
  counts before automatic bundle import; unresolved watches do not imply complete
  intake. Each sidecar file is published atomically.

## Lua producer

`ground_truth/balatro_mod/` is a minimal Steamodded mod (`manifest.json` +
`main.lua`) that emits the contract's Lua side. It hooks the game's own action
callbacks and writes a per-request file *before* the action runs, so the captured
state is the decision state and `action_taken` is the player's real action. On
game over it writes a run-scoped end signal and highest successfully published
request ID. The producer does not wait for the consumer; queued files remain
available if the consumer is delayed or stopped.

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
- `producer/1.0.0` with `issue123-dagger-reference-1`: appends a separate
  `mechanics_reference` object to each action request. Dagger `SelectBlind`
  requests also begin a pre-state watch; after the original `Game.update` runs,
  observed Mult growth and the queued victim's `getting_sliced` flag emit a
  resolved-phase queue file. Fields include Joker position/center, available
  engine identity, Mult, sell cost, runtime revision, and source step/timing.
  The consumer removes this object from step payloads and stores it in the
  isolated reference sidecar. Missing identity or values remain null.
- `producer/1.0.0` with `issue129-hermit-rebate-reference-1`: preserves Dagger
  records and emits sidecar schema `dagger-reference/2.0`. Hermit is observed
  inside its delayed event at the direct `ease_dollars` call. Mail-In Rebate is
  observed per `Card.calculate_joker` discard invocation; repeated direct calls
  for one Joker/card/interval are aggregated with explicit multiplicity.
  Actual base rank and effective `Card:get_id()` are distinct; negative no-rank
  sentinels remain known nonmatches. Nonqualifying, zero, and unknown-input rows
  are retained. The checked-in LÖVE fixture exercises these hooks with stubs.
  Live run `923049899800-1565` verified
  89 mechanics-reference sidecars and imported with 1,117 valid records; its
  no-rank sentinel rows motivated the reader compatibility fix. Reducer
  comparison to video observations and user inspection remain open.

## Repository check

```text
py -3 -m unittest tests.test_file_ipc_bridge tests.test_balatro_mod
```

The checked-in producer filesystem fixture runs against the installed LÖVE
runtime and writes only below the selected temporary `%APPDATA%` directory:

```powershell
$env:APPDATA = Join-Path $env:TEMP ("balatro-showman-queue-" + [guid]::NewGuid().ToString("N"))
New-Item -ItemType Directory -Path "$env:APPDATA\Balatro\agent_io" -Force | Out-Null
lovec tests/lua_file_ipc_fixture
```

It validates queued requests, terminal watermarks and wrapped New Run/Continue
callbacks with stub game state. The Python producer test also ingests the resumed
queue and checks one contiguous session and recording association. These checks
do not execute Balatro's actual save restoration or menu callbacks.

## Installation (reversible)

1. Inspect existing bridge processes before preparing a capture. A single
   consumer must own the shared `agent_io` directory:

   ```powershell
   Get-CimInstance Win32_Process |
     Where-Object { $_.CommandLine -like '*ground_truth.file_ipc_bridge*' } |
     Select-Object ProcessId, CommandLine
   ```

   If no bridge process is listed, start the documented client in Smoke test.
   If exactly one expected, healthy client already owns this IPC directory,
   reuse it and verify its output directory and process state; do not start a
   duplicate. If a listed process is stale, conflicting, or its ownership/path
   is unclear, do not terminate it or start another client without explicit
   authorization. Report the PID/command line and request only the permission
   needed to stop or reconfigure that process. After an authorized stop, verify
   the old process exited before starting its replacement. Preserve queue and
   run files; inspection never authorizes deleting them.

2. Copy the mod folder into the Steamodded mod root. Keep timestamped backups
   outside `Mods` so Steamodded cannot discover a second manifest with the same
   mod ID:

   ```powershell
   $target = "$env:APPDATA\Balatro\Mods\balatro_showman_bridge"
   $backupRoot = "$env:APPDATA\Balatro\bridge-backups"
   $stamp = Get-Date -Format 'yyyyMMdd-HHmmss'
   $backup = Join-Path $backupRoot "balatro_showman_bridge-$stamp"
   if (-not (Test-Path "$env:APPDATA\Balatro")) { throw "Balatro data directory not found" }
   if (Test-Path $backup) { throw "Backup path already exists: $backup" }
   New-Item -ItemType Directory -Path $backupRoot -Force | Out-Null
   if (Test-Path $target) {
     Move-Item -LiteralPath $target -Destination $backup
   }
   Copy-Item -Recurse -Force `
     "ground_truth\balatro_mod" `
     $target
   $sourceHash = (Get-FileHash "ground_truth\balatro_mod\main.lua" -Algorithm SHA256).Hash
   $installedHash = (Get-FileHash "$target\main.lua" -Algorithm SHA256).Hash
   if ($sourceHash -ne $installedHash) { throw "Installed producer hash does not match source" }
   Get-FileHash "ground_truth\balatro_mod\main.lua", "$target\main.lua" -Algorithm SHA256
   ```

   Restart Balatro completely and verify the latest Lovely log reports build
   `issue123-dagger-reference-1`. The producer hash and loaded build are separate
   checks. To roll back, close Balatro, move the new active directory out of
   `Mods`, and move the timestamped backup back to the active target. Keep the
   backup; do not delete it as part of an update.

3. Launch Balatro and confirm the Lovely log reports the mod loaded:
   search `$env:APPDATA\Balatro\Mods\lovely\log\` for
   `[balatro_showman_bridge] loaded; build=issue123-dagger-reference-1; io_dir=...`.
   On a separate diagnostic run, trigger one action and inspect its persisted
   record in that run's `steps.ndjson` after the bridge acknowledges it (or
   inspect the queued `request_<run>_<id>.json` if still present). It must contain
   `"schema_version":"producer/1.0.0"`,
   `"ipc_schema_version":"file-queue/1.0.0"`, `step_id`, and
   `capture_timestamp_ns`; abort if the producer still writes only
   `snapshot.json` or if no persisted/queued action appears. Do not use this
   diagnostic run as the intended video run: if its consumer session already
   exists, a later OBS marker will not attach to it. Preserve its evidence.

## Smoke test

1. Ensure one expected bridge client owns the shared IPC directory, using the
   process inspection in Installation. Start the repository client only if no
   client is already running and starting it is authorized. Write output outside
   the repository:

   ```powershell
   py -3 -m ground_truth.file_ipc_bridge `
     --io-dir "$env:APPDATA\Balatro\agent_io" `
     --out-dir "$env:TEMP\balatro_showman_runs"
   ```

2. Start a run. `SelectBlind`, play/discard, and shop actions each publish a
   distinct `request_<run>_<id>.json`. The client persists it to `steps.ndjson`
   before removing the request file as its acknowledgement.
3. End the run for real (failing the first blind is a quick `loss`). The
   producer writes `run_end_<run>.json` with `last_request_id`; the client waits
   for all requests through that watermark before finalizing `session.json`.
4. Report the field values from `steps.ndjson` and `session.json` in Issue #6.
   Keep saves, logs, dumps, and game assets local.

## Monitor an approved live run

Keep the bridge consumer running while the user plays, and monitor the expected
external output without occupying a foreground command until the run ends. Use a
background watcher or short, nonblocking polls against the known output root.
Establish the baseline before play so a new session is not confused with an older
run. Report sparse progress only when useful; continue responding to the user
while the watcher waits.

Treat the run as ready for inspection only after `session.json` has a terminal
outcome and the declared request watermark is persisted. For mechanics-reference
runs, also wait until the declared reference watermark is resolved. An empty IPC
queue, a quiet game, or an unchanged step count is not completion. Once the
terminal session is finalized, inspect the discovered run, run strict RunBundle
validation, and report the result without asking the user to identify the run by
its opaque ID. A watcher timeout means “still waiting”; it must not finalize the
run or infer an outcome.

## Video alignment procedure

For current live recording, use the OBS started-event hook below and the
preflight/identity procedure in `planning/RUN_BUNDLE_OPERATIONS.md`. The manual
request shown here is a historical diagnostic only: do not issue it before OBS
Record or use its timestamp as evidence that recording began. The bridge
persists the producer's response marker in `session.json`:

The client-side `usage` object in `session.json` and `_recorded_at` on new
`steps.ndjson` records are optional additive metadata under the existing
`producer/1.0.0` session/step contract. They record consumer persistence time
in UTC, not a producer game-event timestamp. Readers must preserve compatibility
with older records: legacy steps still contribute action counts, while runs
containing only legacy steps retain null usage timestamps. `action_counts` must
sum to `n_steps`, and duplicate request replays (including after finalization)
must only re-acknowledge the original action.

```powershell
@{schema_version='producer/1.0.0'; recording_id='obs-2026-09-30-001'; fps=60} |
  ConvertTo-Json -Compress |
  Set-Content "$env:APPDATA\Balatro\agent_io\recording_start.json" -Encoding utf8
```

For a diagnostic, use a fresh producer run with no existing consumer session;
after its first action is persisted, verify that run's `session.json` contains
the resulting `recording` object. A marker on an already-created session will
not be attached retroactively. This alone does not establish a video file or
frame correspondence. Never use the wall-clock filename timestamp as a
substitute.

For an automatic event hook, load `ground_truth/obs_recording_start.py` from
OBS **Tools > Scripts**. Set the `agent_io` directory to a fully expanded
absolute path and configure recording FPS. OBS script properties do not expand
Windows shell variables, so do not enter `%APPDATA%\Balatro\agent_io` as
literal text. On the current machine, the value is
`C:\Users\camgr\AppData\Roaming\Balatro\agent_io`; obtain the
current value in PowerShell with:

```powershell
Join-Path $env:APPDATA 'Balatro\agent_io'
```

Paste the printed path into the OBS script property. The script writes the
request on `OBS_FRONTEND_EVENT_RECORDING_STARTED`; use this hook, rather than
the manual command above, for recording evidence.

Use the producer's persisted `capture_timestamp_ns` response to the OBS
started-event request; do not estimate it from a later snapshot or wall-clock
video filename. Lua samples that clock when it polls the request, not at the
instant OBS begins recording. For a persisted `steps.ndjson`, compute candidate
zero-based frame indices:

```powershell
py -3 planning\align_oracle_video.py runs\<run>\steps.ndjson
```

The utility reads the persisted marker from the sibling `session.json`; the
optional flags override it for diagnostics only.

The utility emits `step_id` and nearest `frame_idx`. Negative indices indicate
that the producer timestamp predates the recorded start and require capture
review; they are not silently clamped. Poll/IPC latency is not measured by this
mapping; inspect rendered pre-action frames against oracle observations and
report actual timing error before claiming the ±3-frame criterion is met.

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
