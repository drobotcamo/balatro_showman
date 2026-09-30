# Balatro Showman Active Plan

This directory defines the active architecture and development contracts for the
Balatro Showman game-state reconstruction project.

The project goal is to reconstruct as much visible Balatro state as possible,
reliably, from recorded gameplay video, validated against a Lua ground-truth
oracle. The resulting dataset is exploratory: it may support analytics,
imitation learning, policy learning, or other work. Winning plays are not a
special objective at this stage.

## How To Use These Documents

- Read `ROADMAP.md` before starting work.
- Read the relevant `agent-state/threads/<issue-number>-<short-name>.md` to resume work from
  another session or worktree.
- Read the relevant component contract before changing that component.
- Treat each contract's inputs, outputs, invariants, and acceptance criteria as
  the interface between agents and development phases.
- Update status and decisions in the document being changed.
- Do not skip a phase gate because a later component can be prototyped early.

## Document Map

- `ROADMAP.md`: phased development plan and phase gates.
- `ARCHITECTURE.md`: system boundaries and data flow.
- `DECISIONS.md`: durable decisions and unresolved questions.
- `LEARNINGS.md`: verified reusable findings and failure modes.
- `TOOLING.md`: verified project and machine-specific command recipes.
- `agent-workflow.md`: session, subagent, and handoff procedures.
- `agent-state/`: branch/worktree-scoped work-thread handoffs.
- `../.opencode/skills/`: reusable triggered procedures.
- `../.opencode/command/`: common agent workflow commands.
- `components/ontology.md`: asset, class, page/zone, and typography vocabulary.
- `components/ground-truth.md`: Lua oracle, evaluation set, annotation/QA tool.
- `components/coordinates.md`: canonical coordinate and stream-layout contract.
- `components/synthetic-data.md`: compositor, glyph, and annotation contract.
- `components/detection.md`: detector and visible-attribute contract.
- `components/page-classification.md`: screen identity and zone assignment.
- `components/ocr.md`: text and numeric state extraction.
- `components/tracking.md`: temporal object identity and cleanup.
- `components/state-composition.md`: structured per-frame state.
- `components/state-reduction.md`: persistent state, action space, and masks.
- `components/events.md`: state transitions and action inference.
- `components/dataset.md`: storage, manifests, and reproducible exports.
- `components/learning.md`: downstream analytics and learning consumers.

## Status Vocabulary

Use one of: `planned`, `designing`, `building`, `validated`, `blocked`, or
`retired`.

Current status: `planned`.
