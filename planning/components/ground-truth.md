# Component Contract: Ground Truth and Evaluation

Status: `building`

## Purpose

Showman Capture is the product name for the operational capture/inspection
capability. `python -m showman` delegates to the existing producer consumer,
Run Store, Inspector, recording association, alignment and development export
interfaces. Usage and vocabulary are in `docs/capture/README.md`; the wrapper
does not change the oracle/video separation or broad acceptance criteria.

Capture `(state, action, outcome)` and independent mechanics reference values;
maintain aligned real-frame evaluation and minimal annotation/QA. Suitability is
field/revision-specific: defaults/coarse legality are not exact engine truth.
`planning/ARCHITECTURE.md` defines separate evidence and answer-key channels.
#123 stages Dagger reference first, then only the extensions consuming slices need.
#82 owns annotation/evaluation; #115 owns Continue identity and live acceptance.

## Inputs

- Modded game client and the Lua bridge (Steamodded).
- Human or scripted play sessions.
- Recorded video with timestamps for frame alignment.
- Annotation/QA tool output.

## Outputs

- Ground-truth run records: per-step state, action label, and run outcome.
- Versioned run bundles with active, interrupted, and finalized lifecycle
  states, provenance, integrity metadata, and read-only inspection access
  (Issue #34).
- Raw engine persistent fields and the game's own legal actions/mask basis, as
  the reducer validation reference (D021).
- Aligned video frames for benchmarked steps.
- Evaluation-set manifests with an annotation protocol.
- A minimal annotation/QA tool for real-frame boxes and text fields.
- Independent pre/action/resolved mechanics reference values with source hashes,
  timing and revision. Old captures with missing values remain unchanged/unknown.

## Invariants

- Ground truth is never synthesized into observed state; it is a separate
  channel used only for validation and outcome labeling.
- Reference access is isolated from reconstruction adapters; perturbing reference
  values cannot change inferred state/effects. Capture anchors retain their origin.
- The oracle emits raw engine fields and engine legality; it does not compute
  canonical `persistent_state` — the pipeline reducer owns that shape (D021).
- Video-to-engine alignment is explicit and auditable (timestamps, offsets).
- Recording coordination is human-confirmed: a tool may request OBS recording
  and associate its marker, but it never assumes video exists without evidence.
- The run-bundle storage boundary does not own the low-level OBS hook or the
  timestamp-to-frame alignment algorithm.
- Evaluation clips are disjoint from synthetic backgrounds and from training
  video.
- The oracle scores page classification, zone assignment, persistent reduction,
  and event inference; it does not replace them.

## Acceptance Criteria

- #123 Dagger: producer/reader scenarios and authorized live capture establish
  pre-Mult, actual victim sell value, resolved post-Mult and identity; demonstrate
  answer-key isolation. Resumed scenarios reuse #115, not a competing lifecycle fix.
- This bounded acceptance does not add registry coverage to Phase 0 or pass the
  broader evidence/evaluation criteria below.
- The oracle emits aligned steps for at least one full run.
- The eval set has action and field-level ground truth sufficient to compute
  Phase 3-8 metrics.
- The annotation/QA tool can label boxes and text fields on real frames and
  export to the eval manifest format.
- Bounded slices use named criteria in the applicable approved versioned protocol,
  fixed before held-out evaluation. Development pilots may inform that protocol;
  they do not pass the broad Phase 3-8 sufficiency criterion.
