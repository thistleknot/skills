---
name: pmi-coverage-deviation
description: >
  Surface where a 2D joint count table (e.g. model x sub-topic) deviates from
  its independence baseline, using pointwise mutual information (PMI) as the
  per-cell deviation signal. Use when many categories share the same sub-topics
  (a dense joint) and the valuable information is which (category, sub-topic)
  pairs are over- or under-represented relative to what their marginals alone
  predict. The residual is the product, not a compression error. Cross-reference:
  crystallize (digest protocol), adaptive-rl-sampler (advantage = additive
  residual), multigran-sparse-retrieval (corpus composition context).
status: active
last_validated: 2026-06-24
validation_method: session + empirical (CV polynomial run; PMI reframing)
---

# PMI Coverage Deviation

## First-Principles Architecture

The whole method in one line: **subtract out what the marginals already explain,
and study what is left.**

Given a joint count matrix `O[i,j]` over two categorical dimensions — for
concreteness, `i = model` (or domain / data source) and `j = sub-topic` — most
of the table is boring. A cell is large because its model is large and its
sub-topic is common. That is structure you already know from the row and column
totals alone. The independence baseline predicts it exactly.

The information lives in the **deviation**: how much more or less a cell holds
than the independence baseline predicts. A model that covers a sub-topic *more
than its overall size would imply* is telling you something real about that
model's specialization. A model with a gap where its peers are full is telling
you about a coverage hole. The marginals are the null. The deviation is the
signal.

Pointwise mutual information (PMI) is the canonical name for that deviation in
log-ratio form. This skill is built around it.

```
workflow:
  1. compute marginals (row, col proportions) from O
  2. compute independence baseline  E_ij = row_i * col_j / N
  3. compute PMI_ij = log(O_ij / E_ij)   <- the deviation signal
  4. choose additive vs log-ratio depending on size heterogeneity
  5. read the residual table as a differential coverage audit
  6. (optional, secondary) compress O to (x, y, z) if a compact
     reconstructable state is also wanted
```

Preconditions: `O` is a 2D non-negative count matrix; the joint is **dense**
(sub-topics genuinely repeat across categories). For a block-diagonal joint
(sub-topics nested within categories, no crossing) this method is degenerate —
there is no cross-structure to deviate, and PMI is undefined or trivial in the
empty cells.

Failure modes: structural zeros make raw PMI go to `-inf` (smoothing required);
heterogeneous category sizes let additive residuals be dominated by the big
categories (use log-ratio); a single cell can be high-PMI purely from low counts
(guard with a count threshold or NPMI).

---

## Pointwise Mutual Information, Expanded

**Pointwise mutual information** measures how much two specific outcomes co-occur
relative to what independence would predict. For a model `i` and sub-topic `j`:

```
PMI(i, j) = log(  P(i, j)  /  ( P(i) * P(j) )  )

with:
  P(i, j) = O_ij / N            observed joint proportion
  P(i)    = row_sum_i / N       model marginal   (your x)
  P(j)    = col_sum_j / N       sub-topic marginal (your y)

equivalently, in raw counts:
  PMI(i, j) = log(  O_ij * N  /  ( row_sum_i * col_sum_j )  )
            = log(  O_ij  /  E_ij  )
  where E_ij = row_sum_i * col_sum_j / N   is the independence baseline.
```

Reading the value:

- `PMI > 0` — the pair co-occurs **more** than independence predicts. This model
  over-covers this sub-topic relative to its size. Specialization signal.
- `PMI = 0` — the pair is exactly at baseline. The marginals fully explain the
  cell. No information beyond the totals.
- `PMI < 0` — the pair co-occurs **less** than predicted. A coverage gap this
  model's peers fill but it does not.

PMI is the per-cell version of the deviation you described: *how much more or
less is the nominal over the interpolated baseline*, in log units so that
proportional surprise is symmetric and size-independent.

### Variants and when to use each

| Variant | Formula | Use when |
|---|---|---|
| Raw PMI | `log(O_ij / E_ij)` | general deviation; symmetric over/under signal |
| Positive PMI (PPMI) | `max(0, PMI)` | you only care about over-coverage; drop the gaps |
| Normalized PMI (NPMI) | `PMI / -log(P(i,j))` | you need a bounded `[-1, 1]` score comparable across cells of different sizes |
| Additive residual | `O_ij - E_ij` | you want raw excess *records*, and category sizes are comparable |

For a coverage audit across **heterogeneous model sizes**, log-ratio (PMI or
NPMI) wins: additive residuals let the big models dominate the signal, while
log-ratio surfaces proportional surprise in small cells too. NPMI is the safest
default when you want one comparable number per cell.

---

## Additive vs Log-Ratio — The Load-Bearing Choice

This single decision changes what the residual table surfaces:

```
additive   R_ij = O_ij - E_ij        units: records
           surfaces large ABSOLUTE gaps
           dominated by big categories
           analog: GRPO advantage (reward - baseline)

log-ratio  PMI_ij = log(O_ij / E_ij) units: nats / bits
           surfaces proportional SURPRISE
           size-independent
           analog: log-odds, mutual information, surprisal
```

Decision rule:
- comparable category sizes, you care about raw record counts → **additive**
- heterogeneous sizes, you care about specialization regardless of scale → **log-ratio (PMI)**

A model built to span many sub-topics (your systems-design framing) is exactly
the heterogeneous-size case: use PMI so a small but disproportionately focused
model is not drowned out by a large generalist one.

---

## The Coverage Audit (the actual output)

For the dense case — many models, shared sub-topics — the PMI table is a
**differential coverage map**:

```
PMI matrix:  rows = models,  cols = sub-topics,  cell = log(O/E)

read it as:
  per row (model):     where does this model over-invest / under-invest
                       relative to the shared baseline every model is measured against
  per column (subtopic): which models specialize in / neglect this sub-topic
  top positive cells:  surprising concentrations (specialization)
  top negative cells:  surprising gaps (coverage holes)
```

The concrete question it answers: **which (model, sub-topic) pairs are
surprising** — meaning their count is not explained by the model being big or
the sub-topic being common, but by a real interaction between the two.

This is the independence model used as a **null hypothesis**, exactly as in a
chi-square test of independence: `E_ij` is the expected count under independence,
and the deviation `O_ij - E_ij` (or its log-ratio PMI) is the excess that
rejects the null for that cell.

---

## Algorithm

### Step 1: Marginals

```python
N = O.sum()
row_p = O.sum(axis=1) / N    # P(i), model marginal  (x)
col_p = O.sum(axis=0) / N    # P(j), sub-topic marginal (y)
```

### Step 2: Independence baseline

```python
E = np.outer(O.sum(axis=1), O.sum(axis=0)) / N   # E_ij = row_i * col_j / N
```

`E` is the rank-1 outer product of the margins — the maximum-entropy joint
consistent with the observed totals. It is what the table would be if model and
sub-topic were independent.

### Step 3: PMI with smoothing

Raw `log(O/E)` is `-inf` wherever `O_ij = 0`. Smooth before the log:

```python
eps = 0.5                      # additive (Laplace) smoothing on counts
O_s = O + eps
E_s = np.outer(O_s.sum(axis=1), O_s.sum(axis=0)) / O_s.sum()
PMI = np.log(O_s / E_s)        # natural log -> nats; use log2 for bits
```

Optionally normalize to `[-1, 1]`:

```python
P_joint = O_s / O_s.sum()
NPMI = PMI / (-np.log(P_joint))
```

### Step 4: Count guard

A cell can show high PMI purely from a tiny count. Mask cells below a minimum
observed count before ranking, so the audit surfaces real concentrations, not
noise:

```python
reliable = O >= min_count      # e.g. min_count = 5
PMI_audit = np.where(reliable, PMI, np.nan)
```

### Step 5: Rank the deviations

```python
# top over-covered (specialization)
top_pos = sorted_cells(PMI_audit, descending=True)
# top under-covered (gaps)
top_neg = sorted_cells(PMI_audit, descending=False)
```

### Step 6 (secondary): Compact state, if also wanted

If, in addition to the audit, you want a compact reconstructable state, the
margins plus a single global scalar `z` recover an approximation:

```
O_ij_hat = N * (z + f(x_i, y_j))
z         = mean over cells of (O_ij/N - f(x_i, y_j))
f         = best polynomial form by cross-validated MSE
```

This is the compression view. It is **secondary** — the residual you discard to
get a clean `z` is the same residual the coverage audit is built from. Do not let
compression throw away the signal you came for.

---

## Theoretical Connections

| Concept | Relationship |
|---|---|
| Independence / log-linear model | `E_ij = row_i·col_j/N` is the no-interaction model; PMI is the interaction term `γ_ij` in log form |
| Chi-square test of independence | `(O-E)²/E` summed is χ²; the per-cell `O-E` is the additive residual, PMI is its log-ratio sibling |
| Mutual information | `MI = Σ P(i,j)·PMI(i,j)` — PMI is the per-cell term whose expectation is MI; the audit is MI decomposed by cell |
| TF-IDF / word association | PPMI over a term-context matrix is a classic NLP weighting; same operation, different matrix |
| Correspondence analysis | SVD of the (standardized) residual table gives model and sub-topic coordinates — the vector version of this audit |
| GRPO advantage | `reward - group_mean` is the **additive** residual against a baseline; PMI is the **log-ratio** form of the same deviation idea |
| QLoRA / RVQ | base + residual decomposition; here the independence baseline is the base, PMI is the residual you actually want |

---

## Failure Modes

### Block-diagonal joint (wrong dataset)

If sub-topics are nested within models (each sub-topic appears in one model
only), the joint is block-diagonal, off-block cells are structural zeros, and PMI
is either undefined or trivially extreme. This method needs a **dense** joint
where sub-topics genuinely repeat across models. The original RL_V2 dataset-source
table was this degenerate case; the coverage audit does not apply to it.

### Structural zeros vs sampled zeros

A structural zero (impossible pair) and a sampled zero (possible but unobserved)
both read as `O_ij = 0` but mean opposite things. Smoothing treats them
identically. If you have structural zeros, mask them out before computing PMI
rather than smoothing them into small positive surprises.

### Low-count high-PMI artifacts

PMI rewards rare co-occurrence. A cell with `O_ij = 1` against a tiny `E_ij` can
top the ranking while being pure noise. Always apply the count guard (Step 4) or
prefer NPMI, which down-weights low-probability cells.

### Heterogeneous sizes with additive residual

Using `O - E` when models differ in size by orders of magnitude lets the largest
model own the entire top of the ranking. Switch to PMI / NPMI.

### Compression discarding the signal

The compact `(x, y, z)` state is built by averaging away the residual. If the
residual *is* the deliverable (the audit), compressing first destroys it. Run the
audit on the full residual table; compress only if a separate compact state is
also needed.

---

## When This Applies vs When It Does Not

**Applies:**
- dense joint — sub-topics shared across many models / domains / sources
- you care about deviation from baseline, not absolute counts
- heterogeneous category sizes (PMI handles this; additive does not)
- goal is a coverage / specialization / gap audit

**Does not apply:**
- block-diagonal joint (nested, non-crossing) — no cross-structure to deviate
- you genuinely want absolute counts, not surprise — just read O
- the marginals themselves are the question — then you do not need the interaction at all

---

## Lessons

- **The residual is the product, not the error.** The marginals explain the
  boring part. PMI is what is left, and what is left is the entire reason to run
  this.

- **PMI = log(O / E), and E is the independence baseline.** Everything reduces to
  observed-over-expected. Expected is the rank-1 outer product of the margins.

- **Log-ratio beats additive for heterogeneous sizes.** Additive residuals are
  dominated by big categories; PMI surfaces proportional surprise regardless of
  scale. NPMI when you need a bounded comparable score.

- **Guard low counts.** PMI rewards rarity; a count threshold or NPMI stops
  single-record cells from topping the audit.

- **Smoothing conflates two kinds of zero.** Structural zeros should be masked,
  not smoothed. Only sampled zeros deserve `+eps`.

- **GRPO advantage is the additive sibling.** `reward - baseline` is `O - E` in
  spirit; PMI is the log-ratio version. Same deviation idea, different units.

- **Compression is secondary and lossy by design.** It averages away the very
  residual the audit needs. Do not lead with it.

---

## Open Questions

1. **PMI vs NPMI for this audit** — does normalized PMI change the top-ranked
   specialization cells materially, or only reorder the tail? Decide the default
   empirically on the real dense dataset.

2. **Correspondence analysis as the vector upgrade** — SVD of the standardized
   residual gives each model and each sub-topic a low-dim coordinate. Does the
   2D map cluster models by specialization in a way the per-cell table hides?

3. **Smoothing sensitivity** — how much does the ranking move as `eps` varies
   from 0.5 to 1.0? If it moves a lot, the signal is fragile and count-limited.

4. **Threshold for "surprising"** — under independence, PMI has a known sampling
   distribution; a per-cell significance cut (or a MAD-based threshold on the PMI
   distribution) separates real deviation from noise. Which threshold rule holds
   up across datasets?

5. **MI decomposition as a single audit score** — total mutual information is the
   count-weighted sum of PMI. Tracking MI over time gives one scalar for "how much
   model and sub-topic are entangled" — a drift signal for whether models are
   converging to the same coverage or diverging into specialists.

---

## Entities Involved

- `poly_form_search.py` — the compression-view reference implementation (secondary)
- `solver_setup.csv` — Excel Solver mockup of the compact (x, y, z) state (secondary)
- Concepts: pointwise mutual information, independence model, log-linear model,
  chi-square residual, mutual information, PPMI / NPMI, correspondence analysis,
  GRPO advantage, QLoRA / RVQ base+residual, MAD thresholding