---
name: training-loop-enhancements
description: "Learning rate warmup, cosine decay schedule, and gradient clipping for stable LLM training. Includes complete enhanced training function combining all three techniques. Configuration recipes for pretraining, SFT, and RL. From Raschka LLM From Scratch Appendix D."
---

# Training Loop Enhancements: Warmup, Cosine Decay, Gradient Clipping

Source: "Build a Large Language Model (From Scratch)" — Appendix D: Adding Bells and Whistles to the Training Loop (Sebastian Raschka)

## Description

Three critical training stabilization techniques for LLMs: learning rate warmup (linear ramp-up to prevent early destabilization), cosine decay (gradual reduction to avoid overshooting minima in later training), and gradient clipping (L2 norm capping to prevent exploding gradients). Includes the complete enhanced training function combining all three.

## When to Use

- Implementing a production-quality training loop for any LLM
- Debugging training instability (loss spikes, NaN gradients, divergence)
- Configuring learning rate schedules for pretraining or fine-tuning
- Deciding warmup duration and minimum learning rate floor

## Key Concepts

### Learning Rate Warmup

Gradually increase LR from a small initial value to peak over the first N steps. Prevents large destabilizing updates before the optimizer's momentum estimates have warmed up.

```python
warmup_steps = int(0.2 * total_training_steps)  # 10-20% of total steps typical
lr_increment = (peak_lr - initial_lr) / warmup_steps

for step in range(total_steps):
    if step < warmup_steps:
        lr = initial_lr + step * lr_increment  # Linear ramp
    else:
        lr = peak_lr  # (or cosine decay from here)
    
    for param_group in optimizer.param_groups:
        param_group["lr"] = lr
```

**Configuration guidelines:**
- `initial_lr`: Very small (e.g., 1e-5 or 3e-5)
- `peak_lr`: The target learning rate (e.g., 1e-3 for pretraining, 1e-4 to 5e-5 for fine-tuning)
- `warmup_steps`: 10-20% of total training steps
- Warmup is LINEAR (not cosine) — simple constant increment per step

### Cosine Decay

After warmup, reduce LR following a half-cosine curve from peak to minimum. Ensures the model makes smaller updates as it converges, reducing risk of overshooting loss minima.

```python
min_lr = 0.1 * initial_lr  # Floor: don't go to zero

if step >= warmup_steps:
    progress = (step - warmup_steps) / (total_training_steps - warmup_steps)
    lr = min_lr + (peak_lr - min_lr) * 0.5 * (1 + math.cos(math.pi * progress))
```

**The cosine schedule:**
- Step = warmup_steps: `progress=0` → `cos(0)=1` → `lr = peak_lr`
- Step = midpoint: `progress=0.5` → `cos(pi/2)=0` → `lr = (peak_lr + min_lr) / 2`
- Step = final: `progress=1.0` → `cos(pi)=-1` → `lr = min_lr`

**Why cosine over linear decay:**
- Cosine spends more time at higher LRs (middle phase), making more progress
- Transitions smoothly at both ends (no discontinuity at warmup→decay boundary)
- Empirically produces better final loss than step or linear decay for LLMs

### Gradient Clipping

Cap gradient norm to prevent any single batch from causing an outsized weight update (exploding gradients).

```python
# Apply AFTER warmup (gradients during warmup are naturally small due to low LR)
if global_step >= warmup_steps:
    torch.nn.utils.clip_grad_norm_(model.parameters(), max_norm=1.0)
```

**How it works (L2 norm clipping):**
1. Compute global L2 norm of all gradients: `|G|_2 = sqrt(sum(g_i^2))`
2. If `|G|_2 > max_norm`: scale all gradients by `max_norm / |G|_2`
3. Effect: gradient direction preserved, magnitude capped

**When gradients explode:**
- Long sequences with many backward steps
- Outlier training examples with unusual loss landscapes
- Early training before optimizer momentum stabilizes
- Mixed-precision training without proper scaling

**max_norm values:**
- `1.0`: Standard for most LLM training (GPT, Llama, Qwen)
- `0.5`: More conservative, for very unstable training
- `5.0`: Lenient, rarely clips

### Complete Enhanced Training Function

```python
import math
from chapter05 import calc_loss_batch, evaluate_model, generate_and_print_sample

def train_model(model, train_loader, val_loader, optimizer, device,
                n_epochs, eval_freq, eval_iter, start_context, tokenizer,
                warmup_steps, initial_lr=3e-05, min_lr=1e-6):
    
    train_losses, val_losses, track_tokens_seen, track_lrs = [], [], [], []
    tokens_seen, global_step = 0, -1
    
    peak_lr = optimizer.param_groups[0]["lr"]  # Use optimizer's initial LR as peak
    total_training_steps = len(train_loader) * n_epochs
    lr_increment = (peak_lr - initial_lr) / warmup_steps
    
    for epoch in range(n_epochs):
        model.train()
        for input_batch, target_batch in train_loader:
            optimizer.zero_grad()
            global_step += 1
            
            # --- Learning Rate Schedule ---
            if global_step < warmup_steps:
                lr = initial_lr + global_step * lr_increment  # Linear warmup
            else:
                progress = (global_step - warmup_steps) / (total_training_steps - warmup_steps)
                lr = min_lr + (peak_lr - min_lr) * 0.5 * (1 + math.cos(math.pi * progress))  # Cosine decay
            
            for param_group in optimizer.param_groups:
                param_group["lr"] = lr
            track_lrs.append(lr)
            
            # --- Forward + Backward ---
            loss = calc_loss_batch(input_batch, target_batch, model, device)
            loss.backward()
            
            # --- Gradient Clipping (after warmup only) ---
            if global_step >= warmup_steps:
                torch.nn.utils.clip_grad_norm_(model.parameters(), max_norm=1.0)
            
            optimizer.step()
            tokens_seen += input_batch.numel()
            
            # --- Evaluation ---
            if global_step % eval_freq == 0:
                train_loss, val_loss = evaluate_model(
                    model, train_loader, val_loader, device, eval_iter)
                train_losses.append(train_loss)
                val_losses.append(val_loss)
                print(f"Ep {epoch+1} (Iter {global_step:06d}): "
                      f"Train loss {train_loss:.3f}, Val loss {val_loss:.3f}")
        
        generate_and_print_sample(model, tokenizer, device, start_context)
    
    return train_losses, val_losses, track_tokens_seen, track_lrs
```

## Configuration Recipes

### Pretraining (from scratch)
```
peak_lr = 1e-3 (or 6e-4 for larger models)
initial_lr = 1e-5
min_lr = 1e-5 (or 0.1 * peak_lr)
warmup_steps = 20% of total
weight_decay = 0.1
max_norm = 1.0
```

### Fine-tuning (SFT on pretrained model)
```
peak_lr = 1e-5 to 5e-5
initial_lr = 1e-6
min_lr = 1e-6
warmup_steps = 10% of total (or first epoch)
weight_decay = 0.1
max_norm = 1.0
```

### RL/GRPO (on SFT checkpoint)
```
peak_lr = 1e-5 to 1e-4 (for LoRA adapters)
peak_lr = 1e-6 to 3e-6 (for full-param)
warmup = 0-5% (RL often skips warmup)
max_norm = 1.0
No cosine decay for short RL runs (100-200 steps)
```

## Design Patterns

1. **Gradient clipping only after warmup**: During warmup, LR is already small → gradients are naturally bounded. Clipping during warmup can prevent necessary initial exploration.
2. **Track LR for debugging**: Store `track_lrs` list and plot it — visual confirmation that the schedule is correct.
3. **min_lr > 0**: Never decay to exactly 0. A floor (e.g., 1e-5) ensures continued learning in final steps.
4. **Warmup compensates for random optimizer init**: AdamW's momentum/variance estimates start at 0 — warmup gives them time to calibrate before large updates begin.

## Failure Modes

| Symptom | Likely Cause | Fix |
|---------|-------------|-----|
| Loss spikes early in training | No warmup, or peak_lr too high | Add warmup, reduce peak_lr |
| Loss plateaus after initial drop | Cosine decayed too fast, or min_lr too low | Increase min_lr or total steps |
| NaN loss | Gradient explosion, no clipping | Add gradient clipping (max_norm=1.0) |
| Loss oscillates wildly | LR too high throughout | Reduce peak_lr, or increase warmup fraction |
| Training loss still high at end | min_lr too small (effectively stopped learning) | Increase min_lr to 10% of peak |
| Val loss increases while train loss drops | Overfitting | Reduce epochs, add regularization, more data |

## Relationship to Our Pipeline

In `mgpo.py` and `vibe_sft.py`:
- SFT uses constant LR (no warmup/cosine) because runs are short (3 epochs, 200 steps)
- RL uses constant LR with patience-based early stopping instead of decay
- Gradient clipping via TRL's built-in `max_grad_norm=1.0`
- For longer production runs, adding warmup + cosine would help stability
- The VRAM-limited setting means each step is expensive → fewer total steps → less need for decay
