---
name: gist-retriever
description: >
  Multi-layer GraphRAG retrieval protocol over a compact derived triplet space. Use when
  running or designing hybrid BM25+dense retrieval, RRF fusion, L2 neighborhood
  expansion, ColBERT reranking, and final candidate selection before syllogistic
  reasoning or answer synthesis.
status: active
last_validated: 2026-04-28
---

# GIST Retriever

## Retrieval Tier: L1 (Vector / Semantic)

This skill operates at **L1** in the three-tier knowledge retrieval cascade.

### Cascade routing

```
Query
  │
  ▼
L2 — wiki / skills markdown (try first: fast, no server needed)
  │   found? → return
  │   not found?
  ▼
L1 — agentic_kg_memory / gist-retriever (try next: BM25 + dense vector)
  │   found? → return
  │   not found?
  ▼
L0 — deep-research (last resort: live web fetch, multi-source corroboration)
       → upsert findings back to L1
       → promote to L2 if findings are stable, reusable patterns
```

### What "not found" means at each tier

- **L2 miss**: no matching skill, wiki page, or memory-bank entry with sufficient relevance
- **L1 miss**: BM25 + dense retrieval returns no candidates above threshold, or coverage is below `saturation_theta`
- **L0 triggered**: both above tiers exhausted — run `deep-research`, store results back to L1

### Promotion rules (L1 → L2)

Promote a memory entry from L1 to L2 when:
- the same claim appears across multiple episodes with consistent support
- the finding is a stable procedure, constraint, or protocol — not a one-off fact
- the information is reusable across sessions and projects



## Scope Boundary

This skill is the **retrieval implementation layer**.

It owns:
- BM25 seed retrieval
- dense/GIST seed retrieval
- RRF fusion
- L2 neighborhood expansion
- document reconstruction from chunks
- ColBERT late interaction
- final candidate selection policy
- local vector-store execution over the derived semantic triplet space

It does **not** own:
- ontology identity selection
- synset or hypernym canonicalization
- throughline scoring policy
- final answer writing

Those belong to `kg_ontology` and `agentic_kg_memory`.

## Core Thesis

For this skills repo, `gist-retriever` should assume the **semantic triplet space
is already derived and compact enough to fit in Chroma**.

So the important abstraction is the layered retrieval pattern, not a dependency on
PostgreSQL or pgvector.

Historical note: a `BaseGISTRetriever` may have existed on top of `PGVectorRetriever`,
but that is not the storage contract this skill should optimize for here.

The abstract part that remains useful is:

- layered seed retrieval
- dual expansion
- late interaction reranking
- subclass-specific reconstruction and final selection

## Retrieval Progression for Compiled Wikis

In an **LLM Wiki** style system, retrieval usually matures in stages instead of
starting with the heaviest stack on day one.

Recommended progression:

1. **Markdown/index-first lookup** for small-to-medium corpora
   - use a maintained `index.md` to find candidate pages quickly
   - follow explicit page links and metadata
   - use direct markdown search when the corpus is still human-navigable
2. **Local markdown search engine** when the wiki grows beyond comfortable manual navigation
   - a `qmd`-style local engine is a good fit here
   - hybrid BM25/vector search over markdown pages is acceptable as a lightweight access path
   - this is still page-oriented retrieval, not the full graph-memory contract
3. **Full hybrid retrieval pipeline** once the corpus or page layer is large enough to justify it
   - BM25 seeds
   - dense/GIST seeds
   - RRF fusion
   - L2 expansion
   - ColBERT reranking

This skill owns the **access path** into compiled pages and evidence bundles. It
does not own the page-maintenance loop itself.

The backend can vary:

- direct markdown lookup over canonical page files
- local markdown search over those same files
- a compiled index such as Postgres/pgvector built from the canonical page layer

The important rule is that the retrieval surface is **rebuildable from the maintained
knowledge artifacts**. Retrieval serves the compiled wiki; it is not the source of truth.

## Base Pipeline

Per query:

| Layer | What happens |
| --- | --- |
| 1 | BM25 lexical retrieval -> `k^2 = 169` chunks |
| 2 | GIST dense / semantic retrieval from the Chroma triplet space -> `169` chunks |
| 3 | RRF fusion of BM25 + GIST -> top `144` hybrid seeds (Fibonacci cascade below `169`) |
| 4 | L2 expansion from seeds: BM25 triplet expansion + dense centroid expansion, RRF-merged |
| 5 | RRF fusion of hybrid seeds + L2 expansion -> combined pool |
| 6 | Document reconstruction (subclass) -> chunks become sections, quotes, or other full units |
| 7 | ColBERT late interaction over all reconstructed docs |
| 8 | Final selection (subclass) -> iterate until the required unique result set is satisfied |

## Key Design Choices

- use a **`k^2` retrieval pool** first, then shrink with a Fibonacci-style cascade
- use **RRF** at merge points instead of score averaging
- use **dual L2 expansion**:
  - BM25 over extracted triplets
  - dense centroid expansion from seed embeddings
- let **ColBERT** score the reconstructed candidates rather than only raw chunks

This creates graph-like neighborhood expansion without requiring a separate graph DB
or heavyweight vector backend for the retrieval stage.

## Cluster Routing Extension

If cluster routing is available, do **not** let it hard-gate the pipeline.

Recommended pattern:

1. run the normal global seed stage first
2. inspect cluster distribution across the top global seeds
3. allocate cluster budgets from that softened distribution
4. apply MMR or other diversity control within each cluster slice
5. keep a small global backstop outside the cluster-filtered pool

Clusters should bias retrieval, not imprison it.

For quote embeddings, do **not** assume that global external clustering should be
the winner metric. If it does not improve the real retrieval eval target, keep it
as a routing diagnostic or post-retrieval summarization aid instead.

Tune the retrieval architecture first:

1. broad-pool size
2. GIST utility vs diversity weight
3. graph path weight / hop budget
4. local community threshold or expansion budget inside layer 2
5. entity-overlap bonus
6. whether local grouping is enabled at all

The weak point in this stance is that local grouping can still help summarize the
retrieved neighborhood after the main candidate pool is already found.

## Relationship to KG Memory

This skill is a retrieval engine that feeds higher-level reasoning.

Typical chain:

`gist-retriever -> candidate pool -> syllogism / judge -> throughline update -> final answer`

In the broader memory stack:

- `gist-retriever` finds candidate evidence
- `kg_ontology` ensures canonical ids are used
- `agentic_kg_memory` updates pages, throughlines, and final evidence-backed conclusions

In LLM Wiki terms:

- `agentic_kg_memory` maintains the compiled wiki/page layer
- `gist-retriever` is the retrieval path into that maintained layer
- lightweight markdown/index-first lookup is the shallow end of the same retrieval job

The default dense store for this skill is:

- ordered `[SEP]` triplet sequences
- embedded once into a compact Chroma collection
- retrieved locally without assuming pgvector

## Subclass Responsibilities

`BaseGISTRetriever` is abstract because two layers depend on the data shape:

### Layer 6: reconstruction

Subclasses decide how chunks become reconstructed documents:

- arXiv sections
- quotes
- passages
- pages

### Layer 8: final selection

Subclasses decide how to pick the final set:

- stop after `K` unique papers
- stop after `K` unique quotes
- stop after enough coverage or diversity

## Storage Contract

The expected local storage split is:

- SQLite for metadata, lexical fields, page ids, and triplet provenance
- Chroma for the dense triplet-sequence embeddings

This is enough because the semantic triplet space is already a strong compression
of the source corpus.

### Atomic list elements — no chunking

**This framework does not chunk.** All stored knowledge lives as atomic-sized list
elements: individual triplets, single premises, one-sentence facts. The pipeline
table above uses the word "chunks" to mean *retrieval candidates* (individual records
returned by BM25/dense search), not split fragments of a larger document.

- Each list element is already at the minimum meaningful unit of information.
- Reconstruction (Layer 6) assembles elements into logical units for the reader,
  not the retriever.
- Never split an atomic element to fit a context budget; evict instead.

## Fallback Behavior

If Chroma is temporarily unavailable:

- fall back to standalone cosine search
- preserve the same higher-level pipeline shape where possible
- surface clearly that the system is running in degraded retrieval mode

The fallback is for continuity, not parity.

## Output Contract

When applying this skill, report:

- the size of the BM25 seed pool
- the size of the dense seed pool
- the RRF merge points
- the L2 expansion method used
- the reconstruction unit
- whether ColBERT reranking ran
- the final selection rule
- whether retrieval used the markdown/index-first path, a local markdown search layer, or the full hybrid pipeline
- whether retrieval is using Chroma or degraded cosine fallback

## Anti-Patterns

Avoid:

- averaging incompatible score scales instead of using RRF
- hard restricting retrieval to one cluster
- reconstructing documents too early before expansion completes
- treating chunk scores as final answer evidence without reconstruction
- silently hiding dense-store failure behind a low-quality fallback
<!-- consolidation:see-also:start -->
## See Also
[[agentic_kg_memory]]  [[kg_ontology]]  [[hyper-parm_tuning]]
<!-- consolidation:see-also:end -->
