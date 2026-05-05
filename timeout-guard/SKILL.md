---
name: timeout-guard
status: active
last_validated: 2026-04-28
description: Use for hung or slow local LLM generations, retry policy design, timeout tuning, or documenting latency-outlier handling. Covers hard per-attempt timeout caps, completion-inclusive baselines (kills/cancels excluded), log-space MAD thresholds with silence-based kill, and restart policy for stale runs.
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

### 2. All completions count toward the baseline; only kills/cancellations are excluded
- Build latency statistics from **every call that returned a completion**, regardless of how slow it was
- Do **not** include timed-out, silence-killed, cancelled, or transport-failed calls in the
  timing baseline

The rolling window is the adaptive mechanism. Excluding slow completions anchors the baseline
to stale "normal" behavior — causing increasingly aggressive kills as model load grows.
A slow completion is evidence of what the model actually does; a killed call has no valid
completion time and must be excluded.

### 3. Wait for a minimum baseline before flagging outliers
- Minimum successful samples before outlier detection: **5**
- Before 5 successful records, just enforce the hard timeout and collect data

Do not pretend a median or MAD is meaningful on tiny samples.

### 4. Two-tier threshold in log-space
LLM latency is usually right-tailed, so use multiplicative reasoning rather than
additive reasoning.

A single wall-clock threshold conflates two distinct failure modes: a model that is
**slow but producing tokens** vs a model that has **stalled**. Use two tiers:

| Tier | Trigger | Action |
|---|---|---|
| **Watch** | `elapsed > exp(log_median + 2 * log_mad)` | Switch from wall-clock monitoring to silence monitoring |
| **Kill** | silence `> SILENCE_TIMEOUT_SECONDS` **or** `elapsed > exp(log_median + 4 * log_mad)` | Interrupt; enter retry path |

Formula:

```text
log_samples       = ln(duration_seconds)
log_median        = median(log_samples)
log_mad           = median(|log_sample - log_median|)
watch_threshold   = exp(log_median + 2 * log_mad)   # ~1.35σ — switch to silence monitoring
kill_threshold    = exp(log_median + 4 * log_mad)   # ~2.7σ, Tukey-equivalent — absolute ceiling
```

**How the silence monitor works (streaming required):**
- Track time of last token received from the stream
- If `now - last_token_time > SILENCE_TIMEOUT_SECONDS`, kill immediately
- This fires well before `kill_threshold` for a stalled model; a slow-but-flowing
  model continues past `watch_threshold` without penalty

Multiplier rationale: under normality, Tukey's IQR×1.5 fence sits at ≈ μ ± 2.698σ.
Since MAD ≈ 0.6745σ → σ ≈ 1.4826·MAD, that fence converts to **median ± 4·MAD**.
`watch_threshold` at 2×MAD sits at ~1.35σ — slow enough to be notable, not enough to kill.
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
1. If `elapsed < watch_threshold`: let it run, enforce hard 300s cap
2. If `elapsed >= watch_threshold`: activate silence monitor — track `last_token_time`
3. Kill if `now - last_token_time > SILENCE_TIMEOUT_SECONDS` (stalled)
4. Kill if `elapsed >= kill_threshold` regardless of token flow (absolute ceiling)
5. Kill if `elapsed >= 300s` regardless (hard cap)

Rule of precedence: hard cap (300s) ≥ kill_threshold ≥ silence timeout. Whichever fires first wins.

### If a call completes successfully
1. Record its duration into the per-model rolling window
2. If there are fewer than **5** successful samples, stop there
3. Otherwise compute both log-space thresholds
4. Include the completion in the rolling window regardless of which zone it fell in — it completed

### If a pipeline run predates policy changes
Restart the run instead of trusting it to "pick up" new timeout settings.

An in-flight process keeps the constants it imported at startup.

## Interpretation Rules
- **Hard cap (300s)**: unconditional kill, always takes precedence
- **Kill threshold (4×MAD)**: absolute ceiling — a flowing model still gets killed here
- **Silence kill**: fired from watch tier — stalled model killed before `kill_threshold`
- **Watch tier (2×MAD)**: not a warning, not a kill — activates the silence monitor
- **Silence kill / hard cap / cancel**: failed call — exclude from baseline entirely
- **Any completion**: include in baseline — slow completions are real evidence of model behavior, not contamination

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
- Mixing killed/cancelled calls into the timing baseline
- Using nominal-space `median + 2*MAD` instead of log-space on right-tailed latency data
- Using mean/stddev on long-tail generation latency
- Treating outlier warnings as hard failures
- Assuming a live process sees new timeout constants without restart

## Dark Factory Reference Values
These are the current values documented by this skill:

```text
hard_timeout_seconds     = 300
outlier_min_samples      = 5
outlier_window           = 50
watch_multiplier         = 2   # log-space; ~1.35σ — activates silence monitor
kill_multiplier          = 4   # log-space; ~2.7σ — absolute ceiling
silence_timeout_seconds  = 20  # kill if no new tokens for this long after watch tier fires
tracking_scope           = per-model
```

If implementation changes, update this file to match the live policy.
<!-- consolidation:see-also:start -->
## See Also
[[stratified-quota-sampling]]  [[mad-dynamic-batching]]  [[class-balancing]]  [[agentic-harness]]  [[deep-research]]
<!-- consolidation:see-also:end -->
