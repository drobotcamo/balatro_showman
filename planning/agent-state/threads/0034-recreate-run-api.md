# Work Thread
Updated: 2026-09-30
Issue: #34
PR: none
Owner: unassigned
Branch: none
Worktree: none
Objective: Design a read-only, terminal-callable observed-run reconstruction API for agent questions about recorded Balatro runs.
Status: planned
Scope: API/tool contract, readiness assessment against Phase 0 ground-truth work, and implementation handoff. Video capture, video alignment, recording consolidation, durable storage technology, and deterministic engine replay are out of scope.
Dependencies: #11 pinned-revision capture and Phase 0 gate; #13 canonical action labels and target resolution; #15 step identity and video-frame alignment; #21 persistent-state fields and engine legal actions.
Completed: User approved separating recreate-run design from video/recording consolidation; observed-run reconstruction only; storage technology deferred; JSON-in/JSON-out CLI backed by reusable Python functions. GitHub Issue #34 created. Existing issue scope and dependencies are recorded in the Issue body.
Next: Inspect the current active run schemas and Phase 0 contracts. Specify tool names, parameters, return shapes, provenance, unknown/error behavior, and a non-freezing prototype boundary. Use the result to prepare an implementation issue or sub-issue only after the contract is reviewable.
Decisions: The initial capability interprets existing observed run bundles. It does not rerun Balatro or claim deterministic replay. The preferred interface is commands such as `python -m recreate_run list`, `summary --run`, `step --run --request-id`, and `find --run ...`, emitting machine-readable JSON. Python functions remain the reusable implementation surface. Storage technology and recording-root consolidation are deferred. The design must not promote unstable Phase 0 fields into a permanent public contract.
Risks: Existing persisted runs are pre- or intermediate-revision; video references and alignment are incomplete; the current run format may change before the Phase 0 gate closes. A prototype must remain read-only, schema-version aware, and explicit about missing or unsupported evidence.
Validation: `py -3 planning\\check_contracts.py` passed (`planning contracts OK`). Future contract examples must use at least one available oracle run; implementation must verify no run artifact mutation.
