# Run Mechanics Design v0.1

Status: design direction and v0.1 initial interface/examples approved by the owner
on 2026-10-04. Later staged examples and applicable exact trigger-order trace
remain open.

Issue #122 defines the interface between video evidence, reconstructed run state,
derived mechanics effects, engine-reference data, and downstream queries. This is
a storage-neutral design. It does not implement a reducer or simulate the game.
The owner approved the initial interface and Dagger/scoring/reset examples on
2026-10-04. The structural schema is `planning/schemas/run_mechanics_v0_1.schema.json`;
the executable positive fixture is `planning/examples/mechanics_v0_1_dagger_positive.json`.
These do not imply source-order completeness, game-rule validation, or held-out
evaluation approval.

## Scope and ownership

The design covers playing cards, Jokers, tarot, planets, spectrals, vouchers,
enhancements, editions, seals, stickers, boss blinds, and decks. It extends the
existing class map without renumbering it. Ontology owns definitions and class
identity; tracking owns visual observation identities; events own observed action
inference; state reduction owns reconstructed persistent state; this design owns
mechanics-level derived effects and their relation to those interfaces.

The Lua oracle is a separate engine-reference channel. It may validate a derived
claim but is never silently promoted to video observation. This design adds no
production reducer or full game simulation. Storage selection follows semantic
approval; a graph database is optional, not a requirement.

## Approved design decisions

### Definitions, instances, state, and effects

Keep four concerns distinct:

1. **Definition** — stable class/catalog identity and versioned mechanic rules
   for an asset such as Dagger or Hermit.
2. **Run instance** — a particular acquired object with a run-scoped identity
   independent of its visual track ID.
3. **Derived state** — reconstructed properties of instances and the run at a
   point or interval in the run.
4. **Derived effect** — a trigger/use/contribution occurrence with context,
   source and target, evidence, rule revision, and result.

Visual track IDs remain observation identities. They are not game-instance IDs
without evidence-backed association. Preserve unknown or ambiguous association
rather than joining by guess.

### Lifecycle and property history

Represent acquisition, copy/creation, movement, replacement/removal, and resume
continuity explicitly. Track property changes with validity intervals and
provenance. Replacement does not erase the old instance or its history. Copying
properties onto an existing target (Death is a consultation example) changes
target attributes without changing target identity or history. Model lifecycles
according to object family: consumable use, voucher run effects, hand-level
changes, blind context, deck rules, card/Joker lifetime, and attached attributes
are not interchangeable.

### Effects and contributions

Use a shared effect vocabulary for trigger/context, condition, dependencies,
ordering, source, target, result, evidence, status, and rule revision. Permit
reusable primitives and custom handlers; do not require one implementation class
per Joker before validating the abstraction.

Persistent mutations (for example, Dagger's mutable Mult) are distinct from
scoring contributions (chips, Mult, and XMult applied in scoring). Also retain
money contributions, atomic multiplicity, all relevant participating cards, and
interval-wide net deltas as distinct queryable information. A use/trigger record
must not imply successful contribution when its condition did not produce one.

### Temporal model and exact trigger order

Observed STEP actions anchor intervals; they are not a complete engine trigger
stream. Derived contexts include scoring, retriggers, destruction, consumable
use, round completion, and other relevant engine moments. Preserve observed
action order separately from internal engine-trigger order.

For this design, **trigger ordering is intended to be exact, not an approximation**.
Establish it by inspecting the applicable game/mod source code and encode the
source revision and ordering evidence. The project owner will verify the traced
ordering; this investigation is expected to be arduous. Do not freeze or claim an
ordering based only on observed STEP boundaries, runtime intuition, or a partial
source inspection. If the relevant code path or version cannot be established,
mark that ordering unsupported/unknown and block exact downstream claims. No
future observation may appear in pre-action model-visible state.

#### Dagger source trace (owner verification pending)

I inspected both the embedded vanilla Lua source and the generated local
Steamodded/Lovely runtime dump. They differ in the timing of Dagger's mutation,
so neither can stand in for the exact source stack used by a recording without
owner confirmation.

**Embedded game source.** The installed `Balatro.exe` SHA-256 is
`0d75fe164accf3312734d4b37ac98788dd15f0b8e4f9bb8b7f90c4e59de93f47`; its
embedded `card.lua`, `functions/state_events.lua`, and
`functions/common_events.lua` hashes are respectively
`5073D834E08119DA9516F1795A8C3D93110669AEB409C29AD1B308E0EB0BE453`,
`6C86AEFB42D0323D737F87AAA84F53E42B755E72CD0BFD163B7D9CCA5C0A99A9`, and
`522EA0810101DE1004685E13E7ED05A750B4E115E5231DCA2CBC97AEB8C3E5FC`.

1. `functions/state_events.lua:333-337` sets the blind, then iterates
   `G.jokers.cards` in array order and calls each Joker's
   `calculate_joker({setting_blind=true,...})` before continuing.
2. `card.lua:2491` enters the setting-blind branch. At `:2561-2577`, Dagger
   finds its index and only schedules a sacrifice when `G.jokers.cards[my_pos+1]`
   exists, Dagger is not being sliced, and the immediate right Joker is neither
   eternal nor already being sliced. It marks that victim `getting_sliced`, then
   queues an event callback. Inside that callback, `ability.mult` is increased
   by `sliced_card.sell_cost * 2` and the victim is dissolved. Thus the Mult
   mutation is pending during the immediate Joker-array loop and resolves later.
3. If there is no destructible Joker immediately to Dagger's right, the guard is
   false: no victim is marked, no destruction event is queued, and no Mult is
   gained. This includes no adjacent Joker and an ineligible adjacent Joker. The
   user confirms the no-destructible-target outcome is visually observed and
   known.

**Generated modded dump.** The local generated dump files have hashes
`card.lua` `2BA1276C5850EA966733D4144602D866DDDBB9CBFFF1F588F409114D79584F54`,
`functions/common_events.lua` `8AE65634B2ABCDF0BC02FE1289CFFF57CACCAE47421BB69917BA8C84272E9968`,
`functions/state_events.lua` `1E04EAAC3BF610F97D6C749F7D3762883B64A414DC5A6E14CE52BBC8FAE682A6`,
and `SMODS/_/src/utils.lua` `AAF8C4CCCCBFC5AECDF6A828AFB4024E1E903ACDFB691A7FF7F9214CE6C95430`.
There, `state_events.lua:283` calls `SMODS.calculate_context`; `utils.lua:2192-2212`
and `:1813-1868` iterate Joker areas/cards in array order; `common_events.lua:777-800`
dispatches `calculate_joker`. Its Dagger branch at `card.lua:2953-2981` queues
the victim dissolve, then calls `SMODS.scale_card` outside that callback. This
differs from the embedded vanilla source, which mutates Mult inside the queued
callback.

The hashes identify local artifacts, not a pinned upstream Steamodded/Lovely
patch set or the exact mods active in any recording. The owner must decide which
source stack governs the intended run and verify the order-sensitive timing
before setting `requires_exact_order=true`. The fixture keeps it false until
then. Sell value at the trigger must still come from visible evidence or a
reproducible derivation under the applicable pricing rules.

#### Installed capture stack trace (2026-10-04; owner verification pending)

The latest startup log is
`C:\Users\camgr\AppData\Roaming\Balatro\Mods\lovely\log\lovely-2026.10.04-16.52.58.log`.
It records Balatro `1.0.1o-FULL`, Lovely `0.10.0`, Steamodded runtime
`26.926.0~dev-a`, and Issue #123 producer build. The Steamodded manifest says
`26.829.0`; `version.lua` gives the loaded runtime identification. The installed
Balatro executable SHA-256 is
`0d75fe164accf3312734d4b37ac98788dd15f0b8e4f9bb8b7f90c4e59de93f47`.

The unpatched files in `lovely/game-dump/` match the executable's embedded Lua
hashes. The active post-Lovely files are in `lovely/dump/` (not
`lovely/game-dump/`) and have these SHA-256 values:

| File | SHA-256 |
| --- | --- |
| `card.lua` | `2BA1276C5850EA966733D4144602D866DDDBB9CBFFF1F588F409114D79584F54` |
| `functions/state_events.lua` | `1E04EAAC3BF610F97D6C749F7D3762883B64A414DC5A6E14CE52BBC8FAE682A6` |
| `functions/common_events.lua` | `8AE65634B2ABCDF0BC02FE1289CFFF57CACCAE47421BB69917BA8C84272E9968` |
| `engine/event.lua` | `0A6A4FAC8436D502DDC654C40BF4579A86AC18121A853650C34F750DFF772D1F` |
| `game.lua` | `9297C27F4AB66E6795AA30CB84E28A10A842A924182B85CF580E1FEDD5E0F8A1` |
| `SMODS/_/src/utils.lua` | `AAF8C4CCCCBFC5AECDF6A828AFB4024E1E903ACDFB691A7FF7F9214CE6C95430` |
| `smods-main/lovely/scaling.toml` | `ADE9F4A7F8B87EA64FE094445354A89710762950E8D9916D3354F779D8BA7666` |

For this stack, `lovely/dump/functions/state_events.lua:241-243` queues the
blocking `new_round` event. Its callback sets the blind and calls
`SMODS.calculate_context({setting_blind=true, ...})` at `:281-284`. The generated
`lovely/dump/card.lua:2953-2981` applies the Dagger eligibility condition: the
immediate right neighbor must exist, must not be eternal according to
`SMODS.is_eternal`, and must not already be getting sliced. It marks the victim,
queues the dissolve event, then calls `SMODS.scale_card` outside that event
callback. The active `smods-main/lovely/scaling.toml` removes vanilla's
`self.ability.mult += sell_cost * 2` line and inserts this `SMODS.scale_card`
call. In `SMODS/_/src/utils.lua:3370-3411`,
`SMODS.scale_card` computes the scalar context and applies the scale before it
returns; `SMODS.additive_scaling` updates the referenced ability value
synchronously. Thus the post-Lovely stack updates Dagger Mult during the
`setting_blind` calculation, while victim dissolution remains queued.

The active event system still matters for the capture boundary. `Event:init`
defaults to blocking events (`engine/event.lua:5-23`), `add_event` appends to
the queue (`:119-129`), and the queue update defers subsequent blocking events
after a blocking event runs (`:171-193`). `Game:update` calls the event manager
at `game.lua:2644`. The producer wraps `Game.update` and samples after the
original update returns; it therefore reads the synchronous Mult mutation after
the setting-blind context, without waiting for a player action. This timing is
different from embedded vanilla, where Mult changes in the queued Dagger event.

This source trace is specific to the logged local stack. The owner must verify
both that this runtime/source stack governs the intended behavior and that
Dagger Mult counts as resolved while victim dissolution is still queued. If so,
exact-order support can be approved for this stack only; other versions or
Lovely patch sets need their own trace. The manifest/runtime version discrepancy
and Lovely patch warnings remain part of its provenance. No Dagger run was made
during this source inspection.

### Evidence, status, and recomputation

Every claim/result carries one status: `observed`, `inferred`, `unknown`,
`ambiguous`, or `unsupported`. Retain source step identities, evidence
references, confidence basis, and enough input/rule-revision provenance for
deterministic recomputation. Raw observations are append-only; derived results
are recomputable and may be superseded. Engine-reference values remain a
separate channel with explicit source identity.

For every mechanic input, record whether it is visually observable,
tooltip-only, historically inferable, or hidden/not available in this particular
recording. Visibility in principle is not proof that a recording observed it.
Unknowns are expected and supported; an exact query must abstain when its required
inputs are unavailable or ambiguous.

Sell value is theoretically knowable and should be represented as a derivable
value when inputs/rules are established. Its derivation may depend on base price,
edition, stickers (including Egg/Gift Card-related effects where applicable),
discounts/vouchers, rental cost, and other pricing rules. If a required value or
rule is not evidenced for the run, retain unknown rather than substituting an
estimate as fact. Whether the current capture producer must add explicit sell
value and pricing inputs is a follow-up contract decision, not approved by this
design direction alone.

Some mechanics are completely non-visual in ordinary footage—for example, which
rank Idol selected. Such results may remain unknown unless independently
inferable from evidence; the pipeline must not invent an observation.

### Lineage and attribution

Represent direct effect attribution separately from upstream causal lineage.
Queries name their attribution policy and may expose overlapping direct and
causal views. Preserve attribute provenance through replacement/copying; give
occurrences deterministic identities for deduplication; report unknown coverage
and explicit ownership/round denominators in aggregates. Lineage is not proof of
counterfactual benefit.

### Failure diagnostics

Structured failures identify the rule/Joker/instance where known, action
interval, missing dependency, expected versus observed values, evidence
references, downstream invalidation, and actionable reason. Provide a readable
diagnostic alongside the structured record. Missing or ambiguous dependencies
must not silently yield precise output.

## Approved initial interface v0.1

The following v0.1 entities and field boundaries are approved for the initial
design. JSON Schema defines their structural envelope; the runnable validator
checks cross-record references and evidence separation. It does not assert that
an inferred result is mechanically true.

- `Definition`: asset/class key, family, definition version, rule set reference.
- `RunInstance`: run identity, instance identity, definition reference,
  lifecycle/provenance, and confidence/status.
- `StateFact`: subject/property/value, validity interval, status, evidence,
  confidence basis, and derivation revision.
- `EffectOccurrence`: deterministic occurrence key, trigger context, exact
  ordering reference, condition/dependencies, source/targets, effect kind and
  value, evidence/status, and rule revision.
- `Participation`: occurrence, participating object, role, and evidence/status,
  including participants that did not contribute a successful effect.
- `Lineage`: upstream/downstream occurrence or state-fact references, causal
  relation, and attribution policy.
- `Diagnostic`: failure identity, interval, missing dependency, expected/observed
  values, evidence, invalidated outputs, and readable reason.

References must resolve within the run bundle. Observation/derived records may
not consume oracle-reference evidence. Exact-order records require source
revision and source evidence; ambiguous ordering is rejected when exact order is
required. Rule revisions are explicit inputs for recomputation.

## Input sufficiency and query contract

Before promising an exact answer, name the query and audit each required input
as visually observed, tooltip-only, historically inferable, or hidden/unavailable
in the recording. Return value, status, coverage, evidence, and uncertainty. A
query over unsupported/unknown dependencies returns a structured diagnostic and
readable reason rather than silently omitting the gap.

At minimum, named queries should address: instance/property state at a step;
effects and participants in an action interval; direct versus upstream
attribution; contribution totals without double-counting; and the evidence basis
and unknown coverage for each result. Exact query semantics are pending worked
example review.

## Initial review slice: Dagger boundary

This first slice covers Dagger's positive growth, zero growth, and missing
dependency cases, plus one scoring effect and one reset example. The owner
approved these example semantics and input boundaries on 2026-10-04. Values below
are synthetic fixture values, not claims about a captured run.

### Actual-capture input sufficiency (evidence-limited)

The existing Dagger investigation examined segments `1898258342000-5384` and
`2317688862100-2663`. The source hashes matched their export manifest. The
serialized snapshots omit mutable Dagger Mult, actual victim sell value, and
game-instance identity. In the latter segment, steps `:174` and `:175` show a
round transition from 19 to 20, one Joker disappearing (Joker count 8 to 7),
and a neighboring-card change consistent with a Dagger sacrifice candidate.
Extracted video frames visibly show Dagger Mult +62 and +70 at 0 and 2 seconds.
The manifest marks timestamp correspondence unverified, so these frames do not
establish exact step alignment. Inventory deltas support an inference, not exact
numeric causation. This capture therefore demonstrates the required distinction:
visible before/after values may support observed state facts, while a missing
sell value, instance match, or precise interval leaves the attributed growth
inferred/unknown. No raw video or external debug export is copied into the
repository.

### Dagger positive growth (illustrative)

**Inputs:** instance `inst-dagger` with `ability.mult=6`; adjacent victim
`inst-victim` with evidenced `sell_cost=4`; destruction context; pre/post source
steps; evidence for both values, victim destruction, and resulting Dagger value;
rule revision `example-rule-dagger-scale-2`. For this synthetic example the
rule input states multiplier 2: increment=`4 x 2 = 8`; resulting Mult=`6 + 8 =
14`. Emit one +8 Mult persistent-mutation contribution and a post-trigger state
fact. The fixture's order is not asserted exact; source-order verification
remains open.

### Dagger zero growth: no destructible Joker to the right (illustrative)

**Inputs:** Dagger Mult=6; no destructible Joker is immediately to its right
(the fixture uses an empty right-hand slot); the ordered Joker row and pre/post
frames visibly show no target, no destruction, and unchanged Dagger Mult.
Expected output: no destruction target, no Dagger-growth effect, no contribution,
and post-trigger Dagger Mult remains 6. This is a known, visually confirmed
outcome, not an unknown dependency. The same no-effect outcome applies when a
right-hand Joker exists but is not destructible (for example, eternal or already
being destroyed); eligibility conditions follow the pinned source revision.

### Dagger missing dependency (illustrative)

**Inputs:** Dagger Mult=6 and a confirmed destructible right-hand target is
destroyed, but the victim's sell value is not visually evidenced or otherwise
derivable. Expected output: status/condition `unknown`, missing sell-value
dependency, no numeric contribution, and a diagnostic pointing to the affected
growth query. Do not substitute an estimate or later snapshot. This differs from
no right-hand Joker, where the known outcome is no destruction and no growth.

### Scoring contribution (illustrative)

Use base Joker with a scored hand. Inputs: one instance, definition Mult=+4,
one scoring occurrence, and evidence that its condition applies. Expected output:
one +4 Mult contribution with deterministic occurrence key; record the Joker as
contributor and scored cards as participants, not contributors; emit no
persistent-state mutation. Report interval net delta separately. This does not
assert order among multiple Jokers.

### Reset boundary (illustrative)

Use round completion with pre-state `hands_remaining=0`, `round_status=current`,
round-scoped temporary counters, and run-persistent `voucher_redeemed=true`.
Post-state evidence shows next-round initial counters and continued voucher.
Close old round-scoped facts at the boundary, open the next round's facts, and
retain the voucher fact. Do not infer unseen reset values. This defines validity
semantics, not the complete reset field set or callback ordering.

### Runnable review checks

The initial runnable checker validates the approved v0.1 envelope independently
of a production reducer. It must reject malformed references,
observed/reference-channel mixing, forbidden answer-key use by reconstruction,
and ambiguous timing where exact ordering is required. It also rejects unresolved
evidence IDs, malformed known-ID lists and missing/invalid exact-order evidence.
Failures identify affected values/dependencies. The executable command validates
positive-growth, zero-growth, missing-dependency, scoring, and reset synthetic
fixtures, plus malformed cross-references, actual document-level answer-key
references, reference-channel mixing, and ambiguous exact timing. These fixtures
exercise interface semantics, not game behavior.

## Staged examples pending consultation

The owner approved including all examples in the design, but explicitly requested
consultation on their concrete inputs, effects, state changes, and query outputs.
These are staged extensions, not prerequisites for the initial Dagger boundary:

1. **Unknown dependency:** a mechanic such as Idol's selected rank when the
   selection is not visually available, including abstention and diagnostics.
2. **Hermit and Mail-In Rebate:** trigger/use conditions, money contribution,
   multiplicity/participation, reset boundary, and direct/upstream queries.
3. **Certificate → Death → later Gold Seal earnings:** Certificate-created
   identity/property history, Death copying onto the existing target, later
   Gold Seal earnings, provenance and attribution policies.
4. **Missing evidence and ambiguous identity:** show unsupported joins, unknown
   coverage, and no fabricated precision.

For each, consult the owner on exact required inputs, observable/inferable/
reference boundaries, records, named query results, property history, and
no-double-counting behavior before freezing schema examples. Historical evidence
in `planning/LEARNINGS.md` motivates Dagger and sell-value capture but does not
itself settle the example.

## Evaluation protocol boundary

Propose a frozen, versioned evaluation protocol with criteria, metrics,
thresholds, minimum support, uncertainty rules, and acceptance authority. Obtain
owner approval before held-out measurements. The design and its examples are not
evidence of reconstruction quality; no threshold is approved here.

## Acceptance and next design gate

Remaining gates after approval of the initial v0.1 interface:

- The runnable initial fixtures exercise all five approved cases. Replace or
  extend synthetic evidence with recording-specific observations only under a
  separately approved evaluation protocol.
- Inspect the applicable game/mod source to establish exact trigger order and
  present that trace for owner verification. This is arduous work and is not
  complete in this design draft.
- Before #129, review Hermit and Mail-In Rebate uses, participation, multiplicity,
  direct contributions, and net deltas.
- Before #130, review Certificate creation, Death copying onto an existing target,
  and later Gold Seal provenance/validity; add deduplication, overlapping upstream
  views, and ambiguous-identity checks before consumers claim support.
- Review remaining unknown-dependency, missing-evidence, and ambiguous-identity
  examples before claiming those mechanics/query families supported.
- Audit input sufficiency and sell-value derivation, including modifiers and
  pricing effects, without treating theoretical knowability as observed evidence.
- Add later-stage checks for timing conflicts and contribution double-counting.
- Freeze the evaluation protocol with owner approval before held-out measurement.

The initial v0.1 schema and example boundary is approved. Later staged examples,
exact order-sensitive behavior, and evaluation criteria remain gated; this
approval is not a claim that those items are complete.
