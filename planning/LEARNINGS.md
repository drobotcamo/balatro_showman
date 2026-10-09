# Engineering Learnings

Append concise, verified findings that should survive the current task. Use
this format:

```markdown
## YYYY-MM-DD: Title

- Context:
- Observation:
- Implication:
- Verification/source:
```

Unresolved questions belong in `planning/DECISIONS.md`; durable choices belong
under its Decisions section. This file is a knowledge base, not a task log.

## 2026-10-09: Hermit and Mail-In Rebate need occurrence-level money attribution

- Context: Issue #129 source inspection of the installed embedded Balatro
  `1.0.1o-FULL` executable, SHA-256
  `0d75fe164accf3312734d4b37ac98788dd15f0b8e4f9bb8b7f90c4e59de93f47`.
- Observation: `card.lua:1385-1391` queues Hermit's dollar calculation, which
  clamps the current resolved dollars to the configured amount. `card.lua:2825-2834`
  evaluates Mail-In Rebate for one `context.other_card`, requiring a non-debuffed
  card whose `get_id()` matches the current-round target. The target rank/id is
  reset in `functions/common_events.lua:2288-2300`. On the installed Steamodded
  stack, `card.lua:1174-1179` makes `get_id()` return a random negative sentinel
  when `SMODS.has_no_rank` applies, even if `base.value` retains a rank label.
- Implication: use the delayed Hermit effect balance, retain every Rebate/card
  participation (including zero), preserve the triggering card's identity/rank
  and target rank, distinguish actual rank from effective trigger rank, and
  separate direct effects from interval money deltas. This
  source trace does not establish behavior for arbitrary mods or live reference
  data. At initial source review #123's sidecar was Dagger-only; the separately
  approved #129 extension now adds versioned Hermit/Rebate reference records.
  The verification below records its first live capture and remaining limits.
- Verification/source: embedded Lua source inspected read-only; focused
  `tests/test_hermit_rebate.py` exercises caps, zero, unknowns, identity,
  multiplicity, ties and aggregation; the v2 sidecar validator accepts the
  observed negative no-rank sentinel while retaining zero contribution. Live
  Run `923049899800-1565` captured 15 Hermit effects and 315 Rebate/card rows;
  8 were later legacy no-rank sentinel rows that the initial reader rejected.
  The corrected reader accepted all 89 mechanics sidecar records and strict
  RunBundle validation passed for the 514-step win. Reducer comparison from
  visual observations and user inspection remain open; captured references are
  not reconstruction inputs.

## 2026-10-05: Dagger victim sell value is a current-cost derivation

- Context: Issue #124 source inspection of installed Balatro `1.0.1o-FULL` and
  the locally active post-Lovely runtime.
- Observation: Vanilla `Card:set_cost` computes purchase cost from hard-coded
  Joker base cost, inflation, edition purchase surcharges, and discount with
  floor/minimum operations; rental then forces cost 1. Sell value is
  `max(1, floor(cost/2)) + ability.extra_value`. Vanilla editions add Foil 2,
  Holographic 3, and Polychrome 5 to purchase cost; these differ from edition
  scoring config values. Clearance Sale/Liquidation set discount to 25%/50%.
  Egg adds its configured amount to its own `extra_value`; Gift Card adds its
  configured amount to each Joker/consumable `extra_value`. The captured patched
  runtime reads edition purchase surcharge from each active edition center's
  `extra_cost` and preserves half-cost-plus-extra_value sell calculation.
- Implication: Reconstruct sell value from source-backed base and interval-valid
  modifiers, applying order and rounding exactly. A missing/contradictory input
  makes the sacrifice increment unknown and Dagger's stored Mult unknown
  downstream until independently re-established. Reference values may validate
  the reducer but cannot supply its inputs.
- Verification/source: Read-only inspection of embedded `card.lua` lines
  369-384, 1917-1923, 2561-2577 and 2985-3010; embedded `game.lua` lines 416,
  451, 593, 610 and 659-661; active
  `%APPDATA%\Balatro\Mods\lovely\dump\card.lua` lines 497-528 and 2953-2973.
  Executable SHA-256 `0d75fe164accf3312734d4b37ac98788dd15f0b8e4f9bb8b7f90c4e59de93f47`,
  active card.lua SHA-256
  `2ba1276c5850ea966733d4144602d866dddbb9cbfff1f588f409114d79584f54`, and
  scaling patch SHA-256
  `ade9f4a7f8b87ea64fe094445354a89710762950e8d9916d3354f779d8ba7666`. Findings
  are limited to these source revisions. `tests/test_dagger_mechanics.py`
  exercises the corresponding synthetic constructor and reducer; no independent
  video-input reconstruction validation was run. The #123 ordinary engine-step
  payloads identify Photograph as Holographic at step 36 and show no Egg/Gift
  Card in any of the 41 recorded steps; the source surcharge (+3) explains base
  $5 → current cost $8 → sell $4 without extra_value. They also show Negative
  Dagger, which explains its sell $5 from base $6 + surcharge $5. These engine
  steps support a source calculation/check, but are not independent video inputs.
  The #124 regression passes all three source-derived sell values through the
  same reducer and matches the isolated sidecar's Mult `0→6→14→22`; per-round
  growth is `6, 8, 8`. This checks the engine-source mechanics slice, not
  video-only inference.

## 2026-10-05: Live Dagger reference captures separate Mult growth from victim removal

- Context: Issue #123 authorized capture, run `1662755302000-5667` (41-step
  loss), associated after explicit owner confirmation with
  `F:\OBS_RECORDINGS\2026-10-05 14-19-09.mkv` and marker
  `issue81-20261005T211909Z` in the external RunBundle
  `F:\OBS_RECORDINGS\issue123_dagger_reference.sqlite`.
- Observation: Reference-only Dagger instance `47973` grew 0→6 at step `:12`
  (Castle `47669`, sell value $3), 6→14 at `:26` (Burnt Joker `49101`, $4),
  and 14→22 at `:36` (Photograph `51265`, $4). Each increment matches twice
  the independently captured victim sell value; each victim remains present
  in the immediate resolved-phase Joker row but is absent in a later pre-action
  row. No intervening STEP action is needed to read the changed Mult.
- Implication: The post-update `resolved` record establishes the Dagger Mult
  mutation, not completed victim dissolution. Keep separate timing claims for
  the two effects. Reference IDs and prices remain outside generic step reads.
  Candidate 60-FPS frame arithmetic is not verified rendered alignment.
- Verification/source: `python -m run_bundle validate --db
  "F:\OBS_RECORDINGS\issue123_dagger_reference.sqlite" --run
  1662755302000-5667 --strict` returned `valid`, 85 records, no bad sequences;
  `python -m run_bundle provenance` has session/steps/reference SHA-256 and
  confirmed marker/video association. Video SHA-256 is
  `ee7b7dd1c88435349b37fe89b2b4156fcd31c2b2de130ef2c586496a5ca984d5`.
  The first 87-step fragment remains active with missing outcome, and the
  separate 96-step Dagger loss has no original marker; neither is repaired or
  silently associated with a video.

## 2026-10-06: Three Dagger video intervals show matching Mult endpoints

- Context: Issue #127's actual-video diagnostic on the user-associated
  `1662755302000-5667` recording; video SHA-256
  `ee7b7dd1c88435349b37fe89b2b4156fcd31c2b2de130ef2c586496a5ca984d5`. The user
  visually confirmed the sampled sequence contains three Dagger sacrifice/trigger
  intervals.
- Observation: At 60 FPS the recording marker maps reference steps 12, 26, and
  36 to candidate frames 2404, 4569, and 5738. Extracted frames at each candidate
  and ±3 frames show stable pre-action Dagger Mult 0, 6, and 14; next-step
  candidates 2582, 4767, and 5876 show 6, 14, and 22. The isolated mechanics
  reference records respectively `0→6 (+6)`, `6→14 (+8)`, and `14→22 (+8)`.
  Decoded presentation timestamps at the three pre-action candidates differ from
  marker-derived elapsed time by −5.197 ms, +7.840 ms, and +4.782 ms. Frame PTS
  deltas are 16/17 ms around the candidates; the sole 33 ms gap is at the video
  tail, outside these intervals.
  The visible endpoint and interval-delta fields therefore match 6/6 and 3/3
  sampled comparisons. The same video-only adapter, run without tooltip prices,
  returns unknown causal effects for all three intervals while retaining visible
  deltas +6/+8/+8; it never copies engine answers or victim prices into inputs.
- Implication: For these three user-reviewed intervals only, rendered
  pre-action correspondence is confirmed within ±3 frames. Directly observed
  Mult endpoints can validate state and support a separate observed delta, while
  missing tooltip/pricing evidence still makes the reducer's causal sell/growth
  result abstain. The observed post-state can re-establish a later baseline
  without making the prior causal effect known. This is one development recording,
  not CV accuracy, held-out evaluation, a coverage pass, or alignment of the rest
  of the video.
- Verification/source: read-only bundle summary reports `valid` integrity, 85 records; `python
  planning/align_oracle_video.py
  "F:\OBS_RECORDINGS\oracle_runs_issue123\1662755302000-5667\steps.ndjson"`
  maps steps 12/26/36 to 2404/4569/5738 and the following steps 13/27/37 to
  2582/4767/5876. FFprobe decoded 6765 frame PTS values, with 2254 intervals of
  16 ms, 4509 of 17 ms, and one terminal 33 ms gap. `python -m run_bundle
  mechanics-reference --db "F:\OBS_RECORDINGS\issue123_dagger_reference.sqlite"
  --run 1662755302000-5667 --step-id <step-id>` reports valid isolated records.
  In-memory adapter output: `(step-12, unknown, 0, null, +6)`, `(step-26,
  unknown, 6, null, +8)`, `(step-36, unknown, 14, null, +8)` where fields are
  interval, causal-effect status, pre-Mult, inferred post-Mult, visible endpoint
  delta. Extracted review frames remain in the local temp directory, not Git.

## 2026-10-04: Existing Dagger video is not an aligned engine-reference capture

- Context: Issue #123 inspection of the Dagger footage identified in
  `planning/ISSUE115_RECORDING_AUDIT.md` and `planning/RUN_MECHANICS_DESIGN.md`.
- Observation: The source recording is
  `F:\OBS_RECORDINGS\2026-10-03 17-56-28.mkv`; the derived unscored clip is
  `F:\OBS_RECORDINGS\qa_debug\review-20261004T041049Z-a2572aa9\clip.mp4`.
  Its manifest associates runs `1898258342000-5384` and
  `2317688862100-2663`, explicitly marks alignment `unverified`, and records
  that the second run lacks its original recording marker. The local
  `run_bundle_issue79.sqlite` has neither run ID. The resumed segment displays
  Dagger +70 before a candidate sacrifice and +74 at a later action boundary;
  the stored snapshots do not record Mult, actual sell cost, or an engine
  instance identity.
- Implication: The old recording remains descriptive evidence only. It cannot
  establish exact pre-Mult, victim price, resolved queued aftermath, or identity
  for #123; retain these values as unknown until a pinned live reference capture.
- Verification/source: Read-only `python -m showman inspect list --db
  "F:\OBS_RECORDINGS\run_bundle_issue79.sqlite"`; bundle queries for both run
  IDs returned `run_not_found`; `planning/ISSUE115_RECORDING_AUDIT.md` lines
  32-55, 187-219; external QA manifest at the path above. No source bundle or
  video was modified.

## 2026-10-04: Poll the installed Dagger mutation after the game update

- Context: Issue #123 resolved-reference instrumentation for the installed
  Balatro runtime documented in `planning/BALATRO_RUNTIME.md`.
- Observation: Installed `Balatro.exe` SHA-256 is
  `0d75fe164accf3312734d4b37ac98788dd15f0b8e4f9bb8b7f90c4e59de93f47`.
  The unpatched `lovely/game-dump/card.lua` hash is
  `5073d834e08119da9516f1795a8c3d93110669aeb409c29ad1b308e0eb0be453`, matching
  the embedded game source; `functions/state_events.lua` hashes to
  `6c86aefb42d0323d737f87aaa84f53e42b755e72cd0bfd163b7d9cca5c0a99a9`.
  In that unpatched source `card.lua:2566-2576` mutates Mult inside a queued
  callback. The active post-Lovely `lovely/dump/card.lua` instead calls
  `SMODS.scale_card` synchronously at `:2969-2980`, leaving the victim dissolve
  queued. Its SHA-256 is
  `2ba1276c5850ea966733d4144602d866dddbb9cbfff1f588f409114d79584f54`;
  the active patch source is `smods-main/lovely/scaling.toml` (SHA-256
  `ade9f4a7f8b87ea64fe094445354a89710762950e8d9916d3354f779d8ba7666`).
  The producer samples after the original `Game.update` returns, so the
  captured Mult has changed without implying the victim is already removed.
- Implication: Record the pre-action baseline with the blind-selection step,
  then write a separate resolved reference record on the first post-update
  observation of the mutation on the same Dagger instance. Tie both records by
  run/step and retain runtime, instance tokens, victim price, observed Mult
  delta, and both monotonic timestamps. This trace is specific to this installed
  patch stack; other source stacks require a new trace before exact timing claims.
- Verification/source: Read-only source inspection and SHA-256 of the installed
  executable/generated dump; focused LÖVE producer fixture simulates an event
  resolution and verifies pre/resolved fields. This does not replace the live
  capture check.

## 2026-10-04: Launch grouped video reviews from a quoted JSON manifest

- Context: Two external Issue #82 videos had to be launched with associated
  oracle directories, including a single play split across two recorder IDs.
- Observation: PowerShell `Start-Process -ArgumentList` with an array split a
  space-containing MKV path and the viewer rejected its trailing filename. A
  single quoted argument string worked. Each viewer also needs an independent
  external export root and its own local URL; two recorder fragments of one
  video must be passed to one viewer process.
- Implication: Use `ground_truth.qa_viewer_launch` with a UTF-8 JSON manifest to
  anchor relative paths, retain explicit video/run grouping, allocate separate
  external output folders, and collect startup logs. Do not infer group identity
  from filenames or recorder ID count.
- Verification/source: Launched both 2026-10-03 Issue #82 videos from their
  actual external paths on 2026-10-04; both servers printed ready URLs, loaded
  their listed runs without diagnostics, and left source video/run files intact.
  PowerShell argument failure and corrected launch output are documented in
  `docs/capture/video-review.md`. This verifies startup only, not frame alignment.

## 2026-10-03: Continue can restore earlier counters without changing logical run identity

- Context: Issue #115's fixed-build live smoke preserved source ID
  `269979952000-1630` and requests 11→12 across a Main Menu/Continue visit.
- Observation: Both pre-action snapshots have zero score and four hands. The
  intervening Options frame shows the first hand resolved to score 13 and three
  hands; Continue visibly restores the earlier state. Source identity and marker
  remain continuous through all 32 records and final loss. The save timing/cause
  of the restored state was not established.
- Implication: Identity continuity is distinct from state continuity. Preserve
  repeated attempted actions across save restoration rather than deduplicating
  equal state/action payloads or assuming counters must remain monotonic.
- Verification/source: `planning/ISSUE115_RECORDING_AUDIT.md`, fixed-build smoke;
  oracle integrity audit passed; decoded frames at 58.763910, 61.5, 63.5 and
  75.175626 seconds. This is lifecycle verification, not measured reconstruction
  quality or confirmed event-edge alignment within ±3 frames.

## 2026-10-03: A quarantined recording marker can contain valid bytes

- Context: A subsequent #115 capture had 135 valid source steps but no attached
  recording object. Its preserved `recording_start_marker.json.invalid` contained
  a marker accepted by the current consumer in an isolated temporary fixture.
- Observation: `_attach_recording_marker` groups OSError with JSON decode errors
  and attempts quarantine for either. Injecting FileNotFoundError during a fixture
  read moved the otherwise valid marker to `.invalid`. The actual read exception
  responsible for the real capture is unknown.
- Implication: A quarantine suffix alone does not establish malformed bytes;
  preserve and validate the evidence separately, without repairing source files
  or inferring confirmation. Transient read failure and invalid content need
  distinct handling in any future reader fix.
- Verification/source: `planning/ISSUE115_RECORDING_AUDIT.md`, subsequent-capture
  section; isolated diagnostic `issue115_new_capture.py` under the approved temp
  directory; `ground_truth/file_ipc_bridge.py` recording-marker read exception path.

## 2026-10-03: Equal resume boundary counters are not duplicate action records

- Context: Issue #115 inspected 15 persisted oracle sessions (1,543 steps),
  including the user-confirmed menu/Continue split in the latest recording.
- Observation: `1898258342000-5384:109` and `2317688862100-2663:1` have equal
  scalar state 12.8777339 seconds apart, but select different cards. Decoded
  frames show the same Big Blind, score, resources and jokers with those distinct
  selections. Raw tracked-deck array ordering changes after reload. The existing
  auditor also crashed on absent legacy timestamps and falsely reported missing
  raw fields for populated `producer/1.0.0` snapshots.
- Implication: Group confirmed fragments by source recording/play while retaining
  every original source step; counter equality alone does not justify deduplication.
  Inspect actual payload coverage independently of schema-name assumptions.
- Verification/source: `planning/ISSUE115_RECORDING_AUDIT.md`; archive audit,
  decoded candidate frames at 412.6541974 / 425.5319313 seconds, and focused
  audit/producer/consumer tests (55 passed). Event-edge alignment and fresh live
  Continue verification remain pending.

## 2026-10-03: Installed Balatro Lua source is readable from the executable

- Context: Locate the installed game's source for agent reference on Cam's
  Windows machine.
- Observation: `C:\Program Files (x86)\Steam\steamapps\common\Balatro\Balatro.exe`
  contains an embedded ZIP archive readable with Python's `zipfile`. It contains
  47 Lua files, including `main.lua`, `game.lua`, `card.lua`, `blind.lua`, and
  `globals.lua`.
- Implication: Agents can inspect the installed Lua source without extracting
  files or modifying the installation. The path and contents are machine- and
  version-specific; `AGENTS.md` includes a read-only inspection command.
- Verification/source: Read the installation directory and enumerated the
  executable's archive with `zipfile.ZipFile`; counted 47 `.lua` entries and
  verified `game.lua` can be read and decoded as UTF-8 on 2026-10-03.

## 2026-10-03: Debug exports need the same source bytes as the displayed records

- Context: Issue #118's video/action viewer exports original oracle lines beside
  a derived clip. Independent review identified a race between hash checks and
  reading the selected lines after a potentially long ffmpeg extraction.
- Observation: Checking a file before extraction does not establish that a later
  read has the same bytes. The viewer now freezes bytes matching the displayed
  parsed records and source hashes, exports those lines, and rechecks inputs after
  extraction. A mutation-during-extraction fixture rejects the package and retains
  its incomplete marker.
- Implication: Keep payloads, copied evidence and their hashes tied to one source
  snapshot; clip production must not silently switch the version of source lines.
- Verification/source: `tests/test_qa_viewer.py` (7 tests passed, including real
  ffmpeg export and mutation-during-extraction); `docs/capture/video-review.md`.
  Browser QA exported five original steps with verified input/output hashes;
  candidate rendered alignment and frame-exact clip timing remain unverified.

## 2026-10-03: One OBS recording can span multiple oracle run IDs

- Context: The Issue #79 development capture contained an Ante 1 run segment,
  followed by a second oracle session in the same video.
- Observation: The first session ended at Ante 5 with no terminal signal; the
  second began in the identical Ante 5 state 13.6 seconds later and ended in a
  win. `Game.start_run` assigns a new producer `run_id`, and the bridge attaches
  a given recording marker ID only once. Consequently the marker appeared on the
  first session only. A single OBS file can therefore cover multiple oracle IDs
  even when the saved game state continues across the boundary.
- Implication: Preserve each oracle session as its own run, inspect the video
  across the boundary, and associate only the marker-supported run unless a
  separate, explicit association is recorded for another segment. Do not infer
  continuity from either run ID or video membership alone.
- Verification/source: Source inspection of `ground_truth/balatro_mod/main.lua`
  (`Game.start_run`) and `ground_truth/file_ipc_bridge.py`
  (`_attached_recording_ids`); Issue #79 recording `issue81-20261003T070517Z`,
  sessions `25980339600-7022` and `778812964300-9775`, their 197 ordered steps,
  and the 60 FPS video. The first-slice segment is confirmed to be in the first
  session; the overall capture is a single observed instance, not a frequency
  estimate.

## 2026-10-02: Passing local tests leave capture lifecycle faults uncovered

- Context: Production retrospective of the active file-IPC recorder.
- Observation: The local suite passed 91 tests and 15 subtests. Separate isolated
  fixtures reproduced a restart leaving two persisted records but `n_steps=1`,
  deletion of malformed input, and a pending snapshot reopening a finalized run
  with a null outcome. The GitHub workflow runs planning/tag checks, not pytest.
- Implication: Add capture restart/finalization/failure acceptance tests before
  relying on recorder output for evaluation. Distinguish planning CI, local
  component tests, and measured live evidence when reporting quality.
- Verification/source: `planning/PRODUCTION_RETROSPECTIVE_2026-10-02.md`,
  Verification record and code references; independent reviewer reproduced the
  fixture results. Real-game failure frequency was not measured.

## 2026-10-02: Request identity claims must be pinned to producer revision

- Context: Migration research compared old run reports with current Lua source.
- Observation: Older reports show per-run request sequences, but current Lua
  initializes local `request_counter` once and `Game.start_run` changes run identity
  without resetting it. The bridge still keys in-memory deduplication by request
  ID alone. The lead also reproduced the three capture faults above in isolated
  fixtures during #92.
- Implication: Do not infer current counter lifetime from older captures. Test
  run-scoped identity across restarts and delayed/missing end signals in #81.
- Verification/source: Explorer C task `ses_f015be329ffeywdOpdk5Y8hoxQ` inspected
  `ground_truth/balatro_mod/main.lua` initialization, emit and start-run hooks;
  `ground_truth/file_ipc_bridge.py` maps. Diagnostic output is recorded in
  `planning/WORKFLOW_MIGRATION_VERIFICATION.md`. No live frequency measured.

## 2026-10-01: Long-running work needs a clean session boundary

- Context: The repository uses multiple agent sessions on shared work-item
  branches and relies on thread batons to transfer execution state.
- Observation: Published agent-harness guidance recommends incremental progress,
  clean end states, and structured progress artifacts for the next session;
  GitHub's cloud-agent workflow likewise makes branch, commit, test, and PR
  state inspectable; OpenAI's harness-engineering report treats repository-local
  knowledge, validation, review, and merge as the agent's end-to-end loop.
- Implication: `/work` should end only with either a verified baton for a fresh
  agent context or a fully completed thread with green checks, required review
  evidence, and merge/settlement. Findings that prevent repeated investigation
  should be promoted to this file rather than left in chat.
- Verification/source: `planning/agent-workflow.md` §`/work` Execution Rule and
  Handoff Protocol; Anthropic, “Effective harnesses for long-running agents,”
  2025-11-26, https://www.anthropic.com/engineering/effective-harnesses-for-long-running-agents;
  GitHub, “About GitHub Copilot cloud agent,” accessed 2026-10-01,
  https://docs.github.com/en/copilot/concepts/agents/coding-agent/about-coding-agent;
  OpenAI, “Harness engineering: leveraging Codex in an agent-first world,”
  2026-02-11, https://openai.com/index/harness-engineering/.

## 2026-10-02: Review evidence must gate completion, not only merge

- Context: Issue #69 found a T2 PR merged with green CI but without the required
  fresh-context reviewer verdict.
- Observation: GitHub separates required reviews, status checks, stale-review
  invalidation, and branch/base requirements; agent-harness guidance likewise
  emphasizes repository-local evidence, incremental work, and mechanical checks.
- Implication: The lead must verify and record reviewer, CI, base/diff,
  dependency, merge, and settlement gates independently. A successful merge
  cannot retroactively prove review compliance.
- Verification/source: GitHub protected-branch documentation accessed
  2026-10-02; Anthropic, “Effective harnesses for long-running agents,”
  2025-11-26; OpenAI, “Harness engineering,” 2026-02-11; Issue #69; and the
  regression markers in `planning/check_contracts.py`.

## 2026-10-02: Handoffs need an owned-worktree boundary

- Context: Issue #69 follow-up requested that workers not leave leftovers for
  later sessions.
- Observation: A baton is useful only when the next worker can distinguish
  committed work from local residue; shared worktrees can also contain changes
  owned by another worker or the user.
- Implication: Require `git status` inspection, commit all worker-owned changes
  and handoff artifacts in the PR, remove owned temporary/generated files, and
  preserve unrelated changes with an explicit exclusion note.
- Verification/source: D027 and the handoff gate in `planning/agent-workflow.md`.

## 2026-10-01: PR bodies must use real multiline input

- Context: Recent PR history included bodies with literal `\\n` sequences where
  section breaks were intended.
- Observation: Passing an escaped string directly to `gh pr create --body` can
  preserve the escape text instead of creating line breaks.
- Implication: Construct substantial issue and PR bodies as multiline files or
  heredocs, then search the final body for unintended `\\n` before submission.
- Verification/source: PR history reviewed while implementing Issue #37; the
  rule is encoded in `.opencode/skill/deslop/SKILL.md` and `AGENTS.md`.

## 2026-10-01: T2 reviewer evidence must be recorded before merge

- Context: Retrospective review of merged Issue #47 PR #57.
- Observation: The compatibility implementation and required CI checks passed, but GitHub has no review record and a fresh-context reviewer found unspecified edge cases in incomplete session metadata and blank NDJSON lines.
- Implication: A green check and a correct-looking diff do not establish the T2 approval boundary; record the independent reviewer verdict on the PR before merging, and keep unresolved compatibility-envelope questions explicit rather than silently enforcing a new interpretation.
- Verification/source: `gh pr view 57 --json reviews,statusCheckRollup,state,mergedAt`; fresh-context reviewer report; `planning/agent-workflow.md` §Approval And Merging.

## 2026-09-30: Bounded autonomy is safer than an unconstrained swarm

- Context: The repository needed agents that could make independent progress on
  complex work without weakening its evidence and approval gates.
- Observation: OpenCode's primary/subagent split, task permissions, finite
  `steps`, commands, and automatic compaction support a lead loop with narrow
  delegation and explicit stopping conditions. Anthropic's agent guidance also
  emphasizes simple composable workflows, environmental ground truth, evaluator
  loops, and human checkpoints.
- Implication: Use one project lead as the default owner; reserve explorer and
  reviewer subagents for independent evidence and adversarial verification.
  Encode checkpoints in prompts and commands rather than adding a custom
  orchestration plugin.
- Verification/source: OpenCode Agents, Commands, Skills, Plugins, and config
  schema docs fetched 2026-09-30; Anthropic, “Building effective agents,”
  published 2024-12-19; repository workflow in `planning/agent-workflow.md`.

## 2026-09-30: Legacy references do not satisfy the Phase 0 boundary

- Context: Phase 0 inventory checked the legacy CV/policy trees, annotation
  helpers, sample runs, and planning contracts.
- Observation: Candidate checkpoints, OCR geometry, schemas, and labeling code
  exist only under `legacy/`; no active provenance records, runnable checked-in
  Lua bridge, real eval clips, or exported eval manifest were found.
- Implication: Legacy artifacts may guide research, but cannot be treated as
  active dependencies or as evidence that the oracle/evaluation gate passed.
- Verification/source: `planning/PHASE0_INVENTORY.md`,
  `planning/ARCHITECTURE.md:84-99`, and the ground-truth contract.

## 2026-09-30: A usable local modded runtime is available

- Context: The local machine was inspected for the Phase 0 bridge feasibility
  work.
- Observation: Steamodded, Lovely, multiple mods, Lovely game dumps/logs, and a
  Steamodded debug socket are present under the user's Balatro data directory.
  The latest log reports version `26.926.0~dev-a` and Lovely `0.10.0`, but also
  reports blacklisted mods and invalid metadata warnings.
- Implication: Bridge work can begin with a read-only compatibility audit and a
  controlled smoke test; the runtime must not yet be treated as a clean oracle.
- Verification/source: `planning/BALATRO_RUNTIME.md` and the verified Lovely
  launch log recorded there.

## 2026-09-30: ONNX + ONNX Runtime is the "Docker" layer for device-portable inference

- Context: D012 required batch GPU to remain possible without changing data
  contracts, but the planning docs did not name a concrete mechanism, and the
  Phase 3 gate demanded "byte-compatible" output across devices.
- Observation: ONNX (versioned model format, pinned opsets) plus ONNX Runtime
  execution providers (CPU, DirectML, CUDA/TensorRT) gives one inference API
  where the device is a provider-ordered session option. All are MIT-licensed
  and free. DirectML is supported, which rules out JAX for this Windows-first
  project. Cross-provider byte-identity is not realistic: different execution
  providers legitimately differ in low-order float bits, so contracts must pin
  a numeric tolerance instead. The Python array API standard
  (data-apis.org) is the analogous device-neutral interface for non-model
  tensor code.
- Implication: Adopted as D017. Detection/Phase 3 gates now require the same
  `.onnx` artifact run under different providers with tolerance-based
  contract compatibility rather than byte-identity.
- Verification/source: onnxruntime.ai execution-provider docs and
  data-apis.org array API standard fetched 2026-09-30; MIT licenses stated in
  the ONNX and ONNX Runtime repository licenses.

## 2026-09-30: Oracle step identity and producer diagnostics need explicit scoping

- Context: The Issue #10 integrity review audited the two persisted runs
  (`F:\OBS_RECORDINGS\oracle_runs\`, 433-step win and 43-step loss).
- Observation: `request_id` restarts at `1` each run, so it is unique only
  within a run and must be keyed with `run_id`. Producer diagnostic fields
  (`meta.game_state`, `meta.pack_kind`, `meta.pack_key`) are not part of any
  storage contract, are absent from the older win run, and in the loss run hold
  a stale pack key across non-pack `G.STATE` values because the field was not
  yet gated to state 999.
- Implication: Never aggregate or join oracle steps on `request_id` alone, and
  do not treat producer diagnostics as observed state. When reading an
  intermediate-revision run, gate `pack_kind`/`pack_key` to `G.STATE == 999`
  before use.
- Verification/source: `planning/audit_oracle_runs.py` output and direct JSON
  inspection, recorded in `planning/ORACLE_DATA_REVIEW.md` §4.2 and §4.4.

## 2026-09-30: File-glob tools can silently skip dot-directories

- Context: Assessing whether `.opencode/command/` existed before proposing an orchestrator work item (Issue #25).
- Observation: The workspace glob tool returned "No files found" for `.opencode/**/*` even though `.opencode/command/`, `.opencode/agents/`, and `.opencode/skill/` all exist; glob patterns apparently ignore dot-directories in this harness. A shell directory listing corrected the record.
- Implication: Do not claim a referenced path is missing based on glob output alone; verify dot-directories with a shell listing before opening a remediation issue. A false "missing files" claim was made and retracted this session.
- Verification/source: `Get-ChildItem .opencode\command, .opencode\agents` listing on 2026-09-30, contrasted with the earlier empty glob result.

## 2026-09-30: Balatro card attribute fields for the producer

- Context: Issue #12 needed the oracle to emit modifier/edition/seal/stickers
  for card and inventory objects matching the adopted object schema.
- Observation: In the installed Balatro `1.0.1o-FULL` game dump, a playing
  card's enhancement is `card.config.center.key` (normal cards use `c_base`;
  enhancements are `m_*`); the edition is `card.edition.type` in
  `{foil,holo,polychrome,negative}` (boolean flags `card.edition.<type>` also
  exist); the seal is `card.seal` in `{Red,Blue,Gold,Purple}`; and
  rental/perishable/eternal are booleans at `card.ability.rental`,
  `.perishable`, `.eternal`. Inventory `class_id` comes from `center_key`
  (`card.config.center.key`), which for base-game jokers/consumables/vouchers
  equals the vendored class-map `class_name`.
- Implication: The adopted contract defines `modifier`/`edition`/`seal` as
  `str | None` but `stickers` as `list[str]` (empty when none). Playing cards
  never carry the three stickers, so `pending_cards.stickers` is structurally
  empty; the audit's pending all-null check excludes it.
- Verification/source: read-only inspection of
  `%APPDATA%\Balatro\Mods\lovely\game-dump\card.lua`
  (`Card:set_edition`, `Card:set_seal`, sticker badges) on 2026-09-30, plus
  `legacy/vendor/balatro-policy-transformer/state_schema.md` §3.

## 2026-09-30: Vendored `legacy/vendor/*` trees are gitlinks without `.gitmodules`

- Context: Issue #12 added a test that reads the vendored class map and a
  generator that embeds it in the Lua producer; a fresh linked worktree was
  created to do the work.
- Observation: `git ls-files -s legacy/vendor/` shows mode `160000` gitlinks for
  `balatro-cv-pipeline` and `balatro-policy-transformer`, but `HEAD` has no
  `.gitmodules` and each directory contains its own `.git`. Contents are not
  tracked by this repository, so a linked worktree or fresh clone has empty
  `legacy/vendor/` directories.
- Implication: Do not rely on vendored files being present in a linked worktree
  or CI checkout. The class-ID test and generator require the vendored map
  locally; `check_contracts.py` does not reference vendored paths, so CI is
  unaffected. Work needing vendored content should use the main worktree (as
  Issue #18 did) and record the dependency.
- Verification/source: `git ls-tree HEAD legacy/vendor/`, `git show
  HEAD:.gitmodules` (absent), and `git worktree add` yielding empty vendor dirs
  on 2026-09-30.

## 2026-10-04: Inspection and legacy generation are not an active mechanics pipeline

- Context: Two-track planning audit at master `33338ea`.
- Observation: Inspector state deltas/transitions explicitly return unsupported;
  annotation export and the video/action viewer inspect existing evidence, not
  inferred mechanics. Active scene/glyph generation and mechanics reduction are
  absent. The legacy compositor lacks seeded configuration and source-level
  evaluation/background separation; its detector emits sampled detections only.
- Implication: Scope a reproducible pack and shared observation adapter explicitly;
  neither viewer availability nor legacy code establishes a reconstruction result.
- Verification/source: Read-only implementation audit of
  `run_bundle/inspection.py`, `ground_truth/eval_manifest.py`,
  `ground_truth/qa_viewer.py`, `legacy/tools/build_synthetic_dataset.py` and
  `legacy/tools/detect.py`; focused exporter/viewer tests: 26 passed, 5 subtests passed.

## 2026-09-30: Engine raw fields for the producer's persistent-state basis (Issue #21)

- Context: D021/D022 requires the oracle to emit engine-truth raw persistent fields and a legality basis without computing canonical `persistent_state`.
- Observation: Verified by read-only inspection of `%APPDATA%\Balatro\Mods\lovely\dump\`: `G.GAME.selected_back_key` (deck center key, game.lua:2044), `G.GAME.stake` numeric 1..8 with stake centers carrying `stake_level` (game.lua:253-260), `G.GAME.used_vouchers` (dict key->true), `G.GAME.bosses_used` (dict boss-key->count, incremented on boss selection in common_events.lua), `G.GAME.hands[name]` = {level, played, played_this_round}, `G.GAME.round_resets` = {ante, blind_ante, blind_states{Small,Big,Boss} strings in {'Select','Upcoming','Skipped','Defeated'}, blind_choices, blind_tags{Small,Big}, boss_rerolled}, `G.GAME.current_round.reroll_cost`/`.free_rerolls`, and counters `skips`/`hands_played`/`unused_discards`/`ecto_minus`/`last_tarot_planet` (a center key). `G.playing_cards` is the run's full playing-card list (cards leave `G.deck.cards` when drawn); stone cards keep a real `card.base` suit/rank (Card constructor, card.lua:127). `first_hand`/`first_discard` are NOT engine fields (reducer-computed). Canonical deck flags derive from deck class_id (`state_reducer.py::apply_deck_initialization`), with `G.GAME.starting_params.no_faces` (Abandoned) as the raw basis.
- Implication: The producer emits these reads verbatim under `raw_persistent` with failure-isolated nulls, plus `legal_actions`/`mask_basis` gating per `mask_schema.md` 2-3; `G.FUNCS.toggle_shop` is the cash-out "Next Round"/shop-leave button, so the recorded action must always be included in `legal_actions` (the file-IPC client rejects snapshots whose `action_taken` is absent).
- Verification/source: lupa (Lua 5.1) harness in the user temp directory executing `ground_truth/balatro_mod/main.lua` against a stub `G` — raw fields, legality across blind/shop/pack/unknown pages, and client acceptance all pass; grep of the lovely dump files cited above.

## 2026-09-30: Steamodded 26.926 runtime diverges from the vanilla game dump on three raw-field reads

- Context: Issue #21's first real `live/3.0.0` capture (50 steps across two sessions in `F:\OBS_RECORDINGS\oracle_runs_live3\`) exposed gaps between the vanilla dump (`lovely\game-dump\`) and the actual patched runtime.
- Observation: (1) `G.GAME.selected_back_key` is null on every step; Steamodded reads the deck center at `G.GAME.selected_back.effect.center.key` (`smods-main/src/overrides.lua:2401-2402`). (2) Stake centers do not match `stake_level == G.GAME.stake` (SMODS renumbers `stake_level` by applied-chain length, `game_object.lua:863-866`); the engine mapping is `G.P_CENTER_POOLS.Stake[G.GAME.stake].key` (= `SMODS.stake_from_index`, `overrides.lua:2407`, `ui.lua:3421`). (3) `G.GAME.bosses_used` is nested `{boss/small/big: {blind_key: count}}` via `SMODS.normalize_bosses_used_table` (`blind.lua`), not the flat `{blind_key: count}` the vanilla dump shows; the real capture also shows `blind_states` uses a fifth value `'Current'`.
- Implication: The producer now reads deck/stake through the Steamodded paths with the vanilla-dump reads as fallbacks, and serializes nested game tables recursively (depth-capped, sorted keys, explicit nulls). Raw emission of nested engine structures must never flatten or drop sub-tables; verify dump-derived field claims against a real capture before relying on them.
- Verification/source: `planning/audit_oracle_runs.py` output on the real capture (50/50 steps legal + mask_basis + counters, deck/stake center keys null), read-only grep of `smods-main/src/`, and the two persisted run directories.
## 2026-09-30: Live/2.0 shop and pack offering zones map to four CardAreas

- Context: Issue #16 needed the Lua producer to snapshot the shop and
  opened-pack offering zones that the adopted action space resolves
  buy/select targets against.
- Observation: In the installed Balatro `1.0.1o-FULL` dump
  (`%APPDATA%\Balatro\Mods\lovely\game-dump`), the shop UI creates exactly
  `G.shop_jokers` (top shelf, jokers/consumables), `G.shop_vouchers` (one
  voucher), and `G.shop_booster` (**singular**), and an opened booster fills
  `G.pack_cards`. `G.shop` is a UIBox, not a CardArea. The canonical live/2.0
  zones are `TopShelfShopOfferings`, `VoucherShopOfferings`,
  `PackShopOfferings`, and `PackOfferings`; the vendored `granularize.py`,
  `mask_builder.py`, `live_encoder.py`, and `live/smoke_test.py` reference only
  these. Bare `ShopOfferings` is absent from the canonical live action map and
  zone vocabulary; it survives only in deprecated/compat paths
  (`data/masking_schema_disorganized.md`, deprecated `action_space_schema.md`
  §5, `compute_action_space_config.py`, `training_data_pipeline.md`) and in the
  review document that proposed it (`ORACLE_DATA_REVIEW.md` §4.5, §7 P5). It
  has no distinct live source, so it is an overloaded legacy alias.
  Booster center keys carry a size suffix (e.g. `p_arcana_normal_1`), so a pack
  object's `class_id` is null against the vendored map while `center_key` is
  retained.
- Implication: Producers must read `G.shop_booster` (not `G.shop_boosters`) and
  emit the four split zones; emitting bare `ShopOfferings` would duplicate
  candidates and reintroduce a name the canonical contract does not define.
- Verification/source: read-only inspection of
  `%APPDATA%\Balatro\Mods\lovely\game-dump\functions\UI_definitions.lua:637-658`,
  `%APPDATA%\Balatro\Mods\smods-main\src\game_object.lua:1723`, and
  `legacy/vendor/balatro-policy-transformer/{granularize.py,mask_builder.py,live/live_encoder.py,live/smoke_test.py,action_map.py}`
  on 2026-09-30.
