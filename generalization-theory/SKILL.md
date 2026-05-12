---
name: generalization-theory
description: >
  Training-dynamics diagnostic skill for distinguishing signal learning from
  memorization through the empirical NTK signal/noise partition. Use when a
  model fits training data but generalizes poorly, groks late, or overfits
  noisy preference data, and you need to decide whether to intervene through
  data, architecture, or optimizer design.
status: active
last_validated: 2026-05-09
validation_method: theoretical
---

# Generalization Theory

## When to Use

Use this skill when:

- train loss improves but test behavior stalls or regresses
- a run appears to memorize examples instead of learning population structure
- grokking or delayed generalization needs a mechanism-level explanation
- benign overfitting, double descent, or noisy-preference DPO behavior needs a unified lens
- you need to choose between data cleanup, architectural bias, or optimizer intervention

Do **not** use this skill when:

- the real task is hyperparameter search orchestration -> `optuna-nested-cv`
- the problem is sequential forgetting across tasks -> `continual-learning`
- you need a retrieval or representation pipeline rather than a training-dynamics diagnosis

---

## Scope Boundary and Paired Skills

This skill owns the **diagnostic lens** for generalization failures.

It owns:
- the signal-channel vs noise-reservoir framing
- interpretation of grokking, benign overfitting, implicit bias, and double descent under that framing
- SNR-style diagnostics for distinguishing generalization from memorization
- intervention selection across data, architecture, and optimizer surfaces

It does **not** own:
- the search loop for tuning interventions -> `optuna-nested-cv`
- agent-behavior hyperparameter tuning -> `agentic-hyperparm`
- continual retention strategies across tasks -> `continual-learning`

---

## Core Thesis

Treat the empirical neural tangent kernel (eNTK) as partitioning behavior into two orthogonal regimes:

| Regime | Geometry | Consequence |
|---|---|---|
| Signal channel | high eigenvalue directions | coherent population patterns accumulate quickly |
| Noise reservoir | near-zero eigenvalue directions | residual error and memorized idiosyncrasies get trapped |

Under this view:
- minibatch SGD is a geometric filter, not just an optimizer implementation detail
- patterns that agree across batches drift into the signal channel
- sample-specific noise diffuses slowly and remains largely test-invisible

---

## Diagnostic Protocol

1. **Start with the failure shape.** Separate "generalizes poorly" into one of: test gap, grokking delay, noisy-preference memorization, or interpolation-threshold instability.
2. **Classify gradients by coherence.** If a pattern is stable across minibatches, treat it as candidate signal. If it is highly sample-specific, treat it as candidate noise.
3. **Track the signal-to-noise ratio in the signal channel.** Rising SNR suggests genuine generalization; flat or falling SNR suggests the run is spending capacity on memorization.
4. **Interpret the stage of training.**
   - early memorization dominance -> diffusive noise walk
   - later population drift -> signal-channel takeover
   - delayed takeover -> grokking-style behavior
5. **Choose the intervention surface that matches the diagnosis.**
   - too little coherent data -> add cleaner, population-level examples
   - architecture spreads mass into noisy directions -> add stronger inductive bias
   - optimizer is not keeping updates in signal directions -> add an SNR-aware preconditioner

---

## Unified Phenomena Map

| Phenomenon | Interpretation under this skill |
|---|---|
| Benign overfitting | memorization is trapped in the noise reservoir and does not dominate test behavior |
| Double descent | the geometry of the signal/noise partition shifts near interpolation |
| Implicit bias | SGD preferentially accumulates coherent gradients in signal directions |
| Grokking | memorization dominates first, then signal-channel drift eventually wins |

---

## Intervention Ladder

Use the lightest intervention that matches the diagnosed bottleneck:

1. **Data:** add more population-coherent samples or reduce label/preference noise.
2. **Architecture:** bias the model toward directions that align with the data manifold.
3. **Optimizer:** use an SNR-style preconditioner to keep updates in signal directions.
4. **Fine-tuning policy:** for noisy DPO or similar alignment regimes, constrain updates away from preference noise before increasing scale or duration.

Rule: if SNR is not improving, do not keep scaling epochs and hope it turns into generalization by itself.

---

## Practical Payoff

The source theory claims that an SNR preconditioner can approximate a population-risk proxy from a single training run and improve:

- grokking speed
- memorization suppression in noisy or implicit-function regimes
- preference fine-tuning robustness under noisy labels

Use this as a design hypothesis and diagnostic target, not as proof that every stack can cheaply compute the exact eNTK.

---

## Applicability Envelope

**Works well when:**
- you need a principled explanation for why train improvement is not turning into test improvement
- the observed behavior looks like memorization, grokking, or noisy-preference overfitting
- you can observe training dynamics well enough to compare coherent vs idiosyncratic behavior

**Fails or degrades when:**
- the dominant problem is data leakage, bad evaluation splits, or another simpler pipeline bug
- you cannot observe enough of the training dynamics to distinguish signal from noise
- the deployment question is purely operational (latency, memory footprint, batching) rather than generalization

**Environment assumptions:**
- a training setup where optimizer, data, and architecture interventions are actually changeable
- access to enough telemetry or checkpoints to inspect generalization behavior over time
- willingness to treat this as a diagnostic theory, not an automatic replacement for holdout evaluation

---

## Evidence

- Litman & Guo, "A Theory of Generalization in Deep Learning," arXiv:2605.01172
