---
name: agentic-design-patterns
description: LangGraph-centered workflow-selection protocol for agentic systems. Use when choosing among Anthropic-style agent patterns, structuring router/gate/worker graphs, or embedding Aider inside a manager-led chatroom with business-analyst, developer, and QA roles.
status: active
last_validated: 2026-04-29
supersedes: []
validation_method: session
---
# Agentic Design Patterns

## Role
This skill sits between `architecture`, `code`, and `agentic-harness`. Use it when the hard part is not a single prompt or a single edit, but the workflow shape of a LangGraph system: which nodes exist, how state flows, where gates sit, and when a worker should loop or stop.

## LangGraph contract
- Keep shared state typed and explicit.
- Use named nodes with stable contracts plus explicit `START` / `END`.
- Express routing and gates in conditional edges instead of burying them in prompt prose.
- Use reducers for accumulators such as worker outputs, votes, messages, or manifests.
- Bound loops with counters, retry caps, or acceptance thresholds in state.
- Keep tools as explicit nodes or tool loops so the graph remains inspectable.

## Workflow chooser
- **Augmented LLM** — one tool-enabled worker with retrieval, memory, or lightweight tool use.
- **Prompt chaining** — sequential stages with a programmatic gate between them.
- **Routing** — classify input once, then dispatch to specialized handlers.
- **Parallel sectioning** — split one task into independent facets and aggregate.
- **Parallel voting** — run repeated judgments and aggregate consensus.
- **Orchestrator-workers** — manager plans, delegates heterogeneous subtasks, then synthesizes.
- **Evaluator-optimizer** — generator/evaluator loop until accepted or capped.
- **Autonomous agent** — bounded tool loop with explicit budget and stop criteria.

## Aider in LangGraph
When `aider` appears inside the graph, treat it as a worker substrate rather than the orchestration framework.

- **Manager** — owns plan, role routing, stop conditions, and final synthesis.
- **Business analyst** — converts the user request into acceptance criteria, scope boundaries, and task cards.
- **Developer** — runs Aider for implementation and repo edits.
- **QA** — runs Aider or harness checks for tests, regressions, and acceptance evidence.

Recommended rule: the manager owns the chatroom state, while each role writes a bounded artifact back into shared LangGraph state. Do not let Aider become the hidden graph controller.

## Working rule
- Use `agentic-design-patterns` to choose graph shape and role topology.
- Use `substrate-selection` to decide whether the workers should be Aider, OpenCode, claw-code, or another runtime.
- Use `agentic-harness` when the problem is harness coherence, legality, or self-repair.
- Use `code` when the task is concrete repo editing rather than workflow design.
<!-- consolidation:see-also:start -->
## See Also
[[agentic-harness]]  [[substrate-selection]]  [[multi-agent-coordination]]
<!-- consolidation:see-also:end -->
