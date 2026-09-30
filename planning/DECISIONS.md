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
T0 planning/process artifacts reach `master` through an auto-PR the agent
opens and merges itself once required CI is green (no review); T1
contract/decision surfaces (AGENTS.md, agent-workflow.md, DECISIONS.md,
ROADMAP.md, components) are user-approved for substantive edits and
agent-safe for routine status flips; T2 pipeline code is merged by agents
with pasted test output, a recorded `@reviewer` verdict, and required CI;
T3 irreversible or unverifiable actions are user-decided. Alternatives
considered: uniform strictness (user reviews everything — bottleneck for a
solo project) and uniform laxity (runnable checks only — no protection
against self-preference bias on untestable claims). `planning-check` is a
required status check on `master` via branch protection. Amendment: T0 was
originally direct commits, but required checks mechanically block direct
pushes (GH006), so T0 became auto-PR at enforcement time.

### D016 — accepted — The repository is public
All history is permanently exposed. No secrets, private data, or unreviewed
vendored artifacts may ever be committed (T3). The `.claude/settings.local.json`
command allow-list and absolute local paths present in history are accepted as
innocuous; machine-specific paths in `TOOLING.md` are intentional. Vendored
submodules point to public upstream repositories.

### D017 — accepted — Model inference targets the ONNX format executed through ONNX Runtime

ONNX (the versioned model format) plus ONNX Runtime execution providers is the
default inference mechanism: models are exported to `.onnx` with a pinned
opset, and execution device is a provider-ordered session option, not pipeline
code — CPU and DirectML providers for laptop development, CUDA/TensorRT
providers for batch GPU. Numerical agreement across providers is required
within a pinned tolerance, not byte-identity: different providers legitimately
differ in low-order float bits. Alternatives considered: JAX (no DirectML
path), MLIR/StableHLO/IREE/TVM compiler stacks (maintenance cost too high for
a laptop-first project), Triton Inference Server (solves serving, not laptop
development), and SYCL/Kokkos (wrong ecosystem for a Python pipeline). The
Python array API standard is the analogous device-neutral interface for
non-model tensor code. This concretizes D012; it does not supersede any prior
decision — D011 and D012 remain in force, D012 as the goal this mechanism
implements.

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