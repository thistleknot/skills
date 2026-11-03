---
name: synthetic-data
description: >
  Structured pipeline for generating high-quality synthetic training data for LLM
  fine-tuning and agent training. Covers eight generation paradigms (Self-Instruct,
  Evol-Instruct, GLAN, Magpie, agent trajectory synthesis, preference data via
  UltraFeedback) implemented in distilabel. Includes mandatory quality gates:
  deduplication, LLM-as-judge scoring, IFD filtering, and coverage auditing.
  Pairs with stratified-quota-sampling and class-balancing for distribution control.
status: active
last_validated: 2026-05-07
---

# Synthetic Data

## When to Use

Use synthetic-data when:

- No labeled data exists and you need to bootstrap a fine-tuning set (Self-Instruct from seeds)
- Real data is too simple for the target capability level (Evol-Instruct complexity escalation)
- You need controlled taxonomic coverage across domains (GLAN syllabus approach)
- Agent trajectory data is scarce (FireAct-style GPT-4 trace generation + distillation)
- Preference pairs for DPO/RLHF are needed without human annotation (UltraFeedback)
- Training data privacy constraints prevent using real examples

Do **not** use when:
- Annotated real data is available, fast to produce, and covers the target distribution
- Creative writing / nuanced safety judgment is required (real human preference data is better)
- Model collapse risk is high and you cannot afford a strong teacher model (GPT-4 minimum)

**Model collapse rule:** Training iteratively on purely synthetic data without diversity
and quality gates degrades outputs (arXiv:2305.17493). A strong fixed teacher model
(GPT-4, Llama-3-70B) is required — self-distillation from the model being trained will collapse.

---

## Eight Generation Paradigms

### 1. Self-Instruct — arXiv:2212.10560 (ACL 2023)
Iterative bootstrapping from 175 seed tasks. LLM generates (instruction, input, output)
triples → ROUGE-L dedup filter (threshold 0.7) → add survivors to pool → repeat.
**Best for:** Zero-resource bootstrap; no labeled data exists.
**distilabel:** `SelfInstruct` task class

```python
from distilabel.steps.tasks import SelfInstruct
task = SelfInstruct(llm=..., num_instructions=5,
                    application_description="Domain description")
```

---

### 2. Evol-Instruct / WizardLM — arXiv:2304.12244 (ICLR 2024)
Evolves instructions along two axes:
- **In-depth:** add constraints, deepen reasoning, increase reasoning steps
- **In-breadth:** generate new topics/domains inspired by the original

WizardMath (arXiv:`2308.09583`, ICLR 2025 oral) applies this to math with RLEIF —
outperforms GPT-3.5-Turbo on GSM8k.

**Best for:** Complexity-gradient data; hard problem generation.
**distilabel:** `EvolInstruct` / `EvolInstructGenerator`

```python
from distilabel.steps.tasks import EvolInstruct
task = EvolInstruct(llm=..., num_evolutions=3,
                    store_evolutions=True, generate_answers=True)
```

---

### 3. GLAN — arXiv:2402.13064 (2024)
Taxonomy-driven, seed-free synthesis: build knowledge taxonomy (fields → disciplines),
then per discipline → subject list → syllabus → key concepts → instructions.
**Best for:** Guaranteed taxonomic coverage; no existing datasets needed.

---

### 4. Magpie — arXiv:2406.08464 (2024)
Feed an aligned model only the left-side chat template up to the user turn; its
autoregressive generation naturally produces realistic user queries. Generated 4M
instructions; outperforms prior SFT+DPO datasets on AlpacaEval/ArenaHard.
**Best for:** High-diversity instruction generation from aligned models without seeds.
**distilabel:** `MagpieBase` / `MagpieGenerator`

---

### 5. Preference Data for DPO/RLHF

**UltraFeedback** (arXiv:`2310.01377`, ICML 2024): 250K conversations, 1M+ GPT-4
annotations. Generates chosen/rejected pairs for DPO. **distilabel:** `UltraFeedback`.

**Self-Rewarding LMs** (arXiv:`2401.10020`, ICML 2024): LLM acts as its own judge;
eliminates separate frozen reward model. Iterative DPO with self-generated preference data.

**DEITA** (arXiv:`2312.15685`, ICLR 2024): 3-axis selection (complexity + quality +
diversity) — 6K well-selected examples beats 60K+ raw examples.

---

### 6. Code-Specific Synthesis

**Phi-1** (arXiv:`2306.11644`): Synthetic "textbook quality" exercises via GPT-3.5.
1.3B param model achieves 50.6% HumanEval pass@1. Data quality > data quantity.

**OSS-Instruct / Magicoder** (arXiv:`2312.02120`, ICML 2024): Open-source code
snippets as seeds → coding instructions. 7B model beats ChatGPT on HumanEval+ (66.5 vs 65.9).

---

### 7. Agent Trajectory Synthesis (FireAct) — arXiv:2310.05915
1. Use GPT-4 to solve tasks in ReAct format (Thought→Action→Observation loops)
2. Filter trajectories that reach the correct final answer
3. Fine-tune smaller model on surviving traces (behavioral cloning)

Fine-tuning 500 GPT-4 ReAct traces into Llama2-7B → +77% HotpotQA performance.

**CodeAct** (arXiv:`2402.01030`, ICML 2024): Python code as action space. 7K multi-turn
interaction trajectories; +20% over text/JSON agents.

---

### 8. Persona Hub — arXiv:2406.20094
1B diverse personas auto-curated from web data as distributional carriers of world
knowledge. Persona-conditioned generation unlocks near-unlimited instruction diversity.

---

## Production Library: distilabel

```
pip install distilabel[openai,hf-inference-endpoints,vllm]
```

**Repo:** `argilla-io/distilabel` — research-paper-backed pipeline DAG; HF Hub export.

```python
from distilabel.pipeline import Pipeline
from distilabel.steps.tasks import EvolInstruct, UltraFeedback
from distilabel.models import InferenceEndpointsLLM

with Pipeline() as pipeline:
    evol = EvolInstruct(
        llm=InferenceEndpointsLLM(model_id="meta-llama/Llama-3.1-70B-Instruct"),
        num_evolutions=3,
        generate_answers=True,
    )
    uf = UltraFeedback(
        llm=InferenceEndpointsLLM(model_id="gpt-4o"),
        aspect="overall-rating",
    )
    evol >> uf  # DAG: evolve → score → preference pairs

distiset = pipeline.run(dataset=seed_dataset)
distiset.push_to_hub("org/my-synthetic-dataset")
```

**Task classes available:**
`SelfInstruct`, `EvolInstruct`, `MagpieGenerator`, `UltraFeedback`, `PrometheusEval`,
`ComplexityScorer`, `QualityScorer`, `InstructionBacktranslation`, `GenerateEmbeddings`

---

## Mandatory Quality Gates

Run in order; discard before next stage:

```
Generated → [Dedup] → [Schema] → [LLM Judge] → [IFD] → [Coverage] → [Safety] → Training
```

### 1. Deduplication
```python
pip install distilabel[minhash]
# MinHash LSH + ROUGE-L self-similarity ≥ 0.7 → discard
# Embedding cosine similarity ≥ 0.95 → discard
```

### 2. Schema / Format Validation
JSON schema for tool calls; Python AST parse + compile check for code;
length bounds (< 20 tokens or > context window); multi-turn minimum 2 turns.

### 3. LLM-as-Judge Scoring
`UltraFeedback` (1–5 helpfulness/honesty/instruction-following) or `PrometheusEval`.
Threshold: discard score < 4.0/5.0 or bottom quartile.

### 4. IFD — Instruction Following Difficulty
```
IFD = PPL(response | instruction) / PPL(response)
```
High IFD → instruction adds constraint (keep). Low IFD → trivial (discard).

### 5. Coverage Audit
```python
pip install vendi-score
# Cluster via k-means / UMAP on GenerateEmbeddings output
# Vendi score target above domain threshold; KL divergence from target distribution
# Sparse clusters (< 10 examples) → trigger targeted re-generation
```

### 6. Safety / Bias Check
Toxicity scoring; demographic parity audit; refusal classifier on preference pairs.

---

## Distribution Control Handoff

```
[synthetic-data]          [stratified-quota-sampling]     [class-balancing]
Generate N raw        →   Balance category counts     →   Reweight residual skew
examples per category     (Box-Cox + Fibonacci tiers)     in CrossEntropyLoss
                          UltraFeedback score as
                          weight_key
```

```python
balanced = stratified_quota_sample(
    class_items=generated_by_category,    # {category: [examples]}
    weight_key="ultrafeedback_score",
    quotas={"LOW": 50, "MID": 80, "HIGH": 130},  # Fibonacci tiers
)
```

---

## Interface Contract

```yaml
inputs:
  seed_pool: list[str]
  taxonomy: dict?
  generation_strategy: self_instruct | evol_instruct | magpie | glan | oss_instruct | trajectory
  teacher_model: str          # GPT-4 or Llama-3-70B minimum
  num_evolutions: int         # default 3
  quality_threshold: float    # default 4.0/5.0
  dedup_threshold: float      # default 0.7
  target_distribution: dict?

outputs:
  generated_dataset: Dataset  # columns: instruction, response, quality_score, category
  coverage_report: dict
  quality_report: dict

preconditions:
  - teacher_model is GPT-4-class (≥70B instruction-tuned)
  - seed_pool not empty (min 10 seeds for self_instruct)

postconditions:
  - all six quality gates executed before output
  - coverage_report flags categories below 10 examples

invariants:
  - never train on outputs from the model being trained (collapse)
  - dedup always runs before LLM judge scoring
```

---

## Integration with Skill Library

| Phase | Skill |
|---|---|
| Balance generated category distribution | `stratified-quota-sampling` |
| Reweight loss on residual class skew | `class-balancing` |
| Tune num_evolutions, quality threshold | `optuna-nested-cv` |
| Track generation experiments | `mlflow` |
| Generate agent trajectory format | `react_agent` (ReAct trace source) |
| Evaluate generated set quality | `checklist` |
| Fine-tune with synthetic SFT data | `continual-learning` (prevent forgetting) |

---

## Evidence

- Wang et al. arXiv:2212.10560 (ACL 2023): Self-Instruct +33% over vanilla GPT-3
- Xu et al. arXiv:2304.12244 (ICLR 2024): Evol-Instruct / WizardLM
- Liu et al. arXiv:2402.13064: GLAN taxonomy-driven coverage
- Xu et al. arXiv:2406.08464: Magpie pre-query extraction, 4M examples
- Cui et al. arXiv:2310.01377 (ICML 2024): UltraFeedback 1M GPT-4 annotations
- Liu et al. arXiv:2312.15685 (ICLR 2024): DEITA 6K selected > 60K raw
- Gunasekar et al. arXiv:2306.11644: Phi-1 textbook quality, 50.6% HumanEval pass@1
- Wei et al. arXiv:2312.02120 (ICML 2024): Magicoder beats ChatGPT on HumanEval+
- Chen et al. arXiv:2310.05915: FireAct +77% HotpotQA with 500 GPT-4 traces
- Shumailov et al. arXiv:2305.17493: model collapse from iterative self-distillation
- `argilla-io/distilabel`: `pip install distilabel[openai,hf-inference-endpoints,vllm]`
<!-- consolidation:see-also:start -->
## See Also
[[model-size-reduction]]  [[tdd-agent]]  [[agentic-harness]]
<!-- consolidation:see-also:end -->
