---
name: stratified-quota-sampling
description: Stratify a long-tailed dataset by normalizing raw counts via Box-Cox, bin into Fibonacci tiers at ±1σ, then sample within each tier using a relevance weight. Applies to any domain with imbalanced class frequency (text length distributions, image class imbalance, sparse entity coverage, hierarchical corpus building). Use when you need balanced representation without throwing away rare classes or flooding on frequent ones.
---

# Stratified Quota-Proportional Sampling

## Purpose
Balance imbalanced datasets by:
1. **Normalizing** raw class counts via Box-Cox to near-normality
2. **Binning** into natural tiers (LOW/MID/HIGH) at ±1σ cutoffs
3. **Allocating quotas** in Fibonacci ratios (5/8/13 — φ-spaced)
4. **Sampling within tiers** using a per-item relevance weight (popularity, quality score, engagement)

This prevents both **under-sampling** of rare classes and **over-sampling** of frequent ones, while respecting the empirical distribution shape.

## The Problem

Naive top-N sampling from long-tailed distributions yields:
- All samples from the head (frequent class)
- Nothing from the tail (rare class)
- Skewed representation

Naive uniform sampling across classes yields:
- Massive over-representation of tail classes
- Loss of signal from frequent classes

**Solution**: Use the empirical frequency distribution itself as a signal. A class with 50 items in the corpus is legitimately different from one with 5 items. The Box-Cox transformation reveals the natural tier structure; Fibonacci quotas honor that while staying balanced.

## The Approach

### 1. Normalize via Box-Cox

```python
ns = np.array([count_1, count_2, ...], dtype=float)
bc, lam = boxcox(ns)
```

Box-Cox transforms `count` → `(count^λ - 1) / λ` (or `log(count)` when λ ≈ 0).
This maps a power-law or geometric distribution toward normal.

**Why**: Right-tailed distributions have different quantile positions in linear space than in log-space.
Box-Cox finds the optimal power law to bring the distribution as close to normal as possible.

### 2. Standardize to z-scores

```python
mu, sigma = bc.mean(), bc.std(ddof=0)
z = (bc - mu) / sigma
```

Now `z ∈ (-∞, +∞)` with mean=0, std=1. The quantiles are symmetric around zero.

### 3. Bin at ±1σ into Fibonacci tiers

```python
LOW_QUOTA  = 5   # φ^4 ≈ 6.18
MID_QUOTA  = 8   # φ^5 ≈ 10.0
HIGH_QUOTA = 13  # φ^6 ≈ 16.2
```

| Tier | z-score | Quota | Rationale |
|------|---------|-------|-----------|
| LOW | z < -1 | 5 | Rare class; allocate conservatively but ensure presence |
| MID | -1 ≤ z ≤ +1 | 8 | Modal class; allocate more heavily |
| HIGH | z > +1 | 13 | Very frequent class; allocate most, but stay sublinear (13 not 50) |

**Fibonacci ratios**: 5 → 8 → 13 follow φ (golden ratio). Aesthetically and mathematically principled; avoids arbitrary thresholds like [3, 5, 10].

### 4. Sample within each tier by relevance weight

For each item in tier, assign a relevance score `w` (popularity, quality, engagement, citation count, etc.).

```python
weights = item_scores / sum(item_scores)
chosen = rng.choice(tier_items, size=quota, replace=False, p=weights)
```

**Why**: Items within a class are not all equal. A text has an engagement score; an image has a quality label; a song has Spotify popularity. Use that signal to prefer high-value samples within the class.

**No replacement**: Each item sampled at most once.

## Guarantees

1. **Sublinear scaling**: If a class has 1000 items, you take 13, not 1000. Prevents data imbalance from overwhelming the dataset.
2. **Presence of rare classes**: Even classes with 5-9 items get represented (LOW tier, quota=5).
3. **Proportional representation**: Tier allocation is derived from the empirical distribution, not arbitrary thresholds.
4. **Deterministic (with seed)**: `np.random.default_rng(SEED)` makes draws reproducible.

## Implementation Template

```python
import numpy as np
from scipy.stats import boxcox

def stratified_quota_sample(
    class_items: dict[str, list[dict]],
    weight_key: str,
    seed: int = 42,
    quotas: dict = None,
) -> list[dict]:
    """
    Stratify class-imbalanced data into tiers, allocate quotas, sample within each tier.

    Args:
        class_items: {class_name: [item_dict, ...], ...}
        weight_key: field in item_dict used for relevance weighting (e.g., 'popularity')
        seed: RNG seed for reproducibility
        quotas: override quotas; default {LOW: 5, MID: 8, HIGH: 13}

    Returns:
        list of selected items across all classes and tiers
    """
    if quotas is None:
        quotas = {'LOW': 5, 'MID': 8, 'HIGH': 13}

    rng = np.random.default_rng(seed)
    classes = sorted(class_items.keys())
    counts = np.array([len(class_items[c]) for c in classes], dtype=float)

    # Box-Cox normalization
    bc, lam = boxcox(counts)
    mu, sigma = bc.mean(), bc.std(ddof=0)
    z = (bc - mu) / sigma

    # Tier assignment
    def tier_quota(z_val):
        if z_val < -1.0:
            return 'LOW'
        if z_val > 1.0:
            return 'HIGH'
        return 'MID'

    tiers = {c: tier_quota(z_val) for c, z_val in zip(classes, z)}

    # Sample within each class
    result = []
    for cls in classes:
        tier_name = tiers[cls]
        quota = quotas[tier_name]
        items = class_items[cls]

        if len(items) == 0:
            continue

        # Popularity-weighted sampling
        weights = np.array([
            max(float(item.get(weight_key, 1)), 1.0) for item in items
        ])
        weights = weights / weights.sum()

        n = min(quota, len(items))
        chosen_idx = rng.choice(len(items), size=n, replace=False, p=weights)
        result.extend([items[i] for i in chosen_idx])

    return result
```

## Domain Examples

### Text corpus by document length

```python
texts = {
    'short': [doc1, doc2, ...],   # 5-50 pages
    'medium': [...],              # 50-500 pages
    'long': [...],                # 500+ pages
}
samples = stratified_quota_sample(
    class_items=texts,
    weight_key='engagement_score',  # citation count, upvote, etc.
)
# Result: balanced subset with natural tier structure preserved
```

### Image dataset by class frequency

```python
images_by_class = {
    'cat': [img1, img2, ...],     # 10K images
    'dog': [...],                 # 5K images
    'bird': [...],                # 500 images (rare)
}
samples = stratified_quota_sample(
    class_items=images_by_class,
    weight_key='quality_score',   # ML model confidence, human rating
)
# Result: ~100-200 total images, balanced across classes by inherent frequency
```

### Entity coverage in hierarchical corpus

```python
entities = {
    'author_1': [doc1, doc2, ...],   # 100 docs (prolific)
    'author_2': [...],                # 20 docs (moderate)
    'author_3': [doc],                # 1 doc (rare)
}
samples = stratified_quota_sample(
    class_items=entities,
    weight_key='novelty_score',   # TF-IDF uniqueness, temporal recency
)
# Result: ensure all authors represented; prolific authors don't drown out rare ones
```

## Key Parameters to Tune

| Parameter | Default | Notes |
|-----------|---------|-------|
| QUOTA_LOW | 5 | Minimum presence for rare classes |
| QUOTA_MID | 8 | Modal tier |
| QUOTA_HIGH | 13 | Ceiling for frequent classes; adjust down if you want more aggressive sublinearity |
| weight_key | None (uniform) | If omitted, sample uniformly within tier; if provided, weight by item quality/relevance |
| seed | 42 | Set to None for fresh draws each run; leave fixed for reproducibility |

## What This Avoids

- ❌ Top-N determinism (always same 10 samples)
- ❌ Uniform random across classes (rare classes drown frequent ones)
- ❌ Per-class independent sampling (ignores global imbalance)
- ❌ Arbitrary hard thresholds (tiers derived from data)

## Anti-Patterns

- Mixing killed/timeout calls into the weight distribution (track only completions)
- Using weight_key on sparse/missing data without a fallback default
- Setting quotas smaller than 1 (defeats the purpose of presence)
- Running without a seed if you need reproducibility

## References

**Box-Cox transformation:**
- Box, G. E. P., & Cox, D. R. (1964). An analysis of transformations.
- SciPy: https://docs.scipy.org/doc/scipy/reference/generated/scipy.stats.boxcox.html

**Stratified sampling:**
- Cochran, W. G. (1977). Sampling Techniques (3rd ed.).
- Neyman allocation: proportional sampling from strata improves variance.

**Fibonacci and golden ratio:**
- Fibonacci ratios naturally appear in growth processes; aesthetically and empirically balanced.
