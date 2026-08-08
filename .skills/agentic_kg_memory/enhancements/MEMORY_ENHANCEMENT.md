# Enhancement Patch: agentic_kg_memory — Hybrid Retrieval Mode

## Source

NS-Mem (2603.15280): query classification and hybrid retrieval for System 2 reasoning.

## Problem

`agentic_kg_memory` currently supports System 1 retrieval well (BM25 + NLI + vector
similarity). It cannot answer queries that require:
- Step ordering ("what comes after X?")
- Constraint satisfaction ("what if prerequisite Y is unavailable?")
- Prerequisite chains ("what else depends on Z?")

These require the logic/procedural layer that NS-Mem adds via DAG-based symbolic queries.

## Proposed Change

Add a **hybrid retrieval mode** to `agentic_kg_memory` that routes queries through
both neural and symbolic paths. The query classifier lives in `cognitive-taxonomy`
(skill reference), but the routing logic and symbolic execution layer live here.

### New Components

#### 1. Query Classifier

Classify each incoming query into one of four types:

| Type | Signal | Example |
|---|---|---|
| factual | "what", "who", "when", "where" | "What did the user say about X?" |
| constraint | "can I", "if", "given", "allowed" | "Can I proceed if Y is broken?" |
| procedural | "how", "steps", "procedure" | "How do I deploy this?" |
| open-ended | "what should", "recommend" | "What should I do?" |

**Implementation:** lightweight LLM call or regex-based heuristic classifier.
Store classification rules in the skill metadata so they can be tuned per domain.

#### 2. Symbolic Query Engine

For constraint and procedural queries, execute deterministic operations over
procedural DAGs stored in the logic layer:

```python
class SymbolicQueryResult(BaseModel):
    answer: str                           # human-readable result
    steps: list[str]                     # ordered step sequence (procedural)
    prerequisites: list[str]             # dependencies for a given step
    alternatives: list[list[str]]        # valid alternative paths
    violated_constraints: list[str]      # which constraints failed
    confidence: float                    # 1.0 for exact, <1.0 for partial matches
```

**Query operations:**
- `get_prerequisites(step)` — BFS/DFS backward from step to START
- `get_next_steps(step)` — forward edges from step
- `find_alternative_paths(start, end)` — find all paths via DAG traverse
- `check_constraints(step, attributes)` — validate attribute requirements
- `get_transition_probabilities(step)` — probabilistic step ordering

#### 3. Logic Layer Integration

The logic layer (Procedural DAGs + dual-index vectors) is the storage backend
for symbolic queries. It is populated by `procedural-memory` skill, and `agentic_kg_memory`
queries it during hybrid retrieval.

**Storage:** SQLite table `procedural_dags` (or reuse existing wiki_pages if DAGs are stored as JSON).
Each row contains: logic_node_id, serialized DAG (JSON), goal_index, step_index.

#### 4. Retrieval Merge Strategy

When a query is routed through both paths (open-ended or multi-layer), merge results:

```
HybridResult = {
    neural_hits: TopK(similarity_retrieval(query)),    # System 1
    symbolic_hits: DAG_query_results(query),           # System 2
    merged: RRF_fusion(neural_hits, symbolic_hits),    # Reciprocal Rank Fusion
}
```

**RRF weight:** default `k = 60`, neural_weight = 0.6, symbolic_weight = 0.4.
Adjust based on query type: factual -> higher neural weight, constraint -> higher symbolic.

### Updated Memory Page Schema

Existing `wiki_pages` table gains an optional `page_type` field:

```sql
ALTER TABLE wiki_pages ADD COLUMN page_type TEXT DEFAULT 'semantic';
```

Values: `'semantic'`, `'episodic'`, `'procedural'`, `'throughline'`.

Procedural pages store the DAG as JSON:

```sql
ALTER TABLE wiki_pages ADD COLUMN procedure_dag TEXT;
```

JSON format: `{"nodes": [...], "edges": [...], "transitions": {...}, "goal": "..."}`

### Updated BM25+NLI Pipeline

The existing pipeline remains unchanged for System 1 queries. For hybrid queries:

```
1. Query arrives
2. Classify query type -> factual / constraint / procedural / open-ended
3. If factual -> existing BM25 -> NLI pipeline (unchanged)
4. If constraint/procedural -> BM25 -> NLI + symbolic DAG query -> merge
5. If open-ended -> BM25 -> NLI + symbolic -> RRF fusion -> return
```

### Updated Evidence for SKILL.md

Add to the "Failure Modes" section:

```markdown
## Failure Modes (Hybrid Retrieval)

| Symptom | Root cause | Fix |
|---|---|---|
| Procedural queries return vague answers | No logic layer data | Enable `procedural-memory` distillation on experience traces |
| Constraint queries timeout | DAG too deep/complex | Add max_depth limit to symbolic traversal; log depth |
| RRF fusion gives poor merge | Weights misaligned | Tune neural_weight/symbolic_weight per domain |
| Symbolic queries crash on malformed DAGs | Invalid procedure DAG | Validate DAG structure on SK-Gen output; reject on insert |
```

Add to the "Evidence" section:

```markdown
- NS-Mem (2603.15280) — hybrid retrieval architecture, query classification, symbolic DAG queries
- RRF fusion — multi-vector retrieval merging
```

## Implementation Order

1. Add `page_type` and `procedure_dag` columns to SQLite schema
2. Implement query classifier (regex + LLM fallback)
3. Implement symbolic query engine (DAG traversal primitives)
4. Implement RRF merge strategy
5. Wire into existing retrieval pipeline
6. Update SKILL.md failure modes and evidence
7. Test with constraint-aware and procedural queries

## Evidence

- NS-Mem (2603.15280) — hybrid retrieval architecture, query classification, +4.35% accuracy gain
