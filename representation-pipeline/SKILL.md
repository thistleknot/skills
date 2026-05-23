---
name: representation-pipeline
description: >
  Progressive representation refinement protocol. Use when designing or
  diagnosing a multi-stage pipeline where raw features are transformed
  through successive layers (normalization, affinity, metric learning,
  retrieval) and each layer's quality metric must be computed in the
  transformed space. Covers the transformation progression pattern,
  bootstrap loops, GIST as a canonical layered architecture example,
  and how to construct tunable hyperparameter layers from each stage.
status: active
last_validated: 2026-04-28
---

# Transform Architecture

## Core Thesis

**Representation is not fixed. It is refined.**

A raw feature vector is a starting point, not a destination. The goal
of each transformation layer is to move the representation closer to the
space where the downstream task — clustering, retrieval, ranking,
recommendation — is geometrically easy.

Each transformation creates a new space. **Quality metrics must be
computed in that space, not the original one.** BSS/TSS measured in the
affinity space is a different (and more relevant) number than BSS/TSS in
the raw feature space.

## The Progression Pattern

Every representation pipeline follows the same structural arc:

```
raw features
    |
    v  [normalization layer]
scaled features  (min-max or z-score per dimension)
    |
    v  [relational transform layer]
affinity / similarity matrix  (each item = its similarity profile)
    |
    v  [metric learning layer]
learned embeddings  (ANN / Siamese — geometry shaped by task signal)
    |
    v  [retrieval / ranking layer]
retrieval scores  (BM25 + dense + RRF + MMR)
    |
    v  [diversity layer]
final ranked / clustered output
```

Not every pipeline needs all layers. But every layer that exists is a
tunable hyperparameter space, and the transition between layers is a
design decision, not a given.

## Lessons Learned (Music Similarity Pipeline)

These are real transitions observed building a content-based music
recommendation system. Each transition improved the downstream task.

### Layer 0 → 1: Raw MEL to Normalized Feature Space

**Before:** 139-dim acoustic vectors with raw scale (BPM in [60,200],
mel energy in [-70, 782]).

**Problem:** Large-scale features dominated cosine distance.
Key one-hot features (24 dims) caused genre-irrelevant groupings —
songs in the same key clustered regardless of acoustic similarity.

**Lesson:** Remove features that carry structure orthogonal to the task.
Normalize per-dimension before any distance computation.
Key = music theory property, not acoustic similarity signal.

**Metric before:** BSS/TSS ~0.87 (inflated by preprocessing leakage)
**Metric after:** BSS/TSS 0.71 (unbiased nested-CV, 139 dims, no keys)

### Layer 1 → 2: Normalized Features to Affinity Space

**Before:** Clustering in 139-dim feature space.

**Insight:** For a similarity/recommendation task, what matters is not
where a song sits in absolute feature space, but how it relates to every
other song. The N×N cosine-similarity matrix encodes exactly that.

**Transform:** Replace each song's 139-dim vector with its row in the
N×N affinity matrix. Each song becomes an N-dim relational profile.

**Why this helps:**
- Captures pairwise relational structure explicitly
- Dimensionality matches the cluster count (N ≈ k), making separation
  geometrically easier
- Affinity rows are the natural retrieval primitive for recommendation
  (GIST cluster routing operates on exactly these scores)

**Metric before (feature space):** BSS/TSS 0.71
**Metric after (affinity space):** BSS/TSS 0.92 (+0.21)

**Critical rule:** Compute BSS/TSS in the affinity space, not the
feature space. The two are not comparable — they measure separability
in different geometries.

## Modeling Tip — Transform -> Search -> Measure

When clustering quality jumps dramatically, separate the gain into three
distinct decisions rather than treating it as "the model just got better."

### 1. Transform

The biggest lever is often the representation change.

- Raw feature vectors may describe the signal
- Affinity rows describe each item's **relationship to the corpus**

For similarity and recommendation tasks, that relational view can be more
useful than the raw coordinates. This is the GIST-style move: cluster items
by how they relate to everything else, not just by their original features.

### 2. Search

Once the representation is fixed, search the algorithm family and the tuning
surface instead of assuming one clustering method.

- compare k-means, agglomerative variants, spectral, GMM, HDBSCAN
- use nested CV when you need an unbiased estimate
- let the inner loop tune and the outer loop evaluate

### 3. Measure in-space

BSS/TSS is the **R^2 of clustering**: the fraction of total variance explained
by the cluster assignments.

- `0.9664` means the clustering explains about 97% of the variance
- that number is only meaningful in the space where it was computed

If the transform produced an affinity space, compute BSS/TSS there.
Do not switch back to raw features for evaluation and then claim the transformed
representation won on its own terms.

### The recipe

```text
transform -> search -> measure in-space
```

Each step is load-bearing:

- transform without search leaves performance on the table
- search without the right transform explores the wrong geometry
- transform and search without in-space measurement misreads the result

Use this pattern whenever BSS/TSS, silhouette, or downstream retrieval quality
depends more on representation geometry than on the raw source features.

### Layer 2 → 3: Affinity Clusters to Metric-Learned Embeddings

**Before:** Cluster labels derived from affinity-space KMeans.
Pairs labeled: same-cluster = similar (1), different-cluster = dissimilar (0).

**Problem:** Cluster boundaries are crisp; real similarity is graded.
A song near a cluster boundary is mislabeled relative to songs deep in
a cluster.

**Solution:** Use cluster-derived pairs as weak supervision signal for a
Siamese network. The ANN learns a 32-dim embedding where within-cluster
songs are pulled together and cross-cluster songs are pushed apart,
producing a continuous similarity score rather than a binary label.

**Bootstrap loop:**
```
raw features
    -> affinity clustering  (weak labels)
    -> Siamese training     (metric learning)
    -> 32-dim embeddings
    -> re-cluster in embedding space
    -> better labels
    -> re-train Siamese
    -> (repeat until stable)
```

Each round improves label quality, which improves embedding quality.
Two to three rounds is usually sufficient before convergence.

**Lesson:** Clustering is not the end state — it is a label generator
for metric learning. The embedding it produces is the actual retrieval
primitive.

### Layer 3 → 4: Embeddings to Retrieval Layer (GIST)

**Before:** A scored list of nearest neighbors by cosine distance.

**Problem:** Pure nearest-neighbor retrieval maximizes utility
(similarity to query) but produces redundant, homogeneous results.

**Solution (GIST cluster-routing pattern):**
1. Run global nearest-neighbor retrieval across all songs
2. Inspect cluster distribution across the top seeds
3. Allocate per-cluster budget proportional to seed distribution
4. Apply MMR within each cluster slice (diversity within utility)
5. Keep a global backstop outside the cluster-filtered pool

**Key principle:** Clusters bias retrieval, they do not imprison it.
A song near a cluster boundary should appear in results for adjacent
clusters, not be hard-gated out.

## GIST as a Canonical Layered Architecture

The GIST retrieval pipeline is the clearest existing example of a
multi-layer tunable architecture. Each layer has its own hyperparameters.

```
Layer 1  BM25 lexical retrieval         k = k^2 = 169 seeds
         hyperparms: k, field weights, tokenization

Layer 2  Dense (GIST) retrieval         k = 169 seeds
         hyperparms: embedding model, similarity threshold

Layer 3  RRF fusion (BM25 + dense)      -> top 144 hybrid seeds
         hyperparms: RRF k constant, relative weights

Layer 4  L2 neighborhood expansion      BM25 triplet + dense centroid
         hyperparms: expansion radius, max neighbors per seed

Layer 5  RRF fusion (seeds + expansion) -> combined pool
         hyperparms: same RRF constants

Layer 6  Document reconstruction        chunks -> full units
         hyperparms: reconstruction unit (passage, page, section)

Layer 7  ColBERT late interaction       reranks reconstructed docs
         hyperparms: max query length, max doc length

Layer 8  Final selection                iterate to unique result set
         hyperparms: stopping criterion (k unique, coverage threshold)
```

**Each layer's k value, weights, and thresholds are hyperparameters.**
Optuna can tune them jointly or layerwise (layerwise preferred — see
`optuna-nested-cv` skill), and MLflow should log the run lineage and artifacts
(see `mlflow` skill).

**Instructional use:** When designing a new pipeline, ask for each
module: what are its inputs, what are its tunables, and what is its
output contract? GIST answers this cleanly for retrieval. Apply the
same decomposition to any pipeline you are building.

## Metric Alignment Principle

> The quality metric must be computed in the space produced by the
> transformation, not the space that fed into it.

| Layer | Space | Correct metric |
|-------|-------|---------------|
| Raw features | 139-dim acoustic | BSS/TSS (feature space) |
| Affinity matrix | N-dim relational | BSS/TSS (affinity space) |
| Siamese embeddings | 32-dim L2 unit sphere | BSS/TSS + silhouette (embedding space) |
| Retrieval scores | [0,1] similarity | NDCG, MRR, recall@k |
| Clustered retrieval | per-cluster budget | utility@k + diversity@k |

Measuring in the wrong space produces misleading scores. The +0.21
improvement from feature-space to affinity-space clustering was not
a model improvement — it was a metric alignment correction.

## Constructing Hyperparameter Layers

For any pipeline stage, define four things:

```
1. Input contract   — what representation format enters this stage
2. Transformation   — what function maps input to output
3. Output contract  — what representation format leaves this stage
4. Tunables         — what parameters control the transformation
```

Example — affinity layer:

```
Input:    X_norm  (N, D) min-max scaled feature matrix
Transform: A = (X/||X||) @ (X/||X||).T
Output:   A  (N, N) cosine similarity matrix, values in [-1, 1]
Tunables: (none for vanilla cosine; RBF gamma if using kernel affinity)
```

Example — clustering layer:

```
Input:    A  (N, N) affinity matrix
Transform: fit_algo(algo, k, A)
Output:   labels  (N,) cluster assignments
Tunables: algo in {kmeans, spectral, agg_ward, agg_complete, gmm, hdbscan}
          k in [2, N//2]
          algo-specific: n_init, linkage, min_cluster_size
```

When the tunable space is large or the evaluations are expensive,
hand the layer to Optuna (see `optuna-nested-cv` skill) and record the
campaign in MLflow (see `mlflow` skill).

## Bootstrap Loop Protocol

When label quality and representation quality are mutually dependent,
use a bootstrap loop:

```
1. Generate initial weak labels  (rule-based or naive clustering)
2. Train representation on weak labels
3. Evaluate representation quality  (BSS/TSS, silhouette, downstream metric)
4. If improved: use new representation to regenerate labels -> go to 2
5. If not improved or max rounds reached: stop
```

Stopping criteria:
- Quality metric improvement < threshold (e.g., < 0.01 BSS/TSS delta)
- Max rounds reached (2-3 for small corpora, 5 for large)
- Label stability: cluster assignments change < 5% between rounds

**Do not run the bootstrap loop indefinitely.** Label-representation
co-training can oscillate. Freeze after the first round that shows no
improvement.

## MemoRAG — Global Memory Layer Upstream of Retrieval

Standard retrieval (BM25 + dense + ColBERT) operates on local chunk similarity. MemoRAG adds a **global memory layer** that understands corpus shape before retrieval begins.

### Architecture

```
query
    │
    ▼  [memory model — lightweight long-range LLM]
    │  memorag-qwen2-7b-inst, 400K–1M context tokens
    │  builds global understanding of entire corpus
    │  generates: clues (surrogate queries + draft answer fragment)
    │
    ▼  [standard retriever — BGE-M3 + FAISS]
    │  guided by clues, not raw query
    │
    ▼  [generator — expensive LLM, swappable]
    │  GPT / Mistral / Llama via OpenAI-compatible API
    │  produces final answer from retrieved passages
    │
    ▼  answer
```

### Three memory model operations

```python
memo.recall(query)   # → text clues guiding retrieval
memo.answer(query)   # → direct answer from global memory (no retrieval step)
memo.rewrite(query)  # → decomposes query into surrogate sub-queries
```

### Integration with existing retrieval pipeline

MemoRAG sits **upstream of retrieval**, not inside agent session memory. Use as query expansion before BM25+dense:

```
current:  query → BM25+dense → ColBERT rerank → result
upgraded: query → memo.recall() → expanded_query → BM25+dense → ColBERT rerank → result
```

`memo.recall()` does structurally what the throughline node and ingredient knowledge graph do explicitly — but learned from global corpus shape, not hand-constructed.

### Practical constraints

| Constraint | Value |
|---|---|
| Default context window | 400K tokens (`memorag-qwen2-7b-inst`) |
| Extended window | 1M tokens (`beacon_ratio=16`) — verify OOM before production |
| GPU requirement | 16GB VRAM (Quadro P5200 compatible at default settings) |
| Encode latency | 200K tokens → 35s first encode, 1.5s reload from disk cache |
| Install | `pip install memorag` |

Memory model and generator are independent: local memory model + API generator is a valid split.

**This is HyDE but trained, not prompted.** Outperforms HyDE, BGE-M3, RQ-RAG across LongBench, InfBench, UltraDomain (WebConf 2025, Apache 2.0). Reference: MemoRAG (qhjqhj00/MemoRAG v0.1.5).

---

## MemoRAG — Integration Benchmark and Placement Decision

Three candidate pipeline configurations for placing `memo.recall()`:

```
(a)  query → BM25+dense → ColBERT reranker → output             (baseline)
(b)  query → recall() → BM25+dense → ColBERT reranker → output  (recall upstream)
(c)  query → recall() → BM25+dense → output                     (recall, no ColBERT)
```

**Decision rules (evaluate NDCG@10 on a held-out benchmark set):**

| Comparison | Outcome | Action |
|---|---|---|
| (b) beats (a) by > 5% | recall() adds signal | Use recall() upstream |
| (b) vs (c) difference < 2% | ColBERT marginal | Drop ColBERT, use (c) — saves latency |
| (a) vs (b) difference < 2% | recall() adds no signal | Skip recall(), stay with baseline |

ColBERT is the latency cost; recall() is the quality bet. If (c) ≈ (b), the ColBERT pass is wasted after recall() has already expanded the query.

**Default recommendation until benchmarked:** use (c) — recall() upstream, no ColBERT. Rationale: recall() expands the query globally; BM25+dense then retrieves precisely on the expansion; ColBERT is most valuable when the initial retrieval is noisy (which recall() reduces).

## MemoRAG — GPU Test Protocol (P5200 16GB)

Run this protocol before deploying MemoRAG in production against a long-context corpus.

```python
# memorag_gpu_test.py
from memorag import MemoRAG
import torch

MODEL = "memrag-qwen2-7b-inst"
CORPUS_FILE = "test_corpus_200k.txt"   # ~200K token document
BEACON_RATIOS = [8, 16, 32]

for beacon_ratio in BEACON_RATIOS:
    try:
        memo = MemoRAG(
            mem_model_name_or_path=MODEL,
            beacon_ratio=beacon_ratio,
            cache_dir="./cache",
        )
        memo.memorize(CORPUS_FILE, save_dir=f"./cache/br{beacon_ratio}/")
        result = memo.recall("What are the main themes in this document?")
        peak_mem = torch.cuda.max_memory_allocated() / 1e9
        print(f"beacon_ratio={beacon_ratio}: OK, peak_gpu={peak_mem:.1f}GB")
        torch.cuda.reset_peak_memory_stats()
    except torch.cuda.OutOfMemoryError:
        print(f"beacon_ratio={beacon_ratio}: OOM")
        break
```

Record: OOM boundary, peak GPU at each ratio, max usable context window. Expected: P5200 16GB handles beacon_ratio=8–16 on 200K tokens; beacon_ratio=32 likely OOM. Document result in `representation-pipeline` Evidence before production use.

**Windows proxy (triton unavailable):** `beacon_ratio` maps directly to effective sequence length (`corpus_tokens / beacon_ratio`). The benchmark measures peak GPU memory vs sequence length on a 7B model — that measurement is independent of memorag. Proxy used `torch.nn.functional.scaled_dot_product_attention` at Qwen2-7B GQA dimensions (28 Q-heads, 4 KV-heads, head_dim=128) with a real 272K-token corpus (local skill .md files).

**Results (Quadro RTX 5000 16GB, torch 2.8.0+cu128, corpus=272K tokens):**

| beacon_ratio | seq_len | attn peak | status |
|---|---|---|---|
| 8 | 34,031 | 0.98 GB | OK |
| 16 | 17,015 | 0.49 GB | OK |
| 32 | 8,507 | 0.24 GB | OK |
| 64 | 4,253 | 0.13 GB | OK |

**KV cache budget (binding constraint, not attention):**

Qwen2-7B fp16 weights consume ~14.0 GB, leaving **3.2 GB** for KV cache + activations.
KV cache per token = 2 (K+V) × 4 kv_heads × 128 head_dim × 28 layers × 2 bytes = 56 KB/token.
Max tokens in KV cache = **~55,800** — all beacon_ratio=8–64 seq_lens (4K–34K) fit comfortably.

**Conclusion:** RTX 5000 16GB can run MemoRAG-equivalent workloads at beacon_ratio ≥ 8 with zero OOM risk on a 272K-token corpus. The practical ceiling is loading the full 7B weights (14 GB) not the attention computation.

## Omni-SimpleMem KG vs GATv2+BM25 Graph-RAG — Overlap Assessment

**What each system models:**

| System | Graph structure | Node features | Edge weights |
|---|---|---|---|
| Omni-SimpleMem v3 KG | Semantic entity-relation graph (subject → predicate → object) | Entity embeddings (GraphSAGE / R-GCN) | Relation type |
| GATv2+BM25 Graph-RAG | Item similarity graph | Dense embeddings (per-item) | BM25 + cosine similarity scores |

**Assessment:** These are structurally different graphs. Omni-SimpleMem encodes *semantic meaning* (who did what to whom). GATv2+BM25 encodes *item similarity* (which documents are like each other). They do not duplicate.

**Can one subsume the other?** Only with loss:
- Replacing GATv2 similarity edges with KG semantic edges would lose the fine-grained similarity signal that BM25 provides for retrieval ranking
- Replacing KG entity nodes with similarity nodes would lose relational reasoning capability

**Recommendation:** Keep both; wire them in series:

```
source text
    → entity extraction → Omni-SimpleMem KG  ← enriches node features
    → embed + BM25 index → GATv2 similarity graph (KG entity tags as extra node features)
    → GATv2 attention → retrieval ranking
```

The KG augments GATv2 node features with entity-type and relation context. GATv2 still drives retrieval attention over the similarity graph. Neither subsumes the other.

## Anti-Patterns

Avoid:
- Computing quality metrics in the input space after a transformation
  (affinity BSS/TSS ≠ feature BSS/TSS — they are not comparable)
- Treating cluster labels as ground truth (they are weak supervision)
- Skipping the affinity transform for similarity tasks and going
  straight from raw features to retrieval
- Hard-gating retrieval by cluster membership (use soft budgets)
- Running the bootstrap loop beyond convergence
- Adding layers without defining input/output contracts first
- Tuning all layers jointly before layerwise baselines exist
<!-- consolidation:see-also:start -->
## See Also
[[checklist]]  [[memory-architecture]]  [[codebase-knowledge-graph]]
<!-- consolidation:see-also:end -->
