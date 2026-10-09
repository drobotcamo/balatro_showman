# Video-Like Dagger Input Protocol v1

Status: bounded development protocol; no evaluation thresholds or actual-video
claims.

## Purpose and boundary

Freeze the first #127 observation-only input shape for the #124 Dagger reducer.
The companion fixture is `tests/fixtures/video_like/dagger_v1.json`. Every case
is explicitly `synthetic_video_like_not_actual_video`; values instantiate the
approved illustrative Dagger example, not pixels, a CV prediction, a captured
run, or engine output. The fixture is not held out and cannot be used to claim
visual-model accuracy.

The adapter is `run_mechanics.video_like.adapt_video_like_record`. It accepts the
versioned `observation` fields in the fixture and projects them into the same
`reduce_sacrifices` reducer used by #124. A sibling `engine_reference` payload is
ignored by the adapter and reserved for later independent comparison. Engine
answers, IDs, event order, or other privileged values inside `observation` are
rejected. Track keys refer to visual observations and may be reused across ordered
intervals only when continuity is supported; they are not persistent game-instance
IDs. `ordered_visual_sequence` means only that the hypothetical
pre/action/aftermath samples have an order; it is not a timestamp or verified
rendered alignment.

An observed sell-value tooltip is a direct observation when the number is
legible. If complete source-derived pricing inputs are also present, compare the
values; disagreement invalidates the exact growth result. Missing tooltip and
incomplete pricing inputs leave causal growth unknown. A separately visible
post-Mult and its arithmetic delta remain observed-state evidence; they do not
fill the missing sell-value input. An unambiguous, ordered post-state can establish
a later reducer baseline without making the earlier effect known. Missing action,
ambiguous identity, or uncertain timing prevent exact opportunity resolution.
Conflicting post-Mult is `ambiguous`; neither value is selected as the result.

## Acceptance procedure

1. Run `python -m run_mechanics.video_like` and retain its JSON-lines output.
2. Run `python -m pytest -q tests/test_video_like_dagger.py tests/test_dagger_mechanics.py`.
3. Confirm all cases and perturbation checks below pass:

| Case/check | Required outcome |
| --- | --- |
| Tooltip $4, Dagger Mult 6, eligible neighbor, observed select-blind action, visible aftermath 14 | Same reducer returns growth 8 and Mult 14; removal remains pending unless separately observed. |
| Missing tooltip and no complete pricing derivation | Unknown causal sell value/growth/effect; never zero. A separately observed post-Mult/state delta stays distinct and may re-establish a later baseline. |
| Missing action | Unknown eligibility/effect. |
| Ambiguous visual identity | Ambiguous attribution and no exact growth. |
| Ambiguous action timing | Ambiguous interval and no exact growth. |
| Tooltip plus complete matching source price | Reducer accepts the value with both evidence paths retained. |
| Tooltip conflicts with complete source price | Ambiguous result; exact growth/Mult are invalidated. |
| Visible post-Mult conflicts with reducer result | Ambiguous result; exact growth/Mult are invalidated. |
| Engine answers/IDs/reference fields changed or absent beside the observation | Normalized reducer output is structurally identical. |
| Reference-only field inserted in the observation projection | Adapter rejects the input. |

Missing/ambiguous/contradictory diagnostics identify interval, rule revision,
visual track key, dependency, affected output/query family, and readable reason.
The existing #124 reducer carries unknown Dagger state to subsequent intervals
until an independent observed baseline re-establishes it. A visually evidenced
post-Mult with unambiguous track identity and ordered timing is retained as that
later baseline while the prior effect remains unknown or ambiguous.

## Commands

```text
python -m run_mechanics.video_like
python -m pytest -q tests/test_video_like_dagger.py tests/test_dagger_mechanics.py
python planning/mechanics_contract_check.py
python planning/check_contracts.py
git diff --check
```

This protocol does not establish an actual-video pair. Actual integration requires
selected visual outputs, verified rendered pre-action correspondence, and a
separate field/effect agreement and abstention report. Timestamp/frame arithmetic
alone is not alignment evidence. No metric threshold, held-out split, or #82 gate
is changed or passed here.
