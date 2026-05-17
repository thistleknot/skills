---
name: request-intent-resolution
description: >
  Build an end-to-end request intent resolution pipeline. Use this skill
  whenever the task involves: mapping support requests to prior resolved
  threads, extracting intent/objective/solution structure from thread history,
  building a Louvain cluster index over a resolution corpus, implementing
  nearest-centroid routing for intent-to-objective mapping, entity schema
  projection for slot elicitation, or evaluating retrieval quality with
  LLM-as-judge. Trigger on any mention of request threads, intent classification,
  thread routing, support ticket similarity, resolution matching, or retrieval eval.
status: active
last_validated: 2026-04-28
---

# Request Intent Resolution Pipeline

## Architecture Overview

```
OFFLINE � discover the space
  prior resolved threads
      ? LLM extract {intent_verb, objective_text, resolution_text, entity_schema}
      ? embed (objective_text + resolution_text)
      ? build kNN graph (cosine sim + entity schema overlap as edge weights)
      ? Louvain community detection ? emergent objective clusters
      ? per cluster: centroid vector + dominant entity signature
      ? store: resolved_threads (pgvector) + cluster_index (SQLite)

ONLINE � route into it
  new intake message
      ? extract {intent_verb, object_domain}      ? sparse, best-effort
      ? embed sparse representation
      ? nearest centroid(s) in cluster index
      ? retrieve top-k threads within cluster by cosine sim
      ? entity signature of cluster ? missing slots to collect

EVAL � continuous
  synthetic eval set
      ? routing pipeline
      ? LLM-as-judge (complete / partial / irrelevant)
      ? fitness scalar: context_recall, MRR@3, judge_score, context_precision
```

**Core principle:** the resolution corpus defines its own topology. Do not
fabricate a bridge from intake to resolution space � discover the structure
from the data, then route into it with whatever signal the intake provides.

The chain is: **intent ? objective cluster ? entity signature**.
Each hop is grounded in real data geometry, not generated assumptions.

---

## Stack

| Concern | Tool |
|---|---|
| Storage | PostgreSQL + pgvector (threads + embeddings) |
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

## Stage 1 � Schema Design

```python
from pydantic import BaseModel
from typing import Optional

class ThreadEntitySchema(BaseModel):
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

class ResolvedThread(BaseModel):
    """
    Require: thread_id unique, resolution_text non-empty
    Guarantee: entity_schema populated from resolution_text, not intake_text
    """
    thread_id: str
    intake_text: str
    objective_text: str
    resolution_text: str
    entity_schema: ThreadEntitySchema
    cluster_id: Optional[int] = None
    objective_embedding: Optional[list[float]] = None

class ClusterRecord(BaseModel):
    """
    Require: centroid_vector length matches embedding dim
    Guarantee: entity_signature contains only fields with >= min_support across members
    """
    cluster_id: int
    centroid_vector: list[float]
    entity_signature: dict        # dominant non-null slots across member threads
    member_thread_ids: list[str]
    size: int

class IntakeQuery(BaseModel):
    """
    Require: message non-empty
    Guarantee: routing proceeds even if extraction yields nothing � falls back
               to full corpus nearest-centroid search
    """
    message: str
    intent_verb: Optional[str] = None
    object_domain: Optional[str] = None
```

**Postgres DDL:**
```sql
CREATE EXTENSION IF NOT EXISTS vector;

CREATE TABLE resolved_threads (
    thread_id       TEXT PRIMARY KEY,
    intake_text     TEXT NOT NULL,
    objective_text  TEXT NOT NULL,
    resolution_text TEXT NOT NULL,
    entity_schema   JSONB NOT NULL DEFAULT '{}',
    cluster_id      INTEGER,
    obj_embedding   vector(768),
    indexed_at      TIMESTAMPTZ DEFAULT now()
);

CREATE INDEX ON resolved_threads USING ivfflat (obj_embedding vector_cosine_ops)
    WITH (lists = 100);
CREATE INDEX ON resolved_threads USING gin (entity_schema);
CREATE INDEX ON resolved_threads (cluster_id);
```

**SQLite cluster index DDL:**
```sql
CREATE TABLE clusters (
    cluster_id       INTEGER PRIMARY KEY,
    centroid_vector  BLOB NOT NULL,   -- np.ndarray serialized via pickle
    entity_signature TEXT NOT NULL,   -- JSON
    member_thread_ids TEXT NOT NULL,  -- JSON array
    size             INTEGER NOT NULL
);
```

**Validation gate:** postgres \d shows vector column + all three indexes.
SQLite clusters table exists.

---

## Stage 2 � Offline Extraction

Extract structured fields from prior resolved threads. Checkpoint to SQLite.

**Extraction prompt (system):**
```
You extract structured information from resolved support threads.
Return only valid JSON. No preamble, no markdown fences.

Schema:
{
  "intent_verb": "string � action the request is asking for (cancel, repair, refund, upgrade...)",
  "objective_text": "string � one sentence: what the request needs to achieve",
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
Request intake: {intake_text}
Resolution: {resolution_text}
```

**Contracts:**
- Require: `resolution_text` non-empty
- Guarantee: all null fields explicit, no missing keys
- Maintain: SQLite checkpoint `(thread_id, status, extracted_at)`
- Assert: `json.loads(response)` succeeds; on failure log + skip, do not crash

**Validation gate:** spot-check 10 random extractions � schema fields should
reflect resolution content, not intake content.

---

## Stage 3 � Embedding Index

```python
"""
Workflow:
  Load threads where obj_embedding IS NULL
  Batch-embed objective_text
  Write vectors to pgvector

Preconditions: Stage 2 complete
Failure modes: OOM (batch_size=32), dim mismatch (assert before write)
"""
from sentence_transformers import SentenceTransformer
import numpy as np

EMBED_MODEL = "avsolatorio/GIST-Embedding-v0"
BATCH_SIZE = 32

def index_threads(conn, model: SentenceTransformer):
    cur = conn.cursor()
    cur.execute(
        "SELECT thread_id, objective_text FROM resolved_threads WHERE obj_embedding IS NULL"
    )
    rows = cur.fetchall()

    for i in range(0, len(rows), BATCH_SIZE):
        batch = rows[i:i + BATCH_SIZE]
        ids = [r[0] for r in batch]
        texts = [r[1] for r in batch]
        embeddings = model.encode(texts, normalize_embeddings=True)
        assert embeddings.shape[1] == 768, f"Dim mismatch: {embeddings.shape[1]}"
        for thread_id, vec in zip(ids, embeddings):
            cur.execute(
                "UPDATE resolved_threads SET obj_embedding = %s WHERE thread_id = %s",
                (vec.tolist(), thread_id)
            )
        conn.commit()
```

**Validation gate:** `SELECT count(*) FROM resolved_threads WHERE obj_embedding IS NULL` = 0.

---

## Stage 4 � Cluster Index (Louvain/Leiden)

This stage defines the objective space topology. All online routing depends on it.

```python
"""
Workflow:
  Load all embeddings + entity_schemas from postgres
  Build kNN graph: nodes = threads, edges = top-k neighbors weighted by combined sim
  Run Leiden community detection ? clusters
  Per cluster: compute centroid, derive entity signature (dominant non-null slots)
  Write cluster assignments back to resolved_threads.cluster_id
  Write cluster records to SQLite cluster index

Preconditions: all obj_embeddings populated
Failure modes: disconnected graph (lower kNN k), too many tiny clusters
               (increase resolution parameter), too few large clusters
               (decrease resolution parameter)

Tunable parameters:
  KNN_K         = 15      neighbors per node in graph construction
  EDGE_W_COSINE = 0.7     weight of cosine sim in edge weight
  EDGE_W_SCHEMA = 0.3     weight of entity schema overlap in edge weight
  LEIDEN_RES    = 1.0     resolution parameter � higher = more/smaller clusters
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
                        thread_ids: list[str], schemas: list[dict]):
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

        member_ids = [thread_ids[i] for i in member_indices]

        # write cluster assignments back to postgres
        for thread_id in member_ids:
            cur.execute(
                "UPDATE resolved_threads SET cluster_id = %s WHERE thread_id = %s",
                (cluster_id, thread_id)
            )

        # write cluster record to SQLite
        sqlite_cur.execute("""
            INSERT OR REPLACE INTO clusters
                (cluster_id, centroid_vector, entity_signature, member_thread_ids, size)
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
- `SELECT count(distinct cluster_id) FROM resolved_threads WHERE cluster_id IS NOT NULL` > 3
- Spot-check 3 clusters: member threads should share a recognizable objective type
- `entity_signature` for each cluster should have >= 1 dominant field

---

## Stage 5 � Retrieval

Soft cluster routing: use global seeds to score the landscape, turn those
signals into mixture-weighted cluster budgets, then do within-cluster retrieval
with MMR and keep a non-cluster-filtered global backstop alive.

```python
"""
Workflow:
  1. Embed sparse intake representation (intent_verb + object_domain, or raw message)
  2. Pull a small global seed set from the full corpus
  3. Score clusters using centroid similarity + seed evidence mass
  4. Allocate retrieval budget across the top clusters proportionally
  5. Retrieve candidates within each cluster and diversify with MMR
  6. Return matches + entity signature diff (missing slots)

Preconditions: cluster index built, all obj_embeddings populated
Failure modes: intake too sparse to route (fall back to global nearest-centroid),
                cluster too small (expand to top-2 clusters)
"""

GLOBAL_SEED_K = 8        # seed evidence pulled before cluster budgeting
CLUSTER_TOP_N = 3        # consider top-N nearest clusters
TOTAL_RESULT_BUDGET = 8  # total cluster-filtered result budget
WITHIN_CLUSTER_K = 6     # candidate threads to pull per cluster before MMR
MMR_LAMBDA = 0.7         # relevance-vs-diversity tradeoff
GLOBAL_BACKSTOP_K = 3    # non-cluster-filtered fallback results

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
        SELECT thread_id, objective_text, resolution_text, entity_schema,
               obj_embedding, cluster_id,
               1 - (obj_embedding <=> %s::vector) AS cosine_sim
        FROM resolved_threads
        WHERE cluster_id = %s
        ORDER BY cosine_sim DESC
        LIMIT %s
    """, (query_vec.tolist(), cluster_id, k))
    return [
        {
            "thread_id": r[0],
            "objective_text": r[1],
            "resolution_text": r[2],
            "entity_schema": r[3],
            "embedding": r[4],
            "cluster_id": r[5],
            "cosine_sim": r[6]
        }
        for r in cur.fetchall()
    ]


def retrieve_global(conn, query_vec: np.ndarray, k: int) -> list[dict]:
    cur = conn.cursor()
    cur.execute("""
        SELECT thread_id, objective_text, resolution_text, entity_schema,
               obj_embedding, cluster_id,
               1 - (obj_embedding <=> %s::vector) AS cosine_sim
        FROM resolved_threads
        ORDER BY cosine_sim DESC
        LIMIT %s
    """, (query_vec.tolist(), k))
    return [
        {
            "thread_id": r[0],
            "objective_text": r[1],
            "resolution_text": r[2],
            "entity_schema": r[3],
            "embedding": r[4],
            "cluster_id": r[5],
            "cosine_sim": r[6]
        }
        for r in cur.fetchall()
    ]


def score_clusters_with_seeds(
    clusters: list[dict],
    seed_threads: list[dict],
    top_n: int,
) -> list[dict]:
    """
    Combine centroid similarity with global-seed evidence mass so cluster routing
    is soft and data-backed rather than a hard single-cluster gate.
    """
    seed_mass = {}
    for row in seed_threads:
        cluster_id = row.get("cluster_id")
        if cluster_id is None:
            continue
        seed_mass[cluster_id] = seed_mass.get(cluster_id, 0.0) + max(row["cosine_sim"], 0.0)

    scored = []
    for cluster in clusters:
        mass = seed_mass.get(cluster["cluster_id"], 0.0)
        cluster_score = 0.7 * cluster["centroid_sim"] + 0.3 * mass
        scored.append({**cluster, "seed_mass": mass, "cluster_score": cluster_score})
    return sorted(scored, key=lambda x: x["cluster_score"], reverse=True)[:top_n]


def allocate_cluster_budget(scored_clusters: list[dict], total_budget: int) -> list[dict]:
    """
    Spread the result budget proportionally across the winning clusters.
    Every surviving cluster gets at least one slot; stronger clusters get more.
    """
    if not scored_clusters:
        return []

    positive_mass = sum(max(c["cluster_score"], 0.0) for c in scored_clusters)
    remaining = total_budget - len(scored_clusters)
    allocated = []
    for cluster in scored_clusters:
        if positive_mass <= 0 or remaining <= 0:
            budget = 1
        else:
            share = max(cluster["cluster_score"], 0.0) / positive_mass
            budget = 1 + int(round(share * remaining))
        allocated.append({**cluster, "budget": max(1, budget)})
    return allocated


def mmr_select(query_vec: np.ndarray, candidates: list[dict], k: int, lambda_mult: float) -> list[dict]:
    """
    Maximal marginal relevance over thread candidates. Keeps high-similarity hits
    while avoiding near-duplicate resolutions from the same cluster slice.
    """
    selected = []
    remaining = candidates[:]
    while remaining and len(selected) < k:
        best_idx = 0
        best_score = float("-inf")
        for idx, candidate in enumerate(remaining):
            redundancy = 0.0
            if selected:
                redundancy = max(
                    cosine_similarity(
                        np.array(candidate["embedding"]).reshape(1, -1),
                        np.array(chosen["embedding"]).reshape(1, -1),
                    )[0][0]
                    for chosen in selected
                )
            score = lambda_mult * candidate["cosine_sim"] - (1 - lambda_mult) * redundancy
            if score > best_score:
                best_score = score
                best_idx = idx
        selected.append(remaining.pop(best_idx))
    return selected


def elicit_slots(entity_signature: dict, known: dict) -> list[str]:
    """
    Fields the cluster expects (entity_signature keys) that are absent in known.
    These are the fields to ask for next turn.
    """
    return [k for k in entity_signature if not known.get(k)]


def resolve(message: str, known_entities: dict,
            conn, sqlite_conn, model) -> list[dict]:
    # embed whatever the intake gives us � sparse is fine
    query_vec = model.encode([message], normalize_embeddings=True)[0]

    clusters = load_cluster_index(sqlite_conn)
    seeded_global = retrieve_global(conn, query_vec, GLOBAL_SEED_K)
    seed_cluster_ids = {row["cluster_id"] for row in seeded_global if row.get("cluster_id") is not None}
    for cluster in clusters:
        cluster["centroid_sim"] = float(np.dot(query_vec, cluster["centroid"]))
    top_clusters = score_clusters_with_seeds(
        [c for c in clusters if c["cluster_id"] in seed_cluster_ids] or clusters,
        seeded_global,
        CLUSTER_TOP_N,
    )
    budgeted_clusters = allocate_cluster_budget(top_clusters, TOTAL_RESULT_BUDGET)

    results = []
    for cluster in budgeted_clusters:
        threads = retrieve_within_cluster(conn, cluster["cluster_id"], query_vec, WITHIN_CLUSTER_K)
        threads = mmr_select(query_vec, threads, cluster["budget"], MMR_LAMBDA)
        missing = elicit_slots(cluster["entity_signature"], known_entities)
        for thread in threads:
            results.append({
                **thread,
                "cluster_id": cluster["cluster_id"],
                "centroid_sim": cluster["centroid_sim"],
                "seed_mass": cluster["seed_mass"],
                "missing_slots": missing
            })

    backstop = retrieve_global(conn, query_vec, GLOBAL_BACKSTOP_K)
    for thread in backstop:
        results.append({
            **thread,
            "cluster_id": None,
            "centroid_sim": None,
            "missing_slots": []
        })

    deduped = {}
    for row in results:
        prior = deduped.get(row["thread_id"])
        if prior is None or row["cosine_sim"] > prior["cosine_sim"]:
            deduped[row["thread_id"]] = row

    final_rows = []
    for row in sorted(deduped.values(), key=lambda x: x["cosine_sim"], reverse=True):
        clean_row = dict(row)
        clean_row.pop("embedding", None)
        final_rows.append(clean_row)
    return final_rows
```

**Validation gate:** retrieve on 5 known threads using only their intent verb.
Correct cluster should appear in top-3 for at least 4/5, and the final result
set should contain at least 2 non-duplicate resolution patterns when the top
cluster has many near-identical threads.

**Routing rule:** clusters bias retrieval, they do not imprison it. Use global
seed hits to estimate which clusters deserve budget, allocate that budget as a
mixture rather than a winner-take-all gate, diversify within-cluster hits with
MMR, and keep a global backstop outside the cluster-filtered pool so
near-boundary threads are still recoverable.

---

## Stage 6 � Eval Pipeline

### Ground Truth Construction

**Tier 1 � Self-retrieval (free)**
Hold out 10% of threads. Route each by its own intake text. Assert correct
cluster appears in top-N and correct thread in top-k within cluster.

**Tier 2 � Synthetic queries (primary eval set)**
Generate sparse intake messages from resolutions � these simulate real intake
signal without entities.

```
System:
Given a resolved support thread, generate {N} distinct request
intake messages that this resolution would answer. Messages should be
sparse � terse, vague, intent-present but entity-absent. No account numbers,
no product names. Just the action and rough domain.
Output only a JSON array of strings.

User:
Resolution: {resolution_text}
```

Store as `(synthetic_query, correct_thread_id, correct_cluster_id)` in SQLite.
Target: 3 synthetic queries per thread minimum.

**Tier 3 � Human-labeled pairs**
Final validation only.

---

### LLM-as-Judge

```
System:
You evaluate whether a retrieved support-thread resolution would solve
a new request. Score using exactly these three classes.

complete (1.0)  � resolution addresses the query's core issue; agent could
                  use it directly with minor slot substitution
partial (0.5)   � related but missing key steps, or similar but not identical
irrelevant (0.0)� does not apply; using it would mislead the agent

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
New request: {message}
Retrieved resolution from prior thread: {resolution_text}
```

Run each judgment 3 times, take majority. Flag 3-way disagreements for manual review.

---

### Metrics

```python
def fitness_score(
    context_recall: float,     # correct thread in top-k at all
    mean_judge_score: float,   # judge score on top-1 result
    mrr_at_3: float,           # reciprocal rank of first complete hit
    context_precision: float   # fraction of top-k scoring complete or partial
) -> float:
    """
    context_recall weighted highest � a miss at retrieval is unrecoverable.
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

Pair this with the `mlflow` skill so each trial logs:

- parameter values
- `fitness_score`
- component metrics from `run_eval_sample(...)`
- experiment tags for corpus / graph version / routing mode
- artifacts that explain failures or wins

Use Optuna for the search state and MLflow for the experiment ledger.

**Dev discipline:** 10% sample, < 5 min wall time. Parallelize judge calls.
Full-corpus eval before deploy only.

---

## Stage 7 � FastAPI Service

```python
from fastapi import FastAPI
from pydantic import BaseModel

app = FastAPI()

class QueryRequest(BaseModel):
    message: str
    known_entities: dict = {}

class MatchResult(BaseModel):
    thread_id: str
    cluster_id: int | None
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

## Stage 8 � Streamlit UI

```python
import streamlit as st
import requests

st.title("Request Intent Resolver")
message = st.text_area("Request message")

if st.button("Resolve") and message:
    resp = requests.post("http://localhost:8000/resolve", json={"message": message})
    for r in resp.json():
        cluster_label = r["cluster_id"] if r["cluster_id"] is not None else "global"
        with st.expander(f"Cluster {cluster_label} � {r['thread_id']} (sim {r['cosine_sim']:.2f})"):
            st.write("**Objective:**", r["objective_text"])
            st.write("**Resolution:**", r["resolution_text"])
            if r["missing_slots"]:
                st.warning("Still needed: " + ", ".join(r["missing_slots"]))
```

---

## Validation Progression

```
unit:       1 thread through full pipeline � cluster assigned, retrieval returns match
small:      10 threads, correct cluster in top-2 for >= 8/10
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
request_intent_resolution/
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
Validation gate before advancing. 10% sample during development � never
wait for a full-corpus run during iteration.

---

## Orchestrator: arXiv Research Variant

Adapts the same intent-routing pattern to scientific paper retrieval.
"Resolved threads" → papers (use case + pseudocode).
"Solution" → extracted algorithm context package.

### Architecture

```
OFFLINE — handled by auto-ingest · arxiv-bridge
  paper abstracts
      → LLM extract (BM25 ⊕ semantic · RRF)
      → SPO triplets + entities
      → entity_set (frozenset) → fingerprint
      → throughline (q_score, entity-anchored)  ──► ingredient KG (entity-indexed)
      → use case · objective function           ──► utility fn index

QUERY TIME — orchestrator
  query
      → LLM extract SPO triples (entailed only)
      → 3-hop KG expansion → augmented entity set
      → intent → nearest use case (utility fn)
      → entity-set match + q_score → top throughlines + papers
      → read · extract pseudocode              (check _methods.md first; extract if absent)
      → group throughline synthesis            (shared entity subset of top-K)
      → solution: group throughline · pseudocode · use case · query
```

The KG is infrastructure. Query time sees only its output (top papers + throughlines),
not its internals. The query itself becomes a mini-RDF graph matched against
the entity-indexed throughline index.

### Throughline Indexing: Entity-Anchored (Offline)

Throughlines are indexed by their **entity set** — the subjects and objects from the
supporting SPO triplets. The entity set is the premise fingerprint. The identity of a
throughline is its premise set, not its claim text (see `agentic_kg_memory` for the full
schema and q-score update cycle).

```text
For each paper (offline, at ingest):
  1. extract SPO triplets from abstract + methods section
  2. entity_set = {norm(s) for (s,p,o) in triples} | {norm(o) for (s,p,o) in triples}
  3. fingerprint = hash(frozenset(entity_set))
  4. index row: (fingerprint, throughline_text, q_score, paper_ids, entity_list, use_case)

At retrieval:
  score = alpha * Jaccard(query_entities, throughline_entities)
         + beta  * cosine(embed(query), embed(throughline.claim_text))
         + gamma * throughline.q_score
  default: alpha=0.5, beta=0.3, gamma=0.2  (tune with Optuna against downstream fitness)
```

Entity-set matching is the primary retrieval channel; semantic similarity balances when
entity sets are sparse or the query is abstract.

---

### Query Expansion: Query as RDF Graph

Before retrieval, extract the user query as its own entailed SPO graph, then expand
3 hops outward through the ingredient KG to build an augmented entity set.

```text
user query text
    → LLM: extract entailed SPO triplets  (only triples implied by the query text;
                                           reject hallucinated or freely-generated triples)
    → hop 1: for each extracted entity, retrieve 1-edge KG neighbors
    → hop 2: expand from hop-1 entities (2 edges out)
    → hop 3: one more expansion (3 edges out)
    → augmented_entity_set = entities(query_triples) | hop1 | hop2 | hop3
```

**Why 3 hops** — hop 1 = direct synonyms/hyponyms, hop 2 = related methods/components,
hop 3 = broader technique class. Signal-to-noise degrades beyond 3 hops.

**Entailment discipline** — extracted triples must be entailed by the query text, matching
the `agentic_kg_memory` rule: classify each candidate triple as {entails | neutral | contradicts};
keep only entailing ones.

```python
QUERY_EXPANSION_PROMPT = (
    "Extract SPO triplets entailed by this query. Return only triples where the "
    "predicate and both nodes are directly implied by the query text. No hallucination. "
    "Output: JSON array of [subject, predicate, object] arrays.\n"
    "Query: {query}"
)


def expand_query_entities(query: str, kg_conn, hop_limit: int = 3) -> set:
    """
    Extract + expand query entities via KG traversal.
    Require: query non-empty, kg_conn open to the ingredient KG.
    Guarantee: returns normalized entity set (empty set valid when KG is cold).
    Maintain: only entailed triples are used; never freely-generated ones.
    """
    raw = llm_json(QUERY_EXPANSION_PROMPT.format(query=query))
    triples = raw if isinstance(raw, list) else []
    entities = {norm(n) for t in triples for n in (t[0], t[2]) if len(t) >= 3}

    frontier = set(entities)
    for _ in range(hop_limit):
        neighbors = kg_neighbors(frontier, kg_conn)   # 1-hop BFS in ingredient KG
        new_ents = neighbors - entities
        entities |= new_ents
        frontier = new_ents
        if not frontier:
            break

    return entities
```

---

### Entity-Set Retrieval + Q-Score

Use the augmented entity set to match throughline candidates; rank by composite score.

```python
import numpy as np


def score_throughlines(
    query_entities: set,
    query_embedding,         # np.ndarray, unit-normalised
    candidates: list,        # list[dict] from throughline index
    alpha: float = 0.5,
    beta: float = 0.3,
    gamma: float = 0.2,
) -> list:
    """
    Rank throughlines by entity overlap + semantic similarity + q_score.
    Require: each candidate has keys: entities (list), claim_embedding (np.ndarray),
             q_score (float).
    Guarantee: returns candidates sorted by composite score descending.
    """
    for c in candidates:
        t_ents = set(c["entities"])
        union = query_entities | t_ents
        jaccard = len(query_entities & t_ents) / len(union) if union else 0.0
        sem_sim = float(np.dot(query_embedding, c["claim_embedding"]))
        c["composite"] = alpha * jaccard + beta * sem_sim + gamma * c["q_score"]
    return sorted(candidates, key=lambda x: x["composite"], reverse=True)
```

**Cross-throughline comparison** — to compare competing group throughlines across
different entity subsets, rank by `q_score * Jaccard(target_entity_set, throughline.shared_entities)`.
The highest adjusted score is the current best explanation for that solution space.

---

### Group Throughline Synthesis

After retrieving top-K papers and their individual throughlines, synthesize a single
**group throughline** grounded in their shared entity subset. This is the deductive
cross-paper conclusion (global throughline) returned as the solution frame.

```python
GROUP_THROUGHLINE_PROMPT = (
    "Synthesize a group throughline from multiple paper throughlines.\n"
    "The shared entity set defines the scope — stay within it.\n\n"
    "Query: {query}\n"
    "Shared entities: {shared_entities}\n"
    "Individual throughlines:\n{throughlines}\n"
    "Key methods (pseudocode summaries):\n{methods}\n\n"
    "Produce a single concise throughline (2–4 sentences) that:\n"
    "- spans all retrieved sources\n"
    "- is grounded only in the shared entity premises\n"
    "- names the strongest point of convergence and any unresolved tension\n\n"
    'Return JSON: {{\"claim_text\": \"...\", \"tension\": \"...\" or null}}'
)


def synthesize_group_throughline(
    query: str,
    top_k_results: list,       # list[dict] each with: throughline, entities, pseudocode
    existing_index: dict,      # fingerprint (int) -> stored throughline dict
    alpha: float = 0.1,
) -> dict:
    """
    Produce or update the group throughline for the retrieved entity cluster.
    Require: top_k_results each have keys: throughline (str), entities (list).
    Guarantee: fingerprint-matched entries are updated, not duplicated.
    Maintain: q_score updated via q_old + alpha*(reward - q_old); never reset.
    """
    entity_sets = [set(r["entities"]) for r in top_k_results if r.get("entities")]
    shared = set.intersection(*entity_sets) if entity_sets else set()
    fingerprint = hash(frozenset(norm(e) for e in shared))

    if fingerprint in existing_index:
        stored = existing_index[fingerprint]
        reward = sum(r.get("composite", 0.5) for r in top_k_results) / max(len(top_k_results), 1)
        stored["q_score"] = stored["q_score"] + alpha * (reward - stored["q_score"])
        stored["visit_count"] = stored.get("visit_count", 0) + 1
        return stored

    throughlines_text = "\n".join(
        f"  [{i+1}] {r['throughline']}" for i, r in enumerate(top_k_results)
    )
    methods_text = "\n".join(
        f"  [{i+1}] {(r.get('pseudocode') or '')[:200]}" for i, r in enumerate(top_k_results)
    )
    result = llm_json(GROUP_THROUGHLINE_PROMPT.format(
        query=query,
        shared_entities=", ".join(sorted(shared)),
        throughlines=throughlines_text,
        methods=methods_text,
    ))
    return {
        "fingerprint": fingerprint,
        "shared_entities": list(shared),
        "claim_text": result.get("claim_text", ""),
        "tension": result.get("tension"),
        "q_score": 0.5,
        "visit_count": 1,
        "paper_ids": [r["arxiv_id"] for r in top_k_results],
    }
```

**Q-score semantics** mirror `agentic_kg_memory` exactly — running average over retrievals;
repeated confirmation compounds asymptotically toward 1; contradiction drives it down;
the prior is never reset.

---

### Orchestration Flow

```python
"""
Orchestrate a research query to a solution context package.

Preconditions:
    - arxiv_retriever.py reachable (pgvector + BM25 + ColBERT pipeline)
    - arxiv_bridge.py reachable for upstream discovery when local corpus is thin
    - extract_methods.py + methods_sspv2.md present for inline extraction
    - CSV: papers/post_processed/arxiv_data_with_analysis_cleaned.csv (use_case column)

Postconditions:
    - Returns list[SolutionContext] with pseudocode, use_case, and original query
    - Papers with pre-existing _methods.md are served instantly (no LLM call)
    - Novel papers without _methods.md are queued via auto-ingest or extracted inline

Failure modes:
    - No papers retrieved: expand via arxiv-bridge (--bridge flag on run.py)
    - _methods.md absent + proxy down: return empty pseudocode, enriched=False
    - KG cold / pgvector unavailable: fall back to BM25-only retrieval
"""

import csv as csv_module
import subprocess
from dataclasses import dataclass
from pathlib import Path

REPO_ROOT = Path(r"C:\Users\user\arxiv_id_lists")
PYTHON    = r"C:\Users\user\py310\Scripts\python.exe"
POST_PROC = REPO_ROOT / "papers" / "post_processed"
MAIN_CSV  = POST_PROC / "arxiv_data_with_analysis_cleaned.csv"


@dataclass
class SolutionContext:
    """
    Final output package assembled for each top paper.
    Require: at least one of pseudocode/use_case must be non-empty.
    """
    arxiv_id:        str
    query:           str
    use_case:        str    # from utility fn index / CSV (thesis + utility fields)
    pseudocode:      str    # from _methods.md; empty when extraction is pending
    enriched:        bool   # True iff _methods.md was present before this call
    throughline:     str = ""   # individual paper throughline (entity-anchored)
    entities:        list = None  # normalized entity set (premise fingerprint basis)
    composite_score: float = 0.0  # alpha*Jaccard + beta*cosine + gamma*q_score


@dataclass
class GroupThroughline:
    """
    Cross-paper deductive synthesis over the shared entity subset of top-K results.
    Produced by synthesize_group_throughline(); returned alongside SolutionContext list.
    """
    claim_text:      str
    tension:         str        # unresolved tension across sources, or empty string
    shared_entities: list
    q_score:         float
    visit_count:     int
    paper_ids:       list
    fingerprint:     int


def _stem(arxiv_id: str) -> str:
    return arxiv_id.replace(".", "_")


def _methods_path(arxiv_id: str) -> Path:
    return POST_PROC / f"{_stem(arxiv_id)}_methods.md"


def _load_csv_index() -> dict[str, dict]:
    """Load main CSV as {stem_id: row}. Both dot and underscore IDs are indexed."""
    if not MAIN_CSV.is_file():
        return {}
    index: dict[str, dict] = {}
    with open(MAIN_CSV, encoding="utf-8", newline="") as fh:
        for row in csv_module.DictReader(fh):
            aid = row.get("arxiv_id", "").strip().strip('"')
            if aid:
                index[aid.replace(".", "_")] = row
                index[aid.replace("_", ".")] = row
    return index


def _load_use_case(arxiv_id: str, csv_index: dict) -> str:
    """Pull thesis + top-2 utility strings from the CSV row for this paper."""
    row = csv_index.get(_stem(arxiv_id)) or csv_index.get(arxiv_id) or {}
    thesis = row.get("thesis", "") or ""
    try:
        utility = __import__("ast").literal_eval(row.get("utility", "[]") or "[]")
    except Exception:
        utility = []
    return "; ".join(filter(None, [thesis] + list(utility[:2])))


def retrieve_top_papers(query: str, top_k: int = 10) -> list[str]:
    """
    Run ArxivRetriever and return sorted list of arxiv_ids.
    Require: pgvector + langchain DB accessible at localhost:5432.
    Guarantee: list ordered by final_score descending.
    """
    import sys
    sys.path.insert(0, str(REPO_ROOT))
    from arxiv_retriever import ArxivRetriever
    from pgvector_retriever import PGVectorConfig
    config = PGVectorConfig()          # defaults to localhost:5432 langchain DB
    retriever = ArxivRetriever(config)
    results = retriever.search(query, top_k=top_k)
    return [r.doc_id for r in results]


def assemble_solution(
    query: str,
    arxiv_ids: list[str],
    csv_index: dict,
    extract_inline: bool = False,
) -> list[SolutionContext]:
    """
    For each paper: load _methods.md if present; otherwise queue or extract inline.

    Require: arxiv_ids non-empty, csv_index loaded via _load_csv_index().
    Guarantee: every returned SolutionContext has use_case populated.
    Maintain: papers already extracted are never re-extracted (invariant).
    Assert: after inline extraction, _methods.md presence is re-checked before reading.
    """
    contexts: list[SolutionContext] = []
    for aid in arxiv_ids:
        mp = _methods_path(aid)
        if mp.is_file():
            pseudocode = mp.read_text(encoding="utf-8")
            enriched   = True
        elif extract_inline:
            md_path = POST_PROC / f"{_stem(aid)}.md"
            if md_path.is_file():
                subprocess.run(
                    [PYTHON, str(REPO_ROOT / "extract_methods.py"), str(md_path)],
                    check=False,
                )
                pseudocode = mp.read_text(encoding="utf-8") if mp.is_file() else ""
                enriched   = bool(pseudocode)
            else:
                pseudocode, enriched = "", False
        else:
            pseudocode, enriched = "", False

        contexts.append(SolutionContext(
            arxiv_id=aid,
            query=query,
            use_case=_load_use_case(aid, csv_index),
            pseudocode=pseudocode,
            enriched=enriched,
        ))
    return contexts


def orchestrate(query: str, top_k: int = 10, extract_inline: bool = False) -> list[SolutionContext]:
    """
    End-to-end: query → top papers → solution context packages.

    Require: query non-empty.
    Guarantee: returns list[SolutionContext] sorted by retrieval rank.
    """
    csv_index = _load_csv_index()
    arxiv_ids = retrieve_top_papers(query, top_k=top_k)
    return assemble_solution(query, arxiv_ids, csv_index, extract_inline=extract_inline)
```

### Solution Package Format

**`SolutionContext`** (one per paper):

| Field | Source | Notes |
|---|---|---|
| `pseudocode` | `_methods.md` (Phase 5) | Core algorithm extracted via gpt-4.1 |
| `use_case` | CSV `utility` + `thesis` columns | Loaded from offline LLM extraction |
| `query` | Passed through unchanged | Original user query |
| `enriched` | `bool` | `False` = extraction pending; queue via auto-ingest |
| `throughline` | throughline index | Entity-anchored per-paper conclusion |
| `entities` | SPO triplet extraction | Normalized entity set (premise fingerprint basis) |
| `composite_score` | Retrieval scoring | alpha*Jaccard + beta*cosine + gamma*q_score |

**`GroupThroughline`** (one per query result set):

| Field | Source | Notes |
|---|---|---|
| `claim_text` | LLM synthesis | Cross-paper deductive conclusion (global throughline) |
| `tension` | LLM synthesis | Unresolved conflict across sources, or empty string |
| `shared_entities` | Entity intersection | Entities common to all top-K results |
| `q_score` | Running average | Prior never reset; compounding confirmation |
| `paper_ids` | Retrieval | Source paper ids for this group synthesis |

The assembled package is the context window for downstream synthesis (not a graph artifact).

### Skip-if-Extracted Rule

Papers are never re-extracted. The invariant is enforced in three places:

1. `arxiv_retriever.py` — attaches `metadata["methods"]` from `_methods.md` if present.
2. `ingest_daemon.py` — checks `_methods.md` existence before entering Phase 5.
3. `assemble_solution()` above — reads `_methods.md` directly; skips the subprocess call.

To force re-extraction: delete `{stem}_methods.md` and re-queue via `auto-ingest`.

### Queue Unenriched Papers

When enriched=False, hand off to the background daemon instead of blocking:

```python
import sys
sys.path.insert(0, str(REPO_ROOT))
from ingest_mcp import queue_papers

pending = [ctx.arxiv_id for ctx in contexts if not ctx.enriched]
if pending:
    queue_papers(pending, priority=5.0, repo_root=str(REPO_ROOT))
    # Daemon enriches in background; _methods.md present next session
```

Use `arxiv_pipeline/run.py --extract` for synchronous inline extraction when the user
is waiting for a complete result (expected latency: 5–18 min for 1–3 papers).

### CLI Invocation

```bash
cd C:\Users\user\arxiv_id_lists

# Full orchestration: retrieve + bridge-discover + extract solution package
python arxiv_pipeline\run.py "agentic memory" --bridge --bridge_derive 3 --extract --output _solution.md

# Retrieval only (KG + BM25 + ColBERT, no extraction)
python arxiv_retriever.py --search "agentic memory" --top-k 10 --save _results.md

# Bridge-only (upstream S2 / arXiv discovery, no local retrieval)
python arxiv_bridge.py "agentic memory" --limit 20 --top-k 10

# Phase 5 inline (extract pseudocode from a single enriched paper)
python extract_methods.py papers\post_processed\2601_09113.md
```

### Related Skills

- `auto-ingest` — background Phase 3–5 daemon and MCP server for queue inspection
- `arxiv-bridge` — upstream Semantic Scholar / arXiv Atom discovery layer
- `pdf-extraction` — standalone PDF → enriched-Markdown workflow
- `agentic_kg_memory` — throughline schema, q-score update cycle, fingerprint dedup semantics
<!-- consolidation:see-also:start -->
## See Also
[[agentic_kg_memory]]  [[react-fastapi-sqlite]]  [[optuna-nested-cv]]  [[mlflow]]  [[representation-pipeline]]
<!-- consolidation:see-also:end -->
