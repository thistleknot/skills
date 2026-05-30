---
name: agentic-orchestration
description: Unified orchestration protocol combining the MLM 5-question decision tree, Anthropic's agent pattern taxonomy, the live agent roster with role contracts, and Aider's architect/editor split as a concrete Planning+ReAct reference implementation. Use when designing or debugging a multi-agent system â€” before writing code and when diagnosing coordination failures.
status: active
last_validated: 2026-05-23
supersedes: []
validation_method: session
see_also: [agentic-design-patterns, agentic-harness, react-agent, agent-governance]
---
# Agentic Orchestration

Three layers in one doc:

1. **Pattern selection** â€” which shape to use before writing any code (decision tree)
2. **Agent roster** â€” the live role contracts and handoff rules for this stack
3. **Reference implementation** â€” Aider's architect/editor split as a concrete Planning+ReAct instantiation

---

## 1. Pattern Selection (Decision Tree)

Most failures are misreads of the problem, not execution failures. Run these five questions first.

### Q1 â€” Is the solution path known before execution starts?

- **Known** (invoice processing, onboarding flows): same steps every time â†’ Q2a
- **Unknown** (research, debugging, branching support): each step depends on prior output â†’ Q2b

### Q2a â€” Fixed deterministic workflow?

â†’ **Sequential Workflow**. Use the model only where interpretation is genuinely needed; deterministic code handles the rest. Failure mode: adding ReAct reasoning where every step is already defined.

### Q2b â€” Does the task need tool access?

Almost always yes â€” proceed to Q3. Tool use sits *under* the reasoning layer; a ReAct agent with tools is still ReAct.

### Q3 â€” Can you articulate task structure before execution begins?

- **Yes** (design â†’ implement â†’ test, provision-in-order, gather â†’ synthesize â†’ write) â†’ **Planning + ReAct** inside each step. Exposes dependencies early. Costs: upfront planning step, plan quality dependence, reduced flexibility.
- **No** (structure only emerges through feedback) â†’ **ReAct alone**, then Q4. Signal you chose wrong: the agent abandons the plan mid-run.

### Q4 â€” Does output quality beat response speed?

Add **Reflection** (generate â†’ critique â†’ refine) only when:
1. Clear, verifiable evaluation criteria exist (valid SQL, passing tests, complete contract)
2. Error cost justifies an extra pass (deployed code, client docs)

**Critic independence is load-bearing** â€” a critic that mirrors the generator just agrees. Use separate framing or a different model as critic.

- **Quality priority + explicit criteria** â†’ add Reflection on top
- **Speed priority or vague criteria** â†’ skip, go to Q5

### Q5 â€” Real specialization or scale bottleneck a single agent can't handle?

The trigger must be a **concrete bottleneck** â€” not architectural preference.

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
| **Single Agent + Reflection** | Quality > speed, explicit verifiable criteria | Generate â†’ Critique â†’ Refine; needs critic independence |
| **Multi-Agent Specialist** | Real scale or specialization bottleneck | Coordinator routes to specialists; adds coordination overhead |

### Pattern assumptions (what breaks each)

| Pattern | Assumes | Breaks when |
|---|---|---|
| ReAct | Next action not knowable in advance | Task has fixed structure â€” reasoning where execution belongs |
| Planning | Major structure identifiable upfront | Structure only emerges during execution â€” plan becomes a lie |
| Reflection | First-pass output often flawed; critique justified | No clear criteria; critic too aligned with generator â€” it just agrees |
| Multi-agent | Decomposition + specialization beats coordination cost | No real specialization need â€” overhead outweighs benefit |

### Failure signals â†’ fixes

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
| **oracle/planner** | qwen3.6-27b | Spec planning, decomposition, and class/function signatures/stubs. | â€” |
| **oracle/planner** | qwen3.6-35b | Spec planning and decomposition. Converts vague goals into acceptance criteria and task cards. | â€” |
| **designer** | qwen3.6-35b | Class/function signatures and stubs. No implementation. | â€” |
| **fixer/coder** | qwen3.6-35b | Spec translation only. Receives ambiguous/multi-file work, breaks into bounded packets, dispatches to @aider. Never touches files directly. | @aider |
| **librarian** | gemini-2.5-flash-lite | Web + docs search. External knowledge retrieval. | â€” |
| **observer/visionary** | qwen-vl-30b | Screenshot and diagram interpretation. Triggered first on any image attachment. | â€” |

### Subagents (agents block, callable from primaries)

| Agent | Model | Role | Bounded by |
|---|---|---|---|
| **pi** | step-3.5-flash | Inner harness. Accepts one bounded objective; runs scripts, returns output; routes internally to @aider/@handyman/@debugger. | One packet scope |
| **aider** | step-3.5-flash | Leaf editor. 2-pass: Reason â†’ Edit. One file, one concern per call. `subtask=DENY` â€” cannot spawn subagents. | Named files only |
| **handyman** | granite-4.1-8b | Mechanical file ops. Zero-reasoning tool calls: move, copy, sample, convert. | Named paths |
| **patcher** | gemma-4-26b | Known-file hotfix. Named file + concrete error â†’ immediate mutation + rerun. | Named file + known error |
| **debugger** | qwen3.6-35b | QA inspector. Stack traces, test failures, feedback loops. | Error isolation |
| **summarizer** | mimo-v2-flash | Context compression. Never edits code. | Compression only |

### Handoff rules

```
orchestrator
  â”œâ”€ image attached?          â†’ observer (immediately, before anything else)
  â”œâ”€ AIDER DIRECT: prompt?    â†’ aider (skip fixer entirely)
  â”œâ”€ file+change concrete?    â†’ aider (skip fixer entirely)
  â”œâ”€ smoke test?              â†’ pi
  â”œâ”€ known-file hotfix?       â†’ patcher
  â”œâ”€ pure file ops?           â†’ handyman
  â”œâ”€ multi-file / ambiguous?  â†’ fixer â†’ aider (packet chain)
  â”œâ”€ trace / test failure?    â†’ debugger
  â””â”€ web research?            â†’ librarian

pi (internal routing only)
  â”œâ”€ edit packet              â†’ aider
  â”œâ”€ file ops                 â†’ handyman
  â””â”€ failure / trace          â†’ debugger
```

**No double duties**: if fixer would just pass an already-concrete task to aider, skip fixer. Orchestrator calls aider directly.

### Routing priorities (orchestrator decision order)

1. Explicit user targeting (e.g. `@aider fix X`) â€” honor unless unsafe
2. `AIDER DIRECT:` prefix or concrete file+change â†’ aider
3. Image/screenshot â†’ observer
4. Smoke test / script execution â†’ pi
5. Known-file hotfix â†’ patcher
6. Pure file ops â†’ handyman
7. Multi-file / ambiguous spec â†’ fixer
8. Trace / test failure â†’ debugger
9. Web/doc research â†’ librarian
10. Default: direct answer or oracle for planning

---

## 3. Aider Architect/Editor as Planning+ReAct Reference

Aider's two-model split is the clearest real-world instantiation of Q3's "structure articulable upfront" branch:

| Aider concept | Anthropic pattern | This stack equivalent |
|---|---|---|
| **Architect** (reasons about what to change) | Planning layer | `coder.toml` â€” spec-packager. Reasons about which files and what to change, produces bounded packets |
| **Editor** (applies the change) | ReAct execution inside each step | `aider.toml` â€” leaf executor. Applies one packet, two-pass: reason â†’ edit |
| Architect â†’ Editor handoff | Plan stage â†’ execution stage | `fixer` dispatches bounded packet to `aider` |

The architect never touches files. The editor never re-plans. The interface between them is the packet: `{files, acceptance_criteria, exact_change_description}`.

**Why this matters for pattern selection**: whenever you have a task where you can write that packet before execution starts, you're in Q3-yes territory â†’ use Planning+ReAct (coderâ†’aider), not pure ReAct.

When you can't write the packet upfront (structure only emerges through execution), use ReAct alone â€” which in this stack means orchestrator â†’ pi or orchestrator â†’ aider directly with a looser prompt.

---

## 4. Anthropic Pattern Taxonomy (cross-reference backbone)

| Anthropic pattern | Decision tree branch | This stack expression |
|---|---|---|
| **Augmented LLM** | Q2b terminal (tools assumed) | Any single agent with MCP tools |
| **Prompt chaining** | Q2a / Q3-yes sequential | oracle â†’ designer â†’ fixer pipeline |
| **Routing** | Q5 specialization | orchestrator â†’ role dispatch |
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
