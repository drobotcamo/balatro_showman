# D028 migration verification

This is a versioned scenario/evidence record for #92, not a live completion
ledger or another implementation plan. PR/CI own review and merge facts.

## Executed and inspected evidence

- Lead executed the isolated section-12 capture probe: `restart: 2 1`,
  `malformed retained: False`, `pending end: None 1`, and SQLAlchemy
  `ArgumentError Could not parse SQLAlchemy URL from given URL string`.
  These reproduce old defects; they are not positive recorder acceptance.
- A supplied instruction/checker map, B supplied gate/issue reconciliation, and C
  compared the lead's probe output with source. All were read-only.
- Fixture-backed validator tests exercise compact numeric/no-tag and historical
  numeric/tagged/full-format records, invalid/missing data, broken references,
  registry integrity, parsed command routing and role permission boundaries.
- Gate fixtures execute a classification model with named protocol/criteria and
  refusal cases. They do not run an agent, approve a protocol or prove determinism.
- Existing CI/protection inspected: only planning/tag checks; required `check`;
  application-only paths do not trigger it. Native required reviews are absent.
  Existing workflow, permissions and tag mappings remain unchanged.
- Local tests use a populated legacy CSV; no fresh-checkout success is claimed.
  PR records exact final commands/results and the independently reviewed SHA.

## Tabletop scenario acceptance

All rows below are tabletop walkthroughs of the revised instructions, not
observed agent actions. Supporting tooling executions are identified separately.

| Scenario | Expected next action | Evidence home | Allowed mutation | Stop boundary |
| --- | --- | --- | --- | --- |
| Ready production issue | Lead inspects relevant state and implements directly | Issue/PR | Bounded branch changes | Actual ambiguity/approval conflict, not portfolio/tag prerequisite |
| Normal success | Checks/current review, integrate, verify merge, record completion | Same PR/issue | Implementation before review; GitHub after merge | Missing acceptance/review/CI; zero required post-merge repository edits |
| Context boundary | One compact checkpoint with revision/results/owner/next | Repository checkpoint plus issue/PR | Owned checkpoint in implementation PR | Fresh lead rechecks live state |
| Historical baton, PR now merged | Recognize later GitHub completion | GitHub plus historical checkpoint | No repair needed | No reopening solely for pre-merge metadata |
| Numeric-only issue | Use #N and numeric compact checkpoint | Issue/optional checkpoint | No registry change | Invalid essential data still fails; fixture-backed |
| Existing tag | Resolve immutable alias and tagged record | Historical registry | No mapping changes | Unknown tag/wrong mapping rejected; fixture-backed |
| Change after review | Obtain current-diff/SHA review again | PR | Bounded fixes then review | Stale verdict cannot permit merge |
| Review comment/native reviews empty | Inspect actual independent task/verdict/SHA | PR comment | Record actual reviewer evidence | Empty array alone neither rejects nor establishes approval |
| Recording confirmation missing | Present observed summary and explicit confirm/decline/interrupt choices | Issue and recording protocol | Read-only inspection before confirmation | No association mutation/default success |
| No applicable required CI | Inspect configuration/protection, report exact gap | PR/issue | No policy edit without approval | No invented pass or bypass |
| Incomplete/stale protocol/evidence/no acceptance | Identify named missing criterion/decision | Versioned protocol/report | Read-only facilitation | Refuse pass; fixture model covers refusal |
| Protocol for different slice/revision | Select actual applicable approved protocol | Protocol/report | No evidence reinterpretation | Inapplicable protocol rejected; fixture model |
| Publication unavailable | Inventory revision/paths/staged/pushed state and exact failure | One unpublished checkpoint and issue if available | Preserve work; local commit only if authorized | Request precise D027 exception or missing publication action; D028 is no waiver |
| Unrelated local file | Preserve/exclude does-not-exist.db | PR ownership note | No stage/delete | No destructive clean-worktree claim |

The next #81 production session is the behavioral trial; this migration does
not claim capture, evaluation, recording confirmation or reconstruction success.

## Exact reserved approval requests

1. Reproducible class-map input: approve either publishing only the canonical
   upstream CSV into a versioned active input location with repository/revision,
   hash and license/redistribution evidence, or repaired pinned submodule retrieval.
   Preserve class IDs and mandatory generator/equality tests. Do not derive the
   expected input from generated output or skip tests. #80 owns eligibility.
2. Application CI: approve a separate test job for application/test/input/dependency
   changes, an agreed Python version (project minimum is 3.11), approved test-tool
   installation, `python -m pytest -q` and
   `python ground_truth/generate_class_ids.py --check`. Preserve planning checks;
   decide separately whether the new check is required by branch protection.
   No new Lua/game/OBS dependency is implied. Until approval, this is a production
   verification gap, not a blocker to the approved instruction migration.

## Production handoff

#81's next lead writes recorder fault/restart tests before repairs, then verifies
a coherent capture-to-inspection command. Transport redesign and converter/schema/
lifecycle changes require a bounded decision. Only after fixture reliability
request runtime/mod/window/destination/format/tolerance and human association.
Sections 10–13 of `planning/WORKFLOW_MIGRATION_IMPLEMENTATION_PLAN.md` retain
the full production cases, semantic limitations, marker/lifecycle questions,
integrity scope, performance evidence needs and oracle-isolated evaluation path.
The inspected Lua request counter is process-scoped, not reset on each run;
run-scoped identity remains required across restarts. No recorder rewrite belongs
in this PR.
