---
name: signal-demodulation-rl-band
description: >
  Demodulate a noisy, non-stationary signal into a normalized space,
  then apply RL band maintenance to maximize time within an empirically
  derived target window. Use when the raw signal has heavy tails,
  skewness, or regime-dependent variance that makes threshold-based
  control unreliable. Produces a stationary MACD-readable signal,
  an empirical band calibrated from an observation window, and an RL
  reward function that targets band maintenance rather than peak
  optimization. Generalizes across system dynamics, portfolio returns,
  system metrics, and any domain where equilibrium maintenance
  outperforms point optimization.
status: active
last_validated: 2026-05-25
validation_method: >
  Dual empirical validation: system dynamic observation study (n=1,
  CNS n=1 observation study, intraday observation study) and quantitative finance
  pipeline (65-week rolling calibration, 13-week tail forecast).
---

# Signal Demodulation + RL Band Maintenance

## When to Use

Use this skill when:

- The raw signal is **non-stationary** — mean, variance, or distribution
  shape change across regimes or time
- The objective is **band maintenance**, not peak optimization — you want
  the signal to stay between a floor and a ceiling
- The signal has **momentum** — it drifts gradually, enabling predictive
  intervention via MACD before threshold breach
- **Empirical calibration data exists** — you have labeled observations
  of floor state, ceiling breach, and recovery
- The control levers are **discrete or bounded** — position sizes, action
  amounts, configuration options

Do **not** use this skill when:

- The signal is already stationary and Gaussian — skip demodulation,
  go directly to `agentic-hyperparm-macd`
- No empirical calibration is possible — explore first, then calibrate
- The system is fully deterministic — use `parm-tuning-as-lp` directly
- Optimization target is a single peak — use Optuna, Bayesian opt,
  or gradient methods

---

## Core Principle: Demodulate First, Control Second

Standard control systems fail on non-stationary signals because threshold
crossings are not comparable across regimes. A price MACD crossover in
a low-volatility regime means something different than the same crossover
in a high-volatility regime. A cognitive load signal during acute
inflammation differs from the same signal at baseline.

The solution is to **demodulate the raw signal into a normalized space**
where the dynamics are stationary. MACD crossovers on the normalized
signal are regime-invariant. Thresholds calibrated in normalized space
hold across conditions. The RL agent learns a single policy that
generalizes across regimes because the input space is stable.

```
Raw signal
    -> Demodulation pipeline (remove distribution artifacts)
    -> Normalized signal (stationary, Gaussian or near-Gaussian)
    -> MACD on normalized signal (regime-invariant momentum)
    -> RL band maintenance (maximize time in target window)
    -> Action on original space (action, position, config)
```

---

## Stage 1: Demodulation Pipeline

The demodulation pipeline strips distributional artifacts from the raw
signal. Apply transforms in this order, stopping when the signal passes
a stationarity check.

### Step 1a — Log transform (if signal is multiplicative)

Use when: the signal is a ratio, rate, or multiplicative process.
Financial returns, system dynamic concentrations, and throughput
metrics are all multiplicative.

```python
x_log = np.log(x / x.shift(1))        # log returns
# or
x_log = np.log(x)                      # log level if already ratio-like
```

Do not use when: the signal can be negative (e.g., net P&L, signed
residuals). Use Yeo-Johnson directly in that case.

### Step 1b — Robust centering and scaling (median / MAD)

Use after log transform. Removes location and scale without sensitivity
to outliers. Critical when the signal has fat tails (financial returns,
system dynamic peaks).

```python
from scipy.stats import median_abs_deviation

median = np.median(x_log)
mad    = median_abs_deviation(x_log)
x_robust = (x_log - median) / (mad * 1.4826)  # 1.4826 converts MAD to sigma-equivalent
```

The 1.4826 constant makes MAD comparable to standard deviation under
normality. Under heavy tails it gives a more conservative (smaller)
scale estimate, which is the correct direction for risk management.

Do not use mean/std here. Under fat tails, mean and std are dominated
by outliers and give unstable normalization across regimes.

### Step 1c — Yeo-Johnson transform (Gaussianize)

Use after median/MAD normalization. Finds the optimal power transform
to make the distribution as Gaussian as possible. Handles negative
values (unlike Box-Cox).

```python
from sklearn.preprocessing import PowerTransformer

pt = PowerTransformer(method='yeo-johnson', standardize=True)
x_normal = pt.fit_transform(x_robust.reshape(-1, 1)).flatten()
```

Save the fitted transformer. At inference time, apply the same fitted
transform — do not refit on the inference window.

### Step 1d — Stationarity check

After demodulation, verify the signal is stationary before proceeding.

```python
from statsmodels.tsa.stattools import adfuller

result = adfuller(x_normal, autolag='AIC')
p_value = result[1]
assert p_value < 0.05, f"Signal not stationary after demodulation (p={p_value:.3f})"
```

If the ADF test fails: the signal has a unit root. Add differencing
(`np.diff`) before the median/MAD step, or increase the log transform
horizon.

---

## Stage 2: Empirical Band Calibration

The target band [floor, ceiling] is **always empirically derived**, not
assumed from priors. Run a structured observation study on the normalized
signal to label operating states.

### Observation study protocol

Run the system at known configurations and label states in normalized
signal space:

| Label | When to record | What to record |
|---|---|---|
| Floor | Minimum acceptable state | x_normal, MACD value, timestamp |
| Floor breach | State degradation begins | x_normal, rate of change |
| Ceiling | Maximum acceptable state | x_normal, MACD value, timestamp |
| Ceiling breach | Failure / overload onset | x_normal, rate of change |
| Ceiling exit | Recovery begins | x_normal, time elapsed |

**Minimum viable calibration:** floor + ceiling breach. Two labeled
points define the band. Additional transition points tighten it.

### Band derivation

```python
# From labeled observations
floor_obs   = x_normal[floor_timestamps]
ceiling_obs = x_normal[ceiling_breach_timestamps]

band_floor   = np.median(floor_obs)
band_ceiling = np.median(ceiling_obs)

# Rate constraint: maximum acceptable rate of change
rate_at_breach = np.diff(x_normal[approaching_ceiling]) / dt
rate_limit     = np.percentile(rate_at_breach, 25)  # conservative: 25th pct
```

### Hysteresis check

If the ceiling exit level differs from the ceiling breach level, the
system has memory (hysteresis). Use asymmetric band boundaries:

```python
ceiling_entry = band_ceiling           # breach threshold (stricter)
ceiling_exit  = ceiling_entry + margin # recovery threshold (looser)
```

Attempting to use a single threshold on a hysteretic system produces
oscillation. Always check for asymmetry before building the controller.

---

## Stage 3: MACD on Normalized Signal

Compute MACD on the normalized (demodulated) signal. Because the signal
is now stationary, MACD parameters calibrated from one period generalize
to others.

```python
def compute_macd(signal, fast_window, slow_window, signal_window):
    fast_ema   = signal.ewm(span=fast_window,   adjust=False).mean()
    slow_ema   = signal.ewm(span=slow_window,   adjust=False).mean()
    macd_line  = fast_ema - slow_ema
    signal_line= macd_line.ewm(span=signal_window, adjust=False).mean()
    histogram  = macd_line - signal_line
    return macd_line, signal_line, histogram
```

### Window calibration

Calibrate from the observation study transition times:

```python
# transition_time = observed time from floor to ceiling in the signal
fast_window   = int(transition_time * 0.3)   # 30% of transition time
slow_window   = int(transition_time * 0.9)   # 90% of transition time
signal_window = fast_window
```

### Trigger conditions

Intervention is triggered when histogram crosses zero AND level confirms:

```python
def should_intervene(histogram, x_normal, band_floor, band_ceiling, margin):
    hist_cross_up   = histogram[-1] > 0 and histogram[-2] <= 0
    hist_cross_down = histogram[-1] < 0 and histogram[-2] >= 0

    near_ceiling = x_normal[-1] > band_ceiling - margin
    near_floor   = x_normal[-1] < band_floor   + margin

    ceiling_signal = hist_cross_up   and near_ceiling
    floor_signal   = hist_cross_down and near_floor

    return ceiling_signal, floor_signal
```

Momentum alone fires early. Level alone fires late. Both together gives
the correct intervention timing.

---

## Stage 4: Translating MACD to RL

MACD is a reactive rule. RL is a learned policy. The translation between
them is the core architectural decision in this skill.

### Why MACD alone is insufficient

MACD fires when momentum crosses zero — it tells you a transition is
happening. It does not tell you:

- How large an action to take
- Whether the transition is recoverable from the current lever position
- How to trade off urgency against overshoot risk
- What to do when multiple signals conflict

These are exactly what RL solves. MACD becomes the **feature** that the
RL agent reads, not the policy itself.

### The translation

```
MACD role in rule-based system     MACD role in RL system
────────────────────────────────   ────────────────────────────────
Trigger: fire action on crossover  Feature: histogram value in state
Action: fixed response             Action: learned, context-dependent
Urgency: ignored                   Urgency: encoded in histogram magnitude
Hysteresis: not handled            Hysteresis: learned from experience
Multi-signal conflicts: ad hoc     Multi-signal: resolved by Q-function
```

### MACD as RL state features

The full MACD decomposition becomes the state vector:

```python
state = {
    # Level: where are we in the band?
    'band_position': (x_normal - band_floor) / (band_ceiling - band_floor),

    # Momentum: which direction is the signal moving?
    'macd_line':     macd[-1],          # fast - slow EMA: direction
    'histogram':     histogram[-1],     # macd - signal: acceleration
    'histogram_delta': histogram[-1] - histogram[-2],  # jerk: is momentum increasing?

    # Regime: what context are we in?
    'regime_label':  classifier.predict(features),

    # History: recent signal trajectory
    'x_normal_history': x_normal[-lookback:],
}
```

The histogram gives urgency: large positive histogram = fast approach to
ceiling = larger corrective action needed. Small histogram = slow drift =
smaller correction sufficient. The RL agent learns this mapping from
experience; MACD just provides the raw momentum information.

### Reward shaped by MACD structure

The MACD structure informs reward shaping. Penalize not just being out
of band but approaching the boundary with high momentum:

```python
def reward(x_normal, histogram, band_floor, band_ceiling):
    band_pos   = (x_normal - band_floor) / (band_ceiling - band_floor)
    in_band    = 0.0 <= band_pos <= 1.0

    # Base reward: in-band fraction
    if not in_band:
        violation = max(band_floor - x_normal, x_normal - band_ceiling)
        return -(violation ** 2)

    # Momentum penalty: being in band but moving fast toward boundary
    margin_to_boundary = min(band_pos, 1.0 - band_pos)
    momentum_risk = max(0, abs(histogram[-1]) - threshold) * (1.0 - margin_to_boundary)

    # Centering bonus: prefer center of band
    center_bonus = 1.0 - 2.0 * abs(band_pos - 0.5)

    return 1.0 + 0.2 * center_bonus - 0.1 * momentum_risk
```

The momentum penalty teaches the agent to take pre-emptive action when
the MACD histogram is large and the signal is near a boundary — exactly
what human experts do when reading MACD charts.

### From reactive MACD to predictive RL

The MACD crossover fires when the transition has already started. The RL
agent, trained on many crossover episodes, learns to act **before** the
crossover by recognizing the histogram shape that precedes it.

This is the core advantage of RL over MACD rules: the agent internalizes
the leading indicator structure of the MACD and acts on it predictively
rather than reactively.

```
MACD rule:   wait for histogram to cross zero, then act
RL policy:   recognize histogram shape at t-2 that precedes crossover,
             act at t-2 instead of t=0
```

The training episodes provide thousands of examples of what the histogram
looks like 2-3 steps before a breach. The Q-function encodes this
pattern. The policy acts earlier, with less overshoot, and without the
oscillation that reactive MACD rules produce near the boundary.

### State space

```python
state = {
    'x_normal':     x_normal[-lookback:],   # normalized signal history
    'macd':         macd_line[-lookback:],   # momentum
    'histogram':    histogram[-lookback:],   # momentum rate of change
    'regime':       regime_label,            # XGBoost / classifier output
    'band_position': (x_normal[-1] - band_floor) / (band_ceiling - band_floor),
}
```

`band_position` is the key state variable: 0.0 = at floor, 1.0 = at
ceiling, 0.5 = center. The RL agent learns to keep `band_position`
in [0.2, 0.8] (inner band with margin).

### Action space

Discrete or continuous depending on the domain:

**Discrete (system dynamics, configuration):**
```python
actions = {
    0: 'hold',
    1: 'small_increase',   # e.g., small discrete action
    2: 'large_increase',   # e.g., large discrete action
    3: 'small_decrease',   # e.g., reduce secondary signal
    4: 'large_decrease',
}
```

**Continuous (portfolio):**
```python
action = delta_weight  # position adjustment in [-max_delta, +max_delta]
```

### Reward function

```python
def reward(x_normal, band_floor, band_ceiling, rate, rate_limit):
    in_band      = band_floor <= x_normal <= band_ceiling
    rate_ok      = abs(rate) <= rate_limit
    band_pos     = (x_normal - band_floor) / (band_ceiling - band_floor)
    center_bonus = 1.0 - 2.0 * abs(band_pos - 0.5)   # peak at center

    if not in_band:
        violation  = max(band_floor - x_normal, x_normal - band_ceiling, 0)
        return -violation ** 2                          # quadratic penalty

    if not rate_ok:
        return 0.5 * center_bonus                       # in band but moving fast

    return 1.0 + 0.2 * center_bonus                     # full reward + centering bonus
```

The centering bonus discourages riding the boundaries — prefer the
center of the band for resilience against disturbance.

### Training protocol

```python
# Rolling window training
for window_start in range(0, len(data) - calibration_window - forecast_window, step):
    cal_data  = data[window_start : window_start + calibration_window]
    test_data = data[window_start + calibration_window :
                     window_start + calibration_window + forecast_window]

    # 1. Demodulate on calibration window
    x_normal_cal, transformer = demodulate(cal_data)

    # 2. Calibrate band from observation study on cal window
    band_floor, band_ceiling = calibrate_band(x_normal_cal, labeled_states)

    # 3. Compute MACD parameters from transition times in cal window
    macd_params = calibrate_macd(x_normal_cal, transition_times)

    # 4. Train RL agent on cal window
    agent = train_rl(x_normal_cal, band_floor, band_ceiling, macd_params)

    # 5. Evaluate on test window (apply same transformer, do not refit)
    x_normal_test = transformer.transform(demodulate_raw(test_data))
    score = evaluate_in_band(agent, x_normal_test, band_floor, band_ceiling)
```

**Critical:** apply the calibration-window transformer to the test window.
Never refit the transformer on the test window — that is data leakage.

---

## Stage 5: Action Mapping Back to Original Space

The RL agent operates in normalized signal space. Actions must be mapped
back to the original domain.

### Inverse demodulation for target setting

```python
def target_to_original(x_normal_target, transformer, median, mad):
    # Inverse Yeo-Johnson
    x_robust_target = transformer.inverse_transform([[x_normal_target]])[0][0]
    # Inverse median/MAD
    x_log_target    = x_robust_target * (mad * 1.4826) + median
    # Inverse log
    x_target        = np.exp(x_log_target)
    return x_target
```

### Domain-specific action translation

**System dynamics:**
```python
# Normalized ER target -> required effective THC level
eff_thc_target = target_to_original(x_normal_target, ...)
# Required action to reach target given current level and PK model
action = solve_pk_inverse(eff_thc_target, current_level, half_life)
action = snap_to_discrete(action, [6.25, 8.33])  # snap to available options
```

**Portfolio:**
```python
# Normalized ER target -> required portfolio weight adjustment
er_target = target_to_original(x_normal_target, ...)
delta_w   = markowitz_solve(er_target, cov_matrix, constraints)
delta_w   = np.clip(delta_w, -max_trade, max_trade)  # risk limit
```

---

## Connecting Windows: Calibration to Forecast

The calibration window is your observation study. The forecast window is
your optimization target. The ratio between them determines how much
the policy can generalize.

```
|<-------- calibration_window ------->|<-- forecast_window -->|
|  observation study + band derivation |  RL policy evaluation |
|  transformer fit + MACD calibration  |  apply frozen params  |
```

**Window sizing heuristics:**
- `calibration_window` >= 4x `forecast_window` for stable band estimation
- `forecast_window` aligned to natural system cycle: quarter (13w),
  circadian (24h), system half-life multiple
- Rolling step = `forecast_window / 2` for 50% overlap between windows

**For the 65w/13w finance case:**
- 52w calibration + 13w forecast = 4:1 ratio (minimum viable)
- Rolling step = 13w (non-overlapping quarters)
- Transformer refit every 52w; band and MACD refit every quarter

---

## Anti-Patterns

**Fitting transformer on full dataset including test window:**
Data leakage. The normalization will encode future information into the
training signal. Always fit on calibration window only.

**Using mean/std instead of median/MAD:**
Under fat tails (financial returns, agent raw signal levels),
mean/std are dominated by outliers and give unstable normalization.
The signal appears stationary when it isn't. Use median/MAD.

**Optimizing to a point instead of a band:**
Maximizing expected return at a point is fragile — a single regime
change collapses it. Band maintenance is robust because you have a
floor that enforces minimum quality and a ceiling that prevents
overexposure. The band is the resilience mechanism.

**Single threshold on a hysteretic system:**
If the system takes longer to recover than to breach, a single threshold
produces oscillation: fix ceiling breach -> overcorrect -> hit floor ->
fix floor breach -> overshoot -> repeat. Always measure hysteresis
from the observation study.

**Reoptimizing on every step:**
Expensive and unnecessary. The MACD histogram crossover is the trigger.
Between triggers, hold the current action. This is the two-layer
architecture: signal layer runs continuously, action layer fires on
events only.

---

## Domain Mapping Table

| Concept | System dynamics | Finance | System Metrics |
|---|---|---|---|
| Raw signal | raw signal level (mg) | Log price return | primary metric |
| Demodulation | interaction dampening model | Log -> median/MAD -> YJ | z-score + Box-Cox |
| Normalized signal | normalized signal level | Normalized ER | normalized primary metric |
| Band floor | 7.58 normalized units | Target ER floor | SLA minimum |
| Band ceiling | 9.0 normalized units | Target ER ceiling | SLA maximum |
| Momentum signal | secondary signal MACD | Return MACD | Metric EWM |
| Control lever | agent amount/timing | Position weight | Config parameter |
| Lever options | discrete option A / option B | Continuous weight | Discrete config |
| Calibration window | Observation study | calibration window history | Baseline period |
| Forecast window | operational target window | forecast quarter window | Deployment window |
| Rate constraint | 2.56 units/hr | Max drawdown rate | Max degradation rate |
| Dampening | secondary signal -> primary signal | Volatility regime | buffering mechanism |

---

## Output Artifacts

1. **Fitted demodulation pipeline** - transformer, median, MAD (frozen for inference)
2. **Empirical band** - floor, ceiling, margin, hysteresis width
3. **MACD parameters** - fast/slow/signal windows calibrated to system
4. **Rate constraint** - maximum acceptable signal velocity
5. **RL reward function** - band maintenance objective with centering bonus
6. **Action mapping** - from normalized space back to original domain
7. **Rolling window evaluation** - in-band fraction per window (benchmark: >85%)
8. **Observation study log** - labeled states with timestamps and model coordinates

<!-- signal-demodulation-rl-band:see-also:start -->
## See Also
[[parm-tuning-as-lp]]  [[agentic-hyperparm-macd]]  [[optuna-nested-cv]]
[[hyper-parm_tuning]]  [[multigran-sparse-retrieval]]
<!-- signal-demodulation-rl-band:see-also:end -->
