---
name: llm-pretraining-fundamentals
description: "Core mechanics of pretraining a causal language model: next-token prediction via cross-entropy loss, training loop (zero_grad/forward/loss/backward/step), temperature scaling, top-k sampling, weight saving/loading for checkpoint resumption. From Raschka LLM From Scratch Ch5."
---

# LLM Pretraining Fundamentals

Source: "Build a Large Language Model (From Scratch)" — Chapter 5: Pretraining on Unlabeled Data (Sebastian Raschka)

## Description

Core mechanics of pretraining a causal language model: next-token prediction via cross-entropy loss, training/validation split, the standard PyTorch training loop (zero_grad → forward → loss → backward → step), text generation strategies (temperature scaling, top-k sampling), and weight saving/loading for checkpoint resumption.

## When to Use

- Implementing or debugging a pretraining loop for any causal LM
- Understanding cross-entropy loss in the context of next-token prediction
- Implementing temperature scaling or top-k sampling for generation
- Saving/loading model checkpoints with optimizer state for resumption
- Loading pretrained weights into a custom architecture

## Key Concepts

### Cross-Entropy Loss for Next-Token Prediction

The training objective: given input tokens, predict the next token. Targets are inputs shifted by one position.

```python
# Flatten for cross_entropy: [batch*seq_len, vocab_size] vs [batch*seq_len]
logits_flat = logits.flatten(0, 1)
targets_flat = targets.flatten()
loss = torch.nn.functional.cross_entropy(logits_flat, targets_flat)
```

Cross-entropy is equivalent to: softmax → select target token probability → log → negate → average. PyTorch's `cross_entropy` does all steps in one numerically stable call.

**Perplexity** = exp(cross_entropy_loss). Interpretable as "effective vocabulary size the model is uncertain about." Lower = better.

### Standard Training Loop

```python
def train_model_simple(model, train_loader, val_loader, optimizer, device,
                       num_epochs, eval_freq, eval_iter, start_context, tokenizer):
    for epoch in range(num_epochs):
        model.train()
        for input_batch, target_batch in train_loader:
            optimizer.zero_grad()
            loss = calc_loss_batch(input_batch, target_batch, model, device)
            loss.backward()
            optimizer.step()
            # Periodic evaluation and text generation for observability
        generate_and_print_sample(model, tokenizer, device, start_context)
```

Key elements:
1. `model.train()` enables dropout
2. `optimizer.zero_grad()` resets gradients from previous step
3. Forward pass → loss computation
4. `loss.backward()` computes gradients via backpropagation
5. `optimizer.step()` updates weights using gradients
6. Periodic eval with `model.eval()` + `torch.no_grad()` (disables dropout, saves memory)

### Data Preparation

- Train/val split (typically 90/10)
- DataLoader with `max_length` = context window, `stride` = context window (non-overlapping chunks)
- Batch size: larger is more efficient but requires more memory
- `drop_last=True` for training (consistent batch sizes), `False` for validation

### Loss Computation Utilities

```python
def calc_loss_batch(input_batch, target_batch, model, device):
    input_batch = input_batch.to(device)
    target_batch = target_batch.to(device)
    logits = model(input_batch)
    loss = torch.nn.functional.cross_entropy(
        logits.flatten(0, 1), target_batch.flatten()
    )
    return loss

def calc_loss_loader(data_loader, model, device, num_batches=None):
    total_loss = 0.
    if num_batches is None:
        num_batches = len(data_loader)
    for i, (input_batch, target_batch) in enumerate(data_loader):
        if i < num_batches:
            loss = calc_loss_batch(input_batch, target_batch, model, device)
            total_loss += loss.item()
        else:
            break
    return total_loss / num_batches
```

### Temperature Scaling

Controls generation diversity by scaling logits before softmax:

```python
scaled_logits = logits / temperature
probs = torch.softmax(scaled_logits, dim=-1)
```

- **temperature = 1.0**: Original distribution (default)
- **temperature < 1.0** (e.g., 0.1): Sharper, more deterministic (approaches greedy)
- **temperature > 1.0** (e.g., 5.0): Flatter, more random (more diverse but potentially nonsensical)

### Top-k Sampling

Restricts sampling to the k most likely tokens:

```python
top_logits, _ = torch.topk(logits, top_k)
min_val = top_logits[:, -1]
logits = torch.where(logits < min_val, torch.tensor(float('-inf')), logits)
probs = torch.softmax(logits, dim=-1)
idx_next = torch.multinomial(probs, num_samples=1)
```

Prevents sampling from the long tail of unlikely tokens that produce garbage.

### Complete Generation Function

```python
def generate(model, idx, max_new_tokens, context_size,
             temperature=0.0, top_k=None, eos_id=None):
    for _ in range(max_new_tokens):
        idx_cond = idx[:, -context_size:]  # Crop to context window
        with torch.no_grad():
            logits = model(idx_cond)
        logits = logits[:, -1, :]  # Only last token's logits matter
        
        if top_k is not None:  # Apply top-k filtering
            top_logits, _ = torch.topk(logits, top_k)
            min_val = top_logits[:, -1]
            logits = torch.where(logits < min_val, float('-inf'), logits)
        
        if temperature > 0.0:  # Probabilistic sampling
            logits = logits / temperature
            probs = torch.softmax(logits, dim=-1)
            idx_next = torch.multinomial(probs, num_samples=1)
        else:  # Greedy decoding
            idx_next = torch.argmax(logits, dim=-1, keepdim=True)
        
        if idx_next == eos_id:
            break
        idx = torch.cat((idx, idx_next), dim=1)
    return idx
```

### Saving and Loading Checkpoints

**Save model only:**
```python
torch.save(model.state_dict(), "model.pth")
```

**Load model:**
```python
model = GPTModel(config)
model.load_state_dict(torch.load("model.pth", map_location=device))
model.eval()
```

**Save model + optimizer (for training resumption):**
```python
torch.save({
    "model_state_dict": model.state_dict(),
    "optimizer_state_dict": optimizer.state_dict(),
}, "checkpoint.pth")
```

**Resume training:**
```python
checkpoint = torch.load("checkpoint.pth", map_location=device)
model.load_state_dict(checkpoint["model_state_dict"])
optimizer.load_state_dict(checkpoint["optimizer_state_dict"])
model.train()
```

Critical: AdamW stores per-parameter momentum/variance. Without restoring optimizer state, resumed training converges poorly.

### Loading Pretrained Weights

Pattern for mapping external weights to custom architecture:
```python
def assign(left, right):
    if left.shape != right.shape:
        raise ValueError(f"Shape mismatch. Left: {left.shape}, Right: {right.shape}")
    return torch.nn.Parameter(torch.tensor(right))
```

Key insight: OpenAI GPT-2 uses weight tying — token embedding weights are reused in the output projection layer (`out_head.weight = params["wte"]`).

## Design Patterns

1. **Observability**: Generate sample text after each epoch to visually inspect quality
2. **Overfitting detection**: When val_loss diverges from train_loss, model is memorizing
3. **Context length**: Can train with shorter context (256) for speed, then load into longer-context config
4. **Dropout at eval**: Always `model.eval()` for inference (disables dropout for deterministic output)

## Failure Modes

- **Val loss diverging from train loss**: Overfitting. Need more data or fewer epochs.
- **Loss not decreasing**: Learning rate too low, or architecture bug.
- **Generated text is repetitive**: Temperature too low or no sampling (pure greedy).
- **Generated text is garbage**: Temperature too high, or model undertrained.
- **Checkpoint load produces nonsense**: Weight mapping error — shapes matched but semantics wrong.

## Practical Notes

- GPT-2 124M: 50,257 vocab, 1024 context, 768 embed, 12 heads, 12 layers
- Initial random probabilities hover around 1/vocab_size ≈ 0.00002
- Training on "The Verdict" (5,145 tokens) takes ~5 min on laptop — educational scale
- Real pretraining: Llama 2 7B = 184,320 A100 GPU-hours, 2T tokens, ~$690K
- AdamW preferred over Adam: better weight decay regularization for LLMs
