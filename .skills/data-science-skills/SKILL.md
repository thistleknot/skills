---
name: data-science-skills
description: >
  USE THIS to look up or ground any data-science or reinforcement-learning
  concept before implementing it — a searchable, curated knowledge base of 1,467
  enriched skills (regression, classification, clustering/dim-reduction, trees &
  ensembles, model-eval, optimization, neural nets, probability & stats, data-prep,
  RL, and more) distilled from 9 textbooks (ISL, Sutton & Barto, Deep RL in Action,
  ML Algorithms, Statistics for ML, Applied Regression Modeling, Data Mining for
  Business Analytics, Basic Statistics, Advanced ML with Python). It is the CONSUMER
  layer: it does not store the corpus or run retrieval itself — it routes a query
  through a query expander (local ollama: query + ToC + tags -> rephrased query)
  into the parallel-rrf-graph-rag-hybrid-cascade-mmr-late-retriever engine, which
  ingested the corpus into pgvector + neo4j and serves whole-skill retrieval over
  MCP. Trigger whenever you (or the user) are about to implement, explain, choose
  between, or debug a data-science / RL technique and want the corpus's grounded,
  cross-referenced treatment instead of reinventing it. Triggers on: "how do I
  implement X", "what technique for Y", "explain/compare A vs B", "search the data
  science skills", "look this up in the DS knowledge base", "ground this in the
  stackskills corpus", any DS/ML/RL concept lookup.
status: draft
last_validated: 2026-07-19
---

# data-science-skills — the knowledge-base lookup skill

**What it is:** the front door to a curated data-science / RL knowledge base. When
you're implementing or reasoning about any DS/ML/RL concept, search here first for
the corpus's grounded, cross-referenced treatment instead of deriving from scratch.

**What it is NOT:** the corpus, and not the retrieval engine. Those are separate:

```
data-science-skills   ── THIS skill: when + how to query (the consumer/usage layer)
  │  routes a query through
  ▼
[query expander]      ── local ollama call: user query + ToC + tags -> rephrased query
  │  hands the rephrased query to
  ▼
[[parallel-rrf-graph-rag-hybrid-cascade-mmr-late-retriever]]
                      ── the ENGINE: ingested the corpus -> pgvector + neo4j; serves
                         whole-skill retrieval (RRF -> MMR -> late-interaction / graph-RAG)
                         over FastMCP (tools: `retrieve`, `browse_toc`)
  │  which was built from
  ▼
skills_master/        ── the CORPUS (downstream data):
   C:\Users\user\Documents\wiki\data science\stackskills\skills_master\  (1,467 *.md)
```

## When to use

- About to **implement** a DS/ML/RL technique → pull the corpus's treatment first.
- Need to **choose between** approaches (e.g. ridge vs lasso, k-fold vs LOO) →
  retrieve the related cluster and compare.
- Want to **explain / ground** a concept with the corpus's cross-referenced version.
- Debugging a method and want the canonical description + adjacent skills.

Prefer this over reinventing: the corpus already merges 9 textbooks' treatments per
concept, with pseudo-code and cross-language examples.

## How to use (the flow)

1. **(Optional) Browse the ToC** — call the engine's `browse_toc` MCP tool to get
   every skill's topic + entity tags. Useful when the query is vague or you want to
   see the neighborhood before querying.
2. **Query expansion (local ollama, in between)** — take the user's raw query plus
   the ToC (topics/folders) and tags, and ask a local ollama model to **rephrase /
   expand** it into a retrieval-optimized query. Grounding the rephrase in the
   corpus's own ToC + tag vocabulary steers it toward terms that actually exist in
   the index → better lexical (BM25), dense, and graph-RAG matching. (Closed 11-topic
   vocab, so this is cheap: 1 call/query, no per-chunk LLM.)
3. **Retrieve** — pass the expanded query to the engine's `retrieve` tool. It runs
   the parallel lanes (dense ‖ tsvector-BM25 ‖ community/graph, RRF-fused) → MMR →
   late interaction, and returns **whole skills** (each with all chunks + ToC/entity
   tags). Pick the `RETRIEVAL_MODE` by intent: **`hybrid`** for a specific lookup
   (default, the measured 2× lever), **community/cascade** for thematic "what
   approaches to X exist" exploration.
4. **Implement from the returned skill(s)** — use their content (definitions,
   pseudo-code, examples, cross-refs) as the grounded basis.

## Query-expander contract

- **Zero-shot context (pre-generated, NOT re-derived at query time):**
  `skills_master\metadata.json` — the corpus ToC augmented with tags, topic-grouped
  (`{topics: {<topic>: {count, tags[], skills[]}}}`). Generated once at end of
  ingestion (`build_corpus_metadata.py`); the expander loads it as its zero-shot
  prompt. This is why expansion is cheap — no per-query ToC/tag derivation.
- **Input:** `{user_query}` + the loaded `metadata.json` (topics, per-topic tags,
  skill lists).
- **Model:** local ollama (default the repo's small tag, e.g. `qwen3.5-oc:4b`),
  thinking suppressed, 1 call per query.
- **Output:** a single rephrased query string biased toward corpus vocabulary.
- **Why:** the raw user query rarely uses the corpus's exact terms; grounding the
  rephrase in the ToC + tags maps symptom/goal phrasing onto retrievable concepts,
  lifting BM25 + graph-RAG recall. (Status: `metadata.json` is generated; the ollama
  expand-step is specified here and wired into the engine's `retrieve` path — see
  that skill to enable/tune.)

## Related

- [[parallel-rrf-graph-rag-hybrid-cascade-mmr-late-retriever]] — the ingestion +
  retrieval **engine** this skill calls (how the corpus is chunked, embedded,
  graph-built, fused, and served; the measured evidence for each lane/stage).
- Corpus source: `wiki\data science\stackskills\skills_master\` (upstream data; not
  part of either skill).
