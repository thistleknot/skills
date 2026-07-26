---
name: parm-tuning-as-lp
description: >
  Frame any hyperparameter or configuration tuning problem as a linear
  or mixed-integer program. Use when the parameter space is discrete,
  the objective is measurable, and constraints can be derived from
  empirical observations or domain knowledge. Produces a solvable
  formulation with orthogonal decision variables, calibrated bounds,
  and a validation loop against the real system.
status: active
last_validated: 2026-05-24
validation_method: empirical observation study
---

# Parameter Tuning as Linear Programming

## When to Use

Use this skill when:

- The parameter space is **discrete and small** â€” a handful of options per lever
- The objective is **quantifiable** â€” RAGAS score, AUC, latency, time in band
- Constraints come from **empirical data points or domain boundaries**, not priors alone
- You want a **globally optimal** configuration, not local hill-climbing
- The problem has **independent failure modes** that map to separable constraints

Do **not** use this skill when:

- The parameter space is continuous and high-dimensional â†’ use Optuna, Bayesian opt
- Constraints are unknown with no empirical calibration data â†’ explore first
- The model is fully nonlinear with no linearization path â†’ use scipy.minimize or CMA-ES
- You are tuning neural network weights â†’ gradient methods dominate

---

## Core Principle: Mutual Exclusivity of Levers

Before formalizing, verify the parameter space is **factored into orthogonal axes**.

The failure mode: redundant parameters that move the same outcome. Adding them increases collinearity, not expressivity. The optimizer navigates cleanly only when levers are decoupled.

**Test:** for each candidate parameter, ask â€” does adjusting this move an outcome that no other parameter controls? If no, merge or eliminate.

**Target:** one degree of freedom per independent failure mode.

Well-factored examples:
- BM25 weight vs semantic weight: lexical recall and semantic recall are genuinely different failure modes â†’ one hybrid weight is sufficient
- Retrieval top-k vs reranker cutoff: recall and precision are separable â†’ two levers
- Chunk size vs chunk overlap: these interact on the same bottleneck â†’ collapse to effective coverage ratio

Poorly-factored examples:
- Learning rate + warmup + decay: all interact on convergence â†’ collapse to effective LR schedule
- Temperature + top-p + top-k: all constrain the same sampling distribution

---

## Perturbation Basis: The Irreducible Ratio

When discrete options exist, prefer **non-integer-reducible ratios** between levels.

Rationale: a ratio like 4:3 (irreducible) gives coverage across scales without overlap. Integer ratios (2:1) create redundancy â€” the upper level is just a double of the lower, adding no new coverage. This is the combinatorial analogue of log-spacing in continuous hyperparameter search.

**Protocol:**
1. List available discrete values per lever
2. Compute pairwise ratios
3. Prefer pairs where gcd(a, b) is small relative to a, b
4. The irreducible ratio is your perturbation unit â€” it applies uniformly across levers

The irreducible ratio also enables **warm-starting**: because the levels are non-overlapping in effect space, a known-good configuration at one level gives a principled starting point for adjacent levels without redundant search.

---

## Formulation Protocol

### Step 1 â€” Define the decision variables

For each controllable parameter, enumerate the discrete options:

```
x[s,k] âˆˆ {0,1}   â€” binary: is option k active at configuration slot s?
Î£_k x[s,k] â‰¤ 1   â€” at most one option per slot (mutual exclusivity)
```

If the problem has a temporal or ordering dimension (e.g., pipeline stages, scheduled events):

```
x[s] âˆˆ {0,1}     â€” is slot s used?
d[s] âˆˆ D         â€” which option, given slot s is used
```

### Step 2 â€” Precompute the response function

Map decision variables to state variables. For systems where output is a sum of individual contributions (RAG scores, additive effects, pipeline outputs):

```
Y[t] = Î£_s x[s] * f(t, d[s], s)
```

Precompute `f(t, d, s)` for all (evaluation point t, option d, slot s) combinations into a lookup matrix. This linearizes the response even when f is nonlinear â€” as long as contributions are additive.

### Step 3 â€” Derive empirical constraints

Each constraint should be grounded in an **observed data point**, not a prior guess.

**Observation study protocol:**
1. Run the system at a known configuration
2. Label states at specific operating points (acceptable, failure, optimal)
3. Read model coordinates at those labeled points
4. Convert observations to inequality constraints

| Observation | Operating point | Model value | Constraint |
|---|---|---|---|
| Minimum acceptable quality | Known config A | metric = 0.72 | Y[t] â‰¥ 0.72 |
| Failure onset | Known config B | metric = 0.81 | Y[t] â‰¤ 0.80 |
| Secondary requirement | Config A | latency = 340ms | L[t] â‰¤ 350ms |
| Rate-of-change trigger | A â†’ B transition | Î”Y/Î”step = 0.04 | Î”Y/Î”step â‰¤ 0.04 |

**Rate constraints** are critical when the system has **adaptation lag** â€” the failure mode is triggered by velocity of change, not absolute level. This is common in systems with feedback loops, caches, or warm-up behavior.

### Step 4 â€” Linearize nonlinearities

Common nonlinearities and linearizations:

**Dampening/interaction:** `Y_eff = Y_raw / (1 + k * C)`
â†’ Fix C at expected average, solve, recompute C from solution, iterate. Converges in 2â€“3 passes.

**Bilinear product:** `a * b` where both vary
â†’ McCormick envelope relaxation.

**Max/min objectives:** `maximize min_t Y[t]`
â†’ Auxiliary variable z: `z â‰¤ Y[t] âˆ€t`, maximize z.

**Threshold indicator:** `z[t] = 1 iff Y[t] âˆˆ [lo, hi]`
â†’ Big-M: `Y[t] â‰¥ lo - M*(1-z[t])`, `Y[t] â‰¤ hi + M*(1-z[t])`

### Step 5 â€” State the objective

**Maximize time/configurations in band:**
```
maximize Î£_t z[t]
```

**Minimize constraint violation:**
```
minimize Î£_t slack_lo[t] + slack_hi[t]
where Y[t] + slack_lo[t] â‰¥ floor, Y[t] - slack_hi[t] â‰¤ ceil
```

**Multi-objective (weighted):**
```
maximize Î± * quality_score + Î² * coverage - Î³ * compute_cost
```
Normalize objectives before weighting.

### Step 6 â€” Solve and validate

**Solver selection:**
- Continuous variables only: `scipy.optimize.linprog`
- Binary/integer variables: PuLP + CBC, OR-Tools, Gurobi
- Nonlinear discrete: grid search over discrete space evaluated on real system

**Critical:** always validate the LP solution against the **real system**, not the linearized approximation. The LP solution is a candidate; the validation is ground truth.

**Iterative refinement:**
1. Solve LP with linearized model
2. Evaluate solution on real system
3. Update linearization parameters from real system output
4. Re-solve
5. Repeat until stable (typically 2â€“3 iterations)

---

## Anti-Correlations: When Two Constraints Fight

Some constraint pairs are **anti-correlated** through the model â€” satisfying one makes the other harder. Identify before solving.

Example in RAG: increasing semantic weight (to satisfy recall constraint) reduces lexical precision (potentially violating precision floor). The constraints fight through the shared scoring function.

**Handling anti-correlations:**
1. Increase the lever that drives both â€” if a third parameter can lift the floor without affecting the ceiling, prefer it
2. Accept a Pareto frontier and present the tradeoff explicitly rather than claiming a single optimum
3. Introduce a new lever that is orthogonal to the anti-correlated pair

The anti-correlation is a signal that the parameter space is **not fully factored**. The correct response is to find the missing orthogonal dimension, not to solve harder.

---

## When LP Fails: Grid Search Fallback

If nonlinearity is too severe for linearization and the discrete space is small:

```python
best_score = 0
best_config = None

for config in product(option_set, repeat=n_slots):
    score = evaluate_real_system(config, constraints)
    if score > best_score:
        best_score = score
        best_config = config
```

Tractable when: n_slots â‰¤ 8, options per slot â‰¤ 12.

For larger spaces: beam search, greedy forward selection, or genetic algorithm over the discrete space.

---

## Warm Start from Known-Good Baselines

When an empirically-derived baseline exists, use it to reduce search:

1. Fix slots where the baseline is verified to satisfy constraints
2. Optimize only over the remaining free slots
3. Use the baseline score as a lower bound â€” reject any candidate that scores below it

The warm start is the critical advantage of observation-study-derived constraints over prior-based constraints: you know where part of the solution already lives.

This is directly analogous to warm-starting gradient descent from a pretrained checkpoint â€” the structure of the known-good solution encodes information the optimizer would otherwise rediscover expensively.

---

## Applicability Envelope

**Works well when:**
- Discrete options, additive or linearizable response model
- At least 2 empirical calibration points per constraint
- Independent failure modes that map cleanly to orthogonal constraints
- Interaction/dampening terms are bounded and well-behaved

**Degrades when:**
- Anti-correlated constraints dominate the feasible region
- The observation study has only one labeled state (under-constrained)
- Rate-of-change threshold is unknown (pending data point)
- System exhibits strong hysteresis â€” entry and exit thresholds differ significantly

**Environment assumptions:**
- Discrete option set is fixed and finite
- Response function is additive or linearizable
- Empirical observation data can be read off system state at labeled operating points
- Solver available: PuLP, scipy, OR-Tools

---

## Output Artifacts

1. **Formal problem statement** â€” decision variables, constraints, objective, solver
2. **Precomputed response matrix** â€” contributions per option per evaluation point
3. **Validated configuration** â€” LP solution verified against real system
4. **Residual gap report** â€” operating points outside optimal band with root cause
5. **Open constraints** â€” pending observations needed to tighten the formulation
6. **Anti-correlation map** â€” constraint pairs that fight, with proposed resolution

<!-- parm-tuning-as-lp:see-also:start -->
## See Also
[[agentic-hyperparm]]  [[optuna-nested-cv]]  [[hyper-parm_tuning]]
<!-- parm-tuning-as-lp:see-also:end -->