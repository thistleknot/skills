---
name: customer-intent-resolution
description: >
  Build an end-to-end customer case intent resolution pipeline. Use this skill
  whenever the task involves: mapping customer support queries to prior resolved
  cases, extracting intent/objective/solution structure from case history,
  building a Louvain cluster index over a resolution corpus, implementing
  nearest-centroid routing for intent-to-objective mapping, entity schema
  projection for slot elicitation, or evaluating retrieval quality with
  LLM-as-judge. Trigger on any mention of customer cases, intent classification,
  case routing, support ticket similarity, resolution matching, or retrieval eval.
---

# Customer Intent Resolution Pipeline

## Architecture Overview

```
OFFLINE — discover the space
  prior resolved cases
      ? LLM extract {intent_verb, objective_text, resolution_text, entity_schema}
      ? embed (objective_text + resolution_text)
      ? build kNN graph (cosine sim + entity schema overlap as edge weights)
      ? Louvain community detection ? emergent objective clusters
      ? per cluster: centroid vector + dominant entity signature
      ? store: resolved_cases (pgvector) + cluster_index (SQLite)

ONLINE — route into it
  new intake message
      ? extract {intent_verb, object_domain}      ? sparse, best-effort
      ? embed sparse representation
      ? nearest centroid(s) in cluster index
      ? retrieve top-k cases within cluster by cosine sim
      ? entity signature of cluster ? missing slots to collect

EVAL — continuous
  synthetic eval set
      ? routing pipeline
      ? LLM-as-judge (complete / partial / irrelevant)
      ? fitness scalar: context_recall, MRR@3, judge_score, context_precision
```

**Core principle:** the resolution corpus defines its own topology. Do not
fabricate a bridge from intake to resolution space — discover the structure
from the data, then route into it with whatever signal the intake provides.

The chain is: **intent ? objective cluster ? entity signature**.
Each hop is grounded in real data geometry, not generated assumptions.

---

## Stack

| Concern | Tool |
|---|---|
| Storage | PostgreSQL + pgvector (cases + embeddings) |
| Cluster index | SQLite (cluster metadata + centroid vectors) |
| Graph + clustering | NetworkX + python-louvain (or igraph + leidenalg) |
| Embeddings | sentence-transformers (GIST or similar) |
| LLM extraction + judge | Ollama (qwen3.5:9b+) via OpenAI-compatible endpoint |
| API layer | FastAPI |
| UI | Streamlit |
| Schema validation | Pydantic |
| Checkpointing | SQLite |
| Eval optimization | Optuna TPE |

**Note on Louvain vs Leiden:** prefer Leiden (`leidenalg` package) over Louvain.
Leiden guarantees well-connected communities; Louvain can produce internally
disconnected clusters when bridge nodes are reassigned. Same interface, stricter
guarantees.

**LLM endpoint:** `http://localhost:11434/v1` (Ollama) or `http://localhost:8080/v1`.

---

## Decomposition

Solve in this order. Do not proceed until current stage passes its validation gate.

```
1. schema_design          no deps
2. extraction_offline     depends on 1
3. embedding_index        depends on 2
4. cluster_index          depends on 3
5. retrieval              depends on 3, 4
6. eval_pipeline          depends on 3, 4, 5
7. fastapi_service        depends on 5
8. streamlit_ui           depends on 7
```

---

## Stage 1 — Schema Design

```python
from pydantic import BaseModel
from typing import Optional

class CaseEntitySchema(BaseModel):
    """
    Normalized entity slots extracted from resolution text.
    Populated from the resolution side, never the intake side.
    Extend with domain-specific fields before running Stage 2.
    """
    account_id: Optional[str] = None
    product_type: Optional[str] = None
    issue_category: Optional[str] = None
    action_required: Optional[str] = None
    resolution_type: Optional[str] = None

class ResolvedCase(BaseModel):
    """
    Require: case_id unique, resolution_text non-empty
    Guarantee: entity_schema populated from resolution_text, not intake_text
    """
    case_id: str
    intake_text: str
    objective_text: str
    resolution_text: str
    entity_schema: CaseEntitySchema
    cluster_id: Optional[int] = None
    objective_embedding: Optional[list[float]] = None

class ClusterRecord(BaseModel):
    """
    Require: centroid_vector length matches embedding dim
    Guarantee: entity_signature contains only fields with >= min_support across members
    """
    cluster_id: int
    centroid_vector: list[float]
    entity_signature: dict        # dominant non-null slots across member cases
    member_case_ids: list[str]
    size: int

class IntakeQuery(BaseModel):
    """
    Require: message non-empty
    Guarantee: routing proceeds even if extraction yields nothing — falls back
               to full corpus nearest-centroid search
    """
    message: str
    intent_verb: Optional[str] = None
    object_domain: Optional[str] = None
```

**Postgres DDL:**
```sql
CREATE EXTENSION IF NOT EXISTS vector;

CREATE TABLE resolved_cases (
    case_id         TEXT PRIMARY KEY,
    intake_text     TEXT NOT NULL,
    objective_text  TEXT NOT NULL,
    resolution_text TEXT NOT NULL,
    entity_schema   JSONB NOT NULL DEFAULT '{}',
    cluster_id      INTEGER,
    obj_embedding   vector(768),
    indexed_at      TIMESTAMPTZ DEFAULT now()
);

CREATE INDEX ON resolved_cases USING ivfflat (obj_embedding vector_cosine_ops)
    WITH (lists = 100);
CREATE INDEX ON resolved_cases USING gin (entity_schema);
CREATE INDEX ON resolved_cases (cluster_id);
```

**SQLite cluster index DDL:**
```sql
CREATE TABLE clusters (
    cluster_id       INTEGER PRIMARY KEY,
    centroid_vector  BLOB NOT NULL,   -- np.ndarray serialized via pickle
    entity_signature TEXT NOT NULL,   -- JSON
    member_case_ids  TEXT NOT NULL,   -- JSON array
    size             INTEGER NOT NULL
);
```

**Validation gate:** postgres \d shows vector column + all three indexes.
SQLite clusters table exists.

---

## Stage 2 — Offline Extraction

Extract structured fields from prior resolved cases. Checkpoint to SQLite.

**Extraction prompt (system):**
```
You extract structured information from resolved customer support cases.
Return only valid JSON. No preamble, no markdown fences.

Schema:
{
  "intent_verb": "string — action the customer wanted (cancel, repair, refund, upgrade...)",
  "objective_text": "string — one sentence: what the customer needed to achieve",
  "entity_schema": {
    "account_id": "string or null",
    "product_type": "string or null",
    "issue_category": "string or null",
    "action_required": "string or null",
    "resolution_type": "string or null"
  }
}

Extract from the RESOLUTION side only. Not from intake.
If a field cannot be determined, use null.
```

**Extraction prompt (user):**
```
Case intake: {intake_text}
Resolution: {resolution_text}
```

**Contracts:**
- Require: `resolution_text` non-empty
- Guarantee: all null fields explicit, no missing keys
- Maintain: SQLite checkpoint `(case_id, status, extracted_at)`
- Assert: `json.loads(response)` succeeds; on failure log + skip, do not crash

**Validation gate:** spot-check 10 random extractions — schema fields should
reflect resolution content, not intake content.

---

## Stage 3 — Embedding Index

```python
"""
Workflow:
  Load cases where obj_embedding IS NULL
  Batch-embed objective_text
  Write vectors to pgvector

Preconditions: Stage 2 complete
Failure modes: OOM (batch_size=32), dim mismatch (assert before write)
"""
from sentence_transformers import SentenceTransformer
import numpy as np

EMBED_MODEL = "avsolatorio/GIST-Embedding-v0"
BATCH_SIZE = 32

def index_cases(conn, model: SentenceTransformer):
    cur = conn.cursor()
    cur.execute(
        "SELECT case_id, objective_text FROM resolved_cases WHERE obj_embedding IS NULL"
    )
    rows = cur.fetchall()

    for i in range(0, len(rows), BATCH_SIZE):
        batch = rows[i:i + BATCH_SIZE]
        ids = [r[0] for r in batch]
        texts = [r[1] for r in batch]
        embeddings = model.encode(texts, normalize_embeddings=True)
        assert embeddings.shape[1] == 768, f"Dim mismatch: {embeddings.shape[1]}"
        for case_id, vec in zip(ids, embeddings):
            cur.execute(
                "UPDATE resolved_cases SET obj_embedding = %s WHERE case_id = %s",
                (vec.tolist(), case_id)
            )
        conn.commit()
```

**Validation gate:** `SELECT count(*) FROM resolved_cases WHERE obj_embedding IS NULL` = 0.

---

## Stage 4 — Cluster Index (Louvain/Leiden)

This stage defines the objective space topology. All online routing depends on it.

```python
"""
Workflow:
  Load all embeddings + entity_schemas from postgres
  Build kNN graph: nodes = cases, edges = top-k neighbors weighted by combined sim
  Run Leiden community detection ? clusters
  Per cluster: compute centroid, derive entity signature (dominant non-null slots)
  Write cluster assignments back to resolved_cases.cluster_id
  Write cluster records to SQLite cluster index

Preconditions: all obj_embeddings populated
Failure modes: disconnected graph (lower kNN k), too many tiny clusters
               (increase resolution parameter), too few large clusters
               (decrease resolution parameter)

Tunable parameters:
  KNN_K         = 15      neighbors per node in graph construction
  EDGE_W_COSINE = 0.7     weight of cosine sim in edge weight
  EDGE_W_SCHEMA = 0.3     weight of entity schema overlap in edge weight
  LEIDEN_RES    = 1.0     resolution parameter — higher = more/smaller clusters
  MIN_CLUSTER   = 5       discard clusters smaller than this
"""
import networkx as nx
import numpy as np
import leidenalg
import igraph as ig
import sqlite3, json, pickle
from sklearn.metrics.pairwise import cosine_similarity

KNN_K = 15
EDGE_W_COSINE = 0.7
EDGE_W_SCHEMA = 0.3
LEIDEN_RES = 1.0
MIN_CLUSTER = 5

def build_graph(embeddings: np.ndarray, schemas: list[dict]) -> nx.Graph:
    """
    Require: embeddings shape (N, D), schemas len N
    Guarantee: connected graph with weighted edges
    """
    N = len(embeddings)
    sim_matrix = cosine_similarity(embeddings)
    G = nx.Graph()
    G.add_nodes_from(range(N))

    for i in range(N):
        top_k = np.argsort(sim_matrix[i])[::-1][1:KNN_K + 1]
        for j in top_k:
            cosine_w = float(sim_matrix[i][j])
            schema_w = schema_overlap(schemas[i], schemas[j])
            weight = EDGE_W_COSINE * cosine_w + EDGE_W_SCHEMA * schema_w
            if G.has_edge(i, j):
                G[i][j]['weight'] = max(G[i][j]['weight'], weight)
            else:
                G.add_edge(i, j, weight=weight)
    return G


def run_leiden(G: nx.Graph) -> list[int]:
    """Convert networkx graph to igraph, run Leiden, return partition list."""
    ig_graph = ig.Graph.from_networkx(G)
    weights = [G[u][v]['weight'] for u, v in G.edges()]
    ig_graph.es['weight'] = weights
    partition = leidenalg.find_partition(
        ig_graph,
        leidenalg.RBConfigurationVertexPartition,
        resolution_parameter=LEIDEN_RES,
        weights='weight'
    )
    labels = [0] * G.number_of_nodes()
    for cluster_id, members in enumerate(partition):
        for node in members:
            labels[node] = cluster_id
    return labels


def derive_entity_signature(schemas: list[dict], min_support: float = 0.6) -> dict:
    """
    Fields present and non-null in >= min_support fraction of cluster members.
    These are the slots this objective class reliably requires.
    """
    if not schemas:
        return {}
    counts = {}
    for schema in schemas:
        for k, v in schema.items():
            if v is not None:
                counts[k] = counts.get(k, 0) + 1
    threshold = len(schemas) * min_support
    return {k: True for k, v in counts.items() if v >= threshold}


def build_cluster_index(conn, sqlite_conn, embeddings: np.ndarray,
                        case_ids: list[str], schemas: list[dict]):
    G = build_graph(embeddings, schemas)
    labels = run_leiden(G)

    clusters = {}
    for idx, cluster_id in enumerate(labels):
        clusters.setdefault(cluster_id, []).append(idx)

    cur = conn.cursor()
    sqlite_cur = sqlite_conn.cursor()

    for cluster_id, member_indices in clusters.items():
        if len(member_indices) < MIN_CLUSTER:
            continue

        member_vecs = embeddings[member_indices]
        centroid = member_vecs.mean(axis=0)
        centroid /= np.linalg.norm(centroid)

        member_schemas = [schemas[i] for i in member_indices]
        entity_sig = derive_entity_signature(member_schemas)

        member_ids = [case_ids[i] for i in member_indices]

        # write cluster assignments back to postgres
        for case_id in member_ids:
            cur.execute(
                "UPDATE resolved_cases SET cluster_id = %s WHERE case_id = %s",
                (cluster_id, case_id)
            )

        # write cluster record to SQLite
        sqlite_cur.execute("""
            INSERT OR REPLACE INTO clusters
                (cluster_id, centroid_vector, entity_signature, member_case_ids, size)
            VALUES (?, ?, ?, ?, ?)
        """, (
            cluster_id,
            pickle.dumps(centroid),
            json.dumps(entity_sig),
            json.dumps(member_ids),
            len(member_ids)
        ))

    conn.commit()
    sqlite_conn.commit()
```

**Validation gate:**
- `SELECT count(distinct cluster_id) FROM resolved_cases WHERE cluster_id IS NOT NULL` > 3
- Spot-check 3 clusters: member cases should share a recognizable objective type
- `entity_signature` for each cluster should have >= 1 dominant field

---

## Stage 5 — Retrieval

Two hops: nearest-centroid cluster routing, then within-cluster case retrieval.

```python
"""
Workflow:
  1. Embed sparse intake representation (intent_verb + object_domain, or raw message)
  2. Nearest centroid(s) in SQLite cluster index
  3. Within matched cluster(s), retrieve top-k cases by cosine sim from pgvector
  4. Return matches + entity signature diff (missing slots)

Preconditions: cluster index built, all obj_embeddings populated
Failure modes: intake too sparse to route (fall back to global nearest-centroid),
               cluster too small (expand to top-2 clusters)
"""

CLUSTER_TOP_N = 2     # consider top-N nearest clusters
WITHIN_CLUSTER_K = 5  # cases to return per cluster

def load_cluster_index(sqlite_conn) -> list[dict]:
    cur = sqlite_conn.cursor()
    cur.execute("SELECT cluster_id, centroid_vector, entity_signature, size FROM clusters")
    clusters = []
    for row in cur.fetchall():
        clusters.append({
            "cluster_id": row[0],
            "centroid": pickle.loads(row[1]),
            "entity_signature": json.loads(row[2]),
            "size": row[3]
        })
    return clusters


def nearest_clusters(query_vec: np.ndarray, clusters: list[dict], top_n: int) -> list[dict]:
    """Cosine similarity between query and all cluster centroids."""
    scored = []
    for c in clusters:
        sim = float(np.dot(query_vec, c["centroid"]))
        scored.append({**c, "centroid_sim": sim})
    return sorted(scored, key=lambda x: x["centroid_sim"], reverse=True)[:top_n]


def retrieve_within_cluster(conn, cluster_id: int,
                             query_vec: np.ndarray, k: int) -> list[dict]:
    cur = conn.cursor()
    cur.execute("""
        SELECT case_id, objective_text, resolution_text, entity_schema,
               1 - (obj_embedding <=> %s::vector) AS cosine_sim
        FROM resolved_cases
        WHERE cluster_id = %s
        ORDER BY cosine_sim DESC
        LIMIT %s
    """, (query_vec.tolist(), cluster_id, k))
    return [
        {
            "case_id": r[0],
            "objective_text": r[1],
            "resolution_text": r[2],
            "entity_schema": r[3],
            "cosine_sim": r[4]
        }
        for r in cur.fetchall()
    ]


def elicit_slots(entity_signature: dict, known: dict) -> list[str]:
    """
    Fields the cluster expects (entity_signature keys) that are absent in known.
    These are the questions to ask the customer next turn.
    """
    return [k for k in entity_signature if not known.get(k)]


def resolve(message: str, known_entities: dict,
            conn, sqlite_conn, model) -> list[dict]:
    # embed whatever the intake gives us — sparse is fine
    query_vec = model.encode([message], normalize_embeddings=True)[0]

    clusters = load_cluster_index(sqlite_conn)
    top_clusters = nearest_clusters(query_vec, clusters, CLUSTER_TOP_N)

    results = []
    for cluster in top_clusters:
        cases = retrieve_within_cluster(conn, cluster["cluster_id"], query_vec, WITHIN_CLUSTER_K)
        missing = elicit_slots(cluster["entity_signature"], known_entities)
        for case in cases:
            results.append({
                **case,
                "cluster_id": cluster["cluster_id"],
                "centroid_sim": cluster["centroid_sim"],
                "missing_slots": missing
            })

    return sorted(results, key=lambda x: x["cosine_sim"], reverse=True)
```

**Validation gate:** retrieve on 5 known cases using only their intent verb.
Correct cluster should appear in top-2 for at least 4/5.

---

## Stage 6 — Eval Pipeline

### Ground Truth Construction

**Tier 1 — Self-retrieval (free)**
Hold out 10% of cases. Route each by its own intake text. Assert correct
cluster appears in top-N and correct case in top-k within cluster.

**Tier 2 — Synthetic queries (primary eval set)**
Generate sparse intake messages from resolutions — these simulate real intake
signal without entities.

```
System:
Given a resolved customer support case, generate {N} distinct customer
intake messages that this resolution would answer. Messages should be
sparse — terse, vague, intent-present but entity-absent. No account numbers,
no product names. Just the action and rough domain.
Output only a JSON array of strings.

User:
Resolution: {resolution_text}
```

Store as `(synthetic_query, correct_case_id, correct_cluster_id)` in SQLite.
Target: 3 synthetic queries per case minimum.

**Tier 3 — Human-labeled pairs**
Final validation only.

---

### LLM-as-Judge

```
System:
You evaluate whether a retrieved customer support resolution would solve
a new customer query. Score using exactly these three classes.

complete (1.0)  — resolution addresses the query's core issue; agent could
                  use it directly with minor slot substitution
partial (0.5)   — related but missing key steps, or similar but not identical
irrelevant (0.0)— does not apply; using it would mislead the agent

Return JSON only: {"score": float, "class": string, "reason": string}
One sentence reason. No preamble.

Anchor examples:
Query: "I was charged twice this month"
Resolution: "Duplicate charge identified; second charge reversed and confirmation
             sent to billing email on file."
Output: {"score": 1.0, "class": "complete", "reason": "Directly addresses
         duplicate billing with the exact corrective action."}

Query: "My internet keeps dropping every evening"
Resolution: "Router firmware updated remotely; connection stabilized."
Output: {"score": 0.5, "class": "partial", "reason": "Router fix is plausible
         but does not confirm evening-specific congestion was diagnosed."}

User:
New customer query: {message}
Retrieved resolution: {resolution_text}
```

Run each judgment 3 times, take majority. Flag 3-way disagreements for manual review.

---

### Metrics

```python
def fitness_score(
    context_recall: float,     # correct case in top-k at all
    mean_judge_score: float,   # judge score on top-1 result
    mrr_at_3: float,           # reciprocal rank of first complete hit
    context_precision: float   # fraction of top-k scoring complete or partial
) -> float:
    """
    context_recall weighted highest — a miss at retrieval is unrecoverable.
    """
    return (
        0.4 * context_recall +
        0.3 * mean_judge_score +
        0.2 * mrr_at_3 +
        0.1 * context_precision
    )
```

**Targets before shipping:**

| Metric | Target |
|---|---|
| context_recall@10 | > 0.80 |
| mean_judge_score | > 0.65 |
| MRR@3 | > 0.60 |
| fitness_score | > 0.70 |

---

### Optuna Integration

Tune graph construction and routing parameters against fitness scalar.

```python
import optuna

def optuna_objective(trial):
    params = {
        "knn_k": trial.suggest_int("knn_k", 5, 30),
        "edge_w_cosine": trial.suggest_float("edge_w_cosine", 0.5, 0.9),
        "leiden_res": trial.suggest_float("leiden_res", 0.5, 2.0),
        "cluster_top_n": trial.suggest_int("cluster_top_n", 1, 4),
        "within_cluster_k": trial.suggest_int("within_cluster_k", 3, 10),
    }
    results = run_eval_sample(**params)
    return fitness_score(**results)

study = optuna.create_study(direction="maximize")
study.optimize(optuna_objective, n_trials=50)
```

**Dev discipline:** 10% sample, < 5 min wall time. Parallelize judge calls.
Full-corpus eval before deploy only.

---

## Stage 7 — FastAPI Service

```python
from fastapi import FastAPI
from pydantic import BaseModel

app = FastAPI()

class QueryRequest(BaseModel):
    message: str
    known_entities: dict = {}

class MatchResult(BaseModel):
    case_id: str
    cluster_id: int
    objective_text: str
    resolution_text: str
    cosine_sim: float
    missing_slots: list[str]

@app.post("/resolve", response_model=list[MatchResult])
async def resolve_endpoint(req: QueryRequest):
    results = resolve(req.message, req.known_entities, conn, sqlite_conn, model)
    return [MatchResult(**r) for r in results]
```

**Validation gate:** `curl -X POST localhost:8000/resolve -d '{"message": "billing issue"}'`
returns results with `cluster_id` and `missing_slots` populated.

---

## Stage 8 — Streamlit UI

```python
import streamlit as st
import requests

st.title("Case Intent Resolver")
message = st.text_area("Customer message")

if st.button("Resolve") and message:
    resp = requests.post("http://localhost:8000/resolve", json={"message": message})
    for r in resp.json():
        with st.expander(f"Cluster {r['cluster_id']} — {r['case_id']} (sim {r['cosine_sim']:.2f})"):
            st.write("**Objective:**", r["objective_text"])
            st.write("**Resolution:**", r["resolution_text"])
            if r["missing_slots"]:
                st.warning("Still needed: " + ", ".join(r["missing_slots"]))
```

---

## Validation Progression

```
unit:       1 case through full pipeline — cluster assigned, retrieval returns match
small:      10 cases, correct cluster in top-2 for >= 8/10
medium:     10% sample, fitness_score > 0.70, wall time < 5 min
production: full corpus, p95 latency < 500ms on /resolve
```

---

## Known Failure Modes

| Failure | Signal | Fix |
|---|---|---|
| Too many tiny clusters | many clusters < MIN_CLUSTER | Lower LEIDEN_RES |
| Too few large clusters | 1-2 clusters absorb everything | Raise LEIDEN_RES |
| Entity signature empty | all fields below min_support threshold | Lower min_support to 0.4 |
| Intake too sparse to route | centroid_sim < 0.4 on all clusters | Fall back to global top-k over full corpus |
| Judge score inflation | all results >= 0.5 | Add adversarial irrelevant pairs to anchor examples |
| Eval too slow | > 5 min on 10% sample | Parallelize judge calls; reduce JUDGE_RUNS to 1 |

---

## Files to Produce

```
customer_intent_resolution/
+-- schema.py           # Pydantic models + Postgres DDL + SQLite DDL
+-- extract_offline.py  # Stage 2: LLM extraction + SQLite checkpoint
+-- index_embeddings.py # Stage 3: batch embed + pgvector write
+-- cluster_index.py    # Stage 4: graph construction + Leiden + cluster index
+-- retrieval.py        # Stage 5: nearest-centroid routing + within-cluster retrieval
+-- eval_pipeline.py    # Stage 6: ground truth gen, judge, metrics, Optuna
+-- api.py              # Stage 7: FastAPI service
+-- ui.py               # Stage 8: Streamlit UI
+-- config.py           # DB conn, model names, thresholds, tunable parameters
```

Implement in topological order. Each file complete and standalone.
Validation gate before advancing. 10% sample during development — never
wait for a full-corpus run during iteration.