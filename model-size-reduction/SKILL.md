---
name: model-size-reduction
description: >
  Architecture-agnostic checkpoint slimming for Hugging Face models. Use when
  the goal is a smaller or more portable model artifact via dtype casting,
  layer dropping, LoRA extraction, or delta sparsification (DARE/TIES/DELLA),
  especially when mergekit does not support the architecture.
status: active
last_validated: 2026-05-09
validation_method: session
---

# Model Size Reduction

## When to Use

Use this skill when:

- a full Hugging Face checkpoint is too large to ship, store, or serve
- mergekit fails on architecture detection but the weights still follow normal layered key patterns
- you want to keep only the task delta as a LoRA adapter
- you need to denoise a fine-tune delta before additional pruning or layer dropping
- you want a checkpointed reduction pipeline that can resume after an interrupted run

Do not use this skill when:

- the real problem is sequential forgetting across tasks -> use `continual-learning`
- the objective is search over training-time hyperparameters -> use `optuna-nested-cv`
- the model is API-only and you cannot access checkpoint weights

---

## Scope Boundary and Paired Skills

This skill owns **post-training checkpoint reduction**.

It owns:
- dtype recasting (`fp32 -> fp16` / `bf16`)
- transformer block dropping by `state_dict` key surgery
- LoRA extraction from `finetuned - base`
- delta sparsification with DARE, TIES, or DELLA
- checkpointed multi-stage reduction pipelines
- validation of reduction aggressiveness with perplexity deltas

It does **not** own:
- continual multi-task retention and forgetting control -> `continual-learning`
- hyperparameter search or holdout design -> `optuna-nested-cv`
- experiment lineage and artifact registry -> `mlflow`

---

## Primitive Selection

| Goal | Primitive | Best default |
|---|---|---|
| Smaller files with minimal behavior change | dtype cast | `float16` or `bfloat16` |
| Fewer total parameters | layer drop | middle-drop before tail-drop |
| Adapter-only artifact | LoRA extraction | rank 16-128 depending on task |
| Denoise a large fine-tune delta | sparsify | DELLA for large deltas, DARE for instruction-style deltas |
| Repeatable multi-stage slimming | checkpointed pipeline | sparsify -> drop -> validate |

Rules:
- Start with dtype cast if the source checkpoint is still `float32`.
- Prefer middle-drop over tail-drop because early syntax layers and late output layers are usually less substitutable.
- Use LoRA extraction first when the fine-tuned model is a clean descendant of a known base checkpoint.
- Use sparsification to reduce interference in the delta; it does **not** reduce disk size by itself.

---

## Reduction Protocol

1. **Diagnose lineage and objective.** Decide whether you need a smaller full model, an adapter-only artifact, or a denoised delta for later compression.
2. **Confirm weight-level compatibility.** Detect the layer-key prefix from the checkpoint (`model.layers.N`, `transformer.h.N`, `model.decoder.layers.N`, `encoder.layers.N`, or equivalent). If no numeric layer pattern exists, stop and inspect `state_dict.keys()` before touching weights.
3. **Choose the lightest viable primitive.**
   - dtype cast for storage-only pressure
   - layer drop for parameter-count reduction
   - LoRA extraction for adapter portability
   - DARE/TIES/DELLA when the fine-tune delta is noisy and still needs to remain task-shaped
4. **Run as a checkpointed pipeline for multi-stage jobs.** Persist each stage as a full model directory so reruns can skip completed work instead of recomputing.
5. **Validate before shipping.** Compare perplexity or a task-specific metric against the source checkpoint. Treat `>15%` perplexity degradation as too aggressive unless the downstream task explicitly tolerates it.

---

## Method Notes

### Dtype cast
- Use when the checkpoint is `float32` and you mainly need smaller artifacts.
- `bfloat16` is safer than `float16` when activation or weight magnitudes are large.

### Layer dropping
- Best for direct parameter-count reduction.
- Keep output indices contiguous and patch `config.json` to the new layer count.
- As a default heuristic: 10% dropped is usually low-risk, 20-25% is moderate, and 33%+ requires aggressive task-specific validation.

### LoRA extraction
- Use when the fine-tuned checkpoint was derived from a known base model.
- Compute `delta = finetuned - base` and keep a low-rank SVD approximation.
- Higher ranks preserve task quality; lower ranks maximize portability.

### DARE / TIES / DELLA
- **DARE**: random pruning plus rescaling; strong default for instruction-style deltas.
- **TIES**: keep the top-magnitude delta entries; good when absolute-value concentration is already informative.
- **DELLA**: row-wise adaptive keep probability; better fit for large or uneven deltas.

Failure boundaries:
- density `< 0.3` is usually capability collapse territory
- DELLA requires `density +/- epsilon` to remain inside `(0, 1)`
- sparsification reduces interference, not file size; combine it with a later reduction stage if footprint is the real objective

---

## Validation Contract

Measure reduction quality against the original checkpoint:

| Relative perplexity delta | Interpretation |
|---|---|
| `< 5%` | effectively lossless |
| `5-15%` | acceptable only if downstream behavior stays intact |
| `> 15%` | too aggressive; back off density or restore layers |

Common failures:
- `No recognized layer key pattern` -> add the actual prefix pattern before editing weights
- `No safetensors in ...` -> resave the source checkpoint with safe serialization first
- OOM during load -> process shards incrementally rather than materializing every tensor at once
- Garbage generations after reduction -> the drop ratio or sparsity level is too aggressive, not "just formatting"

---

## Example

Typical stacked workflow:

1. sparsify a fine-tuned checkpoint against its base
2. checkpoint the sparsified model
3. middle-drop layers from the checkpointed output
4. cast to the deployment dtype
5. validate perplexity delta before publishing

---

## Applicability Envelope

**Works well when:**
- the model is stored as a Hugging Face checkpoint with regular numeric layer keys
- the reduction target is checkpoint size, parameter count, or adapter portability
- mergekit is failing because of architecture registry limits rather than tensor incompatibility
- you can validate the reduced checkpoint against the original

**Fails or degrades when:**
- the checkpoint uses non-standard naming that hides layer indices
- the model is already near the minimum viable depth for its task
- sparsity is pushed low enough to destroy task structure
- you skip post-reduction validation and mistake artifact shrinkage for a safe deployment

**Environment assumptions:**
- access to the source checkpoint files and, for LoRA extraction or sparsification, the matching base checkpoint
- enough disk space for at least one additional full checkpoint copy per pipeline stage
- `torch`, `transformers`, `safetensors`, and optionally `peft` are available
