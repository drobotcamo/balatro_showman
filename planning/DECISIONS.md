# Decisions and Open Questions

## Decisions

- The manual labeling studio is retired from the active plan.
- Synthetic data is the primary detector-labeling strategy.
- The implementation will be our own, closely informed by Marco Costa's public
  CV pipeline.
- The target is broad visible-state reconstruction, including in-round state.
- The laptop is the primary development environment.
- Batch GPU execution must remain possible without changing data contracts.
- The dataset is exploratory; do not optimize exclusively for wins.
- Markdown is the planning and progress format.

## Open Questions

- Which exact Balatro version and mod configuration define the initial ontology?
- Which game assets can be legally and technically sourced for redistribution?
- Should modifiers be detector classes, composition labels, or both?
- What minimum real-frame evaluation set is sufficient for each phase gate?
- Which visible state cannot be recovered reliably from video alone?
- Which event labels can be inferred confidently without player-input logs?
