---
name: marginal-poly-compression
description: >
  Compress a 2D joint count table (categories x sources) into a compact
  (x, y, z) state where x and y are marginal proportion vectors and z is a
  single global scalar derived from the best-fit polynomial form over those
  marginals. Use when you need a compact, reconstructable representation of
  a multi-dimensional dataset composition for balancing, sampling, or state
  tracking. Cross-reference: crystallization (digest protocol), adaptive-rl-sampler
  (sampling use case + GRPO advantage connection), multigran-sparse-retrieval
  (corpus composition context).
status: active
last_validated: 2026-06-24
validation_method: session + empirical (scipy CV run on RL_V2 dataset composition)
---

# Marginal Polynomial Compression

## Driving Question

Given a joint count matrix O[i,j] over two categorical dimensions (e.g. task
category x dataset source), can we represent the full joint as a compact state
(x, y, z) — where x and y are marginal vectors and z is a single scalar —
such that the original table is approximately reconstructable, at compression
ratio >> 1x, with empirically bounded error?

**Answer: yes**, with the form selected by cross-validated polynomial search
and z solved analytically as the mean residual.

---

## Conceptual Lineage

This method synthesizes three prior threads:

| Source concept | Contribution |
|---|---|
| Log-normal / Box-Cox / Markowitz | Distributions have a natural parameterization. Transform into that space before operating. The polynomial exponent search is the transform search. |
| QLoRA (base + LoRA adapter) | You don't store the full thing. Store a good-enough base approximation + a small correction. z is the adapter. x²+y³ is the frozen base. |
| RL state representation | Ask: what is the minimal sufficient statistic for reconstructing the joint? (x, y, z) is the compressed state; reconstruct to nominal on demand. |
| GRPO advantage | z is structurally the group-normalized advantage: a residual of observed score vs distribution-predicted score. GRPO assumes the form is linear; this framework searches it. |

The through-line: **operate in compressed space, reconstruct to nominal only when needed.**

---

## Core Decomposition

```
O_ij  ≈  N * (z + f(x_i, y_j))

where:
  x_i   = row marginal proportion for category i  (row_sum_i / N)
  y_j   = col marginal proportion for source j    (col_sum_j / N)
  f     = polynomial form, selected by CV
  z     = global scalar, solved analytically as mean residual
  N     = grand total count
```

**z is not fit by gradient descent.** Given a fixed form f, z has a closed-form solution:

```
z = mean over observed cells of (O_ij / N - f(x_i, y_j))
```

This is exact: z absorbs the mean offset between the polynomial surface and
the normalized observed counts. MSE is then the residual variance around that
offset.

**Space comparison:**

```
nominal:    x * y  cells
compressed: x + y + 1  values
break-even: x > 2 and y > 2  (viable for any non-trivial grid)
```

---

## Theoretical Connections

### Independence model (baseline)

The simplest form `f(x_i, y_j) = x_i * y_j` is the independence model —
expected counts under the null that category and source are independent.
This is the rank-1 outer product, equivalent to a log-linear model with no
interaction term:

```
log(E_ij) = μ + α_i + β_j   (no γ_ij interaction)
```

z corrects the global offset; it cannot fix cell-level interaction. If the
interaction is heterogeneous (some cells positively coupled, others negatively),
a single z is insufficient — see Failure Modes.

### Saturated model (exact recovery)

If you store the full residual matrix R = O − E, you recover nominal exactly.
This is the saturated log-linear model. The present skill trades exact recovery
for compression by replacing R with a single scalar z plus a polynomial surface.

### PMI connection

The per-cell log ratio `log(O_ij / E_ij)` is pointwise mutual information (PMI).
z is a global PMI approximation — one number summarizing the average coupling
strength across all cells. Positive z = joint is denser than margins predict
on average. Negative z = sparser.

### Residual Vector Quantization (RVQ) analog

The correct ML analog to "track residual to recover nominal" is RVQ (stacked
codebooks, each coding what the prior missed) — not NF4. NF4 is the codec
for storing the residual cheaply when residuals are approximately normal.
The full stack: rank-1 base → polynomial correction → z offset → NF4-store z
if memory is critical.

---

## The GRPO Connection (z as Advantage)

The z term in this framework is structurally identical to the **group-normalized
advantage in GRPO**. Both are residuals: a deviation of an observed score from
what the surrounding distribution predicts.

### The exact correspondence

| GRPO | This framework |
|---|---|
| raw reward `r` | observed proportion `O_ij / N` |
| group mean `mean(r)` | polynomial prediction `f(x_i, y_j)` |
| advantage `(r - mean(r))` | residual `O_ij/N - f(x_i, y_j)` |
| std-normalize `/ std(r)` | optional: divide residual by std of residuals |
| advantage drives token prob update | residual drives cell proportion rebalance |

### Concrete GRPO example

```
prompt: "What is 2 + 2?"   (one group, 4 completions)

completion 1: "4"     raw reward 1.0
completion 2: "4"     raw reward 1.0
completion 3: "5"     raw reward 0.0
completion 4: "fish"  raw reward 0.0

group mean = 0.5, group std = 0.5

z_1 = (1.0 - 0.5)/0.5 =  1.0
z_3 = (0.0 - 0.5)/0.5 = -1.0

loss = -z * log_prob(completion_tokens)
  → push prob up where z > 0 ("4")
  → push prob down where z < 0 ("5", "fish")
```

z is the **signal, not the reward**. Raw reward 1.0 alone says nothing about
whether "4" was surprisingly good or merely expected. z says: relative to what
this prompt/model combination normally produces, this completion was +1 SD above
average. That is the residual this framework computes.

### Applying it back to (model, sub-topic)

For a count matrix where x = model, y = sub-topic:

```
nominal:      O_ij / N           observed proportion at cell (i,j)
interpolated: f(x_i, y_j)        polynomial prediction for that cell
z_ij:         O_ij/N - f(x_i,y_j)  per-cell residual (the advantage)
z (global):   mean over cells of (O_ij/N - f(x_i, y_j))
```

The rebalancing update rule mirrors the GRPO gradient step:

```
under-represented cell (z_ij > 0)  → needs more samples
over-represented cell  (z_ij < 0)  → needs fewer samples
```

GRPO balances completion token probabilities. This framework balances dataset
cell proportions. Same operation, different surface.

### What GRPO assumes that this framework makes explicit

GRPO's normalization is `(r - mean) / std` — a Gaussian/linear form with uniform
weights. In this framework's terms, GRPO implicitly fixes:

```
form = linear,  a = 1,  b = 1,  exponents = 1,  no architecture search
```

This framework generalizes that: the polynomial form is searched empirically by
CV, not assumed. If the within-group reward distribution is log-normal or
heavy-tailed, a different form produces better-normalized advantages. That gap —
**form selection is architecture search, and it happens before the gradient, not
during it** — is the contribution.

### The gradient-descent / weight interpretation

The general form with learnable weights:

```
z + a·x^p + b·y^q
```

In log space this is linear:

```
log(pred) = log(z) + log(a) + p·log(x) + log(b) + q·log(y)
```

That is a single-layer net with log-transformed fixed inputs. The exponents p, q
are weights on `log(x)` and `log(y)`; the powers are multiplicative layers in log
space. When x and y are fixed (observed marginals), z has a closed-form solution
(mean residual) — no gradient needed. GRPO needs iterative descent only because
its analog of y (the model) updates every step, shifting the marginals, so z must
be re-solved continuously rather than once.

**Boundary condition — where the analogy holds:** the partition between input and
output must be structural. In NTP / continued pretraining every token is both
input and target, the x/y distinction collapses, and z has no clean meaning. In
completion tuning (SFT / GRPO) the prompt is fixed context (no gradient) and the
completion is where weights move — that is where input=x, output=y, score=z holds
cleanly.

---

## Algorithm

### Step 1: Compute marginals

```python
N = O.sum()
x = O.sum(axis=1) / N   # shape: (n_categories,)
y = O.sum(axis=0) / N   # shape: (n_sources,)
```

### Step 2: Define candidate forms

Enumerate over:
- Additive power: `x^a + y^b` for a,b in {1,2,3}
- Multiplicative: `x^a * y^b` for a,b in {1,2,3}
- Cross terms: `x^a + y^b + x^c * y^d` for a,b,c,d in {1,2}
- Log transforms: `log(x) + log(y)`, `log(x+y)`
- Root transforms: `sqrt(x) + sqrt(y)`, `sqrt(x*y)`

Do not hardcode `x² + y³`. The exponents are hypotheses, not axioms.

### Step 3: For each form, solve z and compute CV MSE

```python
# Solve z analytically (train cells only)
z = mean(O_ij/N - f(x_i, y_j))  over train_mask

# Evaluate MSE (val cells)
MSE = mean((O_ij - N*(z + f(x_i, y_j)))^2)  over val_mask
```

Use k-fold CV over **nonzero cells only** (structural zeros are not
observations — they are definitional absences and should not be fit).

### Step 4: Select best form by validation MSE

Sort by val MSE ascending. The winner defines the canonical f for this dataset.

### Step 5: Solve z on full observed data

```python
z_final = mean(O_ij/N - f_best(x_i, y_j))  over all nonzero cells
```

### Step 6: Compressed state

```python
state = (x, y, z_final)   # x+y+1 values total
```

### Step 7: Reconstruction

```python
O_hat_ij = N * (z_final + f_best(x_i, y_j))
```

---

## Diagnostics

### Sparsity / block-diagonal diagnostic

Compute val/train MSE ratio across the top-k forms.

```
ratio > 3  →  block-diagonal structure dominates.
             Global z cannot generalize across the structural zeros.
             Decompose: one z per category instead of one global z.
             State becomes x + y + n_categories, still << x*y.

ratio ≤ 3  →  global z generalizes. Proceed.
```

Your RL_V2 dataset (6 categories x 15 sources, block-diagonal by construction)
returned ratio = 1.21 — global z generalizes despite the sparse structure.

### Compression ratio

```
compression = (x * y) / (x + y + 1)
```

RL_V2 result: 90 cells → 22 values = **4.1x compression**.

### MSE interpretation

MSE is in raw count² units. Normalize by mean cell count for a relative error:

```
relative_error = sqrt(MSE) / mean(O[O > 0])
```

If relative_error > 0.5, the polynomial surface is a poor fit — consider
per-category z or switching to the saturated (full residual) representation.

---

## Failure Modes

### Block-diagonal joint with heterogeneous interaction

When sources are nested within categories (not crossing them), the joint is
block-diagonal. A single global z fits the within-block average but cannot
differentiate between blocks. Use per-category z (one scalar per row partition).

### Homogeneous z assumption violated

If some cells are positively coupled and others negatively, z is pulled toward
zero and the polynomial surface dominates. The residual table `R = O − E` will
show mixed signs. Switch to low-rank (SVD of R, keep top-k components) or
sparse (store only large-residual cells).

### Overfitting a high-degree form

Cross terms like `x²*y² + x³*y³` can fit training cells closely while
generalizing poorly. Val MSE is the guard. Never select on train MSE alone.

### Structural zeros included in fit

Including definitional zero cells (source X never appears in category Y by
construction) inflates the zero-mass and drives z negative. Always mask to
observed (nonzero) cells before fitting.

---

## When Per-Category z is Warranted

Use one z per category when:
- The grid is block-diagonal (sources nested in categories)
- You want to track within-category source skew independently
- The global sparsity diagnostic returns ratio > 3

State then becomes: `x (n_cat) + y (n_src) + z_vec (n_cat)` = `2*n_cat + n_src`

This is still << `n_cat * n_src` for any non-trivial grid.

---

## Use Cases

| Use case | How this applies |
|---|---|
| Dataset composition balancing | (x, y, z) encodes current composition; target state encodes desired balance; delta drives resampling |
| RL state representation | Compressed state fits in observation vector; reconstruct to nominal for reward computation |
| Multi-dataset training curriculum | Track z drift across training steps as a signal for when composition has drifted from target |
| Corpus audit | High-residual cells (O_ij >> N*(z+f)) flag over-represented source/category pairs |

---

## Reference Implementation

`poly_form_search.py` — full form enumeration, k-fold CV, z solve, diagnostics.
Runs on any 2D numpy count matrix. Swap O and the CATEGORIES/SOURCES labels.

Key functions:
- `compute_marginals(O)` → x, y, N
- `make_forms()` → list of Form(name, fn)
- `solve_z(O, x, y, N, form, mask)` → scalar z
- `cross_validate(O, x, y, N, form, k)` → (train_mse, val_mse)

---

## Open Questions

1. **Optimal exponent theory**: is there a principled way to predict which
   exponents will win from the distribution shape of x and y, without
   exhaustive search? Candidate: the exponent that linearizes the marginal
   CDF (Box-Cox connection).

2. **z as a time series**: if dataset composition shifts across training
   epochs, does z drift monotonically or oscillate? Does z-drift correlate
   with model performance degradation?

3. **Multi-dimensional extension**: three categorical dimensions (model x
   category x source) → can this decompose as x + y + w + z where z still
   absorbs the three-way interaction as one scalar?

4. **NF4 storage of z**: if z is tracked across many datasets or epochs,
   does the distribution of z values across datasets fit the NF4 normal
   assumption well enough to justify 4-bit storage?

5. **IPF relationship**: iterative proportional fitting (raking) targets
   specific margin totals and adjusts the joint. Does the polynomial form
   search converge to the same solution as IPF under any conditions?

6. **GRPO form search**: GRPO normalizes advantage as `(r - mean) / std`,
   a fixed linear/Gaussian form. Does replacing that with the CV-selected
   polynomial form produce better-normalized advantages when the within-group
   reward distribution is log-normal or heavy-tailed? Testable directly from
   GRPO training logs — the per-step group advantage statistics are z.

7. **z drift across training epochs**: if the model (y-analog) updates each
   step, z must be re-solved continuously. Does z drift monotonically or
   oscillate, and does z-drift correlate with performance degradation?
   Directly answerable from GRPO logs since the group advantage stats are z.

---

## Lessons

- **z is not the form** — the polynomial form f is the hypothesis; z is just
  the mean residual given that hypothesis. Pick f by CV, then z is determined.

- **Structural zeros are not data** — fitting them drives z toward zero and
  masks real interaction signal. Always mask before fitting.

- **NF4 belongs on the residual, not the base** — NF4's normal quantile
  assumption fits Pearson residuals `(O-E)/sqrt(E)`, not raw counts.
  If compressing z storage, normalize first.

- **The independence model is your null, not your answer** — compute E_ij =
  r_i * c_j / N as a baseline. The residual table R = O - E is your
  balancing priority map: high positive residual = structurally
  over-represented, needs downsampling.

- **Val/train MSE ratio is the block-diagonal diagnostic** — if it stays
  near 1 despite sparse structure, global z generalizes. If it blows up,
  decompose to per-category z before concluding the method fails.

- **z is GRPO's advantage in disguise** — both are residuals of an observed
  score against a distribution-predicted score. GRPO fixes the form (linear,
  std-normalized); this framework searches it. Form selection is architecture
  search, and it happens before the gradient, not during it.

- **The analogy needs a structural input/output partition** — it holds for
  completion tuning (prompt fixed = x, completion = y, score = z) and
  collapses for NTP/continued pretraining where every token is both input
  and target.

---

## Entities Involved

- `RL_V2/pull_datasets.py` — dataset composition pipeline that produced the
  empirical count matrix validating this method
- `poly_form_search.py` — reference implementation
- `solver_setup.csv` — Excel Solver mockup for interactive exploration
- Concepts: independence model, log-linear model, PMI, RVQ, QLoRA, Box-Cox,
  IPF/raking, correspondence analysis, saturated model, Pearson residuals