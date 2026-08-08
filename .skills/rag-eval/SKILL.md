---
name: rag-eval
description: >
  Single-pass 10-metric RAG response evaluation via a structured LLM judge.
  One prompt → qwen3.5:4b (Ollama) → Pydantic RAGEvalResult with macro_mean.
  Use whenever a retrieval system needs an answer-quality fitness score:
  retrieval comparison, ablation studies, continuous eval in a training loop.
status: active
last_validated: 2026-05-31
---

# RAG Eval

## When to Use

- Comparing retrieval systems (dense vs BM25 vs hybrid vs reranker)
- Fitness signal inside an autoresearch / hill-climbing loop
- Spot-checking answer quality during RAG pipeline development

---

## Architecture

```
question + answer + context(s) [+ optional ground_truth]
        │
        ▼
  build_prompt()  ──  /no_think prefix + 10-metric definitions
        │
        ▼
  qwen3.5:4b  (Ollama OpenAI-compat endpoint)
  extra_body={"think": False}   ← Ollama-level thinking kill switch
  response_format={"type": "json_object"}
        │
        ▼
  _strip_thinking()  ──  remove <think> bleed, strip markdown fences
        │
        ▼
  RAGEvalResult (Pydantic)  ──  10 floats + computed macro_mean
```

Thinking suppression requires **both**:
- `/no_think` prefix in user message (model-level)
- `extra_body={"think": False}` in the API call (Ollama runtime-level)

---

## Metrics

| Metric | Definition |
|---|---|
| `relevance` | Answer directly addresses the question |
| `entailment` | Answer logically entailed by context (NLI framing) |
| `faithfulness` | All answer claims grounded in context; no hallucination |
| `correctness` | Answer correct relative to `ground_truth`; forced 0.5 when absent |
| `context_entity_precision` | Entities in answer that appear in context |
| `context_entity_recall` | Entities in context captured in answer |
| `factualness` | Accuracy against world knowledge, context-independent |
| `fluency` | Grammatical quality and readability |
| `coherence` | Internal logical consistency; no self-contradiction |
| `informativeness` | Substantive content density; penalises vague filler |
| `macro_mean` | Unweighted mean of the 10 scores (auto-computed) |

`correctness` is post-hoc forced to `0.5` when `ground_truth=None` — the model
cannot reliably abstain when the instruction is only in the prompt.

---

## Usage

```python
from rag_eval import evaluate

result = evaluate(
    question="What causes the greenhouse effect?",
    answer="CO2 and methane trap infrared radiation, warming the atmosphere.",
    context="Greenhouse gases absorb infrared radiation emitted by Earth's surface...",
    ground_truth="Greenhouse gases trap outgoing IR; CO2 and methane are primary.",  # optional
)
print(result.macro_mean)       # scalar fitness
print(result.faithfulness)     # per-metric
print(result.model_dump_json(indent=2))
```

---

## Failure Modes

| Failure | Behaviour |
|---|---|
| JSON parse error | `ValueError` with raw + cleaned response attached |
| Missing metric key | `pydantic.ValidationError` with field name |
| Ollama unreachable | `openai.APIConnectionError` propagates to caller |
| Thinking bleed-through | `_strip_thinking()` removes `<think>` blocks before parse |
| No ground_truth | `correctness` forced to `0.5` post-hoc; macro_mean recomputed |

---

## Implementation

`rag_eval.py` in this folder. CLI smoke test: `python rag_eval.py`

---

## See Also

- `bm25-corpus-sampling` — corpus sampling + retrieval systems that this skill evaluates
- `autoresearch` — uses `macro_mean` as the hill-climbing fitness signal
- `representation-pipeline` — upstream embedding design feeding the retrieval systems
"""
RAG Evaluation Pipeline — Single-Pass 10-Metric Scorer
