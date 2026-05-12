# mergekit — Skill

**Scope:** Use this skill whenever the task involves merging, interpolating, frankenmerging, or extracting LoRA adapters from pretrained LLMs using the `arcee-ai/mergekit` library. Triggers include: "merge two models," "combine fine-tunes," "model soup," "task arithmetic," "TIES," "DARE," "frankenmerge," "layer stacking," "LoRA extraction from merge," or any request to produce a merged `.safetensors` checkpoint.

---

## Architecture Overview

mergekit operates **out-of-core**: it streams tensors layer-by-layer rather than loading full models into RAM. This means merges that would require 2× model VRAM can often run in 8 GB VRAM or entirely on CPU. The mental model:

```
[Model A tensors] ──┐
[Model B tensors] ──┼──► merge_method(parameters) ──► output tensor ──► disk
[Model C tensors] ──┘
```

All configuration lives in a single YAML file. The CLI reads it, instantiates a merge plan, streams tensors, applies the method, and writes the result. No training loop, no gradients.

**Key concepts before touching config:**
- **Task vector** = fine-tuned weights − base weights (δ). Most advanced methods operate on these deltas, not raw weights.
- **Density** = fraction of delta parameters to *keep* after sparsification (1.0 = no pruning).
- **Weight** = contribution of each model to the final blend (normalized across models for linear/task arithmetic).
- **Base model** = the common ancestor from which task vectors are computed. Required for task-vector methods.

---

## Installation

```bash
git clone https://github.com/arcee-ai/mergekit.git
cd mergekit
pip install -e .                   # editable, makes CLI scripts available
pip install -e ".[vllm]"           # optional: vLLM-based evaluation
pip install -e ".[evo]"            # optional: evolutionary merge (requires ray)
```

Minimum pip version: 21.3 (`python -m pip install --upgrade pip` if editable install fails).

**Hardware floor:**
- CPU-only: works, slow, needs RAM ≥ 2× largest model
- GPU: 8 GB VRAM minimum for 7B merges; flash-attention not required

---

## CLI Entry Points

| Command | Purpose |
|---|---|
| `mergekit-yaml config.yml ./output [flags]` | Main merge runner |
| `mergekit-multi config.yml ./output` | Multi-stage merges (chain of configs) |
| `mergekit-pytorch config.yml ./output` | Raw PyTorch (non-HF) model merging |
| `mergekit-tokensurgeon` | Transplant a tokenizer onto a model |
| `mergekit-extract-lora finetuned base ./lora` | Extract LoRA adapter from delta |

**Common flags for `mergekit-yaml`:**

| Flag | Effect |
|---|---|
| `--cuda` | Use GPU |
| `--lazy-unpickle` | Lower peak RAM via lazy tensor loading |
| `--allow-crimes` | Bypass architecture mismatch guards |
| `--copy-tokenizer` | Force copy tokenizer from base model |
| `--lora-merge-cache ./cache` | Cache LoRA merges to disk |

---

## YAML Configuration Schema

```yaml
merge_method: <method>            # required — see Method Reference below
base_model: path/or/hf_id        # required for task-vector methods
dtype: bfloat16                   # float32 | float16 | bfloat16

# Use `models` OR `slices`, never both
models:
  - model: path/or/hf_id
    parameters:                   # per-model overrides
      weight: 0.5
      density: 0.7
  - model: path/or/hf_id
    parameters:
      weight: 0.5
      density: 0.7

# OR — for frankenmerging / layer selection:
slices:
  - sources:
      - model: path/or/hf_id
        layer_range: [0, 16]
      - model: path/or/hf_id
        layer_range: [16, 32]

parameters:                       # global fallback for all tensors
  weight: 1.0
  density: 1.0
  normalize: true

tokenizer:
  source: union                   # union | base | "path/to/model"
  tokens: {}                      # optional per-token embedding overrides

chat_template: auto               # auto | alpaca | chatml | llama3 | mistral | <jinja2>
```

### Parameter Precedence (highest to lowest)

1. `slices.*.sources.parameters` — specific input slice
2. `slices.*.parameters` — output slice
3. `models.*.parameters` — any tensor from a specific model
4. `parameters` — global catchall

Parameters can also be **gradients** (lists) — mergekit interpolates linearly across layers:

```yaml
parameters:
  weight: [0.0, 0.5, 1.0]   # ramps from 0 at first layer to 1 at last
```

---

## Method Reference

### Decision Guide

```
Single smooth interpolation between two models?
  └─► slerp / nuslerp

Simple average / model soup (no common base needed)?
  └─► linear / karcher

Transfer a skill from a fine-tune to another model?
  └─► task_arithmetic

Merging 3+ fine-tunes, reducing interference?
  ├─► ties        (sign consensus, baseline)
  ├─► dare_ties   (random sparsification + sign consensus, often > ties)
  ├─► della       (magnitude-aware sparsification + sign consensus, best for large deltas)
  └─► breadcrumbs_ties (removes both tiny and huge delta outliers)

Layer stacking / architecture frankenstein?
  └─► passthrough + slices

Automated hyperparameter search?
  └─► evolutionary (DARE/TIES base + CMA-ES or PGPE optimizer)
```

---

### `linear`
Weighted average: `Σ(wᵢ * θᵢ) / Σwᵢ`

No base model required. Simplest method. Good for model soups (averaging checkpoints from the same training run).

**Parameters:** `weight` per model (default 1.0). `normalize: true` divides by weight sum.

```yaml
merge_method: linear
models:
  - model: model_a
    parameters: {weight: 0.6}
  - model: model_b
    parameters: {weight: 0.4}
dtype: bfloat16
```

---

### `slerp`
Spherical linear interpolation between **exactly 2** models along the geodesic in weight space.

Preserves norm better than linear at `t=0.5`. Base model is one of the two models (set `base_model` to one of them).

**Parameters:** `t` ∈ [0,1] — 0 = base_model, 1 = the other model. Accepts gradients for layer-varying blend.

```yaml
merge_method: slerp
base_model: model_a
models:
  - model: model_a
  - model: model_b
    parameters: {t: 0.5}
dtype: bfloat16
```

---

### `nuslerp`
Enhanced SLERP. More intuitive weight parameter (maps directly to contribution rather than interpolation fraction). Can also do task-vector SLERP. Handles >2 models as barycentric SLERP.

**Parameters:** `weight` per model, `nuslerp_mode: "model"` (default) or `"task_vector"`.

---

### `task_arithmetic`
Computes task vectors (δᵢ = model_i − base), scales them by weight, sums, adds back to base.

`output = base + Σ(wᵢ * (model_i − base))`

Clean way to add or subtract capabilities. Negative weights subtract a skill.

**Parameters:** `weight` per model, `lambda` global scaling of the merged delta (default 1.0).

```yaml
merge_method: task_arithmetic
base_model: meta-llama/Llama-2-7b-hf
models:
  - model: meta-llama/Llama-2-7b-hf
  - model: coding_finetune
    parameters: {weight: 0.7}
  - model: math_finetune
    parameters: {weight: 0.5}
parameters:
  lambda: 1.0
dtype: bfloat16
```

---

### `ties`
**T**rim, **E**lect **S**ign, merge. Builds on task arithmetic.

Three steps per tensor:
1. **Trim** — zero out delta params below density threshold
2. **Elect** — for each param position, pick the sign with greatest total magnitude across models
3. **Merge** — average only params that agree with elected sign, add to base

Best for: 3+ fine-tunes with potentially conflicting updates.

**Parameters:**
- `density` ∈ (0,1] — fraction of top-magnitude deltas to keep (per model). Start at 0.5–0.7.
- `weight` — contribution of each model's elected delta
- `normalize: true` — divide merged delta by weight sum before adding to base

```yaml
merge_method: ties
base_model: mistralai/Mistral-7B-v0.1
models:
  - model: mistralai/Mistral-7B-v0.1
  - model: model_a
    parameters: {density: 0.6, weight: 0.5}
  - model: model_b
    parameters: {density: 0.6, weight: 0.5}
parameters:
  normalize: true
dtype: bfloat16
```

---

### `dare_linear` / `dare_ties`
Drop And REscale. Sparsifies task vectors by **randomly** setting delta params to zero at rate `(1 - density)`, then rescales remaining params by `1/density` to preserve expected magnitude.

`dare_ties` adds TIES sign election after DARE sparsification. Generally better than plain `ties`.

**Parameters:** same as `ties`. Additional: `int8_mask: true` (saves memory on mask storage).

```yaml
merge_method: dare_ties
base_model: mistralai/Mistral-7B-v0.1
models:
  - model: mistralai/Mistral-7B-v0.1
  - model: model_a
    parameters: {density: 0.53, weight: 0.4}
  - model: model_b
    parameters: {density: 0.53, weight: 0.3}
  - model: model_c
    parameters: {density: 0.53, weight: 0.3}
parameters:
  int8_mask: true
  normalize: true
dtype: bfloat16
```

Density sweep heuristic: start at 0.5, increase if output loses capabilities, decrease if interference remains.

---

### `della` / `della_linear`
**D**rop, **E**lect, **F**use. Adaptive magnitude-based pruning (MAGPRUNE):

1. **Drop** — rank delta params by magnitude per row; assign higher drop probability to lower-magnitude params. Rescale survivors.
2. **Elect** — sign consensus (same as TIES).
3. **Fuse** — average elected params, scale by `lambda`.

Better than DARE when delta distributions are heavy-tailed (large fine-tunes, RLHF models).

**Parameters:**
- `density` — target keep rate
- `epsilon` — max deviation from density in probability assignment (range must stay in [0,1])
- `lambda` — final delta scaling factor
- `weight` per model

```yaml
merge_method: della
base_model: base_model_path
models:
  - model: base_model_path
  - model: model_a
    parameters: {density: 0.6, weight: 1.0, epsilon: 0.1}
  - model: model_b
    parameters: {density: 0.6, weight: 1.0, epsilon: 0.1}
parameters:
  lambda: 1.0
dtype: bfloat16
```

---

### `breadcrumbs` / `breadcrumbs_ties`
Removes both very small (noise) and very large (outlier) delta values before merging. Controlled by two density-like bounds.

**Parameters:** `weight`, `density`, `gamma` (fraction of top-magnitude params to also drop — outlier removal). Note: `gamma` ≡ `β` in the paper; `density = 1 - γ - β`.

---

### `model_stock`
Computes geometrically optimal weights for linear interpolation given ≥3 models. Requires base model. Treats model positions as vectors in weight space, finds the barycenter.

Use when you have many fine-tunes from the same base and want data-free weight selection.

---

### `passthrough`
No-op. Passes tensors through unchanged. Used exclusively for frankenmerging with `slices` — when a layer range comes from one model with no blending.

---

## Frankenmerging (Layer Stacking)

Uses `slices` instead of `models`. Each slice specifies a layer range and its source. Ranges must be contiguous and non-overlapping in the output. Different models can contribute different depth ranges.

```yaml
merge_method: passthrough
slices:
  - sources:
      - model: llama_instruct
        layer_range: [0, 16]    # first 16 layers from model A
  - sources:
      - model: llama_code
        layer_range: [16, 32]   # last 16 layers from model B
dtype: bfloat16
tokenizer_source: base
```

You can also blend at slice boundaries:

```yaml
slices:
  - sources:
      - model: model_a
        layer_range: [0, 24]
        parameters: {weight: 0.7}
      - model: model_b
        layer_range: [0, 24]
        parameters: {weight: 0.3}
merge_method: linear
dtype: bfloat16
```

**Preconditions for frankenmerging:**
- Models must share the same architecture (same hidden_dim, num_heads, etc.)
- Use `--allow-crimes` to bypass this check — output quality not guaranteed
- Embedding and LM head layers are typically copied from one model; set `tokenizer_source` explicitly

---

## LoRA Extraction

Extracts a PEFT-compatible LoRA adapter approximating the delta between two models. Useful for distributing fine-tune diffs compactly.

```bash
mergekit-extract-lora finetuned_model_path base_model_path ./output_lora \
  --rank 64 \
  --no-lazy-unpickle
```

The adapter targets all linear layers. Rank is a fidelity/size tradeoff — higher rank = better approximation, larger file. Rank 32–64 is a reasonable default.

**Precondition:** both models must share architecture. The extraction is a truncated SVD of (finetuned − base) per weight matrix.

---

## Tokenizer Configuration

### Modern (recommended)

```yaml
tokenizer:
  source: union          # merge vocabularies from all models
  tokens:
    <|im_start|>:
      source: chatml_model_path
    <|im_end|>:
      source: chatml_model_path
    <|eot_id|>:
      source: llama3_model_path
      force: true        # use this embedding for ALL models, not just missing ones
```

Token embedding resolution order when a model is missing a token:
1. Base model embedding (if base model has it)
2. Single-model embedding (if only one model has it)
3. Average of all available embeddings

`force: true` bypasses this — locks the embedding to the specified source regardless.

### Token source kinds

```yaml
tokens:
  <|special|>:
    source:
      kind: model_token          # remap from another token's embedding
      model: path/to/model
      token: "<|original_token|>"
  <|unused|>:
    source:
      kind: zero                 # zero-initialize
```

### Legacy (backward compat)

```yaml
tokenizer_source: union   # or "base" or a model path
```

---

## Multi-Stage Merging

For complex workflows: merge A+B → intermediate, then merge intermediate+C.

```yaml
# multi_config.yml
stages:
  - name: stage_1
    config_file: stage1.yml
    output_path: ./stage1_output
  - name: stage_2
    config_file: stage2.yml
    output_path: ./final_output
```

Stage 2 config can reference `./stage1_output` as a model path.

```bash
mergekit-multi multi_config.yml ./final_output
```

---

## Evolutionary Merge (Optional, install with `[evo]`)

Uses CMA-ES or PGPE to optimize per-layer, per-model weights and densities against a benchmark. Requires `ray`.

```bash
mergekit-evolve evolve_config.yml --max-fevals 100 --storage-path ./evo_cache
```

Evolutionary config wraps a base merge config with a search space definition and evaluation task list. Compute-heavy — best with GPU and patience. Use when you have a specific eval target and want to avoid manual sweep.

---

## Workflow

```
1. Environment
   pip install -e . [--cuda flag if GPU]
   huggingface-cli login

2. Config
   Write YAML → validate mentally: method ↔ base_model ↔ model count constraints

3. Run (dry pass first)
   mergekit-yaml config.yml ./output --allow-crimes --lazy-unpickle
   # on GPU:
   mergekit-yaml config.yml ./output --cuda

4. Evaluate
   # quick sanity: load and generate
   from transformers import pipeline
   pipe = pipeline("text-generation", model="./output", device_map="auto")
   print(pipe("Hello, I am", max_new_tokens=50))

   # benchmark: run lm-evaluation-harness or eleuther eval
   lm_eval --model hf --model_args pretrained=./output --tasks hellaswag,mmlu --device cuda

5. Upload
   huggingface-cli upload username/model-name ./output .
```

---

## Common Failure Modes

| Symptom | Likely Cause | Fix |
|---|---|---|
| Output repeats or degenerates | Weights don't sum near 1.0; density too low | Normalize weights; raise density to 0.6–0.8 |
| Architecture mismatch error | Models have different hidden dims or num layers | Use `--allow-crimes` (with caution) or pick compatible models |
| OOM on GPU | Full models loaded | Add `--lazy-unpickle`; reduce to CPU (`--no-cuda`) |
| Tokenizer vocab errors | Union of mismatched tokenizers | Pin `tokenizer.source: base`; use `tokens:` overrides for specials |
| LoRA extraction rank too low | SVD approximation loses too much | Increase `--rank`; check `||A - UV^T|| / ||A||` reconstruction error |
| Task arithmetic adds noise | Base model mismatch | Verify all fine-tunes derive from the *same* base checkpoint |
| TIES/DARE worse than baseline | Density too aggressive | Raise density; try `dare_ties` → `della` |
| Frankenmerge garbles output | Layer boundary at wrong depth | Move boundary to even block boundary (attention + MLP pair) |

---

## Parameter Sweep Starting Points

| Method | density | weight |
|---|---|---|
| `ties` | 0.5–0.7 | equal-split |
| `dare_ties` | 0.5–0.6 | equal-split, sum ~1.0 |
| `della` | 0.6, epsilon=0.1 | 1.0 per model, lambda=1.0 |
| `breadcrumbs_ties` | 0.6, gamma=0.01 | equal-split |
| `slerp` | — | t=0.5 |
| `task_arithmetic` | — | 0.5–0.7, lambda=1.0 |

General rule: for 2-model blends, start with `nuslerp` or `dare_ties`. For 3+ models with a known base, start with `dare_ties`. If delta magnitudes are large, use `della`.

---

## Notes

- `dtype: bfloat16` is the practical default — avoids fp16 overflow, matches most modern training.
- Models must be in HuggingFace safetensors format (or convertible). GGUF is not directly supported.
- mergekit writes a `README.md` model card automatically — edit before uploading.
- The `parameters` gradient feature (list of floats) is underused and often effective — ramp `weight` or `density` across depth to let different layers contribute at different rates.
- For GRPO/DPO fine-tunes: DELLA tends to outperform DARE because RLHF deltas concentrate magnitude in specific parameter directions.
