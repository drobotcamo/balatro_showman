# File-IPC Bridge Spike

This spike exercises the repository-side half of the existing contract without
loading game files or importing `legacy/`.

## Contract

- Input: the Lua-side `snapshot.json` in the shared `agent_io` directory.
- Acknowledgement: `<request_id>\t<action>\n` in `action.txt`.
- Record: `<out-dir>/<run_id>/steps.ndjson`, with `_recorded_action` added.
- Outcome: a Lua-side `run_end.json` containing `run_id` and `outcome` (`win` or
  `loss`) finalizes `session.json`.

## Repository check

```text
py -3 -m unittest tests.test_file_ipc_bridge
```

## User smoke test

1. Confirm the intended Steamodded build and disable warning-producing mods by
   the user's normal, reversible runtime procedure. Do not copy runtime files
   into this repository.
2. Arrange for the Lua mod to emit one `live/2.0.0` snapshot with `meta.run_id`,
   `request_id`, `legal_actions`, and either `action_taken` or a legal action
   supplied below. The repository does not invent the Lua hook or modify the
   installed runtime.
3. Start the client, using an output directory outside the repository:

   ```text
   py -3 -m ground_truth.file_ipc_bridge --io-dir "%APPDATA%\Balatro\agent_io" --out-dir "%TEMP%\balatro_showman_runs" --action SelectBlind
   ```

4. Exercise one game decision, then have the Lua side write
   `{"run_id":"...","outcome":"win"}` or `{"run_id":"...","outcome":"loss"}`
   to `run_end.json`.
5. Report the generated `steps.ndjson` and `session.json` fields, not the files
   themselves, in Issue #6. Keep saves, logs, dumps, and game assets local.

The Lua bridge source and runtime hook remain a user-side blocker: no
`agent_bridge.lua` is present in the repository or verified local runtime, and
Steamodded's debug socket protocol is undocumented in the available evidence.
