---
name: stratified-quota-sampling
description: Stratify a long-tailed dataset by normalizing raw counts via Box-Cox (or Yeo-Johnson for zero-containing data), bin into tiers at standard deviation cutoffs, then allocate quotas per tier. Never log-then-Box-Cox (redundant — Box-Cox contains log at lambda=0). Check dimension correlation via Cramer's V before multi-axis stratification. Allocate over cross-product cells, not per-dimension.
status: active
last_validated: 2026-08-10
---

# Stratified Quota-Proportional Sampling

## Purpose

Balance imbalanced datasets by:
1. **Normalizing** raw class counts via Box-Cox (or Yeo-Johnson) to near-normality
2. **Binning** into natural tiers at standard deviation cutoffs
3. **Allocating quotas** proportional to tier structure
4. **Sampling within tiers** using a per-item relevance weight

This prevents both **under-sampling** of rare classes and **over-sampling** of frequent ones, while respecting the empirical distribution shape.

## When to Use

- Imbalanced class frequencies (text length distributions, image classes, sparse entities)
- Multi-dimensional stratification (regime x dataset x answer_type)
- Any domain where you need balanced representation without flooding on frequent classes

## The Trick

Box-Cox finds the optimal power lambda to bring a right-tailed distribution toward normal:

```
Box-Cox: y(lambda) = (x^lambda - 1) / lambda    (lambda != 0)
                   = log(x)                       (lambda = 0)
```

That's it. One transform, one fitted parameter, the distribution is now approximately normal and you can bin on z-scores meaningfully.

**Never log-then-Box-Cox** — Box-Cox already contains log as its lambda=0 case. Applying log first means Box-Cox is fitting a lambda to already-compressed data. That's double-compression with an uninterpretable parameter.

**Yeo-Johnson** when counts contain zeros (Box-Cox requires strictly positive):

```
Yeo-Johnson: handles x <= 0 via a piecewise extension
```

Pick one:
- Counts are always >= 1? → Box-Cox
- Counts can be 0? → Yeo-Johnson

## The Approach

### 1. Transform via Box-Cox

```python
from scipy.stats import boxcox
import numpy as np

counts = np.array([len(class_items[c]) for c in classes], dtype=float)
# Box-Cox requires strictly positive
bc, lam = boxcox(counts)  # lam is fitted to THIS distribution
```

### 2. Standardize to z-scores

```python
mu, sigma = bc.mean(), bc.std(ddof=0)
z = (bc - mu) / sigma
```

### 3. Bin into tiers

```python
def assign_tier(z_val):
    if z_val < -1.0:
        return "LOW"    # rare classes (below -1 sigma)
    elif z_val > 1.0:
        return "HIGH"   # frequent classes (above +1 sigma)
    else:
        return "MID"    # bulk of distribution
```

### 4. Allocate quotas per tier

Fibonacci ratios (5/8/13) or any monotone allocation that gives more budget to the middle where most classes live:

```python
TIER_QUOTAS = {"LOW": 5, "MID": 8, "HIGH": 13}
# Normalize to budget
total_ratio = sum(TIER_QUOTAS.values())
tier_budgets = {t: int(budget * q / total_ratio) for t, q in TIER_QUOTAS.items()}
```

### 5. Sample within tiers using relevance weight

```python
for tier, tier_classes in grouped_by_tier.items():
    tier_budget = tier_budgets[tier]
    per_class = tier_budget // len(tier_classes)
    for cls in tier_classes:
        pool = class_items[cls]
        weights = np.array([item[weight_key] for item in pool])
        weights /= weights.sum()
        sampled = rng.choice(pool, size=min(per_class, len(pool)), replace=False, p=weights)
```

## Multi-Dimension: Allocate Over Cells, Not Dimensions

If doc_type x model x classification all matter, the strata are the **nonempty cells** of that cross-product:

```python
cells = df.groupby(['doc_type', 'model', 'classification']).size().reset_index(name='count')
# Apply Box-Cox to cell counts, then tier/allocate
bc_cells, lam = boxcox(cells['count'].values.astype(float))
```

Do NOT allocate per-dimension and multiply — correlated dimensions will misallocate.

## Check Dimension Correlation First

Before stratifying on multiple dimensions, verify they're not redundant:

```python
from scipy.stats import chi2_contingency
import numpy as np

def cramers_v(dim_a, dim_b):
    """Cramer's V: association strength between two categorical variables."""
    ct = pd.crosstab(dim_a, dim_b)
    chi2 = chi2_contingency(ct)[0]
    n = ct.values.sum()
    r, c = ct.shape
    return np.sqrt(chi2 / (n * (min(r, c) - 1)))
```

Decision rules:
- V < 0.1: dimensions independent — cell allocation costs nothing extra
- V > 0.3: per-dimension multiplication would misallocate — cell-based is mandatory
- V near 1.0: one dimension is redundant — drop it, cut cell count for free

For small expected cell counts (< 5), use NMI instead:
```python
from sklearn.metrics import normalized_mutual_info_score
nmi = normalized_mutual_info_score(df['doc_type'], df['model'])
```

## Per-Cell Floor

Never let a cell drop below a useful sample size:

```python
allocs = np.maximum(allocs, floor)  # floor=50 for stats, floor=1 for pure coverage
```

Then renormalize by trimming from the largest cells.

## Implementation Template

```python
import numpy as np
import pandas as pd
from scipy.stats import boxcox, yeojohnson

def stratified_quota_sample(
    df: pd.DataFrame,
    strat_cols: list[str],
    budget: int,
    floor: int = 50,
    weight_col: str = None,
    seed: int = 42,
    allow_zeros: bool = False,
) -> pd.DataFrame:
    """Sample from df using Box-Cox tier allocation over cross-product cells."""
    rng = np.random.default_rng(seed)
    
    # Cross-product cells
    cells = df.groupby(strat_cols).size().reset_index(name='_count')
    counts = cells['_count'].values.astype(float)
    
    # Transform to normality
    if allow_zeros or (counts.min() <= 0):
        bc, lam = yeojohnson(counts)
    else:
        bc, lam = boxcox(counts)
    
    # Z-score and tier
    mu, sigma = bc.mean(), bc.std(ddof=0)
    if sigma == 0:
        # All cells same size — uniform allocation
        allocs = np.full(len(counts), budget // len(counts))
    else:
        z = (bc - mu) / sigma
        # Allocation proportional to position in transformed space
        # Shift z to positive, then allocate
        shifted = z - z.min() + 1.0
        shares = shifted / shifted.sum()
        allocs = np.maximum((shares * budget).astype(int), floor)
    
    # Cap at available pool size
    allocs = np.minimum(allocs, counts.astype(int))
    
    # Renormalize if over budget
    while allocs.sum() > budget:
        excess_idx = (allocs - floor).argmax()
        allocs[excess_idx] -= 1
    
    # Sample within each cell
    sampled = []
    for i, row in cells.iterrows():
        mask = pd.Series(True, index=df.index)
        for col in strat_cols:
            mask &= (df[col] == row[col])
        pool = df[mask]
        n = min(int(allocs[i]), len(pool))
        if n == 0:
            continue
        if weight_col and weight_col in pool.columns:
            weights = pool[weight_col].values.astype(float)
            weights /= weights.sum()
            idx = rng.choice(pool.index, size=n, replace=False, p=weights)
        else:
            idx = rng.choice(pool.index, size=n, replace=False)
        sampled.append(pool.loc[idx])
    
    return pd.concat(sampled, ignore_index=True)
```

## Anti-Patterns

- **Log-then-Box-Cox**: redundant. Box-Cox contains log at lambda=0. Never pre-transform.
- **Per-dimension allocation multiplied**: misallocates when dimensions are correlated. Always allocate over cross-product cells.
- **Collapsing a required axis**: if the spec defines N axes, implement N axes. Volume coverage != constructive coverage.
- **No floor**: cells below ~50 samples are useless for stats. Always floor.
- **Fitting lambda per-batch**: fit once on the full population counts, then reuse. Don't refit inside a sampling loop.

## Relation to Other Skills

- **cross-hatch-sampling**: applies allocation hierarchically (regime first, source second). Uses fixed lam=0.5 in its Box-Cox call.
- **class-balancing**: operates at the training-batch level AFTER sampling decides what to include.
- **bm25-corpus-sampling**: uses this for index-warming allocations across doc_type strata.
- **stat-partitioning**: describes the general partition/transform toolkit including Box-Cox.

## References

- Box, G. E. P., & Cox, D. R. (1964). An analysis of transformations.
- Yeo, I.-K., & Johnson, R. A. (2000). A new family of power transformations.
- Cochran, W. G. (1977). Sampling Techniques (3rd ed.).
- Cramer, H. (1946). Mathematical Methods of Statistics.
- SciPy: https://docs.scipy.org/doc/scipy/reference/generated/scipy.stats.boxcox.html
