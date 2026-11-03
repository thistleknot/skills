---
name: adapter-merging-strategies
description: "DARE + TIES-merging pipeline for combining 4+ independently trained LoRA adapters with different reward signals. Covers task arithmetic baseline, TIES sign-aware merging, DARE stochastic sparsification, LoRA-specific reconstruction requirement, and sub-1B scaling considerations. From alphaXiv research synthesis."
---

# Adapter Merging Strategies: DARE + TIES for Multi-Reward LoRA Composition

Source: alphaXiv research synthesis (TIES-Merging arXiv:2306.01708, DARE arXiv:2311.03099, Task Arithmetic arXiv:2212.04089)

## When to Use

- Combining 4+ independently trained LoRA adapters (different domains, rewards, or objectives)
- Parallel-RL architecture: per-domain adapters merged into single multi-capability model
- Any scenario where adapters were trained from the SAME base but with DIFFERENT reward signals
- Resolving sign conflicts and cancellation when naive averaging destroys behavior

## The Problem

Adding many reward-specific updates makes cancellation and directional conflict increasingly likely. Task arithmetic degrades as adapter count grows. TIES-Merging was explicitly designed for this regime.

## Method Comparison

| Method | What it does | Strength with 4+ adapters | Main risk |
|--------|-------------|---------------------------|-----------|
| **Task arithmetic** | Adds scaled deltas: Delta = lambda * sum(w_i * Delta_i) | Cheapest, transparent, good when objectives compatible | Cancellation, magnitude growth, sensitivity to global lambda |
| **DARE** | Randomly drops delta params, rescales survivors by 1/(1-p) | Reduces overlap/redundancy; useful as preprocessor | Randomness, weak guarantees for GRPO; high drop rates destroy coordinated updates |
| **TIES-merging** | Magnitude trim → sign election → disjoint mean | Best for heterogeneous adapters with conflicting objectives | Magnitude != reward importance; can discard small but critical updates |
| **DARE + TIES** | Random sparsification → TIES | Default for 4+ adapters when no joint training possible | Requires tuning both drop rate AND TIES retention |

## Recommended Pipeline: DARE → TIES

### Step 1: Establish Arithmetic Baseline

1. Confirm every adapter trained from the EXACT same base checkpoint
2. Materialize each adapter's dense update: Delta_i = W_i - W_0
3. Normalize each adapter by layer/module norm
4. Set reward-specific weights alpha_i from held-out validation (NOT equal weights)
5. Merge with weighted task arithmetic
6. Evaluate: average reward, worst-case reward, pairwise regressions

### Step 2: DARE + TIES (Main Candidate)

1. Reconstruct each adapter's dense update Delta_i
2. Apply DARE independently to each: hat_Delta_i = (m_i * Delta_i) / (1-p), m_i ~ Bernoulli(1-p)
3. Run TIES on resulting sparse deltas:
   - **Trim**: retain top-k% by magnitude per module
   - **Elect sign**: s_j = sign(sum_i(tilde_Delta_i_j))
   - **Disjoint merge**: average only survivors aligned with elected sign
4. Tune hyperparameters:
   - DARE drop rate p: {0.1, 0.3, 0.5} (conservative for sub-1B)
   - TIES retention k: {0.2, 0.4, 0.6, 0.8}
   - Adapter weights alpha_i
   - Final scale lambda
5. Average results over several DARE random seeds

### Step 3: Reward-Aware Selection

Do NOT select merge solely by average reward. For each candidate measure:
- Per-objective reward score
- KL divergence from base
- Worst-objective score (floor constraint)
- Response length and format compliance
- Pairwise reward correlations

Selection objective (constrained):
```
max_M sum_i(beta_i * R_i(M))  subject to  R_i(M) >= R_i_floor for all i
```

## Critical: LoRA Reconstruction Requirement

**Run TIES and DARE on RECONSTRUCTED weight updates, NOT independently on A and B factors.**

For LoRA: Delta_W_i = s_i * B_i @ A_i

The factorization is non-unique — elementwise merging of A and B introduces arbitrary basis/scale mismatches:
```
merge(B_i) @ merge(A_i) != sum_i(B_i @ A_i)
```

Safe procedure:
1. Reconstruct dense Delta_W_i = scale * B_i @ A_i
2. Merge dense deltas using arithmetic/DARE/TIES
3. Optionally compress merged Delta_W back to desired rank via truncated SVD
4. Validate compressed adapter separately

For sub-1B models with r=16, this dense reconstruction is practical (768×768 or smaller matrices).

## Sub-1B Scaling Considerations

Critical differences from the 7B+ literature:

1. **Conservative DARE drop rates**: Start at p=0.2–0.5, NOT the 0.9–0.99 reported for larger SFT models. Tolerance for extreme drops increases with model size.
2. **Less redundancy**: Sub-1B models have less parameter redundancy — aggressive dropping removes behaviorally coordinated updates.
3. **TIES retention**: Prefer layerwise or modulewise retention over one global top-k threshold. GRPO produces small but coordinated changes in narrow behavioral regions.
4. **Attention vs MLP**: Use higher retention for attention projections (more reward-specific), lower for noisy MLP blocks.

## TIES-Merging Detail

Three stages on task vectors:

1. **Trim**: Retain only largest-magnitude fraction per update
   - Starting point: 20-50% per module
   - Original paper found 20% sufficient for PEFT, but NOT validated for GRPO
   
2. **Elect sign**: For every parameter coordinate j:
   ```
   s_j = sign(sum_i(tilde_Delta_i_j))
   ```
   Choose direction with greatest aggregate signed magnitude.

3. **Disjoint merge**: Average only surviving updates whose signs agree with elected direction. Updates opposing the elected sign are ZEROED, not averaged in.

Key insight: Sign conflicts occur with even 2 models and increase with model count. TIES prevents one adapter's noise from shrinking another's useful update through averaging.

## When Merging Fails

If reward signals are strongly antagonistic, NO merge rule guarantees Pareto-optimal policy. Fallbacks:

1. **Learned adapter weights**: Small calibration stage with multi-objective tuning
2. **Router**: Input-dependent adapter selection (MoE-style)
3. **Few-shot calibration pass**: 5% of data, tune only the merge coefficients
4. **Sequential fine-tuning**: Apply adapters in priority order with decreasing LR

## Application to Our Parallel-RL Architecture

For our 4 per-domain adapters (Math, Code, STEM, Instruction):

1. Train each independently from same SFT base with MGPO (domain-specific reward)
2. Reconstruct dense deltas: Delta_W_i = scale * B_i @ A_i for each adapter
3. Apply DARE (p=0.3 starting point) to each
4. Run TIES with modulewise retention (40% attention, 20% MLP)
5. Tune final scale lambda on the full cross-hatch eval set (112 items, all 4 regimes)
6. Validate: macroF1 must exceed best single-domain adapter AND SFT baseline
7. If merge regresses on any domain: increase that adapter's weight alpha_i

The "5% adapted pass" from Zhu et al. (arXiv 2608.03573) maps to Step 3's calibration — a short fine-tuning run on mixed-domain data AFTER the merge to smooth inconsistencies.

## Implementation Sketch (PyTorch)

```python
import torch
from peft import PeftModel

def reconstruct_lora_delta(adapter_path, base_model):
    """Reconstruct dense Delta_W from LoRA A, B factors."""
    model = PeftModel.from_pretrained(base_model, adapter_path)
    deltas = {}
    for name, module in model.named_modules():
        if hasattr(module, 'lora_A') and hasattr(module, 'lora_B'):
            # Delta_W = scaling * B @ A
            A = module.lora_A['default'].weight  # [r, in_features]
            B = module.lora_B['default'].weight  # [out_features, r]
            scaling = module.scaling['default']
            deltas[name] = (scaling * B @ A).detach()
    return deltas

def dare_sparsify(delta, drop_rate=0.3, seed=42):
    """DARE: random drop + rescale."""
    gen = torch.Generator().manual_seed(seed)
    mask = torch.bernoulli(torch.ones_like(delta) * (1 - drop_rate), generator=gen)
    return (delta * mask) / (1 - drop_rate)

def ties_merge(deltas_list, weights, retention=0.4):
    """TIES: trim → elect sign → disjoint mean."""
    merged = {}
    for key in deltas_list[0]:
        trimmed = []
        for i, deltas in enumerate(deltas_list):
            d = deltas[key] * weights[i]
            # Trim: keep top-k% by magnitude
            threshold = torch.quantile(d.abs(), 1 - retention)
            d[d.abs() < threshold] = 0
            trimmed.append(d)
        
        # Stack and elect sign
        stacked = torch.stack(trimmed)
        sign_sum = stacked.sum(dim=0)
        elected_sign = torch.sign(sign_sum)
        
        # Disjoint merge: average only sign-aligned
        aligned = stacked.clone()
        for i in range(len(trimmed)):
            mismatch = (torch.sign(trimmed[i]) != elected_sign) & (trimmed[i] != 0)
            aligned[i][mismatch] = 0
        
        # Average non-zero aligned values
        nonzero_count = (aligned != 0).sum(dim=0).clamp(min=1)
        merged[key] = aligned.sum(dim=0) / nonzero_count
    
    return merged
```

## Key References

- TIES-Merging: arXiv:2306.01708 — sign election, trim, disjoint merge
- DARE: arXiv:2311.03099 — stochastic delta sparsification with rescaling
- Task Arithmetic: arXiv:2212.04089 — task vectors as weight differences
- Parallel-RL (Zhu et al.): arXiv:2608.03573 — per-domain training + merge + adapted pass
