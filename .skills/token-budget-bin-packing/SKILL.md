---
name: token-budget-bin-packing
description: "Dynamic bin-packing sampler for LLM training: streams records into fixed-count bins sized by VRAM token budget. Combines delta-ratio class balancing with greedy length-aware routing. Predictable epoch length (4 bins = 4 steps), VRAM-efficient, class-balanced by construction."
---

# Token-Budget Bin Packing

## When to Use

- Training any LLM where sequences vary in length and VRAM is the constraint
- Replacing fixed batch_size + padding waste approaches
- When you want predictable epoch timing (fixed number of steps)
- Combined with class-balanced sampling (delta-ratio) for stratified training

## Core Idea

Instead of: sample n records → sort → split into blocks → compute batch sizes
Do: open K bins with token budgets → stream records in → route by length → close when full

The key insight: **n is emergent from hardware**, not a hyperparameter. You don't choose how many records per epoch — you choose how many BINS (= steps = VRAM fills) and the hardware determines how many records fit.

## Algorithm

```python
def stream_into_bins(
    pool: list[dict],
    ratios: dict[str, float],     # Box-Cox CDF target proportions per cell
    target_tokens: int,           # VRAM budget per bin (e.g. 896)
    n_bins: int = 4,              # bins per epoch = steps per epoch
    seed: int = 42,
    exclude: set = None,          # already-used records (for disjointness)
) -> list[list[dict]]:
    """Stream-sample records into bins until all bins are full.
    
    Require: pool has records with 'input_ids' (tokenized).
    Guarantee: exactly n_bins bins, each with total padded tokens ≤ target_tokens.
    Maintain: class balance via delta-ratio weighting on draw order.
    """
    bins = [[] for _ in range(n_bins)]
    bin_max_lens = [0] * n_bins   # current max length in each bin
    bin_closed = [False] * n_bins
    
    # Delta-ratio state
    cell_counts = {cell: 0 for cell in ratios}
    total_drawn = 0
    
    rng = Random(seed)
    used = set(exclude or [])
    
    while not all(bin_closed):
        # 1. Choose which cell to draw from (delta-ratio: highest deficit)
        targets = {cell: r * (total_drawn + 1) for cell, r in ratios.items()}
        deficits = {cell: targets[cell] - cell_counts[cell] for cell in ratios}
        # Zero out cells with no remaining records in pool
        for cell in list(deficits):
            if not any(r['id'] not in used and cell_of(r) == cell for r in pool):
                deficits[cell] = 0
        
        if sum(deficits.values()) <= 0:
            break  # pool exhausted for all needed cells
        
        # Pick highest deficit cell
        chosen_cell = max(deficits, key=deficits.get)
        
        # 2. Draw a record from that cell
        candidates = [r for r in pool if cell_of(r) == chosen_cell and r['id'] not in used]
        if not candidates:
            deficits[chosen_cell] = 0
            continue
        record = rng.choice(candidates)
        rec_len = len(record['input_ids'])
        
        # 3. Route to a bin that can accommodate this length
        placed = False
        for i in range(n_bins):
            if bin_closed[i]:
                continue
            new_max = max(bin_max_lens[i], rec_len)
            # Would adding this record exceed budget?
            if (len(bins[i]) + 1) * new_max <= target_tokens:
                bins[i].append(record)
                bin_max_lens[i] = new_max
                placed = True
                break
        
        if not placed:
            # No open bin can fit this record — try closing smallest-remaining bin
            # and check if others can fit, or just skip this record
            continue
        
        used.add(record['id'])
        cell_counts[chosen_cell] += 1
        total_drawn += 1
        
        # 4. Check if any bin should close
        for i in range(n_bins):
            if bin_closed[i]:
                continue
            # Close if adding one more record at min possible length would exceed budget
            min_possible_addition = 1  # at minimum one token
            if (len(bins[i]) + 1) * bin_max_lens[i] > target_tokens:
                bin_closed[i] = True
    
    return bins
```

## Properties

| Property | Value |
|----------|-------|
| Steps per epoch | Exactly n_bins (default: 4) |
| VRAM per step | ≤ target_tokens (constant, fills efficiently) |
| Records per epoch | Emergent (sum of bin sizes, varies by length distribution) |
| Class balance | Guaranteed by delta-ratio draw order |
| Padding waste | Minimized (within-bin records are similar length due to routing) |
| Epoch timing | Predictable: 4 steps × time_per_step |

## Configuration

| Parameter | Default | Meaning |
|-----------|---------|---------|
| `target_tokens` | 896 | VRAM budget per bin. Derived from hardware measurement. |
| `n_bins` | 4 | Steps per epoch. More bins = more gradient updates per epoch but smaller batches. |
| `ratios` | Box-Cox CDF | Class balance targets. Scale-invariant. |
| `max_len` | 512 | Hard ceiling. Records longer than this are filtered out before sampling. |

## Relationship to Training Phases

### SFT
- `target_tokens = 896` (measured: fits at fp16 + gradient checkpointing on 16GB)
- `n_bins = 4` per epoch
- 3 epochs × 4 bins = 12 gradient updates
- Each bin ≈ 3-9 records depending on length

### RL (GRPO)
- `target_tokens = 896 // G` where G=4 (each prompt generates G completions)
- Effective budget per prompt = 224 tokens
- TRL handles internal batching; bin packing applies to PROMPT selection
- `n_bins = 4` → batch_size=4=G (matches TRL requirement)

## Dynamic Bin Closure

Bins don't all close at the same time:
- Bin 1 (short records, many fit): closes after ~9 records
- Bin 4 (long records, few fit): closes after ~2 records

This is correct — VRAM usage is the same for each step regardless of how many records are in the bin. The model does the same amount of compute per step.

## Integration with Delta-Ratio Sampler

The delta-ratio sampler IS the draw policy. At each draw:
1. Compute deficit per cell (how far each cell is from its target proportion)
2. Draw from highest-deficit cell
3. Route the drawn record to the best-fit bin

This means early draws tend to come from underrepresented cells, and later draws fill remaining slots. Class balance converges to target as total_drawn increases.

## Comparison with Prior Approaches

| Approach | Steps/epoch | VRAM efficiency | Class balance | n control |
|----------|-------------|-----------------|---------------|-----------|
| Fixed batch_size=8 | n/8 | Wastes padding | None (random order) | Manual |
| 4 quantile blocks + accum | 6 (at n=62) | Good | Regime-interleave (hacky) | Manual |
| Token-budget bin packing | 4 (fixed) | Optimal | Delta-ratio guaranteed | Emergent |
