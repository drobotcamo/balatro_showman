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
