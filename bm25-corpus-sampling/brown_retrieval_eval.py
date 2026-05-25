"""brown_retrieval_eval.py — No-LLM BM25-community retrieval comparison on Brown corpus.

Compares six retrieval systems:
  dense_only      — nomic-embed-text cosine similarity (Ollama, embeddings only)
  bm25_full       — BM25 over full corpus (rank_bm25, BM25Okapi)
  hybrid_rrf      — Reciprocal Rank Fusion: dense + bm25_full
  bm25_proxy      — BM25Okapi fitted on 2k PI-stratified proxy sample only;
                    retrieval restricted to proxy pool; measures IDF-preservation lift
  proxy_louvain   — k-means on TF-IDF wordpiece → BM25 score matrix
                    → Pearson correlation matrix → Louvain community rerank
  proxy_wcc       — same BM25 correlation graph → WCC (weakly connected component)
                    cohesion rerank
  proxy_dwpc      — same graph → DWPC-weighted community score rerank
                    (Degree-Weighted Path Count: edge_weight / sqrt(deg_u * deg_v))

Sampling (2 000-para proxy corpus — no LLM needed):
  1. Per paragraph compute token length.
  2. Prune to 95% prediction interval: median ± 1.96 × 1.4826 × MAD.
  3. Bin surviving paragraphs into 10 quantile token-length bins.
  4. Gather per-category counts.
  5. Weight = harmonic mean(token_bin_weight, category_weight).
  6. Sample 2 000 proportionally (quota rounding + floor-1 guarantee).

Evaluation (label-based + intrinsic — NO LLM required):
  context_precision   — fraction of top-K retrieved docs from same Brown category
  context_recall      — |same-cat in top-K| / min(|same-cat total|, K)
  avg_bm25_score      — mean BM25 score of retrieved docs (intrinsic relevance)
  community_density   — mean intra-community BM25 edge weight (proxy systems only; 0 for others)

Ground truth: same Brown category = relevant.
Query set  : 30 paragraphs (PI-stratified sample, seed=99).
Embeddings : nomic-embed-text via Ollama, checkpointed to SQLite.

Require:
  rank_bm25, networkx>=2.7, nltk(brown), scikit-learn, scipy, numpy, requests
  Ollama running on localhost:11434 with nomic-embed-text pulled.
  (qwen3.5:4b NOT required — no LLM judge or question/answer generation.)
"""

import math
import pickle
import sqlite3
import time
import numpy as np
import networkx as nx
import requests
from collections import defaultdict
from pathlib import Path

import nltk
from nltk.corpus import brown
from scipy.stats import median_abs_deviation, norm, pearsonr
from sklearn.preprocessing import PowerTransformer
from sklearn.feature_extraction.text import TfidfVectorizer
from sklearn.cluster import KMeans
from rank_bm25 import BM25Okapi

CKPT       = Path(__file__).parent / "retrieval_eval.db"
K          = 10           # retrieval depth for all metrics
DENSE_POOL = 50           # dense candidates fed to proxy reranker
N_CLUSTERS = 5            # k-means clusters for proxy BM25 graph
CORR_THRESH  = 0.1         # minimum Pearson correlation to create a graph edge
JAC_THRESH   = 0.05        # minimum Jaccard similarity to create a hash-graph edge
CHAR_N       = 3           # character n-gram length for char hash
AE_DIM       = 64          # bottleneck dimension for multi-view projector
AE_THRESH    = 0.55        # cosine similarity threshold for AE graph edges
OLLAMA     = "http://localhost:11434"
EMB_MODEL  = "nomic-embed-text"
N_QUERIES  = 30           # number of eval queries
N_PROXY    = 2000         # proxy corpus size for sampling + TF-IDF vocab




# ── checkpoint ────────────────────────────────────────────────────────────────

def _db():
    db = sqlite3.connect(CKPT)
    db.execute("CREATE TABLE IF NOT EXISTS cache (key TEXT PRIMARY KEY, value BLOB)")
    db.commit()
    return db


def _get(db, key):
    row = db.execute("SELECT value FROM cache WHERE key=?", (key,)).fetchone()
    return pickle.loads(row[0]) if row else None


def _set(db, key, value):
    db.execute("INSERT OR REPLACE INTO cache VALUES (?,?)", (key, pickle.dumps(value)))
    db.commit()


# ── Ollama embedding helper ───────────────────────────────────────────────────

def embed_batch(texts: list[str], db, cache_key: str) -> np.ndarray:
    """
    Embed texts with nomic-embed-text via Ollama, L2-normalised.
    Results are checkpointed so re-runs skip the API calls.

    Require: texts non-empty, Ollama running with nomic-embed-text pulled.
    Guarantee: returns float32 array shape (len(texts), embedding_dim).
    """
    cached = _get(db, cache_key)
    if cached is not None:
        return cached

    print(f"  Embedding {len(texts):,} texts with {EMB_MODEL}...")
    vecs = []
    batch_size = 64
    for i in range(0, len(texts), batch_size):
        batch = texts[i : i + batch_size]
        resp = requests.post(
            f"{OLLAMA}/api/embed",
            json={"model": EMB_MODEL, "input": batch},
            timeout=300,
        )
        resp.raise_for_status()
        vecs.extend(resp.json()["embeddings"])
        if (i // batch_size) % 8 == 0 and i > 0:
            print(f"    {i}/{len(texts)}")

    arr = np.array(vecs, dtype=np.float32)
    norms = np.linalg.norm(arr, axis=1, keepdims=True)
    arr = arr / np.where(norms > 1e-9, norms, 1.0)
    _set(db, cache_key, arr)
    print("  Embeddings cached.")
    return arr


# ── corpus ────────────────────────────────────────────────────────────────────

def build_corpus() -> list[dict]:
    """
    Return all Brown paragraphs with ≥10 alpha tokens as dicts:
    {id, text, tokens, token_len, category}
    """
    docs = []
    for cat in sorted(brown.categories()):
        for fid in brown.fileids(categories=cat):
            for para in brown.paras(fid):
                tokens = [w.lower() for s in para for w in s if w.isalpha()]
                if len(tokens) >= 10:
                    docs.append({
                        "id": len(docs),
                        "text": " ".join(tokens),
                        "tokens": tokens,
                        "token_len": len(tokens),
                        "category": cat,
                    })
    return docs


# ── PI-stratified sampling ────────────────────────────────────────────────────

def pi_stratified_sample(docs: list[dict], n_sample: int = 2000, seed: int = 42,
                         n_bins: int = 10) -> list[int]:
    """
    Sample n_sample doc indices using a two-axis stratification:
      Axis 1 — token-length bins (10 quantile bins within 95% PI)
      Axis 2 — category counts

    Steps:
      1. Compute 95% prediction interval on token lengths:
           lower = median - 1.96 * 1.4826 * MAD
           upper = median + 1.96 * 1.4826 * MAD
      2. Prune paragraphs outside [lower, upper].
      3. Bin survivors into n_bins quantile token-length bins.
      4. Compute category frequency weights (uniform → rare categories get more share).
      5. Per-doc weight = harmonic mean(bin_weight, cat_weight).
      6. Quota-sample proportionally with floor-1 guarantee.

    Require: docs non-empty, n_sample ≤ len(docs).
    Guarantee: returns list of unique doc indices of length n_sample (or fewer if corpus is small).
    """
    lengths = np.array([d["token_len"] for d in docs], dtype=float)
    med = float(np.median(lengths))
    mad = float(median_abs_deviation(lengths, scale=1.4826))
    pi_lo = med - 1.96 * mad
    pi_hi = med + 1.96 * mad

    # prune to PI survivors
    survivors = [i for i, d in enumerate(docs) if pi_lo <= d["token_len"] <= pi_hi]
    surv_lens = np.array([docs[i]["token_len"] for i in survivors], dtype=float)

    # token-length quantile bins
    bin_edges = np.percentile(surv_lens, np.linspace(0, 100, n_bins + 1))
    bin_edges[-1] += 1e-6  # ensure last edge is inclusive
    bin_ids = np.digitize(surv_lens, bin_edges[1:-1])  # 0 … n_bins-1

    bin_counts = np.bincount(bin_ids, minlength=n_bins).astype(float)
    bin_weights = np.where(bin_counts > 0, 1.0 / bin_counts, 0.0)
    bin_weights /= bin_weights[bin_counts > 0].sum() if bin_weights.sum() > 0 else 1.0

    # category inverse-frequency weights
    cat_counts: dict[str, int] = defaultdict(int)
    for i in survivors:
        cat_counts[docs[i]["category"]] += 1
    n_surv = len(survivors)
    cat_w = {c: (n_surv / (len(cat_counts) * cnt)) for c, cnt in cat_counts.items()}
    c_vals = np.array([cat_w[docs[i]["category"]] for i in survivors])
    c_vals /= c_vals.sum()

    # bin weights per survivor
    b_vals = bin_weights[bin_ids]
    b_vals = b_vals / b_vals.sum() if b_vals.sum() > 0 else np.ones(len(survivors)) / len(survivors)

    # harmonic mean of the two weight vectors
    eps = 1e-12
    w = 2.0 * (b_vals * c_vals) / (b_vals + c_vals + eps)
    w /= w.sum()

    rng = np.random.default_rng(seed)
    n_eff = min(n_sample, len(survivors))
    quotas_f = w * n_eff
    quotas = np.maximum(np.round(quotas_f).astype(int), 1)
    excess = int(quotas.sum()) - n_eff
    for idx in np.argsort(quotas)[::-1]:
        if excess <= 0:
            break
        trim = min(int(quotas[idx]) - 1, excess)
        quotas[idx] -= trim
        excess -= trim

    chosen = rng.choice(len(survivors), size=n_eff, replace=False, p=w)
    return [survivors[j] for j in chosen[:n_eff]]


# ── label-based and intrinsic evaluation metrics ─────────────────────────────

def context_precision(retrieved_cats: list[str], query_cat: str) -> float:
    """Fraction of top-K retrieved docs from the same category (signal-to-noise)."""
    return sum(c == query_cat for c in retrieved_cats[:K]) / K


def context_recall(retrieved_cats: list[str], query_cat: str, total_relevant: int) -> float:
    """
    |same-cat in top-K| / min(total_relevant, K).
    Measures whether retrieval surfaced what was needed.
    """
    hits = sum(c == query_cat for c in retrieved_cats[:K])
    denom = min(total_relevant, K)
    return hits / denom if denom > 0 else 0.0


def avg_bm25_score(bm25_index: BM25Okapi, query_tokens: list[str],
                   retrieved_ids: list[int]) -> float:
    """
    Mean BM25 score of retrieved docs (intrinsic relevance signal).
    Higher = retrieved docs contain more query-relevant terms.
    """
    all_scores = bm25_index.get_scores(query_tokens)
    return float(np.mean([all_scores[i] for i in retrieved_ids])) if retrieved_ids else 0.0


# ── closed-vocabulary hash representation ─────────────────────────────────────

class ClosedVocab:
    """
    Lossless dual-level document fingerprint over a closed (enumerable) vocabulary.

    Token hash  : sorted array of token IDs present in the document.
                  Invertible: tok_ids → vocab[id] recovers exact token set.
                  Multiset (with counts) is recoverable via count vector.

    Char hash   : sorted array of char n-gram IDs (n=CHAR_N) over the document text.
                  Not order-preserving but fingerprints morphology exactly.
                  Same format as token hash — same Jaccard distance operation applies.

    Zero-collision guarantee: vocab is fully enumerated at construction time;
    every document token and n-gram maps to a unique integer with no hash function.

    The dual representation captures:
      - token hash  → lexical/semantic identity (what words appear)
      - char hash   → morphological identity (what subword patterns appear)
    Both are comparable without modality switching.
    """

    def __init__(self, docs: list[dict], char_n: int = CHAR_N):
        """
        Build vocabulary and char n-gram table from the full corpus.
        Require: docs[i]["tokens"] is a list of lowercase alpha strings.
        Guarantee: self.V token IDs and self.C char n-gram IDs, both starting at 0.
        """
        all_tokens = sorted(set(tok for d in docs for tok in d["tokens"]))
        self.vocab   : list[str]      = all_tokens
        self.tok2id  : dict[str, int] = {t: i for i, t in enumerate(all_tokens)}
        self.V       : int             = len(all_tokens)

        all_ngrams = sorted(set(
            d["text"][i: i + char_n]
            for d in docs
            for i in range(max(0, len(d["text"]) - char_n + 1))
            if d["text"][i: i + char_n].replace(" ", "").isalpha()
        ))
        self.char_ngrams : list[str]       = all_ngrams
        self.ng2id       : dict[str, int]  = {ng: i for i, ng in enumerate(all_ngrams)}
        self.C           : int              = len(all_ngrams)
        self.char_n      : int              = char_n

    def token_bitvec(self, tokens: list[str]) -> np.ndarray:
        """
        Boolean vector of length V.  bitvec[i] = True iff vocab[i] appears in tokens.
        Invertible: vocab[i] for i where bitvec[i] gives back exact token set.
        """
        vec = np.zeros(self.V, dtype=bool)
        for t in tokens:
            if t in self.tok2id:
                vec[self.tok2id[t]] = True
        return vec

    def token_countvec(self, tokens: list[str]) -> np.ndarray:
        """
        uint16 count vector — recovers multiset exactly (bag-of-words, no order).
        """
        vec = np.zeros(self.V, dtype=np.uint16)
        for t in tokens:
            if t in self.tok2id:
                vec[self.tok2id[t]] += 1
        return vec

    def char_bitvec(self, text: str) -> np.ndarray:
        """
        Boolean vector of length C over char n-grams.
        Same format as token_bitvec — enables same Jaccard operation.
        """
        vec = np.zeros(self.C, dtype=bool)
        for i in range(max(0, len(text) - self.char_n + 1)):
            ng = text[i: i + self.char_n]
            if ng in self.ng2id:
                vec[self.ng2id[ng]] = True
        return vec

    def token_ids(self, tokens: list[str]) -> list[int]:
        """Sorted token ID array — the canonical 'hash string' for this token set."""
        return sorted(self.tok2id[t] for t in tokens if t in self.tok2id)

    def char_ids(self, text: str) -> list[int]:
        """Sorted char n-gram ID array — same canonical format as token_ids."""
        ids = sorted(set(
            self.ng2id[text[i: i + self.char_n]]
            for i in range(max(0, len(text) - self.char_n + 1))
            if text[i: i + self.char_n] in self.ng2id
        ))
        return ids

    def unpack_token_ids(self, ids: list[int]) -> list[str]:
        """Invert token_ids() → recover original token set."""
        return [self.vocab[i] for i in ids]

    def unpack_char_ids(self, ids: list[int]) -> list[str]:
        """Invert char_ids() → recover char n-gram set (not original text order)."""
        return [self.char_ngrams[i] for i in ids]


class MultiViewProjector:
    """
    Linear multi-view autoencoder (TruncatedSVD on concatenated views).

    The three views concatenated per document:
      1. TF-IDF term weights  (proxy_tfidf vocab, ~8 000 features, already L2-normalised)
      2. Token count vector   (ClosedVocab, V features — recovers multiset exactly)
      3. Char n-gram bitvec   (ClosedVocab, C features — morphological signal)

    The SVD bottleneck (z_dim latent dims) is the optimal *linear* compression of all
    three views into a shared space (Eckart-Young theorem: minimum Frobenius reconstruction
    error).  This is the linear limit of a nonlinear multi-view autoencoder; extending to
    a deep encoder/decoder requires PyTorch but the structure is identical.

    Theory (from user):
      - Each view is an independent approximation of the same underlying document.
      - Collinearity between views measures redundancy: if z_tfidf ≈ z_hash, one view adds
        little.  Dense embeddings (nomic-embed-text) are worth adding only when their z is
        orthogonal to the sparse views.
      - The bottleneck z is the unified retrieval representation; community detection on
        z-cosine-similarity graphs replaces the per-view BM25-correlation/Jaccard graphs.

    Require: proxy_tfidf fitted; cv built over full corpus; docs contain 'tokens'+'text'.
    Guarantee: transform() returns L2-normalised float32 array shape (n, z_dim).
    Maintain: fit on proxy corpus, transform can be called on any subset doc_indices.
    """

    def __init__(self, z_dim: int = AE_DIM):
        from sklearn.decomposition import TruncatedSVD
        self.z_dim = z_dim
        self._svd = TruncatedSVD(n_components=z_dim, random_state=42)
        self._fitted = False

    def _build_matrix(
        self,
        doc_indices: list[int],
        docs: list[dict],
        proxy_tfidf: TfidfVectorizer,
        cv: "ClosedVocab",
    ):
        """Sparse (n, V_tfidf + V_tok + C_char) matrix, L2-normalised per row."""
        import scipy.sparse as sp
        from sklearn.preprocessing import normalize as sk_norm

        texts = [docs[i]["text"] for i in doc_indices]
        tokens_list = [docs[i]["tokens"] for i in doc_indices]
        n = len(doc_indices)

        tfidf_mat = proxy_tfidf.transform(texts)

        # token count view — sparse uint16 → float
        tok_rows, tok_cols, tok_vals = [], [], []
        for row, toks in enumerate(tokens_list):
            for t in toks:
                if t in cv.tok2id:
                    tok_rows.append(row)
                    tok_cols.append(cv.tok2id[t])
                    tok_vals.append(1.0)
        tok_mat = sp.csr_matrix((tok_vals, (tok_rows, tok_cols)), shape=(n, cv.V))

        # char n-gram bitvec view
        char_rows, char_cols = [], []
        for row, text in enumerate(texts):
            for i in range(max(0, len(text) - cv.char_n + 1)):
                ng = text[i: i + cv.char_n]
                if ng in cv.ng2id:
                    char_rows.append(row)
                    char_cols.append(cv.ng2id[ng])
        char_mat = sp.csr_matrix(
            (np.ones(len(char_rows), dtype=np.float32), (char_rows, char_cols)),
            shape=(n, cv.C),
        )

        combined = sp.hstack([tfidf_mat, tok_mat, char_mat], format="csr")
        return sk_norm(combined, norm="l2")

    def fit(self, doc_indices: list[int], docs: list[dict],
            proxy_tfidf: TfidfVectorizer, cv: "ClosedVocab") -> "MultiViewProjector":
        """Fit SVD on the proxy corpus (2 000 docs — fast)."""
        X = self._build_matrix(doc_indices, docs, proxy_tfidf, cv)
        self._svd.fit(X)
        self._fitted = True
        return self

    def transform(self, doc_indices: list[int], docs: list[dict],
                  proxy_tfidf: TfidfVectorizer, cv: "ClosedVocab") -> np.ndarray:
        """Project doc_indices into z_dim bottleneck space, L2-normalised."""
        X = self._build_matrix(doc_indices, docs, proxy_tfidf, cv)
        Z = self._svd.transform(X).astype(np.float32)
        norms = np.linalg.norm(Z, axis=1, keepdims=True)
        return Z / np.where(norms > 1e-9, norms, 1.0)

    def explained_variance(self) -> float:
        """Fraction of total variance captured by the z_dim bottleneck."""
        return float(self._svd.explained_variance_ratio_.sum())


def jaccard_bitvec(a: np.ndarray, b: np.ndarray) -> float:
    """
    Jaccard similarity between two boolean vectors.
    J = |A ∩ B| / |A ∪ B| = bitwise_AND.sum() / bitwise_OR.sum()
    O(V/64) with numpy bit-packing vs O(n·|tokens|) for BM25.
    Zero-collision because A and B are drawn from the same closed vocabulary.
    """
    inter = float(np.logical_and(a, b).sum())
    union = float(np.logical_or(a, b).sum())
    return inter / union if union > 0 else 0.0


def build_jaccard_graph(
    candidate_ids: list[int],
    docs: list[dict],
    cv: ClosedVocab,
    jac_thresh: float = JAC_THRESH,
    use_char: bool = True,
) -> nx.Graph:
    """
    Build undirected weighted graph using dual-hash Jaccard similarity.

    Edge weight = mean(token_jaccard, char_jaccard) if use_char else token_jaccard.
    This replaces the BM25 correlation graph with O(n² · (V+C)/64) bitwise ops
    instead of O(n² · |tokens|) float arithmetic — significantly faster for
    large candidate pools.

    Invertibility:
      token bitvec → vocab[i] for active bits → original token set (no order)
      char bitvec  → char_ngrams[i] for active bits → n-gram set (not full text)

    Require: candidate_ids ≥ 2; docs[i]["tokens"] and docs[i]["text"] present.
    Guarantee: nx.Graph with node set = set(candidate_ids); nodes-only if no edges above threshold.
    """
    n = len(candidate_ids)
    G = nx.Graph()
    G.add_nodes_from(candidate_ids)
    if n < 2:
        return G

    tok_vecs = [cv.token_bitvec(docs[i]["tokens"]) for i in candidate_ids]
    chr_vecs = [cv.char_bitvec(docs[i]["text"]) for i in candidate_ids] if use_char else None

    for i in range(n):
        for j in range(i + 1, n):
            tj = jaccard_bitvec(tok_vecs[i], tok_vecs[j])
            if use_char and chr_vecs is not None:
                cj = jaccard_bitvec(chr_vecs[i], chr_vecs[j])
                w = (tj + cj) / 2.0
            else:
                w = tj
            if w > jac_thresh:
                G.add_edge(candidate_ids[i], candidate_ids[j], weight=w)

    return G


def build_bm25_graph(
    candidate_ids: list[int],
    docs: list[dict],
    corr_thresh: float = CORR_THRESH,
) -> nx.Graph:
    """
    Build an undirected weighted graph over candidate_ids where edge weight =
    Pearson correlation between their respective BM25 score vectors.

    Steps:
      1. Each candidate c_i acts as a query; compute BM25 scores against all other candidates.
         This yields an (n × n) BM25 score matrix S where S[i,j] = bm25(c_i as query, c_j as doc).
      2. Pearson-correlate rows of S: corr[i,j] = pearsonr(S[i,:], S[j,:]).
         Two docs are correlated if they retrieve similar neighbours when used as queries.
      3. Add edge (c_i, c_j) if corr[i,j] > corr_thresh; weight = corr[i,j].

    Require: candidate_ids has ≥ 2 elements; docs[i]["tokens"] must be present.
    Guarantee: returns nx.Graph with node set = set(candidate_ids).
               If no edges form (all correlations below threshold), returns graph with nodes only.
    """
    n = len(candidate_ids)
    if n < 2:
        G = nx.Graph()
        G.add_nodes_from(candidate_ids)
        return G

    cand_texts = [docs[i]["tokens"] for i in candidate_ids]
    bm25 = BM25Okapi(cand_texts)

    # BM25 score matrix: row i = scores when doc i is the query
    S = np.zeros((n, n), dtype=float)
    for i in range(n):
        S[i] = bm25.get_scores(cand_texts[i])

    G = nx.Graph()
    G.add_nodes_from(candidate_ids)

    for i in range(n):
        for j in range(i + 1, n):
            if np.std(S[i]) < 1e-9 or np.std(S[j]) < 1e-9:
                continue
            r, _ = pearsonr(S[i], S[j])
            if r > corr_thresh:
                G.add_edge(candidate_ids[i], candidate_ids[j], weight=float(r))

    return G


def community_density(G: nx.Graph, community: set) -> float:
    """
    Mean intra-community edge weight for a given community set.
    Returns 0.0 for singleton communities.
    """
    edges = [(u, v, d["weight"]) for u, v, d in G.edges(data=True)
             if u in community and v in community]
    return float(np.mean([w for _, _, w in edges])) if edges else 0.0


def build_ae_graph(
    candidate_ids: list[int],
    docs: list[dict],
    ae: MultiViewProjector,
    proxy_tfidf: TfidfVectorizer,
    cv: ClosedVocab,
    ae_thresh: float = AE_THRESH,
) -> nx.Graph:
    """
    Build similarity graph on multi-view AE (TruncatedSVD) bottleneck z-space.

    Projects each candidate into the shared z_dim latent space via ae.transform(),
    then adds an edge between any two candidates whose cosine similarity > ae_thresh.
    Because z vectors are L2-normalised, cosine similarity = dot product.

    This is the community-detection equivalent of using the bottleneck z as the
    retrieval representation — replacing the per-view BM25-correlation / Jaccard graphs
    with a single graph over the multi-view compressed representation.

    Require: ae.fit() already called; candidate_ids ≥ 2.
    Guarantee: nx.Graph with node set = set(candidate_ids); nodes-only if no cosine
               similarities exceed ae_thresh.
    """
    G = nx.Graph()
    G.add_nodes_from(candidate_ids)
    if len(candidate_ids) < 2:
        return G

    Z = ae.transform(candidate_ids, docs, proxy_tfidf, cv)  # (n, z_dim) L2-normed
    sim = Z @ Z.T  # cosine similarity matrix (n × n)
    n = len(candidate_ids)
    for i in range(n):
        for j in range(i + 1, n):
            s = float(sim[i, j])
            if s > ae_thresh:
                G.add_edge(candidate_ids[i], candidate_ids[j], weight=s)
    return G


# ── Reciprocal Rank Fusion ────────────────────────────────────────────────────

def rrf_fuse(rank_lists: list[list[int]], rrf_k: int = 60) -> list[int]:
    scores: dict[int, float] = defaultdict(float)
    for ranks in rank_lists:
        for rank, doc_id in enumerate(ranks):
            scores[doc_id] += 1.0 / (rrf_k + rank + 1)
    return sorted(scores.keys(), key=lambda d: -scores[d])



# ── community-detection rerankers ─────────────────────────────────────────────

def _cluster_then_graph(
    dense_top50: list[int],
    docs: list[dict],
    proxy_tfidf: TfidfVectorizer,
    graph_builder=None,
) -> tuple[nx.Graph, list[list[int]]]:
    """
    Common first stage for all proxy rerankers:
      1. Project dense_top50 into TF-IDF wordpiece space.
      2. k-means cluster.
      3. Build similarity graph per cluster using graph_builder.
         graph_builder(member_ids, docs) → nx.Graph

    Returns (G, cluster_member_lists).
    """
    if graph_builder is None:
        graph_builder = build_bm25_graph

    if len(dense_top50) <= 1:
        G = nx.Graph()
        G.add_nodes_from(dense_top50)
        return G, [dense_top50]

    vecs = proxy_tfidf.transform([docs[i]["text"] for i in dense_top50])
    n_c = min(N_CLUSTERS, len(dense_top50))
    labels = KMeans(n_clusters=n_c, n_init=3, random_state=42).fit_predict(vecs)

    G = nx.Graph()
    G.add_nodes_from(dense_top50)
    clusters = []
    for c_id in range(n_c):
        members = [dense_top50[j] for j, lbl in enumerate(labels) if lbl == c_id]
        clusters.append(members)
        if len(members) < 2:
            continue
        subG = graph_builder(members, docs)
        for u, v, d in subG.edges(data=True):
            if G.has_edge(u, v):
                G[u][v]["weight"] = max(G[u][v]["weight"], d["weight"])
            else:
                G.add_edge(u, v, weight=d["weight"])

    return G, clusters


def _community_rerank_louvain(G: nx.Graph, dense_top50: list[int]) -> tuple[list[int], float]:
    if G.number_of_edges() == 0:
        return dense_top50[:K], 0.0
    communities = nx.community.louvain_communities(G, weight="weight", seed=42)
    node_to_comm = {n: cid for cid, comm in enumerate(communities) for n in comm}
    comm_sets = [set(c) for c in communities]
    cohesion: dict[int, float] = defaultdict(float)
    for u, v, data in G.edges(data=True):
        if node_to_comm.get(u) == node_to_comm.get(v):
            cohesion[u] += data["weight"]
            cohesion[v] += data["weight"]
    mean_dens = float(np.mean([community_density(G, cs) for cs in comm_sets if len(cs) > 1]) or 0.0)
    ranked = sorted(dense_top50, key=lambda d: (-cohesion.get(d, 0.0), dense_top50.index(d)))
    return ranked[:K], mean_dens


def _community_rerank_wcc(G: nx.Graph, dense_top50: list[int]) -> tuple[list[int], float]:
    if G.number_of_edges() == 0:
        return dense_top50[:K], 0.0
    components = list(nx.connected_components(G))
    node_to_comp = {n: cid for cid, comp in enumerate(components) for n in comp}
    cohesion: dict[int, float] = defaultdict(float)
    for u, v, data in G.edges(data=True):
        if node_to_comp.get(u) == node_to_comp.get(v):
            cohesion[u] += data["weight"]
            cohesion[v] += data["weight"]
    mean_dens = float(np.mean([community_density(G, c) for c in components if len(c) > 1]) or 0.0)
    ranked = sorted(dense_top50, key=lambda d: (-cohesion.get(d, 0.0), dense_top50.index(d)))
    return ranked[:K], mean_dens


def _community_rerank_dwpc(G: nx.Graph, dense_top50: list[int]) -> tuple[list[int], float]:
    if G.number_of_edges() == 0:
        return dense_top50[:K], 0.0
    degrees = dict(G.degree())
    dwpc: dict[int, float] = defaultdict(float)
    for u, v, data in G.edges(data=True):
        w = data["weight"]
        denom = math.sqrt(degrees[u] * degrees[v]) + 1e-9
        contribution = w / denom
        dwpc[u] += contribution
        dwpc[v] += contribution
    mean_dwpc = float(np.mean(list(dwpc.values()))) if dwpc else 0.0
    ranked = sorted(dense_top50, key=lambda d: (-dwpc.get(d, 0.0), dense_top50.index(d)))
    return ranked[:K], mean_dwpc


def proxy_louvain_rerank(
    dense_top50: list[int], docs: list[dict], proxy_tfidf: TfidfVectorizer,
    graph_builder=None,
) -> tuple[list[int], float]:
    """k-means → graph (BM25 or Jaccard) → Louvain community → rerank."""
    G, _ = _cluster_then_graph(dense_top50, docs, proxy_tfidf, graph_builder)
    return _community_rerank_louvain(G, dense_top50)


def proxy_wcc_rerank(
    dense_top50: list[int], docs: list[dict], proxy_tfidf: TfidfVectorizer,
    graph_builder=None,
) -> tuple[list[int], float]:
    """k-means → graph → WCC (connected components) → cohesion rerank."""
    G, _ = _cluster_then_graph(dense_top50, docs, proxy_tfidf, graph_builder)
    return _community_rerank_wcc(G, dense_top50)


def proxy_dwpc_rerank(
    dense_top50: list[int], docs: list[dict], proxy_tfidf: TfidfVectorizer,
    graph_builder=None,
) -> tuple[list[int], float]:
    """k-means → graph → DWPC-weighted → rerank."""
    G, _ = _cluster_then_graph(dense_top50, docs, proxy_tfidf, graph_builder)
    return _community_rerank_dwpc(G, dense_top50)


# ── main ──────────────────────────────────────────────────────────────────────

def main():
    nltk.download("brown", quiet=True)
    db = _db()

    print("Building corpus...")
    docs = build_corpus()
    n_cats = len(set(d["category"] for d in docs))
    print(f"  {len(docs):,} paragraphs across {n_cats} categories")

    # ── token length stats + PI pruning (informational) ──────────────────────
    lengths = np.array([d["token_len"] for d in docs])
    med = float(np.median(lengths))
    mad = float(median_abs_deviation(lengths, scale=1.4826))
    pi_lo, pi_hi = med - 1.96 * mad, med + 1.96 * mad
    n_pruned = sum(1 for l in lengths if not (pi_lo <= l <= pi_hi))
    print(f"  Token lengths — median={med:.0f}, MAD={mad:.1f}, "
          f"95% PI=[{pi_lo:.0f}, {pi_hi:.0f}], pruned={n_pruned} ({100*n_pruned/len(docs):.1f}%)")

    # ── dense embeddings (nomic-embed-text, checkpointed) ────────────────────
    emb_key = f"emb_nomic_{len(docs)}"
    embeddings = embed_batch([d["text"] for d in docs], db, emb_key)
    print(f"  Embedding shape: {embeddings.shape}")

    # ── full-corpus BM25 ──────────────────────────────────────────────────────
    print("Building full-corpus BM25 index...")
    bm25_full = BM25Okapi([d["tokens"] for d in docs])

    # ── proxy TF-IDF on PI-stratified 2k sample ──────────────────────────────
    print(f"Sampling {N_PROXY}-para proxy corpus (PI-stratified)...")
    sample_idx = pi_stratified_sample(docs, n_sample=N_PROXY, seed=42)
    proxy_tfidf = TfidfVectorizer(max_features=8_000, sublinear_tf=True, analyzer="word")
    proxy_tfidf.fit([docs[i]["text"] for i in sample_idx])
    print(f"  Proxy vocab: {len(proxy_tfidf.vocabulary_):,} terms")

    # ── proxy BM25: BM25Okapi fitted on the 2k sample only ───────────────────
    # Measures IDF-preservation claim: does proxy IDF produce similar rankings
    # to full-corpus BM25? Retrieval pool is restricted to proxy sample docs.
    print("Building proxy BM25 index (2k sample)...")
    bm25_proxy = BM25Okapi([docs[i]["tokens"] for i in sample_idx])
    proxy_set = set(sample_idx)
    # global_idx → position in sample_idx list (for score lookup)
    proxy_pos = {gi: pi for pi, gi in enumerate(sample_idx)}

    # ── query set (PI-stratified, different seed) ─────────────────────────────
    print(f"Sampling {N_QUERIES}-query evaluation set (PI-stratified, seed=99)...")
    query_idx = pi_stratified_sample(docs, n_sample=N_QUERIES, seed=99)
    cat_counts: dict[str, int] = defaultdict(int)
    for d in docs:
        cat_counts[d["category"]] += 1

    # ── evaluation loop ───────────────────────────────────────────────────────
    METRICS = ["context_precision", "context_recall", "avg_bm25", "community_density"]
    systems = [
        "dense_only", "bm25_full", "hybrid_rrf", "bm25_proxy",
        "bm25_louvain", "bm25_wcc", "bm25_dwpc",
        "jac_louvain",  "jac_wcc",  "jac_dwpc",
        "ae_louvain",   "ae_wcc",   "ae_dwpc",
    ]
    results: dict[str, list[dict]] = {s: [] for s in systems}

    # closed-vocabulary hash representation (built once over full corpus)
    print("Building closed vocabulary for hash-based retrieval...")
    cv = ClosedVocab(docs)
    print(f"  Token vocab: {cv.V:,}  |  Char {CHAR_N}-gram vocab: {cv.C:,}")

    # Jaccard graph builder bound to the ClosedVocab instance
    jac_builder = lambda ids, docs_: build_jaccard_graph(ids, docs_, cv)

    # Multi-view autoencoder: TF-IDF + token_countvec + char_bitvec → z_dim bottleneck
    print(f"Fitting multi-view projector (TruncatedSVD z_dim={AE_DIM}) on proxy corpus...")
    ae = MultiViewProjector(z_dim=AE_DIM)
    ae.fit(sample_idx, docs, proxy_tfidf, cv)
    print(f"  Explained variance: {ae.explained_variance():.3f}")
    ae_builder = lambda ids, docs_: build_ae_graph(ids, docs_, ae, proxy_tfidf, cv)

    print(f"\nEvaluating {N_QUERIES} queries × {len(systems)} systems (no LLM required)\n")
    t0 = time.time()

    for qi, qidx in enumerate(query_idx):
        qdoc = docs[qidx]
        qcat = qdoc["category"]
        qtoks = qdoc["tokens"]
        qemb = embeddings[qidx]
        total_rel = cat_counts[qcat] - 1

        # dense top-50 (exclude self)
        cos = embeddings @ qemb
        cos[qidx] = -1.0
        dense50 = list(np.argsort(cos)[::-1][:DENSE_POOL])
        dense10 = dense50[:K]

        # full BM25 top-K
        bm25_scores = bm25_full.get_scores(qtoks)
        bm25_scores[qidx] = -1.0
        bm25_10 = list(np.argsort(bm25_scores)[::-1][:K])

        # proxy BM25 top-K (retrieval restricted to 2k proxy sample)
        proxy_scores_raw = bm25_proxy.get_scores(qtoks)  # len == N_PROXY
        # build (global_idx, score) pairs; exclude self if in proxy set
        proxy_scored = [
            (sample_idx[pi], sc)
            for pi, sc in enumerate(proxy_scores_raw)
            if sample_idx[pi] != qidx
        ]
        proxy_scored.sort(key=lambda x: x[1], reverse=True)
        bm25_proxy_10 = [gi for gi, _ in proxy_scored[:K]]

        # hybrid RRF
        rrf_10 = rrf_fuse([dense50, bm25_10])[:K]

        # BM25-correlation community rerankers
        bm25_lou_10, bm25_lou_dens = proxy_louvain_rerank(dense50, docs, proxy_tfidf)
        bm25_wcc_10, bm25_wcc_dens = proxy_wcc_rerank(dense50, docs, proxy_tfidf)
        bm25_dw_10,  bm25_dw_dens  = proxy_dwpc_rerank(dense50, docs, proxy_tfidf)

        # Jaccard (dual hash) community rerankers
        jac_lou_10, jac_lou_dens = proxy_louvain_rerank(dense50, docs, proxy_tfidf, jac_builder)
        jac_wcc_10, jac_wcc_dens = proxy_wcc_rerank(dense50, docs, proxy_tfidf, jac_builder)
        jac_dw_10,  jac_dw_dens  = proxy_dwpc_rerank(dense50, docs, proxy_tfidf, jac_builder)

        # Multi-view AE bottleneck community rerankers
        ae_lou_10,  ae_lou_dens  = proxy_louvain_rerank(dense50, docs, proxy_tfidf, ae_builder)
        ae_wcc_10,  ae_wcc_dens  = proxy_wcc_rerank(dense50, docs, proxy_tfidf, ae_builder)
        ae_dw_10,   ae_dw_dens   = proxy_dwpc_rerank(dense50, docs, proxy_tfidf, ae_builder)

        sys_results = [
            (dense10,      0.0),
            (bm25_10,      0.0),
            (rrf_10,       0.0),
            (bm25_proxy_10, 0.0),
            (bm25_lou_10,  bm25_lou_dens),
            (bm25_wcc_10,  bm25_wcc_dens),
            (bm25_dw_10,   bm25_dw_dens),
            (jac_lou_10,   jac_lou_dens),
            (jac_wcc_10,   jac_wcc_dens),
            (jac_dw_10,    jac_dw_dens),
            (ae_lou_10,    ae_lou_dens),
            (ae_wcc_10,    ae_wcc_dens),
            (ae_dw_10,     ae_dw_dens),
        ]

        for sys_name, (top10, comm_dens) in zip(systems, sys_results):
            ret_cats = [docs[i]["category"] for i in top10]
            rec = {
                "context_precision": context_precision(ret_cats, qcat),
                "context_recall":    context_recall(ret_cats, qcat, total_rel),
                "avg_bm25":          avg_bm25_score(bm25_full, qtoks, top10),
                "community_density": comm_dens,
            }
            results[sys_name].append(rec)

        elapsed = time.time() - t0
        print(f"  [{qi+1:02d}/{N_QUERIES}] cat={qcat:<16}  elapsed={elapsed:.0f}s")

    # ── results table ─────────────────────────────────────────────────────────
    col = 12
    hdr = f"{'System':<20}" + "".join(f"{m[:col-1]:>{col}}" for m in METRICS) + f"{'composite':>{col}}"
    print("\n" + "=" * len(hdr))
    print(hdr)
    print("-" * len(hdr))

    composite_scores = {}
    all_bm25 = [float(np.mean([r["avg_bm25"] for r in results[s]])) for s in systems]
    bm25_range = max(all_bm25) - min(all_bm25) + 1e-9

    # separator rows: baselines → BM25-correlation → Hash-Jaccard → Multi-view AE
    separators = {4: "── BM25-correlation ──", 7: "── Hash-Jaccard (dual) ──", 10: "── Multi-view AE ──"}

    for si, sys_name in enumerate(systems):
        if si in separators:
            print(f"  {separators[si]}")
        recs = results[sys_name]
        v = {m: float(np.mean([r[m] for r in recs])) for m in METRICS}
        v_norm_bm25 = (v["avg_bm25"] - min(all_bm25)) / bm25_range
        comp = float(np.mean([v["context_precision"], v["context_recall"], v_norm_bm25]))
        composite_scores[sys_name] = comp
        row = (f"{sys_name:<20}"
               + "".join(f"{v[m]:>{col}.4f}" for m in METRICS)
               + f"{comp:>{col}.4f}")
        print(row)

    print("=" * len(hdr))
    best = max(composite_scores, key=composite_scores.__getitem__)
    print(f"\nBest composite: {best}  ({composite_scores[best]:.4f})")

    # IDF-preservation lift: proxy BM25 vs full-corpus BM25
    # Note: bm25_proxy retrieves from proxy pool only (2k docs), bm25_full from full corpus.
    # Positive lift = proxy IDF preserves enough signal to match full-corpus quality.
    proxy_lift = composite_scores["bm25_proxy"] - composite_scores["bm25_full"]
    print(f"\n── IDF-preservation lift (bm25_proxy − bm25_full) ──")
    print(f"  composite Δ: {proxy_lift:>+.4f}  "
          f"({'proxy IDF preserves signal' if proxy_lift >= 0 else 'proxy IDF degrades vs full'})")
    print(f"  Note: bm25_proxy restricted to {N_PROXY}-doc proxy pool; "
          f"bm25_full scores all {len(docs):,} docs.")

    # delta table: Jaccard vs BM25 vs AE per community method
    print("\n── Δ composite per community method ──")
    print(f"  {'method':<8}  {'jac−bm25':>10}  {'ae−bm25':>10}  {'ae−jac':>10}")
    for method in ("louvain", "wcc", "dwpc"):
        bm25_s = f"bm25_{method}"
        jac_s  = f"jac_{method}"
        ae_s   = f"ae_{method}"
        d_jb = composite_scores[jac_s] - composite_scores[bm25_s]
        d_ab = composite_scores[ae_s]  - composite_scores[bm25_s]
        d_aj = composite_scores[ae_s]  - composite_scores[jac_s]
        print(f"  {method:<8}  {d_jb:>+10.4f}  {d_ab:>+10.4f}  {d_aj:>+10.4f}")

    print()
    print(f"Embeddings: {EMB_MODEL}  |  K={K}  |  pool={DENSE_POOL}  |  clusters={N_CLUSTERS}")
    print(f"corr_thresh={CORR_THRESH}  jac_thresh={JAC_THRESH}  ae_thresh={AE_THRESH}  "
          f"ae_dim={AE_DIM}  char_n={CHAR_N}  proxy_n={N_PROXY}  queries={N_QUERIES}")
    print(f"Token vocab={cv.V:,}  Char-ngram vocab={cv.C:,}  "
          f"AE explained_var={ae.explained_variance():.3f}")


if __name__ == "__main__":
    main()
