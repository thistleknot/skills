# Retrieval spec — aggregated multi-lane → RRF → MMR → late interaction

**Spec layer:** Behavioral (ordered, staged pipeline) + Structural (lanes, config,
retrieval unit). This is the canonical spec for the `data_science_skills`
retrieval feature set. All lanes and stages are **retained and configurable** —
nothing is deleted; measured evidence governs *defaults and when to enable each*,
not whether the capability exists.

Entry point: `run_retrieval(query, k)` (plain callable) / `retrieve` (MCP tool) in
`scripts/mcp_server.py`. Retrieval unit = **whole skill**: ranked chunks vote for
their skill; top-k skills are returned with all chunks + ToC/entity tags.

## Pipeline (full superset)

```
query
  │
  ├── LANE A  dense            nomic cosine over pgvector (semantic)
  ├── LANE B  tsvector-BM25     true BM25 in-DB over content_tsv (lexical/OOV)
  ├── LANE C  community         Leiden community + subgraph-DWPC, gated (thematic)
  └── LANE D  topic-route       ToC top-2 topic-restricted dense (routing)      [toggle]
  │       (lanes run in PARALLEL via the async aggregated retriever:
  │        asyncio.gather BARRIER + per-lane wait_for STALL GUARD, own conn/lane)
  ▼
STAGE 1  RRF fusion            weighted reciprocal-rank fusion of enabled lanes
  ▼
STAGE 2  MMR                    diversity rerank over [cosine, density, fused] matrix
  ▼
STAGE 3  late interaction      ColBERT v2 entailment rerank
  ▼
whole-skill rollup → top-k
```

`RETRIEVAL_MODE` selects the active configuration (all retained):

| mode | lanes → stages | default? |
|---|---|---|
| `hybrid` | A ⊕ B → RRF | **DEFAULT** (production floor) |
| `dense` | A only | floor / ablation |
| `fusion` | A ⊕ entity-BM25 → RRF | exact-skill lookup toggle |
| `route` | A ⊕ D → RRF | routing toggle |
| `cascade` | A ⊕ B ⊕ C (⊕ graph-expand) → RRF → MMR → ColBERT | full pipeline |

The aggregated retriever (async, parallel lanes, barrier, per-lane stall guard)
is the serving pattern for any multi-lane mode (`scripts/eval_aggregated.py`
`aggregate()` is the reference implementation).

## Lanes

### A — dense (semantic)
`cosine_seed(store, query, k)` — nomic-embed-text over the `data_science_skills`
PGVector collection. Baseline; covers paraphrase / synonym (terms not in the text).

### B — tsvector-BM25 (lexical, the big lever)
`ts_bm25_seed(conn, query, k)` — true BM25 computed **in one SQL query**:
- Source: `content_tsv` — generated STORED column `to_tsvector('english', document)`,
  snowball-stemmed, GIN-indexed. Native FTS, no extension (pg_bestmatch unavailable).
- tf: `array_length((unnest(content_tsv)).positions,1)` (real per-doc term freq).
- IDF: `ln((N-ndoc+0.5)/(ndoc+0.5)+1)`, materialized in `bm25_idf` via `ts_stat`.
- `k1=1.5`, **`b=0`** — length norm measured to HURT (chunks vote for their whole
  skill, so a longer term-rich chunk is more on-topic evidence, not a length cheat;
  `content_len`/`avgdl=72.1` exist for `b>0` but default off).
- Covers exact-corpus terms + domain/OOV entities embeddings never saw.

### C — community (thematic / topical-cluster)
`lane_community` (see `scripts/eval_aggregated.py`): seed = top dense skill →
its within-community **subgraph-DWPC** neighbors, **gated** by community
density/conductance (skip mushy communities, `conductance > 0.6` → dense fallback).
Built by `build_graph_report.py` from `desc_checkpoint.db` (see Graph construction).

### D — topic-route (routing) [toggle]
`route_topics` + `topic_branch`: embed(query)·11 topic-centroids → top-2 topics →
dense restricted to those topics. "ToC-seeded query expansion" for the closed
11-folder vocab (O(1), no LLM rephrase).

## Stages

### STAGE 1 — RRF fusion
Weighted reciprocal-rank fusion over enabled lanes: `score(id) = Σ_lane w /
(rrf_k + rank_lane(id))`, `rrf_k=60`. `w_graph`/`w_route` parametrize the graph/
route lane weight (start ≤1; raise only if the ablation earns it — nested-vs-flat
fusion reduces to this weight).

### STAGE 2 — MMR (diversity)
`mmr_rerank(pool, cosine_sims, densities, k)` over a `[cosine, density, fused]`
score matrix, `MMR_LAMBDA=0.7`. Diversity rerank; enabled in `cascade`.

### STAGE 3 — late interaction (ColBERT v2)
`colbert_rerank(query, pool, k)` — `colbert-ir/colbertv2.0` token-level late
interaction / entailment rerank. Enabled in `cascade`.

## Graph construction (feeds LANE C — offline, deterministic, no LLM)

The graph's job is **clustering**, not retrieval scoring (GraphRAG's actual role
— cf. cloned `microsoft/graphrag`: extract → Leiden communities → summaries).
Our deterministic adaptation:
1. `build_desc_checkpoint.py` — embed the 1,467 `skill_description`s (nomic) →
   `desc_checkpoint.db` (`skill_derivations(skill_name, embedding_json)`).
2. `build_graph_report.py` — reuses `consolidation/graph_analysis.py`
   (density/conductance/betweenness/Louvain) over the cosine graph (adaptive τ),
   with **subgraph-DWPC computed VECTORIZED** (the skill's k=2 DWPC is pure-python
   O(N³), reimplemented as `Abin@Abin` matmul — identical formula, 19s vs timeout).
   Coarse cosine-graph communities act as pools; **DWPC is computed within each
   community subgraph** (hub-correction relative to the community). Emits
   `graph_report.json`: `skill_comm`, `comm_metrics` (density/conductance/lcc,
   the gate), `dwpc_neighbors` (within-community hub-corrected ranking).

Community "reports" = pre-written `skill_description`s (no LLM summary step —
skills already are curated communities with summaries).

## Measured evidence (deterministic bridging gold n=33; thematic n=20, leakage-scrubbed)

| feature | regime | result vs dense/hybrid | disposition |
|---|---|---|---|
| dense ⊕ tsvector-BM25 (hybrid) | local | **+0.202 R@20** (2×), low variance | **DEFAULT** |
| community lane (Leiden + subgraph-DWPC, gated) | thematic | **+25% rel** recall/precision | enable for thematic intent |
| topic-route | local | +0.101 R@20 but 42% mis-route, high variance | toggle only |
| entity-BM25 (`fusion`) | local | +0.045 (marginal, lossy surrogate) | toggle only |
| MMR | local/thematic | net-negative (pushes clusters down) | cascade only |
| ColBERT late interaction | local | net-negative (−0.116; repairs MMR only) | cascade only |
| ontology synset/hypernym | all | lost 4× (retrieval, graph, community) | graph edges only |

**Routing rule:** lookup ("find the skill on X") → `hybrid`. Thematic ("what
approaches to X exist") → enable LANE C. `cascade` runs the full superset for
ablation / when downstream diversity+entailment reranking is explicitly wanted.

**Open lever (untested):** query→community-report retrieval (embed aggregated
community descriptions, match query→community directly) — GraphRAG's true global
search; most likely path to raise absolute thematic recall above the ~0.20 ceiling.

## Reproducibility

`ingest_skills.ensure_bm25_lane()` builds `content_tsv` + GIN + `content_len` +
`bm25_idf` at ingest (all derived from stored `document`; no re-embed). The
community lane rebuilds from `build_desc_checkpoint.py → build_graph_report.py`.
Everything on the retrieval path is deterministic and LLM-free.
