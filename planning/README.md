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
- Start an agreed ready issue through `agent-workflow.md`; portfolio assessment
  is for unresolved selection. D028 permits cross-component slices, not claims
  that unmeasured broad gates passed.

## Document Map

- `WORKFLOW_MIGRATION_IMPLEMENTATION_PLAN.md`: D028 implementation handoff,
  scoped subagent assignments, migration acceptance, and production follow-through.
- `LEAD_WORKFLOW_MIGRATION_PROMPT.md`: direct lead launch prompt for that migration.
- `PRODUCTION_RETROSPECTIVE_2026-10-02.md`: production/workflow review and evidence.
- `WORKFLOW_MIGRATION_VERIFICATION.md`: scenario evidence and reserved CI/input requests.

- `ROADMAP.md`: phased development plan, phase gates, and component ownership.
- `ARCHITECTURE.md`: system boundaries and data flow.
- `PHASE0_INVENTORY.md`: Phase 0 artifact inventory, provenance, and boundary.
- `FIRST_SLICE_PROTOCOL_V1.md`: development protocol for the initial Small Blind
  and first-shop evaluation slice; held-out criteria remain pending approval.
- `FIRST_SLICE_PILOT_REVIEW.md`: proposed pilot reporting formulas, initial
  unmeasured recoverability matrix, and preparation for criteria approval.
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
criteria and numeric thresholds require the applicable approved versioned
protocol before held-out evaluation (Q03).

## Status Vocabulary

Use one of: `planned`, `designing`, `building`, `validated`, `blocked`, or
`retired`.

Current status: `building`. Capture/storage/inspection components exist and a
historical pinned run has alignment metadata. Recorder reliability, current
rendered correspondence, semantic suitability and evaluation acceptance remain
open. Next delivery is reliable recorded-run inspection (#81), then reviewed
evaluation slice (#79/#82), then measured video-only reconstruction. See
`PHASE0_INVENTORY.md`; live ownership/blockers belong on GitHub, not this index.
