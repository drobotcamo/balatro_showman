# Production retrospective

Date: 2026-10-02
Status: proposal for discussion, not an adopted policy or gate approval.

Follow-up: the user approved all three decisions requested below on 2026-10-02.
D028 in `planning/DECISIONS.md` records that approved direction. Detailed
workflow/roadmap implementation remains next; other recommendations in this
report are proposals, and no phase gate has been approved by this review.

Implementation handoff: `planning/WORKFLOW_MIGRATION_IMPLEMENTATION_PLAN.md`
contains the scoped assignments, acceptance checks and production follow-through.
Its section 8 clarifies the transition boundary: clean-checkout/application CI
remains required production work, but reserved input/CI changes need specific
approval. A verified diagnosis and exact approval request can accompany completion
of the approved instruction migration; they are not proof application CI exists.

## Verdict

The project has built useful oracle-capture and storage infrastructure. It has
not yet demonstrated the active product: reconstructing trustworthy structured
state from video. The workflow explicitly requires completion and settlement
records, and the history shows repeated bookkeeping-only PRs. This suggests
avoidable coordination overhead; its effect on delivery time has not been measured.

The problem is not small PRs. Small, independently useful changes are desirable.
The problem is small administrative changes that require more administrative
changes, while integration and measurement remain deferred.

Keep the evidence discipline, explicit uncertainty, component boundaries, and
independent code review. Reduce duplicated status, settlement work, speculative
gate design, and specialized orchestration. Put the next effort into a reliable
recorded example and then a narrow, measured video-reconstruction slice.

## Scope and limits

Reviewed the git timeline from November 2025 through October 2026; all 55 merged
PRs available through PR #91, including their file lists; current open issues;
selected issue discussions and PR bodies; architecture, roadmap, component and
workflow standards; active capture/storage code and tests; and legacy entrypoints.
An independent read-only explorer inspected code quality and delivered capability.
This was broad sampling of implementation, not a line-by-line audit of all legacy
code or a fresh execution of historical training and game captures.

Source snapshot: local HEAD `ade4453`, branch `issue-84-wave`; remote-tracking
`origin/master` at `ceb1580`. `git diff --stat HEAD origin/master` was empty:
the reviewed file content matched, although commit histories differed. GitHub
had four open issues (#79–#82) and no open PRs. Fifteen worktrees were registered;
that is an inventory count, not a claim that fifteen workers were active.
The pre-existing untracked `does-not-exist.db` was preserved.

GitHub merge times are used in UTC below. The concentrated agent-workflow period
covers September 30 through October 2, not months of controlled observation.
Temporal sequence supports mechanisms and hypotheses, not causal estimates of
productivity. PR counts do not measure working hours, token cost, or waste.
External recordings were not replayed in this review.

## What has actually been produced

| Deliverable | Evidence | Assessment |
| --- | --- | --- |
| Earlier labeling, dataset generation, detector and policy experiments | `legacy/README.md`, legacy CLI/tools, pre-reset git history | Real research assets, but reference-only after the September 30 reset. Their current quality and reproducibility were not re-established. |
| Lua oracle and file-IPC recorder | PRs #9, #24, #28, #29, #32, #41; `ground_truth/` | Useful engine observations, IDs, zones, attributes and actions. Still a smoke subset with capture-reliability gaps. |
| Oracle audit and recording alignment plumbing | PRs #17, #36, #39; audit/alignment helpers | Runnable integrity checks and timestamp mapping; historical live evidence exists in reports. Current frame-level alignment error remains unmeasured here. |
| SQLite storage and inspection | PRs #53, #55, #56, #57, #61, #70 | Transactional storage, raw-byte preservation, lifecycle restrictions, provenance, JSON inspection and compatibility readers. |
| Boundary integration tests | PR #67 | Tests connect storage and compatibility concepts; not an end-to-end video reconstruction demonstration. |
| Provenance inventory | PR #77 | Reproducible candidate inventory. Eligibility and adoption remain unresolved. |
| Active video reconstruction and evaluated dataset | Roadmap Phases 1–10; open #79–#82 | No active integrated detector/OCR/tracking/reducer pipeline or completed evaluation set demonstrated. |

The September reset changed the objective from shop advice toward broad visible
state reconstruction. It correctly stopped treating legacy prototypes as proof
of the new objective. It also expanded the dependency surface substantially.
That strategic tradeoff should be acknowledged rather than scoring old work as
either worthless or complete delivery of the new product.

Phase 0 remains open. It would be inaccurate to say that no alignment work has
been done: `ORACLE_DATA_REVIEW.md:200–223` reports a merged-revision aligned run.
It would also be inaccurate to treat that as present acceptance of all oracle
semantics or alignment precision. `PHASE0_INVENTORY.md:33–39` still says neither
run is revision-pinned or aligned, and its next-action section recommends work
already delivered in #77. The catalogue is not a dependable current-state view.

## PR accounting

Manual classification by primary purpose, informed by changed paths:

| Category | Count | PRs |
| --- | ---: | --- |
| Product/support implementation, executable audit or product tests | 16 | #9, #17, #24, #28, #29, #32, #36, #41, #53, #55, #56, #57, #61, #67, #70, #77 |
| Product design, operational instructions or capture evidence | 10 | #4, #8, #20, #22, #31, #39, #49, #50, #52, #66 |
| Coordination, policy, cataloguing or settlement | 29 | #2, #3, #19, #23, #26, #27, #30, #33, #38, #40, #42, #51, #60, #62, #64, #65, #68, #72, #73, #74, #75, #78, #85, #86, #87, #88, #89, #90, #91 |

These are not value judgments on every PR. #17 is useful production support
despite being described as a review; #88 has tests but tests a workflow skill,
not reconstruction. Mixed PRs are assigned once. Historical branch overlap means
summed PR line changes would double-count some changes, so no line-volume
productivity claim is made.

Thirteen PRs changed only thread files: #23, #27, #30, #42, #51, #62, #68, #75,
#78, #86, #87, #89, #91. PR #73 has zero files/additions/deletions in its final
GitHub diff. #74 is settlement-labelled but also changes workflow policy, so it
is excluded from the thirteen. This is a conservative, reproducible indicator
of administrative amplification: 14 of 55 PRs, about 25%, have no deliverable
beyond thread bookkeeping or an empty final diff.

## How the control system evolved

| Change | Intended benefit | Observed consequence and judgment |
| --- | --- | --- |
| September 30 reset and contracts (`f909bcf`, `4073aa1`) | Separate legacy experiments from a coherent reconstruction plan | Clear oracle/video distinction, but eleven phase gates and broad scope before a thin integrated output. Good direction; oversized initial delivery boundary. |
| Initial agent workflow and compacting (`fd41f4a`, `c076cbd`), tiered approval and #2 | Reproducible handoffs and proportionate approval | Planning checks and protected-branch flow became usable. Requiring a PR for every T0 status update made post-merge thread edits costly. Keep protected branches; remove the need for those edits. |
| Bounded lead loop #3; planning reconciliation #19; orchestrator #26 | Ownership, bounded delegation and reliable work selection | Producer features followed (#24, #28, #29, #32). This is real output, but there is no controlled evidence the extra portfolio layer caused it. Settlement PRs #23, #27 and #30 already appear in this period. |
| One-shot completion #33 and handoff-or-completion #40 | Stop agents at a genuinely useful end state | Product work continued, but #42 and later #51 still repaired/advanced batons. The rules did not remove the underlying duplication or post-merge update requirement. |
| Run-bundle scope/design #49–#52, implementation #53–#57 | A durable operational boundary | Useful storage and inspection shipped. Issue #34 explicitly expanded from read-only inspection into lifecycle and recording coordination; this was an acknowledged scope change, not evidence of agents secretly inventing it. Integration with actual capture remains incomplete. |
| Four-letter tags #60 | Stable, convenient references | Added a registry, allocator/checker and naming rules beside GitHub IDs. No measured retrieval/coordination benefit yet. Retain historical tags; stop expanding this subsystem pending a concrete need. |
| Execution-budget and completion rules #64 | Recover from routine failures and finish continuously | Subsequent history includes useful #67/#70/#77, but also #68/#73/#74/#75/#78 and later settlement work. More forceful completion prose has not eliminated the pattern. |
| Review remediation #65 and gate enforcement #72 | Prevent unreviewed T2 merges | A real defect class motivated the change. The mechanical check asserts prompt text, not actual review evidence. Issue #34 then entered a close/reopen/exception loop over review-record interpretation. |
| Portfolio-state #88 and gate-facilitator #90 | More reliable selection and gate decisions | Too new for an effectiveness verdict. #88/#90 each immediately gained a settlement PR (#89/#91). WAVE first produced blocker/metadata PRs #86/#87; its actual gate use still awaits #79–#82. |

Two feedback loops deserve explicit removal:

1. Merge implementation → update versioned baton with the merge result → open
   another PR → settle that PR's metadata. GitHub already knows the merge state.
   A source-controlled historical checkpoint need not mirror it continuously.
2. Agent misses a rule → add the rule to more prompts → assert that text exists →
   mistake prose presence for behavioral enforcement. The #72 validator checks
   exact phrases and even line breaks in `check_contracts.py:298–314`.

There is also an interpretation problem. The workflow requires a fresh-context
reviewer's verdict recorded on the PR. Issue #34 comments later treated an empty
GitHub `reviews` array as proof no qualifying review existed. Those are different
claims: an agent verdict can be recorded in a comment. The owner accepted the
historical process gap, and it should not be repeatedly reopened without new
substantive evidence. Define the accepted evidence once, tied to a reviewed SHA.

The current branch protection requires status `check`, with native required PR
reviews absent. That explains why prose requirements alone do not block merging.
It does not establish that every historical review was absent or inadequate.

## Code quality and verification

### Strengths to preserve

- Small Python storage boundaries and transactions; callers do not receive ORM
  sessions. Terminal evidence writes are rejected.
- Malformed bundle payloads can be retained as bytes rather than fabricated into
  valid data. Recording provenance is additive and conflicting values are rejected.
- Inspection distinguishes observed, derived, missing and unsupported results.
- Tests exercise migrations, lifecycle behavior, integrity tampering, recording
  confirmation and compatibility cases. The complete local suite is fast.
- Unknown object identities and unresolved actions can remain explicit.

### Findings in production priority order

| Priority | Finding and evidence | Required result |
| --- | --- | --- |
| P0 | Bridge restart resets session metadata while appending existing records (`file_ipc_bridge.py:88–105,143–146`). Reproduced: two persisted records, `n_steps=1`. | Restart preserves count, identity, deduplication and outcome; fault/restart acceptance tests. |
| P0 | `_read_json` deletes malformed input and removes valid input before persistence (`file_ipc_bridge.py:74–85`). Reproduced deletion. | Preserve/quarantine unreadable evidence and only acknowledge durable consumption. |
| P0 | `step_once` handles run-end before pending snapshot (`file_ipc_bridge.py:150–177`); the snapshot can recreate a just-finalized session. Reproduced: outcome becomes null and the run is open again. | Pending final evidence and terminal outcome survive either arrival order. |
| P0 | Lua repeatedly overwrites one snapshot file and uses a 30 ms coalescing rule rather than acknowledgement backpressure (`main.lua:1294–1312`). | Demonstrate no silent loss under a delayed consumer, or explicitly diagnose every loss. Protocol choice needs design approval. |
| P1 | Oracle values use plausible defaults (`main.lua:601–620`); legality is coarse page/selection logic and always includes the recorded action (`1090–1132`). | Distinguish unavailable/approximate values from engine truth. Do not use self-inclusion as independent mask validation. |
| P1 | Only GitHub workflow runs issue-tag and planning checks (`.github/workflows/planning-check.yml:19–25`), not pytest or Lua behavior. Code-only paths also miss its trigger filter. | Clean-checkout application tests run for code changes; approval required for CI policy changes. |
| P1 | Active class-map generation/tests read a local legacy gitlink; `.gitmodules` is absent (`generate_class_ids.py`, `test_class_ids.py:28–44`; known learning). | Reproducible, approved input available to a clean checkout. Do not silently skip the test to make CI green. |
| P1 | OBS event → file request → Lua polling timestamp is treated as recording zero by arithmetic mapping. Current runtime offset/error is not measured. | Human-check real frame/action pairs and record measured error; use presentation timestamps or constrain recording format as appropriate. |
| P1 | Capture produces directory-based NDJSON; compatibility reader explicitly is not a SQLite converter. Inspection `diff`/`transitions` are unsupported. | One documented, executable capture-to-inspection path; state unsupported capabilities plainly. Retain both formats until an explicit integration decision. |
| P1 | Operations guide says `--db <bundle.sqlite>` but inspector calls SQLAlchemy `make_url`. A plain filename is rejected. | Copy-paste CLI example verified in an isolated environment with real output. |
| P2 | Aggregate digest covers payload hashes, not all metadata; finalization does not rehash payload bytes (`repository.py:71–107`). | Explicit integrity scope and tests for mutation/finalization, before treating status as a fresh verification. |
| P2 | Appending reloads all records for hashing; point/range inspection loads the whole run (`repository.py:104–107`, `inspection.py:44–56,97–103`). | Benchmark representative runs; use SQL filtering and change aggregate strategy only if justified. |

The P0 labels prioritize dependable evidence collection, not an assertion of a
live outage. Only the three bridge cases and filename rejection were reproduced
here; overwrite frequency, alignment error, performance and real-engine legality
remain to be measured.

Code style is uneven: storage code packs imports, conditionals and statements
onto single lines, has lightly typed public methods, and contains an unused
`should_raise` in `transition`. The Lua producer mixes extraction, serialization,
transport and hooks in one 1,433-line file (partly generated data). These are
maintenance concerns, but a broad rewrite is lower value than reliability tests
and a runnable integrated path. Refactor touched paths when that enables testing.

Lua checks in the current suite mostly inspect source strings/manifest content.
A previous temporary Lua harness is mentioned in learnings, but it is not a
checked-in executable behavior suite. Likewise the portfolio skill's tests
assert instructions contain phrases; they do not show an agent follows them.
Report those as structural checks, not behavioral validation.

## Why the plan is not producing enough product

The roadmap is organized by technical layers. Phase 9 contains the first explicit
small-video end-to-end gate, after ontology, synthetic generation, detection,
page classification, OCR, tracking, composition/reduction and event inference.
That postpones the earliest test of whether the pieces make a usable product.

Phase 0 also requires numeric thresholds for all later phases before it closes.
#79 therefore combines evaluation design, a recoverability matrix, thresholds for
almost the whole roadmap and a pilot. #82 depends on that protocol, but the
protocol's pilot needs data and review tooling. This creates practical circular
planning pressure even where the issue graph has no literal cycle.

Fix this with progressive commitment: define units, provenance, splits and the
first slice's acceptance criteria now; use a pilot to justify subsequent gates.
Freeze evaluation criteria before scoring a held-out result. Do not choose
thresholds after seeing the result to manufacture a pass. Changing the current
all-phase requirement needs explicit user approval.

## Proposed compact operating model

These are proposed changes, not permissions granted by this report.

| Keep | Change | Retire from routine work |
| --- | --- | --- |
| One accountable lead; independent reviewer for output-affecting changes | Lead selects from an agreed priority queue; portfolio audit when priorities, ownership or dependencies conflict | Routine full-portfolio and handoff audits when selecting work |
| GitHub issue for a bounded outcome; PR for implementation/review | Issue describes observable result, acceptance command, blocker and owner | Separate issues for every design/review/document/settlement step |
| Protected branches and relevant tests | One accepted review-evidence format with reviewed commit SHA and verdict | Repeated prose copies pretending to enforce merge behavior |
| Durable decisions and reusable domain findings | Record once and link; update contracts when interfaces change | Generic workflow advice appended as project discoveries |
| Handoff when work is unfinished | Short checkpoint: objective, commit/worktree, evidence, blocker, next action | Post-merge baton-only PRs and historical-state reconciliation campaigns |
| Component interfaces and uncertainty semantics | Small runnable milestones cross component layers | All-future-phase specification as prerequisite to a first measured slice |

Use one authoritative home per kind of information:

- GitHub issue: outcome, priority, acceptance and blocker.
- PR/CI: diff, reviewed SHA, test output and integration state.
- Repository: current architecture/interfaces, durable decisions, reproducible
  protocols and evidence references.
- Handoff: only context needed to resume unfinished work. GitHub supplies live
  merge/closed state; a pre-merge checkpoint may remain historical without repair.

Start with one active production outcome. A second worker should help resolve
its bottleneck or review it; start a second implementation only when ownership
and acceptance are independent. Fifteen registered worktrees do not justify
fifteen concurrent tasks. Inventory and remove only confirmed-owned obsolete
worktrees during one cleanup, preserving unknown work.

An issue should normally fit this template:

> After this change, a user can [observable action] and receive [artifact].
> Demonstrate with [command/input/output]. Scope excludes [specific boundary].
> Owner: [lead]. Blocked only by [actual prerequisite or decision].

A research/design item is legitimate when it retires a named uncertainty and
enables a named production decision. Require its result, not a code quota.
Create a sub-issue only for independently deliverable work or a real external
blocker. Small coherent PRs remain welcome; do not batch unrelated code merely
to reduce PR count.

The work loop becomes: select outcome → inspect relevant state → implement and
run acceptance → independent review → integrate → record result on the PR/issue.
If blocked, leave one checkpoint with the exact request. Do not substitute a new
workflow feature for the blocked product work.

## Transition plan

### 1. One bounded simplification change

Owner: project lead, with user approval for policy and CI changes.

- Update the workflow once to eliminate settlement-only PRs, define historical
  handoff semantics and one reviewed-SHA evidence format.
- Remove duplicated procedural text from agents/commands/templates; leave links
  and role-specific instructions. Retain tests for real structure, not exact prose.
- Keep existing tags resolvable; stop mandatory new tag allocation if approved.
- Pause additional portfolio/gate skill expansion for the next two production
  milestones. Existing skills can be consulted where useful.
- Reconcile only the current Phase 0 evidence summary; archive historical
  checkpoints as history rather than making each truthful "as of now."
- Make application tests clean-checkout reproducible, then add them to CI with
  approved triggers/check requirements. Resolve the class-map input explicitly.

Exit evidence: no post-merge repository edit is required to complete a normal
item; clean-checkout tests execute; the next lead can find the current outcome,
acceptance command and blocker without reconstructing closed threads. This is
one bounded transition, not a new process platform.

### 2. Deliver a reliable, inspectable recorded run

Owner: one capture lead; user supplies the live recording window and confirms
recording identity; reviewer challenges evidence.

Fix/reproduce the capture faults first. Then use #81 as the outcome anchor,
adjusting scope explicitly because its current text forbids producer changes.
Use an existing suitable recording if it can support the agreed checks; otherwise
capture a fresh current-producer run. Keep repairs and the live capture as linked
small PRs/checklist steps where independently testable, not a new issue tree.

Deliver: pinned producer/runtime identity; externally stored video and raw oracle
evidence with hashes; audit output; verified frame/action samples with error
measurements; and a copy-paste inspection path. The user must be able to inspect
what happened without consulting this retrospective or agent chat.

Exit evidence: delayed-consumer/restart/finalization tests expose no silent loss
under the declared supported cases; one finalized run audits successfully;
sampled synchronization error is reported against a pre-agreed tolerance; source
evidence remains intact. A successful capture is infrastructure delivery, not
yet a reconstruction-quality claim.

Declare the oracle snapshots as pre-action observations: the producer emits before
calling the original action callback (`main.lua:1349–1377`). Verify that rendered
frames correspond to the sampled fields, not just nearby timestamps. Mark
transition/animation intervals ambiguous or unsupported where correspondence
cannot be established. Runtime mislabeling was not reproduced here; this is an
acceptance requirement for trustworthy counter and state comparisons.

### 3. Deliver a small reviewed evaluation slice

Owner: same outcome lead or a clearly handed-off evaluation lead; independent QA.

Rescope #79 and #82 around a pilot before designing every field and future gate.
Use #80 to decide only the dependencies this pilot needs, not the eligibility of
all legacy assets. Retain those issues and rewrite their scope/dependencies with
approval rather than creating duplicate replacements.

Deliver: inspectable frame/oracle pairs, a minimal annotation/review/export path,
deterministic manifest, declared visibility/unknown handling, and source-level
split rules. Choose a bounded sample covering the selected states/transitions;
do not claim statistical generalization from a tiny correlated sample.

Exit evidence: a second person can review the labels and regenerate the manifest;
coverage, disagreement and missingness are reported; development and held-out
sources are separated. Broader annotation features wait for demonstrated need.

### 4. Deliver the first video-only reconstruction result

Owner: reconstruction lead; independent evaluation reviewer.

Proposed first target: one declared page family and a small field subset, such
as money plus hand/discard counters. Select the exact slice with the user based
on footage and available dependencies. If another slice removes more uncertainty,
choose it before implementation. This crosses current phases and requires an
approved roadmap change; it does not declare the skipped broad gates passed.

Deliver: video input → timestamped structured observations with unknowns →
comparison against separately aligned/checked oracle evidence. The reconstruction
path must not consume oracle values. Include a human-inspectable overlay/report.

Exit evidence: one command processes the supported clip, outputs the versioned
artifact and reports per-field error and abstention on held-out material. Pin
acceptance thresholds and minimum support before that evaluation. Unsupported
pages remain unsupported. Broaden coverage only after this loop works.

## Measure the experiment

Evaluate the operating-model change after the next two production milestones,
not after another round of policy edits. Record these on existing outcome issues:

- Artifact accepted, with input identity and reproduction command.
- Time from starting the outcome to its accepted demonstration, including wait.
- Blocking human decisions and how long they waited.
- Escaped defects/rework in the delivered path.
- Standalone settlement PR count, with target zero.

PR throughput, test count and document count are diagnostics, not success metrics.
If two milestones produce no usable artifact, revisit scope or the bottleneck;
do not automatically add another agent role. This is an experiment, not a promise
that fewer documents alone will improve output.

## Methods researched and applied

Sources accessed 2026-10-02. These guide the proposal; they do not prove a causal
claim about this repository or justify adopting a complete external framework.

- [DORA: small batches](https://dora.dev/capabilities/working-in-small-batches/):
  INVEST includes valuable and testable, not merely small. Applied to independently
  usable slices while retaining small PRs.
- [DORA: work-in-process limits](https://dora.dev/capabilities/wip-limits/):
  finish priority work and expose bottlenecks instead of starting more work.
  Applied to one active production outcome and bottleneck-oriented delegation.
- [DORA: continuous integration](https://dora.dev/capabilities/continuous-integration/):
  code changes need fast executable feedback. Applied to application tests and
  clean-checkout inputs rather than planning-check-only protection.
- [Shape Up: Map the Scopes](https://basecamp.com/shapeup/3.3-chapter-12):
  organize around independently finishable integrated parts rather than roles or
  layers. Applied to capture/inspect, review/export, and reconstruct/score slices.
- [Anthropic: Building effective agents](https://www.anthropic.com/engineering/building-effective-agents):
  start simple; add complexity when it demonstrably improves outcomes; use tools
  and environmental feedback. Applied to one lead, bounded research/review and
  behavioral acceptance instead of more instruction-presence checks.

## Verification record

Executed against the reviewed checkout:

```text
python -m pytest -q
91 passed, 15 subtests passed in 6.02s

python planning/check_contracts.py
planning contracts OK

python tools/issue_tags.py check
valid: 8 issue tag(s)

git diff --check
(no output)
```

An isolated temporary diagnostic imported the real FileIpcBridge and used a
temporary IO/output directory, never live recordings. It wrote request 1 with
run `fixture`, restarted the bridge, wrote request 2, supplied malformed JSON,
then supplied request 3 together with a `loss` run-end signal. Assertions checked
the observed failures. It also called SQLAlchemy `make_url("bundle.sqlite")`.

```text
restart: persisted_records=2, session_n_steps=1
malformed_input_retained=False
pending_snapshot_plus_end: outcome=None, n_steps=1, open_sessions=1
documented_db_path: ArgumentError: Could not parse SQLAlchemy URL from given URL string
```

Diagnostic script for this session:
`C:\Users\camgr\AppData\Local\Temp\opencode\retrospective_capture_probe.py`.
Its fixture directories were automatically removed. The behavior sequence above
is sufficient to turn the findings into regression tests when repairs are scoped.

PR inventory can be reproduced with `gh pr list --state merged --limit 100
--json number,title,mergedAt` and each PR's `gh pr view N --json files,body`.
The original review fetched all merged PR file lists through GraphQL and verified
neither the PR collection nor any file list was paginated/truncated. Classification
is explicitly listed above so it can be challenged without rerunning an agent.

## Decisions requested

1. Approve a thin-slice delivery sequence and progressive gate definition instead
   of requiring all Phase 1–10 thresholds before the first reconstruction pilot?
2. Approve eliminating mandatory settlement-only PRs and new tag allocation,
   using GitHub as authority for live completion state?
3. Confirm the first visible output: the proposed recorded-run inspector followed
   by a small video-only field reconstruction, or a different concrete artifact?

The first two change durable policy and roadmap expectations. They need an
explicit decision before implementation. No production behavior, branch protection,
accepted contract, or issue status was changed by this retrospective.
