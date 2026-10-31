---
name: grpo-from-scratch
description: >
  Implement Group Relative Policy Optimization (GRPO) for RLVR from first principles.
  Covers: rollout sampling with temperature+top-p, reward calculation from verifiable
  outputs, group-relative advantage normalization (zero-sum within group), sequence
  log-probability scoring, policy gradient loss with clipped ratios, KL divergence
  penalty, and the full training loop. Use when implementing or debugging GRPO/MGPO
  training, understanding why zero-variance groups produce zero gradient, or diagnosing
  RL training instability. Source: "Build a Reasoning Model (From Scratch)" Ch 6-7,
  Sebastian Raschka.
---

# GRPO from Scratch (Raschka, Ch 6-7)

## Core Algorithm

GRPO = Group Relative Policy Optimization. Used in DeepSeek-R1, VibeThinker.
No separate value model (unlike PPO). Learning signal from relative comparisons within a group.

### The Pipeline (per training step)

```
1. PROMPT → sample G rollouts (temperature=0.8-0.9, top_p=0.9)
2. REWARD each rollout (verifier for math/code, LLM judge for general)
3. ADVANTAGE = normalize rewards within the group (zero-sum)
4. LOGPROBS = compute sequence log-probability of each rollout under current policy
5. POLICY GRADIENT LOSS = -mean(advantage * logprob_ratio)
6. KL PENALTY = beta * KL(current_policy || reference_policy)
7. TOTAL LOSS = policy_gradient_loss + kl_penalty
8. BACKWARD + OPTIMIZER STEP
```

### Key Insight: Why Zero-Variance Groups Produce Zero Gradient

Advantage = (reward_i - mean(rewards)) / std(rewards)
If all G rollouts score identically (std=0), advantage=0 for all → gradient=0.
This is frac_reward_zero_std: the fraction of groups with no learning signal.

### Rollout Sampling

```python
@torch.no_grad()
def sample_response(model, tokenizer, prompt, device,
                    max_new_tokens=512, temperature=0.8, top_p=0.9):
    # Generate with KV cache, temperature scaling, top-p filter
    # Returns: (full_token_ids, prompt_length, answer_text)
```

- Temperature controls exploration (higher = more diverse rollouts)
- Top-p truncates the tail (prevents degenerate low-probability tokens)
- G=4-8 rollouts per prompt is standard (G=4 minimum for variance)

### Reward Calculation

For RLVR (verifiable rewards):
- Math: extract \boxed{answer}, compare to gold → binary 0/1
- Code: execute, check output → binary 0/1
- General (our case): LLM judge scores 0.0-1.0

Format reward bonus: +1 if output contains \boxed{} (or expected format)

### Advantages (Group-Relative Normalization)

```python
def compute_advantages(rewards):
    mean_r = rewards.mean()
    std_r = rewards.std()
    if std_r < 1e-8:  # zero-variance group
        return torch.zeros_like(rewards)
    return (rewards - mean_r) / std_r
```

This is the KEY mechanism that makes RL updates orthogonal across tasks:
- The mean subtraction cancels the "shared gradient direction"
- Only the task-specific residual remains
- This is why Parallel-RL works (Zhu et al. 2608.03573)

### Sequence Log-Probabilities

```python
def compute_logprobs(model, token_ids, prompt_len):
    logits = model(token_ids.unsqueeze(0))
    log_probs = F.log_softmax(logits, dim=-1)
    # Only score the COMPLETION tokens (not the prompt)
    completion_ids = token_ids[prompt_len:]
    token_log_probs = log_probs[0, prompt_len-1:-1]  # shifted by 1
    selected = token_log_probs.gather(1, completion_ids.unsqueeze(1))
    return selected.sum()  # sequence-level log-prob
```

### Policy Gradient Loss

```python
# ratio = exp(logprob_current - logprob_old)
ratio = torch.exp(current_logprobs - old_logprobs)
# Clipped ratio (from Ch 7 improvements)
clipped_ratio = torch.clamp(ratio, 1 - epsilon, 1 + epsilon)
# Loss = -min(ratio * advantage, clipped_ratio * advantage)
loss = -torch.min(ratio * advantages, clipped_ratio * advantages).mean()
```

### KL Divergence Penalty (Ch 7)

```python
kl = (ref_logprobs - current_logprobs).mean()  # simplified KL
total_loss = policy_loss + beta * kl
```

- beta=0.01-0.1 (higher = more conservative, less drift)
- Our experience: beta=0.02 caused collapse (too weak), beta=0.10 is stable

### Training Loop

```python
for epoch in range(num_epochs):
    for prompt in dataset:
        # 1. Sample G rollouts
        rollouts = [sample_response(model, ...) for _ in range(G)]
        # 2. Compute rewards
        rewards = torch.tensor([reward_fn(r) for r in rollouts])
        # 3. Compute advantages
        advantages = compute_advantages(rewards)
        # 4. Skip zero-variance groups
        if advantages.abs().max() < 1e-8:
            continue
        # 5. Compute log-probs and loss
        logprobs = [compute_logprobs(model, ids, plen) for ids, plen, _ in rollouts]
        loss = policy_gradient_loss(logprobs, old_logprobs, advantages)
        loss += beta * kl_penalty(ref_logprobs, logprobs)
        # 6. Update
        loss.backward()
        optimizer.step()
        optimizer.zero_grad()
```

## Ch 7 Improvements

### Clipped Policy Ratios
Prevents large policy updates that cause instability:
```
epsilon = 0.2 (default)
clipped = clamp(ratio, 1-eps, 1+eps)
loss = -min(ratio*adv, clipped*adv)
```

### KL Loss Term
Controls drift from reference policy:
- Reference = frozen copy of initial policy (or SFT checkpoint)
- KL too low (beta=0.02) → model drifts freely → collapse
- KL too high (beta>0.5) → model can't learn → no improvement
- Sweet spot: beta=0.05-0.10 for reasoning tasks

### Entropy Tracking
Monitor diversity of model outputs:
- High entropy (>1.5) = diverse, exploring
- Low entropy (<0.5) = converging, possibly collapsing
- If entropy drops AND reward is flat → training is stuck

### Format Reward (<think> tokens)
Explicitly reward proper formatting:
- +1 for including <think>...</think> reasoning chain
- Forces the model to "show its work"
- Our implementation uses suppress_tokens instead (blocks think at generation level)

## Relation to Our Implementation

| book concept | our implementation |
|---|---|
| sample_response | TRL's GRPOTrainer handles generation internally |
| compute_advantages | TRL's advantage normalization (zero-sum) |
| KL penalty | GRPOConfig.beta=0.10 |
| clipped ratio | TRL's default clip_ratio |
| format reward | suppress_tokens=[248068,248069] (different approach) |
| reward function | make_reward() → 2B judge |
| training loop | TRL's GRPOTrainer.train() |
| frac_reward_zero_std | logged per round for diagnostic |

## Key Lessons from the Book

1. Start with a SMALL model and dataset to validate the pipeline before scaling
2. Verify rollout quality before training (are they diverse? do they contain answers?)
3. Monitor advantages — if all zero, no learning is happening
4. The reference model must be FROZEN throughout training
5. Save checkpoints frequently — RL is unstable and the best point may be mid-training
