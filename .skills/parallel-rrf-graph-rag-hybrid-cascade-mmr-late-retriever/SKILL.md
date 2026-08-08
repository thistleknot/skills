---
name: parallel-rrf-graph-rag-hybrid-cascade-mmr-late-retriever
description: >
  A retrieval-PROCESS skill: a parallel-lane RRF + graph-RAG hybrid cascade ->
  MMR -> late-interaction retriever for a markdown skill corpus, plus the
  ingestion pipeline that feeds it. INGESTION SOURCE (the upstream corpus this
  reads, not part of the skill): C:\Users\user\Documents\wiki\data science\stackskills\skills_master\
  (1,467 enriched markdown files; ingest_skills.py globs `*/*.md` from there).
  Windows-service deployment DELEGATES to the litellm-windows-service skill (NSSM
  procedure) — register-service.ps1 is just the concrete instance. Covers: Docling
  HybridChunker -> nomic-embed-text ->
  langchain PGVector (collection `data_science_skills`, chunks as Documents,
  KG/frontmatter data in `cmetadata` JSONB); a KG entity extractor that stores
  SPO triplets and spaCy named-entity types as chunk metadata and builds an
  entity graph in a dedicated neo4j container (`dss-neo4j`) used for GRAPH
  CONSTRUCTION only (NOT lexical retrieval); WordNet synsets/hypernyms kept as
  graph edges/enrichment only (a departure from kg_ontology); and a FastMCP
  retrieval service whose DEFAULT is HYBRID whole-skill retrieval
  (RETRIEVAL_MODE="hybrid" = dense ⊕ true-BM25 RRF) — the measured winner by 2x
  on deterministic bridging gold (vs dense: R@20 +0.202, nDCG@20 +0.151, MRR
  +0.166, wins every cutoff). The BM25 lane is TRUE BM25 computed IN-DB over the
  native `content_tsv` tsvector column (full snowball-stemmed content, real tf via
  unnest positions, IDF from ts_stat in the materialized `bm25_idf` table, k1=1.5,
  b=0 — length norm measured to HURT even at dl CV=0.65, since chunks vote for
  their whole skill). No pg_bestmatch (unavailable) and no hand-rolled entity-BM25
  (the old enrich_tokens lane was a lossy surrogate, decisively beaten). The FULL
  feature set is retained and configurable (see references/retrieval.md — the
  canonical spec): an async aggregated retriever (parallel lanes: dense || tsvector-
  BM25 || community || topic-route, with asyncio.gather barrier + per-lane stall
  guard) feeding RRF -> MMR -> ColBERT late-interaction, whole-skill return. The
  COMMUNITY lane is the thematic/GraphRAG-analogue: Leiden communities (graspologic)
  over the skill graph + within-community subgraph-DWPC (hub-corrected, vectorized),
  gated by density/conductance — +25% rel recall/precision on thematic queries
  (built by build_desc_checkpoint.py -> build_graph_report.py, reusing the
  consolidation skill's graph-metrics toolkit). RETRIEVAL_MODE selects the config:
  "hybrid" (default, local lookup), "dense" (floor), "route"/"fusion" (toggles),
  "cascade" (full dense⊕bm25⊕community -> RRF -> MMR -> ColBERT). Measured guidance:
  lookup->hybrid, thematic->enable community lane; MMR/ColBERT/ontology retained for
  ablation (measured net-negative for local). Registered as a Windows service via
  NSSM. Use this skill whenever the user
  wants to ingest the stackskills corpus, rebuild its pgvector collection,
  query it via MCP, debug the data-science-skills service, run the retrieval
  eval, or extend the ingestion/retrieval pipeline itself. Triggers on:
  "ingest the skills corpus", "query the data science skills service",
  "rebuild the skills_master pgvector collection", "data_science_skills MCP",
  "graph retrieval for the stackskills wiki", "register the skills retrieval
  service", or any question about how that corpus's KG/retrieval pipeline works.
status: draft
last_validated: 2026-07-19
---

# parallel-rrf-graph-rag-hybrid-cascade-mmr-late-retriever

A retrieval-**process** skill: parallel-lane RRF + graph-RAG hybrid → cascade →
MMR → late-interaction. Ingestion + graph-augmented hybrid retrieval, scoped to
one corpus: the 1,467
enriched markdown files in `skills_master/` produced by the stackskills
merge-and-enrich pipeline (see that folder's own build history for how the
corpus itself was assembled — this skill starts from the finished files).

> **Scope — this is a retrieval/ingestion PROCESS skill, not a corpus.** It
> READS the corpus from `C:\Users\user\Documents\wiki\data science\stackskills\skills_master\`
> and ingests it into pgvector/neo4j, then serves retrieval. It does **not**
> contain the corpus files, and it does **not** ship generated index state
> (`graph_report.json`, `*.db`, caches) — those are produced by the build scripts
> at deploy time against the live corpus (see `.gitignore`) and are regenerable,
> never committed. The skill is: the ingestion pipeline + the retrieval spec +
> the service registration. Nothing else.

This is a **specialized variant**, not a replacement, of two more general
skills already in this library:
- [[gist-retriever]] — the canonical RRF -> L2 expansion -> ColBERT cascade
  shape, but built for an atomic-triplet space on SQLite+Chroma. This skill
  ports that cascade shape onto langchain PGVector with real markdown chunks
  (not atomic triplets) as the retrieval unit, and swaps the BM25 leg for an
  entity-graph density signal.
- [[kg_ontology]] — the reference SPO-extraction skill. This skill **borrows
  its extraction shape but deliberately DEPARTS from its synset-canonical
  identity contract**: here the canonical entity id is the normalized surface
  span (`ridge_regression`, `gradient_descent`), NOT a WordNet synset. Rationale:
  WordNet mis-resolves ML terms ("ridge regression" -> "mountain ridge"), which
  would poison the graph; domain-correct entities are the whole point of the
  retrieval backbone. WordNet synsets/hypernyms are kept only as *enrichment
  tokens* for plain common words, never as identity. See
  `references/ingestion.md` for the exact contract.

Read [[litellm-windows-service]] before touching the Windows service
registration stage — its NSSM procedure and traps (elevation via `-File`,
UTF-8 env vars, port-hold verification) are reused directly.

## Source of truth

- **What folder is read**: `C:\Users\user\Documents\wiki\data science\stackskills\skills_master\*\*.md`
  — 11 topic subfolders, each file has `name/description/topic/sources/
  merged_slugs/enriched` frontmatter plus `## What it is / Key mechanics /
  Pseudocode / Code / Gotchas or pitfalls / When to use` sections.
- **Ingestion never writes back to `skills_master/`.** It is read-only input.
  Re-running ingestion after the corpus changes is how updates propagate —
  there is no separate "sync" step to remember.
- **pgvector target**: langchain `PGVector`, connection
  `postgresql+psycopg://langchain:langchain@localhost:5432/langchain`, collection
  `data_science_skills`. Chunks are stored as langchain `Document`s; all
  entity/SPO/synset/hypernym + frontmatter data lives in the `cmetadata` JSONB
  column. Embeddings via `OllamaEmbeddings(model="nomic-embed-text")`. There is
  NO custom `data_science_skills` table, `bm25_sparse` column, or `dss_*` table —
  PGVector owns its own schema. Do not touch other collections in that DB (e.g.
  the arxiv `paper_sections` / `paper_titles` / `paper_abstracts`).
- **entity graph target**: dedicated neo4j container `dss-neo4j` (bolt
  `localhost:7688`, browser `localhost:7475`, auth disabled), compose file
  `docker/neo4j-compose.yml`, started with
  `docker compose -f docker/neo4j-compose.yml up -d`. The graph lives here, NOT
  in postgres. Node model: `(Chunk {id, skill_slug})-[:HAS_ENTITY]->(Entity {id})`,
  `(Chunk)-[:OF_SKILL]->(Skill {slug, topic, tags})`, `(Entity)-[:IN_SKILL]->(Skill)`,
  `(Entity)-[:CO_OCCURS {weight}]-(Entity)`.

## Ingestion — quick reference

Full detail: [references/ingestion.md](references/ingestion.md). Script:
[scripts/ingest_skills.py](scripts/ingest_skills.py).

1. Frontmatter (name/description/topic/sources/merged_slugs) is regex-parsed
   once per file and stored in `cmetadata`; KG extraction runs on the
   frontmatter-stripped body so source book names + chunk-ref numbers don't
   become graph nodes.
2. Docling `HybridChunker` splits each `skills_master/*.md` body into chunks.
3. Each chunk is embedded with `nomic-embed-text` via
   `OllamaEmbeddings(model="nomic-embed-text")` and stored as a langchain
   `Document` in the `data_science_skills` PGVector collection.
4. KG extraction is a **single Stage-A LLM call** (S-P-O extraction) via Ollama
   `/api/chat` with Qwen3 thinking suppression (`/no_think` + top-level
   `think:false`), per [[ollama-structured]]. Canonical entity id = normalized
   surface span (ASCII-folded, lowercased, spaces->underscores) — this IS the
   graph node identity. WordNet synsets/hypernyms are looked up only as
   `enrich_tokens` for plain single common words, never as identity. There is
   NO per-triplet synset-selection LLM call (that stage was removed).
5. spaCy NER runs separately for named-entity types; noise labels
   (CARDINAL/ORDINAL/DATE/etc.) and numeric/book-name entities are filtered out.
6. Entity/SPO/synset/enrich data + spaCy entities are stored in the chunk's
   `cmetadata` JSONB. The entity graph is written to the `dss-neo4j` container
   (nodes/edges per the model above); `CO_OCCURS.weight` = co-occurrence count,
   and a chunk's graph-density score = sum of its entities' weighted degree.
7. Per skill file (and per topic), the most frequent canonical entities become
   **tags**, stored on the `Skill` node in neo4j.

## Retrieval — quick reference

Full detail: [references/retrieval.md](references/retrieval.md). Service:
[scripts/mcp_server.py](scripts/mcp_server.py).

There is **NO BM25 leg**. The entity graph IS the parallel-to-cosine signal
("entities as BM25 surrogates" means the entity/graph metadata plays that role,
not a literal BM25 column).

```
query
  │
  ▼
cosine seed (langchain PGVector, nomic dense)  ───┐
                                                   ├─► RRF (cosine rank ⊕ graph-density rank)
graph-density signal (neo4j `dss-neo4j`)  ────────┘
  │
  ▼
graph-neighborhood expansion (walk the neo4j co-occurrence graph from the
RRF-fused top hits, discounted by hop — pull in connected chunks)
  │
  ▼
MMR rerank (diversity)
  │
  ▼
ColBERT v2 late-interaction rerank (final filter)
  │
  ▼
whole-skill return: ranked chunks vote for their skill; top-K skills returned
WHOLE (all chunks, ordered by chunk_index) with frontmatter + neo4j tags
```

A `GRAPH_MODE` switch controls the graph's role: `parallel` (graph-density as
the 2nd RRF leg), `cascade` (cosine then graph-expand), `both` (default). The
eval harness (below) settles which is best empirically.

**Retrieval unit = whole skill.** Ranked chunks vote for their skill; the top-K
skills are returned whole. Recall/precision are measured at the skill level.

Config constants in `mcp_server.py`: `GRAPH_MODE`, `COSINE_K=100`,
`GRAPH_RRF_WEIGHT=0.5`, `RRF_K=60`, `RRF_K_OUT=50`, `EXPANSION_HOPS=1`,
`EXPANSION_DISCOUNT=0.5`, `EXPANDED_K=80`, `MMR_LAMBDA=0.7`, `MMR_K=30`,
`TOP_SKILLS=5`.

This merges two existing designs: `arxiv_rag_manifold_revised.py`'s
PGVector/MMR/ColBERT wiring is the base (its `mmr_from_scores` and
`calculate_colbert_scores` patterns are reused), with `gist-retriever`'s
L2-neighborhood-expansion stage grafted in — the neo4j entity graph
substituting for its BM25-triplet expansion.

## Eval harness — quick reference

`scripts/eval_retrieval.py` measures skill-level recall@k / precision@k / MRR /
nDCG@k. Golden queries are LLM-paraphrased (avoid the skill's own wording),
overlap-filtered (Jaccard < 0.6 vs description) and retention-filtered (target
must appear in top-K), cached in `eval_golden.sqlite`. `--gen N` generates,
`--sweep` compares GRAPH_MODE configs (`cosine_only` / `graph_parallel` /
`graph_cascade` / `both`), `--config X` measures one. Winner chosen by nDCG@10 —
this is the "best hierarchical fit given our options" answer. Full detail:
[references/retrieval.md](references/retrieval.md).

## Windows service registration — DELEGATED to [[litellm-windows-service]]

**The NSSM how-to lives in [[litellm-windows-service]], not here.** That skill owns
the procedure and traps (portable `nssm.exe`, `-File` elevation, autostart,
restart, the "Running before the port listens" verification loop). Read it before
touching or debugging the service.

This skill only supplies the **instance**:
- Process to wrap: `scripts/mcp_server.py` (the FastMCP retriever).
- Service name: `parallel-rrf-graph-rag-hybrid-cascade-mmr-late-retriever-mcp`.
- One skill-specific requirement: set `PYTHONIOENCODING=utf-8 PYTHONUTF8=1` (the
  cp1252 crash-trap that hits any Python service on this machine).
- Script: [scripts/register-service.ps1](scripts/register-service.ps1) (applies the
  litellm-windows-service pattern to the above; ingestion is a one-shot script, NOT
  a service — only the MCP server is registered).

```powershell
# elevated, one UAC prompt:
Start-Process powershell -Verb RunAs -ArgumentList '-NoProfile','-ExecutionPolicy','Bypass',`
  '-File','C:\Users\user\.claude\skills\parallel-rrf-graph-rag-hybrid-cascade-mmr-late-retriever\scripts\register-service.ps1'

# verify:
Get-Service parallel-rrf-graph-rag-hybrid-cascade-mmr-late-retriever-mcp
```

## Scope boundary (v1 vs stretch)

**v1 / must-have**: ingestion script (parse frontmatter -> chunk -> embed ->
extract KG metadata -> persist to PGVector + neo4j -> compute tags), the
retrieval cascade as a callable Python function, a FastMCP server exposing
whole-skill retrieval, the eval harness, NSSM registration.

**v2 / stretch, explicitly out of scope for the first build**:
- Cross-collection graph merging with other corpora ingested by this same
  pipeline pattern (e.g. arxiv papers) — this skill is scoped to
  `skills_master/` only.
- Incremental re-ingestion (today: re-running ingestion re-processes the
  whole corpus; a changed-files-only mode is future work).

## GRAPH_MODE — settled empirically, not by guess

The graph's role in retrieval (`parallel` / `cascade` / `both`) is a tunable,
not a fixed design choice. `scripts/eval_retrieval.py --sweep` compares all
configs on skill-level nDCG@10 and picks the winner — this is the "best
hierarchical fit given our options" answer. Default is `both`.

## Verification / status (2026-07-18)

Verified working end-to-end on a **2-skill slice**: both test queries retrieved
the correct skill as #1. The full **1,467-file ingest is a heavy batch job**
(one KG LLM call per chunk) — it needs the run-timeout removed and ideally a
free GPU; under docling GPU contention, 3 files took >9.5 min. Run
`python scripts/ingest_skills.py --reset` for the full corpus once a GPU is
free and the timeout lifted.
