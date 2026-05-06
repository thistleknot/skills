---
name: procedural-memory
description: >
  SK-Gen pipeline for automatic procedure extraction from episodic experience traces.
  Extracts recurring action patterns, verifies them with an LLM, constructs procedural
  DAGs with dual-index vectors, and supports incremental EMA-based updates.
  Based on NS-Mem (2603.15280). Use when an agent needs to learn reusable procedures
  from raw experience without manual curation.
status: staged
tier: L1
last_validated: 2026-05-02
supersedes: []
validation_method: session
---

# Procedural Memory — SK-Gen Pipeline

## Core Thesis

Skills that require manual curation don't compound. Procedures that emerge from
recurring episodic patterns do.

This skill implements the **SK-Gen** pipeline from NS-Mem (2603.15280), which
automatically extracts reusable procedures from raw experience traces through
five steps: action sequence extraction, sequential pattern mining, knowledge
verification, DAG construction, and index generation.

**Result:** +4.35% reasoning accuracy over pure neural memory, up to +12.5%
on constrained reasoning queries.

## When to Use

- An agent needs to learn procedures from raw experience or trace data
- A continuity-log or episodic memory store contains recurring action patterns
- You want to automatically discover reusable workflows without manual skill authoring
- Procedural memory is needed to answer "what steps does procedure X require?"
  or "what comes after step Y?"

## When NOT to Use

- You already have a curated, stable procedure (use `skill-wiki` instead)
- You only need factual recall, not procedural reasoning (use `agentic_kg_memory`)
- The experience traces are too sparse to find recurring patterns (< 5 occurrences)

---

## Architecture Overview

```
Episodic Experiences (raw action traces)
        |
        v
 +-----------------+
 |  Phase 1:      |
 |  Observation   |
 |  Processing    |
 +--------+-------+
          | structured episodic records
          v
 +--------+-------+     +-----------------+
 |  Phase 2:      |     |  Phase 3:      |
 |  Logic Distill |     |  Incremental   |
 |  (batch)       |     |  Maintenance   |
 +--------+-------+     +--------+-------+
          |                      |
          v                      v
 +--------+-------+     +--------+-------+
 | Logic Nodes    |     | Update EMA    |
 | + Procedural   |     | + Update DAG  |
 | DAGs           |     | transitions   |
 +----------------+     +----------------+
```

Each **Logic Node** = (id, goal, {index_vectors}, procedural_DAG, query_functions)
- **Goal-level index** — embeds the procedure's goal description
- **Step-level index** — average of all step embeddings
- **Procedural DAG** — START to steps to GOAL with edge transition statistics

---

## Phase 1: Observation Processing

Convert raw episodic experience traces into structured action sequences.

Each episodic record `e = (t, description, embedding)` contains:
- `t` timestamp in the observation stream
- `description` atomic event narrative (action + entities involved)
- `embedding` vector representation of the description

**Input format:** continuity log entries, episode transcripts, or task execution traces
with timestamped action descriptions and entity references.

**Output:** per-session action sequences `S_v = [a1, a2, ..., aL]` ordered lists
of actions extracted from episodic records belonging to session v.

**Extraction patterns:**
1. Rule-based: parse structured log formats (JSON, CSV) for action fields
2. LLM-based: "Extract temporally-ordered action sequences from these event descriptions"

## Phase 2: Logic Distillation (Batch Pipeline)

Extract procedures from aggregated experience traces. Five sub-steps:

### Step 1: Sequential Pattern Mining

Apply **PrefixSpan** to discover recurring action patterns with temporal ordering.

```
Input:  S_seq = {S1, S2, ..., SV}  (session action sequences)
Output: P_cand = {p : support(p) >= sigma}

support(p) = |{S in S_seq : p subset of S}| / |S_seq|
```

**Threshold:** `sigma = 0.3` — minimum support (pattern appears in 30%+ of sessions).
Lower for rare but important procedures (down to 0.15).

**Key guarantee:** PrefixSpan preserves ordering. `[cut, blanch]` is distinct
from `[blanch, cut]`. This is critical for procedural correctness.

### Step 2: Knowledge Verification

Not every frequent pattern is a useful procedure. Filter candidates:

```
score_p = LLMVerify(p, M_rel)
```

Where `M_rel` is memory retrieved using p as a query. The LLM evaluates:
- Is the pattern a complete, reusable procedure?
- Does it have a clear goal and meaningful steps?
- Are the step dependencies coherent?

**Scoring rubric:**
- 0.0-0.3: Noise (e.g., `[pick_up, put_down]`) — discard
- 0.3-0.6: Partial (e.g., `[open_file, write_code]`) — keep with low priority
- 0.6-0.8: Valid procedure (e.g., `[read_spec, write_test, implement_func]`) — promote
- 0.8-1.0: High-quality procedure — promote with bonus

**Threshold:** `tau = 0.6` for auto-promotion, 0.4 for review queue.

### Step 3: DAG Construction

For verified patterns, construct the Procedural DAG:

```
Nodes: V = {START} union {v_a : a in p} union {GOAL}
Edges: E = {(v_i, v_i+1) : consecutive actions in p}
Attributes: A(v) extracted from associated episodic memories
```

**Properties:**
- START and GOAL are distinguished absorbing nodes
- Each intermediate node maps to an action step with attributes (constraints,
  prerequisites, available alternatives)
- episodic_links point to supporting observations for traceability

### Step 4: Index Generation

Compute dual-level Embedding Index Vectors:

```
i_goal = phi(p.goal)                    # goal-level matching
i_step = (1/|p.steps|) * sum phi(s)     # step-level matching (average)
```

**Analogy:** goal index = document title, step index = document body.
Both enable discovery: users may query by high-level goal ("how to debug")
or by specific step ("what comes after reproducing the issue").

### Step 5: Logic Node Assembly

```
LogicNode = (id, goal, {i_goal, i_step}, DAG, query_functions)
```

Add to the logic layer database.

## Phase 3: Incremental Maintenance

After new episodic experiences arrive, update existing Logic Nodes without
full reconstruction.

### Matching and Gating

```
N* = argmax_{N in logic_layer} sim(phi(o_new), I_N)
```

Only proceed if `sim > delta` (gating threshold, default **0.7**). Prevents noise
from corrupting established procedures. Observations below delta accumulate in a
candidate pool — when sufficient evidence builds, trigger a new distillation cycle.

### Neural Refinement via EMA

Update index vectors using Exponential Moving Average:

```
i_{t+1} = beta * i_t + (1 - beta) * phi(o_new)
```

Where `beta = 0.9` (default). High beta preserves historical semantics; low beta
adapts to distributional drift. Unlike direct replacement, EMA prevents catastrophic
forgetting of historical procedures.

### Symbolic Refinement via Transition Counts

Maintain edge transition counts in each DAG:

```
N_ij <- N_ij + 1  when observation vi -> vj is seen
P(vj|vi) = N_ij / sum_k N_ik
```

This yields probabilistic step ordering. Frequently-taken alternative paths
become visible in the DAG structure without fragmenting the procedure.

**Theoretical guarantee:** transition counts converge almost surely to true
probabilities as observations approach infinity (Theorem 2, NS-Mem paper).

## Knowledge Fusion

When the same procedure is observed across multiple independent sessions,
merge single-path DAGs into a unified multi-path DAG:

1. **Node alignment** — bipartite matching via embedding similarity
2. **Edge union** — preserve all observed transitions (branching points)
3. **Statistic pooling** — Bayesian conjugate update of transition counts

This captures procedural diversity: different users may follow different valid
paths through the same procedure.

## Hybrid Retrieval

Two modes for accessing memory:

### Neural Discovery (System 1)
```
Similar queries -> vector similarity over {i_goal, i_step}
```
Fuzzy matching, semantic retrieval, "tell me about debugging procedures."

### Symbolic Query (System 2)
```
Structured queries -> deterministic DAG operations
```
Exact answers: "What is the minimum set of prerequisites for step X?"
"Show all valid execution paths that include both Y and Z?"
"What alternatives exist when step X fails?"

**Query types mapped to retrieval:**
| Type | Method | Example |
|---|---|---|
| Factual | Neural discovery | "What steps does procedure X have?" |
| Constraint | Symbolic DAG query | "What if prerequisite Y is unavailable?" |
| Sequential | Symbolic DAG query | "What comes after step Z?" |
| Alternative | Symbolic DAG exploration | "Show all valid paths to goal G" |

## Configuration

| Parameter | Default | Description |
|---|---|---|
| sigma (support threshold) | 0.3 | Min pattern frequency for mining |
| tau (verification threshold) | 0.6 | Min LLM score for auto-promotion |
| delta (gating threshold) | 0.7 | Min similarity for incremental update |
| beta (EMA coefficient) | 0.9 | Decay rate for index vector updates |
| tau_pos (semantic reinforce) | 0.8 | Similarity threshold for reinforcing existing nodes |
| tau_neg (semantic weaken) | 0.3 | Similarity threshold for weakening/discarding nodes |

## Data Model

```python
class EpisodicRecord(BaseModel):
    id: str
    timestamp: datetime
    description: str
    embedding: list[float]
    entity_anchors: list[str]
    session_id: str

class LogicNode(BaseModel):
    id: str
    goal: str
    goal_index: list[float]
    step_index: list[float]
    dag_nodes: list[DAGNode]
    dag_edges: list[DAGEdge]
    transition_counts: dict[tuple[str,str], int]
    episodic_links: list[str]  # IDs of supporting episodic records
    created_at: datetime
    updated_at: datetime

class DAGNode(BaseModel):
    id: str
    action: str
    attributes: dict[str, Any]
    is_start: bool = False
    is_goal: bool = False

class DAGEdge(BaseModel):
    source: str
    target: str
    weight: float  # transition count
```

## Evidence

- NS-Mem (2603.15280), Jiang et al., UNSW — full pipeline, experiments, proofs
- PrefixSpan (Pei et al., 2001) sequential pattern mining algorithm
- Ebbinghaus forgetting curve — biological foundation for EMA-style decay
- CoALA taxonomy — procedural memory as a cognitive architecture primitive
<!-- consolidation:see-also:start -->
## See Also
[[memory-architecture]]  [[cognitive-taxonomy]]  [[agentic_kg_memory]]  [[skill-wiki]]  [[agentic-harness]]
<!-- consolidation:see-also:end -->
