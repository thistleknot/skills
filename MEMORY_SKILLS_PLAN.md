# Plan: Agentic Memory — Skill Integration

## Source Papers

| # | arXiv | Title | Key Contribution |
|---|---|---|---|
| 1 | 2601.09113 | The AI Hippocampus | Implicit/explicit/agentic taxonomy, cross-modal coherence |
| 2 | 2603.15280 | Advancing Multimodal Agent Reasoning with Long-Term Neuro-Symbolic Memory | NS-Mem: 3-layer architecture, SK-Gen pipeline, hybrid retrieval |
| 3 | 2512.13564 | Memory in the Age of AI Agents | Forms/functions/dynamics taxonomy, 46-author landscape review |
| 4 | 2512.23343 | AI Meets Brain | Cognitive neuroscience agent crosswalk, memory security |

## What Shipped

### New Skills

#### 1. cognitive-taxonomy
**Location:** `skills/cognitive-taxonomy/SKILL.md`
**Status:** staged

A unified classification system synthesizing all four papers. Covers:
- Three-paradigm taxonomy (implicit/explicit/agentic from AI Hippocampus)
- Forms/functions/dynamics framework (from Memory in the Age of AI Agents)
- Biological-artificial crosswalk (from AI Meets Brain)
- Neuro-symbolic dual-process reasoning (from NS-Mem)
- Query classification to memory routing decision tree
- Complete skill-to-taxonomy mapping

**Use when:** Classifying a memory pattern, choosing an architecture, explaining why vector+BM25 alone is insufficient.

---

#### 2. procedural-memory
**Location:** `skills/procedural-memory/SKILL.md`
**Status:** staged

Direct implementation of NS-Mem's SK-Gen pipeline:
1. Observation processing — convert raw episodic traces to action sequences
2. Logic distillation (batch) — PrefixSpan mining, LLM verification, DAG construction, dual-index generation
3. Incremental maintenance — EMA-based index refinement, transition count updates
4. Knowledge fusion — merge multi-session single-path DAGs into multi-path DAGs
5. Hybrid retrieval — neural discovery (System 1) + symbolic DAG query (System 2)

**Metrics:** +4.35% accuracy over pure neural memory, up to +12.5% on constrained queries.

**Use when:** An agent needs to learn reusable procedures from raw experience without manual curation.

---

#### 3. memory-architecture
**Location:** `skills/memory-architecture/SKILL.md`
**Status:** staged

Canonical layered memory stack with four design templates:
- **Template A:** Factual Knowledge Base (Implicit to Explicit to Working), RAG-lite
- **Template B:** Personal Assistant with Memory (adds Episodic layer)
- **Template C:** Autonomous Agent (adds Procedural layer), target architecture
- **Template D:** Research / Knowledge Synthesis Pipeline

Includes:
- Full 5-layer architecture diagram with inter-layer connections
- Entity anchor flow, procedure discovery flow, query routing lifecycle
- Anti-patterns for common design mistakes

**Use when:** Designing a new agent with memory capabilities, evaluating existing systems for gaps, onboarding new developers.

---

### Enhancement Patches for Existing Skills

#### 4. agentic_kg_memory — Hybrid Retrieval Mode
**Location:** `skills/agentic_kg_memory/enhancements/MEMORY_ENHANCEMENT.md`

Adds System 2 reasoning capability to existing System 1 (BM25+NLI+vector) retrieval:
- **Query classifier** — factual/constraint/procedural/open-ended routing
- **Symbolic query engine** — DAG traversal primitives (prerequisites, alternatives, constraint checking)
- **RRF merge strategy** — reciprocal rank fusion for multi-path results
- **Schema changes** — `page_type` and `procedure_dag` columns

**Rationale:** `agentic_kg_memory` handles fuzzy semantic retrieval well but cannot answer "what comes after?" or "what if prerequisites change?". NS-Mem shows +12.5% gain on constrained queries.

---

#### 5. context-compaction — Type-Aware Consolidation Policy
**Location:** `skills/context-compaction/enhancements/MEMORY_ENHANCEMENT.md`

Adds memory-type classification to compaction decisions:
- **Factual memory** — never evict, 80% of budget
- **Experiential memory** — exponential decay (Ebbinghaus half-life = 7 days), 15% of budget
- **Working memory** — current eviction logic (volatile), 5% of budget

Updates `CompactionPacket` with `memory_type` annotation, adds exponential decay scoring, reorders rehydration by stability layer.

**Rationale:** Current uniform eviction treats user preferences the same as intermediate tool output. Biological systems also separate stable semantics from volatile episodic memory.

---

#### 6. skill-wiki — Procedural DAG Extraction from Continuity Logs
**Location:** `skills/skill-wiki/enhancements/MEMORY_ENHANCEMENT.md`

Adds automatic skill discovery from repeated task patterns:
- **Pattern detection heuristics** — sequence co-occurrence, tool clustering, decision repetition, failure pattern clustering
- **Quality scoring** — LLM assessment with thresholds (0.6 = enhance existing, 0.8 = propose new, 1.0 = auto-promote)
- **SkillProposal data model** — traceable to source continuity log entries
- **Discovery triggers** — task completion hook, daily batch scan, post-promotion re-scan
- **Rate limit** — max 3 proposals per scan

**Rationale:** `skill-wiki` requires manual promotion. Organic procedures in continuity logs are missed. This bridges the gap. SK-Gen-lite for skill discovery.

---

#### 7. kg_ontology — Temporal Entity Resolution
**Location:** `skills/kg_ontology/enhancements/MEMORY_ENHANCEMENT.md`

Adds temporal dimension to entity resolution:
- **Entity state versioning** — canonical node (identity) vs. entity_states (timeline) via new `entity_states` SQL table
- **Temporal query resolution** — "Jack's old bowl" resolves to bowl#1 at state T1, "Jack's new bowl" resolves to bowl#2 at state T2
- **State transition DAG** — tracks entity evolution (config.yaml v1.2 to v2.0)
- **temporal_resolution.py** — new module for timestamp-aware entity lookups
- **Fallback** — no temporal context returns latest state; ambiguous returns all versions with timestamps

**Rationale:** Entities change state over time. Current `kg_ontology` collapses all states into one node. Biological systems distinguish entity identity (neocortex) from entity state (hippocampus/prefrontal cortex).

---

## Relationship Map

```
                   cognitive-taxonomy (reference)
                          |  |  |  |
            +-------------+  |  |  +-------------+
            v              v  v              v
      +-----------+   +----------+    +-------------+
      |agentic_kg |   |procedural|    |  memory-    |
      |_memory    |   |  memory  |    |  architecture|
      +-----+-----+   +----+-----+    +-------------+
            |               |
      +-----+-----+   +-----+------+
      |enhance:   |   |enhance:    |
      |hybrid     |   |skill-wiki  |
      |retrieval  |   |from        |
      +-----------+   |continuity- |
                      |log         |
                      +------------+

  Existing skills with temporal entity
  patch from memory-architecture:
  - memory-bank       (factual/episodic layer)
  - context-compaction (working memory + consolidation policy)
  - continuity-log    (decision packets to procedural extraction)
  - kg_ontology       (entity identity to temporal resolution)
```

## Implementation Order

### Phase 1: Reference Layer (Week 1)
- `cognitive-taxonomy` — deploy as reference skill, immediately useful for all memory decisions
- `memory-architecture` — deploy as design reference
- No code changes, just skill metadata and documentation

### Phase 2: Structural Core (Weeks 2-3)
- `procedural-memory` — the biggest new capability, implements SK-Gen
- `agentic_kg_memory` enhancement — hybrid retrieval mode (requires procedural-memory's DAG infrastructure)
- `kg_ontology` enhancement — temporal entity resolution (feeds entity timelines)

### Phase 3: Lifecycle Integration (Week 4)
- `skill-wiki` enhancement — procedural DAG extraction from continuity logs (depends on procedural-memory's output)
- `context-compaction` enhancement — type-aware consolidation (independent but benefits from entity type annotations)
- Cross-skill wiring: entity anchor flow, procedure discovery flow, query routing

### Phase 4: Tuning and Validation (Week 5)
- Test all enhancements end-to-end with real agent sessions
- Tune thresholds (sigma, tau, delta, half-life, RRF weights)
- Validate accuracy gains from hybrid retrieval
- Validate pattern quality from skill discovery

## Rollout Strategy

Phase 1 skills have zero risk — they're reference skills that don't change any existing behavior. These can be deployed immediately.

Phases 2-3 are additive enhancements. Each is backward-compatible:
- Hybrid retrieval is opt-in for agentic_kg_memory (existing System 1 retrieval unchanged)
- Procedural-memory is a new layer, doesn't replace existing skills
- Type-aware compaction defaults to current behavior (working memory only) until explicit annotations are present
- Temporal entity resolution is opt-in (fallback to current-state resolution)
- Skill discovery is a new proposal pipeline that runs alongside manual authoring

**Recommendation:** Deploy Phase 1 immediately after user approval. Phase 2-3 on a scheduled iteration.

## Evaluation Criteria

| Enhancement | Success Metric | Target |
|---|---|---|
| Hybrid retrieval | Accuracy on constrained queries | +4.35% (per NS-Mem) |
| Type-aware compaction | Factual items preserved across compaction | 100% factual retention |
| Skill discovery | Quality of proposals (LLM score) | >= 0.8 for >= 50% of proposals |
| Temporal resolution | Correct entity state for time-bound queries | >= 90% correct |
| Procedural memory | Number of auto-discovered procedures | >= 3 per 10 sessions |

## Evidence

All four skills/enhancements are grounded in peer-reviewed research (arXiv 2025-2026, one in TMLR). NS-Mem includes public code, empirical benchmarks, and mathematical proofs for convergence and fusion consistency.
