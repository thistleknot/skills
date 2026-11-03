# DSPy Evaluation Topology

**Source:** `stanfordnlp/dspy` @ `2974a6550a403e9b8c90ca9e34331d67d3102fa6`  
**Clone:** `/home/user/harness/integrate/dspy`  
**Purpose:** A framework for programming LM systems as compositional Python modules, then optimizing those modules against explicit metrics. For `agentic-harness`, the portable value is the evaluation contract: program + metric + small trainset -> optimized candidate, with trace-aware proposal and reward-bound refinement loops.

---

## Topology Overview

```text
PROGRAM LAYER ──────────────────────────────────────────────────────────────────
  DSPy module / signature / LM program
       │
       ├── single module or multi-module pipeline
       ├── Python-defined structure instead of prompt-only glue
       └── explicit module boundaries for optimization

EVALUATION CONTRACT LAYER ──────────────────────────────────────────────────────
  program + metric + trainset
       │
       ├── metric is first-class
       ├── trainset can be tiny and partially labeled
       └── score drives optimizer decisions

OPTIMIZER LAYER ────────────────────────────────────────────────────────────────
  BootstrapFewShot / MIPROv2 / GEPA / BootstrapFinetune / BetterTogether
       │
       ├── synthesize demos
       ├── propose instructions
       ├── reflect on traces
       ├── search candidate programs
       └── optionally distill to finetuned weights

REFINEMENT LAYER ───────────────────────────────────────────────────────────────
  BestOfN / Refine
       │
       ├── multiple rollout IDs
       ├── reward_fn + threshold
       ├── feedback loop after failed attempts
       └── fail_count to cap tolerated errors

ARTIFACT + OBSERVABILITY LAYER ─────────────────────────────────────────────────
  compiled program + traces + saved JSON
       │
       ├── optimizer outputs are serializable
       ├── traces are usable as optimization evidence
       └── program state remains inspectable after compilation
```

---

## Feature Inventory

### METRIC-BOUND PROGRAM OPTIMIZATION

**`program + metric + trainset -> compiled candidate`**  
DSPy optimizers take an LM program, a scoring function, and a trainset, then search for a better program. The trainset can be small and even incomplete.

**Migration value:** highest-priority. This is the cleanest reusable evaluation pattern for harness work that can actually be scored.

### TRACE-AWARE OPTIMIZER FAMILY

**`BootstrapFewShot`**  
Bootstraps demos with a teacher program and keeps only demonstrations that satisfy the metric.

**`MIPROv2`**  
Collects traces, filters to high-scoring trajectories, drafts better instructions from code/data/traces, then runs a discrete search with a surrogate model.

**`GEPA`**  
Reflects on trajectories to identify what worked, what failed, and which prompt changes address the gap.

**`BootstrapFinetune` + `BetterTogether`**  
Support prompt->weight and mixed optimization sequences rather than forcing prompt tuning and finetuning into separate worlds.

**Migration value:** very high. Together these give `agentic-harness` a concrete menu of optimizer styles instead of one vague "critic loop".

### REWARD-THRESHOLD REFINEMENT

**`BestOfN`**  
Runs multiple rollouts and returns the first candidate above threshold or the best candidate by reward.

**`Refine`**  
Adds an automatic feedback loop: failed attempts generate detailed feedback that becomes hints for later attempts.

**`fail_count` as error budget`**  
Both loops can continue through some failures or stop early when the error budget is exhausted.

**Migration value:** very high. This is directly portable to harness retry policy design.

### CONSTRAINT-AWARE EVALUATION

**`Assert` / `Suggest` legacy pattern`**  
Older DSPy docs describe hard and soft constraint enforcement with retry/backtracking, but current docs mark this path deprecated.

**`Refine` / `BestOfN` current path`**  
DSPy 2.6 positions `Refine` and `BestOfN` as the replacement for assertion-driven retry.

**Migration value:** high. The harness should encode the modern pattern: reward-threshold refinement first, schema/assertion checks as support rails rather than the whole evaluation strategy.

### COMPOSABILITY + ARTIFACT PERSISTENCE

**`optimizer composition`**  
Optimizers can be chained, ensembled, or used to seed subsequent finetuning.

**`save/load compiled program`**  
Optimizer output is persisted as plain-text JSON and can be reopened for later inference or inspection.

**Migration value:** high. This helps `agentic-harness` keep optimized evaluators inspectable instead of burying them in transient logs.

---

## Harness Adaptation Notes

### WHAT DSPY CONTRIBUTES TO `agentic-harness`

Use DSPy-style patterns when:

1. the artifact or module can be scored by an explicit metric or reward function
2. you can afford a bounded optimization budget over small train/dev slices
3. you want traces to be first-class evidence for why the next prompt or module changed

### WHAT NOT TO COPY BLINDLY

- Do not turn every harness critic loop into a DSPy compile run.
- Do not replace final artifact-backed acceptance with optimizer scores alone.
- Do not keep the deprecated `Assert`/`Suggest` framing when `Refine`/`BestOfN` better describes the modern loop.

---

## Bottom Line

**Bottom line:** DSPy contributes the **metric-first evaluation contract** for `agentic-harness`: explicit reward functions, trace-aware optimization, bounded refinement loops, and inspectable compiled outputs. It is less about "prompting better" and more about giving the harness a disciplined way to improve modules against a measured objective.
