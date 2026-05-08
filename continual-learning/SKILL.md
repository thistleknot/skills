---
name: continual-learning
description: >
  Prevent catastrophic forgetting when a model or agent is updated across multiple
  tasks, domains, or environments. Covers regularization (EWC), episodic buffer
  methods (GEM/A-GEM), architecture-based isolation (PackNet), LoRA-based adapter
  stacking (O-LoRA, InfLoRA), post-hoc model merging (DARE), knowledge distillation
  (LwF), and non-parametric frozen-backbone approaches (MemRL). Exposes each as a
  composable module. Use when sequential fine-tuning would degrade previously
  learned capabilities. Absorbs integrate/MemRL (arXiv:2601.03192).
status: active
last_validated: 2026-05-07
absorbs: [integrate/MemRL]
---

# Continual Learning

## When to Use

Use continual-learning when:

- Fine-tuning an LLM on domain *D2* that will degrade performance on domain *D1*
- Training a DQN/agent on environment *E2* after mastering *E1*
- Incrementally adding new task capabilities to a deployed model without full retraining
- Agent memory must update across episodes without overwriting prior competencies
- You need to merge multiple task-specific adapters into a single model

Do **not** use when:
- Full retraining from scratch is feasible and affordable
- `procedural-memory` EMA is sufficient (traces, not weights, need updating)
- The model is called via API only (no weight access) → use MemRL or `agentic_kg_memory` instead

---

## Stability-Plasticity Decision Tree

```
Do you have access to model weights?
        │
   NO ──┴── YES
   │              │
   ▼              ├─► How many past tasks must be preserved?
MemRL             │
(frozen LLM +     ├─ 1–3 tasks, small model → EWC
 Q-value memory)  │
                  ├─ 3–10 tasks, ~500 examples/task buffer OK → A-GEM
                  │
                  ├─ Many tasks, task ID available at inference → PackNet
                  │
                  ├─ LLM, PEFT only, no replay buffer → O-LoRA / InfLoRA
                  │
                  ├─ Have per-task adapters, want single merged model → DARE
                  │
                  └─ No replay allowed (privacy) → LwF (distillation only)
```

---

## Six Approaches

### 1. EWC — Elastic Weight Consolidation
**arXiv:** `1612.00796` (PNAS 2017)

After training on task *T*, compute Fisher information diagonal *F_i* to measure
each weight's importance. When learning task *T+1*, add a quadratic penalty:
```
L = L_new + (λ/2) Σ_i F_i (θ_i − θ*_i)²
```
Weights crucial for task *T* (high *F_i*) are penalized if they deviate from *θ\*_T*.

```python
from avalanche.training import EWC

strategy = EWC(
    model, optimizer, criterion,
    ewc_lambda=0.4,
    train_mb_size=32, train_epochs=1, eval_mb_size=32
)
for experience in scenario.train_stream:
    strategy.train(experience)
```

**Limitations:** Fisher diagonal approximation; only penalizes single prior task without
multi-task memory; computationally heavy for large models.

---

### 2. GEM / A-GEM — Gradient Episodic Memory
**GEM arXiv:** `1706.08840` (NeurIPS 2017) | **A-GEM arXiv:** `1812.00420` (ICLR 2019)

Maintain an episodic buffer *M_k* of examples from each past task. Before applying
a gradient step on task *T+1*, project the gradient so it does **not increase loss**
on any stored *M_k*:
```
GEM: min ||g̃ − g||² s.t. ⟨g̃, g_k⟩ ≥ 0 ∀k   (QP per task)
A-GEM: project only if ⟨g, g_ref⟩ < 0          (single avg constraint)
```

A-GEM is nearly as accurate as GEM at a fraction of the compute cost.

```python
from avalanche.training import AGEM

strategy = AGEM(
    model, optimizer, criterion,
    patterns_per_exp=500, sample_size=64,
    train_mb_size=32, train_epochs=1
)
```

---

### 3. PackNet — Structured Pruning + Binary Masking
**arXiv:** `1711.05769` (CVPR 2018)

After training task *T*:
1. Prune a fraction of weights (set to zero, free capacity)
2. Binary-mask the remaining active weights as "owned by task T" (frozen forever)
3. Train task *T+1* using only free (unmasked) parameters

Zero forgetting by construction. Requires task ID at inference. Scales to ~3 tasks
per 100M-parameter model before running out of capacity.

**DQN application:** Prune DQN after mastering environment *E1*, free ~30% weights,
freeze *E1* mask, train *E2* in freed capacity.

---

### 4. O-LoRA / InfLoRA — Orthogonal LoRA Adapters
**O-LoRA arXiv:** `2310.14152` (EMNLP 2023) | **InfLoRA arXiv:** `2404.00228` (CVPR 2024)

Each task gets its own LoRA adapter *(A_k, B_k)*. Task interference is prevented by:
- **O-LoRA:** project new adapter update to be orthogonal to subspace of all prior adapters
- **InfLoRA:** analytically construct a subspace that provably eliminates cross-task interference

No replay data required. Works with HuggingFace PEFT:

```python
pip install peft

from peft import get_peft_model, LoraConfig, TaskType

# Per-task adapter — repeat for each new task, then orthogonalize subspaces
config = LoraConfig(task_type=TaskType.CAUSAL_LM, r=16,
                    lora_alpha=32, lora_dropout=0.1)
model_task_k = get_peft_model(base_model, config)
```

**Best for:** LLM fine-tuning when replay buffer is unavailable or privacy-constrained.

---

### 5. DARE — Delta-Param Sparsification + Model Merge
**arXiv:** `2311.03099` (ICML 2024)

Post-hoc CL via model merging: train separate LoRA adapters per task independently
(no sequential forgetting), then merge into a single model:
1. For each adapter: randomly drop p% of delta parameters, rescale remaining by 1/(1-p)
2. Average merged delta parameters across all tasks

```python
# Example using merge-kit or manual DARE
delta_params = [adapter_k.weight - base.weight for k in tasks]
for delta in delta_params:
    mask = torch.rand_like(delta) > p          # drop p fraction
    delta = delta * mask / (1 - p)             # rescale
merged_delta = sum(delta_params) / len(delta_params)
final_model.weight = base.weight + merged_delta
```

Scales better in larger models (7B+). Not truly online CL — requires all adapters
available at merge time.

---

### 6. LwF — Learning without Forgetting
**arXiv:** `1606.09282` (ECCV 2016 / TPAMI 2017)

Use the frozen old model as a soft-label teacher on new task data:
```
L = L_CE(new_task) + λ · KL(f_old(x), f_new(x))
```
No old data required — teacher's soft predictions on new data preserve old task behavior.

**DER/DER++** (NeurIPS 2020): also store logit vectors in replay buffer for
even stronger distillation. Available in Mammoth as `der` / `derpp`.

---

## MemRL — Non-Parametric CL for Agents
**arXiv:** `2601.03192` (ICML 2026)
**Code:** `github.com/MemTensor/MemRL`

MemRL solves stability-plasticity by **never touching backbone LLM weights**.
Memory entry: `(Intent, Experience, Q-value)`.

**Two-phase retrieval:**
1. **Semantic:** embed current task → retrieve candidate pool via vector similarity
2. **Utility:** within pool, rank by learned Q-value (expected reward for using that memory)

**Q-value update after task execution:**
```python
Q(s, a) = Q(s, a) + α * (reward - Q(s, a))   # Monte Carlo update
```

Over time, high-utility memories accumulate high Q-values; noise/failures are
deprioritized despite semantic similarity to new tasks.

**Why it doesn't forget:** backbone weights are frozen (stability guaranteed);
plasticity comes from evolving memory Q-values.

**Benchmarks:** Outperforms fine-tuning + RAG on HLE (hard reasoning), BigCodeBench,
ALFWorld (embodied navigation), and Lifelong Agent Bench.

**Integration with deep-q-rl:** MemRL's Q-value memory update mirrors the AHA
correction mechanism in `deep-q-rl`. Natural composition: use MemRL for long-term
non-parametric memory; use `deep-q-rl` for short-term value-based planning.

---

## Production Libraries

| Library | Install | Methods | Stars |
|---|---|---|---|
| **Avalanche** | `pip install avalanche-lib` | EWC, GEM, A-GEM, LwF, Replay, full benchmark suite | ~2000 |
| **Mammoth** | clone + `pip install -r requirements.txt` | 70+ methods including DER/DER++, ICLR 2026 additions | active |
| **HuggingFace PEFT** | `pip install peft` | LoRA adapters (backbone for O-LoRA/InfLoRA) | >18000 |

---

## CL Regimes for LLMs (Survey: arXiv:2402.01364)

| Regime | Setting | Best Method |
|---|---|---|
| Continual pre-training | Domain adaptation at scale | LwF + replay subset |
| Continual instruction tuning | New task types added incrementally | O-LoRA / InfLoRA |
| Continual alignment | RLHF updates without degrading safety | DARE merge |
| Continual RL | Multi-environment sequential training | EWC on DQN, or MemRL (non-parametric) |
| Agent lifelong learning | Open-ended skill accumulation | Voyager pattern (skill library) or MemRL |

---

## Interface Contract

```yaml
inputs:
  model: nn.Module
  task_stream: list[Dataset]
  method: ewc | gem | agemom | packnet | o_lora | inf_lora | dare | lwf | memrl
  buffer_size: int?           # for GEM/A-GEM (examples per past task)
  ewc_lambda: float?          # for EWC regularization strength
  lora_rank: int?             # for O-LoRA/InfLoRA
  dare_p: float?              # drop fraction for DARE (default 0.9)

outputs:
  updated_model: nn.Module
  bwt: float                  # backward transfer (forgetting metric)
  fwt: float                  # forward transfer (new task facilitation)
  per_task_accuracy: dict

preconditions:
  - model weights are accessible (not API-only) — else use MemRL
  - for PackNet: task_id available at inference

postconditions:
  - bwt >= -0.05 (less than 5% forgetting on prior tasks)
  - per_task_accuracy reported for all tasks seen so far

invariants:
  - PackNet masks are never modified after being set
  - MemRL never modifies backbone weights
```

---

## Integration with Skill Library

| Concern | Skill |
|---|---|
| Agent memory without weight updates | `agentic_kg_memory` + MemRL pattern |
| Trace-level forgetting prevention | `procedural-memory` (EMA-based) |
| Multi-environment RL | `deep-q-rl` (add EWC/PackNet wrapper) |
| Synthetic data to reduce forgetting replay cost | `synthetic-data` |
| Fine-tuning after synthetic SFT | this skill |

---

## Evidence

- Kirkpatrick et al. arXiv:1612.00796 (PNAS 2017): EWC, sequential Atari + MNIST
- Lopez-Paz & Ranzato arXiv:1706.08840 (NeurIPS 2017): GEM, defines BWT/FWT metrics
- Chaudhry et al. arXiv:1812.00420 (ICLR 2019): A-GEM, efficient gradient projection
- Mallya & Lazebnik arXiv:1711.05769 (CVPR 2018): PackNet, zero forgetting by construction
- Wang et al. arXiv:2310.14152 (EMNLP 2023): O-LoRA, orthogonal subspace learning
- Liang & Li arXiv:2404.00228 (CVPR 2024): InfLoRA, interference-free subspace
- Yu et al. arXiv:2311.03099 (ICML 2024): DARE, model merging post-hoc CL
- Zhang et al. arXiv:2601.03192 (ICML 2026): MemRL, outperforms fine-tuning+RAG
- Wang et al. arXiv:2305.16291: Voyager lifelong skill library in Minecraft
- Wu et al. arXiv:2402.01364: CL regimes survey for LLMs
- `ContinualAI/avalanche`: `pip install avalanche-lib`
- `aimagelab/mammoth`: 70+ methods, clone + requirements install
<!-- consolidation:see-also:start -->
## See Also
<!-- consolidation:see-also:end -->
