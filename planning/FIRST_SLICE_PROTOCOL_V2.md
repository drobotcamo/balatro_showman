# First-Slice Held-Out Evaluation Protocol v2

Status: frozen for prospective first-slice evaluation. @drobotcamo approved the
scoped criteria on 2026-10-03 in
https://github.com/drobotcamo/balatro_showman/issues/79#issuecomment-5971771156.
This version supersedes v1's pending pilot-acceptance criteria and first-shop
completion rule. It does not authorize held-out collection/scoring by itself,
assert that any system meets a threshold, or claim broad Phase 0 completion.

## Purpose, scope and completion

Evaluate one run segment from starting a Balatro run through selecting and
defeating the Small Blind, cashing out, and making purchases during the
immediately following shop visit. The five stages remain:

1. Start a run.
2. Select the Small Blind.
3. Play hands and discard as needed to defeat it.
4. Cash out and reach the shop.
5. Purchase from that first shop and observe the resulting state.

The scoped labels remain those in `FIRST_SLICE_PROTOCOL_V1.md`: page/stage,
relevant controls and interactions, visible cards/objects and their page/zone/order
and visible attributes, displayed score/target/progress, cash-out/reward, and first
shop offers/names/types/prices/money/selection/purchase/result. Oracle raw fields
and legal actions validate a separate channel; they never fill visual labels.
Unknown, missing, unsupported, occluded, ambiguous and not-applicable remain
distinct. Hidden deck order, unseen identities and undisplayed effects are not
positive visual labels.

The first-shop stage is complete when at least one affordable offer is actually
purchased and the resulting state is visible. Record the observed offer inventory,
prices, affordability, selections, completed purchases and result. If no purchase
is possible, record the constraint and mark this stage incomplete. Do not substitute
a later shop or infer a purchase from an unobserved state change.

This is a first-slice protocol only. Other pages, later blinds/shops, game versions,
and broad Phase 3–10 obligations remain staged. Metrics are separate by stage and
label family; there is no single aggregate score that can pass the slice.

## Evaluation units, splits and context

- Primary unit: one ordered run segment with a single run identity.
- Observation unit: a sampled source-video frame, optionally paired with an oracle
  step and explicit alignment evidence.
- Transition unit: action-to-result interval, with observations kept separate from
  oracle legal-action and reducer-mask validation.
- Assign the complete source recording and associated run segment to one split.
  Group repeated captures, excerpts, transformed copies and resumed segments from
  the same underlying play. Never split neighboring frames from one play across
  development, training and held-out material.
- Before held-out collection, declare and record the source-level split assignment,
  protocol version and grouping. Audit the external training and synthetic-source
  registries for overlap. Held-out sources may not revise labels, matching,
  thresholds, support requirements, normalization or context rules.
- A per-frame state label uses the target frame only. A transition/action-result
  label may use frames from the same run within 2.5 seconds on either side. Record
  every context frame used. A future frame must not rewrite an earlier raw state;
  values are not carried forward unless a separately specified, provenance-bearing
  inference is evaluated.

## Alignment and eligible support

Record source video/run/frame/step/schema identity, timestamp, alignment method and
version, marker/offset/FPS, and measured alignment uncertainty or failure. Marker
arithmetic alone does not establish rendered pre-action correspondence. A pair is
eligible for oracle comparison only when its visual reference is resolved and its
rendered correspondence is independently confirmed within the user-selected ±3
frame tolerance. Unverified, failed or disputed pairs remain unscored; report them
in reference coverage and missingness rather than dropping them.

For each stage/family/recording, report:

- `N`: scheduled annotation/comparison opportunities, including missing or
  disputed source evidence;
- `E`: opportunities with resolved reference and required alignment/provenance;
- `A`: explicit prediction abstentions among `E`;
- `P`: valid non-abstaining predictions among `E`;
- `I`: invalid predictions among `E`;
- `C`: exact matches among `P` under the frozen field comparison rule.

Check `E = A + P + I` and `0 ≤ C ≤ P ≤ E ≤ N`. Report reference availability
`E/N`, prediction coverage `P/E`, abstention `A/E`, invalid-output rate `I/E`,
conditional exact accuracy `C/P`, and correct yield `C/E` separately. A zero
denominator is undefined with zero support, never 100%. These ratios are defined
only for actual prediction opportunities; annotation inventory counts are not
accuracy or sufficiency claims.

## Metrics and frozen pass criteria

Apply each rule separately to every scored stage and label family:

- **Categorical, page, control, object-identity, numeric and event fields:** exact
  match under the declared field rule. The lower bound of the 95% source-recording-
  clustered confidence interval for exact accuracy must be at least `0.95`.
  Numeric fields also report exact/value error and absolute error in stated units.
- **Normalized OCR text:** normalization must be named/versioned before scoring.
  The lower 95% source-clustered confidence bound for exact field accuracy must be
  at least `0.95`; the upper bound for normalized character error rate must be at
  most `0.02`. Preserve raw OCR separately from normalized text.
- **Boxes, when a box task is part of the scored scope:** match one-to-one within
  the declared class and zone; IoU is intersection area divided by union area.
  Use IoU `0.50` as the match threshold. Per-family precision and recall must each
  have a lower 95% source-clustered confidence bound of at least `0.90`. Report
  support and unmatched/duplicate/ambiguous cases. Aggregate mAP alone is not a
  pass criterion; the detection contract's per-family, small-object and
  false-positive obligations remain when applicable.
- **Prediction coverage:** the lower 95% source-clustered confidence bound for
  `P/E` must be at least `0.90`.
- **Abstention:** the upper 95% source-clustered confidence bound for `A/E` must
  be at most `0.10`. A guessed value is an error, not a match or abstention.
- Report annotation disagreement/adjudication, invalid output, exclusions,
  missingness, alignment success/error, failures, per-recording results and
  variation separately. Do not pool away a failing or under-supported stratum.

Intervals resample independent source recordings as clusters, not frames. Report
the interval estimator/version and support with each result. Do not report an
inferential interval or generalization claim with fewer than 20 independent
recordings.

## Minimum support and decision rule

A held-out evaluation needs at least 20 independent source recordings overall.
Each scored stratum needs observations from at least 5 independent recordings and
at least 100 eligible opportunities. If either per-stratum floor or the overall
recording floor is not met, report descriptive evidence as inconclusive, not pass.
The selected first-slice pilot has one recording and seven sampled frames, so it
does not meet these held-out support floors.

## Recoverability disposition for the first-slice pilot

Recoverability is field- and condition-specific. The reviewed pilot evidence is
recorded in the external report referenced by #79 and its seven-frame manifest
(video SHA-256 `b425402bcd6b7b1538a0eea1429205041c551099b0c680647914827407f5537a`,
manifest SHA-256 `723beaaea90f0914e1fa948758fc899555f9751011592c2752ec3b212edc6d2a`).
It contains one recording, seven correlated frame samples and no reconstruction
predictions; all seven timestamp-to-rendered-frame alignments remain unverified.

| Field/condition | Scoped status | Evidence and condition | Downstream handling |
| --- | --- | --- | --- |
| Main menu, blind selection/play, cash-out, interactive shop and next-blind page identity under clear UI | `conditionally_recoverable` | User-reviewed samples at 1920×1080 from one recording | Preserve these sample labels; do not infer classifier accuracy or generalization. |
| Visible controls and OCR values shown clearly in the sampled frames | `conditionally_recoverable` | New Run, Small Blind, target, cash-out and visible shop/next-blind text | Keep raw and normalized values; score only with predictions and frozen comparisons. |
| Juggler identity in the first-shop purchase sequence | `conditionally_recoverable` | $4 offer in frame 2271; Juggler in Joker area in frame 2398; user-confirmed purchase | Preserve identity and transition evidence; hidden attributes remain unknown. |
| Interactive page identity during the shop-entry splash | `unmeasured` | SHOP splash at frame 1954 without stable interactive controls | Keep page ambiguous until context establishes it. |
| Full first-shop inventory, adjacent offer identity and cropped hand-card details | `unmeasured` | Inventory was not exhaustively annotated; hand cards are cut off in the sample | Do not interpret unreviewed as absent; retain unknown/occluded where later reviewed. |
| Video-to-oracle rendered correspondence and timing | `unmeasured` | Seven nearest-frame candidates with no measured synchronization error | Do not score oracle comparisons. |

No global `unrecoverable` disposition is supported. These scoped classifications do
not settle Q04 for other fields, conditions, pages, resolutions or source sets.
Unknown values remain unknown; this protocol changes no reducer or oracle contract.

## Frozen pilot evidence and limits

The independent frame reviewer agreed with all 32 labels in the seven-frame
development manifest; zero disagreements and exclusions were recorded. Coverage
inventory is 21 reviewed, 10 unreviewed and 4 absent frame-family slots. This is
one review of one annotator's labels, not an inter-annotator agreement estimate.
The source run itself has no terminal outcome and remains active; the sampled
first-slice segment is present before its later continuation. No prediction
accuracy, field error, precision/recall, IoU, prediction coverage or abstention
has been measured. This is not a Phase 0 or broad-phase pass.

## Authority and version boundary

The user @drobotcamo is the acceptance authority for this slice. The criteria above
are frozen for prospective first-slice evaluation; held-out collection/scoring
still requires a declared source-level split before collection. This approval does
not itself authorize a particular held-out source set or recording action. Results
cannot tune this version. Any criteria, matching, support, normalization or context
change requires a successor version and a fresh held-out source set, or a
documented decision about invalidated evidence.

Thresholds/support for other phases, broad Phase 0 completion, asset eligibility,
game-version coverage, and applicable detection/page/OCR/tracking/composition/
reduction/event/dataset/learning criteria remain open obligations.
