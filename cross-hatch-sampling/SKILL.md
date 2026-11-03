---
name: cross-hatch-sampling
description: >
  Two-axis class-balanced batch construction that projects dataset source (Y)
  and answer type (X) simultaneously to express the full latent representation
  across training batches. Uses MMR-style deficit-driven selection: each draw
  goes to the (regime, source) cell furthest below its target ratio, ensuring
  convergence on both axes without maintaining separate trackers. Use when
  constructing RL/SFT batches that must cover all answer-type behaviors without
  lopsided F1, sizing HPO batches small enough for bounded trials while
  guaranteeing regime representation, or selecting few-shot exemplars that cover
  answer formats AND dataset diversity simultaneously. Trigger on "class balance
  my batch", "regime coverage", "answer type sampling", "two-axis MMR",
  "cross-hatch", or "lopsided F1 from unbalanced batches".
---

# Cross-Hatch Sampling

## Description

Two-axis class-balanced batch construction that projects dataset source (Y) and answer type (X) simultaneously to express the full latent representation across training batches. Uses MMR-style deficit-driven selection: each draw goes to the (regime, source) cell furthest below its target ratio, ensuring convergence on both axes without maintaining separate trackers.

## When to Use

- Constructing RL/SFT training batches that must cover all answer-type behaviors (abstain, answer-with-context, answer-without-context) without lopsided F1
- Sizing HPO batches small enough for bounded trials while guaranteeing every regime is represented
- Scaling from HPO (n=9) to production (n=200) without changing the sampling mechanism — only batch count grows
- Selecting few-shot exemplars that cover answer formats AND dataset diversity simultaneously
- Any scenario where two categorical axes must be balanced jointly and the rarest class determines the epoch boundary

## Mechanism

### The Two Axes

```
X-axis (answer type / regime):
  R1: context + answerable
  R2: context + unanswerable (abstain)
  R3: no context + answerable
  R4: no context + unanswerable (abstain)

Y-axis (dataset source within regime):
  R1 sources: SQuAD answerable, HotpotQA, domain synthetic R1
  R2 sources: SQuAD unanswerable, domain synthetic R2
  R3 sources: Dolly, SciQ, glaive, domain synthetic R3
  R4 sources: synthetic impossible, domain synthetic R4
```

### Selection Formula

```
weight(regime_r, source_s) ∝ (target_ratio_r - current_ratio_r) × (target_ratio_s|r - current_ratio_s|r)
```

Pick the cell with the highest combined deficit. Ties broken by pool size (larger pool preferred for diversity).

### Sizing via Power Allocation

Given k regimes with pool sizes, use `power_allocate(sizes, n, alpha=0.5)` to determine per-regime targets. This is square-root allocation (alpha=0.5): share_k = n_k^0.5 / sum(n_j^0.5). The (min, max) band constrains valid cohort sizes:

| band (min, max per regime) | valid n range (4 regimes, this pool) |
|---|---|
| (1, 1) | n=4 |
| (1, 2) | n=4–7 |
| (1, 3) | n=4–9 |
| (2, 3) | no solution (skew too large) |

### Epoch Length from Rarest Class

```
epoch_batches = unique_records_in_rarest_regime // records_per_batch_from_that_regime
```

For this corpus: 80 unique R4 // 2 per batch = 40 batches per epoch without repetition.

### Repetition Policy

Sample WITHOUT replacement until a regime is exhausted within an epoch. Once exhausted, switch to WITH replacement for that regime only. Under stochastic generation (temp=1.0, top_p=0.95), repeated prompts produce different completions → fresh reward variance → gradient signal preserved.

### Rotation Between Batches

Each internal batch draws a FRESH n-record sample via the two-axis MMR mechanism. No batch reuses the prior batch's records. This mimics production where the pool is consumed in class-balanced slices.

## Properties

- Every regime appears before any regime doubles (X-axis convergence)
- Every source within a regime appears before any source doubles (Y-axis convergence)
- New dataset sources (e.g., domain synthetic) arrive with ratio 0 → selected immediately
- Same `calculate_allocations` machinery as all other stratification in the pipeline
- Scales from HPO (n=9) to production (n=200) by increasing batch count, not changing the mechanism
- The rarest class sets the global epoch boundary — prevents exhaustion-induced distribution shift

## Why "Cross-Hatch"

The name comes from the visual: if you draw the regime axis horizontally and dataset source vertically, the sampling pattern fills the grid like cross-hatching — alternating strokes on each axis until coverage is uniform. The projection onto either axis alone shows balanced representation; the joint pattern shows source diversity within each answer type.

## Relation to Prior Art

- **Power-allocated stratified sampling** (`stratified-quota-sampling` skill): the underlying allocation mechanism. Cross-hatch applies it hierarchically (regime first, source second).
- **MMR (Maximal Marginal Relevance)**: the deficit-driven selection principle. Cross-hatch extends MMR from relevance-diversity tradeoff to class-balance-source-balance tradeoff.
- **Length-quantile batching** (`length_partition.py`): operates AFTER cross-hatch draws the records. Cross-hatch decides WHAT to train on; quantile batching decides HOW to pad it efficiently.

## Code Pattern

```python
def cross_hatch_draw(pool, n, regime_targets, source_targets, rng, seen=None):
    """Draw n records with two-axis MMR class balance.
    
    regime_targets: dict regime -> target count (from calculate_allocations)
    source_targets: dict (regime, source) -> target count
    seen: set of already-drawn ptext IDs (for without-replacement within epoch)
    """
    seen = seen or set()
    selected = []
    regime_counts = {r: 0 for r in regime_targets}
    source_counts = {k: 0 for k in source_targets}
    
    for _ in range(n):
        # X-axis: regime with largest deficit
        regime_deficit = {r: regime_targets[r] - regime_counts[r] for r in regime_targets}
        target_regime = max(regime_deficit, key=regime_deficit.get)
        
        # Y-axis: source within that regime with largest deficit
        eligible_sources = {k: source_targets[k] - source_counts[k] 
                          for k in source_targets if k[0] == target_regime}
        target_source = max(eligible_sources, key=eligible_sources.get)
        
        # Draw from that (regime, source) cell
        candidates = [r for r in pool 
                     if regime_of(r) == target_regime 
                     and r.get("source") == target_source[1]
                     and r["ptext"] not in seen]
        if not candidates:
            # Fallback: any record from target_regime not yet seen
            candidates = [r for r in pool 
                         if regime_of(r) == target_regime and r["ptext"] not in seen]
        if not candidates:
            # Exhaustion: sample with replacement
            candidates = [r for r in pool if regime_of(r) == target_regime]
        
        record = rng.choice(candidates)
        selected.append(record)
        seen.add(record["ptext"])
        regime_counts[target_regime] += 1
        source_counts[target_source] += 1
    
    return selected
```

## Provenance

Operator design decision 2026-08-10. Motivated by:
1. The all-R4 cohort failure (n=5 without regime stratification → zero gradient)
2. The (1,3) sizing analysis showing n=9 is sufficient for 4-regime coverage
3. The two-axis MMR memory entry for few-shot selection (same principle, different granularity)
4. The macro-F1 lopsidedness diagnosis (training dominated by R3 → precision on abstention lags)
