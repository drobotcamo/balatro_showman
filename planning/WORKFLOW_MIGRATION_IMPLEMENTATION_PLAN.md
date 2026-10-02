# Production-focused workflow migration: lead implementation plan

Prepared: 2026-10-02.
Authority: user-approved D028 in `planning/DECISIONS.md`, followed by the user's
request for this detailed delegated implementation plan. This file specifies
the migration; it is not evidence that the migration or a product gate passed.

## 1. Assignment and reading order

Implement one bounded reconciliation of the current workflow, roadmap, templates,
agent instructions, and their checks. Make the next production outcome a reliable,
inspectable recorded run. Use bounded subagents for parallel research and fresh
review, with one lead owning all implementation and integration.

Read, in order:

1. `AGENTS.md`, this plan, and D028. Read the current workflow to understand the
   rules being replaced, rather than treating every old rule as a new blocker.
2. `planning/PRODUCTION_RETROSPECTIVE_2026-10-02.md`: findings, historical evidence,
   research, limits, and PR accounting. This is the companion evidence report,
   not a second task queue. This plan carries forward its actionable insights.
3. `planning/agent-state/threads/0000-production-retrospective.md`: local handoff.
4. `planning/agent-workflow.md`, `planning/ROADMAP.md`, relevant component contracts,
   and current issue/branch/PR state. Read additional files by assignment below.
5. Load the OpenCode customization skill when actually editing `.opencode/` or
   `opencode.json`; use deslop for substantial prose. Avoid reloading skills
   already supplied in the session.

Start directly as the lead using `planning/LEAD_WORKFLOW_MIGRATION_PROMPT.md`.
Do not route through an orchestration session simply to be assigned this already
specified task. `/work` is not required; its present text still encodes several
rules this migration removes.

### Outcome

An agent given a ready production issue can implement, validate, obtain independent
review, integrate, and record completion without reconstructing closed portfolio
history, allocating a tag, or opening a second PR just to settle a baton.

The deliverable is changed, consistent instructions plus executable checks and
scenario evidence, not another recommendation document. The existing retrospective
and this plan are inputs. Do not write a second retrospective before implementing.

### Scope and stop boundary

This invocation completes the workflow migration and leaves the existing production
queue actionable. It may reproduce existing defects and prepare their acceptance
cases, but does not mix capture/storage implementation into the workflow PR.
The first production milestone then exercises the new workflow in its own bounded
work item. Do not claim that migration completion means production delivery.

One issue and one PR should own this migration. Do not create separate issues for
design, research, templates, tests, review, integration or settlement. Split only
if an independently necessary external decision cannot be resolved within scope;
record it on the existing issue first. Small coherent production PRs remain useful.

## 2. Approval and permission boundaries

The user explicitly approved all three choices recorded in D028:

| Approved direction | Implementation consequence |
| --- | --- |
| Progressive gates and a thin-slice delivery sequence | Stop requiring all Phase 1–10 thresholds before the first reconstruction pilot; define each evaluation boundary before held-out scoring. |
| GitHub-authoritative completion; no mandatory settlement-only PRs or new tags | Remove those obligations from every current entrypoint and validator; retain historical identifiers and evidence. |
| Recorded-run inspector, reviewed evaluation slice, then small measured video-only reconstruction | Reconcile existing #79–#82 and roadmap sequencing around these outputs. |

The follow-up implementation-plan request calls for the compact lead loop, scoped
delegation, and file-level reconciliation described here. Routine edits necessary
to implement those directions do not need repeated approval. Preserve D026's
independent review and D027's owned-change accounting; supersede only conflicting
completion-record requirements explicitly, with a reference to D028.

The following are still separate decisions, not implied authorizations:

- CI workflow triggers, required checks, branch protection, credentials,
  deployment behavior, and permission changes.
- New agent roles, editing subagent permissions, increased delegation depth,
  dependency/model-weight additions, asset promotion or redistribution.
- A queue/spool/acknowledgement transport redesign, hash/schema/lifecycle changes,
  a new converter or ingestion contract, and any other substantive product interface.
- Numeric quality thresholds, selected target fields/pages, supported runtime,
  recording protocol and held-out data policy for a concrete evaluation.
- Destructive worktree cleanup or changes to work owned by someone else.

Respect the host's actual action permissions. The launch prompt requests the normal
branch/commit/PR/merge lifecycle; runtime permission prompts or a lack of credentials
can still block those operations. A policy cannot make unavailable tooling work.
Record the exact blocker and a resumable checkpoint instead of declaring a merge.

## 3. Starting state and preservation

Snapshot at preparation, to be rechecked rather than assumed:

- Checkout: `C:\Users\camgr\Documents\code_projects\balatro_showman`.
- Branch `issue-84-wave`, HEAD `ade4453`; local `origin/master` at `ceb1580`.
  Their tracked content matched at review time; the branch is not a fresh work item.
- Fifteen registered worktrees; this does not mean fifteen active agents.
- No open PRs; open issues #79, #80, #81, #82.
- `does-not-exist.db` was pre-existing and untracked. Preserve and exclude it.
- Review-owned local files/edits to carry into the migration after inspection:
  `planning/DECISIONS.md` (D028), `planning/LEARNINGS.md` (capture finding),
  `planning/PRODUCTION_RETROSPECTIVE_2026-10-02.md`, this plan,
  `planning/LEAD_WORKFLOW_MIGRATION_PROMPT.md`, the planning index link, and
  `planning/agent-state/threads/0000-production-retrospective.md`.

Inspect status, diff, current remote/default branch, worktrees, and relevant GitHub
state before editing. Recheck for another migration issue/PR rather than duplicating
it. Do not attach migration work to closed WAVE work merely because it is checked
out. Use a dedicated migration branch based on the integration branch, normally
`master` here; verify instead of assuming the workflow's generic `main` example.

A new worktree does not contain uncommitted D028 or untracked reports. Transfer
only the inspected, explicitly listed review inputs using safe tools; do not rely
on conversation memory, copy the entire dirty checkout, stash unrelated work,
reset, clean, or force checkout to make the branch transition easy. An in-place
new branch is acceptable only if it preserves all local work and has the intended
base. Explain ownership of carried edits in the PR.

Include approved review inputs with implementation; do not create a preliminary
PR just to settle this handoff. No cleanup campaign over fifteen worktrees is a
prerequisite. Remove none without confirming ownership and obtaining required
permission. Avoid logging private recordings, credentials or external file contents.

## 4. Delegation and ownership

Current configuration already supports the needed staffing:

- `opencode.json` selects `lead` and limits subagent depth to one.
- `.opencode/agents/lead.md` permits `explorer` and `reviewer` tasks only.
- Those agents are read-only and may not delegate further.

Use that configuration. Do not invent implementation-worker roles or broaden
permissions. The user wants useful parallel assistance, not a swarm. Launch A and B
independently where the harness supports concurrency. If calls are synchronous,
run them sequentially without claiming parallelism. C can run while the lead makes
non-overlapping changes. D must be a fresh-context reviewer of the integrated diff.

| Assignment | Agent | Ownership and requested result |
| --- | --- | --- |
| A: instruction and validator map | explorer | Read-only: workflow, agents, commands, skills, templates, tags, checker/tests. Return contradictions, exact paths, compatibility requirements, and recommended edits. |
| B: gates and issue reconciliation | explorer | Read-only: roadmap, Q03/Q04, current evidence and #79–#82. Return an acyclic milestone/dependency plan and draft issue changes with retained criteria and approval gaps. |
| C: production readiness and verification | explorer | Read-only source analysis: application CI gap, class-map reproducibility, capture faults, command examples. Inspect the diagnostic and the lead's execution output; return acceptance cases, evidence limits, and changes requiring approval. No fixture execution, live capture or source edits. |
| D: independent adversarial review | reviewer | Challenge the integrated diff at an identified SHA against D028, this plan, tests, and the workflow scenarios. Return verdict, material gaps, exact references, and remaining uncertainty. |

The lead owns all tracked edits, GitHub issue updates, branch/PR operations, final
test selection, decisions and integration. No subagent can approve policy, waive
review gaps, edit or close issues, merge, promote assets, or mutate live evidence.
The configured explorer prohibits file modification and state-changing commands,
including fixture-writing diagnostics. The lead executes those checks in isolated
approved temporary storage, supplies output to C, and owns scratch cleanup. Do not
reinterpret a task brief as permission to override the configured read-only role.

Each assignment must include: precise question; authoritative input paths; allowed
actions; excluded file/data boundaries; expected output; and a stopping condition.
Require the return format: findings with references, proposed edits, checks/output,
changed files (expected none), unresolved questions. Subagent suggestions are
evidence for the lead, not automatically adopted decisions.

Do not duplicate their investigations. Resume the same task for follow-up. If a
subagent finds a policy conflict, the lead resolves it at the specific boundary
while continuing independent work. Budget research to the migration, not another
55-PR audit. Preserve time/context for integration, tests and fresh review.

### Copyable delegation briefs

**A:** "Read D028, the migration plan sections 5–7, and current workflow/config.
Map every active requirement for new tags, completion batons, portfolio repair,
duplicated review prose and exact-string validators. Return a file-level edit map
and backward-compatibility tests. Read-only; do not edit, allocate tags, alter
permissions, create issues or research production code. Stop when each affected
entrypoint/checker is accounted for."

**B:** "Read the retrospective, D028, roadmap, ground-truth/dataset contracts,
current inventory/oracle review and live #79–#82. Draft milestone-aligned issue
body changes and gate wording. Break protocol/pilot circular dependencies without
claiming broad phase completion. Distinguish existing evidence, stale claims and
unmeasured requirements. Read-only; no GitHub writes, threshold invention or
code implementation. Return changed-scope proposals and actual blockers."

**C:** "Inspect section 12's capture reproducer, application CI, the legacy class-map
input and the documented inspection CLI. The lead will execute fixture-writing
diagnostics and supply output; compare it with source behavior. Return acceptance
cases, source/output references, confidence labels and a narrow proposal for
approval-gated CI/input work. No edits, fixture execution, installs, new dependencies,
game/OBS operations or live-data mutation. Distinguish inspected from executed evidence."

**D:** "Review the integrated migration at <SHA> against D028 and this plan.
Try to refute completion. Check source-of-truth ownership, no settlement recursion,
new numeric issue compatibility, preserved historical aliases/checkpoints,
progressive gates without weakened evidence, unchanged unapproved permissions/CI,
coherent issue updates, and all section 8 scenarios. Verify tests cover behavior
or structure as claimed, not instruction presence sold as agent enforcement.
Return holds/holds with gaps/refuted with actionable references and reviewed SHA."

## 5. Target operating model

### One home for each kind of information

| Information | Authoritative home | What must not be duplicated |
| --- | --- | --- |
| Outcome, priority, acceptance, owner, actual blocker | GitHub issue | Another live task ledger in Markdown |
| Diff, validation, independent verdict, reviewed SHA, merge | PR and CI | Post-merge status in a new repository commit |
| Interfaces, invariants, durable decisions, protocols, evidence references | Repository | Session transcripts or guesses about live issue state |
| Extra context needed to resume unfinished work | Small repository checkpoint | Full issue body, full PR history, continuously current completion status |

A normal completed task does not require a new checkpoint. If a checkpoint was
committed before merge, it remains accurate as an as-of record. GitHub can show
that the work completed later. The next agent checks that state before resuming;
the difference is not automatically corruption, noncompliance or a repair task.

Keep old full-format thread files readable. For new unfinished-work checkpoints,
use a compatible compact representation: title plus `Updated`, `Issue`, `PR`,
`Branch`, `Worktree`, `Objective`, `Validation`, `Risks` and `Next`. `Validation`
records the checked commit/revision and meaningful results; `Risks` records the
blocker and ownership exclusions. Extra historical fields remain accepted.
If a task has no issue/PR yet, say `none`; never invent identifiers or success.

These records are not locks. GitHub/branch/worktree evidence still determines
ownership. Context exhaustion, an external decision, unavailable permission or
missing live evidence can justify a verified handoff; finishing code does not
justify manufacturing a blocker to avoid review/integration.

### Lead loop

1. Select the agreed ready outcome; inspect relevant working and issue state.
2. State observable acceptance, scope and intended verification.
3. Implement, using bounded independent research when it removes uncertainty.
4. Run relevant checks and obtain fresh review of the current implementation.
5. Integrate when authorized and record post-merge evidence on the same PR/issue.
6. If blocked, retain one factual checkpoint with the exact requested action.

Routine progress does not require permission pauses. A ready task does not need
a full portfolio audit. Use the orchestrator when priority, ownership or dependency
conflicts genuinely require it. Preserve its read-mostly authority; do not let it
become a second implementation owner. Stop speculative portfolio/gate skill
expansion during the first two production milestones.

One active production outcome is the default. Parallel research/review inside
that outcome is encouraged; independent implementation concurrency must have
distinct ownership and independently testable acceptance. Do not measure success
by worker count. A blocked capture should prompt its exact human request, not a
new workflow feature to keep agents occupied.

### Review and completion evidence

Record once on the PR: reviewer identity/task reference, reviewed commit SHA,
verdict, checks and outputs, material findings/disposition, and remaining limits.
Do not paste entire tool transcripts. Record user-approved exceptions explicitly.
Changing implementation after review requires review of the changed diff/current
SHA before merge. Prevent last-minute baton edits from silently invalidating the
review; include intended tracked artifacts before the final reviewed commit.

An owner-posted comment can preserve an actual fresh-context review; an empty
native GitHub `reviews` array alone cannot disprove that review. The lead's own
assertion is not a substitute for an independent task/verdict. Do not reopen
accepted historical process gaps without new substantive evidence.

Preserve risk-proportionate review tiers. Resolve the current contradiction
between T0 self-merge after checks and the universal "not sole approver" wording
by stating clearly that the independent-review rule applies where the tier requires
it; do not add reviews to every T0 status change. Use a fresh reviewer for this
cross-cutting migration even though it includes prose.

Review, required CI, correct base, dependency order and verified merge are separate
facts. Do not claim prose tests mechanically enforce these GitHub actions. Keep
the existing required checks and permissions unless a specific change is approved.
If action permission is missing, report a verified blocked handoff, not completion.

### Tags, issues and work units

New numeric issue references and numeric checkpoint filenames are normal. Preserve
the eight historical tag mappings and resolution of tagged paths. No allocator
availability should block new work. The optional allocation utility may remain
for compatibility; do not delete it while CI still invokes its `check` subcommand.

Issue template: observable user action and artifact; acceptance command/protocol;
scope boundary; owner; actual prerequisite or decision. Research/design is useful
when it retires a named uncertainty enabling production. Split work only when it
is independently useful/reviewable or externally blocked, not for each workflow
stage. Do not use small-PR counts as a reason to combine unrelated code changes.

## 6. File-level migration checklist

Read each file before editing; line references in the retrospective are historical.
Update policy and the tests that consume it in the same coherent diff.

| File(s) | Required treatment |
| --- | --- |
| `AGENTS.md` | Keep correctness/provenance/approval principles and entrypoint links. Qualify unconditional work-thread updates: unfinished-work checkpoints, not every completion. Avoid repeating the lead loop. |
| `planning/agent-workflow.md` | Canonical definition of source-of-truth ownership, short lead loop, proportionate review, historical checkpoints, numeric issues, and real escalation. Remove post-merge baton obligations and routine settlement repairs. |
| `planning/DECISIONS.md` | Retain D028 and history. Reconcile Q03 with progressive gates. Explicitly note any superseded conflicting completion-record requirements; preserve independent review and owned-change hygiene. Do not fabricate resolution of Q02/Q04. |
| `planning/ROADMAP.md` | Add the agreed integrated milestone sequence; remove the all-future-threshold prerequisite and make threshold ownership/timing explicit. Preserve broad component gates/statuses and links. |
| `planning/README.md` | Concise current entrypoint/capability summary, correct protocol timing and link to this migration. No copied backlog. |
| `planning/ARCHITECTURE.md` | Reconcile only if sequencing language conflicts with approved slices. Preserve oracle/video separation and active/legacy boundary. Correct or qualify "perfect" oracle language if needed to reflect established limitations, not a new interface. |
| `.opencode/agents/lead.md` | Thin role adapter to canonical workflow. Preserve existing task permissions. Remove repeated settlement and historical-audit instructions. |
| `.opencode/command/work.md` | Thin entrypoint to lead/canonical workflow. No duplicate merge/baton checklist with different semantics. |
| `.opencode/agents/orchestrator.md`, `.opencode/command/orchestrate.md` | Historical-checkpoint-aware audit; no default repair of closed batons; use when work selection is actually unresolved. Retain non-implementation authority. |
| `.opencode/skill/portfolio-state/SKILL.md` | Remove tag allocation as prerequisite and obsolete allocator-blocker scenario. Preserve duplicate checking, audit-only behavior and verification. Do not expand the skill. |
| `.opencode/command/handoff.md`, `.opencode/command/resume.md` | Apply compact historical checkpoint semantics and live-state recheck. Current commands route to `build`; make routing consistent with the accountable lead if configuration guidance supports it. Do not broaden permissions or add roles to achieve this. |
| `.opencode/command/verify.md`, `.opencode/agents/reviewer.md` | Keep read-only adversarial role; include reviewed revision and evidence. No authority to adopt policies or silently waive material gaps. |
| `.opencode/skill/project-memory/SKILL.md`, `planning/agent-state/README.md` | Record reusable findings/decisions once; checkpoints only for unfinished work. Explain old full-format/new compact compatibility. |
| `.github/PULL_REQUEST_TEMPLATE.md` | Optional historical tags; delivered behavior, validation, reviewed SHA and limits. Conditional checkpoint update, no second settlement artifact. |
| `.github/ISSUE_TEMPLATE/work-item.md` | Minimal outcome, acceptance, owner and blocker. Do not recreate the workflow in the template. |
| `planning/issue-tags.md`, `planning/issue-tags.json`, `tools/issue_tags.py` | Rewrite mandatory-allocation prose; preserve existing mappings and check behavior. Avoid gratuitous allocator rewrites. |
| `planning/check_contracts.py` | Preserve meaningful structural checks; remove exact review phrasing/line-break assertions and mandatory allocator markers. Accept historical full/new compact numeric/tagged checkpoints. Test invalid inputs as well as valid compatibility cases. |
| `tests/test_portfolio_state_skill.py` | Remove obsolete prose assertions or relabel remaining ones as structural. Do not replace old mandatory phrases with new phrases and call it behavioral validation. |
| `.opencode/skill/gate-facilitator/SKILL.md` and `fixtures/cases.json` | Derive required criteria from the applicable versioned protocol, not an unconditional all-Phase-1–10 row. Use named criteria/protocol identity rather than unexplained positional rows where fixtures change. Preserve refusal on missing evidence/protocol/human acceptance. |
| `planning/PHASE0_INVENTORY.md`, `planning/ORACLE_DATA_REVIEW.md` | Reconcile current summary versus historical dated evidence; inventory already shipped, old captures have different revisions/coverage. Do not erase source findings or invent current live acceptance. |
| `planning/components/ground-truth.md`, `dataset.md`, `detection.md`, `synthetic-data.md`, and other directly affected contracts | Update approved protocol timing/ownership references only where needed. Keep leakage controls, coordinate semantics, observed/inferred distinction and broad acceptance obligations. |
| `.github/workflows/planning-check.yml`, `opencode.json` | Inspect but preserve unapproved CI/permission policy. Produce a concrete approval request if changes are necessary; do not quietly edit them under a documentation tier. |

Do not rewrite all closed threads, renumber issues, normalize the entire decisions
history, delete existing skills to reduce counts, or reformat unrelated production
code. Documentation length is not the goal: remove obligations and contradictions,
not essential evidence. This extensive implementation plan is a one-time reference,
not a new mandatory full read for every future production task.

## 7. Roadmap and issue reconciliation

Use the existing issues and keep their useful acceptance criteria. Fetch current
bodies/comments before updating; preserve new user work. Update bodies with actual
line breaks via inspected body files, not escaped newline strings. Summarize the
supersession once; do not append mutually contradictory instructions indefinitely.

| Issue | New role | Retain | Remove or defer |
| --- | --- | --- | --- |
| #81 | First production outcome: reliable, inspectable recorded run | Pinned producer/runtime, audited final run, recording provenance, human verification and explicit limits | Blanket prohibition on the recorder repairs needed for this outcome; adjust explicitly before code work. Do not add full detector/reducer development. |
| #79 | Evaluation protocol for the first supported slice | Units, source/run splits, matching, temporal context, unknowns, minimum support, uncertainty, recoverability and user-approved criteria | Requirement to settle every future field/phase threshold before the pilot. Broader matrix/metrics remain staged obligations. |
| #82 | Minimum annotation/review/export needed for that slice | Coordinate transforms, deterministic manifest, independent QA, diagnostics and leakage controls | Comprehensive all-field tooling before a bounded pilot. Avoid a permanent labeling platform project. |
| #80 | Eligibility of dependencies actually needed by the selected slice | Artifact-specific provenance, distinction between code/assets/weights/data licenses, user decision | Reviewing/promoting every legacy candidate as a prerequisite to capture or a dependency-free pilot. |

Make real dependency distinctions:

1. Recorder fault tests can run with fixtures before a live session or full protocol.
2. A declared capture/synchronization check needs agreed runtime, recording format
   and tolerance, not every downstream detector threshold.
3. Draft #79's evaluation units and development-pilot protocol before tooling.
4. #82's minimal tool and development pilot inform reasonable supported scope.
5. Finalize/version evaluation criteria before collecting/scoring the declared
   held-out evaluation; do not tune thresholds against the held-out result.
6. #80 blocks only use of an unresolved artifact; missing optional candidates do
   not block unrelated work. Verify the class-map dependency before calling it optional.

Keep capture existence, synchronization accuracy, oracle semantic correctness,
evaluation readiness and broad phase completion distinct. Allow cross-component
slices without changing all phase statuses to validated. Unknown or inadequate
support cannot pass. Do not call the now-smaller pilot statistically generalizable.

At migration completion, #81 must identify its owner/next action and verification
plan. #79–#82 should no longer form a practical protocol/tooling prerequisite loop.
Record remaining human decisions explicitly rather than inventing thresholds.

## 8. Migration verification and acceptance

### Baseline already observed, not promised in a new environment

```text
python -m pytest -q
91 passed, 15 subtests passed in 6.02s
python planning/check_contracts.py
planning contracts OK
python tools/issue_tags.py check
valid: 8 issue tag(s)
git diff --check
no whitespace errors
```

The application suite passed in the populated local checkout. This is not a
fresh-checkout guarantee. Existing GitHub CI runs tag/planning checks only, with
path filters excluding application-only edits and several agent/template paths.
Required status was `check`; native required PR reviews were absent. Reverify
before relying on these facts. Do not infer that green historical CI ran pytest.

### Executable checks

- Run the narrow affected tests while changing validators/instructions, then run
  the existing suite once against the integrated result. Do not repeat a broad
  suite after unchanged results without a reason.
- Run `python planning/check_contracts.py`, `python tools/issue_tags.py check`,
  and `git diff --check` on the final diff. Check new files too; ordinary git diff
  omits untracked files until they are staged or inspected separately.
- Add meaningful validator tests: new numeric issue/checkpoint with no tag passes;
  valid old tagged and full-format checkpoints pass; duplicate/invalid registry
  mappings and missing essential checkpoint data fail; broken references fail.
- Keep decision-ID uniqueness/order, open-question linkage, component ownership,
  required sections/status, and real configuration/reference checks.
- Verify command routing and role permission boundaries structurally using existing
  parsing capabilities; do not add a dependency merely to test a few frontmatters.
- Check gate fixtures for protocol/criterion identity and refusal cases. JSON
  examples and string assertions do not execute an agent or prove determinism.

### Scenario acceptance, reviewed independently

For each scenario, record expected next action, evidence home, allowed mutation
and stopping condition. Label a tabletop walkthrough as such. Where possible
execute fixture-backed checks of the supporting tooling; actual next production
work is the behavioral trial. Do not fake merges, reviews or human confirmations.

| Scenario | Required behavior |
| --- | --- |
| Ready production issue | Lead starts relevant inspection/implementation without mandatory portfolio reconstruction or tag allocation. |
| Normal successful task | Review and checks precede integration; completion recorded on existing PR/issue; zero post-merge repository edits required. |
| Unfinished work/context boundary | One concise factual checkpoint identifies checked revision, worktree, results, blocker and next action. |
| Historical pre-merge baton; PR now merged | Agent recognizes historical context and live completion; no repair PR or reopening solely for stale metadata. |
| Numeric-only new issue | All relevant templates, workflow and checks accept it without registry changes. |
| Existing four-letter tag | References and historical checkpoint still resolve; registry integrity enforced. |
| Material implementation change after review | Obtain review of current diff/SHA; stale verdict cannot satisfy merge. |
| Review present as PR comment, native reviews empty | Inspect task/verdict/SHA evidence; neither automatically reject nor accept solely on native review presence. |
| Required user recording confirmation missing | Stop before association mutation, present exact choices/request, preserve evidence; no fabricated recording success. |
| No applicable/required CI result | Inspect configuration/protection, report exact gap; no invented pass or unapproved policy edit. |
| Gate protocol incomplete, evidence stale, or human acceptance absent | Refuse gate pass; identify actual criterion/decision, without restoring all-future-phase prerequisite. |
| Valid protocol for a different slice or revision | Reject it as inapplicable; select the actual approved protocol before evaluating named criteria. |
| Commit, push or PR publication unavailable | Preserve owned work and record exact unpublished paths/revisions and permission failure; request the specific D027 exception or publication action. Do not claim published handoff compliance or completion. |
| Existing unrelated local file | Preserve and exclude; do not delete/stage it to satisfy clean-worktree rhetoric. |

### Completion checklist

- [ ] D028 is carried into the branch and reflected consistently in live entrypoints.
- [ ] No normal completion path requires new tag allocation or settlement-only PR.
- [ ] Historical records and tag mappings remain valid without bulk rewrites.
- [ ] Current gate/issue dependencies enable the agreed first production slice.
- [ ] Review evidence is defined once and tied to the reviewed revision.
- [ ] Validator coverage matches claimed structural behavior; obsolete text tests removed.
- [ ] Scenarios reviewed with explicit evidence and limitations.
- [ ] Application test/input/CI gaps are accurately reported with bounded next actions.
- [ ] Independent reviewer finds no unaccepted material gaps in the integrated diff.
- [ ] Required current checks, base, dependency and merge facts verified when publishing is authorized.
- [ ] Completion posted on the same PR/issue; no settlement follow-up required.

Clean-checkout application testing is a production priority, but adding CI is not
pre-approved. Migration acceptance requires a verified diagnosis and exact approval
request for any reserved change, not pretending application CI exists or indefinitely
blocking approved instruction changes while waiting on it. If approved during this
work, implement the narrowly agreed CI/input changes with suitable verification;
otherwise retain them as an explicit production dependency, not a hidden omission.

## 9. Integration, publication and handoff

The supplied launch prompt requests creation/update of the bounded migration issue,
branch, commit, PR and merge after required evidence. Honor actual permissions and
repository policies. Inspect status/diff/recent log before committing; stage only
intended files. Do not force push, amend without authorization or bypass hooks.

Use `gh` for GitHub changes and register the implementation PR with the thread via
the available PR-link tool immediately after opening or beginning work on it.
Check thread PR links before finishing. Historical PRs read as evidence are not
implementation PRs and should not be linked indiscriminately.

Include final intended repository artifacts before the last reviewed SHA. After
merge, verify the merge commit and post a concise completion comment on the same
issue/PR: artifact delivered, checks, reviewed SHA/verdict, merge identity, remaining
limits and the next production command/task. Close the issue when criteria are
addressed. Do not change a baton solely to add that merge hash.

If blocked, use one unfinished-work checkpoint and issue/PR update. State exactly
what is missing, what is safe to continue, which files belong to whom, and the next
command. Never claim "complete" for a local diff when requested publication remains
blocked. Conversely, a completed merge does not need a new thread-closing PR.

Publication-blocked handoffs need an explicit D027 disposition. The existing rule
requires owned changes to belong in the PR; D028 does not automatically waive that
requirement when commit, push or PR creation is unavailable. Distinguish accounting
for work from successfully publishing it. Record the last committed SHA, owned
modified/untracked paths, whether anything was staged/committed/pushed, available
patch/checkpoint location, exact failing or denied operation, unrelated exclusions,
validation and concrete recovery action. Commit locally only if authorized; do
not discard unpublished work to manufacture compliance. If GitHub is unavailable,
keep the checkpoint locally and report that it is unpublished.

Request a narrowly scoped user exception or the missing publication action. The
migration may propose a durable blocked-publication exception to D027, but must
obtain explicit approval and record its conditions before adopting it. Until then,
report the unsatisfied publication requirement and preserved recovery state, not
a policy-compliant completed handoff. Continue independent approved work where
possible. This distinguishes a truthful blocker report from a fictitious success.

## 10. Production follow-through: first outcome

This is the next work item, anchored on #81 after its scope is reconciled. Use the
new workflow rather than restarting a portfolio assessment. One lead owns the
usable capture-to-inspection result, even if it lands through multiple useful PRs.

### Recorder acceptance cases

Convert the reproduced failures into executable regression tests before fixes:

1. Restart: persisted records and session counts agree; replayed input does not
   duplicate steps; terminal state is not reset. Define recovery from truncated
   records explicitly and retain evidence of corruption.
2. Malformed/unreadable input: preserve original bytes or quarantine with diagnostic
   provenance; do not silently delete. Distinguish an incomplete writer from stable
   malformed input. Avoid an infinite poison-file retry that prevents progress.
3. Pending snapshot plus run-end: preserve final evidence and terminal outcome
   across both arrival orders, retries and restart. Merely reversing function order
   does not establish correctness for all sequences.
4. Persistence failure: do not mark a request consumed before durable append;
   inject failures around append/session update/ack and verify recovery semantics.
5. Identity: request numbers may recur across producer restarts; the inspected
   Lua counter is process-scoped, not reset by `Game.start_run`. Use `(run_id, request_id)` for
   deduplication/joins; current in-memory maps use request ID alone until run-end.
   Missing/delayed end signals must not conflate different runs.
6. Producer/consumer delay: the single snapshot path and 30 ms coalescing are not
   a queue. Test delayed/stopped consumers and close callbacks; explicitly detect
   gaps/drops and distinguish intended coalescing from unknown missing events.

Choose any protocol redesign through a bounded decision with alternatives,
compatibility, failure semantics and a recommendation. Do not promise exactly-once
delivery just because happy-path tests pass. Preserve recording performance and
laptop practicality; do not block the game indefinitely without an approved design.

### Oracle semantics and lifecycle

- `state_values` contains plausible defaults (deck size/capacities). Missing engine
  reads must not silently become truth in evaluation. Document the affected fields
  and correct/lower claims before using them as a reference.
- `compute_legal_actions` is coarse page/selection logic and includes the recorded
  action. An action being in that list is not independent proof of engine legality
  or mask correctness. Canonical persistent state is intentionally not implemented
  in the producer; do not add a second reducer to make reports look complete.
- Lua snapshots are pre-callback, pre-action. Evaluate rendered correspondence,
  not merely close timestamps. Animations/transitions can be ambiguous.
- Bridge marker attachment currently rewrites all open sessions with the current
  marker; lifetime, run ownership, freshness and finiteness need deliberate checks.
  The separate association API's stronger validation does not automatically protect
  the raw bridge path. Do not overwrite historical association by implication.
- Audit endless-play behavior: producer finalization does not itself prevent later
  emission. Treat this as an investigation, not a reproduced live defect.
- Prefer a checked-in executable Lua fixture harness for high-value extraction/hook
  behavior when the dependency/runtime choice is approved. Existing source-string
  tests and a historical temporary harness are insufficient behavioral evidence.

### Capture-to-inspection integration

The bridge writes `session.json` and `steps.ndjson`; compatibility reading is not a
SQLite converter. Existing SQLite APIs and recording-association functions do not
by themselves form a user-facing recorder. Choose and verify the smallest coherent
operational path before declaring the inspector milestone delivered.

Preserve D024: compatibility is read-only; conversion, if approved, writes a new
bundle with source hashes, adapter version and diagnostics. Do not silently migrate
old evidence or adopt a new storage engine. Fix the documented plain SQLite filename
versus SQLAlchemy URL mismatch, with actual CLI acceptance/error-output checks.
`transitions` and `diff` are explicitly unsupported; either keep that truthful scope
or obtain a separate implementation decision. Do not imply deterministic replay.

Integrity claims need precise scope: aggregate digests cover payload digests, not
all sequence/kind/provenance metadata; finalization is not a fresh payload rehash.
Test metadata tampering and corrupted bytes followed by finalization when touching
this path. Avoid presenting hash validation as semantic correctness or authenticity.

Append currently reloads the run for aggregate hashing, and point/range inspection
loads all records before filtering. Benchmark representative sizes before redesigning
these P2 concerns. Move filters into SQL when justified; don't let hypothetical
scale-out postpone the first usable run. Clean dense one-line code/unused variables
only where it improves the changed path's readability and verification.

### Live evidence and user checkpoint

After fixture reliability, ask for runtime/mod configuration, external recording
destination/identity and the recording window. Follow the documented human-confirmed
association checkpoint: present observed summary; allow corrections; explicit
confirm/decline/interrupt; no default confirmation or claims to control OBS.

Record checked-in and installed producer identities; runtime/schema versions;
run/recording IDs; source hashes; video FPS/presentation-timestamp assumptions;
alignment method and sampled error. Positive frame indices alone are not measured
alignment. OBS callback/file/poll delay and VFR/dropped frames can matter. Validate
field/frame correspondence around at least a nontrivial action and page transition,
covering the selected scope. Fix a tolerance before acceptance, not afterward.

One finalized run with successful audit, trustworthy sample correspondence and
copy-paste inspection output is the milestone. It proves a supported capture path,
not general reconstruction accuracy or all action-family coverage. Preserve live
gaps such as unobserved sell/buy-use callbacks separately from synthetic test success.

## 11. Evaluation and reconstruction follow-through

Use #79/#82/#80 as revised in section 7. Define source-level splits, units,
temporal context, unknown/missing/occluded/ambiguous handling, matching and minimum
support. A field recoverability matrix can start with the selected slice and grow;
retain unmeasured entries rather than inventing full coverage.

Use independent frame QA; do not automatically promote producer-derived page names
to independently verified labels. Do not synthesize observed annotations from oracle
values. Store coordinate transforms and inspectable source-pixel mapping. Keep
deterministic export with provenance and diagnostics; neighboring frames and the
same source recording must not leak across train/dev/evaluation boundaries.

The first video-only result can target one page family and a few visible counters,
subject to the user's concrete target decision. A baseline is useful before broad
ontology/model development if its dependencies and contract are approved. The
reconstruction input must exclude oracle values; align/join the oracle only for
scoring. Output timestamped versioned observations, uncertainty/abstention and a
human-inspectable overlay/report. Report per-field error, support and abstention
separately. Do not choose acceptance thresholds after seeing held-out performance.

Keep broad detection/OCR/tracking/reduction/event/learning contracts and the
ONNX/runtime portability direction where applicable; an early slice is not a
license for unrelated architecture changes or model additions. Legacy labeling,
detector and policy artifacts remain potential references, not approved active
dependencies or proof the new goal is met. Verify class-map retrieval/provenance
instead of silently skipping failing fresh-checkout tests or importing legacy code.

## 12. Portable capture diagnostic

This preserves the earlier temporary probe so a new lead need not rely on that
machine-local file. Run from the repository root using the existing environment.
Save this snippet to an approved temporary script, then execute it with Python.
It imports the real bridge, writes only a temporary directory, and asserts the
old defects; after repairs, convert these expectations into positive regression
tests rather than treating probe assertion failures as new regressions.

```python
import json
import sys
from pathlib import Path
from tempfile import TemporaryDirectory

sys.path.insert(0, str(Path.cwd()))
from ground_truth.file_ipc_bridge import FileIpcBridge
from sqlalchemy.engine import make_url

def emit(io, request):
    (io / "snapshot.json").write_text(json.dumps({
        "request_id": request, "meta": {"run_id": "fixture"},
        "action_taken": "PlayHand", "legal_actions": ["PlayHand"],
    }), encoding="utf-8")

with TemporaryDirectory(prefix="retro-capture-") as directory:
    root = Path(directory)
    io, out = root / "io", root / "out"
    io.mkdir()
    bridge = FileIpcBridge(io, out)
    emit(io, 1)
    bridge.step_once()
    bridge = FileIpcBridge(io, out)
    emit(io, 2)
    bridge.step_once()
    session_path = out / "fixture" / "session.json"
    steps_path = out / "fixture" / "steps.ndjson"
    session = json.loads(session_path.read_text(encoding="utf-8"))
    records = steps_path.read_text(encoding="utf-8").splitlines()
    print("restart:", len(records), session["n_steps"])
    assert len(records) == 2 and session["n_steps"] == 1
    (io / "snapshot.json").write_text("{broken", encoding="utf-8")
    bridge.step_once()
    print("malformed retained:", (io / "snapshot.json").exists())
    assert not (io / "snapshot.json").exists()
    emit(io, 3)
    (io / "run_end.json").write_text(json.dumps({
        "run_id": "fixture", "outcome": "loss",
    }), encoding="utf-8")
    bridge.step_once()
    session = json.loads(session_path.read_text(encoding="utf-8"))
    print("pending end:", session["outcome"], len(bridge.open_sessions()))
    assert session["outcome"] is None and len(bridge.open_sessions()) == 1

try:
    make_url("bundle.sqlite")
except Exception as error:
    print(type(error).__name__, str(error))
else:
    raise AssertionError("Expected plain SQLite filename rejection")
```

Expected pre-repair output: restart `2 1`; malformed retained `False`; pending end
`None 1`; SQLAlchemy `ArgumentError` for the plain filename. These defects were
reproduced independently twice in review. Their live frequency was not measured.

## 13. Evidence ledger and anti-regression lessons

The companion retrospective contains the complete PR lists, timeline, source
references and methods. Preserve those distinctions when summarizing the work:

| Review insight | Implementation response |
| --- | --- |
| 55 merged PRs; 16 implementation/support/test, 10 product design/operations/evidence, 29 coordination | Measure accepted artifacts, not PR throughput. Categories are primary-purpose judgments, not time/spend estimates. |
| Thirteen thread-only PRs plus #73 with empty final diff; #74 excluded because it changes policy | Remove the post-merge mirror requirement; target zero settlement-only PRs. Don't call all documentation waste. |
| September reset changed shop-advice goal to broad reconstruction | Retain legacy knowledge, but score delivery against the active objective and explicit supported slice. |
| Repeated one-shot/completion/budget rules did not eliminate settlement churn | Remove the mechanism instead of adding another instruction copy. Short history does not prove causal productivity effects. |
| Run-bundle scope expanded explicitly in #34 | Respect acknowledged user scope changes; don't portray them as unauthorized agent invention. Integrate the resulting components now. |
| Inventory says alignment pending while historical review reports an aligned run | Separate dated evidence from current acceptance; reconcile current summary once, preserve source reports. |
| Review remediation confused native GitHub reviews with recorded independent verdicts | Define actual evidence once; verify SHA/task/verdict rather than a single API array. |
| Four-letter tags and latest skills have no demonstrated measured benefit yet | Preserve compatibility, remove mandatory burden, pause expansion; do not claim the latest skills were experimentally disproven. |
| Planning CI and phrase tests pass despite behavioral faults | Use executable production tests and accurately labelled structural checks; propose CI changes explicitly. |
| Local class map comes from gitlinks without `.gitmodules` | Resolve reproducible approved inputs before claiming clean-checkout readiness. |
| Recorder loses or misrepresents evidence under simple fixtures | Fix boundary reliability before using it to score reconstruction. |
| Legal actions/defaults can look more authoritative than they are | Separate engine observations, approximations, unsupported values and independent reference truth. |
| Timestamp arithmetic is not rendered-state alignment | Measure offset and pre/post-action correspondence; retain ambiguous intervals. |
| Storage/compatibility tests are not video end-to-end tests | Demand a user-runnable capture/inspect path, then reconstruction/scoring with oracle isolation. |
| Dense storage code, large mixed-responsibility Lua file, scaling costs | Improve touched paths and benchmark; avoid a broad rewrite instead of an artifact. |
| Phase layering pushes first end-to-end result to Phase 9; all-phase thresholds overload Phase 0 | Deliver integrated slices with progressively fixed criteria and source-level holdouts. |
| Many worktrees and duplicated batons increase ownership ambiguity | One outcome owner; preserve unfamiliar work; no cleanup campaign as prerequisite. |

Research basis: DORA small batches (valuable/testable as well as small), WIP limits
(finish bottleneck work), continuous integration (fast code feedback), Shape Up
integrated scopes, and Anthropic simple evidence-driven agent workflows. Direct
links and limitations are in the retrospective. Do not add a framework or demand
compliance with a named standard merely because it appeared in research.

### Evaluate the change after two production milestones

Record on the existing outcome issues: accepted artifact/reproduction command,
time from start to accepted demonstration including blocked time, outstanding
human decisions, escaped defects/rework, and settlement-only PR count. Do not
build a metrics service. If output remains absent, revisit scope and bottlenecks;
do not automatically add another agent, gate skill, checker or policy document.

## 14. Required final lead report

Report the implemented simplifications, changed paths, exact checks/results,
independent reviewed revision/verdict, issue/PR/merge references if published,
remaining approval/environment blockers, and #81's concrete next action. State
which workflow scenarios were walked and which behaviors were actually executed.

Success is a usable operating path followed by production output. Neither the
length of this plan, green prose checks, issue closure, nor a successful merge
alone establishes that product outcome.
