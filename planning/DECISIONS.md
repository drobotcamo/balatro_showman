# Decisions

One entry per durable choice. Entries are append-only: superseded entries are
marked `superseded`, never deleted. State the alternative and why the chosen
option fits the tenets in `AGENTS.md` when the alternative is material.
Unresolved questions are first-class outputs; a question that blocks a gate
must be linked from `ROADMAP.md`.

## Decisions

### D001 — accepted — The Lua live bridge is the ground-truth oracle
State, action, and outcome ground truth comes from the Lua bridge. Manual
capture is a one-time confirmation of ontology, layout, and data format, not
the data-volume strategy.

### D002 — accepted — Video reconstruction is the scale channel
It applies to footage with no engine access and is scored against the oracle
rather than graded by inspection alone.

### D003 — accepted — The vendored class-ID map is the versioned base ontology
IDs are extended, never renumbered, so existing granularized data and
published weights stay interpretable.

### D004 — accepted — Modifiers, editions, and seals are composition labels
They attach to parent objects instead of being separate base detector classes.
A dedicated visible-attribute channel is still trained and evaluated for
their recall.

### D005 — accepted — The heavy manual labeling studio is retired
A minimal annotation/QA tool and a documented evaluation protocol are
required and count as active tooling.

### D006 — accepted — Outcome-conditioned learning and the policy transformer are optional consumers
Outcomes are metadata, never a collection filter.

### D007 — accepted — Canonical coordinate space and stream-layout normalization are mandatory
They apply across all stages.

### D008 — accepted — Synthetic data is the primary detector-labeling strategy

### D009 — accepted — The implementation is our own, informed by Marco Costa's public work
The downstream state/action/mask contract is adopted from his published
policy-transformer schemas unless explicitly superseded.

### D010 — accepted — The target is broad visible-state reconstruction
This includes in-round state, not only menus or macro state.

### D011 — accepted — The laptop is the primary development environment

### D012 — accepted — Batch GPU execution must remain possible without changing data contracts

### D013 — accepted — The dataset is exploratory
Do not optimize exclusively for wins.

### D014 — accepted — Markdown is the planning and progress format

### D015 — accepted — The approval policy is risk-tiered evidence
T0 planning/process artifacts commit directly to `master` with CI as the
gate; T1 contract/decision surfaces (AGENTS.md, agent-workflow.md,
DECISIONS.md, ROADMAP.md, components) are user-approved for substantive
edits and agent-safe for routine status flips; T2 pipeline code is merged by
agents with pasted test output, a recorded `@reviewer` verdict, and required
CI; T3 irreversible or unverifiable actions are user-decided. Alternatives
considered: uniform strictness (user reviews everything — bottleneck for a
solo project) and uniform laxity (runnable checks only — no protection
against self-preference bias on untestable claims). `planning-check` is a
required status check on `master` via branch protection.

## Open Questions

- **Q01** — Which exact Balatro version and mod configuration define the
  initial ontology?
- **Q02** — Which game assets can be legally and technically sourced for
  redistribution?
- **Q03** — What numeric threshold does each phase gate require, recorded in
  the Phase 0 evaluation protocol?
- **Q04** — Which visible state cannot be recovered reliably from video alone?
- **Q05** — Which event labels can be inferred confidently without
  player-input logs, and what oracle agreement rate is required before they
  are trusted?
- **Q06** — How is confidence propagated from detection/OCR through
  composition into event confidence?