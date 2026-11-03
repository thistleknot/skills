---
name: mouse-model-testing
description: >
  Test/tune a system component in an isolated, accelerated micro-harness (a
  "mouse model") instead of the full pipeline. Use whenever validating a
  feature, tuning a learner/policy/hyperparameter, or answering "does X
  materially help?" would otherwise mean a slow, noisy end-to-end run. Rip the
  REAL component out, crank the variable of interest at full rate, and measure
  a quantity that is INDEPENDENT of the slow thing (updates-to-learn,
  samples-to-threshold) so it translates back to macro. Pairs Optuna for the
  search. Distinct from autoresearch (hill-climbs the full system) and
  optuna-nested-cv (ML model/CV search) — this is component isolation +
  translation. Triggers: "test in mice", "mouse model", "isolate before
  scaling", "why is this so slow to validate", "find the optimal config fast",
  "does this feature actually lift".
status: active
last_validated: 2026-07-18
supersedes: []
validation_method: session
---

# Mouse-Model Testing

**Scientists test in mice first.** Do NOT validate or tune a component by running the whole system — that is slow,
noisy, and contended. Isolate the REAL component in a controlled micro-environment, drive the variable of interest at
full/accelerated rate, and measure a quantity that is INDEPENDENT of the slow dimension (steps / scale / cadence) so
the result TRANSLATES to macro by construction. Target: ≤10 minutes from question to curve, ideally seconds.

## When to Use

Use a mouse model when:
- Validating whether a feature **materially helps** (lift), before shipping it.
- **Tuning** a learner, policy, or hyperparameter mix.
- A full end-to-end run to answer the question would take 10s of minutes / hours or fight for compute.
- The component's behaviour is governed by a **scale-invariant** quantity (updates-to-converge, samples-to-signal,
  gradient-to-noise ratio) you can measure without the slow loop.

Do NOT use it when:
- The question is genuinely emergent/whole-system (multi-component interaction) — but even then, isolate each link
  first and only compose in the full run as the final confirmation.
- There is no isolatable component (then reduce scope until there is).

## The Pattern

1. **Isolate the real tissue.** Instantiate the ACTUAL class/function under test — never a reimplementation. The
   mouse measures the real organism, not a sketch of it.
2. **Accelerate the bottleneck.** Remove the slow cadence/gate; drive the component at full rate (feed updates,
   samples, or inputs directly).
3. **Measure a scale-invariant quantity.** updates-to-converge, samples-to-threshold, lift-per-update — NOT
   wall-clock or step count. That invariance is what licenses the macro claim.
4. **State the translation explicitly.** Map the invariant back: "K updates needed × steps/update = macro steps;
   can the macro budget supply K?" A mouse result without a stated translation is just a lab curiosity.
5. **Sanity-guard against a bad task.** Before concluding "the component is broken", run the trivial-est version to
   separate a weak component from a hard/low-signal test task.
6. **Permutation battery, not one case.** Vary the controlled input ≥3 ways so you gate the RULE, not a memorised
   instance.

## Optuna in the Mouse (tuning, not just verifying)

Wrap the harness in an Optuna study (TPE, ~20–30 trials, mouse-sized episodes/trial) at a **FIXED COMPUTE budget** so
every trial is compared at equal overhead. At fixed compute, batch size IS the frequency lever (updates =
compute/batch), so one search over (lr, batch) trades frequency × batch × lr jointly. Anchor search bounds to
EXISTING constants (e.g. `lr ∈ [BASE_LR/3, BASE_LR·100]`), not fresh magic numbers.

## Three Traps (each cost a near-miss)

- **Objective-fidelity trap.** The mouse reward MUST match the SHAPE of the real reward (target-tracking vs monotone
  vs sparse). A monotone proxy ("maximize the mean") never punishes overshoot, so Optuna will hand you a reckless
  config that looks great in the mouse and DIVERGES on the real target-tracking task. Shape the mouse reward like the
  real one.
- **Immortal-mouse trap.** If the real agents/episodes DIE (finite, variable lifespan), an immortal mouse mis-ranks
  configs. A frequent-update policy that wins on an infinite horizon can lose under die-off, where few, stabler
  updates beat many noisy ones. **Model the mortality** (sample lifespans, measure the metric AT DEATH). Often the
  honest conclusion is that within-lifetime learning is structurally futile and the across-generation process is the
  real learner.
- **Magic-constant trap.** When Optuna hands you an optimum, express it as a FUNCTION of a REAL constant, never a
  pasted number: the RLOO leave-one-out minimum (2), natural log base `e`, `1/dim`, `π`/`φ`, or an existing symbol
  (e.g. an encoder width). If a scalar truly survives, derive it (rounding, softmax-of-sign) off something principled.

## Worked Example (the maw-RL, 2026-07-18)

A "does the RL beat its warm-start?" question burned an hour of contended in-game ablations (8 runs × 1700 steps,
kept crashing on a Unicode print). The mouse settled it in minutes:
- `tools/probe_maw_isolated.py` — does the REAL `ColonyMawRL` learn at full update rate? (yes, but slow).
- `tools/mouse_maw_parallel.py` / `mouse_learner_fix.py` — sweep batch/lr; found lr, not batch, was the binding lever.
- `tools/mouse_optuna.py` — Optuna at fixed compute; the FIRST run used a monotone bandit and "found" a reckless
  lr=0.14 that diverged (objective-fidelity trap); a target-tracking reward flipped it to a stable modest optimum.
- `tools/mouse_mortality.py` — exponential die-off INVERTED the immortal result: with ~3 updates before death,
  bigger batches win, and NO cadence cleared 10% lift ⇒ within-life RL is inert by mortality; the GA is the real
  learner. All cadence tuning was reverted. Mouse behaviours pinned as regressions in `tests/test_maw_mouse.py`.

## Relationship to the Operating Contract

This is "isolate before scaling / never debug through the full pipeline / synthetic permutation gates" made
concrete. Default to it for EVERY feature-validity or tuning question before touching the live system. Once the mouse
gives a verdict, PIN it as a permanent unit test so a future change fails in the mouse, in seconds, not in production.
