# Issue #129 RunBundle Query Report

Status: prepared for owner inspection. This report uses RunBundle action
snapshots as reducer inputs. The mechanics-reference sidecar is summarized
separately as an engine answer channel and never supplies reducer fields.

## Source and validation

- Run: `15595792437600-8332`, 347 action steps, outcome `lost`.
- RunBundle: `F:\OBS_RECORDINGS\issue123_dagger_reference.sqlite`.
- Capture directory: `F:\OBS_RECORDINGS\oracle_runs_issue129\15595792437600-8332`.
- `session.json` SHA-256:
  `88d559a1a63bf4e8fbc0fbace019756d9e2daed82a08b0624b0fe2f30d8e9621`.
- `steps.ndjson` SHA-256:
  `2ba3b8b962a8e69cf8a53eaa7596cd487176a20ad96cf22a5c8e6c567ab46586`.
- `mechanics_reference.ndjson` SHA-256:
  `25586c217508af60022ab92e3f490b1971ac2df81f4c30122662fcd66ff8d148`.
- Strict validation: `valid`, 763 RunBundle records, no bad sequences.
- Mechanics-reference watermark: 69 resolved, 0 pending.

## Query results

| Named query | RunBundle-derived result | Status |
| --- | --- | --- |
| Hermit direct money this run | `$40` | Known |
| Mail-In Rebate earnings by target rank and round | Unknown from action snapshots | Unknown |
| Most frequent qualifying discarded rank | Unknown from action snapshots | Unknown |
| Most frequent rank discarded while Rebate was owned | Tie: `3` and `4`, 29 participations each | Known |

### Hermit

The action snapshots explicitly select `c_hermit` at steps `:308`, `:311`,
and `:329`. Their pre-use balances are `$38`, `$54`, and `$0`; the next action
snapshots show `$58`, `$74`, and `$0`. Applying the pinned source formula
`max(0, min(dollars_before, 20))` yields direct contributions `$20`, `$20`, and
`$0`, totaling `$40`. Each interval delta agrees with the direct contribution.
The three separate engine-reference occurrences report the same amounts.

### Mail-In Rebate discarded-rank frequency

RunBundle snapshots show 66 discard intervals with at least one `j_mail` in
`CurrentJokers`, containing 281 card participations. Each card is counted once
per discard interval even when two Mail-In Rebate Jokers are present. The
observed rank histogram is:

| Rank | Participations | Rank | Participations |
| --- | ---: | --- | ---: |
| 2 | 18 | 9 | 22 |
| 3 | 29 | 10 | 23 |
| 4 | 29 | Jack | 23 |
| 5 | 27 | Queen | 11 |
| 6 | 23 | King | 17 |
| 7 | 27 | Ace | 9 |
| 8 | 23 | | |

The separate reference sidecar produces the same 281-card histogram. Both
channels therefore identify ranks `3` and `4` as tied at 29.

### Unknown Rebate queries and reference-only expected answers

RunBundle action snapshots do not include the round's Rebate target rank, the
effective `Card:get_id()` used by the trigger, or per-card debuff and trigger
multiplicity. Their generic consumable/action representation also does not give
stable Joker/card instance tokens. The reducer therefore does not claim earnings
by target rank or qualifying-rank frequency from these inputs.

For validation only, the separate mechanics-reference channel records 542
Joker/card participations from two Rebate instances. Its direct contributions
sum to `$370`. Reference earnings by round and target rank are:

| Round | Target rank | Direct earnings | Round | Target rank | Direct earnings |
| ---: | --- | ---: | ---: | --- | ---: |
| 2 | 7 | $20 | 9 | King | $50 |
| 3 | 7 | $30 | 10 | King | $50 |
| 4 | 4 | $20 | 11 | 9 | $20 |
| 5 | 2 | $0 | 12 | 10 | $20 |
| 6 | 4 | $40 | 13 | 5 | $30 |
| 7 | 4 | $40 | 14 | Ace | $10 |
| 8 | 3 | $40 | | | |

Counting distinct discarded cards with positive captured direct contribution
gives qualifying-rank reference counts: `4` = 10 and `King` = 10, a tie. These
are reference answers, not reducer results or reducer inputs.

## Reducer behavior change

The Rebate report now evaluates the discarded-rank-frequency query independently
from the other Rebate fields. With complete ownership/card-rank coverage, missing
target/effective rank or trigger multiplicity leaves earnings and qualifying-rank
queries unknown while preserving a known discarded-rank frequency. Invalid,
reference-only, contradictory, or incomplete rank evidence still makes that
frequency unknown.

## Reproduction

```text
python -m run_bundle validate --db F:\OBS_RECORDINGS\issue123_dagger_reference.sqlite --run 15595792437600-8332 --strict
py -3 -m pytest -q tests/test_hermit_rebate.py tests/test_dagger_mechanics.py
py -3 planning/check_contracts.py
```
