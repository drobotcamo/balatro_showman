# Balatro Showman Planning

Two complementary delivery tracks produce trustworthy run data:

- Deep data: evidence-linked state, mechanics effects and run-dynamics analytics,
  beginning with a validated Dagger slice (#121–#127).
- Visual data: synthetic scenes/glyphs and video-only observations that improve
  and broaden those same outputs.

Observed evidence, derived state/effects and independent engine references remain
distinct. Analysis is a product now; learning is an optional downstream consumer.

## Start Here

1. `ROADMAP.md`: small delivery outcomes, owners, prerequisites and exact next action.
2. `ARCHITECTURE.md`: shared interfaces, provenance and reference isolation.
3. Relevant `components/` contract and live issue/PR; checkpoints in
   `agent-state/threads/` supply extra context, not current completion state.
4. `agent-workflow.md`: implementation, approval, publication and handoff rules.

## Evidence And Operations

| Need | Canonical reference |
| --- | --- |
| Capture / inspect / export | `../docs/capture/README.md`, `../docs/capture/reference.md` |
| First-slice criteria and annotation | `FIRST_SLICE_PROTOCOL_V2.md`, `FIRST_SLICE_ANNOTATION.md`; #82 owns live evaluation |
| Development history | `FIRST_SLICE_PROTOCOL_V1.md`, `FIRST_SLICE_PILOT_REVIEW.md` |
| Runtime and oracle | `BALATRO_RUNTIME.md`, `BRIDGE_SPIKE.md`, `ORACLE_DATA_REVIEW.md` |
| Run-bundle operations/storage | `RUN_BUNDLE_OPERATIONS.md`, `RUN_BUNDLE_STORAGE.md` |
| Provenance and reducer boundary | `PHASE0_INVENTORY.md`, `PERSISTENT_STATE_OWNERSHIP.md` |
| Decisions, findings and commands | `DECISIONS.md`, `LEARNINGS.md`, `TOOLING.md` |
| Mechanics interface, Dagger source findings and checks | `RUN_MECHANICS_DESIGN.md`, `dagger_sell_value.md`, `schemas/run_mechanics_v0_1.schema.json`, `mechanics_contract_check.py`, `../run_mechanics/dagger.py` |
| #127 video-like Dagger inputs | `VIDEO_LIKE_DAGGER_PROTOCOL_V1.md`, `../tests/fixtures/video_like/dagger_v1.json`, `../run_mechanics/video_like.py` |

Component contracts cover vocabulary/geometry, visual generation/inference,
composition/reduction/events, evidence/storage and analytics. #122 publishes the
approved initial mechanics interface and examples in `RUN_MECHANICS_DESIGN.md`;
D039 approves Dagger order for the pinned installed stack. #124 owns the bounded
Dagger sell-value constructor, reducer and round analytics; broader staged
mechanics remain open as recorded there.
Workflow migration and retrospective documents are historical references, not a
second current execution plan.

Status: `building`. Capture, inspection, annotation export and the viewer exist;
active mechanics and visual inference do not. #82's seven-frame pilot has no
predictions and unverified alignment. #115 owns Continue identity/live acceptance.
No broad phase pass or reconstruction accuracy follows from this planning revision.

Use `planned`, `designing`, `building`, `validated`, `blocked` or `retired` in
contracts. Run `python planning/check_contracts.py` for mechanical consistency;
it does not validate semantics, measured quality or gate thresholds. New slice
protocols require approval before held-out scoring; D034 remains frozen.
