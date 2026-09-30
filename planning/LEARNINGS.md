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

## 2026-09-30: ONNX + ONNX Runtime is the "Docker" layer for device-portable inference

- Context: D012 required batch GPU to remain possible without changing data
  contracts, but the planning docs did not name a concrete mechanism, and the
  Phase 3 gate demanded "byte-compatible" output across devices.
- Observation: ONNX (versioned model format, pinned opsets) plus ONNX Runtime
  execution providers (CPU, DirectML, CUDA/TensorRT) gives one inference API
  where the device is a provider-ordered session option. All are MIT-licensed
  and free. DirectML is supported, which rules out JAX for this Windows-first
  project. Cross-provider byte-identity is not realistic: different execution
  providers legitimately differ in low-order float bits, so contracts must pin
  a numeric tolerance instead. The Python array API standard
  (data-apis.org) is the analogous device-neutral interface for non-model
  tensor code.
- Implication: Adopted as D017. Detection/Phase 3 gates now require the same
  `.onnx` artifact run under different providers with tolerance-based
  contract compatibility rather than byte-identity.
- Verification/source: onnxruntime.ai execution-provider docs and
  data-apis.org array API standard fetched 2026-09-30; MIT licenses stated in
  the ONNX and ONNX Runtime repository licenses.
