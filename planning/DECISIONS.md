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

### D025 — accepted — Required recording policy is a coordination hard gate
When the runner declares recording required, confirmation and valid marker
association must succeed before the user-facing coordination boundary returns
success. Declined, missing, stale, malformed, interrupted, or conflicting
recording evidence returns `blocked` with code `recording_required`; it does
not mutate the run bundle. Optional recording retains explicit non-video
outcomes. This is enforced at the recording-association boundary rather than
adding a new run-bundle lifecycle status, preserving the existing lifecycle
contract. Alternative: treat `required` as advisory notification only; rejected
because it would allow a run to proceed despite the runner's stated policy.
Source: user decision for Issue #46, 2026-10-02.

### D026 — accepted — T2 merge and settlement require independent review evidence
T2 work cannot be merged or marked complete from green CI, a successful merge,
or a lead's own inspection alone. The current PR must contain a fresh-context
`@reviewer` verdict of `holds` and its evidence, with `holds with gaps` and
`refuted` blocking unless the documented exception applies. CI, base/diff,
dependency order, merge, and post-merge settlement remain separate checks.
Already-merged work missing review evidence is reported as a process violation.
This is a narrow enforcement of the existing risk-tiered policy, not a new
review tier or architecture. Alternative: trust the merge result and CI;
rejected because Issue #69 demonstrated that this permits completion claims
without the required independent evidence. Source: Issue #69 and the T2 gate
in `planning/agent-workflow.md`, informed by GitHub protected-branch status and
review semantics and agent-harness guidance from Anthropic and OpenAI.

### D027 — accepted — Worker-owned worktree state must be settled in the PR
Workers must not hand off or complete with worker-created leftovers in the
worktree. Every owned change, including handoff artifacts, belongs in the PR;
temporary and generated files must be removed. Unrelated pre-existing changes
are preserved and explicitly excluded rather than deleted. Alternative: leave
local leftovers for the next worker; rejected because it makes ownership and
review scope ambiguous and can hide incomplete work. Source: Issue #69
follow-up request and the handoff gate in `planning/agent-workflow.md`.

### D028 — accepted — Deliver integrated slices with progressive gates and simpler completion records
The next delivery sequence is a reliable, inspectable recorded run, a reviewed
evaluation slice, and a small measured video-only reconstruction. Define and
approve each slice's evaluation criteria before scoring held-out results; Phase
0 need not establish numeric thresholds for every future phase before the first
reconstruction pilot. This changes gate sequencing, not the requirement to
report provenance, uncertainty, coverage, and independent evaluation evidence.

GitHub is authoritative for live completion state. Eliminate mandatory
settlement-only PRs and mandatory allocation of new four-letter issue tags;
existing tags remain valid references. Repository handoffs preserve the context
needed to resume unfinished work rather than continuously mirroring merge state.
Implementation and review evidence remain required; post-merge results belong
on the existing issue or PR.

Implement these changes in one bounded workflow/roadmap reconciliation, then
prioritize capture reliability and the recorded-run inspection milestone.
Alternatives: retain all-phase threshold prerequisites and mirrored completion
records, or add more orchestration; rejected because the retrospective found
unresolved integration gaps and repeated bookkeeping-only changes. CI changes
and transport redesign still require their own explicit scope and approval.
Source: user approved all three decisions requested in
`planning/PRODUCTION_RETROSPECTIVE_2026-10-02.md`, 2026-10-02. The detailed
workflow, roadmap and issue text must be reconciled in the implementation step.

D028 supersedes conflicting mandatory tag allocation and post-merge repository
completion-record requirements. D026's independent review and separate CI/base/
dependency/merge checks remain; post-merge evidence is recorded on the same PR or
issue. D027's owned-change and publication accounting remains unchanged, including
checkpoints for unfinished work. No unpublished-work exception is implied.

### D029 — accepted — Oracle file IPC uses durable per-request queue files

Replace the overwriteable snapshot singleton with uniquely named per-run request
files. The producer publishes each complete JSON request by writing a temporary
file and renaming it into the queue; request IDs restart within each run and all
deduplication uses `(run_id, request_id)`. The consumer persists the step and
session count before acknowledging by removing the queued request. If it crashes
before removal, restart replays the file against persisted request identity and
does not append a second row. The producer writes a per-run end signal with the
highest successfully published request ID. The consumer retains that signal
until all IDs through the watermark are durable, then persists the terminal
outcome. Missing IDs remain incomplete and diagnosed; the consumer must not
finalize merely because the queue is momentarily empty. Producer-side write
failures remain explicit capture diagnostics and do not block game callbacks.

This is at-least-once file delivery with idempotent consumer persistence, not an
exactly-once claim. Legacy singleton inputs remain readable with an explicit
unwatermarked/incomplete diagnostic; they cannot satisfy queue completeness.
Alternatives: retain the single slot and defer out-of-order completeness (rejected
because a delayed consumer can lose the terminal request), or add only a terminal
watermark (rejected because it detects but cannot preserve an overwritten event).
No database, new runtime dependency, or unbounded wait in the game is introduced.
Source: user approval during Issue #81 on 2026-10-02.

### D030 — accepted — Required `check` CI runs focused app tests for #81 paths

Keep the existing required status context `check`. Extend the planning-check
workflow's path filter to run for the #81 Python recorder, bundle-inspection,
producer-contract test, their focused tests, and their existing
dependency/configuration paths. Install
Python 3.11, project runtime dependencies, and pytest, then run the focused
recorder, producer-contract, and inspection tests together with existing
issue-tag and planning checks.
This makes the required check applicable to the current implementation without
changing branch protection. The full test suite and class-ID generator remain
unverified by clean-checkout CI because the vendored class-map gitlink has no
`.gitmodules` URL and the two class-map tests fail in a clean worktree. Do not
skip or mask them; publishing the approved class-map source or restoring pinned
submodule retrieval remains a separate user-authorized input decision. The
focused CI scope must be described accurately and expanded when that input is
resolved. Alternative: run the whole suite while silently ignoring class-map
failures (rejected because it conceals missing test inputs). Source: user
approval during Issue #81 on 2026-10-02; clean worktree reproduced the missing
CSV on the same date.

### D031 — accepted — `/work` continues through acceptance with prepared human checkpoints

The assigned issue's acceptance list is the unit of `/work`; the lead continues
in-scope implementation, review, blocker remediation, required validation and
integration until merged, or until one precise human/external action blocks the
remaining work. A partial slice, green focused suite, review verdict, or status
summary is not completion. Genuine context exhaustion checkpoints and resumes
the same issue and does not waive D027 publication accounting.

Before asking for live recording input, the lead follows the established run
procedure and completes safe, authorized producer/runtime/OBS-configuration/path/
smoke/bridge preparation. User input is minimized and requested only for the
remaining human action. The post-capture D025 terminal association confirmation
remains separate and mandatory for required recording. New independent work is
duplicate-checked, bounded, and gets reviewer critique before it is presented as
ready; this does not create a new universal approval tier. The production lead
has no fixed OpenCode `steps` ceiling because reaching it forces a text-only
response; read-only reviewer/explorer limits and genuine context checkpoints
remain. No CI, permission, deployment, producer protocol, or human-control
authority is broadened.

Alternatives: stop after individual PR slices and ask the user to re-prompt, or
retain a fixed lead iteration cap; rejected because both create avoidable early
stops before issue acceptance. Source: user's direct `/work` continuation and
recording-preparation requirements, recorded in
`https://github.com/drobotcamo/balatro_showman/issues/104`; OpenCode Agents
documentation, “Max steps,” https://opencode.ai/docs/agents/#max-steps.

### D032 — accepted — Review blocks on material acceptance gaps, not every limit

For tier-required independent review, the lead supplies the agreed acceptance,
exclusions, reviewed base/head, checks and inspectable evidence locations. The
read-only reviewer verifies independently and ties blockers to a failed required
claim, introduced material defect or missing proof needed for acceptance. A
review can return `holds` with nonblocking limits; `holds with gaps` remains
blocking for material gaps under D026. Implementation changes require
current-diff review, preferably by resuming the same reviewer. The lead resolves
in-scope blockers without routine user pauses; only the user may accept a material
exception. No new role, skill, CI rule or approval tier is added.

Alternative: require a new review round or user disposition for every uncertainty
or optional suggestion. Rejected because PRs #102, #105 and #106 needed evidence
reconciliation after review without a code defect; #93 and #94 show why review of
actual corrections must remain. Source: user approval for Issue #109 after review
of 30 recent PRs; Google Engineering Practices, “The Standard of Code Review”
and “How to write code review comments”; Anthropic, “Building effective agents.”

### D033 — accepted — Issue #107 intake is unattended and incomplete capture is explicit

RunBundle intake from the file-IPC bridge is hands-off: it imports after durable
terminal storage and an accepted producer watermark, without a per-run
confirm/reject/defer prompt or persisted verification result. The user's live
Balatro smoke run is a one-time acceptance check for this integration. The
existing Issue #46 recording-association operation remains separate and is not
called by automatic intake.

When a user cleanly ends capture without a producer terminal outcome, the bridge
records terminal lifecycle status `incomplete` with no outcome. This is distinct
from `interrupted`, which remains resumable. A process crash leaves the durable
session active and recoverable; it does not infer that capture ended. Alternatives:
the initially misread per-run confirmation checkpoint was rejected by the user;
reusing `interrupted` for cleanly ended capture was rejected because it implies
resumability. Source: user clarification and approval during Issue #107 on
2026-10-03, recorded at
`https://github.com/drobotcamo/balatro_showman/issues/107#issuecomment-5965862714`.

### D034 — accepted — First-slice held-out evaluation criteria are frozen before collection

For the selected Small Blind/first-shop slice, exact categorical and numeric
accuracy must have a lower 95% confidence bound clustered by source recording of
at least 0.95. Normalized OCR exact-field accuracy has the same lower bound and
normalized character error rate has an upper bound of 0.02. When boxes are scored,
match one-to-one by class/zone at IoU 0.50, with per-family precision and recall
lower bounds of 0.90. Prediction coverage has a lower bound of 0.90 and abstention
an upper bound of 0.10, reported separately by field/stratum.

Held-out support requires 20 independent recordings overall and, for each scored
stratum, at least five contributing recordings and 100 eligible opportunities.
Under-support results are descriptive/inconclusive, never a pass. A state label
uses its target frame only; transition labels may use same-run context up to 2.5
seconds on either side with frame IDs recorded, without future-frame rewriting or
carry-forward. The first-shop slice requires at least one affordable completed
purchase with a visible result; if none is possible, record the constraint and
mark the stage incomplete.

This decision applies only to the first slice. It does not authorize a particular
held-out source set, claim any system meets a threshold, or resolve future phase
criteria. Alternative considered: one aggregate score and frame-level support;
rejected because it hides family failures and overstates evidence from correlated
frames. Source: explicit user approval in Issue #79 comment
https://github.com/drobotcamo/balatro_showman/issues/79#issuecomment-5971771156;
frozen protocol `planning/FIRST_SLICE_PROTOCOL_V2.md`.

### D035 — accepted — First-slice recoverability remains field- and condition-specific

The reviewed seven-frame pilot supports conditional recoverability only for the
named clear page/control/OCR samples and the Juggler identity in the reviewed
purchase sequence. Shop-entry page identity, the full shop inventory, cropped
hand-card identity/attributes and rendered timestamp alignment remain unmeasured.
No field is declared globally unrecoverable, and no reducer/oracle boundary
changes. Unknowns remain unknown; a future unsupported field or unreviewed
condition cannot inherit a positive result.

Alternative considered: resolve Q04 globally from this recording; rejected because
one correlated recording, seven frames and unverified alignment do not establish
general recoverability. Source: user approval in Issue #79 comment
https://github.com/drobotcamo/balatro_showman/issues/79#issuecomment-5971771156;
external pilot report and manifest referenced by the issue. Q04 remains open for
other conditions and phases.

### D036 — accepted — Present operational evidence tooling as Showman Capture

Balatro Showman remains the video-reconstruction project. Its operational
recording/storage/inspection capability is presented as Showman Capture, with
Recorder, Run Store and Inspector surfaces. A task-oriented `python -m showman`
entrypoint delegates to existing interfaces, retains their package/schema names,
and provides a labeled synthetic onboarding path. Documentation prioritizes
future agents: vocabulary, task instructions, exact API/result meanings, and
verification come before implementation history.

The user selected this name, documentation plus runnable onboarding plus a
unified CLI, and an agent-first audience on 2026-10-03 in this branding session.
Alternatives were one project name without a sub-brand, deferred naming, and
documentation alone. This is presentation and additive access, not a change to
storage, lifecycle, reconstruction semantics, evaluation thresholds, or phase
acceptance. Canonical product documentation: `docs/capture/README.md`.

## Open Questions

- **Q01** — Which exact Balatro version and mod configuration define the
  initial ontology?
- **Q02** — Which game assets can be legally and technically sourced for
  redistribution? Bounded disposition for the current pilot and future
  unresolved legacy artifacts: `user-supplied`; no such artifacts are
  redistributed by this repository. Artifact-specific evidence and
  compatibility review remain required for every consuming slice.
- **Q03** — Which criteria, thresholds, minimum support and uncertainty rules
  does each applicable phase/slice protocol require before held-out evaluation?
  The selected first slice is frozen by D034; all other applicable scopes remain
  open.
- **Q04** — Which visible state cannot be recovered reliably from video alone?
  D035 records first-slice field/condition findings only; the global and other
  phase question remains open.
- **Q05** — Which event labels can be inferred confidently without
  player-input logs, and what oracle agreement rate is required before they
  are trusted?
- **Q06** — How is confidence propagated from detection/OCR through
  composition into event confidence?
