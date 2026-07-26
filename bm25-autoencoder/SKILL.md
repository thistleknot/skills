---
name: multigran-sparse-retrieval
description: >
  Build a multi-granularity sparse retrieval system over a text corpus. Use
  when the task involves: paragraph-level balanced sampling with token-length
  and topic stratification, dual-hash (character n-gram + wordpiece) sparse
  representation with invertible lookup, BM25 correlation graph with Louvain/
  WCC community detection, sparse autoencoder bottleneck as unified retrieval
  metric, or phi-weighted EMA archetype embedding across temporal attestations.
  Trigger on any mention of BM25 sparse matrix, wordpiece hashing, paragraph
  sampling stratification, correlation-graph retrieval, or sparse autoencoder
  retrieval distance.
status: active
last_validated: 2026-05-25
validation_method: design review
---

# Multi-Granularity Sparse Retrieval

## Core Insight

Text has at least two natural granularities â€” character surface form and
tokenizer-derived units â€” that are collinear but not identical. The gap between
their sparse representations is structured signal, not noise. A retrieval system
that operates over both simultaneously, and learns their joint latent structure
via a sparse autoencoder, approximates what a dense embedding captures at a
fraction of the compute cost and with full invertibility at the input layer.

---

## Architecture

```
OFFLINE (index time)

  corpus paragraphs
      â†’ [Stage 1] balanced 2k sample
            token-length stats â†’ 95% PI prune â†’ bins
            topic counts
            joint projection â†’ stratified sample

      â†’ [Stage 2] dual-hash sparse representation
            character n-gram hash  â†’ sparse vector C
            wordpiece BM25 hash    â†’ sparse vector W
            concat [C â€– W]         â†’ input matrix X

      â†’ [Stage 3] sparse autoencoder
            encoder: X â†’ bottleneck Z (L1-penalized)
            decoder: Z â†’ XÌ‚ (reconstruction = inversion)
            train offline, freeze for retrieval

      â†’ [Stage 4] correlation graph
            BM25 score matrix (paragraph Ã— paragraph)
            â†’ Pearson/Spearman correlation
            â†’ threshold significant correlations â†’ edges
            â†’ Louvain community detection (soft assignment)
            â†’ WCC (hard connected components)
            â†’ DWPC path similarity (down-weights high-degree hubs)

      â†’ [Stage 5] composite retrieval index
            per paragraph: (Z, community_id, avg_bm25_score)
            stored in SQLite with inverted index for hash lookup

ONLINE (query time)

  query text
      â†’ dual-hash â†’ [C â€– W]
      â†’ encode â†’ Z_q
      â†’ ANN search over Z (bottleneck distance)
      â†’ filter/rerank by community overlap + avg BM25 prior
      â†’ return top-k paragraphs with inversion path
```

---

## Stage 1 â€” Balanced Sampling

**Goal:** produce a 2k paragraph sample representative across length and topic.

**Token length pruning:**
- Compute token length per paragraph (wordpiece tokenizer)
- Fit distribution, derive 95% prediction interval
- Drop paragraphs outside the interval (outliers distort bin boundaries)
- Bin survivors: use median + 1.4826Â·MAD as scale; derive bin edges from
  center Â± nÂ·scale. Prefer 5â€“8 bins. Label each paragraph with its bin.

**Topic counts:**
- Run LDA or NMF over the corpus (k=10â€“20 topics)
- Assign dominant topic per paragraph
- Cross-tabulate: bin Ã— topic â†’ stratum grid

**Sampling:**
- Target 2k total; allocate proportionally to stratum size
- If any stratum has < 5 paragraphs, merge with nearest neighbor stratum
- Output: 2k paragraphs with (bin, topic, token_len) metadata

**Validation gate:** stratum coverage â‰¥ 80% of non-empty cells. No stratum
contributes > 20% of the 2k sample.

---

## Stage 2 â€” Dual-Hash Sparse Representation

**Goal:** represent each paragraph as two sparse vectors in the same format,
both invertible via lookup over a closed vocabulary.

### Character n-gram hash

```
Require: paragraph text p, n-gram size n âˆˆ {2,3,4}, vocabulary V_c (prebuilt)
Guarantee: sparse vector C âˆˆ R^|V_c|, no collisions within V_c
Maintain: V_c is closed over the corpus â€” built offline, not extended at query time
```

- Extract all character n-grams from p
- Index each n-gram into V_c (perfect hash over known corpus n-gram set)
- Weight: TF of each n-gram within p
- Inversion: n-gram_id â†’ n-gram string via static reverse table V_c^{-1}
- Paragraph reconstruction: candidate set = paragraphs sharing n-gram ids
  (inverted index lookup, not exact decode â€” that's correct behavior)

### Wordpiece BM25 hash

```
Require: paragraph text p, wordpiece tokenizer T, BM25 corpus stats
Guarantee: sparse vector W âˆˆ R^|V_w|, entries = BM25 weight per token
Maintain: V_w = tokenizer vocabulary (closed, fixed)
```

- Tokenize p with T â†’ token ids
- Compute BM25 weight per token id against corpus
- Store as sparse dict {token_id: bm25_weight}
- Inversion: token_id â†’ token string via tokenizer decode (trivial, O(1))

### Concatenation

```python
X = scipy.sparse.hstack([C, W])  # shape: (n_paragraphs, |V_c| + |V_w|)
```

Same format, same dtype (float32), different index ranges. No ambiguity between
the two halves â€” split point is |V_c|.

**Validation gate:** zero hash collisions within each vocabulary. Verify by
asserting len(set(hash(ng) for ng in V_c)) == len(V_c) offline.

---

## Stage 3 â€” Sparse Autoencoder

**Goal:** learn joint latent Z that captures collinear structure between C and W.
Bottleneck Z is the unified retrieval coordinate. Decoder provides principled
inversion at the latent level.

```
Architecture:
  Encoder: X (sparse) â†’ dense hidden â†’ Z (bottleneck, L1 penalty)
  Decoder: Z â†’ dense hidden â†’ XÌ‚ (reconstruction)

Loss: MSE(X, XÌ‚) + Î» Â· â€–Zâ€–â‚

Î» controls sparsity of Z. Start at 1e-3, tune by inspecting
mean active dimensions in Z (target: 5â€“15% of bottleneck dim).
```

```python
import torch
import torch.nn as nn

class SparseAutoencoder(nn.Module):
    """
    Sparse autoencoder over concatenated character n-gram and wordpiece
    BM25 sparse vectors.

    Require: input X is normalized (L2 or max-norm per row)
    Guarantee: bottleneck Z has L1-penalized activations; decoder
               reconstructs both C and W halves
    Maintain: split_idx marks boundary between C and W in X
    Failure modes: if lambda_l1 too high, Z collapses to zero â€”
                   monitor mean active dims per batch
    """

    def __init__(self, input_dim: int, bottleneck_dim: int,
                 hidden_dim: int, split_idx: int, lambda_l1: float = 1e-3):
        super().__init__()
        self.split_idx = split_idx
        self.lambda_l1 = lambda_l1
        self.encoder = nn.Sequential(
            nn.Linear(input_dim, hidden_dim),
            nn.ReLU(),
            nn.Linear(hidden_dim, bottleneck_dim),
            nn.ReLU()
        )
        self.decoder = nn.Sequential(
            nn.Linear(bottleneck_dim, hidden_dim),
            nn.ReLU(),
            nn.Linear(hidden_dim, input_dim)
        )

    def forward(self, x: torch.Tensor):
        z = self.encoder(x)
        x_hat = self.decoder(z)
        recon_loss = nn.functional.mse_loss(x_hat, x)
        sparsity_loss = self.lambda_l1 * z.abs().mean()
        return z, x_hat, recon_loss + sparsity_loss

    def encode(self, x: torch.Tensor) -> torch.Tensor:
        return self.encoder(x)

    def decode(self, z: torch.Tensor) -> torch.Tensor:
        return self.decoder(z)
```

**Training:**
- Batch over the 2k sample (full corpus for production)
- Input: dense slice from sparse X via `.toarray()` per batch
- Normalize rows before input (max-norm)
- Adam, lr=1e-3, 50â€“100 epochs
- Checkpoint to SQLite after each epoch; load-if-exists

**Validation gate:** reconstruction MSE on held-out 10% < 0.1 (normalized).
Mean active bottleneck dims per sample: 5â€“15% of bottleneck_dim.

---

## Stage 4 â€” Correlation Graph

**Goal:** build a paragraph-level graph where edges encode BM25 score
correlation, then detect communities as retrieval regions.

```
Require: BM25 score matrix M âˆˆ R^(n Ã— n), significance threshold Ï„
Guarantee: graph G with edges only where |corr(i,j)| â‰¥ Ï„
Maintain: diagonal excluded; undirected graph
```

```python
import numpy as np
import scipy.stats
import networkx as nx
import community as community_louvain  # python-louvain

def build_correlation_graph(
    bm25_matrix: np.ndarray,
    tau: float = 0.3,
    p_threshold: float = 0.05
) -> nx.Graph:
    """
    Build paragraph correlation graph from BM25 score matrix.

    Require: bm25_matrix shape (n, n), symmetric, diagonal = self-scores
    Guarantee: returns undirected graph; edges only where Pearson r â‰¥ tau
               AND p-value < p_threshold
    Maintain: no self-loops
    Failure modes: dense graph if tau too low â€” monitor edge count,
                   target < 5% of possible edges for n > 500
    """
    n = bm25_matrix.shape[0]
    G = nx.Graph()
    G.add_nodes_from(range(n))
    for i in range(n):
        for j in range(i + 1, n):
            r, p = scipy.stats.pearsonr(bm25_matrix[i], bm25_matrix[j])
            if abs(r) >= tau and p < p_threshold:
                G.add_edge(i, j, weight=abs(r))
    return G

def detect_communities(G: nx.Graph) -> dict:
    """
    Run Louvain + WCC community detection.

    Returns dict with:
      louvain: {node_id: community_id}
      wcc: list of frozensets (connected components)
      dwpc: {(i,j): degree_weighted_path_count} for sampled pairs
    """
    louvain = community_louvain.best_partition(G, weight='weight')
    wcc = list(nx.connected_components(G))
    return {'louvain': louvain, 'wcc': wcc}
```

**DWPC** (degree-weighted path coefficient): for inter-community distance,
down-weight paths through high-degree nodes. Use on sampled node pairs only
(full DWPC is O(nÂ²Â·|E|)).

```python
def dwpc(G: nx.Graph, source: int, target: int, damping: float = 0.4) -> float:
    """
    Degree-weighted path count between source and target.
    Paths through high-degree nodes are penalized by degree^(-damping).

    Require: source and target are nodes in G
    Guarantee: scalar similarity score â‰¥ 0
    Failure modes: disconnected source/target returns 0.0
    """
    try:
        paths = list(nx.all_simple_paths(G, source, target, cutoff=4))
    except nx.NetworkXNoPath:
        return 0.0
    score = 0.0
    for path in paths:
        weight = 1.0
        for node in path[1:-1]:
            weight *= G.degree(node) ** (-damping)
        score += weight
    return score
```

**Validation gate:** Louvain modularity Q > 0.3. WCC largest component < 60%
of nodes (if larger, raise tau). Edge density < 5% for n > 500.

---

## Stage 5 â€” Composite Retrieval Index

**Goal:** store per-paragraph (Z, community_id, avg_bm25) in SQLite for fast
retrieval with composite distance scoring.

```python
import sqlite3
import numpy as np
import json

def build_index(
    db_path: str,
    paragraph_ids: list,
    Z: np.ndarray,
    louvain: dict,
    avg_bm25: np.ndarray,
    char_inverted: dict,
    wp_inverted: dict
) -> None:
    """
    Write retrieval index to SQLite.

    Require: Z shape (n, bottleneck_dim), normalized rows
    Guarantee: each paragraph has one row; inverted indexes stored as JSON
    Maintain: char_inverted and wp_inverted keyed by hash_id â†’ [para_ids]
    """
    con = sqlite3.connect(db_path)
    con.execute("""
        CREATE TABLE IF NOT EXISTS paragraphs (
            para_id TEXT PRIMARY KEY,
            z_vector BLOB,
            community_id INTEGER,
            avg_bm25 REAL
        )
    """)
    con.execute("""
        CREATE TABLE IF NOT EXISTS inverted_char (
            ngram_id INTEGER PRIMARY KEY,
            para_ids TEXT
        )
    """)
    con.execute("""
        CREATE TABLE IF NOT EXISTS inverted_wp (
            token_id INTEGER PRIMARY KEY,
            para_ids TEXT
        )
    """)
    for i, pid in enumerate(paragraph_ids):
        con.execute(
            "INSERT OR REPLACE INTO paragraphs VALUES (?,?,?,?)",
            (pid, Z[i].tobytes(), louvain[i], float(avg_bm25[i]))
        )
    for ngram_id, pids in char_inverted.items():
        con.execute(
            "INSERT OR REPLACE INTO inverted_char VALUES (?,?)",
            (ngram_id, json.dumps(pids))
        )
    for token_id, pids in wp_inverted.items():
        con.execute(
            "INSERT OR REPLACE INTO inverted_wp VALUES (?,?)",
            (token_id, json.dumps(pids))
        )
    con.commit()
    con.close()
```

**Composite retrieval distance** at query time:

```
d(q, p) = Î± Â· â€–Z_q âˆ’ Z_pâ€–â‚‚
         + Î² Â· (1 âˆ’ community_overlap(q, p))
         + Î³ Â· (1 / avg_bm25_p)

Default: Î±=0.6, Î²=0.3, Î³=0.1
community_overlap = 1 if same Louvain community, else 0
```

Tune Î±, Î², Î³ via RAGAS: macro-mean of context precision, context recall,
answer relevancy, faithfulness over a held-out QA eval set.

---

## Phi-Weighted EMA Over Temporal Attestations

When the corpus spans multiple eras (e.g. archetype tracking across historical
texts), weight paragraph embeddings by attestation recency using phi-decay EMA.

```
Î±_R = 1/Ï† â‰ˆ 0.618  (recency-dominant)
Î±_T = 1 âˆ’ 1/Ï† â‰ˆ 0.382  (tradition-dominant)

n = days since first attestation, rounded to nearest 90-day quarter.
If residual = 45 exactly (equidistant), snap to 182 (mid-year).

EMA_t = Î± Â· Z_t + (1 âˆ’ Î±) Â· EMA_{tâˆ’1}

Run both streams. Gap â€–EMA_R âˆ’ EMA_Tâ€–â‚‚ measures cultural renegotiation rate.
Wide gap â†’ archetype in active drift. Narrow gap â†’ costume changed, signal stable.
```

---

## Stack

| Concern | Tool |
|---|---|
| Sparse matrices | scipy.sparse (CSR) |
| Tokenizer | HuggingFace tokenizers (wordpiece) |
| BM25 | rank_bm25 |
| Autoencoder | PyTorch |
| ANN search | faiss (IndexFlatL2 for bottleneck dim â‰¤ 256) |
| Graph | networkx + python-louvain |
| Storage | SQLite |
| Topic modeling | sklearn NMF or gensim LDA |
| Evaluation | RAGAS (macro-mean: context precision, recall, answer relevancy, faithfulness) |
| LLM endpoint | Ollama qwen3.5 or llama.cpp at localhost:11434 |

---

## Decomposition Order

```
1. corpus_loader         no deps
2. sampler               depends on 1
3. dual_hash             depends on 1
4. autoencoder_train     depends on 3
5. bm25_matrix           depends on 1
6. correlation_graph     depends on 5
7. index_build           depends on 4, 6
8. retriever             depends on 7
9. eval_ragas            depends on 8
```

Do not proceed to stage N+1 until stage N passes its validation gate.

---

## Validation Gates Summary

| Stage | Gate |
|---|---|
| Sampler | â‰¥80% stratum coverage; no stratum > 20% of sample |
| Dual hash | Zero collisions in V_c and V_w |
| Autoencoder | Recon MSE < 0.1; active bottleneck dims 5â€“15% |
| Correlation graph | Louvain Q > 0.3; largest WCC < 60% nodes; edge density < 5% |
| Retriever | RAGAS macro-mean > 0.65 on held-out QA set |

---

## Dead Ends

### Using dense embeddings as the primary signal before establishing sparse structure
Dense embeddings hide what the sparse signals can reveal explicitly. Build the
sparse structure first; add dense embeddings as a late fusion signal only after
RAGAS confirms the sparse system's ceiling.

### Feature hashing (collision-based)
Deliberately collapses dimensions to reduce size. Breaks invertibility. Use
perfect hashing over a closed vocabulary instead.

### Computing DWPC over all node pairs
O(nÂ²Â·|E|) â€” intractable for n > 200. Sample inter-community pairs only, or
restrict to pairs within DWPC cutoff=4.

### Tuning Î±, Î², Î³ by hand
Always tune via RAGAS on a held-out eval set generated by LLM extraction from
the corpus. Gut feel on retrieval weights is not validation.

---

## Applicability Envelope

**Works well when:**
- corpus is bounded and vocabulary is closed (fixed wordpiece tokenizer)
- paragraphs have meaningful length variation worth stratifying on
- corpus spans identifiable topics (LDA/NMF produces coherent topics)
- retrieval needs interpretability â€” sparse signals are auditable, bottleneck
  activations are inspectable

**Fails or degrades when:**
- corpus is too small (< 500 paragraphs) â€” correlation graph becomes trivial
- vocabulary is open-ended and grows at query time â€” breaks invertibility
- bottleneck dim is too large â€” Z becomes dense, loses retrieval speed advantage
- tau set too low â€” graph becomes nearly complete, community structure
  meaningless

---

## Linear Bottleneck (TruncatedSVD) â€” No-Training Alternative

Before training a PyTorch AE, try the **linear bottleneck** first. It requires no gradient descent, is deterministic, and is often sufficient when corpus structure is approximately linear.

The optimal linear dimensionality reduction is TruncatedSVD (Eckart-Young theorem): minimises Frobenius-norm reconstruction error over all rank-k linear maps.

```python
from sklearn.feature_extraction.text import TfidfVectorizer, CountVectorizer
from sklearn.decomposition import TruncatedSVD
from sklearn.preprocessing import normalize
from scipy.sparse import hstack
import numpy as np

class MultiViewProjector:
    """
    Linear multi-view bottleneck: TF-IDF + token count + char bitvec â†’ TruncatedSVD â†’ z.

    Views (concatenated before SVD):
        1. TF-IDF (max_tfidf_features) â€” term importance
        2. Token CountVectorizer (closed vocab, min_df=2) â€” bag-of-words multiset
        3. Char n-gram bitvec (analyzer="char", n=char_n) â€” morphological surface

    Require: len(docs) > ae_dim
    Guarantee: transform() returns L2-normalised z âˆˆ R^{n Ã— ae_dim}
    Failure modes: corpus < ae_dim docs causes TruncatedSVD to fail
    """

    def __init__(self, max_tfidf_features=8000, ae_dim=64, char_n=3):
        self.max_tfidf_features = max_tfidf_features
        self.ae_dim = ae_dim
        self.char_n = char_n
        self.tfidf_vec = self.token_vec = self.char_vec = self.svd = None
        self.explained_variance_ = 0.0

    def fit(self, docs: list[str]):
        self.tfidf_vec = TfidfVectorizer(max_features=self.max_tfidf_features, sublinear_tf=True).fit(docs)
        self.token_vec = CountVectorizer(min_df=2).fit(docs)
        self.char_vec = CountVectorizer(analyzer="char", ngram_range=(self.char_n, self.char_n), min_df=2).fit(docs)
        X = self._build_matrix(docs)
        self.svd = TruncatedSVD(n_components=self.ae_dim, random_state=42).fit(X)
        self.explained_variance_ = float(self.svd.explained_variance_ratio_.sum())
        return self

    def _build_matrix(self, docs):
        X_t = self.tfidf_vec.transform(docs)
        X_c = self.token_vec.transform(docs)
        X_n = (self.char_vec.transform(docs) > 0).astype("float32")
        return hstack([X_t, X_c, X_n], format="csr")

    def transform(self, docs: list[str]) -> np.ndarray:
        return normalize(self.svd.transform(self._build_matrix(docs)), norm="l2")
```

**When to upgrade to PyTorch AE:** if `explained_variance_` < 0.30 after fitting on the proxy corpus, the linear bottleneck is leaving > 70% of variance on the floor â€” switch to the nonlinear SparseAutoencoder in Stage 3.

Typical explained variance:
- Brown corpus (general text): 0.35â€“0.42
- Technical corpora (narrow domain): 0.55â€“0.70 (TF-IDF dominates, views are collinear)
- Mixed-domain corpora: 0.25â€“0.35 (high residual â†’ consider nonlinear)

---

## Collinearity Test Protocol

Run this before adding dense embeddings to the retrieval stack. Dense embeddings (nomic-embed-text, BGE) are worth the compute only if they add signal orthogonal to the sparse views.

```python
from sklearn.cross_decomposition import CCA
import numpy as np

def view_collinearity(z1: np.ndarray, z2: np.ndarray, n_components: int = 10) -> float:
    """
    Measure collinearity between two latent spaces via Canonical Correlation Analysis.
    Returns mean canonical correlation across n_components pairs.
    1.0 = views fully collinear, 0.0 = orthogonal.

    Require: z1, z2 âˆˆ R^{n Ã— d}, n > n_components
    """
    cca = CCA(n_components=n_components, max_iter=1000)
    z1_c, z2_c = cca.fit_transform(z1, z2)
    return float(np.mean([np.corrcoef(z1_c[:, i], z2_c[:, i])[0, 1] for i in range(n_components)]))
```

**Decision tree:**
- `collinearity(sparse_z, dense_z) > 0.70` â†’ dense redundant; skip embedding call
- `collinearity < 0.40` â†’ dense orthogonal; add as 4th view or fuse graphs with RRF
- `0.40â€“0.70` â†’ borderline; run community NMI (normalized mutual information) to decide:
  - if `NMI(sparse_communities, dense_communities) > 0.80` â†’ same partition, skip dense
  - else â†’ dense changes community structure, worth adding

**Per-view collinearity:** also compare views against each other before concatenating.
If `collinearity(tfidf_z, token_z) > 0.85` â†’ token count vector is redundant given TF-IDF.
In practice, char bitvec adds morphological signal not in TF-IDF (handles OOV stems and spelling variants).

---

## Connection to Music Embedding Matrix Pattern

The `music/` repo builds an embedding matrix: items (tracks) Ã— features (MFCC, chroma, â€¦) â†’ sparse matrix â†’ SVD â†’ z per track. This is the same architecture applied to text:

| `music/` pattern | `bm25-autoencoder` |
|---|---|
| items = tracks | items = paragraphs |
| features = audio feature axes | features = TF-IDF terms + token IDs + char n-grams |
| sparse matrix = track Ã— feature presence | sparse matrix = doc Ã— term weight / count |
| TruncatedSVD(k) â†’ z per track | TruncatedSVD(k) â†’ z per doc |
| cosine sim on z â†’ track similarity graph | cosine sim on z â†’ retrieval community graph |
| walk back: feature_id â†’ audio feature name | walk back: token_id â†’ vocab[id] (bag-of-words recovery) |

The BM25 wordpiece sparse matrix is the "starting schema." Each wordpiece token is a feature axis; each document is an item. The dual-hash gives invertibility: you can reconstruct the token set (bag-of-words) from the compressed z path â€” same as recovering which audio features place a track in its z-space position.

---

## See Also

[[bm25-corpus-sampling]]  [[representation-pipeline]]  [[cluster-quantized-knn]]  [[median-bifurcation]]
