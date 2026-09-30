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

Scope is deliberately small (Issue #6 smoke test):

- Snapshots carry real `state`, `page_name`, hand/pending/joker/consumable
  `objects`, `request_id`, and runtime metadata.
- `persistent_state` and `legal_actions` are sparse; action labels are coarse
  (`PlayHand`, `SelectBlind`, ...), not the canonical zoned action space. This
  is a transport/liveness proof, not a model-input snapshot.

## Repository check

```text
py -3 -m unittest tests.test_file_ipc_bridge tests.test_balatro_mod
```

## Installation (reversible)

1. Copy the mod folder into the Steamodded mod root:

   ```powershell
   Copy-Item -Recurse -Force `
     "ground_truth\balatro_mod" `
     "$env:APPDATA\Balatro\Mods\balatro_showman_bridge"
   ```

   To remove it, delete `$env:APPDATA\Balatro\Mods\balatro_showman_bridge`.
   Nothing is written outside that folder, `agent_io`, and the Python output
   directory.

2. Launch Balatro and confirm the Lovely log reports the mod loaded:
   search `$env:APPDATA\Balatro\Mods\lovely\log\` for
   `[balatro_showman_bridge] loaded; io_dir=...`.

## Smoke test

1. Start the repository client, writing outside the repository:

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

## Status

The producer is verified against the installed runtime (Balatro `1.0.1o-FULL`,
Steamodded `26.926.0~dev-a`, Lovely `0.10.0`) with two real runs, and the
current revision is exercised by an external, not-checked-in lupa/luaparser
harness (blind/select, Arcana and Buffoon packs, an unknown kind, voucher 998,
win/loss finalize). Provenance of the persisted runs:

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

A capture pinned to this exact revision is still pending, as are the
`persistent_state`/action-space and field/storage conformance questions tracked
in Issue #10. Issue #10's integrity and conformance findings are in
`planning/ORACLE_DATA_REVIEW.md`; both persisted runs above are pre- or
intermediate-revision, so no persisted run yet reflects this exact file.
Steamodded's debug socket is not used as a transport.
