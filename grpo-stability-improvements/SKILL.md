---
name: grpo-stability-improvements
description: >
  Practical extensions to stabilize GRPO training for reasoning models. Covers: clipped
  policy ratios, KL divergence penalties (when to use and when to omit), format rewards,
  entropy/advantage tracking for failure detection, and 15 state-of-art modifications
  from DAPO/Dr.GRPO/DeepSeek-V3.2. Use when training is unstable, reward collapses,
  entropy drops, or deciding which GRPO variant to implement. Source: "Build a Reasoning
  Model (From Scratch)" Ch 7, Sebastian Raschka.
---

# GRPO Stability Improvements (Raschka Ch 7)

## The Core Problem

Basic GRPO works for short runs (~50-100 steps) but becomes unstable on longer training:
- Reward initially improves, then crashes
- Model starts producing nonsensical text
- Evaluation accuracy drops to 0%

## Diagnostic Metrics (track ALL jointly)

### Advantage Statistics
- `adv_mean`: should always be ~0 (sanity check)
- `adv_std`: reflects gradient signal strength
  - Near 1.0 = well-scaled, stable
  - Near 0 = vanishing signal (all rollouts same quality)
  - Very large = spiky updates, instability risk

### Entropy
- Measures model's uncertainty when generating next token
- High entropy (>1.5) = exploring, diverse outputs
- Low entropy (<0.5) = converging OR collapsing
- Low entropy + flat reward = COLLAPSE (stop immediately)
- Increasing entropy + increasing reward = healthy exploration

### Policy Ratio
- `ratio = exp(new_logprobs - old_logprobs)`
- Values near 1.0 = small change (stable)
- Large values (>5) = the policy changed a LOT in one step (risky)
- Track and report during training

## Fix 1: Clipped Policy Ratios

```python
epsilon = 0.2  # PPO default; GRPO often uses larger (1.0-10.0)
log_ratio = new_logps - old_logps
ratio = torch.exp(log_ratio)
clipped_ratio = torch.clamp(ratio, 1 - epsilon, 1 + epsilon)

unclipped_obj = ratio * advantages
clipped_obj = clipped_ratio * advantages
loss = -torch.min(unclipped_obj, clipped_obj).mean()
```

**Effect:** Prevents overly large single-step updates. Model can't jump too far in one step.
**Book finding:** "Training with clipped policy ratios is more stable — no visible drop around step 400."

### DeepSeek-R1's Approach
1. Generate large rollout pool (8192 responses) from reference policy
2. Split into 16 minibatches
3. For each: compute old_logps (reference), new_logps (current), update current
4. Refresh reference model after all minibatches

## Fix 2: KL Divergence Penalty

```python
kl_coeff = 0.001 to 0.05  # typical range
ref_logps = sequence_logprob(ref_model, token_ids, prompt_len)
kl_loss = kl_coeff * (current_logps - ref_logps).mean()
total_loss = policy_gradient_loss + kl_loss
```

**Effect:** Constrains long-term drift from reference model.
**WARNING (book finding):** KL can DESTABILIZE training when:
- Rewards collapse to zero → advantages are zero → only KL gradient remains
- KL then dominates and pushes model in arbitrary directions
- "The model started producing nonsensical text and random tokens"

**Domain-specific tuning (DeepSeek-V3.2):**
- Math: KL_coeff = 0 (omit entirely)
- Code: KL_coeff = 0.001
- General: KL_coeff = 0.01-0.05

**Our experience:** beta=0.02 caused collapse. beta=0.10 was stable. Consistent with book's warning that too-strong KL + reward collapse = instability.

## Fix 3: Format Reward

```python
def reward_format(token_ids, prompt_len, start_think_id, end_think_id):
    gen = token_ids[prompt_len:].tolist()
    try:
        return float(gen.index(start_think_id) < gen.index(end_think_id))
    except ValueError:
        return 0.0

total_reward = correctness_reward + format_weight * format_reward
```

**Pitfall:** If format_weight is too high, model learns to format correctly but answer incorrectly.
**Fix:** Make format reward CONDITIONAL on correctness (only give format bonus if answer is also correct).
**Our approach:** suppress_tokens blocks think at generation level (different mechanism, same goal).

## 15 State-of-Art Modifications (from DAPO, Dr.GRPO, DeepSeek-V3.2)

1. **Filter zero-gradient examples** (DAPO): Skip groups where all rewards identical
2. **Active sampling** (DAPO): Prioritize prompts with mixed correct/incorrect → stronger signal
3. **Token-level loss** (DAPO): Per-token instead of per-sequence → reduces length bias
4. **Omit KL** (DAPO, Dr.GRPO): Remove KL for math → better stability
5. **Larger clip range** (DAPO): Relax epsilon for reliable reward signals
6. **Truncate importance weights** (verl): Cap large weights so off-policy doesn't dominate
7. **Remove std normalization** (Dr.GRPO): Normalize by mean only, no std division
8. **Domain-specific KL** (DeepSeek-V3.2): Different beta per data type
9. **Importance-weighted KL** (DeepSeek-V3.2): Correct KL when rollouts from older policy
10. **Mask off-policy sequences** (DeepSeek-V3.2): Exclude unlikely rollouts under current policy
11. **Preserve sampling mask** (DeepSeek-V3.2): Compute probs only over tokens available during sampling
12. **Keep original advantage norm** (DeepSeek-V3.2): Standard group-based when it works
13. **Normalize reward components** (GDPO): Normalize each reward type separately before combining
14. **Sequence-level IS + clipping** (GSPO): Correct and clip at whole-sequence level
15. **Clip IS weights directly** (CISPO): Limit importance weights for stable off-policy corrections

## Relevance to Our Architecture

### What we currently have:
- TRL handles clipping internally (default epsilon)
- beta=0.10 for KL (book says omit for math, 0.001-0.05 range typical)
- We suppress think tokens (instead of format reward)
- We track frac_reward_zero_std (maps to #1: filter zero-gradient)
- We have patience-based early stopping (our extension beyond the book)

### What we should adopt for Parallel-RL:
- **#4: Omit KL for math domain** (our Math RL adapter)
- **#2: Active sampling** = our MGPO maxent selection (same idea!)
- **#8: Domain-specific KL** (different beta per adapter)
- **#1: Filter zero-gradient** (already implemented as zero-var skip)
- **Temperature 0.65** instead of book's 0.8 (Parallel-RL paper's finding)

## Key Takeaway

"There is a nearly infinite number of settings and modifications to try. Exploring a single modification thoroughly could become a month- or year-long research project."

→ Start with the basics (clipping + modest KL), measure, then selectively add modifications that address OBSERVED problems. Don't implement all 15 at once.
