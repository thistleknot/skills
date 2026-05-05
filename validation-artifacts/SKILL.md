---
name: validation-artifacts
description: >
  Mandatory validation artifacts collection protocol. Before claiming "validation
  passed", produce reproducible evidence: training records (holdout splits, loss
  curves, eval metrics), inference results on holdout sets, deterministic test
  logs, visual regression reports, API benchmarks, script execution proofs.
  Use when any skill claims something "works" — enforce artifacts first, claims
  second. Prevents "trust me" validation; makes proof visible and reproducible.
---

# Validation Artifacts — Seeing Is Believing

**Core principle:** "Validation passed" is worthless without proof. This skill enforces mandatory artifact collection before any success claim.

Never accept:
- ❌ "Model trained successfully"
- ❌ "Tests passing"
- ❌ "UI looks good"
- ❌ "API working"

Always demand:
- ✅ Training records (holdout loss curves, final eval metrics)
- ✅ Inference results (predictions on holdout, confusion matrix)
- ✅ Test execution logs (stdout, exit codes, reproducibility)
- ✅ Visual proofs (before/after screenshots, diffs)
- ✅ API benchmarks (latency, throughput, error rates)
- ✅ Script outputs (sample runs with inputs/outputs)

---

## Artifact Categories

### 1. Training Validation (ML/Neural Network Tasks)

**What to capture:**

```
training_artifacts/
├── holdout_split.txt
│   ├── Train size: N_train
│   ├── Val size: N_val
│   ├── Test size: N_test
│   ├── Stratification: (yes/no, what field)
│   └── Random seed: (for reproducibility)
│
├── training_log.csv
│   ├── epoch, train_loss, val_loss, train_accuracy, val_accuracy, learning_rate
│   └── One row per epoch; capture every N steps if frequent
│
├── loss_curve.png
│   ├── X-axis: epoch
│   ├── Y-axis: loss (log scale recommended)
│   ├── Two lines: train_loss (blue), val_loss (red)
│   └── Convergence plot; show where overfitting starts
│
├── eval_metrics.json
│   ├── Test accuracy, F1, precision, recall (per class if multiclass)
│   ├── Confusion matrix
│   ├── ROC-AUC if applicable
│   └── Baseline comparison: "Previous model achieved X, new model Y"
│
├── hyperparams.yaml
│   ├── Learning rate schedule
│   ├── Batch size, optimizer, regularization
│   ├── Early stopping patience, checkpoint strategy
│   └── Any tuning done (Optuna history if applicable)
│
└── reproducibility.txt
    ├── Git commit SHA (what code was trained)
    ├── PyTorch/TF version
    ├── CUDA version if GPU
    ├── Random seeds (numpy, torch, python)
    ├── Data version/commit SHA
    └── Exact command that was run
```

**Validation gate:** Do NOT claim "training complete" until:
- [ ] Holdout split captured and stratified appropriately
- [ ] Loss curve shows convergence (val_loss plateaus or improves monotonically after initial noise)
- [ ] Final test metrics computed on held-out test set (not train/val)
- [ ] No train/val/test data leakage (verify with random seed + data checksums)
- [ ] Hyperparameters documented
- [ ] Command is reproducible (someone else can re-run with same results ±epsilon)

**Red flags:**
- ❌ Val loss still decreasing (model not converged)
- ❌ Train loss >> Val loss (underfitting)
- ❌ Val loss >> Train loss (overfitting; needs regularization)
- ❌ No test set evaluation (only train/val metrics claimed)
- ❌ "Eval loss during training" missing (can't see convergence)

---

#### 1a. SPO Training Pipeline Validation (Synthetic Pair Optimization)

**What to capture for SPO/synthetic pair training:**

When training models on synthetic paired data (original ↔ inferred), collect these specific artifacts:

```
spo_training_artifacts/
├── optuna_tuning/
│   ├── optuna_trials.json
│   │   ├── Trial number, hyperparameters tested, eval_loss achieved
│   │   ├── All trials in sequence (shows search history)
│   │   └── Marked: best_trial_number, best_eval_loss
│   │
│   ├── optuna_config.yaml
│   │   ├── Search space: learning rate range, batch size range, dropout range
│   │   ├── Optimization direction: minimize (loss) or maximize (accuracy)
│   │   ├── Pruner: patience=5, max_epochs=20
│   │   └── Sampler: TPE or grid search
│   │
│   └── best_hyperparams.yaml
│       ├── Learning rate (from Optuna)
│       ├── Batch size
│       ├── Dropout / regularization
│       ├── Optimizer (Adam, SGD, etc.)
│       └── Trial number that found these
│
├── training_phase/
│   ├── best_hyperparams_applied.yaml
│   │   ├── Same as above (confirmation of what was used for final training)
│   │   └── "Using best_hyperparams from optuna trial #42"
│   │
│   ├── training_log.csv
│   │   ├── epoch, train_loss, val_loss, eval_loss
│   │   ├── One row per epoch (full training run)
│   │   ├── Shows all epochs: 1 through final_epoch
│   │   └── Timestamps for each epoch
│   │
│   ├── training_epochs.txt
│   │   ├── "Total epochs trained: N"
│   │   ├── "Early stopping triggered at epoch M (best val_loss at epoch K)"
│   │   ├── "Final epoch: N"
│   │   └── "Training time: X hours"
│   │
│   └── eval_loss_summary.txt
│       ├── "Optuna best eval_loss: <value>"
│       ├── "Final model eval_loss (on holdout): <value>"
│       ├── "Delta: optuna vs final: <value>"
│       └── "Interpretation: (improved/regressed/stable)"
│
└── holdout_validation/
    ├── synthetic_pairs_holdout.csv
    │   ├── Column: original_synthetic (what was in training data)
    │   ├── Column: inferred_output (what model predicted on holdout)
    │   ├── Column: match (yes/no, comparing original vs inferred)
    │   ├── Side-by-side pairing for visual inspection
    │   └── 50-100 representative samples minimum
    │
    ├── holdout_eval_loss.json
    │   ├── "eval_loss_on_holdout": <final_value>
    │   ├── "metric": "cross_entropy / mse / custom_loss"
    │   ├── "dataset_size": N
    │   └── "Note: If not directly available during training, compute from predictions"
    │
    ├── holdout_statistics.txt
    │   ├── "Total holdout samples: N"
    │   ├── "Match rate: X%"
    │   ├── "Mismatch examples: top 10 failures"
    │   └── "Confidence scores: mean, min, max"
    │
    └── loss_comparison.png
        ├── X-axis: epoch
        ├── Y-axis: loss (log scale)
        ├── Line 1: Optuna eval_loss (dashed red, single point at best trial)
        ├── Line 2: Training phase val_loss (solid blue, all epochs)
        ├── Line 3: Final holdout eval_loss (dashed green, single point at end)
        └── Annotations: labels for each, delta between optuna and final
```

**Key insight: Two eval_loss values**
- **Optuna eval_loss**: Best loss achieved during hyperparameter tuning phase (small dataset, 20 epochs max)
- **Final model eval_loss**: Loss on full holdout set after training with best hyperparams (large dataset, full training)
- These will differ; that's expected. Show both for comparison.

**Validation gate:** Do NOT claim "SPO training complete" until:
- [ ] Optuna tuning captured: all trials, best trial number, best_eval_loss
- [ ] Optuna config documented: search space, pruner settings, sampler
- [ ] Best hyperparameters extracted from Optuna and saved
- [ ] Full training run logged: epoch, train_loss, val_loss, final epochs count
- [ ] Final model eval_loss computed on holdout set
- [ ] Holdout validation: synthetic pairs (original ↔ inferred) shown side-by-side in CSV
- [ ] Match rate calculated: how many inferred match original
- [ ] Loss comparison plot: shows Optuna eval_loss vs final model eval_loss visually
- [ ] If final eval_loss not available, compute it from holdout predictions (show calculation)

**Red flags:**
- ❌ Optuna trials not documented (can't see hyperparameter search)
- ❌ Only Optuna eval_loss reported, no final model eval_loss (incomplete validation)
- ❌ Only final eval_loss reported, no Optuna history (can't verify search was good)
- ❌ Final eval_loss suspiciously similar to Optuna eval_loss (suggests data leakage or misreporting)
- ❌ Holdout pairs not shown side-by-side (can't visually verify inferences)
- ❌ Match rate not calculated (how do we know model is working?)
- ❌ Epochs trained not documented (reproducibility question)
- ❌ Loss comparison plot missing (can't see convergence delta)

**Example structure:**

```
spo_training_artifacts/
├── optuna_tuning/
│   ├── optuna_trials.json  (50 trials, best at #42 with eval_loss=0.124)
│   ├── optuna_config.yaml  (search space, pruner patience=5, max_epochs=20)
│   └── best_hyperparams.yaml  (lr=0.001, batch_size=32, dropout=0.2)
│
├── training_phase/
│   ├── best_hyperparams_applied.yaml  (same as above, confirmed)
│   ├── training_log.csv  (120 epochs, final val_loss=0.098)
│   ├── training_epochs.txt  ("Trained 120 epochs, early stopping at epoch 115")
│   └── eval_loss_summary.txt  ("Optuna: 0.124, Final: 0.087, improved by 29.8%")
│
└── holdout_validation/
    ├── synthetic_pairs_holdout.csv  (100 rows: original vs inferred)
    ├── holdout_eval_loss.json  (0.087 on full holdout set)
    ├── holdout_statistics.txt  ("Match rate: 94.2%")
    └── loss_comparison.png  (Shows three points: optuna, training curve, final)
```

**Interpretation guide:**
- If final eval_loss < Optuna eval_loss: ✅ Training improved hyperparams (expected)
- If final eval_loss ≈ Optuna eval_loss: ⚠️ No improvement; check for data leakage or plateau
- If final eval_loss > Optuna eval_loss: ❌ Regression; investigate training dynamics
- Match rate should be >80% for acceptable model quality; <60% is concerning

---

### 2. Inference Validation (Predictions on Holdout)

**What to capture:**

```
inference_artifacts/
├── predictions.csv
│   ├── Sample ID, ground_truth, predicted_class, confidence_score
│   └── 100-200 rows minimum (representative sample)
│
├── confusion_matrix.json
│   ├── Rows: ground truth, Cols: predictions
│   ├── All classes
│   └── Sorted by class name for consistency
│
├── metrics_per_class.json
│   ├── For each class: precision, recall, F1, support
│   ├── Macro-average, weighted-average
│   └── Per-class ROC-AUC if binary/multilabel
│
├── error_analysis.txt
│   ├── Top N misclassified examples
│   ├── Ground truth, predicted, confidence, reason (manual inspection)
│   ├── Patterns: "Model confuses class A with B when feature X is high"
│   └── Actionable insights for next iteration
│
└── inference_latency.json
    ├── Mean latency (ms per prediction)
    ├── P50, P95, P99 latencies
    ├── Throughput (samples/sec)
    ├── Hardware used (CPU/GPU type, batch size)
    └── Baseline comparison: "Previous model: X ms, new model: Y ms"
```

**Validation gate:** Do NOT claim "inference working" until:
- [ ] Predictions generated on held-out test set (not train/val)
- [ ] Confusion matrix computed; inspect for systematic errors
- [ ] Per-class metrics show balanced performance (no class collapse)
- [ ] Error analysis done; failure modes understood
- [ ] Latency measured; meets SLA if applicable
- [ ] Results reproducible with fixed seed

**Red flags:**
- ❌ All predictions are majority class (model learned trivial solution)
- ❌ One class F1 >> others (class imbalance not handled)
- ❌ Confidence scores all ~0.5 (model unsure; needs calibration)
- ❌ Latency > SLA (needs optimization or different architecture)
- ❌ Can't reproduce predictions (non-deterministic; likely RNG not seeded)

---

### 3. Deterministic Validation (Tests, Scripts, Reproducibility)

**What to capture:**

```
script_artifacts/
├── test_results.txt
│   ├── Test command run
│   ├── Timestamp
│   ├── Exit code (0 = pass, nonzero = fail)
│   ├── Stdout (captured)
│   ├── Stderr (if any)
│   └── Summary: N passed, M failed
│
├── test_execution_log.json
│   ├── Per-test: name, pass/fail, duration, output
│   ├── Timestamp for each test
│   └── Total duration
│
├── coverage_report.txt
│   ├── Line coverage %, branch coverage %
│   ├── Uncovered lines (if coverage < 80%, explain why)
│   └── Coverage delta from previous run
│
├── reproducibility_proof.txt
│   ├── Run 1: commit SHA, seed, exit code, summary output
│   ├── Run 2: same, run deterministically again
│   ├── "Identical output achieved on 2 independent runs"
│   └── Timestamps to show no flakiness
│
└── example_runs.txt
    ├── Input examples
    ├── Expected output
    ├── Actual output
    ├── Status: MATCH / DIFFER (with diff if differ)
    └── At least 3 representative examples
```

**Validation gate:** Do NOT claim "script/test passing" until:
- [ ] Full test suite run captured with exit code 0
- [ ] Stdout/stderr logged (especially error cases)
- [ ] Example runs with inputs/outputs provided (not just "works")
- [ ] Reproducibility verified: 2+ independent runs identical
- [ ] Coverage measured (>80% for new code, explain if lower)
- [ ] No flaky tests (run 3x, all pass)

**Red flags:**
- ❌ Exit code nonzero (test failed, not passed)
- ❌ Stderr has warnings or errors (even if exit code 0)
- ❌ Coverage < 60% (undertested code)
- ❌ Run 1 passes, Run 2 fails (flaky; needs investigation)
- ❌ "Works on my machine" with no reproducibility proof

---

### 4. Visual Validation (UI/Frontend Changes)

**What to capture:**

```
visual_artifacts/
├── before_screenshot.png
│   ├── Full page viewport (1920x1080 or consistent size)
│   ├── Timestamp
│   ├── Browser/OS (for context)
│   └── State: fresh load, no user interaction yet
│
├── after_screenshot.png
│   ├── Same viewport, same state
│   ├── Timestamp (after changes applied)
│   ├── Same browser/OS
│   └── Focused on changed region(s)
│
├── visual_diff.png
│   ├── Overlay or side-by-side comparison
│   ├── Highlight added/removed/modified elements
│   └── Use tool like pixelmatch or Visual Regression Tracker
│
├── interaction_flow.txt
│   ├── Steps to reproduce visible state
│   ├── "Click button X → scroll to Y → observe Z"
│   ├── Preconditions (logged in, data loaded, etc.)
│   └── Expected visual result
│
└── accessibility_check.txt
    ├── axe/Lighthouse accessibility audit
    ├── Issues found (if any)
    ├── Contrast ratios, ARIA labels, keyboard navigation
    └── Pass/fail: "No new accessibility issues introduced"
```

**Validation gate:** Do NOT claim "UI change working" until:
- [ ] Before & after screenshots captured at same resolution
- [ ] Visual diff generated; no unintended changes visible
- [ ] Responsive behavior checked (mobile, tablet, desktop)
- [ ] Interaction flow captured; can be reproduced
- [ ] Accessibility audit passed (no new issues)
- [ ] Cross-browser tested (Chrome, Firefox at minimum)

**Red flags:**
- ❌ Before/after screenshots at different resolutions (can't compare)
- ❌ Visual diff shows unintended pixel changes (regression)
- ❌ Layout broken on mobile (responsive design failed)
- ❌ Accessibility audit shows new issues (regression)
- ❌ Only tested in one browser (untested elsewhere)

---

#### 4a. UI Module Unit Testing via Hacks (Autonomous Validation)

**Pattern: Temporary layout hacks + headless PNG capture for autonomous unit testing**

When testing UI modules autonomously without manual interaction, use this workflow:

**Workflow:**
1. **Create hack commit** (test/hack branch or local commit)
   - Modify HTML/CSS to set default state for isolated module testing
   - Examples: hide parent containers, set default form values, change layout to show only target module
   - Commit message: `HACK: Isolate [module] for unit testing via headless PNG capture`

2. **Capture PNG with headless Chromium**
   ```bash
   chromium --headless --screenshot=module_test.png \
     --window-size=1920,1080 \
     file:///path/to/modified/page.html
   ```

3. **Validate visually** (automated or manual review)
   - PNG is clean, module displays correctly in isolation
   - No rendering errors, no broken layouts
   - Text legible, colors correct, spacing as expected

4. **Commit proof**
   - Store PNG: `validation_artifacts/2026-05-03-[module]-unit-test/module_test.png`
   - Store hack diff: `validation_artifacts/2026-05-03-[module]-unit-test/hack_diff.patch`
   - Commit message references both

5. **Revert hack** (tracked separately)
   - `git revert [hack-commit]` or `git reset --hard HEAD~1`
   - Commit message: `Revert hack: Reset [module] to production state`
   - This creates an auditable trace: hack → validate → revert

**Storage convention:**
```
validation_artifacts/2026-05-03-[module]-unit-test/
├── module_test.png                 # Headless capture with isolated module
├── hack_diff.patch                 # Show what UI changes were made
├── headless_command.txt            # Exact chromium invocation for reproducibility
├── test_summary.txt                # What was tested, what passed
└── revert_commit.txt               # SHA of the revert commit (proves we cleaned up)
```

**Git history for accountability:**
```
abc1234 Revert hack: Reset modal to production state
def5678 Add validation artifacts for modal unit test
ghi9012 HACK: Isolate modal component for headless PNG testing
───────────────────────────────────────────────────────
(clean history: hack is visible, but reverted)
```

**Integration with headless-browser-verification:**
- Use headless-browser-verification skill to automate PNG capture and comparison
- Pairs with this artifact pattern to provide "unit test in isolation" capability
- Enables autonomous testing of UI modules without manual browser interaction

**Example use case:**
Testing a modal component:
1. Hack: Hide all overlays, set modal to always-visible state
2. Capture: `chromium --screenshot=modal_open.png page.html`
3. Validate: PNG shows clean, properly-positioned modal with all elements visible
4. Commit: Store PNG + hack diff as proof
5. Revert: `git revert [hack-commit]` to restore production state

**Validation gate for this pattern:**
- [ ] Hack commit clearly labeled "HACK" in message (searchable)
- [ ] PNG captured with headless Chromium (tool + command documented)
- [ ] Hack diff saved showing exact UI changes made
- [ ] PNG looks correct (module renders, no errors)
- [ ] Revert commit exists (proves cleanup, maintains clean history)
- [ ] Timeline auditable: hack → validate → revert (3 commits, all visible)

**Red flags:**
- ❌ Hack commit not clearly labeled (hard to search/audit)
- ❌ PNG captured with manual browser (not reproducible)
- ❌ Hack never reverted (leaves code dirty)
- ❌ No diff saved (can't understand what was hacked)
- ❌ Multiple hacks stacked without intermediate validation (untraceable)

---

### 5. API Validation (REST/GraphQL Endpoints)

**What to capture:**

```
api_artifacts/
├── request_response_samples.json
│   ├── POST /api/users {"name": "Alice", ...}
│   ├── Response: 201 {"id": 123, "name": "Alice", ...}
│   ├── POST /api/users with invalid data
│   ├── Response: 400 {"error": "Name required", "code": "INVALID_INPUT"}
│   └── 5-10 representative request/response pairs
│
├── status_codes.txt
│   ├── Success cases: 200, 201, 204
│   ├── Client error cases: 400, 401, 403, 404
│   ├── Server error: 500 (if applicable)
│   └── Each: example request, actual response code
│
├── latency_profile.json
│   ├── Endpoint, method, mean latency (ms), P50, P95, P99
│   ├── Batch size / concurrency tested
│   ├── Hardware (CPU, RAM, network conditions)
│   └── Delta from baseline: "+5ms vs previous version"
│
├── load_test_results.json
│   ├── Tool: k6, locust, or ab
│   ├── RPS (requests/second) tested
│   ├── Error rate at each RPS level
│   ├── Saturation point (where errors spike)
│   └── SLA compliance: "Maintain <100ms p95 at 1000 RPS? PASS/FAIL"
│
├── schema_validation.txt
│   ├── OpenAPI/GraphQL schema
│   ├── All request params documented
│   ├── All response fields documented
│   ├── Type validation: "String fields are actually strings, not nulls"
│   └── "Schema matches implementation: YES/NO"
│
└── error_handling.txt
    ├── Test: POST with missing required field → 400 with message
    ├── Test: GET with invalid ID → 404 with message
    ├── Test: Concurrent writes to same resource → no corruption
    ├── Test: Rate limiting (if applicable) → 429 after N requests
    └── All error cases handled gracefully
```

**Validation gate:** Do NOT claim "API working" until:
- [ ] Sample request/response pairs provided (5+ cases)
- [ ] All HTTP status codes documented (success and error cases)
- [ ] Schema validation passed (implementation matches docs)
- [ ] Error handling tested (missing params, invalid types, etc.)
- [ ] Latency measured and within SLA
- [ ] Load test results show acceptable error rate at target RPS
- [ ] No data corruption on concurrent access

**Red flags:**
- ❌ No error handling examples (what happens on bad input?)
- ❌ Status code always 200 (no differentiation between success/error)
- ❌ Schema mismatch (docs say field X is String, but API returns null)
- ❌ Latency > SLA (endpoint too slow)
- ❌ Error rate spikes >5% under load (unstable)

---

### 6. Script Validation (CLI Tools, Utilities)

**What to capture:**

```
script_artifacts/
├── execution_samples.txt
│   ├── $ python script.py --help
│   ├── Output: (capture full help text)
│   ├── $ python script.py input.csv --output output.csv
│   ├── Output: "Processed 1000 rows in 2.3s, wrote output.csv"
│   ├── $ python script.py --bad-arg
│   ├── Output: "ERROR: --bad-arg not recognized. Use --help for options."
│   └── 5+ representative runs with inputs and outputs
│
├── error_cases.txt
│   ├── Input: missing required file
│   ├── Output: "ERROR: input_file not found" (helpful message)
│   ├── Exit code: 1 (indicates error)
│   ├── Input: malformed data
│   ├── Output: "ERROR: Line 5 invalid format" (specific problem)
│   ├── Exit code: 1
│   └── All error cases have actionable error messages
│
├── performance.txt
│   ├── Input size: N
│   ├── Execution time: T seconds
│   ├── Memory used: M MB
│   ├── "Baseline: previous version took 10s, new version 2.5s (-75%)"
│   └── Within acceptable range? YES/NO
│
└── data_integrity.txt
    ├── Input: sample data file
    ├── Output: transformed data
    ├── Spot-check: "Row 1 input, expected output, actual output: MATCH"
    ├── Hash check: "Input SHA256: ABC, Output SHA256: XYZ (different OK)"
    └── Manual verification: "Sample rows visually inspected; data looks correct"
```

**Validation gate:** Do NOT claim "script working" until:
- [ ] Sample executions provided with inputs and outputs
- [ ] --help / usage message captured
- [ ] Error cases tested (missing input, bad args, malformed data)
- [ ] Error messages are actionable (not "Error: 1")
- [ ] Performance measured and acceptable
- [ ] Data integrity verified (spot-check, hashing)
- [ ] Exit codes correct (0 for success, 1+ for error)

**Red flags:**
- ❌ No error case examples (what happens on bad input?)
- ❌ Error messages cryptic ("Error code 42")
- ❌ No performance measurement (could be slow)
- ❌ Output data not spot-checked (could be corrupted)
- ❌ Always exits 0 (even on errors; bug)

---

## Artifact Checklist (Copy for Every Task)

Before claiming validation passed:

### Training/ML Tasks
- [ ] Holdout split documented (train/val/test sizes, stratification, seed)
- [ ] Loss curve plot (train vs val, shows convergence)
- [ ] Final eval metrics on test set (not train/val)
- [ ] Confusion matrix or per-class breakdown
- [ ] Hyperparameters documented
- [ ] Reproducibility proof (command, versions, seed, delta-comparison to baseline)
- [ ] Error analysis (why does model fail on certain inputs?)
- [ ] Inference latency measured

### Inference Tasks
- [ ] Predictions generated on held-out test set
- [ ] Confusion matrix computed
- [ ] Per-class metrics (P, R, F1)
- [ ] Error analysis (misclassified examples, patterns)
- [ ] Latency measured (mean, P95, P99)
- [ ] Baseline comparison (previous model vs new)

### Script/Test Tasks
- [ ] Full test run with exit code 0
- [ ] Stdout/stderr captured
- [ ] Example runs provided (inputs → expected → actual output)
- [ ] Reproducibility verified (2+ independent runs identical)
- [ ] Coverage measured (>80% for new code)
- [ ] No flaky tests (run 3x, all pass)

### UI/Frontend Tasks
- [ ] Before & after screenshots (same resolution, same state)
- [ ] Visual diff generated (no unintended changes)
- [ ] Responsive design verified (mobile, tablet, desktop)
- [ ] Accessibility audit passed (no new issues)
- [ ] Interaction flow documented (steps to reproduce)
- [ ] Cross-browser tested (Chrome, Firefox minimum)

### API Tasks
- [ ] Sample requests/responses (5+ cases)
- [ ] Status codes documented (success and error)
- [ ] Schema validation passed
- [ ] Error handling tested
- [ ] Latency measured, within SLA
- [ ] Load test results (RPS, error rate, saturation point)
- [ ] Concurrent access tested (no corruption)

### CLI/Script Tasks
- [ ] Help message captured (--help)
- [ ] Sample executions with outputs (5+ cases)
- [ ] Error cases tested (actionable messages)
- [ ] Exit codes correct (0/1)
- [ ] Performance measured
- [ ] Data integrity spot-checked

---

## Integration with Other Skills

**Used by:**
- `validation` — when claiming "tests pass", demand artifacts
- `checklist` — when LLM-as-judge scores result, require supporting evidence
- `tdd-agent` — before marking Red→Green→Refactor complete, collect artifacts
- `debugging` — when claiming "bug fixed", prove it with before/after artifacts
- `git-workflow` — before pushing to dev, validate with artifacts; diff + proof
- `headless-browser-verification` — UI module unit testing via hacks (Section 4a: hack → capture → validate → revert)

**Pattern:**
```
1. Implement feature/fix
2. Run tests/validation
3. Collect artifacts (this skill)
4. Validate claims against artifacts (validation skill)
5. If artifacts align with claims → proceed to next step
6. If discrepancy found → iterate, recollect artifacts, revalidate
```

**UI Module Testing Pattern (NEW):**
```
1. Create hack commit: modify layout/defaults to isolate module
2. Capture PNG: headless Chromium screenshot of isolated module
3. Validate: PNG looks correct, module renders, no errors
4. Commit artifacts: store PNG + hack diff in validation_artifacts/
5. Revert hack: git revert to restore production state
6. Auditability: hack → validate → revert visible in git log

See Section 4a for detailed workflow and red flags.
```

**Never:**
- ❌ "Validation passed" without artifacts
- ❌ "Tests passing" without test output logs
- ❌ "Model trained" without loss curves
- ❌ "UI looks good" without screenshots
- ❌ "API working" without request/response examples
- ❌ "Module tested" without headless PNG proof (for UI work)

Always:
- ✅ Validation claim + supporting artifacts
- ✅ Artifacts timestamped and reproducible
- ✅ Artifacts linked to specific commit/version
- ✅ Before/after comparison where applicable
- ✅ Error cases demonstrated, not just happy path
- ✅ Hacks tracked and reverted (for UI module testing)

---

## Storage Convention

Artifacts live in `./validation_artifacts/` at project root:

```
project/
├── validation_artifacts/
│   ├── 2026-05-03-training/
│   │   ├── holdout_split.txt
│   │   ├── training_log.csv
│   │   ├── loss_curve.png
│   │   └── eval_metrics.json
│   ├── 2026-05-03-ui-change/
│   │   ├── before_screenshot.png
│   │   ├── after_screenshot.png
│   │   └── visual_diff.png
│   └── 2026-05-03-api-test/
│       ├── request_response_samples.json
│       ├── latency_profile.json
│       └── load_test_results.json
└── ...
```

Commit artifacts to git (or store external URLs in manifest if files too large):
```
git add validation_artifacts/
git commit -m "Add validation artifacts for feature X

- Training: loss curves, eval metrics, holdout split
- Inference: confusion matrix, per-class metrics
- Reproducibility: command, versions, seeds

Proof: Artifacts stored in validation_artifacts/2026-05-03-*
```

---

## References

- ML model validation: Goodfellow et al., "Deep Learning", Ch. 7 (Regularization)
- Test coverage: Martin Fowler, "Test Pyramid"
- API testing: REST Assured, Postman Collections
- Visual regression: Percy, Chromatic, Visual Regression Tracker
- Load testing: k6 documentation, Locust
<!-- consolidation:see-also:start -->
## See Also
[[headless-browser-verification]]  [[git-workflow]]  [[agentic-harness]]
<!-- consolidation:see-also:end -->
