---
name: lora-parameter-efficient
description: >
  LoRA (Low-Rank Adaptation) for parameter-efficient fine-tuning of LLMs. Covers: the
  low-rank decomposition (W = W0 + BA), rank selection, alpha scaling, target module
  selection, training only B and A while freezing base weights, merging adapters for
  inference, and stacking multiple adapters. Use when implementing LoRA for RL or SFT,
  choosing rank/alpha, understanding update scale (lr * alpha / r), or debugging
  adapter-trained gates. Source: "Build a Large Language Model (From Scratch)" Appendix E,
  Sebastian Raschka.
---

# LoRA — Parameter-Efficient Fine-Tuning (Raschka, Appendix E)

## Core Mechanism

Instead of updating all parameters W, decompose the update as:
```
W_new = W_frozen + B @ A
```
Where:
- W_frozen: original pretrained weights (not updated)
- B: (d_out × r) matrix, initialized to ZERO
- A: (r × d_in) matrix, initialized random
- r: rank (much smaller than d_out or d_in)

Only B and A are trained. Trainable params = 2 * r * d (vs d*d for full).

## Key Parameters

### Rank (r)
- Controls capacity of the adapter
- r=16 is standard for most tasks
- r=64 for knowledge-heavy tasks (CPT)
- Higher r = more capacity but more parameters

### Alpha (α)
- Scaling factor: effective update = (α/r) * B @ A
- Convention: α = 2r (so scaling = 2.0)
- Our convention: α = 4r for RL stage (α=64, r=16 → scale=4)

### Update Scale
The comparable quantity across configs: `lr * α / r`
- Two configs with different α/r are NOT comparable by lr alone
- Report update scale alongside lr in every comparison

### Target Modules
Which layers get LoRA adapters:
- Attention: q_proj, k_proj, v_proj, o_proj (format/routing knowledge)
- FFN: gate_proj, up_proj, down_proj (factual knowledge)
- All-linear: both attention + FFN (maximum capacity)

## Implementation

```python
from peft import LoraConfig, get_peft_model

config = LoraConfig(
    r=16,
    lora_alpha=64,  # alpha = 4r
    lora_dropout=0.0,  # no dropout for RL (need all signal)
    bias="none",
    task_type="CAUSAL_LM",
    target_modules=["q_proj", "k_proj", "v_proj", "o_proj",
                    "gate_proj", "up_proj", "down_proj"],
)
model = get_peft_model(base_model, config)
```

## Adapter-Trained Gate

After training, verify the adapter actually moved:
```python
max_B = max(p.abs().max() for n, p in model.named_parameters() if "lora_B" in n)
assert max_B > 1e-4, "adapter didn't train (B stayed at zero initialization)"
```

B initializes to EXACTLY zero. If max|B| < 1e-4 after training, the adapter is a no-op.

## Stacking Adapters

Multiple LoRA adapters can be stacked:
```
base + CPT_adapter (frozen) + SFT_adapter (frozen) + RL_adapter (trainable)
```

Each adapter's B@A is added to the base weights. They compose by summation.
For the Parallel-RL architecture: train per-domain adapters independently, then sum their deltas.

## Merging for Inference

```python
# Merge adapter into base weights (no runtime overhead)
merged_model = model.merge_and_unload()
# Now merged_model.linear.weight = W_frozen + B @ A
```

## Key Lessons

1. **B inits to zero** — this is load-bearing for the adapter-trained gate
2. **Alpha/rank ratio determines effective step size** — must be reported alongside lr
3. **LoRA at r=16 on 0.8B ≈ 10.8M trainable** — fits in 16GB with generation + judge
4. **Don't carry lr across parameterizations** — 1e-4 is safe for LoRA, catastrophic for full-param
5. **Dropout=0 for RL** — you need every bit of the sparse gradient signal
