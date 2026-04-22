# ReAct Agent Skill

A structured Reason-Act-Observe loop for autonomous multi-step task execution
in VS Code Copilot agent mode. Handles refactoring, migrations, builds, pipeline
construction, data processing, and infrastructure setup — any task where the
agent must plan, act, observe results, and iterate until done.

## How to Invoke

**Automatic** — Just describe a multi-step task. The skill triggers on phrasing
that implies autonomous execution:

> *"Refactor all the fixture files in this project"*
> *"Build a FastAPI endpoint for user auth"*
> *"Migrate the database schema to use UUIDs"*

**Explicit** — Name it directly:

> *"Use the react_agent skill to implement X"*

**With memory** — Pull from past cases before planning:

> *"Use the react_agent skill. Check memory for similar past tasks. Task: X"*

Copilot reads the `description` field in SKILL.md to decide whether to load
the skill. You never need to reference HARNESS.md, MEMORY.md, or QUALITY.md
directly — the skill orchestrates them internally.

## Architecture

```
SKILL.md ─── The Loop
  │           Defines the full execution lifecycle:
  │           Reframe → Recon → Plan → Execute (ReAct) → Complete
  │
  ├── HARNESS.md ─── The Brake
  │     Validation layer between intent and execution.
  │     Fires inside every ACT step: structural, semantic,
  │     and environmental checks. Adversarial pre-ACT pass
  │     (Skeptic / Scope Guard / Verifier). Rejects illegal
  │     actions before they run.
  │
  ├── MEMORY.md ─── The Brain
  │     Two systems:
  │     1. Fact-Grounded Query Pipeline (8 steps)
  │        Thesis-first abductive reasoning over a knowledge base.
  │        query → objective → premises → entailment → telos →
  │        source retrieval → graph extraction → response
  │     2. Case Memory (episodic → semantic promotion)
  │        4-phase retrieval, utility scoring (MemRL),
  │        lifecycle management, knowledge article updates.
  │
  └── QUALITY.md ─── The Finish Line
        5-dimension exit check: Safety, Completeness,
        Executability, Maintainability, Cost-Awareness.
        No subtask closes without passing this gate.
```

## Reading Order

| Order | File | What you learn | Time |
|-------|------|----------------|------|
| 1 | **SKILL.md** | The outer loop, LLM routing, phases 0–4, ReAct steps, anti-patterns, state machine diagram | 5 min |
| 2 | **HARNESS.md** | What prevents bad actions — structural/semantic/environmental validation, retry protocol, scope guard | 3 min |
| 3 | **MEMORY.md** | How knowledge is stored, retrieved, and reasoned over — the fact-grounded pipeline, case format, 4-phase retrieval, retention rules, lifecycle management | 8 min |
| 4 | **QUALITY.md** | What "done" means — the 5-dimension check and rating scale | 2 min |

SKILL.md is the backbone — read it first, even if you only skim. Everything
else plugs into the phases and steps it defines.

## Execution Flow

```
User task
  │
  ▼
Phase 0: Reframe ──────────── task.md       (abstract requirements, acceptance criteria)
Phase 1: Recon ────────────── recon.md      (survey codebase, map dependencies)
Phase 2: Plan ─────────────── plan.md       (ordered subtasks with validation criteria)
  │
  │  [user confirms plan, or autonomous mode proceeds]
  │
  ▼
Phase 3: Execute (per subtask)
  │
  │  ┌─────────────────────────────────────────────┐
  │  │ REASON    Society of Thought pass            │
  │  │           (Proposer / Skeptic / Verifier)    │
  │  │                                              │
  │  │ VALIDATE  Harness check (HARNESS.md)         │
  │  │           legal? in scope? reversible?       │
  │  │                                              │
  │  │ ACT       Execute the change                 │
  │  │                                              │
  │  │ OBSERVE   Read output, check artifact,       │
  │  │           run tests                          │
  │  │                                              │
  │  │ REFLECT   Log to memory, decide next step    │
  │  │           success → next step                │
  │  │           failure → diagnose → retry/pivot   │
  │  └─────────────────────────────────────────────┘
  │
  ▼
Phase 4: Completion
  ├── Verify acceptance criteria (task.md)
  ├── Run full validation suite
  ├── 5-dimension quality check (QUALITY.md)
  └── Generate summary
```

## Working Directory

The skill writes its state to `.react_agent/` in the project root:

```
.react_agent/
├── task.md            Reframed requirements and acceptance criteria
├── recon.md           Reconnaissance findings
├── plan.md            Ordered subtask plan
├── progress.md        Current status dashboard
├── changes.jsonl      Append-only action log
├── memory.jsonl       Append-only outcome/lesson log
├── index_summary.md   Compressed working context (long tasks)
├── archive/           Full tool outputs under stable keys
└── cases/             Completed task episodes (case_NNN.json)
```

## Prerequisites

**Required:**
- VS Code with GitHub Copilot agent mode

**For LLM routing (optional but recommended):**
- [copilot-proxy](http://127.0.0.1:8069/v1) running locally
- Model routing: `gpt-4o` for reasoning/planning, `gpt-4.1` for code generation

**For the Fact-Grounded Query Pipeline (MEMORY.md Steps 1–8):**
- Ollama with Qwen3-2b (objective extraction, telos synthesis, graph extraction)
- KNWLER (SPO triplet extraction)
- MSMarco (entailment scoring)
- Post-processed markdown files as the knowledge article index

## Research Basis

The skill draws from 12 research papers across five areas:

| Area | Techniques | Papers |
|------|-----------|--------|
| Memory structure | A-MEM (Zettelkasten notes), SimpleMem (density gate) | Xu et al. 2025, Zeng et al. 2025 |
| Retrieval | MemoRAG (pre-scan), HippoRAG (PPR graph walk), MemR³ (evidence-gap) | Qian et al. 2024, Gutiérrez et al. 2024, Kuang et al. 2024 |
| Utility scoring | MemRL (EMA Q-value), Memento (Q-learning, write-on-completion) | arXiv:2601.03192, Qu et al. 2025 |
| Lifecycle | MemOS (active/dormant/archived), Memex(RL) (indexed context) | Zhu et al. 2025, Nair et al. 2025 |
| Quality | RAG-Modulo (critic notes), RAPTOR (hierarchical index at scale) | Besta et al. 2024, Sarthi et al. 2024 |
| Reasoning | Society of Thought (multi-perspective deliberation) | Kim et al. 2025 |
