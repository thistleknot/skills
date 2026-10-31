---
name: agentic-design-patterns
description: Apply selected agent patterns as inspectable LangGraph workflows with explicit state, node contracts, Pi and Aider roles, and safe parallel lanes. Use after agentic-orchestration selects the pattern shape.
status: active
last_validated: 2026-10-31
supersedes: []
validation_method: source consolidation review; retained LangGraph contracts
---

# Agentic Design Patterns

Use this skill after [agentic-orchestration](../agentic-orchestration/SKILL.md) selects the workflow pattern. `agentic-orchestration` is the canonical source for the five-question chooser, pattern assumptions, and pattern failure signals. This skill applies that decision to a LangGraph implementation.

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

## Pi + Aider in LangGraph

When `pi` or `aider` appears inside the graph, keep the roles separate.

- `pi` is a **delegated harness node** — a bounded mini-manager for one subproblem.
- `aider` is a **worker substrate** — a narrow editor/executor, not the orchestration framework.
- **Manager** — owns plan, role routing, stop conditions, and final synthesis.
- **Business analyst** — converts the user request into acceptance criteria, scope boundaries, and task cards.
- **Pi node** — optional child harness that runs a local subgraph for one delegated scene.
- **Developer** — runs Aider for implementation and repo edits.
- **QA** — runs Aider or harness checks for tests, regressions, and acceptance evidence.

The manager owns chatroom state. Each role returns a bounded artifact to shared LangGraph state; `pi` does not take over the outer graph and `aider` does not become its hidden controller.

## Lane parallelism rule

**Parallelize artifact-producing lanes; serialize shared-UI lanes.**

An artifact-producing lane writes to an independent file, database row, endpoint, or background result. A shared-UI lane writes to one terminal stream, chat turn, progress bar, or other shared display. Fan out independent workers and join only for display or synthesis.

| Lane type | Output target | Strategy | Why |
|---|---|---|---|
| File writes | Independent paths | Parallel | No contention |
| API / agent calls | Independent endpoints | Parallel | Latency overlaps |
| DB rows | Different primary keys | Parallel | No lock contention |
| Terminal or chat output | One shared stream | Serial | Preserve readable order |
| Progress display | One shared widget | Serial | Avoid display races |

## Working boundary

- Use `agentic-orchestration` to choose graph shape and role topology.
- Use `substrate-selection` to select Aider, OpenCode, claw-code, or another worker runtime.
- Use `agentic-harness` for harness coherence, legality, or self-repair.
- Use `code` for concrete repository edits.

## Archive

The superseded full chooser is preserved verbatim in [archive/2026-10-31-SKILL.md](archive/2026-10-31-SKILL.md). It was reduced because it duplicated the canonical chooser in `agentic-orchestration`.

<!-- consolidation:see-also:start -->
## See Also
[[agentic-orchestration]]  [[agent-governance]]  [[evaluator-optimizer]]  [[react-agent]]
<!-- consolidation:see-also:end -->
