# Balatro Showman Active Plan

This directory defines the active architecture and development contracts for the
Balatro Showman game-state reconstruction project.

The project goal is to reconstruct as much visible Balatro state as possible,
reliably, from recorded gameplay video. The resulting dataset is exploratory:
it may support analytics, imitation learning, policy learning, or other work.
Winning plays are not a special objective at this stage.

## How To Use These Documents

- Read `ROADMAP.md` before starting work.
- Read the relevant component contract before changing that component.
- Treat each contract's inputs, outputs, invariants, and acceptance criteria as
  the interface between agents and development phases.
- Update status and decisions in the document being changed.
- Do not skip a phase gate because a later component can be prototyped early.

## Document Map

- `ROADMAP.md`: phased development plan and phase gates.
- `ARCHITECTURE.md`: system boundaries and data flow.
- `DECISIONS.md`: durable decisions and unresolved questions.
- `components/ontology.md`: asset and class vocabulary.
- `components/synthetic-data.md`: compositor and annotation contract.
- `components/detection.md`: detector training and inference contract.
- `components/ocr.md`: text and numeric state extraction.
- `components/tracking.md`: temporal object identity and cleanup.
- `components/state-composition.md`: structured per-frame state.
- `components/events.md`: state transitions and action inference.
- `components/dataset.md`: storage, manifests, and reproducible exports.
- `components/learning.md`: downstream analytics and learning consumers.

## Status Vocabulary

Use one of: `planned`, `designing`, `building`, `validated`, `blocked`, or
`retired`.

Current status: `planned`.
