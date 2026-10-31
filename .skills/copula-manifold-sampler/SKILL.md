---
name: copula-manifold-sampler
description: "Multi-dimensional class-balanced training sampler that tracks a joint manifold of (dataset × answer_type × token_length_quantile × score_bucket) with cumulative delta-ratio correction across epochs. Integrates token-budget bin packing with dynamic routing. For RL adds score diversity as a 4th axis. Maintains randomness as the equalizer between draws."
---

# Copula Manifold Sampler

## What It Is

A unified sampling and batching system for LLM training that maintains class balance across a multi-dimensional manifold while respecting hardware (VRAM) constraints. It combines:

1. **Delta-ratio deficit-driven sampling** — draws records from the most underrepresented cell
2. **Token-budget bin packing** — routes records into VRAM-efficient bins by length
3. **Cumulative cross-epoch correction** — deficits persist across epochs so nothing gets permanently shorted
4. **Score-diversity axis for RL** — adds reward distribution as a balancing dimension during GRPO

## The Manifold

### SFT (3 axes, up to 96 cells):
```
Axis 1: Dataset (6)       — Agentic, Code, Instruction, Math, ReadingComp, STEM
Axis 2: Answer Type (4)   — R1, R2, R3, R4
Axis 3: Token Length (4)  — Q1 (short), Q2 (medium), Q3 (long), Q4 (very long)
```

### RL (4 axes, up to 480 cells):
```
Axis 1: Dataset (6)       — same
Axis 2: Answer Type (4)   — same
Axis 3: Token Length (4)  — same
Axis 4: Score Bucket (5)  — [0.0-0.2), [0.2-0.4), [0.4-0.6), [0.6-0.8), [0.8-1.0]
```

Not all cells are populated (structurally empty cells like R1|Code don't exist in the data). Empty cells are NaN — ignored in deficit calculations.

## Target Proportions

Each POPULATED cell has a target proportion derived from:
1. Start with raw pool counts per (dataset, answer_type) cell
2. Apply Box-Cox transform → z-score → norm.cdf → normalize to sum=1
3. These are the 2D (dataset × answer_type) base ratios
4. Within each 2D cell, the length quantile targets are UNIFORM (25% each)
5. For RL, the score bucket targets are also UNIFORM within each 3D cell

This means: class balance is enforced at the (dataset × answer_type) level via Box-Cox CDF, and WITHIN each class the length/score distributions are kept uniform.

## Algorithm: Delta-Ratio Stream + Bin Packing

```python
class CopulaManifoldSampler:
    def __init__(self, pool, ratios, target_tokens, n_bins=4):
        self.pool = pool
        self.ratios = ratios              # Box-Cox CDF target proportions per 2D cell
        self.target_tokens = target_tokens
        self.n_bins = n_bins
        
        # Cumulative state — PERSISTS across epochs, never resets
        self.cumulative_counts = defaultdict(int)  # {(dataset, answer_type, len_q): count}
        self.cumulative_drawn = 0
        self.used_ids = set()             # tracks what's been seen (for without-replacement within epoch)
    
    def sample_epoch(self, epoch_seed):
        """Sample one epoch's worth of bins. Returns list of bins (each bin = one training step)."""
        rng = Random(epoch_seed)
        bins = [[] for _ in range(self.n_bins)]
        bin_max_lens = [0] * self.n_bins
        bin_closed = [False] * self.n_bins
        epoch_used = set()  # within-epoch no-replacement
        
        while not all(bin_closed):
            # 1. Compute deficit across ALL manifold cells
            deficits = {}
            for cell in self.get_populated_cells():
                target = self.ratios[cell[:2]] * (self.cumulative_drawn + 1) / len(self.get_len_quantiles())
                deficit = target - self.cumulative_counts[cell]
                # Only consider cells with available records
                if self.has_available(cell, epoch_used):
                    deficits[cell] = max(deficit, 0)
            
            if not deficits or sum(deficits.values()) <= 0:
                break
            
            # 2. Draw from highest-deficit cell (with randomness as tiebreaker)
            # Stochastic: sample proportional to deficits (not pure argmax)
            total_deficit = sum(deficits.values())
            weights = {cell: d / total_deficit for cell, d in deficits.items()}
            chosen_cell = rng.choices(list(weights.keys()), weights=list(weights.values()), k=1)[0]
            
            # 3. Pick a random record from that cell
            record = self.draw_random(chosen_cell, epoch_used, rng)
            rec_len = len(record['input_ids'])
            
            # 4. Route to best-fit open bin
            placed = False
            for i in range(self.n_bins):
                if bin_closed[i]:
                    continue
                new_max = max(bin_max_lens[i], rec_len)
                if (len(bins[i]) + 1) * new_max <= self.target_tokens:
                    bins[i].append(record)
                    bin_max_lens[i] = new_max
                    placed = True
                    break
            
            if not placed:
                # Record doesn't fit anywhere — skip it, deficit remains for next epoch
                continue
            
            # 5. Update cumulative state
            epoch_used.add(record['id'])
            self.cumulative_counts[chosen_cell] += 1
            self.cumulative_drawn += 1
            
            # 6. Check bin closure
            for i in range(self.n_bins):
                if not bin_closed[i] and (len(bins[i]) + 1) * bin_max_lens[i] > self.target_tokens:
                    bin_closed[i] = True
        
        return [b for b in bins if b]  # return non-empty bins
```

## Key Properties

### Cumulative Correction
- `cumulative_counts` NEVER resets between epochs
- If R4|Code got shorted in epoch 1 (bin couldn't fit its long prompt), epoch 2's first draws will prioritize R4|Code
- Over N epochs, every cell converges to its target ratio regardless of per-epoch bin routing variance
- Self-correcting without explicit compensation logic

### Randomness as Equalizer
- Within the deficit-weighted draw, ties are broken randomly
- The `rng.choices(weights)` call is STOCHASTIC — highest deficit gets drawn MOST OFTEN but not ALWAYS
- This prevents deterministic sequences (always the same cell order) which could create batch-level correlations
- Different seed per epoch ensures different draw sequences

### Score Dimension (RL only)
For RL, after round 1 each prompt has reward scores from G=4 rollouts:
- Bucket scores at 0.05 precision
- Count frequency per bucket
- The "score_bucket" axis in the manifold = which 0.2-wide band the prompt's MEAN score falls in
- Target: UNIFORM across score bands (uncertain prompts get same representation as easy/hard ones)
- This prevents the maxent selection from ONLY picking uncertain items and starving the confident ones

### Token Length Quantile Assignment
Before sampling begins:
1. Compute token lengths for all records in pool
2. Determine quartile boundaries: Q1=[0, p25], Q2=(p25, p50], Q3=(p50, p75], Q4=(p75, max_len]
3. Each record gets a length_quantile label (Q1-Q4)
4. Target within each (dataset, answer_type) cell: 25% per length quantile

### Bin Routing Logic
- Bins are ordered short→long (bin 0 gets short records first)
- A record goes to the FIRST open bin that can accommodate it
- Because records are drawn in deficit-priority order (not length order), bins fill with mixed lengths
- But the `(len + 1) * new_max ≤ budget` constraint naturally clusters similar lengths together
- Long records that make bin_max jump will only go in bins that are still nearly empty

## Configuration

| Parameter | SFT Default | RL Default | Meaning |
|-----------|-------------|------------|---------|
| `target_tokens` | 896 | 896 // G = 224 | VRAM budget per bin |
| `n_bins` | 4 | 4 | Steps per epoch (= bins filled before eval) |
| `max_len` | 512 | 512 (prompt only) | Hard ceiling, filter before sampling |
| `ratios` | Box-Cox CDF | Same + score axis | Target proportions per manifold cell |
| `len_quantiles` | 4 (quartiles) | 4 | How many length buckets |
| `score_buckets` | N/A | 5 (0.2 bands) | RL only: reward score diversity bands |

## Eval Strategy: Stratified Split Scoring

To cut eval time from 8 min (62 items) to ~1.5 min per checkpoint:

1. Split the 62-item eval set into 3 stratified subsets of ~21 each (one per epoch)
2. Within each epoch subset, split into 2 halves (~10 + ~11)
3. Score half 1 at mid-epoch, half 2 at epoch end
4. Full epoch score = union of both halves (21 items)
5. Full training score = union of all 3 epoch subsets (62 items)
6. Each epoch's subset is different but all drawn stratified-uniform from the same 62 (min class=1 per epoch guaranteed)
7. The subsets don't change between trials — same eval instrument per epoch across all lr trials

This preserves the full 62-item coverage over the complete run while making each individual eval 3× faster.

### Split Construction
```python
# Pre-split eval into 3 epoch groups, stratified so each group has ≥1 from every populated cell
eval_groups = stratified_split(eval_set, n_groups=3, min_per_cell=1)
# Each group further split into 2 halves for mid/end eval
for group in eval_groups:
    group.mid_half = group[:len(group)//2]
    group.end_half = group[len(group)//2:]
```

| Old Component | Replaced By |
|---|---|
| `bootstrap_cohort()` in mgpo.py | CopulaManifoldSampler.sample_epoch() |
| `stratified_sample()` in stratify.py | Same |
| `continuation_probabilities()` in mgpo.py | Score-axis deficit in the manifold |
| 4-block quantile split in vibe_sft.py | Bin packing within sample_epoch() |
| `calculate_allocations()` for batch sizing | Emergent from bin closure |
| Fixed `TARGET_EFF_BATCH` | Eliminated — batch = bin size, determined by target_tokens |

## Training Loop Integration

### SFT
```python
sampler = CopulaManifoldSampler(pool, ratios, target_tokens=896, n_bins=4)
for epoch in range(epochs):
    bins = sampler.sample_epoch(seed=base_seed + epoch)
    for bin_records in bins:
        train_one_step(model, bin_records)  # pad to bin_max, forward+backward+step
    score = eval(model, eval_set)
    if score < prev_score: break  # patience=0
```

### RL
```python
sampler = CopulaManifoldSampler(pool, ratios, target_tokens=224, n_bins=4)  # budget/G
# After round 1: add score axis
sampler.add_score_axis(reward_history, n_buckets=5)
for round in range(rounds):
    bins = sampler.sample_epoch(seed=base_seed + round)
    for bin_records in bins:
        grpo_step(model, bin_records, G=4)  # TRL generates G completions per prompt
    score = eval(model, eval_set)
```

## Observability

Every epoch prints:
```
[manifold] epoch=2 drawn=47 | cell deficits:
  R1|Agentic|Q1: target=4.2 actual=4 (deficit=0.2)
  R4|Code|Q3:    target=2.1 actual=1 (deficit=1.1) ← PRIORITY NEXT EPOCH
  ...
[bins] 4 bins: sizes=[9, 6, 3, 2] max_lens=[93, 139, 263, 448]
```

Plus the full cross-hatch grid at eval time showing per-cell performance.
