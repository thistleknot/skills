---
name: mlflow
description: >
  MLflow experiment tracking protocol. Use when running Optuna searches, comparing
  model or pipeline variants, or operating agentic harnesses where params, metrics,
  artifacts, and run lineage must be persisted and queryable across runs.
status: active
last_validated: 2026-04-28
---

# MLflow Tracking Protocol

## Scope Boundary

This skill is the **experiment ledger layer** that sits alongside
`optuna-nested-cv` and underneath the broader `hyper-parm_tuning` methodology.

It owns:

- experiment naming and run hierarchy
- params / metrics / tags / artifact logging
- nested runs for campaigns, folds, trials, final fits, and holdout checks
- run lineage across dataset version, representation version, branch, commit,
  and framework
- optional model promotion after holdout validation

It does **not** own:

- search policy or split design (see `hyper-parm_tuning`)
- Optuna sampler mechanics or nested CV logic (see `optuna-nested-cv`)
- deciding which product metric matters
- replacing real checkpoints, databases, or artifact stores

## Core Thesis

Optuna decides **what to try**. MLflow remembers **what happened**.

Without MLflow, a tuning process can still be resumable, but it is harder to:

- compare runs across days or branches
- inspect artifacts that explain why a trial won
- tie a result back to the exact dataset, transform, or framework version
- reuse the same ledger across different search engines or coding agents

Use both:

- **Optuna SQLite** for sampler state and resumability
- **MLflow** for searchable experiment history and artifact lineage

## Skill Topology

Treat the tuning stack like this:

```text
hyper-parm_tuning  -> experimental design, objective, split, layer order
optuna-nested-cv   -> black-box search engine, nested CV, sampler behavior
mlflow             -> run ledger, artifact registry, comparison surface
agentic-harness    -> control plane that can route frameworks and log outcomes into mlflow
```

Parallel, not redundant:

- `optuna-nested-cv` can exist without MLflow, but you lose the rich ledger
- MLflow can exist without Optuna, but you lose the search engine
- together they give reproducible search plus inspectable history

## Default Run Topology

Use nested runs that mirror the actual workflow:

```text
experiment: "siamese_affinity_search"
    run: campaign
        run: outer_fold_0
            run: trial_000
            run: trial_001
            ...
        run: outer_fold_1
            run: trial_000
            ...
        run: final_train
        run: holdout_eval
```

Recommended meaning:

- **campaign run** -> one search request against one fixed architecture
- **outer_fold run** -> one evaluation fold in nested CV
- **trial run** -> one Optuna suggestion and its scalar outcome
- **final_train run** -> fit with chosen params on the full train split
- **holdout_eval run** -> one final unbiased report, logged once

## Naming and Tagging Contract

At minimum, tag each run with:

- `system`
- `objective`
- `corpus_hash`
- `representation_version`
- `split` (`tune`, `outer_fold`, `final_train`, `holdout`)
- `study_name`
- `trial_number`
- `branch`
- `commit`
- `framework`
- `agent_role`

For agentic coding workflows, also tag:

- `story_id`
- `artifact_path`
- `coherence_status`
- `critic_round`
- `prompt_hash`

If you cannot answer "what exact conditions produced this run?" from tags alone,
the run is under-instrumented.

## What to Log

### Params

Log every tunable that could change behavior:

- model hyperparameters
- retrieval thresholds
- clustering configuration
- search-space choice
- framework or agent routing choice
- budget knobs (`n_trials`, `patience`, `max_epochs`, `timeout`)

### Metrics

Always log:

- the scalar objective
- component metrics used to build it
- run duration
- failure counts or retry counts if applicable

Examples:

- `objective`
- `bss_tss`
- `silhouette`
- `recall_at_10`
- `judge_mean`
- `holdout_score`
- `illegal_action_rate`
- `gate_pass_rate`
- `critic_violations`
- `artifact_generated`

### Artifacts

Persist the artifacts that explain a run, not just the score:

- config JSON / YAML
- plots
- evaluation tables
- confusion matrices
- cluster assignments
- embeddings or checkpoints
- prompt packets
- critic reports
- generated repositories or generated files

## Optuna Pairing Pattern

Use MLflow for visibility and Optuna for search state.

```python
import mlflow
import optuna

mlflow.set_tracking_uri("file:./mlruns")
mlflow.set_experiment("siamese_affinity_search")

with mlflow.start_run(run_name="campaign"):
    mlflow.log_params({
        "study_name": study_name,
        "n_trials": n_trials,
        "objective_name": "composite_score",
    })

    def objective(trial):
        with mlflow.start_run(
            run_name=f"trial_{trial.number:03d}",
            nested=True,
        ):
            params = {
                "lr": trial.suggest_float("lr", 1e-4, 1e-2, log=True),
                "dropout": trial.suggest_float("dropout", 0.0, 0.5),
            }
            mlflow.log_params(params)
            score = run_trial(**params)
            mlflow.log_metric("objective", score)
            mlflow.set_tags({
                "study_name": study_name,
                "trial_number": trial.number,
            })
            return score

    study = optuna.create_study(
        study_name=study_name,
        storage="sqlite:///optuna_runs.db",
        direction="maximize",
        load_if_exists=True,
    )
    study.optimize(objective, n_trials=n_trials)

    mlflow.log_params(study.best_params)
    mlflow.log_metric("best_value", study.best_value)
```

Rule:

- **Optuna SQLite** is the source of truth for search-state resumability
- **MLflow** is the source of truth for human inspection and artifact comparison

Do not replace one with the other.

## Agentic Harness Pairing Pattern

For `agentic-harness`, MLflow becomes the **station ledger**.

Use one experiment per project or harness family, then log:

- framework used (`claude-code`, `opencode`, `copilot-cli`)
- story id / branch
- critic rounds
- legality failures
- gate results
- artifact path
- coherence result

Good harness metrics:

- `illegal_action_rate`
- `gate_timeout_count`
- `critic_violation_count`
- `tests_generated`
- `tests_passed`
- `artifact_generated`
- `time_to_first_artifact_sec`
- `coherence_binary`

Good harness artifacts:

- run logs
- generated repo bundle
- critic report
- diff bundle
- failing fixtures
- final evidence packet

This lets the harness compare **frameworks, prompts, critics, and routing policies**
using one shared experiment surface.

## Promotion Rule

Only promote or bless a run after the holdout or representative verification pass.

Recommended sequence:

1. log search trials
2. choose best candidate
3. run final train or representative full build
4. log holdout / verification result
5. only then mark the run as promoted, blessed, or canonical

Do not crown a trial winner before it survives the final check.

## Anti-Patterns

Avoid:

- logging only the final best score
- mixing `tune` and `holdout` results without tags that separate them
- storing only metrics and not the artifacts that explain them
- using MLflow as a substitute for Optuna study state
- omitting dataset / representation version tags
- reusing the same experiment name after a structural pipeline change
- logging manual hotfix outputs as if they were generated artifacts

## Minimal Output Contract

When this skill is used, the final answer should report:

- MLflow experiment name
- winning run id or run name
- best params
- scalar objective and component metrics
- holdout or representative verification result
- artifact location for inspection
<!-- consolidation:see-also:start -->
## See Also
[[optuna-nested-cv]]
<!-- consolidation:see-also:end -->
