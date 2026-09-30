# Decisions and Open Questions

## Decisions

- The Lua live bridge is retained as the ground-truth oracle for state, action,
  and outcome. Manual capture is a one-time confirmation of ontology, layout,
  and data format, not the data-volume strategy.
- Video reconstruction remains the scale channel because it applies to footage
  with no engine access. It is scored against the oracle rather than graded by
  inspection alone.
- The existing vendored class-ID map is adopted as the versioned base ontology.
  IDs are extended, never renumbered; existing granularized data and published
  weights stay interpretable.
- Modifiers, editions, and seals are composition labels attached to parent
  objects, not separate base detector classes. A dedicated visible-attribute
  channel is still trained and evaluated for their recall.
- The heavy manual labeling studio is retired. A minimal annotation/QA tool and
  a documented evaluation protocol are required and count as active tooling.
- Outcome-conditioned learning and the policy transformer are retained as
  optional downstream consumers. Outcomes are metadata, never a collection
  filter.
- A canonical coordinate space and stream-layout normalization are mandatory
  across all stages.
- Synthetic data is the primary detector-labeling strategy.
- The implementation is our own, closely informed by Marco Costa's public CV
  pipeline; the downstream state/action/mask contract is adopted from his
  published policy-transformer schemas unless explicitly superseded.
- The target is broad visible-state reconstruction, including in-round state.
- The laptop is the primary development environment.
- Batch GPU execution must remain possible without changing data contracts.
- The dataset is exploratory; do not optimize exclusively for wins.
- Markdown is the planning and progress format.

## Open Questions

- Which exact Balatro version and mod configuration define the initial ontology?
- Which game assets can be legally and technically sourced for redistribution?
- What numeric threshold does each phase gate require, recorded in the Phase 0
  evaluation protocol?
- Which visible state cannot be recovered reliably from video alone?
- Which event labels can be inferred confidently without player-input logs, and
  what is the oracle agreement rate required before they are trusted?
- How is confidence propagated from detection/OCR through composition into event
  confidence?
