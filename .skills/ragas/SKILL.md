---
name: ragas
description: >
  Reproduce ragas-style multi-aspect LLM evaluation with a SINGLE small model and ONE JSON schema
  (a wrapper-based "own version of ragas"), instead of many per-metric LLM calls. Use when building or
  tuning an LLM-as-a-judge that scores a GENERATED ANSWER against a gold reference (+ optional context):
  choosing which ragas metrics apply, folding them into one schema-constrained generation whose ORDERED
  fields emulate sequential ragas calls, and mapping ragas concepts onto deterministic backups. Covers the
  full ragas metric taxonomy with an applies-to-a-single-answer-judge decision for each.
triggers:
  - "ragas"
  - "ragas metrics"
  - "llm as a judge rubric"
  - "answer evaluation vs gold"
  - "faithfulness / factual correctness / response relevancy"
  - "single json schema judge"
  - "context-entity-precision"
metadata:
  status: active
  last_validated: 2026-07-01
  source: docs.ragas.io/en/stable/concepts/metrics/available_metrics
---

# ragas

## Purpose

[ragas](https://docs.ragas.io) is a library of evaluation metrics for LLM apps. Each metric is a *paradigm*
for one aspect of quality; LLM-based metrics spend one or more LLM calls to produce a score. This skill is
for the case where you want ragas-style **multi-aspect** judging but with **one small model** (e.g. a 2B) and
**one JSON schema per (question, gold, context, answer)** — a wrapper-based ragas — because per-metric calls
are too slow/expensive and a single schema-constrained generation is deterministic and cheap.

The key move: **use the JSON schema's field ORDER as the reasoning chain.** Earlier fields (extractions,
sub-judgments) are the evidence the model conditions the final score on — emulating sequential ragas calls
inside one generation. Compute `final_score` LAST.

## The task shape decides which metrics apply

ragas metrics split by what they evaluate. An **answer-vs-gold judge** (our case) evaluates a generated
answer against a gold reference and optional given context. It does NOT retrieve — so **retrieval metrics do
not apply.** Decide per metric:

| ragas metric | group | measures | applies to an answer-vs-gold judge? |
|---|---|---|---|
| Context Precision | RAG-retrieval | are retrieved chunks relevant/ranked | **No** — no retrieval |
| Context Recall | RAG-retrieval | did retrieval cover the gold | **No** |
| Context Entities Recall | RAG-retrieval | gold entities present in retrieved context | **No** (but inspires answer-side *entity recall*) |
| Noise Sensitivity | RAG | robustness to irrelevant context | **No** (marginal) |
| Response Relevancy | RAG | does the answer address the question | **Yes** — guards off-topic padding |
| Faithfulness | RAG | answer grounded in context, no hallucination | **Yes** — for context-present regimes (R1/R2) |
| Multimodal Faithfulness / Relevance | RAG-MM | image+text | **No** — text only |
| Answer Accuracy (Nvidia) | Nvidia | answer correctness vs reference | **Yes** — core |
| Context Relevance (Nvidia) | Nvidia | retrieved context relevance | **No** — no retrieval |
| Response Groundedness (Nvidia) | Nvidia | claims supported by context | **Yes** — = Faithfulness lens |
| Topic Adherence | Agentic | stays on allowed topics | **Yes (Agentic domain)** |
| Tool Call Accuracy | Agentic | correct tool + args | **Yes (Agentic)** |
| Tool Call F1 | Agentic | precision/recall over tool calls | **Yes (Agentic)** |
| Agent Goal Accuracy | Agentic | did the agent achieve the goal | **Yes (Agentic)** |
| **Factual Correctness** | NL-compare | claim precision/recall vs gold | **Yes — CORE** (= context-entity-precision/recall) |
| Semantic Similarity | NL-compare | embedding similarity to gold | **Yes** — paraphrase backoff |
| Non-LLM String Similarity | NL-compare | edit/lexical distance | **Yes** — deterministic backup |
| BLEU / CHRF / ROUGE | NL-compare | n-gram/char overlap | **Yes** — deterministic backups (short/extractive golds) |
| String Presence / Exact Match | NL-compare | gold substring / exact hit | **Yes** — deterministic backup for short/option golds |
| Execution-based Datacompy / SQL Equivalence | SQL | query result / equivalence | **No** — unless a SQL domain |
| Aspect Critic | general | binary pass/fail on a defined aspect | **Yes** — exploit checks (abstained-on-answerable? fluent-but-wrong?) |
| Simple Criteria Scoring | general | score against a stated criterion | **Yes** — a lightweight rubric axis |
| Rubrics-based Scoring | general | score against a rubric | **Yes** — this IS the judge rubric |
| Instance-specific Rubrics | general | per-example rubric | **Yes (optional)** — per-item gold rubric |
| Summarization | other | summary quality | **No** — unless summarizing |

## The single-schema wrapper pattern

Fold the *applicable* metrics into ONE schema whose fields are ordered as a reasoning chain. Prompt the model
to fill fields IN ORDER, each earlier field being evidence for the later ones, `final_score` last:

```
gold_key_claims       # Factual Correctness — extract the gold's key facts/entities
answer_covered        #   → recall: which gold claims the answer states
answer_wrong_claims   #   → precision / Faithfulness: entities asserted NOT in gold∪context (hallucination)
relevant_to_question  # Response Relevancy (0-1)
grounded_in_context   # Faithfulness / Response Groundedness (0-1; 1.0 if no context needed)
is_abstention         # Aspect Critic — did it decline / say "unanswerable"
abstention_appropriate# Aspect Critic — appropriate ONLY if gold is empty/unanswerable
conciseness           # efficiency (0-1)
final_score           # synthesized LAST from the above
```

Rules that make it work on a WEAK model:
- **Field order = call order.** The model reasons through extractions/checks before scoring — this is what a
  2B follows where it ignores abstract rules.
- **Anchors beat prose.** Prefix 3–4 short scored exemplars (fantastic ~1.0, expected ~0.5, and *horrible*
  ~0.1 = the actual failure modes you observed, e.g. abstention-on-answerable, fluent-but-wrong). Keep them
  short for small-model context.
- **Isolate one answer per call.** Batched multi-answer object prompts contaminate per-answer scores; score
  one pair per call, keep throughput up with N concurrent requests.
- **Route by domain.** Verifiable domains bypass the judge: Math → programmatic verifier, Code → execution
  verifier; the schema judge is for soft/factoid domains where the judge IS the reward.
- **Deterministic backups.** For short/option/exact golds, use Exact Match / String Presence / ROUGE (ragas
  non-LLM metrics) rather than the LLM — cheaper and un-gameable.

## When NOT to use this

- If you genuinely retrieve, evaluate retrieval with the real RAG-retrieval metrics (Context
  Precision/Recall/Entities Recall) separately — do not fold them into an answer-only judge.
- If you can afford per-metric calls and need calibrated per-metric scores for analysis, run ragas proper.
- Multimodal / SQL / Summarization tasks: use the dedicated metrics, not this answer-vs-gold schema.

## Output

Return either (a) a metric-selection decision for a given task (which of the above apply + why), or (b) a
single ordered JSON `judge_schema` (fields + one-line intent each) plus the anchor set and the routing rules.
```

Sources: [ragas metric list](https://docs.ragas.io/en/stable/concepts/metrics/available_metrics/).
