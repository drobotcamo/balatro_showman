# Engineering Learnings

Append concise, verified findings that should survive the current task. Use
this format:

```markdown
## YYYY-MM-DD: Title

- Context:
- Observation:
- Implication:
- Verification/source:
```

Unresolved questions belong in `planning/DECISIONS.md`; durable choices belong
under its Decisions section. This file is a knowledge base, not a task log.

## 2026-09-30: Bounded autonomy is safer than an unconstrained swarm

- Context: The repository needed agents that could make independent progress on
  complex work without weakening its evidence and approval gates.
- Observation: OpenCode's primary/subagent split, task permissions, finite
  `steps`, commands, and automatic compaction support a lead loop with narrow
  delegation and explicit stopping conditions. Anthropic's agent guidance also
  emphasizes simple composable workflows, environmental ground truth, evaluator
  loops, and human checkpoints.
- Implication: Use one project lead as the default owner; reserve explorer and
  reviewer subagents for independent evidence and adversarial verification.
  Encode checkpoints in prompts and commands rather than adding a custom
  orchestration plugin.
- Verification/source: OpenCode Agents, Commands, Skills, Plugins, and config
  schema docs fetched 2026-09-30; Anthropic, “Building effective agents,”
  published 2024-12-19; repository workflow in `planning/agent-workflow.md`.
