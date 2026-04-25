---
name: timeout-guard
description: Use for hung or slow local LLM generations, retry policy design, timeout tuning, or documenting latency-outlier handling. Covers hard per-attempt timeout caps, success-only timing baselines, two-tier log-space MAD thresholds (warn at 2×MAD, kill at 4×MAD), and restart policy for stale runs.
---
# Timeout Guard

## Purpose
Use this skill when a local model call is hanging, a long-running pipeline is
drifting into timeout territory, or you need to reason about whether a run
should continue, retry, warn, or restart.

This skill documents the current policy used by the dark_factory harness.

## Current Policy

### 1. Hard timeout is the enforcement mechanism
- Set a hard per-attempt timeout of **300 seconds**
- Let the transport layer raise `ReadTimeout`
- Feed that timeout into the existing retry path rather than inventing a second
  kill mechanism

The timeout is what actually stops bad calls. Everything else here is
observability and diagnosis.

### 2. Only successful completions count toward the baseline
- Build latency statistics from **successful completions only**
- Do **not** include timed-out, cancelled, or transport-failed calls in the
  timing baseline

The goal is to model normal completion behavior, not contaminate the baseline
with failure modes.

### 3. Wait for a minimum baseline before flagging outliers
- Minimum successful samples before outlier detection: **5**
- Before 5 successful records, just enforce the hard timeout and collect data

Do not pretend a median or MAD is meaningful on tiny samples.

### 4. Two-tier threshold in log-space
LLM latency is usually right-tailed, so use multiplicative reasoning rather than
additive reasoning.

A single threshold forces a false choice between sensitivity and permissiveness.
Use two tiers instead:

| Tier | Formula | Action |
|---|---|---|
| **Warn** | `exp(log_median + 2 * log_mad)` | Log slow-call warning; keep running |
| **Kill** | `exp(log_median + 4 * log_mad)` | Interrupt; enter retry path |

Formula:

```text
log_samples       = ln(duration_seconds)
log_median        = median(log_samples)
log_mad           = median(|log_sample - log_median|)
warn_threshold    = exp(log_median + 2 * log_mad)
kill_threshold    = exp(log_median + 4 * log_mad)
```

Multiplier rationale: under normality, Tukey's IQR×1.5 fence sits at ≈ μ ± 2.698σ.
Since MAD ≈ 0.6745σ → σ ≈ 1.4826·MAD, that fence converts to **median ± 4·MAD** (~2.7σ).
The warn tier at 2×MAD sits at ~1.35σ — flags genuinely slow runs without killing them.
Caveat: equivalence holds under normality. Heavy-tailed distributions shift the MAD-unit
fence; calibrate empirically if the log-duration distribution is strongly non-normal.

Do **not** use mean/stddev here. Long-tail latency makes that too noisy.

### 5. Track per model, not per endpoint
- Maintain timing windows per **model name**
- Example: `qwen3.6` and `gpt-4.1` should not share the same latency baseline

Different models have different nominal speeds even when they hit the same style
of endpoint.

### 6. Use a rolling window
- Keep a bounded history, e.g. **50** successful samples per model
- Old timing behavior should age out naturally

This keeps the threshold responsive to current runtime conditions.

### 7. MAD==0 means "do not flag", not "everything is an outlier"
If the rolling window is constant enough that `MAD == 0`, skip outlier
flagging.

That case means the threshold has collapsed and would produce nonsense alerts.

## Decision Ladder

### If a call is still running
1. If elapsed time is **under warn_threshold**, let it run
2. If elapsed time crosses **warn_threshold**, log a slow-call warning and keep running
3. If elapsed time reaches **kill_threshold** (or hard cap of 300s, whichever is lower), interrupt and enter the existing retry path

### If a call completes successfully
1. Record its duration into the per-model rolling window
2. If there are fewer than **5** successful samples, stop there
3. Otherwise compute both log-space thresholds
4. If the call exceeded warn_threshold, log a slow-call warning
5. If the call exceeded kill_threshold, log a hard-outlier event (it should have been interrupted, but record it either way)

### If a pipeline run predates policy changes
Restart the run instead of trusting it to "pick up" new timeout settings.

An in-flight process keeps the constants it imported at startup.

## Interpretation Rules
- **Hard timeout (300s)** means the call is bad enough to stop and retry unconditionally
- **Kill threshold (4×MAD)** means the call is a statistical outlier; interrupt and retry
- **Warn threshold (2×MAD)** means the call is slow but within the plausible tail; keep running, log it
- A warn is not a failure — do not retry on warn alone
- A timed-out or killed call should not enter the baseline

## What to Log
For slow completed calls, log:
- model name
- elapsed seconds
- completion tokens, if available
- effective throughput (`tokens / seconds`)
- current log-space-derived nominal median
- current nominal threshold
- sample count used for the threshold

This is enough to tell whether the model is merely slow or genuinely drifting.

## When to Restart a Whole Run
Restart the whole run when:
- the process was started before a timeout-policy change
- the process is stuck in a stale retry loop using old constants
- the run log confirms it is still operating under superseded behavior

Do **not** restart just because one call logged as a slow outlier.

## Anti-Patterns
- Computing thresholds before 5 successful samples
- Mixing failed calls into the timing baseline
- Using nominal-space `median + 4*MAD` on heavily skewed latency data
- Using mean/stddev on long-tail generation latency
- Treating outlier warnings as hard failures
- Assuming a live process sees new timeout constants without restart

## Dark Factory Reference Values
These are the current values documented by this skill:

```text
hard_timeout_seconds = 300
outlier_min_samples  = 5
outlier_window       = 50
warn_multiplier      = 2   # log-space; ~1.35σ — slow but alive
kill_multiplier      = 4   # log-space; ~2.7σ — Tukey-equivalent, interrupt
tracking_scope       = per-model
```

If implementation changes, update this file to match the live policy.
