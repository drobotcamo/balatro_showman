# Balatro Showman Planning

The project reconstructs as much visible Balatro state as possible, reliably,
from recorded gameplay video, validated against a Lua ground-truth oracle.
The dataset is exploratory: it may support analytics, imitation learning, or
other work. Winning plays are not a special objective at this stage.

## How To Use These Documents

- Read `ROADMAP.md` before starting work.
- Read the relevant `agent-state/threads/<issue-number>-<short-name>.md` to
  resume work from another session or worktree.
- Read the relevant component contract before changing that component; its
  inputs, outputs, invariants, and acceptance criteria are the interface
  between agents and development phases.
- Do not skip a phase gate because a later component can be prototyped early.

## Document Map

- `ROADMAP.md`: phased development plan and phase gates.
- `ARCHITECTURE.md`: system boundaries and data flow.
- `agent-workflow.md`: single definition of work-item, approval, subagent, and
  handoff rules.
- `DECISIONS.md`: durable decisions and open questions.
- `LEARNINGS.md`: verified reusable findings and failure modes.
- `TOOLING.md`: verified project and machine-specific command recipes.
- `agent-state/`: work-thread handoffs.
- `../.opencode/agents/`: configured subagents.
- `../.opencode/command/`: workflow commands (`/resume`, `/handoff`).
- `../.opencode/skills/`: reusable triggered procedures.
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

Planning documents are validated by running python on
`planning/check_contracts.py`.

## Status Vocabulary

Use one of: `planned`, `designing`, `building`, `validated`, `blocked`, or
`retired`.

Current status: `planned`.