# Retrieval — measured design

> **MEASURED CONCLUSION (2026-07-19, supersedes the cascade design below).**
> Two evals settled the retrieval path empirically:
> - **Topical-cluster relevance** (LLM-judged, the stated goal — "ask about
>   regression, also surface cross-validation"): **dense-only wins at every
>   cutoff.** nDCG@10 — dense 0.856 > dense⊕entity-BM25 0.789 > dense⊕ontology-
>   graph 0.734; R@30 — 0.687 / 0.627 / 0.613. The BM25 and graph legs DILUTE
>   topical recall (they inject lexically/structurally-adjacent-but-topically-
>   weaker skills into the top ranks).
> - **Exact-skill lookup** (self-retrieval): dense⊕entity-BM25 wins (+0.155
>   nDCG@10). Different objective, different retriever.
>
> Production default is therefore `RETRIEVAL_MODE="dense"` (cosine only ->
> whole-skill). `"fusion"` = dense⊕entity-BM25 RRF (exact-lookup toggle).
> `"cascade"` = the full graph/MMR/ColBERT path below — **measured net-negative
> for both objectives, retained diagnostic-only**. ColBERT reranking dropped the
> fused score (-0.116); n-hop ontology traversal never beat 1-hop BM25 (hops
> 1/2/3 identical — distant shared ancestors are noise); the entity CO_OCCURS
> graph added ~nothing. The cascade text below documents that diagnostic path.

## Cascade (diagnostic-only) — full detail

Entry point: `retrieve(query, k=...)` in `scripts/mcp_server.py`, exposed as
an MCP tool. The cascade (RETRIEVAL_MODE="cascade") merges two existing designs:
`arxiv_rag_manifold_revised.py`'s PGVector/MMR/ColBERT wiring is the base;
`gist-retriever`'s L2-neighborhood-expansion stage is grafted in between the RRF
fuse and the MMR rerank, with the neo4j entity graph substituting for its
BM25-triplet expansion. Kept for ablation; not the production path.

**There is NO BM25 leg.** "Entities as BM25 surrogates" means the entity/graph
metadata plays the parallel-to-cosine role a BM25 leg would — it is NOT a
literal BM25 sparse column (no such column exists; see `references/ingestion.md`
section 4). The graph-density signal from neo4j is the second signal fused with
cosine.

## GRAPH_MODE switch

A `GRAPH_MODE` constant controls how the graph participates:
- `parallel` — graph-density is the 2nd RRF leg fused with cosine (Stage 1).
- `cascade` — cosine seeds first, then graph-neighborhood expansion (Stage 2).
- `both` (default) — graph-density fuses in the RRF AND expands the pool.

The eval harness (`scripts/eval_retrieval.py --sweep`) settles which mode wins
empirically on skill-level nDCG@10 — see the Eval harness section below.

## Stage 1a — cosine seed retrieval

Embed the query with `nomic-embed-text` (langchain `OllamaEmbeddings` /
`search_query: ` prefix). Similarity search over the `data_science_skills`
PGVector collection for the top `COSINE_K` candidates (default 100 — large
enough that RRF/graph/MMR/ColBERT have real material to work with, per the same
"retrieve wide, narrow in stages" logic `gist-retriever` documents).

## Stage 1b — graph-density signal (neo4j)

The second RRF leg (when `GRAPH_MODE` is `parallel` or `both`) is the
graph-density score from neo4j (`dss-neo4j`): for each candidate chunk, the
weighted connectivity of its entities in the `CO_OCCURS` graph. This is the
"entities as BM25 surrogates" signal — structural connectivity standing in for
the lexical-match leg. No BM25 tokenization, no sparse vectors, no query->synset
resolution.

## Stage 1c — RRF fusion (the "1 parallel" step)

Reciprocal rank fusion of the cosine ranking (1a) and the graph-density ranking
(1b), over their **union** (a chunk found by only one leg still enters at the
other leg's worst-case rank rather than being dropped):

```
rrf_score(chunk) = GRAPH_RRF_WEIGHT       / (RRF_K + graph_rank(chunk))
                  + (1 - GRAPH_RRF_WEIGHT) / (RRF_K + cosine_rank(chunk))
```

`RRF_K` default 60 (the standard RRF constant). `GRAPH_RRF_WEIGHT` default
`0.5` (equal weight) — tunable; the eval harness sweep exercises the
graph-vs-cosine balance across GRAPH_MODE configs. Take the top `RRF_K_OUT`
(default 50) by fused score.

## Stage 2 — graph-neighborhood expansion (1st cascaded filter)

Active when `GRAPH_MODE` is `cascade` or `both`. For each of the `RRF_K_OUT`
fused seeds, walk the neo4j `CO_OCCURS` graph outward from that chunk's entities
by `EXPANSION_HOPS` (default 1 hop) to find chunks connected via shared or
edge-connected canonical entities (via `HAS_ENTITY`). Add any newly-discovered
chunk to the candidate pool with a discounted score (`EXPANSION_DISCOUNT`,
default `0.5×` the score of the seed it was expanded from — an expanded chunk
should rank behind a directly-fused one, all else equal). This mirrors
`gist-retriever`'s L2 expansion stage but substitutes the explicit neo4j entity
graph for its BM25-triplet expansion. Cap the expanded pool at `EXPANDED_K`
(default 80) — drop lowest discounted-score chunks first if the walk
over-produces.

## Stage 3 — MMR rerank (2nd cascaded filter)

Port `arxiv_rag_manifold_revised.py`'s `mmr_from_scores` pattern: build a
score matrix over the expanded pool (columns = [cosine similarity,
graph-density, RRF-fused score] at minimum — more dimensions can be added
later without changing the MMR mechanics; note there is no BM25 dimension —
graph-density replaces it), compute relevance as the row sum,
compute diversity as pairwise cosine similarity between score vectors
(not between raw embeddings — this is the existing script's actual
mechanism, not a hypothetical), and greedily select `MMR_K` (default 30)
chunks balancing `MMR_LAMBDA` (default 0.7, matching the existing script's
default) relevance against diversity.

## Stage 4 — ColBERT v2 rerank (3rd cascaded filter, final)

Port `arxiv_rag_manifold_revised.py`'s `calculate_colbert_scores` pattern:
`colbert-ir/colbertv2.0` via `transformers.AutoModel` (not the standalone
`colbert-ai` package — the existing script deliberately uses the raw
transformers path so it doesn't need ColBERT's own indexing infrastructure),
MaxSim scoring (per-query-token max similarity against document tokens,
summed), scores normalized to `[0, 1]`. Take the top `MMR_K`->ColBERT-ranked
chunks — these are the input to the whole-skill vote below.

## Stage 5 — whole-skill return (the retrieval unit)

**The retrieval unit is a whole skill, not a chunk.** The ColBERT-ranked chunks
**vote for their skill** (a chunk contributes its rank/score to its
`skill_slug`); the top `TOP_SKILLS` (default 5) skills are returned **WHOLE** —
all their chunks, ordered by `chunk_index` — with the skill's frontmatter and
its neo4j-derived `tags`. Recall and precision are measured at the **skill
level**, not the chunk level (see the eval harness). This is why a chunk-level
top-k isn't the final output: the MCP client gets complete skills, not
fragments.

## Config constants (`mcp_server.py`)

`GRAPH_MODE`, `COSINE_K=100`, `GRAPH_RRF_WEIGHT=0.5`, `RRF_K=60`,
`RRF_K_OUT=50`, `EXPANSION_HOPS=1`, `EXPANSION_DISCOUNT=0.5`, `EXPANDED_K=80`,
`MMR_LAMBDA=0.7`, `MMR_K=30`, `TOP_SKILLS=5`.

## Reconciling "1 parallel RRF, to 3 cascaded filters"

RRF (Stage 1c) is the one parallel-fusion step — it combines two independent
rankings computed in parallel (cosine, graph-density). Graph expansion
(Stage 2), MMR (Stage 3), and ColBERT (Stage 4) are the three cascaded filters
that run in sequence afterward; whole-skill voting (Stage 5) is the final
aggregation into the retrieval unit.

## Eval harness — how the mode is settled

`scripts/eval_retrieval.py` measures **skill-level** recall@k / precision@k /
MRR / nDCG@k. Golden queries are LLM-paraphrased to avoid the skill's own
wording, then filtered twice: overlap-filtered (Jaccard < 0.6 vs the skill
description, so a query can't just echo it) and retention-filtered (the target
skill must appear in the top-K, so unanswerable queries are dropped). Golden
queries are cached in `eval_golden.sqlite`.

CLI:
- `--gen N` — generate N golden queries.
- `--sweep` — measure and compare the GRAPH_MODE configs
  (`cosine_only` / `graph_parallel` / `graph_cascade` / `both`).
- `--config X` — measure a single config.

The winner is chosen by **nDCG@10** — this is the "best hierarchical fit given
our options" answer, decided by measurement rather than by guessing which
GRAPH_MODE is right.

## Attaching tags to results

Each returned skill carries its neo4j `Skill.tags` (top-N canonical entities,
see `references/ingestion.md` section 6) plus its frontmatter (name/topic) —
this lets an MCP client browse "what else is tagged the same way" without a
second query.

## Fallback behavior

If PGVector, neo4j, or Ollama is unreachable, `retrieve()` should raise rather than
degrade silently — this corpus is small enough (1,467 files) that a
degraded-mode fallback isn't worth the complexity `gist-retriever` accepts
for its much larger/looser corpus target. Surface the failure to the MCP
client; do not return a low-quality result set disguised as a real one
(per `gist-retriever`'s Anti-Patterns: "silently hiding dense-store failure
behind a low-quality fallback").
