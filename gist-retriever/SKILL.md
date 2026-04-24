---
name: gist-retriever
description: >
  Multi-layer GraphRAG retrieval protocol over a compact derived triplet space. Use when
  running or designing hybrid BM25+dense retrieval, RRF fusion, L2 neighborhood
  expansion, ColBERT reranking, and final candidate selection before syllogistic
  reasoning or answer synthesis.
---

# GIST Retriever

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

## Relationship to KG Memory

This skill is a retrieval engine that feeds higher-level reasoning.

Typical chain:

`gist-retriever -> candidate pool -> syllogism / judge -> throughline update -> final answer`

In the broader memory stack:

- `gist-retriever` finds candidate evidence
- `kg_ontology` ensures canonical ids are used
- `agentic_kg_memory` updates pages, throughlines, and final evidence-backed conclusions

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
- whether retrieval is using Chroma or degraded cosine fallback

## Anti-Patterns

Avoid:

- averaging incompatible score scales instead of using RRF
- hard restricting retrieval to one cluster
- reconstructing documents too early before expansion completes
- treating chunk scores as final answer evidence without reconstruction
- silently hiding dense-store failure behind a low-quality fallback
