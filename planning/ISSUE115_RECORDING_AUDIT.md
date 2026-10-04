# Issue #115: recorder continuity and archive inspection

Inspection date: 2026-10-03. Source archive: `F:\OBS_RECORDINGS`.
Issue: [#115](https://github.com/drobotcamo/balatro_showman/issues/115).
This report records source evidence and descriptive QA. It is not a Phase 0,
held-out coverage, alignment-gate, or reconstruction-quality result.

## Continue defect and regression

The old `Game.start_run` hook allocated an ID and reset numbering for every
invocation. Balatro Continue supplies `args.savetext` to that same method.
The corrected hook preserves its in-process identity, counter, failure count
and terminal flags on Continue. New Run still allocates an identity. A cold
process has no identity to restore; cross-process save identity is outside #115.

`tests/lua_file_ipc_fixture/main.lua` executes the producer under LÖVE with
stubbed game callbacks. It checks cold Continue, New Run, menu nonfinalization,
the recorded Ante 4 / Round 11 / 12,243 chips / two hands / $39 state at
109→110→111, argument/return forwarding, loss and win watermarks, and no
post-terminal resurrection. The Python test feeds the resumed queue to the real
consumer and checks one 111-step session with contiguous IDs and one recording
association. Its marker is a fixture, not an OBS handshake.

Checks: `py -3 -m unittest tests.test_audit_oracle_runs tests.test_balatro_mod
tests.test_file_ipc_bridge`: 55 tests passed, including the Windows LÖVE test
(not skipped). `py -3 planning/check_contracts.py`: `planning contracts OK`.
`git diff --check`: no whitespace errors. Actual save restoration and a fresh
live recording remain necessary for issue acceptance.

## Preserved source group

Report-level logical recording/play group: `issue115-20261003-175628`.
It contains exactly one video and these two immutable source sessions, in order:

| Source run ID | Original step IDs | Steps | Original outcome | Original marker |
| --- | --- | ---: | --- | --- |
| `1898258342000-5384` | `1898258342000-5384:1`–`:109` | 109 | null | `issue81-20261004T005632Z` |
| `2317688862100-2663` | `2317688862100-2663:1`–`:271` | 271 | win | absent |

Source directories are under `F:\OBS_RECORDINGS\oracle_runs_issue79`.
Shared source video: `F:\OBS_RECORDINGS\2026-10-03 17-56-28.mkv`.
User-confirmed continuity is recorded in #115 and #82. This report preserves
both source IDs, hashes and original step IDs; it does not create a synthetic
replacement session or copy a marker into the second source. The group is one
source recording/play for disjointness, never two independent evaluation samples.
It does not declare a new held-out split or grant evaluation acceptance.

SHA-256 observed during inspection:

| File | SHA-256 |
| --- | --- |
| shared MKV | `92b22f573ffa0c64c061ac03ac9e5a179a1757a9410e674394762790532b10d9` |
| `1898258342000-5384/session.json` | `76961d442430667b2d2df84ae17c176ac2888f4da465b6d6501f5f5f1c3798ae` |
| `1898258342000-5384/steps.ndjson` | `703d1ad9ea1b7639859747c7b799fcf379e71fb3576e6d72434c039e9173b707` |
| `2317688862100-2663/session.json` | `0848194126783452f3cea667264eb83fd775eaf17f98e88055e6cb66c4a5b6e5` |
| `2317688862100-2663/steps.ndjson` | `cdea555f4c97c634d33886436627035632657434c8db53e316ef03273b58fb0d` |

`ffprobe` reports 1920×1080, nominal/average 60/1 FPS, 1,340.317 seconds and
1,940,079,025 bytes. Producer marker timestamp: `1895948216800` ns.
Using that marker for the second segment is a diagnostic interpretation backed
by shared-video continuity, not mutation of its source provenance.

The SQLite inspector's `list` command reports only the two development-pilot
segments and the 33-step prospective capture. These latest two sessions are not
in `F:\OBS_RECORDINGS\run_bundle_issue79.sqlite`; no import, migration or
association operation was performed during this inspection.

### Boundary evidence

`1898258342000-5384:109` → `2317688862100-2663:1` is 12.8777339 seconds apart.
All scalar state fields match. The selected cards do not: the first selects
7♠, 6♠, 5♦, 3♥, 3♦; the second selects A♠, A♣, 5♦, 3♥, 3♦.
These are two distinct attempted hands in the same game state, not a duplicated
event to delete. The tracked-deck array order also changes on reload.

Decoded candidate frames at 412.6541974 and 425.5319313 seconds show Big Blind,
target 13,500, score 12,243, two hands, two discards, $39, Ante 4 / Round 11,
the same jokers and Ectoplasm. Card selection differs as above. These direct
observations corroborate continuity; an event-edge measurement within ±3 frames
has not been established by these two decoded snapshots.

## Archive census and anomalies

All 15 `session.json`/`steps.ndjson` pairs found recursively beneath
`F:\OBS_RECORDINGS\oracle_runs*` were parsed and audited: 1,543 steps total.
All declared step counts match line counts. This census covers persisted oracle
data; it is not exhaustive visual inspection of every MKV in the directory.
No source files were repaired or normalized.

| Archive directory | Source ID | Steps | Audit result / notable evidence |
| --- | --- | ---: | --- |
| `oracle_runs` | `122174123700-6680` | 28 | integrity pass; 24 null inventory classes |
| `oracle_runs` | `1790821374-5833` | 39 | legacy missing timestamps/step IDs; no raw fields |
| `oracle_runs` | `184013382700-5967` | 29 | integrity pass; tracked deck grows to 53 |
| `oracle_runs` | `1790805058-5327` | 433 | legacy missing timestamps/step IDs; 38 `Unknown_999` pages |
| `oracle_runs` | `1790807319-8546` | 43 | legacy missing timestamps/step IDs; no unknown pages |
| `oracle_runs` | `53440456500-3281` | 38 | integrity pass; tracked deck 51–52 |
| `oracle_runs_issue79` | `1898258342000-5384` | 109 | only integrity failure: null outcome, fragment |
| `oracle_runs_issue79` | `2317688862100-2663` | 271 | integrity pass; missing marker; resumed segment |
| `oracle_runs_issue79` | `25980339600-7022` | 197 | only integrity failure: null outcome, pilot fragment |
| `oracle_runs_issue79` | `37294333000-7139` | 33 | integrity pass; loss; marker present |
| `oracle_runs_issue79` | `778812964300-9775` | 197 | integrity pass; win; no marker, pilot continuation candidate |
| `oracle_runs_issue81` | `1429448811400-9237` | 29 | integrity pass; loss; marker present |
| `oracle_runs_live3` | `1790821980-7054` | 40 | legacy missing timestamps/step IDs; null outcome |
| `oracle_runs_live3` | `1790822213-2231` | 10 | legacy missing timestamps/step IDs; requests 41–50 |
| `oracle_runs_live3b` | `1790823405-3642` | 47 | legacy missing timestamps/step IDs |

The two dated `oracle_runs` directories have filename prefixes before their
source IDs; directory name and source identity are not interchangeable.

Findings requiring explicit interpretation:

- A second modern fragmentation candidate is `25980339600-7022:197` →
  `778812964300-9775:1`: 13.5992316 seconds apart with equal scalar state,
  Ante 5 / Round 15, zero score, four hands, $40. Selected cards differ.
  Its shared development video is already documented in the pilot report.
  This is not independent confirmation of a Continue event by the user.
- Legacy `1790821980-7054` → `1790822213-2231` has equal boundary state and
  object arrays, with requests 40→41. Missing producer timestamps prevent a
  measured time gap. It is a continuity candidate, not an authorized regrouping.
- Six legacy sessions, 612 steps, lack modern top-level capture timestamps and
  step IDs. The contemporary audit correctly rejects them; missing historical
  fields are not new corruption. It previously crashed comparing `None`
  timestamps. The audit now reports all invalid timestamps without that crash.
- Raw fields are actually populated on every step in the nine timestamped
  sessions. The previous auditor inferred absence from `producer/1.0.0` rather
  than inspecting payloads. It now reports observed coverage without treating
  that schema as the `live/3.0.0` contract or relaxing required fields.
- The latest 380-step play has 79 Buy/Use/Sell callback records with no selected
  object (18 + 61). Sample `:17` and resumed `:193` expose buy-and-use's coarse
  callback instrumentation. A callback record is not necessarily a separate
  human input. Exact target/action claims must retain that uncertainty.
- The latest sources contain 162 inventory-object observations with null class
  IDs (79 + 83), despite available center keys. These are observation counts,
  not 162 unique unknown cards. Preserve the keys; do not invent class IDs.
- `deck_total` reads `G.GAME.starting_deck_size` with a fallback of 52, whereas
  `deck_remaining` counts the current deck area. In the resumed source, 145
  records report remaining greater than total. Sample `:193`–`:196` says 53/52
  while raw tracked cards contain 53 cards. This is a producer field-semantics
  mismatch, not proof of damaged source data; changing it is outside this fix.

## Random five-step segments for human review

Sampling is over original source steps, with no synthetic cross-boundary step
IDs. Sources are sorted by ID, each five-step window stays inside its source,
and three nonoverlapping windows are drawn using Python
`random.Random('issue115-five-step-segments-v1').choice(pool)`, rejecting only
overlap. There are 372 eligible starting windows. Selected zero-based
`(source_index, start)` pairs: `(0,14)`, `(1,192)`, `(0,62)`.
No sample was replaced because of an anomaly. This is descriptive sampling,
not a v2 held-out evaluator. Times below use the shared producer marker.

Snapshots precede the wrapped callback. A step's displayed state is therefore
the input to that action, not its completed result. The next state can expose
the result. First/last candidate frames of all three windows were decoded and
visually inspected; intermediate narratives below are oracle-based and label
unresolved inference. Exact frame-edge alignment remains unverified.

### A. Ante 1 shop: Judgement produces The Tribe

Source `1898258342000-5384:15`–`:19`, approximately 00:49.846–00:56.455.
Ghost Deck, Gold Stake. Initial jokers: Chaos the Clown and polychrome Banner.

1. `:15`, CashOut: You have beaten the Big Blind with 499 against its 450
   requirement. Three hands and two discards remain, with $0 before collection.
   The frame visibly offers a $7 cash-out: $4 blind reward and $3 unused hands.
2. `:16`, BuyShopItem: The shop state now has $7. You select The Fool in top
   shelf position 1; Mars occupies position 0. Telescope and two Standard packs
   remain available. The last used Tarot/Planet is Judgement.
3. `:17`, UseConsumable: A second callback arrives about 45 ms after the buy
   snapshot. The Fool has left the shelf, but dollars still read $7 and the
   resolved target is null. This fits the internal buy-and-use path; it does not
   independently prove a second click or identify its target from this record.
4. `:18`, UseConsumable: Dollars now read $4 and Judgement is in consumable
   slot 0. The last-used field is The Fool. You explicitly use that Judgement.
   Together the neighboring records support buying/using Fool to recreate
   Judgement, then using the recreated Tarot.
5. `:19`, RerollShop: The next state has three jokers: Chaos, polychrome Banner,
   and newly present The Tribe. Judgement is gone and again becomes last-used.
   You initiate the shop's $0 reroll; the frame still shows the old Mars offer,
   Telescope and Standard packs because this is the pre-reroll snapshot.

Review focus: the logical story is three shop decisions around Fool/Judgement,
but the recorder exposes internal callbacks as separate steps. Does that match
your recollection of using Buy & Use here?

### B. Ante 7: Pluto, then entering The Eye

Source `2317688862100-2663:193`–`:197`, approximately 18:08.527–18:18.159.
Initial state: $18, hand-size limit 5, eight jokers / eight slots, Strength held.
The frame shows The Fool's $3 Buy & Use button under the cursor.

1. `:193`, UseConsumable: The recorder has no resolved target. Strength remains
   in inventory and the shelf payload now contains only eternal Credit Card.
   The visually present Fool buy-and-use and the following recreated Pluto
   support a Fool-related callback, but this source step alone cannot name it.
2. `:194`, UseConsumable: You have $15, Strength in slot 0, and Pluto in slot 1.
   The last-used field is The Fool. Pluto in slot 1 is the explicit action
   target, so this step records using the recreated High Card planet.
3. `:195`, LeaveShop: Dollars remain $15; Pluto has disappeared and Strength
   remains. The last-used field is now Pluto. You leave the shop. Current jokers
   are negative Ceremonial Dagger, Mystic Summit, negative eternal Green Joker,
   foil eternal Hanging Chad, polychrome Banner, eternal rental Constellation,
   Mime, and negative perishable Joker. This schema does not serialize their
   dynamic ability values; no exact Constellation gain is asserted from JSON.
4. `:196`, SelectBlind: Big Blind is defeated and The Eye is selected. You
   commit to the Ante 7 boss with $15, four hands, two discards, and hand limit 5.
5. `:197`, PlayHand: Round advances from 20 to 21. The Eye requires 220,000 and
   prohibits repeated hand types. You select 6♥, 6♦, 3♠, 3♥, leaving a gold
   blue-seal K♣ unselected: a Two Pair attempt. The frame shows seven jokers;
   Mystic Summit has disappeared. Its position immediately right of Ceremonial
   Dagger makes Dagger consumption the likely explanation, but no separate
   destruction event is recorded. The frame's Dagger display rises from +70
   before the blind to +74; Constellation changes from ×2.3 to ×2.4 after Pluto.
   Score is still zero and four hands remain because the hand has not resolved
   at this captured action boundary. This window does not supply the result.

Review focus: buying Fool to repeat Pluto, sacrificing Mystic Summit to Dagger,
and deliberately retaining the gold blue-seal king while opening with Two Pair.

### C. Ante 3 shop: Death and Ceremonial Dagger

Source `1898258342000-5384:63`–`:67`, approximately 03:38.187–03:47.447.
After Small Blind: $25, four jokers, no consumables. Jokers are eternal Green
Joker, Chaos the Clown, polychrome Banner, and The Tribe.

1. `:63`, RerollShop: You initiate a $0 reroll. The pre-action shelf holds Earth
   and eternal Mad Joker; Wasteful and a Mega Standard pack remain below.
   Those unchanged lower offers are visible in the decoded frame.
2. `:64`, BuyShopItem: The next shelf contains Death and Ceremonial Dagger.
   Dollars are still $25, consistent with the free reroll. You select Death in
   position 0, while the joker count remains four and consumable count zero.
3. `:65`, BuyShopItem: Death is now in consumable slot 0 and dollars are $22.
   You select Ceremonial Dagger, now position 0 on the shelf. This records a
   distinct second purchase; it is not the same target as the previous step.
4. `:66`, LeaveShop: Dollars are $16 and all five joker slots are occupied.
   Ordering is Green Joker, Chaos, polychrome Banner, Ceremonial Dagger, The
   Tribe. Death remains held. The $6 difference supports the Dagger purchase.
5. `:67`, SelectBlind: You choose the Big Blind, with Small marked defeated and
   The Wall upcoming. The frame shows Big Blind target 4,800 and The Wall
   target 12,800. Dagger is immediately left of The Tribe. That positioning
   makes Tribe a likely next sacrifice, but this window ends before blind
   startup resolves; it does not record Tribe's destruction or Death's use.

Review focus: the intentional Dagger/Tribe ordering and saving Death for later.

## Reproduction and limits

From the repository root, the existing audit accepts one or more source
directories: `py -3 planning/audit_oracle_runs.py <directory> ...`.
The two latest sources return the null-outcome failure on the first fragment
and integrity pass on the second. Null outcome is retained, not repaired.
Use `python -m run_bundle list --db <existing-db>` for bundle inventory.
Video metadata is inspected with `ffprobe`; candidate PNGs use
`ffmpeg -ss <seconds> -i <video> -frames:v 1 <external-output.png>`.

Temporary read-only diagnostic scripts and decoded PNGs are under
`C:\Users\camgr\AppData\Local\Temp\opencode\issue115_*` / `issue115-*.png`;
source videos, sessions and database remain external. The archive includes
other MKVs with no established session relationship. File naming alone was not
used to invent associations. Future acceptance still requires the fixed build
loaded in a restarted game, an authorized exit-to-menu/Continue smoke capture,
neighboring-frame inspection and explicit post-capture association confirmation.
