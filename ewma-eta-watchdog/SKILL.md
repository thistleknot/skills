---
name: ewma-eta-watchdog
description: >
  Adaptive-alpha EWMA of per-job durations for a windowed batch runner, giving
  (1) a live ETA and (2) a 95% prediction-interval watchdog that kills runaway
  jobs. Use when driving many similar long jobs through a fixed-concurrency
  window (docling/VLM pipelines, per-file transforms, per-paper extraction,
  scrape-then-process batches) and you need a self-calibrating "this one is
  hung" ceiling plus an honest remaining-time estimate — without a hand-tuned
  timeout. Covers the EWMA mean+variance recurrence with sample-adaptive alpha,
  the variance-collapse guards that stop the interval from killing normal jobs,
  the ETA = remaining * ema / window formula, and companion idle-priority /
  cooperative GPU-yield gating so the batch cedes shared resources to
  higher-priority work. Distinct from optuna-nested-cv (search over models) and
  agentic-hyperparm (agent behavior dials) — this is runtime batch scheduling
  telemetry and runaway control.
status: active
---

# EWMA ETA + Prediction-Interval Watchdog

Runtime control for a fixed-window batch runner: learn the job-duration
distribution online, project an ETA from it, and kill jobs that blow past a
self-calibrating 95% ceiling. No hand-tuned per-job timeout — the ceiling adapts
to the observed distribution.

## When to use

- Many *similar* long jobs (seconds–minutes each), run WINDOW-at-a-time.
- Duration varies enough that one fixed timeout is either too loose (lets hangs
  waste hours) or too tight (kills legitimately slow jobs).
- You want a live ETA that sharpens as the run proceeds.
- Runaways should be *logged and retried next run*, not block the batch.

Do NOT use for: uniform sub-second tasks (overhead not worth it), or jobs whose
duration is intentionally unbounded (training runs) — there "slow" is not "hung".

## The three moving parts

### 1. Adaptive-alpha EWMA (mean + variance)

Smoothing factor tracks sample count so early samples move the estimate fast and
later ones smooth it — the standard N-sample EMA mapping:

```
alpha(n) = max(ALPHA_FLOOR, 2 / (n + 1))     # floor keeps it responsive at large n
```

Incremental mean + variance (EWMA / West-style recurrence):

```
diff  = x - mean
mean  = mean + alpha * diff
var   = (1 - alpha) * (var + alpha * diff * diff)
sdev  = sqrt(var)
```

First sample seeds `mean = x, var = 0`. Only feed CLEAN completions (rc==0 and
the expected artifact exists) — killed/failed jobs are not samples of the
success-time distribution and would poison the estimate.

### 2. 95% prediction-interval watchdog

```
ceiling = mean + Z95 * sdev            # Z95 = 1.96, one-sided upper
```

A still-running job whose elapsed time exceeds `ceiling` is killed (whole
process tree), logged, and left without its output so the next run retries it.

**Variance-collapse guards (critical — without these it kills normal jobs):**

- **sdev floor:** if the first jobs cluster, `var -> 0` and the ceiling collapses
  onto the mean, so the next slightly-slow-but-normal job gets killed. Floor it:
  `sdev = max(sdev, SDEV_FLOOR_FRAC * mean)` (0.30 is a sane default).
- **warm-up:** don't arm the killer until `n >= MIN_SAMPLES` (e.g. 4). Before
  that, use a generous `HARD_CAP` fallback.
- **absolute age floor:** never kill a job younger than `MIN_KILL_S` (e.g. 120s)
  — nothing can meaningfully "hang" in the first couple minutes.
- **absolute ceiling:** always cap at `HARD_CAP_S` regardless of the PI, so a
  drifting EMA can't push the ceiling to infinity.

### 3. ETA from the EMA

With WINDOW jobs running in parallel, wall-clock per job ~ `ema / WINDOW`:

```
eta_seconds = (total - done) * mean / WINDOW
```

Print it on every completion; it converges within a handful of samples.

## Reference constants (starting points)

```
WINDOW          = 2       # concurrency
POLL_S          = 5       # watchdog inspection interval
MIN_SAMPLES     = 4       # clean completions before PI killer arms
Z95             = 1.96
ALPHA_FLOOR     = 0.15
SDEV_FLOOR_FRAC = 0.30
MIN_KILL_S      = 120
HARD_CAP_S      = 1800
```

## Why a poll loop, not concurrent.futures.as_completed

`as_completed` only yields when a future *finishes* — it cannot preempt a hung
job. A watchdog that kills runaways must inspect the elapsed time of
still-running jobs, which requires polling. The poll loop harvests completions
AND enforces the ceiling in the same pass.

## Companion patterns (shared-resource courtesy)

When the batch shares a GPU/box with higher-priority work:

- **Idle priority:** set the driver process to Idle priority class at startup
  (`SetPriorityClass(GetCurrentProcess(), IDLE_PRIORITY_CLASS=0x40)` on Windows);
  children inherit it. Caveat: work submitted through a *shared server* (e.g. an
  Ollama daemon) runs at that server's priority, NOT the driver's — lowering the
  driver only deprioritizes work it runs directly.
- **Cooperative yield gate:** before launching each NEW job, check a sentinel
  file (`_gpu_hold`) and/or a free-VRAM threshold (`nvidia-smi
  --query-gpu=memory.free`). If higher-priority work is present, stop launching
  new jobs; in-flight jobs finish and the window drains, ceding the resource.
  This is the ONLY way to yield shared-server GPU work that idle priority can't
  touch. Gate new launches only — never kill in-flight jobs for courtesy.

## Failure modes / gotchas

- **Feeding non-clean times into the EMA** skews the ceiling — only clean
  completions are samples.
- **No sdev floor** => the killer eats normal jobs the moment durations cluster.
- **Block-buffered stdout to a file** hides live ETA/kill lines — run the driver
  with `python -u` (unbuffered) when redirecting to a log.
- **Restarting the driver to add a feature discards in-flight compute** — edit
  the script and let it take effect on the NEXT natural run instead.
- **`tail -f` detaches when the log is recreated** by a redirect on restart; use
  `tail -F` (follow-by-name) for monitors.

## Reference implementation

`D:\c\arxiv_id_lists\run_staged_scheduler.py` — windowed docling/VLM/methods
pipeline driver: `EwmaStats` class, `clear_to_launch()` yield gate,
`set_idle_priority()`, `kill_tree()` via `taskkill /F /T`, per-job logs, and a
`_watchdog_kills.csv` follow-up log.
