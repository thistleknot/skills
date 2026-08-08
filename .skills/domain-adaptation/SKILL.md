---
name: domain-adaptation
description: >
  Use when a general model must perform in a specialized vertical -- healthcare,
  finance, tabular/numeric prediction, law -- where generic behavior fails on
  domain-specific knowledge, numeric nuance, or evaluation. Covers domain
  pretraining/generative tabular learning, vertical RAG evaluation, prompt-level
  distillation for regulated deployment, and the numeracy gap in embeddings.
status: active
last_validated: 2026-07-27
---

# Domain Adaptation

Distilled from arXiv 2310.07338 (Generative Tabular Learning), 2404.16621
(Hippocrates, healthcare), 2406.05504 (G-Transformer, counterfactual clinical),
2412.13018 (OmniEval, financial RAG benchmark), 2509.05691 (numeracy gap),
2509.11944 (temporal-graph medical reasoning), 2602.21103 (Prompt-Level
Distillation).

## When to Use

- A general LLM/embedding model underperforms in a vertical because it misses
  domain knowledge, numerical precision, or domain-specific evaluation criteria.
- You need predictive modeling over tabular/structured domain data, or
  counterfactual outcome prediction under changing regimes (clinical treatment).
- Deployment is *regulated* (law, finance, healthcare) so interpretability and
  verifiability are hard requirements, not nice-to-haves.

**Do NOT use when** a general model already meets the domain bar, or when the gap
is generic reasoning rather than domain fit. Watch the costs: domain pretraining
is compute-heavy with data-privacy exposure (2310.07338); clinical models need
large curated datasets like MIMIC-IV (2406.05504).

## Core Concepts

- **Generative Tabular Learning (2310.07338).** Fold LLM capabilities into
  tabular prediction so one model does zero-shot / in-context prediction across
  healthcare, finance, retail without per-task fine-tuning -- domain adaptation
  via pretraining on diverse tabular data plus numeric-sequence understanding.

- **The numeracy gap (2509.05691).** Text embedding models capture semantics but
  fail on numerical nuance -- critical in finance/healthcare. Before trusting an
  embedding in a numeric-heavy vertical, test its ability to encode magnitude and
  numeric relations; do not assume semantic strength implies numeric strength.

- **Vertical evaluation (OmniEval, 2412.13018).** Adapt the *benchmark*, not just
  the model: a matrix of task classes x domain topics (5 classes x 16 financial
  topics) with automatic + human metrics surfaces where a RAG system breaks down
  per-topic. You cannot claim domain readiness without domain-specific eval.

- **Counterfactual / temporal domain modeling (2406.05504, 2509.11944).**
  G-Transformer does g-computation for outcome prediction under dynamic
  time-varying treatment; temporal reasoning graphs enable backtracking and
  progression tracking for medical diagnosis. Domains with time-varying state
  need architectures that model that state, not static classifiers.

- **Prompt-Level Distillation for regulated deploy (2602.21103).** Extract a
  teacher's reasoning patterns into structured instructions so a compact model
  matches frontier performance with full human-verifiable logic and negligible
  latency -- makes advanced reasoning viable in law/finance/moderation where
  black boxes are disallowed.

## Protocol

```
adapt_to_domain(base_model, domain):
    gap <- diagnose(base_model, domain)      # knowledge? numeracy? evaluation?
    if gap == numeracy:  test_numeric_encoding(base_model)   # 2509.05691
    if gap == knowledge:
        model <- pretrain_or_GTL(base_model, domain_data)    # privacy-aware
    if domain_is_temporal:
        model <- temporal_or_g_computation(model)            # time-varying state
    bench <- vertical_matrix(task_classes x domain_topics)   # OmniEval-style
    if regulated(domain):
        model <- prompt_level_distill(teacher=model)         # verifiable, compact
    return validate(model, bench)            # per-topic, not aggregate only
```

Failure modes: pretraining cost + privacy; benefits uneven across users; small
domains lack the data to train or evaluate reliably.

## Related

`rag-eval` / `ragas` (vertical RAG scoring), `stat-partitioning` (numeric
thresholds), `crystallization` (domain-fact distillation).
