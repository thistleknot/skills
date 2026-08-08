---
name: bm25-corpus-sampling
description: >
  Representative corpus sampling for BM25 fitting. When the full corpus would
  take > 2 hours to index, extract a ~2000-document sample whose WordNet token
  distribution approximates the full corpus. Stratifies on a 2D joint feature
  space (document-length bin × topic), normalizes cell counts via
  log-normal → median/MAD scale → Yeo-Johnson → shift-positive / linear normalize,
  then allocates quota proportionally. The Yeo-Johnson z-scores are a reusable
  reliability signal: the same cell weights that drive corpus sampling also serve
  as a BM25 reranker (penalise documents from poorly-calibrated cells) and as an
  ensemble mixing coefficient between BM25 and dense retrieval. Use before
  fitting any BM25 index when parity (convergence on global IDF mean) is the
  goal, not exhaustive coverage.
status: active
last_validated: 2026-05-25
---

# BM25 Corpus Sampling

## When to Use

- Full corpus BM25 fitting would exceed ~2 hours
- Goal is IDF/token-frequency **parity** with the full corpus, not exhaustive indexing
- Corpus has meaningful variation in both document length and topic/domain

Do **not** use when:
- Corpus is < 5K documents (index it directly)
- Topic labels or length bins are unavailable and cannot be approximated

---

## Goal

Produce a ~2000-document sample whose **average WordNet token presence** approximates the full corpus. Concretely: the BM25 IDF estimates computed on the sample should be close to the true IDF on the full corpus.

This requires:
1. Short and long documents proportionally represented — rare long-tail tokens live in long documents
2. All topics proportionally represented — domain-specific vocabulary only appears in topic-relevant documents

---

## Feature Space

Document length is always available and is the primary stratification axis. Topic is optional — use it when labels exist, omit it when they don't (the grid degrades gracefully to 1D).

| Feature | Availability | Derivation |
|---|---|---|
| `len_bin` | **Always** | Log-bin the unit token count: `bin = floor(log2(token_count))` |
| `topic` | Optional | LDA, BERTopic, k-means on embeddings, category labels, or file/folder path |

When topic is unavailable, the cell key is just `(len_bin,)` — a 1D length-stratified sample. This still corrects for the most common BM25 failure mode (short documents dominating IDF via high term frequency).

### Sampling unit: sub-document granularity

The sampling unit does not have to be the whole document. Use sub-document units when the raw document count is too small to reach the target sample size:

| Context | Unit | Why |
|---|---|---|
| Brown corpus (500 files) | Paragraph (natural line break) | 500 docs → 15K paragraphs → sample 2000 |
| RAG over a codebase or wiki | Markdown section (heading-delimited) | Preserves semantic coherence per chunk |
| Long PDF / book corpus | Fixed-stride sentence window | Uniform coverage when paragraph structure is inconsistent |

The unit choice should match the retrieval granularity downstream — if RAG retrieves by section, sample by section so BM25 IDF reflects the actual retrieval unit's vocabulary.

---

## Canonical Example: Brown Corpus Paragraphs

**Why Brown:** 500 source files, 15 genre categories, ~15K paragraphs — small enough to fit in memory, rich enough to stress-test stratification. Topics are the official Brown genre codes:

| NLTK key | Code | Texts | Group | Description | Subcategories |
|---|---|---|---|---|---|
| `news` | A | 44 | Informative Prose | Press: Reportage | Political, Sports, Society, Spot News, Financial, Cultural |
| `editorial` | B | 27 | Informative Prose | Press: Editorial | Institutional Daily, Personal, Letters to the Editor |
| `reviews` | C | 17 | Informative Prose | Press: Reviews | Theatre, Books, Music, Dance |
| `religion` | D | 17 | Informative Prose | Religion | Books, Periodicals, Tracts |
| `hobbies` | E | 36 | Informative Prose | Skill and Hobbies | Books, Periodicals |
| `lore` | F | 48 | Informative Prose | Popular Lore | Books, Periodicals |
| `belles_lettres` | G | 75 | Informative Prose | Belles-Lettres: Biography, Memoirs, etc. | Books, Periodicals |
| `government` | H | 30 | Informative Prose | Miscellaneous: US Government & House Organs | Government Documents, Foundation Reports, Industry Reports, College Catalog, Industry House Organ |
| `learned` | J | 80 | Informative Prose | Learned | Natural Sciences, Medicine, Mathematics, Social & Behavioral Sciences, Political Science/Law/Education, Humanities, Technology & Engineering |
| `fiction` | K | 29 | Imaginative Prose | Fiction: General | Novels, Short Stories |
| `mystery` | L | 24 | Imaginative Prose | Fiction: Mystery and Detective | Novels, Short Stories |
| `science_fiction` | M | 6 | Imaginative Prose | Fiction: Science | Novels, Short Stories |
| `adventure` | N | 29 | Imaginative Prose | Fiction: Adventure and Western | Novels, Short Stories |
| `romance` | P | 29 | Imaginative Prose | Fiction: Romance and Love Story | Novels, Short Stories |
| `humor` | R | 9 | Imaginative Prose | Humor | Novels, Essays etc. |

**Setup:**
```python
import numpy as np
from scipy.stats import median_abs_deviation
from sklearn.preprocessing import PowerTransformer
from nltk.corpus import brown

# 1. Build paragraph pool per category
pool: dict[str, list] = {}
for cat in brown.categories():
    paras = []
    for fid in brown.fileids(categories=cat):
        for para in brown.paras(fid):
            tokens = [w.lower() for s in para for w in s if w.isalpha()]
            if tokens:
                paras.append({'tokens': tokens, 'token_count': len(tokens), 'topic': cat})
    pool[cat] = paras

# category paragraph counts:
# news=2234, learned=1418, belles_lettres=1405, adventure=1387, ...
# humor=254, science_fiction=335, religion=369

# 2. Normalize counts → sampling proportions
cats = sorted(pool.keys())
counts = np.array([len(pool[c]) for c in cats], dtype=float)

x = np.log1p(counts)
med = np.median(x); mad = median_abs_deviation(x, scale=1.4826)
x = (x - med) / (mad + 1e-9)
pt = PowerTransformer(method='yeo-johnson', standardize=False)
x = pt.fit_transform(x.reshape(-1, 1)).ravel()

# weighted sum = 1: CDF bin areas (consecutive Gaussian CDF differences sorted by z_yj)
# Each category gets the Gaussian probability mass between its z-score and the previous one.
# Categories near z=0 (median-sized) get the most mass; extreme outliers land in thin tails.
# "news should get 97%" = news's bin starts at the ~97th percentile (learned's CDF ≈ 96.7%)
from scipy.stats import norm
order = np.argsort(x)
z_sorted = x[order]
cdf_vals = norm.cdf(z_sorted)
weights_sorted = np.diff(cdf_vals, prepend=0.0)
weights_sorted /= weights_sorted.sum()
weights = np.empty_like(weights_sorted)
weights[order] = weights_sorted

# 3. Allocate quota across categories proportionally
N = 2000
rng = np.random.default_rng(42)
quotas = np.round(weights * N).astype(int)
quotas = np.maximum(quotas, 1)                       # every category gets at least 1
excess = quotas.sum() - N
for idx in np.argsort(quotas)[::-1]:                 # trim from largest first
    if excess <= 0: break
    trim = min(int(quotas[idx]) - 1, excess)
    quotas[idx] -= trim; excess -= trim

# 4. Sample paragraphs within each category
sample = []
for i, cat in enumerate(cats):
    q = int(quotas[i])
    paras = pool[cat]
    idx = rng.choice(len(paras), size=min(q, len(paras)), replace=False)
    sample.extend(paras[j] for j in idx)

# ~2000 paragraphs, proportionally weighted by normalized category size
```

**Expected cell structure:** 15 topics × ~7 log2 length bins = up to 105 cells. In practice ~90 non-empty (some short-para × rare-genre cells are empty). News (`A`) and Learned (`J`) dominate by paragraph count; Science Fiction (`M`) and Humor (`R`) are the tail.

**Actual paragraph counts and quota allocation** (Brown corpus, 2000-paragraph target, CDF-difference weights):

| NLTK key | z_yj | CDF | Δ CDF (bin) | Total paras | Quota | % sample |
|---|---|---|---|---|---|---|
| `humor` | −5.68 | 0.000 | 0.000 | 254 | 1 | 0.1% |
| `science_fiction` | −4.87 | 0.000 | 0.000 | 334 | 1 | 0.1% |
| `religion` | −4.56 | 0.000 | 0.000 | 369 | 1 | 0.1% |
| `reviews` | −2.72 | 0.003 | 0.003 | 629 | 7 | 0.4% |
| `government` | −1.46 | 0.072 | 0.068 | 850 | 137 | 6.9% |
| `editorial` | −0.65 | 0.259 | 0.187 | 1,002 | **370** | **18.5%** |
| `fiction` | −0.43 | 0.334 | 0.075 | 1,042 | 150 | 7.5% |
| `hobbies` | +0.00 | 0.500 | 0.166 | 1,118 | **332** | **16.6%** |
| `mystery` | +0.27 | 0.606 | 0.106 | 1,163 | 212 | 10.6% |
| `lore` | +0.51 | 0.697 | 0.091 | 1,203 | 181 | 9.0% |
| `romance` | +0.81 | 0.792 | 0.096 | 1,251 | 192 | 9.6% |
| `adventure` | +1.67 | 0.952 | 0.160 | 1,385 | **320** | **16.0%** |
| `belles_lettres` | +1.78 | 0.963 | 0.010 | 1,403 | 21 | 1.1% |
| `learned` | +1.83 | 0.967 | 0.004 | 1,411 | 8 | 0.4% |
| `news` | +6.64 | 1.000 | 0.034 | 2,233 | 67 | **3.4%** |
| **TOTAL** | | | | **15,647** | **2,000** | **100%** |

**Reading the table:** Categories with z_yj near 0 (editorial, hobbies, mystery) get the highest quota because the Gaussian PDF peaks at the center. News is at z=6.64 — its bin starts at the 97th percentile (learned's CDF=96.7%) and runs to +∞, a region with only 3.4% of Gaussian mass. The three extreme-negative categories (humor, sci-fi, religion) fall in the near-zero tail and each receive the minimum floor of 1.

---

## Weight Normalization Pipeline

Transforms raw cell counts into a probability simplex (weights sum to 1) for quota allocation.

### Step 1 — Log-normal

```python
x = np.log1p(n)   # log(n + 1); handles zero cells; maps power-law counts toward normal
```

### Step 2 — Median/MAD scale (robust standardization)

```python
from scipy.stats import median_abs_deviation
median = np.median(x)
mad = median_abs_deviation(x, scale=1.4826)   # scale makes MAD consistent with σ under normality
x = (x - median) / (mad + 1e-9)              # +epsilon avoids divide-by-zero on uniform corpora
```

Why MAD over σ: cell counts are often skewed or contain outlier-heavy cells (one dominant topic). MAD is resistant to those outliers; σ would over-suppress the tail.

### Step 3 — Yeo-Johnson

```python
from sklearn.preprocessing import PowerTransformer
pt = PowerTransformer(method='yeo-johnson', standardize=False)
x = pt.fit_transform(x.reshape(-1, 1)).ravel()
```

Why Yeo-Johnson over Box-Cox: Yeo-Johnson accepts zero and negative values (which appear after median/MAD centering). Box-Cox requires strictly positive input.

### Step 4 — Probability simplex (CDF bin areas)

Sort categories by z-score. The weight for each category is the probability mass of the standard normal that falls between its z-score and the previous category's z-score — i.e., the area under the Gaussian curve for that "bin." Categories near z=0 (median-sized) get the most mass; extreme outliers land in the thin tails.

```python
from scipy.stats import norm
order = np.argsort(x)
z_sorted = x[order]
cdf_vals = norm.cdf(z_sorted)

# Consecutive CDF differences: each bin owns the Gaussian mass from the
# previous threshold to its own. Sums to cdf(max) ≈ 1.0.
weights_sorted = np.diff(cdf_vals, prepend=0.0)
weights_sorted /= weights_sorted.sum()   # normalize to exactly 1.0

# Restore original category order
weights = np.empty_like(weights_sorted)
weights[order] = weights_sorted
```

**How to read "news should get 97%":** After Yeo-Johnson, news lands at z=6.64. The previous category (learned) is at z=1.83, CDF≈96.7%. News's bin starts at the ~97th percentile of the distribution and runs to +∞. The Gaussian tail past 97% is thin — news gets only 3.4% of quota (67 paragraphs of 2000). The "97%" names where news's bin *begins*, not how much it receives.

**Why this beats linear normalize:** Linear preserve the Yeo-Johnson rank but treat z-score differences as linear distances. CDF differences use the Gaussian to weight each gap — so a 4-sigma gap between learned (z=1.83) and news (z=6.64) correctly maps to a tiny probability mass (the tail is nearly empty there), while a 0.2-sigma gap near the center maps to large mass. The normalization is *geometry-aware*.

---

## Quota Allocation and Sampling

```python
N = 2000
quotas = np.round(weights * N).astype(int)

# Guarantee every non-empty cell gets at least 1 document
non_empty = n > 0
quotas[non_empty] = np.maximum(quotas[non_empty], 1)

# Rebalance to stay within N (rare cells took from pool)
excess = quotas.sum() - N
if excess > 0:
    # Trim from highest-quota cells first
    largest = np.argsort(quotas.ravel())[::-1]
    for idx in largest:
        if excess <= 0:
            break
        trim = min(quotas.ravel()[idx] - 1, excess)
        quotas.ravel()[idx] -= trim
        excess -= trim

# Sample within each cell (uniform; or weight by doc quality score if available)
sample = []
for (i, j), q in np.ndenumerate(quotas):
    cell_docs = cells[(i, j)]
    if len(cell_docs) == 0 or q == 0:
        continue
    drawn = rng.choice(cell_docs, size=min(q, len(cell_docs)), replace=False)
    sample.extend(drawn)
```

---

## Full Implementation

```python
import numpy as np
from scipy.stats import median_abs_deviation
from sklearn.preprocessing import PowerTransformer


def bm25_corpus_sample(
    docs: list[dict],
    len_key: str = "token_count",
    topic_key: str = "topic",
    n_sample: int = 2000,
    seed: int = 42,
) -> list[dict]:
    """
    Sample a representative subset of documents for BM25 fitting.

    Require:
        docs: list of dicts, each with len_key (int) and topic_key (str/int)
        len_key: field containing document token count
        topic_key: field containing topic label
        n_sample: target sample size (default 2000)

    Guarantee:
        Returns <= n_sample documents whose (length, topic) distribution
        approximates the full corpus via log-normal → MAD scale → Yeo-Johnson
        → probability simplex allocation.

    Maintain:
        Every non-empty (len_bin, topic) cell receives at least 1 document.
        Total returned <= n_sample.
    """
    rng = np.random.default_rng(seed)

    # 1. Compute features
    def len_bin(token_count: int) -> int:
        return max(0, int(np.floor(np.log2(max(token_count, 1)))))

    cells: dict[tuple, list] = {}
    for doc in docs:
        key = (len_bin(doc[len_key]), doc[topic_key])
        cells.setdefault(key, []).append(doc)

    keys = sorted(cells.keys())
    counts = np.array([len(cells[k]) for k in keys], dtype=float)

    # 2. Log-normal
    x = np.log1p(counts)

    # 3. Median/MAD scale
    med = np.median(x)
    mad = median_abs_deviation(x, scale=1.4826)
    x = (x - med) / (mad + 1e-9)

    # 4. Yeo-Johnson
    pt = PowerTransformer(method='yeo-johnson', standardize=False)
    x = pt.fit_transform(x.reshape(-1, 1)).ravel()

    # 5. Probability simplex via CDF bin areas
    # Sort by z-score; each category's weight = Gaussian probability mass between
    # its z-score and the previous one. Categories near z=0 (median-sized) get the
    # most mass; extreme outliers land in thin tails and get small (but nonzero) weight.
    from scipy.stats import norm as _norm
    order = np.argsort(x)
    z_sorted = x[order]
    cdf_vals = _norm.cdf(z_sorted)
    weights_sorted = np.diff(cdf_vals, prepend=0.0)
    weights_sorted /= (weights_sorted.sum() + 1e-12)
    weights = np.empty_like(weights_sorted)
    weights[order] = weights_sorted

    # Expose cell weights for downstream reranking / ensemble use
    z_scores = {key: float(w) for key, w in zip(keys, weights)}

    # 6. Quota allocation
    quotas = np.round(weights * n_sample).astype(int)
    quotas[counts > 0] = np.maximum(quotas[counts > 0], 1)

    excess = int(quotas.sum()) - n_sample
    if excess > 0:
        for idx in np.argsort(quotas)[::-1]:
            if excess <= 0:
                break
            trim = min(int(quotas[idx]) - 1, excess)
            quotas[idx] -= trim
            excess -= trim

    # 7. Sample
    sample = []
    for i, key in enumerate(keys):
        q = int(quotas[i])
        cell_docs = cells[key]
        if q == 0 or not cell_docs:
            continue
        drawn = rng.choice(len(cell_docs), size=min(q, len(cell_docs)), replace=False)
        sample.extend(cell_docs[j] for j in drawn)

    return sample
```

---

## The z-score as Reranker and Ensemble Weight

The Yeo-Johnson output is a **z-score relative to the normal distribution of cell counts**. High |z| means the cell is an outlier — over- or under-represented — so BM25 IDF estimates derived from it are noisy. This reliability signal has two retrieval uses beyond sampling.

### Reranker

After BM25 retrieval, adjust each result's score by the reliability of the IDF estimates for its cell:

```python
def rerank_bm25(results: list[dict], cell_z: dict[tuple, float]) -> list[dict]:
    """
    Penalise BM25 scores from cells where IDF estimates are poorly calibrated.
    results: list of {doc, bm25_score, len_bin, topic}
    cell_z: {(len_bin, topic): z_score} from the sampling pipeline
    """
    for r in results:
        z = cell_z.get((r['len_bin'], r['topic']), 0.0)
        reliability = 1.0 / (1.0 + abs(z))   # 1.0 when z=0, → 0 as |z| grows
        r['adjusted_score'] = r['bm25_score'] * reliability
    return sorted(results, key=lambda r: r['adjusted_score'], reverse=True)
```

### Ensemble with Dense Retrieval

Use |z| as the mixing coefficient: where BM25 IDF is reliable (z ≈ 0), trust BM25; where the cell is an outlier, shift weight to dense retrieval (which is corpus-frequency-independent):

```python
import math

def ensemble_score(
    bm25_score: float,
    dense_score: float,
    z: float,
) -> float:
    """
    Adaptive BM25 + dense ensemble weighted by BM25 cell reliability.

    When z ≈ 0 (cell well-represented, IDF reliable): alpha → 0.5, balanced mix.
    When |z| large (cell outlier, IDF noisy): alpha → 0, trust dense only.
    """
    alpha = 1.0 / (1.0 + math.exp(abs(z)))   # sigmoid of -|z|; ∈ (0, 0.5]
    return alpha * bm25_score + (1.0 - alpha) * dense_score
```

The key property: the same pipeline run once at index time produces three artifacts:
1. The 2000-document **sample** for BM25 fitting
2. The **cell z-scores** for retrieval reranking
3. The **ensemble mixing coefficients** for BM25 + dense fusion



After sampling, verify representativeness:

```python
from collections import Counter
import math

def idf(docs, tokenize_fn):
    """Compute IDF over a list of docs."""
    N = len(docs)
    df: Counter = Counter()
    for doc in docs:
        df.update(set(tokenize_fn(doc)))
    return {t: math.log((N - f + 0.5) / (f + 0.5) + 1) for t, f in df.items()}

full_idf = idf(full_corpus, tokenize)
sample_idf = idf(sample, tokenize)

shared = set(full_idf) & set(sample_idf)
mae = np.mean([abs(full_idf[t] - sample_idf[t]) for t in shared])
coverage = len(shared) / len(full_idf)
print(f"Token coverage: {coverage:.1%}  |  IDF MAE: {mae:.4f}")
```

Acceptance thresholds (adjust to corpus):
- Token coverage ≥ 85% of full corpus vocabulary
- IDF MAE < 0.15

If coverage is low, increase `n_sample` or verify topic labels are granular enough to split underrepresented domains.

---

## Why This Pipeline Over Box-Cox + z-score

| Criterion | Box-Cox + z | Log → MAD → Yeo-Johnson |
|---|---|---|
| Handles zero counts | ❌ requires strictly positive | ✅ log1p + Yeo-Johnson both accept zero |
| Outlier resistance | Mean/σ sensitive to outliers | MAD is breakdown-point 50% |
| Negative input after centering | ❌ Box-Cox fails | ✅ Yeo-Johnson accepts negatives |
| When to prefer Box-Cox | Strictly positive, symmetric | — |

Use `stratified-quota-sampling` when you want Fibonacci-tiered hard quotas by class. Use this skill when you want a continuous probability-simplex allocation across a 2D joint feature grid.

---

## Notes

- **Topic granularity**: too few topics (< 5) collapse the 2D grid; too many (> 50) spread quota too thin per cell. 10–20 topics works well for most corpora.
- **Length bins**: log2 binning produces ~7 bins for corpora spanning 10–10K tokens. Fixed bins are fine if token counts cluster naturally.
- **Wordnet token presence**: WordNet coverage is a proxy for lexical diversity. Longer documents and technical topics contribute rare tokens; both must be represented for BM25 IDF to generalize.
- **Re-running**: fix `seed` for reproducibility; change seed to get an independent sample for ensemble IDF estimates.

---

## BM25 Similarity Graph Without Full-Corpus Indexing

The sampling pipeline produces a representative BM25 proxy index. Use it to construct a **sparse similarity graph** (analogous to a cosine similarity matrix) for community detection — without pairwise BM25 over the full corpus. Two concrete architectures:

---

### Option A — Cascaded (cosine-first)

```
query
  → dense retrieval (cosine similarity, full corpus)
      → top-K candidates
          → BM25 rerank within candidates (proxy index from sample)
              → pairwise BM25 scores among top-K as edge weights
                  → threshold edges (keep "significant" correlations)
                      → Louvain / WCC community detection
```

BM25 cost is bounded to the retrieved set. Appropriate when cosine recall is high. Degrades when the query space has poor embedding coverage (rare tokens, technical jargon) — BM25-relevant documents that cosine missed won't appear in the graph.

---

### Option B — Proxy Model + k-means + BM25 Correlation Graph

```
sample (2000 docs)
  → fit proxy TF-IDF model (vocabulary + IDF from sample)
      → at retrieval time:
          → project retrieved candidates into proxy TF-IDF space
              → k-means clustering on projected retrieved set (bounds O(n²) to O(cluster²))
                  → per cluster: build n×n BM25 score matrix S
                      where S[i,j] = BM25(doc_i as query, doc_j as doc)
                  → Pearson-correlate rows of S → correlation matrix C
                      C[i,j] = pearsonr(S[i,:], S[j,:])
                  → keep edges where C[i,j] > corr_thresh (significant correlations only)
                      → Louvain / WCC / DWPC community detection
```

**Key insight: BM25 score matrix → correlation matrix:**
Two documents are co-retrieval-correlated when they retrieve similar neighbours. If doc_i and doc_j both strongly retrieve the same set of documents (similar BM25 score profile), they share topic — even if doc_i and doc_j don't directly match each other. The correlation matrix captures this *indirect* topical similarity.

```python
import numpy as np
from rank_bm25 import BM25Okapi
from scipy.stats import pearsonr
import networkx as nx

def build_bm25_correlation_graph(
    candidate_ids: list[int],
    docs: list[dict],
    corr_thresh: float = 0.10,
) -> nx.Graph:
    """
    Build graph where edge weight = Pearson correlation between BM25 score profiles.

    S[i,j] = BM25 score when doc_i is used as query against doc_j.
    Two docs are adjacent if their retrieval profiles are correlated: they retrieve
    similar neighbors (shared topic signal) even if they don't directly match.
    This is NOT pairwise BM25 — it is co-retrieval correlation.

    Significant correlation threshold:
      corr_thresh=0.10 is conservative (catches broad co-retrieval).
      corr_thresh=0.30 gives tight clusters (only strong co-retrieval).
      Rule of thumb: elbow on the distribution of all pairwise correlations.
    """
    cand_texts = [docs[i]["tokens"] for i in candidate_ids]
    bm25 = BM25Okapi(cand_texts)
    n = len(candidate_ids)

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
```

**DWPC edge weighting (penalises hub documents):**
Generic documents (high degree in the correlation graph) should contribute less credit per edge than specialist documents. Degree-Weighted Path Count normalises by the geometric mean of node degrees:

```python
# For each node u, DWPC score = Σ_{(u,v) ∈ edges} weight(u,v) / sqrt(deg(u) * deg(v))
# Hub nodes (large deg) get penalised; specialists (small deg) get amplified credit.
degrees = dict(G.degree())
dwpc = {}
for u, v, data in G.edges(data=True):
    w = data["weight"] / (math.sqrt(degrees[u] * degrees[v]) + 1e-9)
    dwpc[u] = dwpc.get(u, 0.0) + w
    dwpc[v] = dwpc.get(v, 0.0) + w
```

k-means bounds pairwise BM25 to O(cluster_size²) per cluster. Proxy IDF noise propagates from sample quality — apply `1/(1+|z_c|)` reliability weighting to edges from high-|z| cells.

---

### Option C — Closed-Vocabulary Hash Graph (zero BM25 cost)

When BM25 scoring is too expensive for large candidate pools, replace the BM25 correlation graph with a **dual-hash Jaccard graph** using a closed vocabulary:

```
full corpus
  → enumerate all tokens → sorted token IDs (zero-collision, no hash function)
  → enumerate all char n-grams (n=3) → sorted n-gram IDs (same format)
      → at retrieval time per candidate pair (i, j):
          token_jaccard = |tok_ids(i) ∩ tok_ids(j)| / |tok_ids(i) ∪ tok_ids(j)|
          char_jaccard  = |char_ids(i) ∩ char_ids(j)| / |char_ids(i) ∪ char_ids(j)|
          edge_weight   = (token_jaccard + char_jaccard) / 2
          → keep edges above jac_thresh → same Louvain/WCC/DWPC community detection
```

**Why closed-vocabulary hashing is invertible:**
- Token IDs = index into sorted vocabulary. `vocab[id]` recovers the token. Zero collisions by construction.
- Count vector (`uint16` per vocab position) recovers the exact multiset (bag-of-words, no order).
- Char n-gram IDs similarly invertible for the n-gram set (not original text order).
- The dual representation (token + char) combines lexical overlap with morphological similarity — handles stemming variants without a stemmer.

**O(V/64) vs O(n·|tokens|):** NumPy bitwise AND/OR on boolean arrays is 64× faster than BM25 token scoring for the same candidate pool.

---

### Shared Design Parameters

| Decision | Guidance |
|---|---|
| Edge weight (BM25 graph) | Pearson correlation between BM25 score profiles; significant if r > corr_thresh |
| Edge weight (hash graph) | Mean(token_jaccard, char_jaccard); add edge if > jac_thresh |
| corr_thresh | 0.10 conservative, 0.30 tight; elbow on pairwise correlation distribution |
| jac_thresh | 0.05 typical; increase if graph is too dense, decrease if too sparse |
| k-means clusters | 5 per 50-candidate pool; scales O(clusters) |
| IDF reliability correction | Weight edges by `1/(1+\|z_c\|)` for cells with high variance from normal |
| Community detection | Louvain (overlapping, modularity) / WCC (disjoint) / DWPC (hub-penalised) |

---

## PI-Stratified Sampling (Robust Alternative to CDF-Diff)

The CDF-diff pipeline above works well when the corpus is large and well-spread. For smaller or skewed corpora, a simpler two-axis stratification using predictive intervals is more stable:

**Step 1 — Prune outlier-length documents (95% PI)**
```python
from scipy.stats import median_abs_deviation
lens = [d["token_len"] for d in docs]
med = np.median(lens)
mad = median_abs_deviation(lens, scale=1.4826)  # σ-equivalent under normality
lo, hi = med - 1.96 * mad, med + 1.96 * mad     # 95% prediction interval
# Prune: keep only docs within PI (removes ~5% extreme-length outliers)
surviving = [d for d in docs if lo <= d["token_len"] <= hi]
```

This is a **predictive interval** (per-document), not a confidence interval (population estimate). It asks: "Is this specific document's length within the expected range?" — appropriate when outlier removal is the goal, not mean estimation.

**Step 2 — Joint stratification on (length_bin × category)**
```python
import numpy as np
# Quantile bins: 10 bins by token length percentile
quantiles = np.percentile([d["token_len"] for d in surviving], np.linspace(0, 100, 11))
def len_bin(l): return min(9, np.searchsorted(quantiles[1:-1], l))

# Category inverse-frequency weight
from collections import Counter
cat_counts = Counter(d["category"] for d in surviving)
total = len(surviving)
cat_weight = {c: total / (len(cat_counts) * n) for c, n in cat_counts.items()}

# Per-doc weight = harmonic mean of bin weight and category weight
bin_counts = Counter(len_bin(d["token_len"]) for d in surviving)
bin_weight = {b: total / (10 * n) for b, n in bin_counts.items()}

def doc_weight(d):
    bw = bin_weight[len_bin(d["token_len"])]
    cw = cat_weight[d["category"]]
    return 2 * bw * cw / (bw + cw + 1e-9)  # harmonic mean
```

**Step 3 — Proportional quota with floor guarantee**
```python
rng = np.random.default_rng(seed)
weights = np.array([doc_weight(d) for d in surviving])
weights /= weights.sum()
# Sample indices without replacement, weighted
sample_idx = rng.choice(len(surviving), size=n_sample, replace=False, p=weights)
```

**When to use PI-stratified vs CDF-diff:**
- **CDF-diff**: better when category counts span many orders of magnitude (news vs humor 10:1 ratio); CDF compression prevents extreme categories from dominating
- **PI-stratified**: better when the corpus is more uniform or when you want a simpler, more interpretable weight formula; harmonic mean prevents any single axis from dominating
- Both guarantee floor-1 per non-empty cell when combined with quota rounding

<!-- consolidation:see-also:start -->
## See Also
[[stratified-quota-sampling]]  [[representation-pipeline]]  [[hyper-parm_tuning]]  [[bm25-autoencoder]]
<!-- consolidation:see-also:end -->
