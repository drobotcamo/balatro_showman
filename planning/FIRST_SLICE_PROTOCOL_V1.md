# First-Slice Development Evaluation Protocol v1

Status: development protocol. The user selected the five-stage Small
Blind/first-shop sequence and approved the visible label scope below on
2026-10-02. Pilot acceptance criteria remain pending review. This version
supports development annotation and pilot work; it does not authorize held-out
scoring or claim Phase 0 completion.

## Purpose and boundary

Evaluate one bounded Balatro run segment from starting a run through completing
the Small Blind, cashing out, and making purchases during the immediately
following shop visit. The sequence is intentionally broad enough to exercise
foundational page, object, text, action, state, and temporal-alignment concepts.
It is a development slice, not a claim of coverage across all game pages,
blind sizes, decks, stakes, seeds, resolutions, or game versions.

The five stages are:

1. Start a run.
2. Select the Small Blind.
3. Play hands and discard as needed to defeat the Small Blind.
4. Cash out and reach the shop.
5. Purchase multiple items from that shop visit.

Record the actual number of offers, affordability, selection, completed
purchases, and resulting state. Preserve shop constraints and any inability to
make multiple purchases as pilot evidence; do not substitute another shop visit
or silently treat an unobserved purchase as completed. The pilot review must
propose an operational completion rule for “various items” for user approval.

The slice ends after the post-purchase state is observable, or is marked
incomplete if the run cannot reach that point. Later blinds, later shop visits,
and a full-run outcome are outside this protocol version.

## Evaluation units and source identity

- The primary unit is a run segment with a single run identity and ordered
  stage/event records.
- The observation unit is a sampled video frame paired, where available, with
  the oracle step/action and an explicit alignment record. Preserve source video,
  run, frame, timestamp, oracle-step, and schema/version identities.
- The transition unit is the action-to-result interval: start run, blind
  selection, each play/discard action, blind completion, cash-out, and each
  purchase. Keep observed action labels separate from oracle legal-action and
  reducer mask validation (D020/D021).
- Split development and any future held-out material by independent source
  recording/run, never by frame or neighboring steps from the same run. A source
  video and its associated oracle run belong to one split. Repeated captures,
  excerpts, or transformed copies of the same underlying play remain grouped.
- No held-out source may inform annotation revisions, matching rules, thresholds,
  support requirements, or temporal-context choices. Record split assignment and
  protocol version before held-out collection or scoring.

No minimum number of independent runs or recordings is established by v1. The
pilot must report counts and dependence; it cannot support statistical
generalization claims. Final minimum support and uncertainty rules require
approval after pilot review.

## Scope of labels

Annotate what is visibly present and observable for these stages:

- Page identity and stage transition, with evidence frame/time and annotator
  confidence or unresolved status.
- Visible controls relevant to starting the run, selecting the Small Blind,
  playing/discarding, cashing out, and purchasing. Record control identity and
  observed interaction/result; do not infer an action solely from the next page.
- Visible cards and other selectable/playable objects in their page zones,
  including stable identity where evidence supports it, order, and visible
  attributes. Unknown identity/attribute remains unknown.
- Displayed score/target and progress needed to establish Small Blind defeat,
  where shown; cash-out/reward values where shown.
- Shop offers, displayed names/types, prices, visible attributes, money shown,
  selected/purchased status and post-purchase money/offer changes.
- Oracle raw persistent fields and engine legal actions as validation references
  only. They are not visual labels and do not fill missing observations.

Do not infer hidden deck order, unseen card identity, undisplayed effects, or
engine-only values from the oracle into video-observation ground truth. Keep
`unknown`, `missing`, `unsupported`, `occluded`, `ambiguous`, and `not_applicable`
distinct where the annotation schema supports them; never turn an uncertain
label into a positive match.

## Temporal context and alignment

The target is a timestamped sequence, not just isolated screenshots. Annotators
may inspect the ordered source frames and adjacent context within the same run
to identify transitions and associate a visible result with an observed action.
Record the context window used for each transition label. Do not use a future
frame to fill the visual state of an earlier target frame, and do not carry values
forward unless the producing stage explicitly records that inference and its
provenance. Preserve raw per-frame observations separately from any temporal
stabilization.

For every scored frame/transition, retain the source timestamp, frame identity,
oracle-step identity if available, alignment method/version, and alignment
uncertainty or failure. Existing marker/frame mappings alone are not proof of
rendered pre-action correspondence or measured synchronization error. Unaligned
or disputed pairs remain unscored for oracle comparison and count in coverage
and missingness reports.

## Matching and pilot procedure

- Compare page identity, visible controls/objects, OCR fields, and transition
  outcomes as separate label families; do not collapse them into one aggregate
  score.
- Match entities within their annotated page/zone and frame/transition using
  stable IDs where justified, otherwise use a documented one-to-one match on
  class/attributes and location. Freeze the matching rule for a scored pilot
  version; unmatched, duplicate, or ambiguous predictions remain errors or
  unresolved cases under that rule, not hand-corrected successes.
- Compare inferred actions with observed action labels separately from comparing
  reducer persistent state/masks with oracle raw fields/legal actions.
- Have a second reviewer inspect pilot annotations and disagreements. Preserve
  original labels, adjudicated labels, rationale, reviewer identity, and schema
  version; unresolved disagreements remain ambiguous.
- Keep failures, incomplete runs, annotation exclusions, and alignment failures
  in the manifest with reasons. Do not silently filter difficult stages.

## Required pilot reporting

Report per stage and label family:

- numerator, denominator, support, and excluded/unscored counts with reasons;
- exact-match accuracy for categorical labels and field-level exact/value error
  for numeric/text fields, with the comparison/matching rule stated;
- precision/recall or intersection-over-union only where a relevant object/box
  task and its matching rule are defined;
- coverage and abstention/unknown rates separately from conditional accuracy;
- annotation disagreement and adjudication counts;
- alignment success, measured correspondence evidence, and uncertainty;
- per-recording results and variation, not only pooled frame totals; and
- incomplete-stage counts, failure cases, missingness, and limitations.

Do not claim generalization from a small or correlated pilot. No numeric pass
threshold, confidence interval procedure, minimum support, or aggregate pass
rule is approved in v1. Insufficient support is inconclusive, not a pass.

## Recoverability matrix

For each scoped field/label family, maintain a pilot matrix with status
`recoverable`, `conditionally_recoverable`, `unrecoverable`, or `unmeasured`;
record evidence/source identities, visibility conditions, failure modes,
uncertainty, and downstream handling. Until pilot evidence is reviewed, use
`unmeasured` rather than predicting recoverability. A field may be classified
unrecoverable only for a stated visibility/context condition and with evidence;
this does not settle Q04 globally.

Downstream outputs preserve uncertainty and abstain rather than inventing a
value. Any reduction/oracle-boundary change based on recoverability evidence
requires the relevant user decision; this protocol alone does not change those
contracts.

## Approval and version boundary

This version records the user-selected stage and label scope and development
procedure. Pilot review must propose named evaluation criteria, numeric
thresholds, minimum support, uncertainty rules, acceptance authority, and the
recoverability disposition for this slice (Q03/Q04). It cannot silently approve
them. The user must approve those criteria and a frozen protocol version before
any held-out collection/scoring. Held-out results may not tune that version.
Changes after freeze require a new version and a fresh held-out source set or an
explicitly documented decision about invalidated evidence.

This protocol does not settle other pages, later blinds/shops, future-phase
metrics, asset eligibility, game/version configuration, or broad Phase 0
acceptance. Those remain governed by the roadmap, component contracts, and
linked open questions.
