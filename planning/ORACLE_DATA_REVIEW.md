# Oracle Data Integrity and Storage-Contract Conformance (Issue #10)

Status: review complete; proposals tracked as follow-up issues (P5 applied by
Issue #16/PR #28, others pending).
Parent: Issue #6 (Lua producer, merged in PR #9). Owner: Issue #10.
Evidence is external and not committed (D016): run directories under
`F:\OBS_RECORDINGS\oracle_runs\`. This document records findings, not data.

Reconciliation, 2026-10-02 (D028): the sections below preserve dated review
findings and proposals, not a live follow-up queue. Sections 2/6 report a pinned
29-step run with marker and positive frame mappings; this is different evidence
from the older runs. Those mappings do not establish measured synchronization
error or rendered pre-action correspondence. Current recorder fault fixtures
and semantic limits are recorded in the production retrospective. External video
was not replayed for this reconciliation. GitHub #81 owns current capture/inspect
acceptance; #79/#82 stage protocol/tooling, and Q03 criteria are progressive.
Old all-phase timing/proposal status below is historical, not reinstated policy.

## 1. Purpose and Scope

Verify the integrity of the two persisted Lua-oracle runs and confirm whether
their fields conform to the Phase 0 storage contracts or record the exact gaps.
In scope: integrity counts, field-by-field mapping to the intended long-term
step/persistent-state storage, a Phase 0 oracle-gate verdict, and unapplied
proposals. Out of scope: building the reconstruction pipeline, changing
contracts or durable policy, setting Phase 1-10 thresholds, expanding the
producer's action space, and event extraction.

## 2. Evidence Under Review

| Run | Steps | Outcome | Directory | Video |
| --- | --- | --- | --- | --- |
| win | 433 | win | `F:\OBS_RECORDINGS\oracle_runs\2026-09-30_14-50-37_1790805058-5327\` | `F:\OBS_RECORDINGS\2026-09-30 14-50-37.mkv` |
| loss (verify) | 43 | loss | `F:\OBS_RECORDINGS\oracle_runs\2026-09-30_15-31_verify_1790807319-8546\` | none recorded |
| loss (superseded candidate) | 39 | loss | `F:\OBS_RECORDINGS\oracle_runs\1790821374-5833\` | none recorded |
| loss (merged revision) | 29 | loss | `F:\OBS_RECORDINGS\oracle_runs\184013382700-5967\` | `F:\OBS_RECORDINGS\2026-10-01 00-58-04.mkv` |

Each run directory holds `session.json` (client contract `record/1.0.0`),
`steps.ndjson` (client-added `_recorded_action`, snapshot contract
`live/2.0.0`). The original win and verify directories also contain `NOTE.txt`.
Runtime is identical across the reviewed runs: Balatro
`1.0.1o-FULL`, Steamodded `26.926.0~dev-a`, Lovely `0.10.0`.

**Provenance caveat.** The win and verify runs predate the merged producer
revision. The loss run is an intermediate revision where pack diagnostics were
not yet gated to `G.STATE == 999` (see §4.4). The new run was captured after
reinstalling the checked-in producer and restarting Balatro; source and
installed `main.lua` SHA-256 matched
`2BDC1B14C2BC27D37861168AAA58E7D634CD0D3567403BA84A570560A791C031`.

The superseded candidate loss run `1790821374-5833` covers blind select, in-blind play,
cash-out, shop, and both pack page families, and emits the newer offering zones
and canonical object IDs. It is not sufficient evidence: its directory has no
video or provenance note, its records have no frame index/offset or
merged-revision identifier, and the audit fails on a null
`capture_timestamp_ns` value before reporting integrity (`TypeError` in
`planning/audit_oracle_runs.py`). The merged-revision run
`184013382700-5967` covers blind select, in-blind play, cash-out, shop, and a
booster pack; its session contains the recording marker and its audit passes.

## 3. Method / Reproduction

`planning/audit_oracle_runs.py` is a read-only, stdlib-only audit. It fails
(exit 1) only on integrity invariants and reports conformance gaps as findings.
From the repository root:

```powershell
py -3 planning\audit_oracle_runs.py `
  "F:\OBS_RECORDINGS\oracle_runs\2026-09-30_14-50-37_1790805058-5327" `
  "F:\OBS_RECORDINGS\oracle_runs\2026-09-30_15-31_verify_1790807319-8546" `
  "F:\OBS_RECORDINGS\oracle_runs\184013382700-5967"
```

Result: `oracle run integrity OK` (exit 0). All counts below are this tool's
output unless a section states otherwise; the pack-diagnostic staleness check
is a direct JSON inspection and is marked as such.

## 4. Integrity Findings

### 4.1 Structural integrity — passed

- Step lines match `session.n_steps` exactly (433 and 43).
- Exactly one `run_id` per run, and it equals the `session.json` `run_id`.
- `request_id` is unique and non-null on every step; contiguous `1..N` per run.
- `action_taken` is non-empty on every step; `_recorded_action` equals it on all
  steps (client read the same value it acknowledged).
- `page_name` is present on every step.
- `session.outcome` is `win` / `loss` and `ended_at > started_at`.
- All 14 `state` keys are present on every step.
- Runtime metadata is identical across all steps in both runs.

### 4.2 Request-id identity

`request_id` restarts at `1` for each run (win `1..433`, loss `1..43`). It is
unique only within a run. Any downstream store must key steps by
`(run_id, request_id)` or remap to a global step id; keying by `request_id`
alone would collide across runs.

### 4.3 Page and action coverage

| Run | Pages (counts) | Actions (counts) |
| --- | --- | --- |
| win | In_Shop 191, In_Blind 149, `Unknown_999` 38, Blind_Select 28, Cash_Out 27 | UseConsumable 119, DiscardHand 57, BuyShopItem 57, RerollShop 46, PlayHand 39, SellItem 30, SelectBlind 23, CashOut 22, LeaveShop 22, SkipPack 14, SkipBlind 4 |
| loss | In_Blind 15, In_Shop 15, Blind_Select 5, `In_JokerStandardPlanet_Pack` 5, Cash_Out 3 | UseConsumable 13, PlayHand 11, BuyShopItem 4, SelectBlind 4, CashOut 3, LeaveShop 3, DiscardHand 2, SkipBlind 1, SellItem 1, RerollShop 1 |

The 38 `Unknown_999` steps in the win run are 8.8% of that run and are the
pre-fix Steamodded `SMODS_BOOSTER_OPENED` page. The loss run has zero unknown
pages but only 5 pack steps and no `In_TarotSpectral_Pack` or voucher state.

### 4.4 Pack-diagnostic staleness (verify run only)

In the verify run, `meta.pack_kind` / `meta.pack_key` are non-null on 23/43
steps and persist across non-pack states: the same `Celestial` /
`p_celestial_normal_1` appears on `G.STATE` 999 (pack), 5 (shop), 7
(blind-select), 1 (in-blind), and 8 (cash-out). At HEAD, `encode_meta` reads
these fields only when `G.STATE == 999`, so this is an intermediate-revision
artifact, not a HEAD behavior. It does mean the verify run's pack diagnostics
are unreliable outside its actual 999 steps. (Direct JSON inspection.)

### 4.5 Object-channel coverage

The `class_id` distinct counts below are direct JSON inspection; the remaining
counts are `planning/audit_oracle_runs.py` output.

| Metric | win | loss |
| --- | --- | --- |
| Total objects | 3526 | 177 |
| Object types | card 1388, joker 1759, tarot 227, spectral 117, planet 35 | card 120, joker 43, tarot 13, planet 1 |
| Zones | CurrentJokers 1759, CurrentHand 928, PendingCards 460, CurrentConsumables 379 | CurrentHand 73, PendingCards 47, CurrentJokers 43, CurrentConsumables 14 |
| Playing-card `class_id` | present, 0..51 (52 distinct non-null) | present, 0..51 (37 distinct non-null) |
| Inventory objects without `class_id` (center_key only) | 2138 / 2138 | 57 / 57 |
| `modifier` / `edition` / `seal` null | 3526 / 3526 (100%) | 177 / 177 (100%) |
| `pending_cards` total | 460 | 47 |

No card modifier, edition, or seal was captured in either run, and no
inventory object carries a canonical `class_id`. The pack/shop offering zones
the action space needs (`PackOfferings`, `VoucherShopOfferings`,
`TopShelfShopOfferings`, `ShopOfferings`) are never emitted: the producer only
snapshots hand/pending/jokers/consumables. Shop and pack contents are therefore
absent from the recorded state even though shop/pack actions were taken.

### 4.6 Value-range caveats (semantic, not corruption)

- win `deck_remaining` reaches 55 while `deck_total` is fixed at 52; the
  "remaining" count is `#G.deck.cards`, which can exceed the starting size when
  effects add cards. `deck_total` is `starting_deck_size`, not a live total.
- win `hand_size_current` reaches 18 while `hand_size_total` is 8–10;
  `hand_size_current` is the live hand count, which can exceed the configured
  card limit transiently.
- win `round` reaches 23 and `ante` 8; `round` is the global round counter, not
  a per-ante round index.
- `sent_at_real_time` is wall-clock seconds (`os.time()`); the win run has 413
  distinct seconds over 433 steps (max 2 steps share a second), so it is not a
  tick-accurate alignment clock.

## 5. Storage-Contract Conformance and Field Mapping

Target schemas: the adopted downstream contract (D009) as vendored under
`legacy/vendor/balatro-policy-transformer/` — step shape in
`granularization_schema.md` (schema `3.0.0`), persistent/observation/internal
fields in `state_schema.md`, labels in `action_space_schema.md`, masks in
`mask_schema.md` — plus the active component contracts in `planning/components/`.

### 5.1 Field-by-field mapping

| Producer field | Intended storage field | State | Notes |
| --- | --- | --- | --- |
| `schema_version:"live/2.0.0"` | granularized `3.0.0` / record `1.0.0` | **conflict** | Producer label is a transport label; it is neither the granularized step schema nor the session schema. Version semantics need a decision. |
| `request_id` | `step_id` | conformant with remap | Per-run only; map to `(run_id, request_id)` or global `step_id`. |
| `page_name` | `page_name` | conformant with caveat | Real page identity, but producer-derived from a hardcoded `G.STATE` map; win run has `Unknown_999`. Needs ontology vocabulary and the explicit-unknown convention. |
| `source_kind` | `source_kind` (`pass_through`/`select`/`commit`/`swap_synth`) | **missing** | Present on every step but always `null`. |
| `action_subtype` | `action_subtype` | **missing** | Present but always `null`. |
| `state.*` | observation fields | **partial** | 14 scalar fields present; missing `reroll_price` and `cash_out` (both `state_schema.md` §6 observations). `hand_and_level` is also absent but is a reducer OCR input (`state_schema.md` §5.3), not a per-step observation. Extra `deck_remaining`, `deck_total`, `round_score`, `hand_size_*`, `jokers_*`, `consumables_*` are useful observations. |
| `objects[]` | `objects[]` | **partial** | Zone + `position_in_zone` conform; playing cards conform; inventory objects lack canonical `class_id`; `modifier`/`edition`/`seal` all null; shop/pack offering zones absent. |
| `pending_cards[]` | `pending_cards[]` | conformant | List of card payload dicts (`class_id, object_type, modifier, edition, seal, card`), without the `zone`/`position_in_zone` keys that `objects` card entries carry. |
| `target_zone` | `target_zone` | **missing** | Present but always `null`; no target resolution. |
| `target_position` | `target_position` | **missing** | Present but always `null`. |
| `persistent_state:{}` | `persistent_state` (`state_schema.md` §3) | **missing** | Empty on 100% of steps. No deck, stake, `tracked_deck_cards`, hand levels, vouchers, or blind status. |
| `action_taken` | `action` / `source_action` | **partial** | Carries only the coarse base label (`PlayHand`, `UseConsumable`, ...); the canonical zoned `action` (`Base_Zone_i`, `SWAP_i_j`), the typed `source_action`/`source_action_subtype`, and `target_action_id` are all missing. |
| `legal_actions` | `action_mask` / legality | **missing** | Field never emitted. |
| `frame_idx` | `frame_idx` / traceability | **missing** | No frame index, timestamp-to-frame mapping, or video offset in either run. |
| `meta.run_id` | run identity | conformant | Required by the client; matches `session.json`. |
| `meta.game_state_id` | producer diagnostic | non-contract | Roughly the step counter; `request_id` is authoritative. |
| `meta.game_stage_id` | producer diagnostic | non-contract | `G.STAGE`; constant `2` (RUN) in both runs. |
| `meta.game_state` | producer diagnostic | missing in win run | Raw `G.STATE`; absent from the win run, present in the loss run. Not a storage field. |
| `meta.pack_kind` / `meta.pack_key` | producer diagnostic | non-contract | Not a storage field; stale/ungated in the loss run (§4.4). |
| `meta.sent_at_real_time` | alignment timestamp | **partial** | Wall-clock seconds, not frame-accurate; no offset artifact. |
| `meta.producer`, `meta.smoke_subset`, `meta.runtime` | provenance | conformant | Good provenance; `smoke_subset:true` marks this as a smoke run. |
| `meta.page` | duplicate of `page_name` | redundant | Carries the same value. |
| `_recorded_action` (client) | client-added | conformant | Equals `action_taken` on every step. |

### 5.2 Missing target fields (absent everywhere)

`step_id`, `frame_idx`, `source_event_index`, `micro_index`, the canonical
`action` label, `source_action`/`source_action_subtype` (the coarse base is
only carried by `action_taken`), `swap_pair`, `selected_object`,
`action_mask`/`legal_actions`, `target_action_id`, and the entire
`persistent_state` structure. `selected_object` cannot be populated without
`target_zone`/`target_position`, which are always null.

### 5.3 Conformant fields

Per-run identity/alignment (`run_id`, `request_id` uniqueness, step/outcome
counts), `page_name` presence, consistent `objects`/`pending_cards` keys for
the zones it does emit, card `class_id`/rank/suit fields for playing cards,
runtime provenance, and the client's `record/1.0.0` session wrapper.

## 6. Phase 0 Oracle-Gate Verdict

Roadmap Phase 0 gate bullet: "The Lua oracle emits aligned `(state, action,
outcome)` for at least one run." Ground-truth contract invariant: "Video-to-
engine alignment is explicit and auditable (timestamps, offsets)."

**Finding: the merged-revision run proves transport liveness and auditable
video-to-engine alignment, but the full Phase 0 gate remains open.**
Reasoning, stated so the user can override:

- Met: the merged-revision loss run persists one aligned record per
  decision step, with a single `run_id`, unique `request_id`s, `action_taken`
  on every step, a real `loss` outcome, a persisted recording marker, and
  positive frame mappings from `planning/align_oracle_video.py`. This satisfies
  the aligned-run existence claim.
- Met: the run covers blind select, in-blind play, cash-out, shop, and a
  booster pack. All four canonical offering zones are present and positioned.
- Not sufficient for downstream metric acceptance: the coarse base-only action
  labels, empty `persistent_state`, and incomplete object attributes cannot
  support the Phase 7 (persistent reduction, mask agreement) or Phase 8 (event
  inference) metrics the oracle is meant to score.

**Exact gaps blocking the full gate as written:** (1) no canonical zoned action
label or `target_action_id`; (2) `persistent_state` remains empty despite raw
fields; (3) object modifiers/editions/stickers remain incomplete; (4) the
evaluation set, annotation protocol, and numeric thresholds remain open.

The coarse action labels and empty `persistent_state` were known at handoff and
are by design for a smoke test. The recommendation is to record the oracle as
"transport validated; contract conformance pending" rather than closing the
gate, and to treat gaps (3)-(6) as the next producer iteration, gated on a
decision about producer ownership (see §7, P3).

## 7. Proposals (follow-up issues)

Follow-up issues are tracked as sub-issues of #10: P3 = #14 (decision, blocking),
P1 = #15, P2 = #13, P4 = #12, P5 = #16, P6 = #11.

**P1 — Fix step identity and alignment before any aggregation.** Key steps by
`(run_id, request_id)` (or emit a global `step_id`) and add `frame_idx` plus a
video-offset field. Recommend adding a `schema_version` that identifies the
producer/oracle transport revision, distinct from the granularized `3.0.0`.
*Recommendation: adopt; it is required by the dataset traceability invariant.*

**P2 — Add canonical zoned action labels and target resolution.** Emit
`target_zone`/`target_position` from the game's selected/offering zones and a
canonical `action` label (`Base_Zone_i`, `SWAP_i_j`) alongside the coarse
`action_taken`, with `source_kind`. *Recommendation: adopt; defer full action
space until the persistent contract is decided.*

**P3 — Decide whether the oracle owns `persistent_state` or the reducer does.**
D009 adopts the published persistent-state/action/mask contract; the producer
currently leaves `persistent_state` as an empty object. Options: (a) producer
emits full persistent state (oracle-side reducer), (b) producer emits only
observations and the pipeline reducer reproduces persistent state, with the
oracle as validation channel, (c) producer emits raw game fields sufficient to
recompute the reducer state. *Recommendation: (c) — keep the oracle as a
validation channel and add the raw fields the reducer needs (deck/stake,
jokers/consumables with canonical IDs, hand levels, vouchers, blind status),
avoiding two divergent reducers.* This is a durable decision (D009/Q04) and
must be user-approved before implementation.

**P4 — Map inventory `center_key` to canonical class IDs.** Emit the vendored
class-map `class_id` for jokers/tarots/planets/spectrals/vouchers (and
modifiers/editions/seals) so the oracle matches the ontology contract.
*Recommendation: adopt; without it the oracle cannot score detection/OCR
classes.*

**P5 — Snapshot shop and pack offering zones.** Add `ShopOfferings`,
`VoucherShopOfferings`, `TopShelfShopOfferings`, `PackOfferings`, and
`PackShopOfferings` to `objects`. *Recommendation: adopt; required for shop and
pack event/mask validation.*

*Applied by Issue #16 (2026-09-30): the producer now emits the four canonical
live/2.0 zones — `TopShelfShopOfferings`, `VoucherShopOfferings`,
`PackShopOfferings`, `PackOfferings`. Bare `ShopOfferings` is a deprecated
offline-extractor alias with no distinct live CardArea and is intentionally not
emitted; the user approved this substitution (Issue #16 comment).*

**P6 — Capture at least one run pinned to the merged revision and record the
video offset.** The two persisted runs miss the reviewed revision. This is a
manual game-capture task, not a code change. *Recommendation: required before
any Phase 0 gate closure.*

These proposals were unapplied when this review was written. Follow-up work is
tracked under Issue #10's sub-issues. P5 was applied by Issue #16 (PR #28) with
the four canonical zones noted above. P3 is a durable contract decision that
needs user input; the remaining producer-scope changes follow from that
decision.

## 8. Residual Uncertainty

- The win run is from a pre-fix revision; any claim about pack-page handling
  from that run is superseded by the loss run and the synthetic harness.
- The loss run's `pack_kind`/`pack_key` diagnostics are unreliable outside its
  999 steps (§4.4); treat them as evidence only on those steps.
- `page_name` is producer-generated ground truth, not an independently
  annotated label; page-classification accuracy cannot be scored from it.
- No `In_TarotSpectral_Pack` page or voucher-redeem state appears in either
  live run; those remain synthetically verified only.
- The evaluation set, annotation protocol, and Phase 1-10 thresholds (Q03) are
  unchanged by this review and remain open.

## 9. References

- Contracts: `planning/components/ground-truth.md`,
  `planning/components/state-composition.md`,
  `planning/components/state-reduction.md`, `planning/components/dataset.md`.
- Decisions: D009 (adopted downstream contract), D016 (public repo / external
  evidence), D001, D014; open questions Q03, Q04.
- Producer: `ground_truth/balatro_mod/main.lua`, `ground_truth/file_ipc_bridge.py`,
  `planning/BRIDGE_SPIKE.md`.
- Adopted schemas: `legacy/vendor/balatro-policy-transformer/{granularization_schema,state_schema,action_space_schema,mask_schema}.md`.
- Tool: `planning/audit_oracle_runs.py`.
