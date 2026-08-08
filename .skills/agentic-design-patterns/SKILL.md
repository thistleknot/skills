---
name: agentic-design-patterns
description: LangGraph-centered workflow-selection protocol for agentic systems. Use when choosing among Anthropic-style agent patterns, structuring router/gate/worker graphs, or embedding Aider inside a manager-led chatroom with business-analyst, developer, and QA roles. Includes a 5-question decision tree for principled pattern selection before any code is written.
status: active
last_validated: 2026-05-23
supersedes: []
validation_method: session
---
# Agentic Design Patterns

## Role
This skill sits between `architecture`, `code`, and `agentic-harness`. Use it when the hard part is not a single prompt or a single edit, but the workflow shape of a LangGraph system: which nodes exist, how state flows, where gates sit, and when a worker should loop or stop.

## Pattern Selection: Decision Tree

Run these five questions **before writing any code**. Each branch narrows the pattern space by a concrete task property. Mistakes are cheapest to fix here.

### Q1 — Is the solution path known in advance?
A *known* path means the full step-by-step process can be defined before execution (e.g. invoice processing, onboarding flows). An *unknown* path means each step depends on prior outputs (research, debugging, branching support).

- **Known** → Q2a
- **Unknown** → Q2b

### Q2a — Is this a fixed, deterministic workflow?
Use **Sequential Workflow**. Agent executes ordered steps; use the model only for interpretation or generation, deterministic code for everything else. Main failure mode: over-engineering with ReAct-style reasoning where every step is already defined. If edge cases start breaking it, move to Q2b.

### Q2b — Does the task require tool access or external information?
Almost always yes. Tool use is foundational — it adds capability without changing the reasoning layer. A ReAct agent with tools is still ReAct; a planning agent with tools is still planning. Proceed to Q3 with tool use assumed unless the task is genuinely self-contained.

### Q3 — Is the task structure articulable before execution begins?
A task is *structurally articulable* when it can be broken into ordered subtasks with clear dependencies before execution (e.g. design → implement → test). Structure being articulable enables early dependency exposure and avoids mid-execution surprises. But it has costs: upfront planning step, plan quality dependence, reduced flexibility.

- **Structure clear upfront** → **Planning + ReAct inside steps**
- **Structure only emerges during execution** → **ReAct**, then Q4

### Q4 — Does output quality matter more than response speed?
Reflection (generate → critique → refine) is worth adding only when:
1. Clear, verifiable quality criteria exist (valid SQL, correct contract, passing tests)
2. The cost of errors justifies an extra pass (deployed code, client-facing docs)

**Critic independence is critical** — a critic that mirrors the generator agrees rather than evaluates. Strong reflection often requires separate framing or a different model.

- **Quality priority + clear criteria** → add **Reflection** on top
- **Speed priority or vague criteria** → skip, go to Q5

### Q5 — Does the task have a specialization or scale problem a single agent can't handle?
The trigger must be a **concrete bottleneck** that specialization or scale actually solves — not architectural preference. Multi-agent adds coordination overhead, shared state complexity, and more failure points.

Use Multi-agent when:
- Task is too large for a single context window
- Different stages need clearly different reasoning styles (legal vs. financial, coding vs. security audit)
- Parallel execution materially reduces wall-clock time

If none of those apply, a single strong agent is usually better.

- **Real specialization or scale bottleneck** → **Multi-Agent**
- **No bottleneck** → stay single-agent

### Decision tree → pattern map

| Destination Pattern | When to Use | Why It Works |
|---|---|---|
| **Single Agent + Tools + ReAct** | Unknown path, no clear upfront structure, no strict quality constraints, no specialization needs | Best default. Flexible exploration, inexpensive failure detection, iterative improvement |
| **Planning Agent + ReAct** | Structure knowable upfront; each step still requires adaptive reasoning | Planner defines stages + deps; ReAct handles local uncertainty. Reduces mid-execution failure |
| **Single Agent + Reflection** | High-quality output required, latency acceptable, evaluation criteria explicit | Generate → Critique → Refine. Works best when verifiable criteria exist |
| **Multi-Agent Specialist System** | Strong specialization needs OR scale exceeds single-agent capacity | Coordinator routes to specialists; enables parallelism + domain expertise, but adds coordination overhead |

## Pattern assumptions (what each pattern asserts about the task)

| Pattern | Core assumption | Breaks down when |
|---|---|---|
| **ReAct** | Next best action not fully knowable in advance; reason + tool interleaved improves decisions | Task has a fixed structure — you're burning compute on decisions that don't need to be made |
| **Planning** | Major task structure identifiable upfront; roadmap improves downstream reliability | Structure only emerges during execution — plan becomes a lie mid-run |
| **Reflection** | First-pass outputs often incomplete or flawed; iterative self-critique justifies added cost | No clear evaluation criteria; critic mirrors generator too closely and just agrees |
| **Multi-agent** | Task benefits from specialization/decomposition; parallel or modular execution > coordination overhead | No real specialization needed — overhead outweighs benefit |

## Failure signals and fixes

| Signal | What it means | Fix |
|---|---|---|
| ReAct looping excessively | Too many steps; agent uncertain about progress or structure | Task likely needs planning, better tool structure, or a clearer stopping condition |
| Planning agent abandoning plan | Plan created but execution diverges | Task less structured than assumed; switch to lightweight planning + ReAct |
| Reflection not improving output | Critique cycles don't meaningfully change output | Evaluation criteria are unclear or critic too aligned with generator; refine the critique setup or use a different model as critic |
| Multi-agent routing failures | Wrong specialist selection or outputs don't combine downstream | Routing logic issue; use deterministic rules for predictable cases instead of LLM routing |

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

Recommended rule: the manager owns the chatroom state, while each role writes a bounded artifact back into shared LangGraph state. Do not let `pi` silently take over the outer graph, and do not let `aider` become the hidden graph controller.

## Lane parallelism rule

> **Parallelize artifact-producing lanes; serialize shared-UI lanes.**

An **artifact-producing lane** writes to an independent output target (file, DB row, API endpoint, background agent result). These lanes never contend — run them all at once.

A **shared-UI lane** writes to a single shared stream (terminal stdout, a chat turn, a progress bar). These lanes contend — serializing them is not a bottleneck, it is correctness.

| Lane type | Output target | Strategy | Why |
|---|---|---|---|
| File writes | Independent paths | Parallel | No contention; pure throughput gain |
| API / agent calls | Independent endpoints | Parallel | Latency hides behind wall-clock |
| DB rows (different PKs) | Append-only table | Parallel | No lock contention |
| Terminal print / chat output | Single stdout | Serial | Interleaved output is unreadable noise |
| Progress display / spinner | Shared UI widget | Serial | Race conditions corrupt display state |

**Application in this workflow**: when structuring an orchestrator-workers graph, put every worker that produces a distinct artifact in a parallel fan-out. Collapse back to a serial node only at the display/synthesis step. Workers that share nothing except their output channel must be serialized at that channel boundary — not before.

## Working rule
- Use `agentic-design-patterns` to choose graph shape and role topology.
- Use `substrate-selection` to decide whether the workers should be Aider, OpenCode, claw-code, or another runtime.
- Use `agentic-harness` when the problem is harness coherence, legality, or self-repair.
- Use `code` when the task is concrete repo editing rather than workflow design.
<!-- consolidation:see-also:start -->
## See Also
[[agentic-orchestration]]  [[agent-governance]]  [[evaluator-optimizer]]  [[react-agent]]
<!-- consolidation:see-also:end -->
