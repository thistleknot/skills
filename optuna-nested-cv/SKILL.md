---
name: optuna-nested-cv
description: >
  Optuna-based hyperparameter search protocol. Use when running TPE search over
  algorithm choice, model architecture, or pipeline hyperparameters where
  evaluations are costly, the search must be resumable, and an unbiased
  generalization estimate is required. Covers nested CV, composite scoring,
  study namespacing, and seeded domain examples (ANN training, silhouette-guided
  clustering).
status: active
last_validated: 2026-04-28
---

# Optuna Tuning Protocol

## Methodology Primer

This section absorbs the methodology contract from `hyper-parm_tuning` so this skill
is self-contained. `hyper-parm_tuning` is now superseded by this section.

### Preconditions

Before running any search, all six of these must be true:

1. A fixed pipeline shape or model workflow (Optuna tunes values, not structure)
2. A baseline configuration that runs end to end
3. A bounded search space for each factor
4. A single scalar objective (composite is fine; ambiguous is not)
5. A `tune` split and a separate `holdout` split — never the same bank
6. A persistence path for trial artifacts (`sqlite:///optuna_runs.db` minimum)

If any one is missing, fix that first. Do not start the search.

### Layerwise Decomposition

Tune one layer at a time. Only use joint tuning after a stable layerwise baseline exists
and evidence shows interaction effects are load-bearing.

Default order:
1. Tune stage 1 with everything downstream disabled or fixed
2. Freeze stage 1 best params
3. Tune stage 2 with stage 1 fixed
4. Continue until the full stack is configured

### Search Space Types

| Type | Use when | Examples |
|---|---|---|
| Log | Multiplicative or order-of-magnitude behavior | LR, regularization, decay factors, temperature scales |
| Linear | Narrow bounded ranges, additive behavior | Thresholds in small interval, bonuses near zero, top-k over modest range |
| Categorical | Discrete strategy choices | Ranking mode, distance metric, affinity rule |

`trial.suggest_float("lr", 1e-4, 1e-2, log=True)` vs `trial.suggest_float("threshold", 0.3, 0.9)` vs `trial.suggest_categorical("algo", ["kmeans", "hdbscan"])`.

### Structured Search (Alternative to TPE)

Use when evaluations are expensive and you need interpretability over breadth.

```text
1. Start from a center configuration
2. For each factor, probe center+σ and center-σ
3. Score each probe on the tune bank
4. Record the winning direction per factor
5. Build a joint candidate from all winning directions
6. Run r local refinement samples around the current best
7. Accept only if the new config beats the incumbent

Total budget: baseline + 2N probes + 1 joint + r refinements = 2N + r + 2
```

Benefits over TPE: fixed budget, explicit directional signal per factor, easier interpretation. Tradeoff: less exploration of factor interactions.

### Sampler Policy for LLM Judges

When the evaluator is an LLM judge, score each query with three named sampler takes:

| Take | Purpose |
|---|---|
| `conservative` | Checks evidence under low-variance judging |
| `balanced` | Middle estimate |
| `creative` | Stress-tests coverage under looser reading |

Use the same three takes consistently across all trials so parameter changes are compared under the same judge-variance surface. Per-query score = mean across these three takes before rolling up to the corpus scalar.

### Noise Handling

Never score a trial from one stochastic take. Use multiple sampler settings, repeated seeds, or median-of-k when the scorer has occasional outliers. The rule: do not let evaluator variance masquerade as parameter signal.

### Sampling Policy Contract

If final training uses a fixed-budget sampler, Optuna must evaluate the **same**
sampling regime. Do not search on full-dataset epochs and then deploy a quota or
coverage scheduler later.

Use this split of ownership:
- `stratified-quota-sampling` owns the no-replacement coverage scheduler and quota logic
- `class-balancing` owns residual loss weighting after the sample is drawn
- `optuna-nested-cv` owns the study, search budget, scalar objective, and namespace isolation

Treat any of these as a new study namespace trigger:
- full-epoch training -> fixed-budget coverage training
- with-replacement -> without-replacement sampling
- changed quota family or tier allocation rule
- changed sample fraction or token budget semantics

---

## Scope Boundary

This skill is the **Optuna implementation layer** on top of the general
`hyper-parm_tuning` methodology.

Pair it with `mlflow` when you need searchable experiment history, artifact
comparison, or cross-run lineage. Optuna owns the search loop; MLflow owns
the experiment ledger.

It owns:
- SQLite-backed study persistence and resumability
- TPE sampler configuration and startup budget
- nested cross-validation structure (outer holdout, inner Optuna)
- search over sampler-policy knobs once the sampler contract is fixed
- per-fold normalization to prevent preprocessing leakage
- composite scalar objective construction
- study namespace design to isolate experiments
- trial pruning for degenerate configurations
- seeded domain recipes (ANN training, clustering)

It does **not** own:
- product-level decisions about which metrics matter
- architecture changes mid-search
- sampler mechanics themselves (see `stratified-quota-sampling`)
- class-loss weighting mechanics (see `class-balancing`)
- LLM judge scoring (see `hyper-parm_tuning` for that path)
- experiment UI / artifact registry behavior (see `mlflow`)

## Core Thesis

Optuna is a persistent, resumable black-box optimizer.
Its value is not just finding good params — it is **making every trial
auditable and the search reproducible**.

In practice:

- Optuna's SQLite backend preserves sampler state
- MLflow should preserve run metadata, metrics, and artifacts

Three rules before any search begins:

1. **Fix the pipeline shape.** Optuna tunes values, not structure.
2. **One scalar per study.** Composite is fine; ambiguous is not.
3. **Isolate tune from holdout.** Outer CV provides the unbiased estimate;
   inner Optuna runs only on the outer training fold.

## Nested CV Pattern

This is the load-bearing structure for unbiased evaluation.

```
outer fold i  (holdout for this fold)
    |
    +-- inner Optuna study (runs on outer training data only)
    |       objective: scalar(X_train_fold)
    |       trials: N_TRIALS
    |       study_name: f"{corpus_id}_d{ndim_tag}_outer{i}"
    |
    +-- best inner params -> fit on X_train_fold
    +-- evaluate on X_test_fold  -> outer_score[i]

unbiased_score = mean(outer_score)
final_model    = fit(best_params, X_all)
```

Key rules:
- **Fit the scaler on the training fold only.** Apply to both.
  Fitting on the full corpus before splitting is preprocessing leakage.
- **Outer loop is for evaluation, not selection.**
  Final params come from the best inner trial of the best outer fold,
  not from a re-search on the full corpus.
- **Study names include fold index.**
  `study_outer0`, `study_outer1`, ... so each fold's search is independent
  and resumable separately.

### Per-fold normalization

```python
def normalize_fold(X_train_raw, X_test_raw):
    mins, maxs = X_train_raw.min(0), X_train_raw.max(0)
    denom = np.where((maxs - mins) == 0, 1.0, maxs - mins)
    X_train = (X_train_raw - mins) / denom
    X_test  = (X_test_raw  - mins) / denom   # may exceed [0,1] -- correct
    return X_train, X_test
```

Test fold values outside `[0, 1]` after transform are **correct behavior**,
not a bug. Do not clip them.

## Study Persistence

Always use a SQLite backend so trials survive restarts.

```python
import optuna

study = optuna.create_study(
    study_name  = f"pipeline_{corpus_hash}_d{ndim}_outer{fold_i}",
    storage     = "sqlite:///optuna_runs.db",
    direction   = "maximize",
    load_if_exists = True,
)
```

Then mirror the same campaign into MLflow:

```python
import mlflow

mlflow.set_tracking_uri("file:./mlruns")
mlflow.set_experiment("pipeline_search")
```

Name conventions that prevent collisions:

| Segment | Purpose |
|---------|---------|
| pipeline prefix | identifies the system (e.g., `cluster`, `siamese`) |
| corpus hash (12 chars) | changes when input data changes |
| `d{ndim_tag}` | changes when feature dimensionality or transform changes |
| `outer{i}` | isolates each CV fold |
| `_composite` suffix | separates composite-objective studies from BSS/TSS-only |

If any segment changes, Optuna treats it as a new study and starts fresh.
This is the correct behavior — do not reuse stale studies across config changes.

Apply the same rule to MLflow experiment or tag naming so runs from different
representations are not mixed together.

## MLflow Pairing

Recommended run hierarchy:

```text
campaign run
    outer_fold_0
        trial_000
        trial_001
    outer_fold_1
        trial_000
    final_train
    holdout_eval
```

Minimum MLflow logging for each trial:

- params suggested by Optuna
- scalar objective
- component metrics
- fold index
- study name
- trial number
- any plot or artifact needed to explain the result

Rule:

- do not use MLflow as a replacement for Optuna storage
- do not use Optuna SQLite as a replacement for MLflow artifact tracking

## Composite Scalar Objective

When multiple intrinsic metrics are available, blend them explicitly.

### Clustering example (BSS/TSS + Silhouette)

```python
def composite_score(X, labels):
    sil  = silhouette_score(X, labels)          # [-1, 1]
    bss  = bss_tss(X, labels)                   # [0, 1]
    return 0.5 * ((sil + 1) / 2) + 0.5 * bss   # both mapped to [0, 1]
```

Why silhouette is needed alongside BSS/TSS:
- BSS/TSS can be gamed by singleton clusters (one point = its own centroid,
  maximises between-cluster variance artificially).
- Silhouette penalises singletons — a cluster of one has no neighbours to
  compare against, producing low scores.
- Together they penalise both fragmentation and poor geometric separation.

### ANN training example (loss + downstream metric)

```python
def ann_objective(trial, X_train, X_val, pairs_val):
    lr         = trial.suggest_float("lr", 1e-4, 1e-2, log=True)
    embed_dim  = trial.suggest_categorical("embed_dim", [16, 32, 64])
    dropout    = trial.suggest_float("dropout", 0.0, 0.5)
    margin     = trial.suggest_float("margin", 0.2, 1.0)

    model = train(X_train, lr=lr, embed_dim=embed_dim,
                  dropout=dropout, margin=margin,
                  max_epochs=20, patience=5)   # small budget for search

    val_loss = evaluate_loss(model, X_val, pairs_val)
    return -val_loss   # maximize negative loss = minimize loss
```

## ANN Training Recipe (Siamese / Metric Learning)

This is the seeded recipe for tuning neural embedding models.

### Two-phase protocol

**Phase 1 — Optuna search (small budget)**

- Use a **subset** of training data (e.g. 20-30% or N ≤ 500 pairs)
- `max_epochs = 20`, `patience = 5` (early stopping)
- Search over: `lr`, `embed_dim`, `dropout`, `margin`, `n_layers`
- 30-50 trials is sufficient to find the regime

**Phase 2 — Full training (best params)**

- Apply best params from Phase 1 to the **full training corpus**
- `max_epochs = 100`, `patience = 20`
- Evaluate on holdout at the end — report once, do not re-tune

```python
# Phase 1
study = optuna.create_study(
    study_name="siamese_search",
    storage="sqlite:///optuna_siamese.db",
    direction="minimize",
    load_if_exists=True,
)
study.optimize(lambda t: ann_objective(t, X_sub, X_val, pairs_val),
               n_trials=40)

# Phase 2
best = study.best_params
model = train(X_train_full, **best, max_epochs=100, patience=20)
holdout_score = evaluate(model, X_holdout)
```

This prevents the full corpus training cost from being paid on every trial
while still finding good architecture and regularization parameters.

### What to tune for ANN

| Parameter | Type | Range | Notes |
|-----------|------|--------|-------|
| `lr` | log-float | 1e-4 – 1e-2 | Almost always log scale |
| `embed_dim` | categorical | [16, 32, 64, 128] | Powers of 2 |
| `dropout` | float | 0.0 – 0.5 | Linear |
| `margin` | float | 0.2 – 1.5 | Contrastive/triplet margin |
| `n_layers` | int | 1 – 4 | Linear |
| `batch_size` | categorical | [32, 64, 128] | Often low sensitivity |
| `weight_decay` | log-float | 1e-5 – 1e-3 | L2 regularisation |

Start with `lr`, `embed_dim`, `dropout`, `margin`. Add others only when
those four are stable.

## Clustering Recipe (Silhouette + BSS/TSS)

This is the seeded recipe for unsupervised clustering search.

**Important boundary:** for quote embeddings or retrieval corpora, clustering may
be useful as a routing or diagnostic layer without being the right winner metric.
If the real task is retrieval quality, let Optuna optimize the retrieval
architecture against the real eval target and keep clustering metrics as
diagnostics unless evidence shows clustering is genuinely load-bearing.

### Algorithm candidates

Include multiple algorithm families so Optuna explores the landscape:

```python
def make_objective(X, n_folds):
    def objective(trial):
        algo = trial.suggest_categorical(
            "algo", ["kmeans", "spectral", "agg_ward", "agg_complete",
                     "agg_average", "gmm", "hdbscan"]
        )
        k = trial.suggest_int("k", 2, min(15, len(X) // 2))

        labels = fit_algo(algo, k, X)
        if len(set(labels)) < 2:
            return 0.0   # prune degenerate trial

        return composite_score(X, labels)
    return objective
```

### Affinity-space transform (relational clustering)

When the task is pairwise similarity (recommendation, retrieval), transform
features to the affinity space before clustering:

```python
def cosine_affinity(X_norm):
    norms = np.linalg.norm(X_norm, axis=1, keepdims=True)
    norms = np.where(norms < 1e-10, 1e-10, norms)
    return (X_norm / norms) @ (X_norm / norms).T   # (N, N)
```

Each row becomes the song/item's similarity profile against the corpus.
Clustering in this space optimises for **relational structure** rather than
absolute feature geometry. BSS/TSS is computed in the affinity space.

Observed effect: affinity-space BSS/TSS consistently higher than
feature-space BSS/TSS on small corpora because the dimensionality matches
the cluster count, making separability easier to achieve.

### Modeling tip: transform before search, measure in-space

For clustering, treat the winning result as a three-part recipe:

```text
transform -> search -> measure in-space
```

1. **Transform**
   - move from raw features to the affinity / relational space when the task
     is fundamentally about pairwise similarity
2. **Search**
   - let Optuna compare algorithm families and `k` values under nested CV
3. **Measure in-space**
   - BSS/TSS is the **R^2 of clustering**, so report it in the transformed space
     that the clustering actually used

Example interpretation:

- `BSS/TSS = 0.9664` means the cluster assignments explain about 97% of the
  variance in that representation space

Do not mix spaces when reporting the result. A strong affinity-space BSS/TSS
is evidence about the affinity geometry, not the original raw feature geometry.

### Retrieval-stack note: tune the architecture, not the cluster story

When clustering on quote embeddings does not produce stable gains, stop trying to
make global external clustering "win" the search by itself.

Instead, let Optuna search the retrieval architecture against the real eval
target. Common factors include:

1. broad-pool size
2. GIST utility vs diversity weight
3. graph path weight / hop budget
4. local community threshold or expansion budget inside layer 2
5. entity-overlap bonus
6. whether local grouping is enabled

Use clustering outputs for diagnostics, routing priors, or summarization support
only. Their weak point is that they can still be locally helpful even when they
should not dominate model selection.

### Study namespace for clustering

```python
ndim_tag = f"{n_dims}_{transform}"   # e.g. "139_raw" or "18_affinity"
study_name = f"cluster_{chash[:12]}_d{ndim_tag}_outer{fold_i}"
# composite variant:
study_name_composite = study_name + "_composite"
```

Mirror `study_name` into MLflow tags so the same logical search is queryable
from both systems.

## Trial Budget Guidelines

| Phase | Recommended trials | Rationale |
|-------|--------------------|-----------|
| Startup (TPE warmup) | 10–20 | Random before model is fit |
| Main search | 30–80 | Depends on space size |
| Refinement | 10–20 | Around best found config |

Minimum viable: 30 trials with a 5-10 startup.
For categorical-dominated spaces (algo choice), 40–60 is usually sufficient.

Set `n_startup_trials` on the TPE sampler:

```python
sampler = optuna.samplers.TPESampler(
    n_startup_trials=10,
    seed=42,
)
```

## Pruning Degenerate Trials

Always prune configurations that produce meaningless scores:

```python
# Clustering: all-noise or single cluster
if len(set(labels)) < 2 or (labels == -1).all():
    return 0.0

# ANN: NaN loss
if math.isnan(loss):
    raise optuna.TrialPruned()
```

Returning `0.0` (rather than pruning) for clustering degeneracy is correct
because the sampler needs to learn that the configuration is bad, not just
that it was skipped.

## Resumability Contract

A study is resumable if and only if:
- The study name has not changed
- The storage DB still exists
- The objective function is semantically identical

Check existing trials before running new ones:

```python
n_existing = len([t for t in study.trials if t.value is not None])
n_new = max(0, N_TRIALS - n_existing)
if n_new > 0:
    study.optimize(objective, n_trials=n_new)
```

This pattern prevents re-running trials on expensive objectives when
restarting a search that was interrupted.

## Anti-Patterns

Avoid:
- Running Optuna on the full dataset when a subset suffices for Phase 1
- Reusing a study whose name should have changed (e.g., after a feature
  format change — use `ndim_tag` to force a new namespace)
- Fitting the scaler on the full corpus before fold splits (leakage)
- Using BSS/TSS alone for clustering — it is gameable by singletons
- Treating the outer CV score as the model selection criterion — it is an
  evaluation metric only
- Changing the objective function between trials in the same study
- Skipping holdout validation after search completes
- Logging only the winning trial and throwing away the artifact trail of the rest
<!-- consolidation:see-also:start -->
## See Also
[[hyper-parm_tuning]]  [[representation-pipeline]]  [[mlflow]]
<!-- consolidation:see-also:end -->
