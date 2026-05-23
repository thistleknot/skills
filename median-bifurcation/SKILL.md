---
name: median-bifurcation
description: >
  Universal pattern for splitting any problem space along median boundaries
  to create discriminative signal. Choose a partition axis, produce both
  sides explicitly, drop the unwanted half at inference. Applied recursively,
  n bifurcations yield 2^n epistemic cells at zero additional labeling cost.
  Use when you need contrastive pressure in training data, even cluster splits,
  or dimension reduction via ranked median cuts. Inspired by ANOVA and
  k-means via medians.
status: active
last_validated: 2026-05-17
---

# Median Bifurcation

**Trigger question:** "Do I have a principled way to create both sides of a distinction,
or am I only generating positive examples?"

---

## Core Pattern

Every useful distinction a model or system must learn is a binary median cut.
Positive-only inputs collapse to pattern-matching with no discriminative pressure —
the model learns what the target looks like but not what it excludes.

**Three steps:**

1. **Choose the partition axis** — the dimension along which the split is meaningful
   (entailed / non-entailed, observed / inferred, relevant / irrelevant, above / below threshold).
2. **Produce both sides explicitly** — the negative is a hard negative baked in, not mined post-hoc.
3. **At inference / downstream use, drop the unwanted partition** — the model or system
   learned the boundary through contrast; only one side is needed at runtime.

The cut point is the **median** (or a robust equivalent) because:
- The median is breakdown-point ½ — immune to 49% contamination
- It guarantees equal-sized partitions, which eliminates class-imbalance drift
- It is parameter-free and distribution-agnostic

---

## Recursive Extension

Applied recursively, two orthogonal bifurcations yield **four cells** with no
additional labeling cost:

| | observed | inferred |
|---|---|---|
| **entailed** | entailed × observed | entailed × inferred |
| **non-entailed** | non-entailed × observed | non-entailed × inferred |

Each cell is a distinct epistemic class. Three bifurcations → 8 cells. The cost
scales as O(n axes), the resolution scales as O(2^n).

This is the same principle as **contrastive learning** but applied at the
supervised data level rather than the loss level. The loss sees normal
cross-entropy; the discriminative pressure is already baked into the data.

---

## Domain Instantiations

### 1. Transformer / Reasoning Model Training (SPO)

**Axis:** entailment — does this premise load-bear the throughline (conclusion)?

```python
def bifurcate_premises(premises: list[Triplet], throughline: str) -> dict:
    """
    Split premises into entailed / non-entailed relative to a throughline.
    Both partitions are included in the training target.
    At inference, only the entailed partition is emitted.
    """
    entailed     = [p for p in premises if load_bears(p, throughline)]
    non_entailed = [p for p in premises if not load_bears(p, throughline)]
    return {"entailed": entailed, "non_entailed": non_entailed}
```

A premise is entailed if and only if it load-bears that specific throughline —
not exhaustive extraction, but discriminative extraction under a chosen frame.
The throughline (syllogism / conclusion) is the anchor.

### 2. Feature Engineering / Clustering

**Axis:** any continuous variable — split at the median to create balanced binary features.

```python
import numpy as np

def median_bifurcate(values: np.ndarray, labels=None) -> tuple[np.ndarray, np.ndarray]:
    """
    Split array at median into below / above halves.
    Returns (below_mask, above_mask). Equal sizes guaranteed for even n.
    Optional labels array split in parallel.
    """
    med = np.median(values)
    below = values <= med
    above = values > med
    return below, above
```

Applied across k factors simultaneously → k-dimensional cell assignment →
natural cluster derivation without iterative k-means convergence.

### 3. Dynamic Batching (see `mad-dynamic-batching`)

**Axis:** token length — split at the median of the MAD-filtered distribution.

Negative IDs signal below-median; positive IDs signal above-median.
Each side is partitioned into `n` equal quantile bands for anchor-pack batching.
This is the same pattern: the split creates homogeneous groups without discarding data.

### 4. ANOVA-style Factor Analysis

**Axis:** treatment levels — split continuous treatment at the median to create
a binary factor, then test interaction effects across crossed bifurcations.

The median cut is the minimum-cost way to produce balanced cells for a factorial design.

---

## Relationship to Contrastive Learning

| Approach | Where contrast lives | Cost |
|---|---|---|
| Contrastive loss (SimCLR, triplet) | Loss function; requires negative mining | Negative mining at training time |
| **Median bifurcation** | Training data; negatives baked in | Zero — negatives are produced at data-prep time |
| Standard cross-entropy | None — positives only | Discriminative signal absent |

Median bifurcation is **data-level contrastive learning**. The loss is ordinary
cross-entropy; the boundary pressure comes from the data layout.

---

## When NOT to Use This

- When the natural data distribution is already maximally contrastive (e.g., binary labels are given)
- When the partition axis is meaningless for the task (don't bifurcate for bifurcation's sake)
- When you need >2 splits and the axes are not orthogonal — use stratified sampling instead

---

## Related Skills

- `mad-dynamic-batching` — applies this pattern to token-length distributions for batching
- `stratified-quota-sampling` — quota-based stratified splits across multiple strata
- `class-balancing` — handles imbalance that arises *after* a split

<!-- consolidation:see-also:start -->
## See Also
[[continual-learning]]  [[continuity-log]]  [[program-synthesis]]
<!-- consolidation:see-also:end -->
