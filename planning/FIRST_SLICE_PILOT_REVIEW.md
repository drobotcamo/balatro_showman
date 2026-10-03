# First-Slice Pilot Review Worksheet

Status: preparation for #79, not a scored pilot or an approved successor to
`FIRST_SLICE_PROTOCOL_V1.md`. That merged protocol governs #82 development work.
The definitions below are proposed reporting conventions for review, not new
annotation-tool interfaces, approved thresholds, or permission to score held-out
sources. No reconstruction measurements are available in this worksheet.

## Evidence to review

The #82 lead supplies the external manifest/report location and hashes, export
schema and tool revision, development split assignment, protocol version, source
recording/run identities, source/alignment hashes, sampled frame/transition IDs,
and independent QA reviewer/disposition. Preserve original and adjudicated labels
and unresolved disagreements. Review source pixels independently of producer
page names and oracle values. Freeze and identify each pilot's matching and
comparison rules before scoring that pilot; changed rules produce a new report.

Accepted #81 source evidence is recorded on
https://github.com/drobotcamo/balatro_showman/issues/81#issuecomment-5964870591:
run `1429448811400-9237`, marker `issue81-20261003T022251Z`, finalized loss,
29 steps, with reported integrity and sampled correspondence checks. This is a
candidate development source, not an annotated pilot or proof of complete v1
stage coverage. #82 must establish the five-stage coverage from visible evidence.
Any source defects affecting selected labels remain explicit exclusions or
uncertainties; an accepted recording is not universal semantic suitability.

The #79 comment mentioning `planning/EVALUATION_PROTOCOL_V0.md` refers to a
shop-only draft found in local checkpoint commit
`4c9cad5f1ac632218e2017b25ae44b132691fd9f`, not a merged protocol. Use v1;
do not combine that draft's sampling/context choices with the approved scope.

## Proposed count ledger and formulas

Create a ledger for each recording, stage, label family and relevant visibility
condition. Retain frame, transition and object units separately. Do not treat
neighboring frames as independent runs. Report counts before ratios:

- `N`: all scheduled annotation/comparison opportunities in the stratum,
  including missing frames, incomplete stages and disputed alignment.
- `E`: opportunities with resolved independent visual reference and the required
  provenance/alignment for that comparison; report every reason for `N - E`.
- `A`: explicit prediction abstentions among `E`, broken down by unknown,
  missing, unsupported, occluded and ambiguous status.
- `P`: valid non-abstaining predictions among `E`.
- `I`: malformed predictions among `E`; do not silently count them as abstentions.
- `C`: exact matches among `P`, under the declared comparison rule.

Suggested checks: `E = A + P + I` and `0 <= C <= P <= E <= N`.
Suggested ratios: reference coverage `E/N`, prediction coverage `P/E`,
abstention `A/E`, invalid-output rate `I/E`, conditional exact accuracy `C/P`,
and correct yield `C/E`. Report zero denominators as undefined with zero
support, never as 100%. Separate reference ambiguity from model abstention.
An unsupported positive guess is not a match. Record the opportunity schedule
and unit explicitly so object counts do not get pooled with frame counts.

For numeric fields, report exact count and absolute-error sum/count (MAE)
for valid paired numbers, with units and signed errors retained. For text,
report raw exact match separately from any named normalization; character error
rate, if applicable, is total edit distance divided by reference character count.
Empty references need a declared rule; do not drop them to improve the score.
No numeric tolerance or normalization is approved here.

For applicable detection tasks, report `TP`, `FP`, `FN`, precision
`TP/(TP+FP)` and recall `TP/(TP+FN)`, using the declared one-to-one matching rule,
class/zone restrictions and overlap criterion. IoU is intersection area divided
by union area for valid boxes in the same coordinate system. Keep duplicate
predictions and unmatched entities visible; no overlap threshold is selected
here. This worksheet does not replace per-family recall, small-object recall,
false-positive-rate or aggregate mAP obligations in the detection contract.

For transition/action labels, state the event unit and time-matching rule;
unobserved interactions are unresolved, not inferred successes. Report QA
disagreements over doubly reviewed opportunities, adjudicated counts and remaining
ambiguity. Report alignment success over attempted comparisons, correspondence
error with units, inspected sample IDs and uncertainty separately from accuracy.

List results per recording and stage even when a pooled summary is provided.
Describe dependence and observed range across recordings. A one-recording pilot
cannot estimate recording-level variation or justify generalization. Minimum
independent-source support and an uncertainty procedure remain user decisions;
no frame-level confidence interval is promoted to recording-level certainty.

## Initial recoverability matrix

All rows are `unmeasured`: v1 identifies scope, not recoverability evidence.
These are family-level placeholders. #82/#79 review must expand them into named
fields/conditions and evidence IDs, not classify an entire family from one frame.

| Scoped family | Status | Evidence needed / visibility condition | Downstream handling until measured |
| --- | --- | --- | --- |
| Page identity and stage transition | unmeasured | Independent pixels/time across all five stages; distinguish transitions and overlays | Preserve unknown/ambiguous page; do not substitute producer page labels |
| Relevant controls and observed interactions | unmeasured | Control visible, interaction evidence and action-to-result interval | Unseen interaction stays missing/ambiguous; next page alone is insufficient |
| Visible card/object identity, zone and order | unmeasured | Source-pixel mapping, independent identity/order labels, duplicates and occlusion cases | Preserve unsupported/occluded/unknown identity; no hidden-deck inference |
| Visible object attributes | unmeasured | Named applicable attributes and conditions, including modifier/edition/seal/sticker when visible | Keep raw observations and unknown attributes; no oracle completion |
| Small Blind score, target and progress | unmeasured | Displayed values and timing around play/discard and defeat | Missing display remains missing; retain raw text and normalization provenance |
| Cash-out and reward values | unmeasured | Visible reward fields and cash-out transition | Do not use engine-only rewards as visual truth |
| First-shop offers, names/types, prices and money | unmeasured | Offer visibility, affordability, OCR and changing shop state | Preserve raw/normalized distinction and unsupported offers |
| Selected/purchased status and resulting state | unmeasured | Observed purchase/result intervals and post-purchase money/offer changes | Incomplete or ambiguous purchase remains unresolved; no invented purchase count |

For each measured row retain source/frame/transition IDs, context window,
alignment and QA evidence, support, errors, uncertainty and failure conditions.
Use `recoverable`, `conditionally_recoverable` or `unrecoverable` only with
evidence and a stated condition; otherwise retain `unmeasured`. A conditionally
recoverable row names its visibility/context requirement. An unrecoverable row
names what evidence cannot resolve. Neither classification changes reducer or
oracle contracts without the relevant user decision.

## Pilot review and approval packet

After #82 delivers the artifacts, the #79 lead recomputes applicable counts by
stratum and independently reviews visibility, disagreements, missingness,
failures, exclusions and recoverability evidence. Where no reconstruction
predictions exist, annotation coverage/QA can be reported but reconstruction
accuracy remains unmeasured. Fixture tests alone cannot supply real-frame proof.

Then propose, for user approval, named criteria with formulas/matching rules,
thresholds, minimum independent-recording and per-stratum support, treatment of
insufficient support, recording-level uncertainty, permitted temporal context
and any carry-forward provenance, operational first-shop purchase completion,
recoverability disposition and downstream handling. Name the source-level holdout
plan and acceptance authority. Do not preselect numbers without pilot evidence.

Record the user's explicit scoped Q03/Q04 approval in a versioned successor and
the decision log. Freeze it and the source split before held-out collection or
scoring; never tune it on held-out results. Unresolved scopes stay open. Broader
detection/page/OCR/tracking/composition/reduction/events/dataset/learning metrics,
including Phase 10 quality/reporting, remain applicable obligations, not passed
or waived by this worksheet.
