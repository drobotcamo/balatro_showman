# Oracle vs Reducer Ownership of Persistent State (Issue #14)

Status: decided — option (c), recorded as D021 after explicit user choice
(2026-09-30). This note is the source for the decision; D021 is the durable
entry.
Work item: Issue #14. Parent: Issue #10. Grandparent: Issue #6.
Related: `planning/ORACLE_DATA_REVIEW.md` §7 (P3), D009 (adopt the published
downstream contract), D020 (the reducer owns the action-space index), Q04
(which visible state is unrecoverable from video alone), and component
contracts `planning/components/ground-truth.md`,
`planning/components/state-reduction.md`, `planning/components/events.md`.

## 1. Question

D009 adopts the published downstream contract: canonical `persistent_state`
(`state_schema.md` §3), per-step `[OBSERVATION]` fields (§6), the action-space
index (`action_space_schema.md`), and legality masks (`mask_schema.md`). The Lua
producer today emits `state` scalars, `objects[]`, `pending_cards[]`, and a
coarse `action_taken`, with `persistent_state` empty on 100% of steps
(`ORACLE_DATA_REVIEW.md` §5.1, §6 gap 4). The decision: **where is canonical
persistent state produced, and where does the producer's schema/version
boundary sit?**

Constraints that hold regardless of the chosen option:

- Exactly one canonical reducer defines `persistent_state` and the action-space
  index / masks (`planning/components/state-reduction.md`; D020).
- The oracle is a separate validation channel, never merged into observed state
  (`planning/components/ground-truth.md` invariant).
- Phase 7 acceptance ("the reducer reproduces reference persistent state from
  ground-truth runs"; "masks agree with oracle legal actions") needs a reference
  that is engine truth, not a second implementation of the same reducer.

The canonical shape is not a clean engine read: it contains video-reducibility
artifacts such as the `tracked_deck_cards` FIFO capped at 75, the closest-match
consumable rule, Aura's collapsed `e_foil` placeholder, and unmodeled
random/hand-wide spectrals (`state_schema.md` §5.5, §7). Any ownership choice
must say what happens to those.

## 2. Options And Tradeoffs

### (a) Producer emits full persistent state (oracle-side reducer)

The oracle computes canonical `persistent_state` in Lua, either by shaping
engine state or by implementing the reducer, and emits it directly.

- Pros: the reference arrives already in the target schema, so the pipeline
  reducer's output can be diffed field-by-field with no Python re-reduction; the
  oracle is self-contained for Phase 7.
- Cons: the canonical shape includes video-only reduction artifacts (FIFO cap,
  closest-match, `e_foil` placeholder), so Lua must re-express the published
  reducer's semantics — a second implementation that can drift from the Python
  reducer. A mapper bug then becomes indistinguishable from a reducer bug, and
  mask validation would consume a state shaped by our own code rather than the
  engine's. Largest Lua surface of the three options.

### (b) Producer emits observations only; pipeline reducer reproduces persistent state

The producer keeps (roughly) today's outputs; the pipeline reducer is the only
producer of `persistent_state`; the oracle supplies outcomes/actions but no
persistent-state reference.

- Pros: least producer work; one reducer.
- Cons: there is no independent reference for persistent state, so Phase 7's
  "reproduces reference persistent state from ground-truth runs" cannot be
  scored and mask agreement has nothing to agree with. This defers the gate
  rather than satisfying it; it is not a viable final boundary.

### (c) Producer emits the raw engine fields the reducer needs; oracle stays a validation channel

The oracle emits engine-truth raw fields sufficient to recompute the reducer
state (deck class ID and flags, stake class ID, tracked deck cards and their
modifier/edition/seal/stickers, hand levels/played counts, vouchers redeemed,
bosses used, blind statuses and counters, etc.) plus the engine's own legal
actions/mask basis. The pipeline reducer (Phase 7) maps observations plus those
raw fields into canonical `persistent_state`; the oracle does not reshape the
canonical output.

- Pros: one canonical reducer (D020); the comparison reference is engine truth
  or engine legality, not a peer reducer; raw fields are low-complexity reads
  from `G`; engine legal actions give a genuinely independent Phase 7 mask
  oracle. Aligns with the ground-truth invariant and avoids two divergent
  reducers.
- Cons: the oracle does not emit the canonical shape directly, so validation
  needs a documented, tested mapping from raw fields to `state_schema.md` §3;
  the raw-field transport needs its own version boundary. The gap between
  engine truth and video-recoverable state must be stated explicitly (this is
  the Q04 output).

## 3. Recommendation

**(c).** Keep the oracle as an independent validation channel that emits the
raw engine fields and true legal actions, and keep a single Python reducer as
the only producer of canonical `persistent_state` (D020). This satisfies the
Phase 7 acceptance criteria without a second reducer: "reproduces reference
persistent state" compares the pipeline reducer against engine-truth raw fields
and their documented mapping; "masks agree with oracle legal actions" compares
against engine legality. Unrecoverable-from-video fields become an explicit,
measured gap (Q04) rather than being hidden by an oracle that already emits the
canonical shape.

(a) is rejected primarily because it creates a second reducer whose bugs are
inseparable from the pipeline's, and because it makes the mask oracle depend on
our own state-shaping. (b) is rejected because it leaves Phase 7 unscorable.

This matches the recommendation recorded in `ORACLE_DATA_REVIEW.md` §7 P3;
this note adds the schema-boundary detail.

**Outcome (2026-09-30):** the user selected **(c)**. Recorded as D021 in
`planning/DECISIONS.md`. Producer follow-up for the raw-field schema is tracked
separately; #13 depends on this boundary and #12/#16 are annotated as
independent.

## 4. Consequences If (c) Is Chosen

- Producer gains a raw persistent-field schema with a version label distinct
  from the granularized `3.0.0` (this is also P1's transport-version point).
- The oracle additionally emits an engine-truth legality/mask basis for Phase 7
  mask agreement.
- The pipeline reducer defines and documents the raw-field -> `state_schema.md`
  §3 mapping, including how video-only artifacts (FIFO cap, closest-match,
  Aura placeholder, unmodeled spectrals) are handled.
- Q04 is answered by diffing engine-truth raw fields against their
  video-recoverable projections; the diff is recorded as the oracle boundary.

## 5. Effect On Producer Follow-Ups

- `[ground-truth] Producer: canonical action labels and target resolution`
  (#13): depends on the chosen boundary (the mask/label basis); annotate with
  the decision. Its target resolution is unaffected.
- `[ground-truth] Producer: canonical object IDs and card attributes` (#12):
  independent of the decision, but the chosen boundary fixes who owns the raw
  class-ID/attribute fields the reducer and oracle both consume.
- `[ground-truth] Producer: capture shop and pack offering zones` (#16):
  independent; offering zones are observations and mask inputs, consumed the
  same way under any option.

## 6. Decision Requested

1. Choose (a), (b), or (c), or record an explicit deferral with rationale.
2. If (c): confirm that (i) the producer emits a versioned raw persistent-field
   schema rather than canonical `persistent_state`, and (ii) the oracle also
   emits an engine-truth legal-action/mask basis for Phase 7.

Until the user records a choice, no `DECISIONS.md` entry exists for this
boundary and no producer implementation may assume one.
