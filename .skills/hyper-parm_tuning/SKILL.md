---
name: hyper-parm_tuning
description: Hyperparameter optimization protocol for expensive systems. Use when tuning retrieval stacks, model pipelines, rankers, thresholds, or any workflow where evaluations are costly and overfitting risk is real.
status: superseded
superseded_by: optuna-nested-cv
last_validated: 2026-04-28
---
# Hyperparameter Tuning Protocol

## Core Thesis
Treat tuning as experimental design, not blind search.

- Freeze the architecture first. Do not tune while the workflow shape is still changing.
- Optimize a single scalar objective. Multi-metric dashboards are useful, but the search loop needs one number.
- Separate `tune` from `holdout`. Never search and confirm on the same bank.
- Tune one layer at a time unless strong interactions force a joint search.
- Persist every trial so the process is resumable and auditable.

If the system includes a persistent memory layer, define that layer in its own skill first. This skill only covers how to optimize it after the behavior is already specified.

## Skill Topology

This skill is the **methodology layer**.

Use it with:

- `optuna-nested-cv` for the Optuna / TPE implementation layer
- `mlflow` for experiment tracking, run lineage, and artifact comparison

Think of the split this way:

```text
hyper-parm_tuning -> what to optimize, in what order, against what scalar
optuna-nested-cv  -> how to run the search
mlflow            -> how to record the search and compare outcomes
```

## When to Use
Use this skill when:
- evaluations are expensive
- the system has multiple tunable stages or layers
- an LLM judge, human rubric, or noisy scorer is involved
- you need a reusable process, not one-off guesswork

Do not use this skill when:
- the architecture is still unsettled
- there is no stable evaluator
- the "hyperparameters" are really feature or product decisions

## Methodology Primer
For the full search preconditions, scalar-objective contract, judge sampler policy,
and bank design, see `optuna-nested-cv`'s **Methodology Primer**. That
higher-authority skill now owns the reusable optimizer setup contract; this file
keeps the Weighted Stage Allocation pattern and the tuning-specific cautions that
remain distinctive here.

## Decomposition Strategy
This section is the canonical home for the **Weighted Stage Allocation** pattern.
See `optuna-nested-cv` for the full methodology primer and optimizer mechanics;
apply those mechanics stage by stage using the order below.

Prefer layerwise tuning over full joint tuning.

Typical order:
1. Tune stage 1 with everything downstream disabled or fixed
2. Freeze stage 1 best params
3. Tune stage 2 with stage 1 fixed
4. Freeze stage 2 best params
5. Continue until the full stack is configured

Use joint tuning only after a stable layerwise pass, and only when evidence shows interaction effects are load-bearing.

## Search Mechanics
See `optuna-nested-cv`'s **Methodology Primer** for the full search-space typing
(`linear` / `log` / `categorical`), structured-probe details, TPE guidance, and
noise-handling contract. This skill keeps the stage order; `optuna-nested-cv`
owns the reusable search mechanics.

## Persistence
Persist every trial artifact.

Prefer MLflow as the searchable run ledger, even when another tool stores
search state underneath it.

Each saved trial should include:
- parameter values
- scalar score
- component metrics
- split or bank used
- timestamp
- trial index
- evaluator notes or reason text, if available

If Optuna is involved:

- keep the Optuna SQLite study for resumability
- log the trial to MLflow for comparison, artifact browsing, and cross-run lineage

This turns tuning into a reproducible experiment instead of an ephemeral chat outcome.

## Trial Loop
For each trial:

1. Materialize the candidate config
2. Run the system on the `tune` bank
3. Collect raw metrics
4. Reduce them to the scalar objective
5. Persist the artifact
6. Compare against the incumbent
7. Update best params only if the score improves

## Retrieval-Architecture Tuning vs Clustering Diagnostics
When tuning quote retrieval or similar semantic-memory systems, do **not** make
global external clustering the winner metric.

Use the real retrieval eval target for selection, and treat clustering outputs as:

- diagnostics for geometry
- optional routing aids
- optional post-retrieval summarization structure

This is the stronger default when quote embeddings do not cluster cleanly enough
to deserve ownership of model selection.

Typical retrieval-architecture factors to tune instead:

1. broad-pool size
2. GIST utility vs diversity weight
3. graph path weight / hop budget
4. local community threshold or expansion budget inside layer 2
5. entity-overlap bonus
6. whether local grouping is enabled at all

Weak point: some local clustering may still help summarization after retrieval.
That does **not** make cluster quality the primary objective.

## Post-Selection Validation
After selecting the final config:

1. Persist the chosen params as a named artifact
2. Re-run the full evaluation on the `holdout` bank
3. Compare holdout against tune performance
4. Record any degradation explicitly

If holdout collapses, do not hide it. That means the tune set was overfit or unrepresentative.

## Diagnostics from Failures
Bad trials should produce repair signals, not just low scores.

Examples:
- low precision -> retrieval or normalization issue
- low recall -> candidate generation or pruning issue
- unstable score -> evaluator noise or underspecified prompt
- strong train/holdout gap -> overfitting or bad split design

Turn repeated failure patterns into backlog items or automatic diagnostics.

## Anti-Patterns
Avoid these:

- tuning while still changing architecture
- tuning and validating on the same bank
- optimizing multiple metrics without defining one scalar
- tuning all layers jointly before a layerwise baseline exists
- using one noisy evaluation sample per trial
- failing to persist best params and trial traces
- changing the evaluator halfway through the search

## Reusable Workflow
When invoked, apply this sequence:

1. Identify the fixed system architecture
2. Define the scalar objective
3. Define `tune` and `holdout` banks
4. Partition tunables into layers or stages
5. Choose search-space types: `linear`, `log`, `categorical`
6. Run a baseline evaluation
7. Tune the first layer
8. Freeze the first layer best params
9. Repeat for downstream layers
10. Persist the final chosen params
11. Run holdout once for confirmation
12. Convert recurring misses into a repair queue

Where available, log every step above into MLflow so the campaign, final fit,
and holdout pass all remain tied together.

## Minimal Output Contract
When using this skill, the final answer should report:

- the scalar objective used
- the split design (`tune` vs `holdout`)
- the tuning order by layer
- the search strategy used (`structured` or `tpe`)
- the best params found
- the holdout result
- any remaining uncertainty or overfit risk
<!-- consolidation:see-also:start -->
## See Also
[[nearest-neighbor-chain]]  [[synthetic-data]]  [[mad-dynamic-batching]]
<!-- consolidation:see-also:end -->
