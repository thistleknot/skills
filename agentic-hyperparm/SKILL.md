---
name: agentic-hyperparm
description: >
  Behavioral hyperparameter tuning protocol for AI agents. Use when tuning the
  cognitive dial set of an agentic system: retrieval depth, reranking, chunking,
  context budget, planning depth, verification passes, abstention policy, and
  sampler settings. Covers parameter taxonomy, interaction map, layerwise tuning
  order, evaluation design, and the trial loop. Distinct from optuna-nested-cv
  (ML pipeline search) and hyper-parm_tuning (retrieval/ranking stacks) — this
  skill targets the agent's own behavioral parameters, not model weights or
  pipeline architecture.
status: active
last_validated: 2026-04-30
---

# Agentic Hyperparameter Tuning Protocol

## Core Thesis

An agent's behavior is governed by a dial set that is orthogonal to model weights.
These dials control how much the agent retrieves, how it reasons, how much it
spends on verification, and how conservative or creative it is at generation time.
Tuning them correctly compounds across every task the agent runs.

The challenge is distinct from ML hyperparameter tuning in three ways:

1. **Evaluation is end-to-end and slow.** A full agent episode is the unit of
   measurement. There is no cheap proxy like a loss curve.
2. **Outputs are stochastic.** The same config produces different outputs across
   runs. Single-trial scoring is meaningless.
3. **Parameters interact strongly.** Retrieval depth is wasted if context budget
   cannot hold the results. Verification passes gain diminishing returns if
   temperature is near zero. Abstention policy must match the safety posture of
   the deployment context.

## Parameter Taxonomy

Eight behavioral axes, organized into four layers.

### Layer 1 — Retrieval
These determine what context the agent can see before reasoning.

| Parameter | What it controls | Search space type |
|---|---|---|
| `retrieval_depth` | Number of chunks/documents fetched (top-k) | Linear integer, e.g. `[3, 5, 10, 20, 50]` |
| `reranking` | Whether and how retrieved results are reordered before injection | Categorical: `none`, `bm25_rerank`, `cross_encoder`, `llm_judge` |
| `chunk_size` | Token size of each indexable unit | Categorical or log-linear: `[128, 256, 512, 1024]` |
| `chunk_overlap` | Token overlap between consecutive chunks | Linear fraction of chunk_size, e.g. `[0.0, 0.1, 0.2, 0.33]` |

### Layer 2 — Context Management
These control what fraction of retrieved content reaches the prompt.

| Parameter | What it controls | Search space type |
|---|---|---|
| `context_budget` | Max tokens allocated to injected context | Log-linear: `[512, 1024, 2048, 4096, 8192]` |

Rule: `context_budget` must be tuned **after** `retrieval_depth` and `chunk_size`
are settled. A budget too small to hold `retrieval_depth × chunk_size` tokens
silently truncates the retrieval benefit.

### Layer 3 — Reasoning
These govern how deeply the agent reasons before committing to an answer.

| Parameter | What it controls | Search space type |
|---|---|---|
| `planning_depth` | Number of planning/chain-of-thought steps before acting | Integer linear: `[1, 2, 3, 5, 8]` |
| `verification_passes` | Number of self-critique or validation loops before output | Integer linear: `[0, 1, 2, 3]` |
| `abstention_policy` | Threshold and strategy for refusing, deferring, or asking | Categorical + threshold: `{strategy: [refuse, defer, ask], threshold: [0.3, 0.5, 0.7, 0.9]}` |

### Layer 4 — Sampling
These affect generation variance and token diversity.

| Parameter | What it controls | Search space type |
|---|---|---|
| `temperature` | Output distribution sharpness | Log: `[0.0, 0.2, 0.5, 0.7, 1.0, 1.2]` |
| `top_p` | Nucleus sampling cutoff | Linear: `[0.7, 0.8, 0.9, 0.95, 1.0]` |
| `repetition_penalty` | Penalize token repetition | Log: `[1.0, 1.05, 1.1, 1.2, 1.5]` |

Sampler settings are the cheapest to evaluate but the noisiest to isolate.
Tune them **last** and average across multiple episode seeds.

## Interaction Map

Strong interactions that must inform layerwise decomposition order:

| Interaction | Effect | Implication |
|---|---|---|
| `retrieval_depth` × `context_budget` | Retrieved tokens that exceed the budget are silently dropped | Settle `retrieval_depth` and `chunk_size` before sizing the budget |
| `temperature` × `verification_passes` | At low temperature the agent produces near-identical drafts; passes add cost but not diversity | High-temp configs benefit more from verification than low-temp configs |
| `planning_depth` × `verification_passes` | Multiplicative cost: both lengthen the episode | Tune one at a time; do not simultaneously sweep both |
| `chunk_size` × `retrieval_depth` | Smaller chunks require deeper retrieval to cover the same semantic surface | These two must be co-tuned; do not treat them as independent |
| `abstention_policy` × `temperature` | High temperature makes the agent less calibrated; abstention threshold needs compensating adjustment | Tune abstention only after sampling is settled |

## When to Use

Invoke this skill when:
- The agent works but quality, cost, or safety is not at the level required
- The deployment context has changed (new domain, new retrieval corpus, new policy)
- You have added a new retrieval layer or changed the corpus and the old dial
  settings are no longer validated
- Cost or latency is too high and you need to find where to tighten

Do **not** invoke this skill when:
- The agent pipeline shape is still changing (tune after freezing architecture)
- There is no evaluator — no stable measurement means no signal
- The "tuning" is actually a product decision (what abstention policy should
  mean is a design choice, not a numerical optimization)

## Preconditions

Before tuning, all six must be true:

1. Fixed agent pipeline shape — tool calls, prompt templates, memory layers
2. A baseline configuration that completes representative tasks end to end
3. A bounded candidate set for each parameter
4. A single scalar objective, even if composite
5. A `tune` bank and a separate `holdout` bank — never the same episodes
6. A persistence path for trial artifacts and scores

If any one is missing, fix that first.

## Evaluation Framework

### Scoring Axes

Agent quality is multi-dimensional. Collapse to one scalar before searching.

| Axis | Proxy metric | Notes |
|---|---|---|
| Task quality | Answer accuracy, coherence, human preference | LLM-judge score or rubric |
| Cost efficiency | Tokens consumed per episode | Directly measurable |
| Latency | Wall time per episode | Directly measurable |
| Safety | Abstention rate on out-of-policy queries | Requires a policy-labeled test set |
| Calibration | Agreement between agent confidence and actual correctness | Optional; expensive to measure |

### Composite Scalar

Define one scalar before starting any search:

```python
score = (
    quality_weight * quality_score
    - cost_weight * normalized_token_cost
    - latency_weight * normalized_latency_ms
    + safety_weight * safety_score
)
```

Keep weights and normalization constants fixed across all trials. Changing the
objective halfway through the search invalidates every prior trial.

### Noise Handling

Agent outputs are stochastic. Never score a trial from a single episode.

Default: run each config on three seeds (`seed_a`, `seed_b`, `seed_c`) and take
the mean scalar. If the evaluator is itself an LLM judge, also run it under the
standard sampler trio from `hyper-parm_tuning`:

- `conservative` — low-variance judge read
- `balanced` — middle estimate
- `creative` — looser judge read

Score = mean across (3 seeds × 3 judge takes) = 9 evaluations per trial.
Reduce if budget is tight; never below 3 per trial.

### Episode Bank Design

Use explicit banks:

- `tune` — used during search; 30–50 representative episodes
- `holdout` — used once after choosing the final config; ≥20 episodes
- `diagnostic` — error analysis only; never for selection

The tune bank should cover: easy tasks, hard tasks, edge cases, and adversarial
inputs in proportion to the expected live distribution. A skewed tune bank
produces a tuned config that fails on production inputs it never saw.

## Layerwise Tuning Protocol

Tune in strict layer order. Freeze each layer before moving to the next.

### Recommended Order

```
1. chunk_size + chunk_overlap  (index rebuild required; settle early)
2. retrieval_depth             (depends on chunk_size being fixed)
3. reranking                   (depends on retrieval_depth being fixed)
4. context_budget              (size it to hold retrieval output)
5. planning_depth              (expensive; tune with upstream context fixed)
6. verification_passes         (multiplicative cost; tune after planning)
7. abstention_policy           (domain-specific; tune after sampling is settled)
8. temperature + top_p + repetition_penalty  (cheapest; tune last; noisiest)
```

Rationale: upstream parameters determine what information reaches the model.
Downstream parameters (sampling, verification) cannot compensate for bad retrieval.
Fix the information surface first.

### When to Use Joint Tuning

Only run joint tuning after a stable layerwise baseline exists **and** evidence
shows that interaction effects are load-bearing (e.g., a joint sweep scores
measurably better than the sequential freeze result). Joint tuning before that
is wasted budget.

## Search Strategy

### Option A — Structured Probe (Default for Expensive Evaluations)

```text
1. Start from the current best (or a center config if no baseline exists)
2. For each parameter in the layer, probe center+sigma and center-sigma
3. Score each probe on the tune bank
4. Record the winning direction for each parameter
5. Build a joint candidate from all winning directions
6. Run local refinement samples around the current best
7. Accept only if the new config beats the incumbent
```

Budget with `n` parameters and `r` refinement samples: `2n + r + 1` evaluations.

### Option B — TPE/Bayesian (for Broader Exploration)

Use `optuna-nested-cv` for the search engine. Register the composite scalar as
the Optuna objective. Persist the study to SQLite so the search is resumable.

Reserve TPE for layers where parameter interactions are strong and interpretability
is less important than coverage.

Always log every trial to MLflow for lineage and cross-run comparison.

## Trial Loop

For each trial:

1. Materialize the candidate config as a named dict
2. Apply the config to the agent (update retriever, prompt template, sampler)
3. Run the agent on the `tune` bank, `n_seeds` times
4. Collect per-episode scores
5. Reduce to the composite scalar (mean across seeds and judge takes)
6. Persist the trial (config + all component scores + scalar + timestamp)
7. Compare against incumbent; update best only on strict improvement

## Persistence

Every trial must be saved. Minimum artifact:

```json
{
  "trial_id": "...",
  "layer": "retrieval",
  "params": {"retrieval_depth": 10, "chunk_size": 512},
  "scores": {"quality": 0.73, "cost": 0.41, "latency_ms": 1200},
  "scalar": 0.61,
  "bank": "tune",
  "n_seeds": 3,
  "timestamp": "..."
}
```

Prefer MLflow as the searchable run ledger. If Optuna is involved, keep the
Optuna SQLite study for resumability and log each trial to MLflow for
cross-run comparison.

## Post-Selection Validation

After choosing a final config:

1. Persist it as a named artifact: `best_agent_config.json`
2. Run the full evaluation on the `holdout` bank
3. Compare holdout vs tune scalar; record any degradation
4. If holdout collapses (>10% degradation vs tune), the tune bank was overfit
   or unrepresentative — do not deploy; redesign the tune bank

## Diagnostics from Failures

| Pattern | Likely cause |
|---|---|
| Low quality, high retrieval tokens | Context budget truncating the retrieval; increase budget or decrease retrieval_depth |
| High cost, marginal quality gain from verification | verification_passes too high for the temperature setting; lower passes or raise temperature |
| Erratic abstention | abstention_policy threshold not calibrated to the domain; tune on a policy-labeled bank |
| Strong tune/holdout gap | Tune bank is not representative; sample from live distribution |
| Flat quality across temperature range | Task is not sensitive to sampling variance; deprioritize sampler tuning |
| Planning depth changes nothing | Task is short-horizon; planning overhead is wasted; set `planning_depth=1` |

## Anti-Patterns

- Tuning while the pipeline shape is still changing
- Scoring a trial from a single episode run
- Tuning sampling before retrieval and context are settled
- Using holdout for selection (turns it into another tune set)
- Changing the composite scalar definition mid-search
- Joint-tuning all eight parameters simultaneously as a first pass
- Treating abstention threshold as a numerical optimization without a
  policy-labeled test bank

## Relationship to Other Skills

| Skill | Role in this workflow |
|---|---|
| `optuna-nested-cv` | Search engine for Option B (TPE); provides study namespacing, resumable SQLite persistence, and the nested-CV unbiased estimator |
| `hyper-parm_tuning` | Methodology precursor; the layerwise and structured-search protocol here extends its principles to agent behavior |
| `mlflow` | Experiment ledger; log every trial so the full tuning campaign, final fit, and holdout pass are tied together |
| `agentic-harness` | Provides the pipeline control plane whose behavioral config this skill tunes |
| `evaluator-optimizer` | Use when the quality evaluator itself needs to be refined iteratively alongside the agent config |

## Minimal Output Contract

When this skill completes, report:

- The composite scalar definition (weights, normalization)
- The tune and holdout bank sizes
- The layerwise tuning order followed
- The search strategy used (structured or TPE)
- Best config found per layer, with its tune scalar
- The holdout scalar for the final config
- Any tune/holdout gap and its interpretation
- Remaining uncertainty (e.g., parameters not yet tuned due to missing evaluator)
<!-- consolidation:see-also:start -->
## See Also
[[hyper-parm_tuning]]  [[optuna-nested-cv]]
<!-- consolidation:see-also:end -->
