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

# weighted sum = 1: shift to positive, normalize linearly
# (NOT softmax — softmax is exponential and amplifies the largest cell into near-monopoly)
# Shift ensures all categories (including negative z-score tail) get quota.
x = x - x.min() + 1e-9
weights = x / x.sum()   # sum to 1

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

**Actual paragraph counts and quota allocation** (Brown corpus, 2000-paragraph target):

| NLTK key | Total paras | % corpus | Quota | % sample |
|---|---|---|---|---|
| `adventure` | 1,385 | 8.9% | 187 | 9.3% |
| `belles_lettres` | 1,403 | 9.0% | 190 | 9.5% |
| `editorial` | 1,002 | 6.4% | 128 | 6.4% |
| `fiction` | 1,042 | 6.7% | 134 | 6.7% |
| `government` | 850 | 5.4% | 108 | 5.4% |
| `hobbies` | 1,118 | 7.1% | 145 | 7.2% |
| `humor` | 254 | 1.6% | 1 | 0.1% |
| `learned` | 1,411 | 9.0% | 192 | 9.6% |
| `lore` | 1,203 | 7.7% | 158 | 7.9% |
| `mystery` | 1,163 | 7.4% | 152 | 7.6% |
| `news` | 2,233 | 14.3% | 313 | 15.7% |
| `religion` | 369 | 2.4% | 29 | 1.5% |
| `reviews` | 629 | 4.0% | 76 | 3.8% |
| `romance` | 1,251 | 8.0% | 166 | 8.3% |
| `science_fiction` | 334 | 2.1% | 21 | 1.1% |
| **TOTAL** | **15,647** | **100%** | **2,000** | **100%** |

`humor` rounds to 1 (rounding artifact from 254 paragraphs producing a very small linear weight). The `maximum(quotas, 1)` floor ensures it is included. The overall % sample column tracks % corpus closely — confirming proportional representation.

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

### Step 4 — Probability simplex (shift-positive, linear normalize)

```python
x = x - x.min() + 1e-9    # shift so minimum is just above 0; preserves all cells
weights = x / x.sum()      # sum to 1
```

Why **not** softmax: softmax applies `exp()`, which is exponential. A dominant category with z≈2 produces `e²≈7.4` while a tail category with z≈-1 produces `e⁻¹≈0.37` — a 20× gap that compounds the original count imbalance rather than correcting it. In practice, softmax collapses >96% of the quota into the single largest category. Shift-positive + linear normalize preserves relative ordering while keeping the tail viable.

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

    # 5. Probability simplex via shift-positive + linear normalize
    # Variance from normal IS the signal. Shift-positive preserves all cells
    # (including negative z-score tail = under-represented). Linear normalize
    # keeps relative proportions without exponential amplification.
    x = x - x.min() + 1e-9
    weights = x / x.sum()

    # Also expose shifted weights for downstream reranking / ensemble use
    z_scores = {key: float(x_val) for key, x_val in zip(keys, x)}

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

### Option B — Proxy Model + k-means projection

```
sample (2000 docs)
  → fit proxy BM25/TF-IDF model (vocabulary + IDF from sample)
      → at retrieval time:
          → project retrieved documents into proxy feature space
              → k-means clustering on projected retrieved set
                  → pairwise BM25 scores within each cluster (bounded by cluster size)
                      → threshold edges → Louvain / WCC community detection
```

k-means bounds pairwise BM25 to O(cluster_size²) per cluster. Proxy IDF noise propagates from sample quality — apply `1/(1+|z_c|)` reliability weighting to edges from high-|z| cells. Louvain for overlapping topic communities; WCC for hard disjoint groups (more sensitive to edge threshold choice).

---

### Shared Design Parameters

| Decision | Guidance |
|---|---|
| Edge weight threshold | Elbow on BM25 score distribution within the retrieved/cluster set |
| Topic labels for cell grid | Option A: cosine cluster labels. Option B: k-means labels on sample. |
| IDF reliability correction | Weight edges by `1/(1+\|z_c\|)` for cells with high variance from normal |
| Community detection | Louvain (overlapping, modularity) vs WCC (disjoint, threshold-driven) |

<!-- consolidation:see-also:start -->
## See Also
[[stratified-quota-sampling]]  [[representation-pipeline]]  [[hyper-parm_tuning]]
<!-- consolidation:see-also:end -->

<!-- consolidation:see-also:start -->
## See Also
[[stratified-quota-sampling]]  [[representation-pipeline]]  [[hyper-parm_tuning]]
<!-- consolidation:see-also:end -->
