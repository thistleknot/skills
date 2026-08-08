# Agentic Memory Integration

Synthesized from four recent papers on memory in AI agents. Each feature is tagged with its source paper and mapped to an existing or proposed skill.

---

## Source Papers

| # | arXiv | Title |
|---|---|---|
| 1 | 2601.09113 | The AI Hippocampus: How Far are We From Human Memory? (Jia et al.) |
| 2 | 2603.15280 | Advancing Multimodal Agent Reasoning with Long-Term Neuro-Symbolic Memory (Jiang et al.) |
| 3 | 2512.13564 | Memory in the Age of AI Agents (46 authors) |
| 4 | 2512.23343 | AI Meets Brain: Memory Systems from Cognitive Neuroscience to Autonomous Agents (Liang et al.) |

---

## New Skills

### 1. cognitive-taxonomy

**Source:** Papers 1, 2, 3, and 4 (synthesis)

A unified classification system for all memory patterns. Solves the problem of "which kind of memory do I need for this task?" by providing one consistent taxonomy.

**Features:**
- Three-paradigm taxonomy (implicit/explicit/agentic) from Paper 1
- Forms/functions/dynamics framework from Paper 3
- Biological-artificial crosswalk (brain to AI mappings) from Paper 4
- Neuro-symbolic dual-process reasoning axis (System 1 vs System 2) from Paper 2
- Query classification to memory routing decision tree
- Complete skill-to-taxonomy mapping for the entire skill set

**Mapped to:** `cognitive-taxonomy/SKILL.md`

---

### 2. procedural-memory

**Source:** Paper 2 (NS-Mem), empirical benchmark + public code

Direct implementation of the SK-Gen pipeline. The single highest-signal addition: +4.35% reasoning accuracy over pure neural memory, up to +12.5% on constrained queries.

**Features:**
- **Observation processing** — converts raw episodic traces to structured action sequences
- **Sequential pattern mining** — PrefixSpan for temporal-order-preserving pattern discovery
- **Knowledge verification** — LLM-based scoring of candidate procedures (0.0-1.0 quality rubric)
- **DAG construction** — procedural Directed Acyclic Graphs with START/GOAL anchors and edge attributes
- **Dual-index vectors** — goal-level (title-like) and step-level (body-like) embeddings for multi-granularity discovery
- **Incremental EMA updates** — exponential moving average on index vectors to prevent catastrophic forgetting
- **Transition count statistics** — probabilistic step ordering from observed execution frequencies
- **Knowledge fusion** — merge single-path DAGs from multiple sessions into unified multi-path DAGs
- **Hybrid retrieval** — neural discovery (System 1) + symbolic DAG query (System 2)

**Mapped to:** `procedural-memory/SKILL.md`

---

### 3. memory-architecture

**Source:** Papers 1, 2, 3, and 4 (synthesis)

Canonical layered architecture template. Solves the "what layers does my agent need?" design question with four concrete templates.

**Features:**
- **5-layer stack diagram** — implicit / semantic / episodic / procedural / working
- **Layer detail specs** — what each store, how it updates, which skills compose it, what reasoning mode it supports
- **Cross-layer connection flows** — entity anchor flow, procedure discovery flow, query routing, memory lifecycle
- **4 design templates:**
  - Template A: RAG-lite (Implicit -> Explicit -> Working)
  - Template B: Personal Assistant (adds Episodic)
  - Template C: Autonomous Agent (adds Procedural) — target architecture
  - Template D: Research/Synthesis Pipeline
- **Anti-patterns catalog** — vector-only memory, episodic dump, no entity anchors, no decay policy, manual-only procedures

**Mapped to:** `memory-architecture/SKILL.md`

---

## Enhancement Patches

### 4. agentic_kg_memory — Hybrid Retrieval Mode

**Source:** Paper 2 (NS-Mem)

Adds System 2 reasoning to existing System 1 (BM25+NLI+vector) retrieval. Currently `agentic_kg_memory` handles fuzzy semantic retrieval but cannot answer "what comes after?" or "what if prerequisites change?".

**Features:**
- Query classifier (factual / constraint / procedural / open-ended routing)
- Symbolic query engine with DAG traversal primitives (prerequisites, alternatives, constraint checking, transition probabilities)
- RRF merge strategy for fusing neural and symbolic retrieval results
- Schema changes: `page_type` column, `procedure_dag` JSON column in wiki_pages table

**Mapped to:** `agentic_kg_memory/enhancements/MEMORY_ENHANCEMENT.md`

---

### 5. context-compaction — Type-Aware Consolidation Policy

**Source:** Paper 4 (Ebbinghaus forgetting curve + factual/experiential/working memory lifecycle)

Current compaction uses a uniform eviction policy. Biological systems separate stable semantics from volatile working memory. This patch adds that distinction.

**Features:**
- Memory type annotation on PreCompact packets (factual / experiential / working)
- Type-aware eviction ordering — factual always kept, experiential via decay, working evicted first
- Exponential decay for experiential items (configurable half-life, default 7 days)
- Budget allocation: 80% factual / 15% experiential / 5% working
- Rehydration ordering by stability layer (factual first, working last)

**Mapped to:** `context-compaction/enhancements/MEMORY_ENHANCEMENT.md`

---

### 6. skill-wiki — Procedural DAG Extraction from Continuity Logs

**Source:** Paper 2 (SK-Gen pipeline adapted)

`skill-wiki` requires manual skill promotion. Organic procedures that emerge across many task executions in continuity logs are missed. This patch auto-discovers them.

**Features:**
- Pattern detection heuristics: sequence co-occurrence, tool clustering, decision repetition, failure pattern clustering
- Quality scoring with thresholds (0.6 = enhance existing, 0.8 = propose new skill, 1.0 = auto-promote)
- SkillProposal data model with traceability to source continuity log entries
- Discovery triggers: task completion hook, daily batch scan, post-promotion re-scan
- Rate limit: max 3 proposals per scan

**Mapped to:** `skill-wiki/enhancements/MEMORY_ENHANCEMENT.md`

---

### 7. kg_ontology — Temporal Entity Resolution

**Source:** Paper 4 (hippocampus vs prefrontal cortex entity state tracking)

`kg_ontology` resolves surface forms to canonical nodes but assumes entities are static. Entities change state over time and the current layer loses that dimension.

**Features:**
- Entity state versioning via new `entity_states` SQL table (canonical node stays stable, states evolve)
- Temporal query resolution — "old config" resolves to v1.2 state, "new config" resolves to v2.0 state
- State transition DAG — tracks entity evolution paths
- `temporal_resolution.py` — new module for timestamp-aware entity lookups
- Fallback: no temporal context returns latest state

**Mapped to:** `kg_ontology/enhancements/MEMORY_ENHANCEMENT.md`

---

## Implementation Order

| Phase | Skills | Timeline |
|---|---|---|
| 1 — Reference | cognitive-taxonomy, memory-architecture | Week 1 |
| 2 — Structural Core | procedural-memory, agentic_kg_memory enhancement, kg_ontology enhancement | Weeks 2-3 |
| 3 — Lifecycle Integration | skill-wiki enhancement, context-compaction enhancement, cross-skill wiring | Week 4 |
| 4 — Tuning | thresholds, accuracy validation, end-to-end testing | Week 5 |

Phase 1 skills have zero risk (reference-only, no behavior changes). Phases 2-3 are additive and backward-compatible.

## Evaluation Targets

| Feature | Metric | Target |
|---|---|---|
| Hybrid retrieval | Accuracy on constrained queries | +4.35% |
| Type-aware compaction | Factual items preserved across compaction | 100% |
| Skill discovery | Quality score >= 0.8 of proposals | >= 50% |
| Temporal resolution | Correct entity state for time-bound queries | >= 90% |
| Procedural memory | Auto-discovered procedures | >= 3 per 10 sessions |
