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

### D015 — superseded — The approval policy is risk-tiered evidence
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
pushes (GH006), so T0 became auto-PR at enforcement time. Superseded by D019;
the inline amendment above is preserved as history.

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

### D018 — accepted — Delegation is evidence-driven and minimal
Agents use direct repository tools for routine inspection, editing, checks, and
GitHub metadata. At most one implementation agent is used per issue; exploratory
agents are reserved for information unavailable through local inspection, and a
reviewer is deferred until a final T2 diff exists. Routine conflict resolution
does not spawn another agent, existing sessions are resumed where practical, and
agent prompts/results stay concise. Alternative: unconstrained delegation was
rejected because Issue #6 demonstrated that duplicate research, implementation,
conflict-resolution, and review sessions create token cost without proportional
evidence.

### D019 — accepted — T0 planning/process artifacts reach `master` as auto-PRs
T0 planning/process artifacts (thread files, `LEARNINGS.md`, `TOOLING.md`,
`.opencode/` configs and agents, `.github/` templates, and non-T1 planning
prose) are merged by the agent through an auto-PR once the required status
check (`planning-check` workflow, context `check`) is green; no human review
is required. T1
contract/decision surfaces are user-approved for substantive edits and
agent-safe for routine status flips; T2 pipeline code is merged with pasted
test output, a recorded `@reviewer` verdict, and required CI; T3 irreversible
or unverifiable actions are user-decided. Alternatives considered: direct
commits to `master` (rejected — required status checks mechanically block
direct pushes, GH006, so T0 must travel as a PR); human review of T0 (rejected
as a bottleneck for a solo project); runnable-checks-only (rejected because
checks cannot protect untestable claims). This supersedes D015 and keeps the
`planning-check` workflow (context `check`) a required status check on
`master`.

### D020 — accepted — The reducer owns the action-space index; events label observed actions
Persistent reduction (Phase 7) defines the action-space index and emits
deterministic legality masks over it. Event/action inference (Phase 8) consumes
state deltas and emits each event's canonical action label, target, and
`target_action_id` within that index. This gives the mask coordinate space and
observed-action labeling single, separate owners, avoiding two divergent action
mappings. Alternative considered: the reducer also emitting `target_action_id`
(rejected because it would need the inferred action before events exist, or
would duplicate the event mapper).

### D021 — accepted — The oracle emits raw engine fields and legal actions; the reducer owns canonical persistent state
Canonical `persistent_state` is produced by the single pipeline reducer
(Phase 7), not by the Lua oracle. The oracle emits engine-truth raw persistent
fields (deck class ID and flags, stake, tracked deck cards with their
modifier/edition/seal/stickers, hand levels and played counts, vouchers
redeemed, bosses used, blind statuses and counters) plus the game's own legal
actions as the validation reference. The producer transport gains a versioned
raw-field schema distinct from the granularized `3.0.0`; the reducer documents
and tests the raw-field mapping to the adopted persistent-state contract
(`legacy/vendor/balatro-policy-transformer/state_schema.md` §3), including the
video-only artifacts (tracked-deck FIFO cap, closest-match consumable rule,
Aura `e_foil` placeholder, unmodeled random/hand-wide spectrals). The
engine-truth versus video-recoverable gap is the recorded Q04 output.
Alternatives considered: (a) the oracle computes and emits canonical
persistent state — rejected because it creates a second reducer that can drift
from the pipeline's and makes the mask oracle depend on our own state-shaping;
(b) the producer emits observations only with no persistent-state reference —
rejected because the Phase 7 state-reproduction and mask-agreement criteria
become unscorable. This concretizes D009 and D020; source: Issue #14 design
note `planning/PERSISTENT_STATE_OWNERSHIP.md` and
`planning/ORACLE_DATA_REVIEW.md` §7 (P3).

### D022 — accepted — The orchestrator assesses portfolio state with T0 write authority and is the primary issue creator

Portfolio-level assessment, handoff auditing, and next-issue selection belong
to a dedicated orchestrator agent (`.opencode/agent/orchestrator.md`, invoked
via `/orchestrate`) with a fixed procedure: state assessment, handoff audit
against repository evidence, readiness derivation from issue dependencies and
the ROADMAP open questions and gates, and a recommendation ending in the next
issue and worktree decision. Its write authority is T0 only (thread batons,
stale-thread closure, issue/PR comments, issue creation); it never edits
pipeline code, never merges PRs, and is never the sole approver of its own
changes. It is the primary issue creator; workers may still propose
sub-issues per `planning/agent-workflow.md`. Worktree selection is codified:
T0/planning issues may run in-place when the main checkout is free; T2
pipeline issues get a dedicated worktree.
Alternatives considered: (a) the per-item lead agent also orchestrates —
rejected because a session owning one work item cannot audit its own handoffs
impartially and portfolio state assessment went unowned; (b) an external
dependency-aware issue tracker (e.g. beads) as the source of truth — rejected
for now because GitHub Issues plus structured planning tables already carry
dependencies and gates, and adopting a new coordination authority is a larger
architecture change than this phase needs. Source: Issue #25 and user-approved
design conversation of 2026-09-30.

### D023 — accepted — Issue #34 owns run-bundle storage and human-confirmed recording coordination
Issue #34 builds the first durable, versioned run-bundle storage layer and the
read-only inspection API over it. A bundle supports active, interrupted, and
finalized runs, preserves provenance, and can be audited without knowing the
future Phase 9 dataset storage technology. The tool may request and associate
an OBS recording, but must notify a present user and require explicit or
verified recording-start confirmation. It must not silently assume that video
exists or replace the low-level OBS marker hook and timestamp-to-frame
alignment owned by the recording/alignment work (Issues #15 and #35).

Canonical persistent state, canonical action-space labels, video alignment
semantics, large-batch partitioning, and migration of legacy recording roots
remain owned by their existing components or later phases. Read-only access to
pre-existing artifacts alone was rejected because recording and inspection need
one durable lifecycle boundary. Owning all future dataset storage was rejected
because it couples operational capture to Phase 9 scale concerns. Source:
user-approved Issue #34 scope revision, 2026-10-01.

### D024 — accepted — Run bundles use SQLite and include an explicit endless outcome
Run bundles are SQLite databases rather than directory-based JSONL event logs.
SQLite is selected because the project will accumulate many oracle and
video-synthesized runs and needs indexed, low-latency queries without coupling
the operational bundle to the later Phase 9 dataset format. The database must
remain inspectable with standard SQLite tooling, use explicit schema and
producer versions, preserve append-only evidence semantics at the application
boundary, and support atomic transactions, integrity records, interrupted
writes, and read-only inspection. Large-scale Phase 9 exports and partitioning
remain separate consumers of the bundle.

The persistence implementation uses SQLAlchemy 2.x for ORM and SQL toolkit
access, with Alembic as the only schema migration system. The repository/API
boundary must not expose ORM sessions or make a competing ORM part of the
implementation.

The lifecycle outcomes are `active`, `interrupted`, `completed`, `endless`,
`won`, `lost`, and `aborted`. `endless` means the run ended without a win, loss,
or abort outcome; it is not an alias for `completed`. Existing evidence is
never rewritten when a lifecycle outcome or external recording evidence is
added. Validation is diagnostic by default and strict on request, and uses
SHA-256 over canonical records and database-level integrity metadata without
repairing evidence. Query results retain the stable status/provenance envelope
(`observed`, `derived`, `missing`, `unknown`, or `unsupported`).

Compatibility is read-only in the initial implementation: adapters may inspect
currently available oracle artifacts but must not silently upgrade unstable
fields. No in-place migration is supported. If conversion is later needed, it
must write a new SQLite bundle that records the source identity and hash,
adapter/version, source references, and field-level diagnostics.

Alternatives considered: a directory of immutable JSONL files was rejected for
query latency and indexing across many runs; a future Phase 9 database was
rejected because operational capture and scale-out dataset concerns have
different lifecycle and migration requirements. This decision changes the
physical representation proposed in Issue #43, but does not change D023's
ownership boundaries or the contracts owned by Issues #13, #15, #21, and #35.
Source: user-approved Issue #43 design revision, 2026-10-01.

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
