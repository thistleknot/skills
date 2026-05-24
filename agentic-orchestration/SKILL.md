---
name: agentic-orchestration
description: Unified orchestration protocol combining the MLM 5-question decision tree, Anthropic's agent pattern taxonomy, the live agent roster with role contracts, and Aider's architect/editor split as a concrete Planning+ReAct reference implementation. Use when designing or debugging a multi-agent system — before writing code and when diagnosing coordination failures.
status: active
last_validated: 2026-05-23
supersedes: []
validation_method: session
see_also: [agentic-design-patterns, agentic-harness, react-agent, agent-governance]
---
# Agentic Orchestration

Three layers in one doc:

1. **Pattern selection** — which shape to use before writing any code (decision tree)
2. **Agent roster** — the live role contracts and handoff rules for this stack
3. **Reference implementation** — Aider's architect/editor split as a concrete Planning+ReAct instantiation

---

## 1. Pattern Selection (Decision Tree)

Most failures are misreads of the problem, not execution failures. Run these five questions first.

### Q1 — Is the solution path known before execution starts?

- **Known** (invoice processing, onboarding flows): same steps every time → Q2a
- **Unknown** (research, debugging, branching support): each step depends on prior output → Q2b

### Q2a — Fixed deterministic workflow?

→ **Sequential Workflow**. Use the model only where interpretation is genuinely needed; deterministic code handles the rest. Failure mode: adding ReAct reasoning where every step is already defined.

### Q2b — Does the task need tool access?

Almost always yes — proceed to Q3. Tool use sits *under* the reasoning layer; a ReAct agent with tools is still ReAct.

### Q3 — Can you articulate task structure before execution begins?

- **Yes** (design → implement → test, provision-in-order, gather → synthesize → write) → **Planning + ReAct** inside each step. Exposes dependencies early. Costs: upfront planning step, plan quality dependence, reduced flexibility.
- **No** (structure only emerges through feedback) → **ReAct alone**, then Q4. Signal you chose wrong: the agent abandons the plan mid-run.

### Q4 — Does output quality beat response speed?

Add **Reflection** (generate → critique → refine) only when:
1. Clear, verifiable evaluation criteria exist (valid SQL, passing tests, complete contract)
2. Error cost justifies an extra pass (deployed code, client docs)

**Critic independence is load-bearing** — a critic that mirrors the generator just agrees. Use separate framing or a different model as critic.

- **Quality priority + explicit criteria** → add Reflection on top
- **Speed priority or vague criteria** → skip, go to Q5

### Q5 — Real specialization or scale bottleneck a single agent can't handle?

The trigger must be a **concrete bottleneck** — not architectural preference.

Use Multi-agent when:
- Task overflows a single context window
- Stages need genuinely different reasoning styles (legal vs. financial, coding vs. security audit)
- Work parallelizes cleanly and wall-clock time matters

Otherwise one strong agent is cheaper and simpler.

### Pattern map

| Pattern | When | Key property |
|---|---|---|
| **Single Agent + Tools + ReAct** | Unknown path, no clear structure, no strict quality bar, no specialization need | Best default. Flexible, cheap failure detection |
| **Planning + ReAct** | Structure knowable upfront; each step still needs adaptive reasoning | Planner sets stages + deps; ReAct handles local uncertainty |
| **Single Agent + Reflection** | Quality > speed, explicit verifiable criteria | Generate → Critique → Refine; needs critic independence |
| **Multi-Agent Specialist** | Real scale or specialization bottleneck | Coordinator routes to specialists; adds coordination overhead |

### Pattern assumptions (what breaks each)

| Pattern | Assumes | Breaks when |
|---|---|---|
| ReAct | Next action not knowable in advance | Task has fixed structure — reasoning where execution belongs |
| Planning | Major structure identifiable upfront | Structure only emerges during execution — plan becomes a lie |
| Reflection | First-pass output often flawed; critique justified | No clear criteria; critic too aligned with generator — it just agrees |
| Multi-agent | Decomposition + specialization beats coordination cost | No real specialization need — overhead outweighs benefit |

### Failure signals → fixes

| Signal | Meaning | Fix |
|---|---|---|
| ReAct looping excessively | Agent uncertain about progress or structure | Add planning, improve tool contracts, or add explicit stop condition |
| Planning agent abandons plan | Task less structured than assumed | Switch to lightweight planning + ReAct |
| Reflection not improving output | Criteria vague or critic too aligned | Redefine criteria; use different model or framing as critic |
| Multi-agent routing failures | Wrong specialist selected or outputs don't compose | Replace LLM routing with deterministic rules for predictable cases |

---

## 2. Agent Roster and Role Contracts

This stack maps directly onto the Q5 "genuine specialization" answer. Each role exists because it solves a bottleneck the others can't.

### Primary agents (opencode first-class residents)

| Agent | Model | Role | Delegates to |
|---|---|---|---|
| **orchestrator** | gemma-4-26b / deepseek-v4-flash | Root router. Routes to cheapest sufficient specialist. Never writes code directly. Owns heartbeat. | Any |
| **oracle/planner** | qwen3.6-35b | Spec planning and decomposition. Converts vague goals into acceptance criteria and task cards. | — |
| **designer** | qwen3.6-35b | Class/function signatures and stubs. No implementation. | — |
| **fixer/coder** | qwen3.6-35b | Spec translation only. Receives ambiguous/multi-file work, breaks into bounded packets, dispatches to @aider. Never touches files directly. | @aider |
| **librarian** | gemini-2.5-flash-lite | Web + docs search. External knowledge retrieval. | — |
| **observer/visionary** | qwen-vl-30b | Screenshot and diagram interpretation. Triggered first on any image attachment. | — |

### Subagents (agents block, callable from primaries)

| Agent | Model | Role | Bounded by |
|---|---|---|---|
| **pi** | qwen3.5-9b | Inner harness. Accepts one bounded objective; runs scripts, returns output; routes internally to @aider/@handyman/@debugger. | One packet scope |
| **aider** | qwen3.5-9b | Leaf editor. 2-pass: Reason → Edit. One file, one concern per call. `subtask=DENY` — cannot spawn subagents. | Named files only |
| **handyman** | granite-4.1-8b | Mechanical file ops. Zero-reasoning tool calls: move, copy, sample, convert. | Named paths |
| **patcher** | gemma-4-26b | Known-file hotfix. Named file + concrete error → immediate mutation + rerun. | Named file + known error |
| **debugger** | qwen3.6-35b | QA inspector. Stack traces, test failures, feedback loops. | Error isolation |
| **summarizer** | mimo-v2-flash | Context compression. Never edits code. | Compression only |

### Handoff rules

```
orchestrator
  ├─ image attached?          → observer (immediately, before anything else)
  ├─ AIDER DIRECT: prompt?    → aider (skip fixer entirely)
  ├─ file+change concrete?    → aider (skip fixer entirely)
  ├─ smoke test?              → pi
  ├─ known-file hotfix?       → patcher
  ├─ pure file ops?           → handyman
  ├─ multi-file / ambiguous?  → fixer → aider (packet chain)
  ├─ trace / test failure?    → debugger
  └─ web research?            → librarian

pi (internal routing only)
  ├─ edit packet              → aider
  ├─ file ops                 → handyman
  └─ failure / trace          → debugger
```

**No double duties**: if fixer would just pass an already-concrete task to aider, skip fixer. Orchestrator calls aider directly.

### Routing priorities (orchestrator decision order)

1. Explicit user targeting (e.g. `@aider fix X`) — honor unless unsafe
2. `AIDER DIRECT:` prefix or concrete file+change → aider
3. Image/screenshot → observer
4. Smoke test / script execution → pi
5. Known-file hotfix → patcher
6. Pure file ops → handyman
7. Multi-file / ambiguous spec → fixer
8. Trace / test failure → debugger
9. Web/doc research → librarian
10. Default: direct answer or oracle for planning

---

## 3. Aider Architect/Editor as Planning+ReAct Reference

Aider's two-model split is the clearest real-world instantiation of Q3's "structure articulable upfront" branch:

| Aider concept | Anthropic pattern | This stack equivalent |
|---|---|---|
| **Architect** (reasons about what to change) | Planning layer | `coder.toml` — spec-packager. Reasons about which files and what to change, produces bounded packets |
| **Editor** (applies the change) | ReAct execution inside each step | `aider.toml` — leaf executor. Applies one packet, two-pass: reason → edit |
| Architect → Editor handoff | Plan stage → execution stage | `fixer` dispatches bounded packet to `aider` |

The architect never touches files. The editor never re-plans. The interface between them is the packet: `{files, acceptance_criteria, exact_change_description}`.

**Why this matters for pattern selection**: whenever you have a task where you can write that packet before execution starts, you're in Q3-yes territory → use Planning+ReAct (coder→aider), not pure ReAct.

When you can't write the packet upfront (structure only emerges through execution), use ReAct alone — which in this stack means orchestrator → pi or orchestrator → aider directly with a looser prompt.

---

## 4. Anthropic Pattern Taxonomy (cross-reference backbone)

| Anthropic pattern | Decision tree branch | This stack expression |
|---|---|---|
| **Augmented LLM** | Q2b terminal (tools assumed) | Any single agent with MCP tools |
| **Prompt chaining** | Q2a / Q3-yes sequential | oracle → designer → fixer pipeline |
| **Routing** | Q5 specialization | orchestrator → role dispatch |
| **Parallelization** | Q5 scale | Fan-out to multiple pi/aider instances |
| **Orchestrator-subagents** | Q5 full | orchestrator + entire subagent roster |
| **Evaluator-optimizer** | Q4 reflection | Single agent + debugger in critique loop |
| **Autonomous agent (HITL)** | Q4/Q5 with safety gates | orchestrator with human checkpoint before destructive ops |

---

## 5. Working Rules

- **Choose pattern before topology.** Don't wire agents until the decision tree answer is clear.
- **Cheapest sufficient first.** Escalate only when a concrete bottleneck justifies it.
- **Surgeon rule for aider.** One packet, one file, one concern. If the packet touches three files, it's three aider calls.
- **Critic independence.** Reflection only works when the critic can disagree. If the same model generates and critiques, add a framing layer or use a different model.
- **No double duties.** If a role would immediately pass a task to the next role without adding value, skip it.
- **Use `agentic-design-patterns`** for the full decision tree detail and LangGraph contract.
- **Use `agentic-harness`** when the problem is harness coherence, legality, or self-repair.
- **Use `agent-governance`** for safety rails, trust tiers, and audit when agents can take destructive actions.
