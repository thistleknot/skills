---
name: mad-dynamic-batching
description: >
  MAD-gated token-aware dynamic batching for ML training data.
  Convert MAD to sigma (×1.4826), filter within 95% CI of median,
  then split the retained data into 4 equal-sized quantile partitions
  per side. Within each partition, anchor-pack batches to target tokens.
  Use when preparing variable-length training data and you need equal
  partition sizes with a robust center-of-distribution gate.
status: active
last_validated: 2026-05-02
---

# MAD Dynamic Batching

## Purpose

Prepare training data for efficient batched training when items have
variable token lengths and the distribution contains outliers. Uses
**MAD (median absolute deviation)** converted to a sigma-equivalent
scale to set a 95% confidence filter, then partitions the retained
data into **equal-sized quantile bands** on each side of the median.

## The Problem

Dynamic batching packs variable-length items into sequences that fill
a token budget. Naive approaches break on heavy-tailed data:

- **Mean ± std** is destroyed by long-tail outliers.
- **Fixed thresholds** are arbitrary.
- **Fixed-width MAD bands** produce unequal partition sizes — the
  center band swells, outer bands starve.

**Solution**: Use MAD as a robust sigma estimator, filter at the 95%
CI, then split the retained data into equal-sized quantile partitions.
This guarantees balanced partition sizes while staying robust to outliers.

## The Algorithm

### 1. Compute median and MAD, convert to sigma

```python
import numpy as np

def robust_stats(values: np.ndarray) -> tuple[float, float, float]:
    """Return (median, MAD, sigma_est) for token counts."""
    med = np.median(values)
    mad = np.median(np.abs(values - med))
    if mad == 0.0:
        mad = 1.0  # degenerate: all same length
    sigma_est = mad * 1.4826  # MAD → sigma conversion (normal dist)
    return med, mad, sigma_est
```

For a normal distribution, `MAD ≈ 0.6745 × sigma`, so multiplying by
`1.4826` recovers sigma. This gives a robust sigma estimate that isn't
skewed by outliers.

### 2. Filter at 95% CI

```python
def filter_95ci(values: np.ndarray, median: float, sigma_est: float) -> np.ndarray:
    """Return indices of items within median ± 1.96 × sigma_est."""
    margin = 1.96 * sigma_est
    lower = median - margin
    upper = median + margin
    return np.where((values >= lower) & (values <= upper))[0]
```

This keeps ~95% of data for near-normal distributions. For heavy-tailed
data, the actual retained fraction will be lower — which is correct,
since the tails are contamination.

### 3. Split retained data into 4 equal-sized quantile partitions per side

```python
def assign_equal_partitions(
    values: np.ndarray,
    retained_idx: np.ndarray,
    median: float,
    n_partitions: int = 4,
) -> dict[int, list[int]]:
    """
    Split retained items into 2×n_partitions equal-sized groups
    centered on the median.

    Returns:
        {partition_id: [item_indices, ...]}
        Negative IDs = below median, positive = above median.
        Each partition has approximately equal count.
    """
    retained_vals = values[retained_idx]

    # Separate below and above median
    below_mask = retained_vals <= median
    above_mask = retained_vals > median

    below_idx = retained_idx[below_mask]
    above_idx = retained_idx[above_mask]

    partitions = {}

    # Split below-median into n_partitions equal groups (sorted ascending)
    below_sorted = below_idx[np.argsort(values[below_idx])]
    below_chunks = np.array_split(below_sorted, n_partitions)
    for i, chunk in enumerate(below_chunks):
        # Partition IDs: -4, -3, -2, -1 (shortest → closest to median)
        partitions[-(n_partitions - i)] = chunk.tolist()

    # Split above-median into n_partitions equal groups (sorted ascending)
    above_sorted = above_idx[np.argsort(values[above_idx])]
    above_chunks = np.array_split(above_sorted, n_partitions)
    for i, chunk in enumerate(above_chunks):
        # Partition IDs: +1, +2, +3, +4 (closest to median → longest)
        partitions[i + 1] = chunk.tolist()

    return partitions
```

**Partition layout** (token count → short to long):

```
-4       -3       -2       -1       |       +1      +2      +3      +4
  ↑                                 |                                 ↑
  shortest (retained)               |               longest (retained)
                                    median
Each partition has ~N/(2×4) items — equal size by construction.
```

### 4. Anchor-pack batches within each partition

Each partition batches independently to a target token budget. Items
are sorted longest-first. A batch starts with the longest remaining
item (the anchor), then selects `n` additional items where
`n × anchor_length` stays just under `target_tokens`.

```python
def batch_with_budget(
    items: list[dict],
    lengths: np.ndarray,
    target_tokens: int = 65536,
    n_partitions: int = 4,
) -> list[list[dict]]:
    """
    Filter at 95% CI, split into equal partitions, anchor-pack each.

    Args:
        items: list of item dicts (must have 'token_count' field)
        lengths: array of token counts
        target_tokens: per-batch token budget
        n_partitions: number of quantile bands per side (default 4)

    Returns:
        list of batches, where each batch is a list of item dicts
    """
    med, mad, sigma_est = robust_stats(lengths)
    retained_idx = filter_95ci(lengths, med, sigma_est)
    partitions = assign_equal_partitions(lengths, retained_idx, med, n_partitions)

    batches = []

    # Process partitions from center outward (highest density first)
    for pid in sorted(partitions.keys(), key=lambda p: abs(p)):
        part_idx = np.array(partitions[pid])
        part_items = [items[i] for i in part_idx]
        part_lens = lengths[part_idx]

        # Sort longest-first for anchor packing
        sorted_order = np.argsort(part_lens)[::-1]
        sorted_items = [part_items[i] for i in sorted_order]
        sorted_lens = part_lens[sorted_order]

        batches.extend(_anchor_pack(sorted_items, sorted_lens, target_tokens))

    return batches


def _anchor_pack(
    items: list,
    lengths: np.ndarray,
    target_tokens: int,
) -> list[list]:
    """
    Longest-first anchor pack within one partition.

    1. Pick the longest remaining item as the anchor.
    2. n = floor((target_tokens - anchor_len) / anchor_len).
    3. Grab the next n unused items (all ≤ anchor by sort order).
    4. Repeat with remaining items.

    Guarantees every batch ≤ target_tokens while maximising fill.
    """
    if len(items) == 0:
        return []

    n_items = len(items)
    used = np.zeros(n_items, dtype=bool)
    batches = []

    for i in range(n_items):
        if used[i]:
            continue

        anchor_len = int(lengths[i])
        remaining_budget = target_tokens - anchor_len

        if remaining_budget <= 0:
            batches.append([items[i]])
            used[i] = True
            continue

        max_n = remaining_budget // anchor_len
        batch = [items[i]]
        batch_tokens = anchor_len
        used[i] = True

        count = 0
        for j in range(i + 1, n_items):
            if used[j] or count >= max_n:
                continue
            if batch_tokens + int(lengths[j]) <= target_tokens:
                batch.append(items[j])
                batch_tokens += int(lengths[j])
                used[j] = True
                count += 1

        batches.append(batch)

    return batches
```

## Why MAD → Sigma, Not Raw MAD

| Approach | Partition sizes | Robust to outliers? |
|----------|----------------|-------------------|
| Mean ± std | Unequal (skewed by outliers) | No |
| Fixed MAD bands (±1, ±2, ±3, ±4) | Unequal (density varies) | Yes |
| **MAD → sigma → quantiles** | **Equal by construction** | **Yes** |

The MAD-to-sigma conversion (`×1.4826`) gives a robust scale estimate.
The 95% CI filter removes contamination. The quantile split guarantees
equal partition sizes regardless of the underlying density shape.

## Parameter Tuning

| Parameter | Default | Range | When to change |
|-----------|---------|-------|----------------|
| `ci_level` | 0.95 (1.96σ) | 0.90–0.99 | Lower = wider filter (more items); higher = stricter |
| `n_partitions` | 4 per side | 2–8 | More = finer granularity; fewer = coarser but larger batches |
| `target_tokens` | 65536 | Model-dependent | Set to model's max sequence length or smaller |

## Usage

```python
items = load_training_data()
lengths = np.array([it['token_count'] for it in items])

batches = batch_with_budget(items, lengths, target_tokens=65536)

# Inspect partition balance
from collections import Counter
# Each partition had equal item count by construction
```

## Anti-Patterns

- Using mean ± std on heavy-tailed data (outliers destroy the center)
- Fixed-width MAD bands when you need equal partition sizes
- Ignoring the filtered-out tail — inspect what was dropped; if >10%,
  the distribution may need preprocessing (truncation, separate handling)
- Setting `n_partitions` too high for small datasets (partitions < 10
  items each → anchor packing degrades)

## References

- Iglewicz & Hoaglin (1993). *How to Detect and Handle Outliers*.
- MAD → sigma conversion: `sigma ≈ MAD × 1.4826` for normal distributions.
- 95% CI: `median ± 1.96 × sigma_est`
