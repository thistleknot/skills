---
name: uncertainty-quantification
description: >
  Structured UQ protocol for LLM outputs: three-tier sampling consistency
  (semantic entropy, SelfCheckGPT), conformal prediction sets, and verbalized
  confidence. Produces a recommendation: proceed / proceed_with_caveat /
  abstain / escalate. Use before any agent commits to an irreversible action
  based on LLM-generated content, or when hallucination risk must be surfaced.
  Distinct from checklist (structured audit of an artifact) and validation
  (test execution). Pair with agent-governance for the policy enforcement layer.
status: active
last_validated: 2026-05-07
---

# Uncertainty Quantification

## When to Use

Use uncertainty-quantification when:

- The agent is about to **commit an irreversible action** (write, delete, send, deploy)
  and the decision was informed by LLM output
- Building a **selective-generation system** that should abstain rather than hallucinate
- Evaluating **factual claims** in a RAG pipeline before surfacing to users
- Deciding whether to **retrieve more context** or accept the current generation
- The downstream consumer needs a **calibrated confidence score**, not just an answer

Do **not** use when:
- Speed is critical and the action is trivially reversible (just rerun if wrong)
- The question has a deterministic, checkable answer → use `validation` or `tdd-agent`
- You're evaluating output quality (correctness, style) → use `checklist` or `evaluator-optimizer`

---

## Three-Tier Protocol

```
┌─────────────────────────────────────────────────────────────────┐
│ TIER 1 — FAST (always run, ~0 extra tokens)                     │
│  IF white-box: mean_token_entropy via logprobs                  │
│  IF black-box: "Rate your confidence 0–100%. [answer]"          │
│  Cost: negligible.                                              │
│  Threshold: entropy > 0.7 OR verbal < 60% → flag ⚠              │
├─────────────────────────────────────────────────────────────────┤
│ TIER 2 — STANDARD (stakes matter, ~3–5 extra samples)           │
│  Sample N=3–5 at temperature 0.7–1.0                            │
│  Compute SelfCheckGPT-NLI or EigValLaplacian (black-box)        │
│  Cost: 3–5× inference.                                          │
│  Threshold: inconsistency score > 0.5 → flag ⚠⚠                 │
├─────────────────────────────────────────────────────────────────┤
│ TIER 3 — THOROUGH (irreversible actions, high-stakes domains)   │
│  White-box: full semantic entropy (N=10) with NLI clustering    │
│  Black-box: Conformal Factuality back-off algorithm             │
│  Cost: 10× inference + small NLI model                          │
│  Threshold: SE > 1.5 nats → escalate to human                   │
└─────────────────────────────────────────────────────────────────┘
```

**Always use Tier 3 minimum when the action is irreversible**, regardless of
how confident the model appears on Tier 1.

---

## Seven UQ Paradigms

### 1. Semantic Entropy
**arXiv:** `2302.09664` (ICLR 2023 Spotlight); extended to **Nature 2024**
**Code:** `github.com/jlko/semantic_uncertainty` — runnable research code
**Requirement:** white-box (logprobs)

```
1. Sample N responses at T > 0
2. Cluster via NLI: rᵢ, rⱼ same cluster iff bidirectional entailment
3. P(cluster_k) ∝ sum of sequence likelihoods in cluster
4. SE = -Σ_k P(cluster_k) log P(cluster_k)
```

High SE = semantically diverse outputs = likely hallucination.
Outperforms token-level entropy because "London" and "The capital of England"
cluster together despite different token distributions.

**Black-box approximation:** EigValLaplacian (arXiv:`2305.19187`, TMLR 2024) —
graph spectral method over pairwise NLI similarity; no logprobs needed.
Code: `github.com/zlin7/UQ-NLG`

---

### 2. SelfCheckGPT
**arXiv:** `2303.08896` (EMNLP 2023)
**Library:** `pip install selfcheckgpt` (MIT)

Checks whether a sentence in the response is consistent with independently
sampled passages (no logprobs needed — black-box compatible).

| Variant | Mechanism | Recommended? |
|---|---|---|
| SelfCheck-Prompt | Ask LLM "Is this sentence supported?" | ✅ Best accuracy |
| SelfCheck-NLI | DeBERTa contradiction probability | ✅ Fast, no extra API |
| SelfCheck-BERTScore | BERTScore similarity | Fast, approximate |

```python
from selfcheckgpt.modeling_selfcheck import SelfCheckNLI

selfcheck = SelfCheckNLI(device="cpu")
sentences = ["Paris is the capital of France.", "The Eiffel Tower is 400m tall."]
scores = selfcheck.predict(
    sentences=sentences,
    sampled_passages=sampled_passages  # N=3–5 independent samples
)
# scores[i] ≈ probability sentence i is inconsistent with the samples
```

---

### 3. Verbalized Confidence
**arXiv:** `2305.14975` (EMNLP 2023 — "Just Ask for Calibration")

For RLHF-tuned models (GPT-4, Claude), verbalized confidences are
**better calibrated than token-level logprobs** — RLHF training shifts the
log-probability distribution, breaking logprob-based calibration.

```python
prompt = f"Answer the following question and rate your confidence (0–100%): {question}"
# or two-step: answer first, then ask for confidence separately
```

Threshold: verbal < 60% = proceed_with_caveat; < 40% = abstain.

P(True) (arXiv:`2207.05221`, Kadavath/Anthropic): "Is this answer correct?
True/False" → P(True) as confidence. Available in LM-Polygraph.

---

### 4. Conformal Prediction
**arXiv:** `2306.10193` (ICLR 2024 — Conformal Language Modeling)
**arXiv:** `2402.10978` (Conformal Factuality — back-off algorithm)

Returns a **set** of candidates that contains at least one acceptable answer
with statistical coverage guarantee ≥ 1 - α (distribution-free).

Conformal Factuality progressively makes outputs less specific until the
entailment set hits the desired confidence level:
`"Paris" → "a city in France" → "in Europe"` (80–90% correctness guarantees on QA).

**Best for:** High-stakes factual claims where you need statistical guarantees,
not just a point estimate.

---

### 5. R-Tuning — Refusal-Aware Fine-Tuning
**arXiv:** `2311.09677` (NAACL 2024 Outstanding Paper)
**Code:** `github.com/shizhediao/R-Tuning`

Fine-tuning approach: identify knowledge gaps in base model, construct refusal-
aware training examples ("I'm not sure but…" for unknown questions), fine-tune.
Refusal generalizes as a meta-skill to out-of-domain tasks.

**Use when:** You own and can fine-tune the model, and the deployment domain
has known failure modes. Better calibration than test-time prompting alone.

---

### 6. Input Clarification Ensembling
**arXiv:** `2311.08718` (ICML 2024)
**Code:** `github.com/UCSB-NLP-Chang/llm_uncertainty`

Generates diverse **clarifications of the input** → feeds each to the same LLM
→ ensembles outputs. Decomposes total uncertainty into:
- **Aleatoric** (irreducible from input ambiguity)
- **Epistemic** (from model knowledge gap)

Requires only one LLM copy (unlike true deep ensembles).

---

### 7. LM-Polygraph (Unified Library)
**arXiv:** `2406.15627` (TACL 2025)
**Library:** `pip install lm-polygraph`
**Repo:** `IINemo/lm-polygraph`

20+ UQ estimators in one library; works with HuggingFace (white-box) and
OpenAI-compatible APIs (black-box).

```python
from lm_polygraph.estimators import (
    SemanticEntropy,          # white-box, high compute (Kuhn 2023)
    EigValLaplacian,          # black-box (Lin 2023)
    VerbalisedUncertainty1S,  # black-box, fast (Tian 2023)
    MeanTokenEntropy,         # white-box, fast
    PTrue,                    # white-box (Kadavath 2022)
)
```

---

## Abstain / Escalate Decision Table

| Signal | Threshold | Recommendation |
|---|---|---|
| Verbal confidence ≥ 80% + low token entropy | — | **Proceed** |
| Verbal confidence 50–79% OR SelfCheck 0.2–0.5 | moderate inconsistency | **Proceed with caveat** |
| Verbal confidence < 50% | — | **Seek clarification / retrieve context** |
| SelfCheck-NLI > 0.6 | high contradiction rate | **Flag hallucination risk; do not act** |
| Semantic entropy > 1.5 nats | strong predictor of error | **Abstain** |
| Conformal set size > K (domain-calibrated) | — | **Escalate to human** |
| Action is irreversible | — | **Always Tier 3 minimum** |

---

## Interface Contract

```yaml
# Behavioral contract

inputs:
  response: string
  query: string
  model_access: white-box | black-box
  budget: fast | standard | thorough
  samples: list[string]?   # optional pre-computed N=3–5 samples

outputs:
  uncertainty_score: float    # [0.0=certain, 1.0=maximally uncertain]
  method_used: string
  recommendation: proceed | proceed_with_caveat | abstain | escalate
  signals:
    token_entropy: float?
    verbal_confidence: float?
    semantic_consistency: float?
    num_semantic_sets: int?
  rationale: string

preconditions:
  - response != "" and query != ""
  - budget="fast" requires no sampling
  - model_access="white-box" requires logprobs

postconditions:
  - uncertainty_score is monotone with error rate on calibration set
  - recommendation="abstain" iff uncertainty_score >= 0.8
  - recommendation="escalate" iff irreversible AND uncertainty_score >= 0.5

invariants:
  - semantic_consistency only computed if budget != "fast"
  - never raise uncertainty_score purely from response length
  - this skill is read-only; does not modify LLM state
```

---

## Library Reference

| Method | Status | Install |
|---|---|---|
| SelfCheckGPT | ✅ PyPI package | `pip install selfcheckgpt` |
| LM-Polygraph (20+ methods) | ✅ PyPI package | `pip install lm-polygraph` |
| Semantic Entropy | ✅ Research code | `github.com/jlko/semantic_uncertainty` |
| EigValLaplacian / UQ-NLG | ✅ Research code | `github.com/zlin7/UQ-NLG` |
| R-Tuning | ✅ Training code | `github.com/shizhediao/R-Tuning` |
| SaySelf | ✅ Code released | `github.com/xu1868/SaySelf` |
| Conformal Factuality | ⚠️ Paper-only | arXiv:2402.10978 |
| Deep ensembles | ⚠️ Prohibitive VRAM | LM-Polygraph has token-level variant |

---

## Integration with Skill Library

| Context | Skill |
|---|---|
| Irreversible agent actions | Pair with `agent-governance` for policy enforcement |
| RAG / retrieval pipelines | Feed UQ score to `gist-retriever` for selective retrieval |
| Self-improving loops | Feed abstain signals to `evaluator-optimizer` as "redo" trigger |
| Agentic harness gates | Use as a pre-action coherence check in `agentic-harness` |
| Output evaluation | `checklist` for structured critique; UQ for probabilistic reliability |

---

## Evidence

- Kuhn et al. arXiv:2302.09664 (ICLR 2023 Spotlight): semantic entropy detects hallucinations
- Kuhn et al. Nature 2024: semantic entropy extended and replicated
- Manakul et al. arXiv:2303.08896 (EMNLP 2023): SelfCheckGPT, AUC-PR 93.4%
- Zhang et al. arXiv:2311.09677 (NAACL 2024 Outstanding Paper): R-Tuning refusal calibration
- Tian et al. arXiv:2305.14975 (EMNLP 2023): verbalized > logprob for RLHF models
- Quach et al. arXiv:2306.10193 (ICLR 2024): conformal prediction for LLMs
- Mohri & Hashimoto arXiv:2402.10978: conformal factuality with 80–90% correctness guarantees
- Vashurin et al. arXiv:2406.15627 (TACL 2025): LM-Polygraph 20+ method benchmark
<!-- consolidation:see-also:start -->
## See Also
[[tdd-agent]]  [[evaluator-optimizer]]  [[memory-bank]]
<!-- consolidation:see-also:end -->
