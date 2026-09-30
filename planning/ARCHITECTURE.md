# Active Architecture

The pipeline has two data channels that meet at validation:

- **Ground-truth channel** (Lua live bridge): exact state, action, and
  outcome read from the game engine. Small, perfect, and only available for
  our own modded runs. Used as an oracle and for a hand-checkable eval set.
- **Reconstruction channel** (video): estimates the same things from footage
  with no engine access. Large, noisy, and the reason the project exists.

Video-only outputs are scored against the ground-truth channel, not against
"manual inspection."

```text
OFFLINE TRAINING DATA
  asset sprites + metadata + backgrounds
        |
  ontology / class map / typography
        |
  synthetic scene + glyph generator
        |
  detector + OCR training datasets
        |
        v
  trained detector and OCR models (used by the online stages below)

ONLINE VIDEO INFERENCE
  video --> normalize --> frame sampler --> object detector
            (canonical coords)
                                 |
                                 v
                       page + zone assignment
                                 |
                                 v
            OCR + tracking and temporal stabilization
            (one shared stabilization/provenance model)
                                 |
                                 v
                       structured state composition
                                 |
                                 v
                       persistent-state reduction (action space + masks)
                                 |
                                 v
                       event / action inference  <-- oracle validation
                                 |
                                 v
                       versioned datasets
                                 |
                                 v
                       analysis and learning

GROUND-TRUTH CHANNEL
  Lua bridge --> aligned (state, action, outcome) --> eval manifests, oracle scoring
```

Page/zone identity is inferred from detections, coordinates, and the ontology
before OCR; OCR consumes the page/zone assignment for field-region context, and
tracking owns the one stabilization model shared with OCR (D007, D020). This is
the acyclic bootstrap order: detect -> page/zone -> OCR + tracking -> compose ->
reduce -> infer events.

Feedback edges (not drawn): tracking feeds duplicate/miss cleanup back into
detection reconciliation; the oracle scores page classification, zone
assignment, persistent reduction, and event inference; eval-set failures
steer synthetic generation.

## Design Principles

- State reconstruction is the primary product; learning is a downstream
  consumer.
- The Lua bridge is the validation oracle for actions and outcomes. Video-only
  action inference must be measured against it, never assumed correct.
- Synthetic labels are authoritative for synthetic data, but real-frame
  evaluation against ground truth is mandatory.
- A single canonical coordinate space and stream-layout normalization are
  defined once and used by every stage; no stage invents its own geometry.
- Page/screen identity and zone assignment are first-class inferred outputs,
  not implicit steps.
- The pipeline declares the downstream contract it targets (persistent state +
  action space + legality masks) or explicitly deprecates it; it does not leave
  the consumer interface undefined.
- Every stage writes a versioned, inspectable artifact.
- Uncertainty and unknown values are represented explicitly.
- Models are exported to the ONNX format with a pinned opset and executed
  through ONNX Runtime execution providers (D017): CPU and DirectML execution
  are supported for development; batch GPU execution is an optimization, not
  a different pipeline.
- Object identity, object attributes, and object relationships are separate
  concepts.
- The pipeline must support the whole visible game, not only shop decisions.

## Boundary

The active implementation must not import from `legacy/`. `legacy/` is read-only
reference.

Any asset, model, or dataset an active stage depends on must live in a versioned
active store outside `legacy/`, with a provenance record (source, version,
license, retrieval coordinates, checksum):

- Sprite and metadata assets are committed or vendored with recorded provenance.
- Model weights are retrievable or stored with a checksum; a stage must state
  which model version it requires.
- Third-party trees are pinned as real git submodules (`.gitmodules`) when they
  must stay external, or vendored by copy when redistribution allows.
- Nothing an active stage requires may be gitignored; ignored paths hold only
  derived caches and large local data.
