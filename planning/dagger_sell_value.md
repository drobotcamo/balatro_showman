# Dagger Sell-Value Findings

Issue #124 implementation notes for reconstructing the Dagger victim's sell
value. These findings describe the installed Balatro `1.0.1o-FULL` source and
the locally loaded Lovely/Steamodded runtime. Revalidate source/rules when the
recording's source stack differs.

## Source access

`AGENTS.md` documents that vanilla Lua source is readable from the embedded ZIP
inside `Balatro.exe` using Python `zipfile`. The active patched runtime source is
under `%APPDATA%\Balatro\Mods\lovely\dump\`; inspect this, rather than only
`lovely\game-dump\`, when reasoning about the captured modded stack. Capture
runtime identification and the relevant file hashes with any derived result.

## Vanilla calculation

`card.lua:369-384`, `Card:set_cost`, defines the calculation:

1. `extra_cost` starts at `G.GAME.inflation` (so inflation is an additional
   required interval input even though it was not in the initial modifier list).
   For Joker victims, `base_cost` comes from the Joker center's hard-coded
   `cost` (`card.lua:335`, defaulting to 1 only when absent).
2. Edition surcharges are added: Holographic `+3`, Foil `+2`, Polychrome `+5`,
   Negative `+5` (vanilla source constants). These purchase-cost surcharges
   differ from the edition's scoring effects (`G.P_CENTERS.e_*.config.extra`).
3. Current cost is
   `max(1, floor((base_cost + extra_cost + 0.5) * (100 - discount_percent) / 100))`.
4. Rental sets current cost to `1`.
5. `sell_cost = max(1, floor(current_cost / 2)) + (ability.extra_value or 0)`.

Therefore discount applies to base cost plus applicable edition/inflation
surcharges, not to the final sell value; floor/minimum operations are material.
Couponed shop offers set purchase cost to zero after sell value is assigned and
are not a general sell-value modifier.

Clearance Sale and Liquidation set `G.GAME.discount_percent` to the center's
`extra` value and call `set_cost` for cards (`card.lua:1917-1923`). Vanilla
`game.lua` defines those values as 25 and 50, respectively. They therefore
produce 75% and 50% of pre-discount cost, before floor/minimum operations.

## Persistent Joker value effects

- Egg (`card.lua:2985-2992`) increments its own `ability.extra_value` by its
  configured `ability.extra`, then recalculates cost.
- Gift Card (`card.lua:2993-3010`) increments `ability.extra_value` for every
  Joker and consumable in the respective areas by its configured `ability.extra`,
  then recalculates cost. Ownership, affected-card membership and the configured
  increment must be known at the sacrifice interval.
- These values are additive after the half-cost calculation, so they are not
  multiplied by discounts or halved by the sell formula.

## Edition behavior in the captured modded stack

The active post-Lovely `card.lua` factors generic edition purchase-price
surcharges through each edition center's `extra_cost` (`Card:set_cost_value`,
lines 507-524). The loaded Steamodded edition definitions provide the same
vanilla values: Foil 2, Holographic 3, Polychrome 5, Negative 5
(`smods-main/src/game_object.lua:3693,3726,3759,3792`). The edition scoring
configs (Foil 50 chips, Holographic +10 Mult, Polychrome X1.5) are separate.
`Card:set_sell_value` (lines 526-528) uses the same
`max(1, floor(cost/2)) + extra_value` rule. Custom editions still require their
own active `extra_cost` evidence.

## Rental distinction

Rental sets the card's purchase `cost` to 1 before `set_sell_value`, so it
affects this constructor via that override (the sell value is then at least 1,
plus extra value). Separately, `Card:calculate_rental` charges `G.GAME.rental_rate`
each round; that recurring payment does not itself alter `sell_cost`.

## Dagger dependency and uncertainty

On the approved captured stack, Dagger scales stored Mult by
`2 * victim.sell_cost`; its Mult mutation resolves synchronously while victim
removal remains pending (D039). The constructor may emit a numeric value only
when all inputs and applicable rules are supported for the interval. If a needed
input is missing or contradictory, emit an unknown sell value and unknown Dagger
increment, then propagate Dagger Mult as unknown for subsequent rounds until a
new independent observation re-establishes it. Do not use the isolated engine
reference as a reconstruction input. It remains a separate validation channel.

## Reference cross-check caveat

The owner-confirmed #123 reference contains resolved values for Castle ($3),
Burnt Joker ($4), and Photograph ($4). Vanilla `game.lua` defines their base
costs as 6, 8, and 5. Castle and Burnt Joker match base half-cost with no extra
value; Photograph's $4 does not follow from its base cost alone (base half-cost
is $2). The reference schema does not expose `ability.extra_value` or its
history. Do not backsolve extra value from the reference for reconstruction;
establish the Photograph value from observation or the chronological Egg/Gift
Card effects and other price inputs, or leave it unknown. The #123 record reports
the price as engine-reference data, not visual evidence of its derivation.

## Source inspected

- Embedded vanilla `card.lua`: `Card:set_cost` (369-384), Clearance Sale / Liquidation
  (1917-1923), Dagger scaling (2561-2577), Egg / Gift Card (2985-3010), rental
  charge (2271-2275).
- Active `%APPDATA%\Balatro\Mods\lovely\dump\card.lua`:
  `Card:set_cost` (497-505), `Card:set_cost_value` (507-524),
  `Card:set_sell_value` (526-528), Dagger scaling (2953-2973), Gift Card
  (3399-3416), rental charge (2644-2649).
- Embedded vanilla `game.lua`: Egg base cost 4 / increment 3 (`j_egg`, line
  416), Gift Card base cost 6 / increment 1 (`j_gift`, line 451), Clearance Sale
  discount 25 and Liquidation discount 50 (lines 593, 610), and edition scoring
  configs (Foil 50, Holographic 10, Polychrome 1.5; lines 659-661). Edition
  scoring configs are not sale-cost surcharges.
- Active Steamodded `src/game_object.lua`: edition `extra_cost` fields for Foil,
  Holographic, Polychrome and Negative at lines 3693, 3726, 3759 and 3792.
  Its inspected file SHA-256 is
  `9b201d810eff0d79e22a1b505668f5c9f23255f5ca6e7d687802b81081db1690`.
- The runtime is identified in `planning/RUN_MECHANICS_DESIGN.md` D039. Exact
  active-file hashes must be attached to executable rule revisions before making
  a numeric claim for a recording.

`run_mechanics/dagger.py` implements the bounded source-backed arithmetic,
Egg/Gift Card `extra_value` updates, immediate-right-neighbor/eternal/already-
slicing eligibility checks, chronological Dagger effect reducer, and separate
reference comparator. `tests/test_dagger_mechanics.py` checks these rules on
synthetic inputs. Inputs require the exact pinned stack, all source hashes,
per-field source channels, and evidence IDs; reference-channel values are rejected
from pricing, eligibility, and baseline inputs. Input extraction from actual
visuals, same-reducer validation on independent observation inputs, and populated
gold-stake analytics remain pending. The analytics selector requires outcome,
stake, owner confirmation, and a selection evidence ID; unverified runs are
excluded. The #123 reference run is White stake, and
its reference channel does not contain the persistent `extra_value` history
needed to independently reconstruct Photograph's $4 sell value from base cost $5.
