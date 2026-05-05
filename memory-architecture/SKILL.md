---
name: memory-architecture
description: >
  Unified memory architecture reference synthesized from four papers on agentic
  memory. Defines the canonical layered architecture (implicit/explicit/agentic),
  provides design templates for combining memory skills into coherent systems.
  Use when designing a new memory-augmented agent system or evaluating an existing
  one for gaps.
status: active
tier: L2
last_validated: 2026-05-03
supersedes: []
validation_method: documentation_review
---

# Memory Architecture — Unified Design Reference

## Core Thesis

Memory architecture is not a single component — it is a **stack of complementary
layers**, each addressing a distinct cognitive function. The four memory papers
converge on the same layered structure. This skill codifies that consensus into
reusable design templates.

**Reference papers:**
- AI Hippocampus (2601.09113) — implicit/explicit/agentic paradigms
- Memory in the Age of AI Agents (2512.13564) — forms/functions/dynamics
- AI Meets Brain (2512.23343) — biological-artificial crosswalk
- NS-Mem (2603.15280) — neuro-symbolic dual-process memory

## When to Use

- Designing a new agent with memory capabilities
- Evaluating an existing memory system for architectural gaps
- Deciding which memory skills to compose for a specific use case
- Onboarding a new developer to the memory stack
- Explaining why a system needs more than just "add a vector DB"

## When NOT to Use

- Implementing individual memory mechanics (use the specific skills)
- Making runtime decisions (use `cognitive-taxonomy` for classification)
- Managing project state (use `memory-bank`)

---

## The Canonical Memory Stack

Every memory-augmented agent system should compose these layers from the bottom up:

```
 +------------------------------------------------------------------------+
 |  Layer 0: Implicit Memory                                              |
 |  What it stores: General patterns, world knowledge, reasoning ability  |
 |  Storage: Model parameters (pre-trained weights)                       |
 |  Update: Full fine-tuning (expensive, infrequent)                      |
 |  Skills: N/A (pre-existing)                                            |
 |  Gap: Stale knowledge, no personal history                             |
 +---------------------------+--------------------------------------------+
                             |
 +---------------------------v--------------------------------------------+
 |  Layer 1: Explicit Memory — Semantic Layer                             |
 |  What it stores: Factual knowledge, entity attributes, world facts     |
 |  Storage: Vectors (Chroma), Knowledge graphs (SQLite), BM25 index      |
 |  Update: Append + consolidate (reinforce/weaken)                       |
 |  Skills: agentic_kg_memory + kg_ontology                                |
 |  Retrieval: Vector similarity + BM25 + NLI validation                  |
 |  Reasoning: System 1 (intuitive, inductive)                            |
 +---------------------------+--------------------------------------------+
                             |
 +---------------------------v--------------------------------------------+
 |  Layer 2: Agentic Memory — Episodic Layer                              |
 |  What it stores: Timestamped observations, experiences, traces         |
 |  Storage: Session artifacts, JSON/MD files, task execution logs        |
 |  Update: Append (always), summarize periodically                       |
 |  Skills: continuity-log, memory-bank (activeContext)                    |
 |  Retrieval: Temporal proximity + semantic similarity                   |
 |  Reasoning: System 1 (what happened, when)                             |
 +---------------------------+--------------------------------------------+
                             |
 +---------------------------v--------------------------------------------+
 |  Layer 3: Agentic Memory — Procedural Layer                            |
 |  What it stores: Reusable procedures, step dependencies, constraints   |
 |  Storage: Procedural DAGs + dual-index vectors                         |
 |  Update: SK-Gen batch distillation + EMA incremental refinement        |
 |  Skills: procedural-memory, skill-wiki (manual authoring)             |
 |  Retrieval: Neural discovery + symbolic DAG query                      |
 |  Reasoning: System 1 (fuzzy) + System 2 (deterministic)               |
 +---------------------------+--------------------------------------------+
                             |
 +---------------------------v--------------------------------------------+
 |  Layer 4: Working Memory                                                 |
 |  What it stores: Active task state, recent tool calls, current plan    |
 |  Storage: In-context (fast tier) to compacted summaries (slow)         |
 |  Update: Continuous, with eviction triggers                            |
 |  Skills: context-compaction + continuity-log (compact-safe)             |
 |  Retrieval: Direct access (in-context) + rehydration (from compact)    |
 |  Reasoning: Both System 1 & 2 (holds the active reasoning trace)       |
 +---------------------------+--------------------------------------------+
                             |
 +---------------------------v--------------------------------------------+
 |  Memory Lifecycle (across all layers)                                   |
 |  Formation: Extraction from raw experience to structured records        |
 |  Consolidation: Pattern discovery (SK-Gen), reinforcement, fusion       |
 |  Retrieval: Neural + symbolic hybrid                                    |
 |  Decay: EMA-based forgetting, configurable pruning                     |
 |  Evaluation: Semantic QA, episodic recall, constraint satisfaction       |
 +------------------------------------------------------------------------+
```

## Layer Details and Cross-Layer Relationships

### Layer 0: Implicit Memory

**Role:** Foundation for all reasoning. Provides zero-shot ability to understand
language, recognize patterns, and perform basic inference.

**What it lacks:** No temporal continuity, no personal history, no ability to
learn from specific interactions without expensive retraining.

**Engineering implication:** Implicit memory is a one-way street (training to usage).
Agents with only implicit memory cannot "remember" anything outside their training
distribution. Explicit layers are mandatory for any agent that needs to learn.

### Layer 1: Explicit Semantic Memory

**Role:** Scalable, queryable, updatable factual knowledge. The "encyclopedia"
layer — always available, always fresh.

**Skills:**
- `agentic_kg_memory`: Triplet storage, BM25 narrowing, NLI validation, dense
  retrieval via Chroma, memory evolution (reinforce/weaken/add)
- `kg_ontology`: Entity identity resolution — ensures "SOW" and "Statement of
  Work" map to the same canonical node. Prevents duplicate node accumulation.

**What it lacks:** No temporal ordering, no step dependencies, no System 2 reasoning.
Cannot answer "what came first?" or "what is the prerequisite of X?".

**Cross-layer connections:**
- **Downstream:** Feeds entity anchors to episodic layer (Layer 2)
- **Upstream:** Receives procedural rules from Layer 3 that expand entity attributes
- **Peer:** Shares Chroma + SQLite backends with episodic layer

### Layer 2: Episodic Memory

**Role:** Timestamped records of what happened. Enables the agent to answer personal
experience questions: "What did we do last time?" "How did we solve this before?"

**Skills:**
- `continuity-log`: Compact-safe decision packets between session boundaries
- `memory-bank` (activeContext.md): Current session state, immediate next steps
- `memory-bank` (progress.md): Milestone history, what changed, known issues

**What it lacks:** No pattern extraction (raw records require manual searching),
no procedural generalization (can recall what happened but not extract reusable procedures).

**Cross-layer connections:**
- **Downstream:** Action sequences feed into SK-Gen in procedural layer (Layer 3)
- **Upstream:** Receives entity references from semantic layer (Layer 1)
- **Peer:** Shares entity anchors with semantic layer; uses compaction from Layer 4

### Layer 3: Procedural Memory

**Role:** Reusable procedures with step dependencies, constraints, and alternatives.
The "how-to" layer that enables System 2 reasoning over structured knowledge.

**Skills:**
- `procedural-memory`: SK-Gen pipeline for automatic procedure extraction from
  episodic traces, EMA-based incremental refinement, hybrid neural + symbolic
  retrieval, knowledge fusion across sessions
- `skill-wiki`: Manual skill authoring and curation (completes auto-discovered ones)

**What it lacks:** Automatic SK-Gen requires sufficient episodic data (> 5 occurrences
of similar procedures). Rare or novel procedures must be manually authored.

**Cross-layer connections:**
- **Downstream:** Consumes episodic records from Layer 2
- **Upstream:** Updates semantic attributes when procedures reveal new entity properties
- **Peer:** Procedural DAGs reference episodic nodes for evidence traceability

### Layer 4: Working Memory

**Role:** The active reasoning workspace. Holds what the agent is currently thinking
about, enabling both System 1 (intuitive) and System 2 (analytical) reasoning.

**Skills:**
- `context-compaction`: Tiered eviction (fast/slow/archive), compaction triggers,
  PreCompact/PostCompact hooks, MemGPT-inspired paging
- `continuity-log`: Compact-safe decision packets that survive compaction

**What it lacks:** Finite capacity. Everything that exceeds context window must be
evicted to slower layers (1-3). The eviction policy determines what information
survives the transition.

**Cross-layer connections:**
- **Consolidation:** Decisions made here are logged to continuity-log (Layer 2)
- **Refresh:** Can pull facts from semantic layer (Layer 1) during reasoning
- **Eviction:** Old working memory is compacted, new info takes its place

## Design Templates by Use Case

### Template A: Factual Knowledge Base (RAG-lite)

```
Implicit -> Explicit (agentic_kg_memory) -> Working
```

**For:** Agents that need up-to-date factual answers but no procedural reasoning.
**Layers used:** 0, 1, 4
**Missing:** Layers 2, 3 — no episodic memory, no learned procedures
**Accuracy floor:** System 1 reasoning only

### Template B: Personal Assistant with Memory

```
Implicit -> Explicit -> Episodic -> Working
```

**For:** Personal agents that remember user preferences, past conversations, and
accumulate experience over time.
**Layers used:** 0, 1, 2, 4
**Missing:** Layer 3 — no learned procedures (but may not need them)
**Accuracy floor:** Factual + experiential recall

### Template C: Autonomous Agent with Procedural Reasoning

```
Implicit -> Explicit -> Episodic -> Procedural -> Working
```

**For:** Agents that operate in open-ended environments, need to learn procedures
from experience, and must support constraint-aware reasoning.
**Layers used:** ALL
**Performance:** +4.35% over Template B, up to +12.5% on constrained queries
**This is the target architecture** for production-grade autonomous agents.

### Template D: Research / Knowledge Synthesis Pipeline

```
Implicit -> Explicit (dense + graph) -> Procedural (knowledge graph DAGs)
```

**For:** Deep research, literature synthesis, claim verification.
**Layers used:** 0, 1, 3 (procedural for claim chains and evidence trails)
**Missing:** Layers 2, 4 (episodic/working less relevant for batch analysis)

## Integration Points

### Entity Anchor Flow (Layer 1 to Layer 2)

```
Episode arrives with entity mentions
        |
        v
kg_ontology resolves entities to canonical DKG nodes
        |
        v
Episodic record links to entity anchors
        |
        v
Semantic layer creates/updates entity nodes
        |
        v
Entity anchors enable cross-layer recall:
  - All episodes involving this entity (episodic -> entity)
  - All entity attributes (semantic -> entity)
  - All procedures using this entity (procedural -> entity)
```

### Procedure Discovery Flow (Layer 2 to Layer 3)

```
Sufficient episodic records accumulate
        |
        v
SK-Gen: extract action sequences
        |
        v
PrefixSpan: find recurring patterns
        |
        v
LLMVerify: score procedural quality
        |
        v
DAG construction + index generation
        |
        v
Logic Node added to procedural layer
        |
        v
Can now answer: "How do I do X?" with step sequences,
prerequisites, and constraint-aware alternatives
```

### Query Routing (Layer 4 to Layers 1-3)

```
Working memory receives query
        |
        v
cognitive-taxonomy: classify query type
        |
 +----+---+----------+----------+
 v      v          v          v
Factual Constraint  Procedural  Open-ended
        |      |          |           |
        v      v          v           v
Layer 1  Layer 3    Layer 3     Layers 1+2+3
```

### Memory Lifecycle (All Layers)

```
Formation  ->  Consolidation  ->  Retrieval  ->  Decay
   |              |                |            |
   v              v                v            v
Extraction   Pattern mining    Neural +      EMA decay
              Knowledge fusion  symbolic      Configurable
              Reinforce/weaken  query         pruning
```

## Anti-Patterns

| Anti-Pattern | Symptom | Fix |
|---|---|---|
| **Vector-only memory** | Only Layer 1, no Layer 3 | Add `procedural-memory` for System 2 reasoning |
| **Episodic dump** | Layer 2 grows without consolidation | Add SK-Gen distillation on fixed schedule |
| **No entity anchors** | Duplicate nodes across episodic and semantic | Add `kg_ontology` resolution |
| **Working memory overflow** | Frequent context compaction with state loss | Add `continuity-log` with `do_not_redo` field |
| **No decay policy** | Memory bloat, degraded retrieval | Add EMA-based forgetting or Ebbinghaus-style decay |
| **Manual-only procedures** | No auto-discovery from experience | Enable SK-Gen batch distillation |

## Evidence

- AI Hippocampus (2601.09113) implicit/explicit/agentic paradigm taxonomy
- Memory in the Age of AI Agents (2512.13564) forms/functions/dynamics
- AI Meets Brain (2512.23343) biological-artificial crosswalk, lifecycle
- NS-Mem (2603.15280) neuro-symbolic dual-process architecture, +4.35% empirical gain
- MemGPT (arXiv:2310.08560) tiered memory architecture foundation
<!-- consolidation:see-also:start -->
## See Also
[[cognitive-taxonomy]]  [[procedural-memory]]  [[context-compaction]]
<!-- consolidation:see-also:end -->
