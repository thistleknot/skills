---
name: cognitive-taxonomy
description: >
  Reference skill encoding the unified memory taxonomy from four papers on agentic
  memory: implicit/explicit/agentic paradigms (2601.09113), forms/functions/dynamics
  (2512.13564), biological-artificial crosswalk (2512.23343), neuro-symbolic dual-process
  (2603.15280). Use when classifying a memory pattern, choosing an architecture,
  explaining why vector+BM25 alone is insufficient, or deciding what kind of memory
  to use for a given task type.
status: staged
tier: L2
last_validated: 2026-05-02
supersedes: []
validation_method: session
---

# Cognitive Taxonomy — Memory Classification Reference

## Core Thesis

Memory is not one thing. Four recent surveys converge on the same conclusion:
memory is multi-layered, and each layer serves a different cognitive function.

This skill provides a unified classification system drawn from:

- **AI Hippocampus** (2601.09113) — implicit/explicit/agentic paradigms
- **Memory in the Age of AI Agents** (2512.13564) — forms/functions/dynamics
- **AI Meets Brain** (2512.23343) — biological-artificial crosswalk
- **NS-Mem** (2603.15280) — neuro-symbolic dual-process integration

## When to Use

- Classifying an existing memory skill (which layer does it serve?)
- Designing a new memory system (which layers are needed?)
- Explaining why vector+BM25 alone is insufficient (the System 2 gap)
- Deciding what kind of memory to use for a given task type
- Cross-checking whether a design is over-reliant on one paradigm

## When NOT to Use

- Implementing memory mechanics (use `procedural-memory` or `agentic_kg_memory`)
- Managing project state (use `memory-bank`)
- Evolving skills (use `skill-wiki`)

---

## 1. Three Paradigm Taxonomy (AI Hippocampus)

Every memory system falls into exactly one of three paradigms by **where the knowledge lives**.

| Paradigm | Where Knowledge Lives | Examples |
|---|---|---|
| **Implicit** | Neural weights (parameters) | Pre-trained LLM weights, fine-tuning, RLHF policies |
| **Explicit** | External storage + retrieval | Vectors, knowledge graphs, textual corpora |
| **Agentic** | Persistent temporal structures | Memory cards, episodic traces, skill DAGs |

**Key insight:** Implicit memory provides general patterns and world knowledge.
Explicit memory provides scalable, queryable, updatable facts. Agentic memory
provides temporal continuity across interactions.

A complete system needs all three. A system with only implicit memory has stale
knowledge and no personal history. A system with only explicit memory has no
general reasoning ability. A system with only agentic memory has no generalization
to novel situations.

**In this skill set:**
- Implicit = not skinned (pre-existing model weights)
- Explicit = `agentic_kg_memory` (triplets, BM25, Chroma, vectors)
- Agentic = `procedural-memory` + `context-compaction` + `continuity-log`

## 2. Forms/Functions/Dynamics Taxonomy (Memory in the Age of AI Agents)

### Forms (What is stored)

| Form | Description | Examples |
|---|---|---|
| **Token-level** | Raw text tokens retained in context | In-context learning, prompt cache |
| **Parametric** | Knowledge encoded in model weights | Fine-tuning, instruction tuning |
| **Latent** | Information hidden in representation space | Prompt-induced latent memory, LoRA adapters |

### Functions (What memory does)

| Function | Purpose | Query Pattern |
|---|---|---|
| **Factual** | Store and retrieve discrete facts | "What is X?" "Who did Y?" |
| **Experiential** | Learn from past outcomes | "What happened last time?" "How did we solve Z?" |
| **Working** | Support immediate reasoning | "Given X, what should I do next?" |

### Dynamics (How memory changes over time)

| Phase | Process | Mechanism |
|---|---|---|
| **Formation** | Raw experience to structured record | Distillation, extraction, summarization |
| **Evolution** | Memory updates with new evidence | Reinforcement, weakening, forgetting curves |
| **Retrieval** | Accessing stored memory for current task | Vector similarity, symbolic query, hybrid |

**Decision matrix for skill design:** Every memory skill serves one function,
uses one or more forms, and operates at one or more dynamic phases.

## 3. Biological-Artificial Crosswalk (AI Meets Brain)

Maps human memory mechanisms to artificial systems. Not metaphorical structural
isomorphies that suggest concrete design patterns.

| Biological System | Artificial Counterpart | Function |
|---|---|---|
| **Sensory memory** (milliseconds) | Context window token cache | Transient perception |
| **Short-term/Working memory** (seconds-minutes) | `context-compaction` fast tier | Active reasoning |
| **Hippocampus** (encoding + consolidation) | SK-Gen pipeline in `procedural-memory` | Episodic to semantic transfer |
| **Prefrontal cortex** (procedural rules) | Logic layer DAGs in `procedural-memory` | System 2 reasoning |
| **Neocortex** (semantic knowledge) | `agentic_kg_memory` semantic layer | Stable knowledge |
| **Synaptic weights** (long-term storage) | Implicit memory (model params) | General patterns |
| **Ebbinghaus forgetting curve** | Configurable decay in consolidation policy | Noise suppression |

**Key engineering insight:** Biological memory is not a pipeline it is a **network**
with feedback loops. The hippocampus sends memories to the cortex for consolidation,
but the cortex also sends schemas back to guide hippocampal encoding. Translation:
`agentic_kg_memory` (semantic schemas) should guide `procedural-memory` (episodic
distillation), and procedural DAGs should update semantic entities in both directions.

## 4. Neuro-Symbolic Dual-Process (NS-Mem)

Extends the three-paradigm taxonomy with a **reasoning mode axis**:

| Reasoning Mode | Memory Layer | Retrieval Method | Use Case |
|---|---|---|---|
| **System 1** (intuitive) | Episodic + semantic | Vector similarity, BM25 | Factual recall, semantic matching |
| **System 2** (analytical) | Logic/procedural | Deterministic DAG query | Constraint satisfaction, step ordering |

**Why this matters for your skill set:** Currently, `agentic_kg_memory` handles
System 1 retrieval well (BM25 + NLI + vector similarity). It does **not** handle
System 2 reasoning over structured dependencies. That requires the logic/procedural
layer from NS-Mem DAG-based symbolic queries that can answer "what comes after?",
"what are the prerequisites?", and "what if constraint X is not met?".

The NS-Mem paper shows **+4.35% accuracy gain** from adding this layer, with up to
**+12.5% on constrained reasoning queries**. This is not incremental it closes a
fundamental gap.

## 5. Query Classification to Memory Routing

From NS-Mem, the most important engineering decision is **query routing**:

```
Incoming query
    |
    v
Query Classification
    |
 +--+---+----------+----------+
 v      v          v          v
Factual Constraint  Procedural  Open-ended
    |      |          |           |
    v      v          v           v
Semantic Logic     Episodic     Multi-layer
Layer      Layer    + Logic      hybrid
            |       Layer
            v
       Symbolic
        DAG
         query
```

| Query Type | Example | Routing |
|---|---|---|
| **Factual** | "What did the user say about X?" | Semantic layer to vector similarity |
| **Constraint** | "Can I proceed given Y is broken?" | Logic layer to DAG query with constraint filter |
| **Procedural** | "How do I do Z?" | Procedural DAG to step enumeration |
| **Open-ended** | "What should I do?" | Multi-layer hybrid to all layers, ranked |

This is the single most impactful design decision for any memory-augmented agent.

## 6. Skill-to-Taxonomy Mapping

| This Skill Set | Paradigm | Function | Reasoning Mode |
|---|---|---|---|
| `agentic_kg_memory` | Explicit | Factual + experiential | System 1 |
| `kg_ontology` | Explicit (entity identity) | Factual | System 1 |
| `memory-bank` | Explicit + agentic | Factual + experiential | System 1 |
| `context-compaction` | Agentic | Working | System 1 (volatile) |
| `continuity-log` | Agentic | Experiential | System 1 |
| `procedural-memory` (new) | Agentic + explicit | Experiential + working | System 1 + System 2 |
| `skill-wiki` | Agentic (procedural) | Working (procedural) | System 1 (skill selection) |
| `memory-architecture` (new) | Meta-knowledge | Factual (about memory) | System 1 |
| `cognitive-taxonomy` (new) | Meta-knowledge | Factual (about memory) | System 1 |

## Evidence

- AI Hippocampus (2601.09113) implicit/explicit/agentic taxonomy, published TMLR 2025
- Memory in the Age of AI Agents (2512.13564) forms/functions/dynamics taxonomy, 46 authors
- AI Meets Brain (2512.23343) biological-artificial crosswalk, cognitive neuroscience bridge
- NS-Mem (2603.15280) neuro-symbolic dual-process, +4.35% accuracy gain, code available
