---
name: agentic-hyperparm-macd
description: >
  Frame any continuous hyperparameter or system-tuning problem as an
  agentic equilibrium control loop. Use when the objective is to
  MAINTAIN a metric within an empirically-derived band — not optimize
  to a peak — and when the parameter space has discrete levers.
  Uses MACD momentum signals to detect drift before threshold breach,
  LP to select the corrective action, and an observation study to
  calibrate the band boundaries. Produces a closed-loop controller
  with explainable actions and a validated operating range.
status: active
last_validated: 2026-05-24
validation_method: empirical observation study (n=1, CNS pharmacokinetic model)
---

# Agentic Hyperparameter Equilibrium via MACD

## When to Use

Use this skill when:

- The goal is **band maintenance**, not peak optimization — you want the
  metric to stay between a floor and a ceiling, not climb indefinitely
- The metric has **momentum** — it drifts gradually, not instantaneously,
  which means you can anticipate transitions before they happen
- The parameter space is **discrete and small** — a handful of levers
  with enumerable options (same as `parm-tuning-as-lp`)
- You have **at least two labeled observations**: a floor state and a
  ceiling state, empirically measured from the real system
- The failure modes are **separable** — different parameters control
  different failure modes (see `parm-tuning-as-lp` for factoring protocol)

Do **not** use this skill when:

- The metric is noisy and non-stationary — MACD will generate false signals
- The system has no inertia — if metric jumps discontinuously, momentum
  is not informative
- You are optimizing, not maintaining — use `parm-tuning-as-lp` directly
- Constraints are unknown — run the observation study first

---

## Core Principle: The Signal Is Momentum, Not Level

Standard hyperparameter tuning watches the metric level and acts when it
crosses a threshold. This is reactive — by the time you know you've
breached the ceiling, you're already in the failure state.

MACD-based control watches **momentum** — the rate of change of the metric
— and acts when momentum signals an impending transition. This is
**predictive**: you intervene before the breach, not after.

The MACD signal on a metric M is:

```
fast_ema[t] = EMA(M, α_fast)
slow_ema[t] = EMA(M, α_slow)
MACD[t]     = fast_ema[t] - slow_ema[t]
signal[t]   = EMA(MACD, α_signal)
histogram[t]= MACD[t] - signal[t]
```

**Interpretation:**
- `MACD > 0` and rising: metric accelerating upward → approaching ceiling
- `MACD < 0` and falling: metric decelerating → approaching floor
- `histogram crosses zero upward`: momentum inflection → trigger ceiling-side check
- `histogram crosses zero downward`: momentum inflection → trigger floor-side check

The histogram crossover is your **intervention signal** — not the level.

---

## The Two-Layer Architecture

```
┌─────────────────────────────────────────────────────┐
│                   SIGNAL LAYER                      │
│  MACD on metric → detect momentum → fire trigger    │
└─────────────────────┬───────────────────────────────┘
                      │ trigger: which direction, how urgent
┌─────────────────────▼───────────────────────────────┐
│                   ACTION LAYER                      │
│  LP over discrete parameter space → select action   │
│  Constraint: stay in [floor, ceiling] band          │
│  Objective: maximize future time in band            │
└─────────────────────┬───────────────────────────────┘
                      │ action: parameter delta
┌─────────────────────▼───────────────────────────────┐
│                   SYSTEM                            │
│  Apply action → observe metric[t+1] → feed back     │
└─────────────────────────────────────────────────────┘
```

The signal layer runs continuously. The action layer fires only on
triggers. This prevents over-correction — you don't re-solve the LP
every step, only when momentum signals a transition.

---

## Observation Study Protocol

Before building the controller, run a structured observation study to
calibrate the band boundaries. This is the same protocol as
`parm-tuning-as-lp` with one addition: label **transition states**,
not just operating states.

| Label | When to record | What to record |
|---|---|---|
| Floor | Minimum acceptable state | Metric value, parameter config, MACD value |
| Ceiling breach | First sign of failure | Metric value, parameter config, MACD value |
| Ceiling exit | Failure clears | Metric value, time elapsed, MACD value |
| Post-ceiling recovery | System restabilized | Metric value, whether floor was re-entered |

**The transition observations are the most valuable.** They give you:

1. The **rate of change** at breach (`ΔM/Δt` at ceiling breach = your rate constraint)
2. The **hysteresis width** (ceiling breach ≠ ceiling exit → system has memory)
3. The **MACD value at trigger** (calibrates the intervention threshold)

If hysteresis is present — if the ceiling exit level differs from the
ceiling breach level — the controller must model it explicitly. A single
threshold is insufficient. Use an asymmetric band: ceiling_entry <
ceiling_exit, floor_entry > floor_exit.

---

## MACD Parameter Calibration

The MACD windows are calibrated to the system's time constants:

```
α_fast   = 2 / (fast_window + 1)
α_slow   = 2 / (slow_window + 1)
α_signal = 2 / (signal_window + 1)
```

**Calibration heuristics:**
- `fast_window` ≈ half the typical transition time (breach onset to peak)
- `slow_window` ≈ 2-3× the fast window
- `signal_window` ≈ fast_window

For RAGAS metrics updated per eval batch:
- If batches run every 100 steps, transition typically takes 3-5 batches
- `fast_window = 2 batches`, `slow_window = 5 batches`, `signal_window = 2 batches`

For continuous real-time metrics:
- Calibrate from the observation study: measure how long the metric
  takes to move from floor to ceiling after a parameter change
- Set `fast_window` to ~30% of that transition time

---

## Agent Loop

```python
def agent_loop(system, params, constraints, macd_cfg, lp_cfg):
    metric_history = []
    param_config = params.warm_start  # empirically validated baseline

    while system.running:
        # Observe
        metric = system.evaluate(param_config)
        metric_history.append(metric)

        # Signal layer: compute MACD
        macd, signal, hist = compute_macd(metric_history, **macd_cfg)

        # Check triggers
        if crosses_zero_upward(hist):
            # Metric accelerating toward ceiling
            direction = 'reduce'
            urgency = abs(hist[-1])
        elif crosses_zero_downward(hist):
            # Metric decelerating toward floor
            direction = 'increase'
            urgency = abs(hist[-1])
        else:
            # No trigger — hold current config
            continue

        # Check if level is also near boundary (confirm trigger)
        if direction == 'reduce' and metric < constraints.ceiling - constraints.margin:
            continue  # momentum signal but level safe — wait
        if direction == 'increase' and metric > constraints.floor + constraints.margin:
            continue

        # Action layer: LP selects next config
        candidate = lp.solve(
            current_config=param_config,
            direction=direction,
            constraints=constraints,
            urgency=urgency
        )

        # Validate candidate on real system before committing
        candidate_metric = system.evaluate(candidate)
        if constraints.floor <= candidate_metric <= constraints.ceiling:
            param_config = candidate

        # Log
        log(metric, macd, signal, hist, param_config, direction)
```

**Key design decisions:**

1. **Trigger confirmation** — only act when both momentum AND level agree.
   Momentum alone can fire early (before the level is actually at risk).
   Level alone fires too late. Both together gives the right timing.

2. **LP on each trigger, not each step** — re-solving the LP is expensive
   and unnecessary when momentum is flat. Fire only on histogram crossovers.

3. **Validate before committing** — always evaluate the LP candidate on
   the real system before making it the active config. The LP is a
   proposal, not a guarantee.

4. **Urgency-weighted LP** — scale the LP's correction magnitude by
   `abs(histogram)`. High urgency = allow larger parameter jumps.
   Low urgency = prefer minimal perturbation (Occam's razor on actions).

---

## Connecting to RAGAS / Cross-Entropy Loss

For RAG pipelines evaluated via RAGAS:

- **Metric:** macro-mean of (context precision, context recall, answer
  relevancy, faithfulness)
- **Floor:** minimum acceptable RAGAS score from empirical evaluation
  (run baseline, label the acceptable threshold)
- **Ceiling:** rarely needed for quality metrics, but can represent
  compute budget limit (if RAGAS is too high, you're over-retrieving)
- **Levers:** BM25 weight, semantic weight, top-k, chunk size, reranker
  cutoff — factored into orthogonal axes per `parm-tuning-as-lp`
- **MACD signal:** computed on rolling RAGAS score across eval batches

For cross-entropy loss:
- **Floor:** target loss (below this = overfitting signal)
- **Ceiling:** acceptable loss (above this = underfitting)
- **Levers:** learning rate schedule, regularization weight, dropout
- **MACD signal:** on validation loss curve — crossovers signal
  transition between underfitting and overfitting regimes

---

## The Irreducible Ratio as Perturbation Unit

Inherit from `parm-tuning-as-lp`: prefer discrete lever values whose
ratio is irreducible. The irreducible ratio gives non-overlapping
coverage across scales and enables **warm-starting from any operating
point** without redundant search.

For RAGAS tuning, if BM25 weights are {0.3, 0.4, 0.5, 0.6}:
- 0.3:0.4 = 3:4 (irreducible) ✓
- 0.4:0.6 = 2:3 (irreducible) ✓
- 0.3:0.6 = 1:2 (reducible — 0.6 is just double 0.3, no new coverage) ✗

---

## Anti-Correlations Under MACD Control

Anti-correlated constraints (satisfying one makes the other harder)
create oscillation in the MACD controller if not handled:

- LP selects action to fix ceiling breach
- Action over-corrects, metric drops below floor
- LP selects action to fix floor breach
- System oscillates between both failure states

**Solutions:**

1. **Dead band**: add a margin inside the floor and ceiling (inner band)
   where no action is taken. Only trigger outside the inner band.

2. **Damped correction**: limit the LP correction to a fraction of the
   required move per trigger. Apply multiple small corrections rather
   than one full correction.

3. **Orthogonal factoring**: if oscillation persists, the levers are not
   fully orthogonal. Find the missing dimension that resolves the
   anti-correlation.

---

## Output Artifacts

1. **Calibrated band** — floor, ceiling, and margin from observation study
2. **MACD parameters** — fast/slow/signal windows calibrated to system time constants
3. **LP action space** — factored discrete levers with irreducible ratio basis
4. **Agent loop implementation** — signal layer, action layer, validation
5. **Hysteresis map** — entry vs exit thresholds if asymmetric
6. **Oscillation guard** — dead band and damping parameters

<!-- agentic-hyperparm-macd:see-also:start -->
## See Also
[[parm-tuning-as-lp]]  [[optuna-nested-cv]]  [[hyper-parm_tuning]]  [[agentic-hyperparm]]
<!-- agentic-hyperparm-macd:see-also:end -->
