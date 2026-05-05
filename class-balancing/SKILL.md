---
name: class-balancing
description: >
  Box-Cox log-ratio class weighting protocol for imbalanced classification.
  Use when computing per-class weights for CrossEntropyLoss (PyTorch) or
  class_weight in sklearn. Provides mathematically grounded weights that
  outperform inverse-frequency for heavy-tailed distributions. Called by
  pdf-extraction skill for layout classifier training.
status: active
last_validated: 2026-05-02
---

# Class Balancing Skill

## When to Use This vs Alternatives

| Situation | Recommended approach |
|-----------|---------------------|
| Mild imbalance (worst ratio < 10:1) | `class_weight='balanced'` (sklearn) or inverse-frequency |
| Heavy-tail / power-law counts | **Box-Cox log-ratio** (this skill) |
| Very small minority classes (< 5 samples) | SMOTE or oversampling first, then Box-Cox |
| Multi-label or ordinal targets | Per-label inverse frequency; Box-Cox per class |
| Regression imbalance (target density) | Kernel density reweighting instead |

---

## Scope Boundary and Paired Skills

Use this skill for **loss weighting after sample selection**, not for choosing
which records enter a batch or epoch.

| Need | Owner |
|------|-------|
| Choose records from an imbalanced pool under a fixed coverage budget | `stratified-quota-sampling` |
| Reweight class loss after the sample has already been chosen | `class-balancing` |
| Tune sample fraction, quota ratios, or weighting knobs against a scalar objective | `optuna-nested-cv` |

Rules:
- Do **not** use class weights as a substitute for a no-replacement coverage scheduler.
- Do use this skill after quota sampling when the selected subset still has meaningful residual skew.
- If the weighting policy is part of the model-selection surface, namespace the Optuna study separately from runs that use a different sampler or weighting contract.

---

## Box-Cox Log-Ratio Protocol

### Rationale

Raw inverse-frequency `N/count_c` over-penalises the majority class and
under-penalises moderate minorities. Taking the log compresses the range;
Box-Cox then finds the optimal power transform so the weight distribution
is closer to Gaussian — giving smoother gradient signals than either raw
inverse-frequency or log-inverse alone.

### Algorithm

```python
from collections import Counter
from scipy.stats import boxcox
import numpy as np

def boxcox_class_weights(labels: list) -> dict:
    """
    Compute per-class weights via Box-Cox transform of log-inverse-frequency.

    Require: at least 2 distinct classes; all counts >= 1.
    Guarantee: returns {class_name: weight}; weights are non-negative.
    Failure modes:
        - Single class: returns {class: 1.0}
        - boxcox ValueError: falls back to raw log-inv
    """
    counts = Counter(labels)
    if len(counts) < 2:
        return {c: 1.0 for c in counts}

    N = len(labels)
    classes = sorted(counts)

    # Step 1: log-inverse-frequency (strictly positive for all minority classes)
    log_inv = np.array([np.log(N / counts[c]) for c in classes], dtype=float)
    log_inv = np.clip(log_inv, 1e-6, None)   # majority class may be ~0; add eps

    # Step 2: Box-Cox transform (finds optimal lambda automatically)
    try:
        bc, lam = boxcox(log_inv)
    except Exception:
        bc = log_inv   # fallback

    # Step 3: clip negatives, normalize to sum=1
    bc = np.clip(bc, 0.0, None)
    total = bc.sum()
    if total < 1e-9:
        bc = np.ones_like(bc)
        total = bc.sum()

    return {c: float(bc[i] / total) for i, c in enumerate(classes)}
```

### PyTorch usage
```python
import torch
import torch.nn as nn

weights = boxcox_class_weights(train_labels)
classes = sorted(weights)
w_tensor = torch.tensor([weights[c] for c in classes], dtype=torch.float32).to(device)
criterion = nn.CrossEntropyLoss(weight=w_tensor)
```

### sklearn usage
```python
from sklearn.linear_model import LogisticRegression

weights = boxcox_class_weights(train_labels)
sample_weights = np.array([weights[lbl] for lbl in train_labels])
clf = LogisticRegression()
clf.fit(X_train, y_train, sample_weight=sample_weights)
```

---

## Comparison: Weighting Methods

| Method | Formula | When it works |
|--------|---------|---------------|
| Inverse frequency | `N / count_c` | Mild imbalance; linear scale acceptable |
| Log-inverse | `log(N / count_c)` | Moderate imbalance; compresses extremes |
| **Box-Cox log-inverse** | `BC(log(N/count_c))` | Heavy-tail; optimal transform per dataset |
| Effective samples | `(1-β^n)/(1-β)` | Few-shot; small N per class |
| SMOTE | Synthetic oversample | Minority too sparse for reweighting |

---

## IQR / MAD Relationship (for outlier-robust counts)

When label counts themselves contain outliers (e.g., corpus sampling bias),
apply robust preprocessing before weighting:

```python
import numpy as np

counts_arr = np.array(list(counts.values()), dtype=float)
median = np.median(counts_arr)
mad = np.median(np.abs(counts_arr - median))
upper_fence = median + 4.0 * mad   # ≈ Tukey IQR*1.5 under normality (~2.7σ)
# Cap runaway majority classes
capped = {c: min(v, upper_fence) for c, v in counts.items()}
```

Note: `IQR * 1.5 ≈ median + 4 * MAD` under normality (2.698 × 1.4826 ≈ 4.0).
Under heavy-tailed data, calibrate the MAD multiplier empirically.

---

## Used By

| Consumer | Usage |
|----------|-------|
| `pdf-extraction` | `train_layout_classifier.py` — EfficientNet-B0 layout region classifier |
| Any PyTorch classifier | Drop-in `CrossEntropyLoss(weight=...)` |
| Any sklearn estimator | Drop-in `sample_weight=` array |
| `stratified-quota-sampling` users | Residual class weighting after quota-based subset selection |
<!-- consolidation:see-also:start -->
## See Also
[[stratified-quota-sampling]]  [[mad-dynamic-batching]]  [[optuna-nested-cv]]  [[timeout-guard]]  [[mlflow]]
<!-- consolidation:see-also:end -->
