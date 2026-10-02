# Balatro Showman Planning

The project reconstructs as much visible Balatro state as possible, reliably,
from recorded gameplay video, validated against a Lua ground-truth oracle.
The dataset is exploratory: it may support analytics, imitation learning, or
other work. Winning plays are not a special objective at this stage.

## How To Use These Documents

- Read `ROADMAP.md` before starting work.
- Read the relevant `agent-state/threads/<issue-number-or-tag>-<short-name>.md` to
  resume work from another session or worktree.
- Read the relevant component contract before changing that component; its
  inputs, outputs, invariants, and acceptance criteria are the interface
  between agents and development phases.
- Do not skip a phase gate because a later component can be prototyped early.

## Document Map

- `ROADMAP.md`: phased development plan, phase gates, and component ownership.
- `ARCHITECTURE.md`: system boundaries and data flow.
- `PHASE0_INVENTORY.md`: Phase 0 artifact inventory, provenance, and boundary.
- `BRIDGE_SPIKE.md`: file-IPC oracle contract and the Lua producer spike.
- `ORACLE_DATA_REVIEW.md`: issue #10 integrity and storage-conformance findings.
- `PERSISTENT_STATE_OWNERSHIP.md`: issue #14 oracle-vs-reducer decision note.
- `BALATRO_RUNTIME.md`: discovered local Balatro/Steamodded/Lovely runtime facts.
- `audit_oracle_runs.py`: read-only oracle-run integrity audit.
- `agent-workflow.md`: single definition of work-item, approval, subagent, and
  handoff rules.
- `DECISIONS.md`: durable decisions and open questions.
- `LEARNINGS.md`: verified reusable findings and failure modes.
- `TOOLING.md`: verified project and machine-specific command recipes.
- `agent-state/`: work-thread handoffs.
- `../.opencode/agents/`: configured subagents.
- `../.opencode/command/`: workflow commands (`/work`, `/orchestrate`,
  `/resume`, `/handoff`, `/verify`).
- `../.opencode/skill/`: reusable triggered procedures.
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

Planning documents are mechanically validated by running python on
`planning/check_contracts.py`: thread naming and handoff fields, decision and
learning formats and append-only ordering, open-question linkage, component
sections and status, roadmap ownership and gates, and resolvable backtick file
references in the core agent/planning documents. It does not judge prose
quality or validate gate thresholds; the
numeric thresholds are a Phase 0 evaluation-protocol deliverable (Q03).

## Status Vocabulary

Use one of: `planned`, `designing`, `building`, `validated`, `blocked`, or
`retired`.

Current status: `building`. Phase 0 is the active phase; the Lua-oracle
transport is validated, but contract conformance, video-to-engine alignment,
and the evaluation set are pending (see `PHASE0_INVENTORY.md`).
