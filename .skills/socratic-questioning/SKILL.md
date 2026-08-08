---
name: socratic-questioning
description: >
  Use when a user's request is underspecified or ambiguous and guessing wastes
  work -- the fix is to actively probe and resolve intent through targeted
  questions instead of assuming. Covers information-theoretic question selection,
  real-time coaching/oversight of a collaborator, and multi-agent SOP-style
  workflows that verify intermediate understanding before acting.
status: active
last_validated: 2026-07-27
---

# Socratic Questioning

Distilled from arXiv 2510.2741 (Nous / closing the expression gap via Socratic
questioning), 2502.17643 (Socratic AI-enabled coaching), 2308.00352 (MetaGPT
SOP-encoded workflows), 2409.10277 (Cognitive Kernel active information
gathering).

## When to Use

- The stated request has an *expression gap*: the user knows the goal but the
  instruction is ambiguous, and acting on the literal text would produce the
  wrong artifact.
- A collaborator (human or agent) is executing a task and could drift; real-time
  probing can catch a misalignment before it compounds.
- You have a structured task space where the *most informative* next question can
  be chosen rather than asked at random.

**Do NOT use when** intent is already unambiguous -- extra questions are friction,
not diligence (CLAUDE.md: surface inferred intent once, then proceed). Also skip
when no structured task space exists to define an information gain; then a single
plain clarifying question beats a Socratic loop.

## Core Concepts

- **Intent as an information-theoretic target (Nous, 2510.2741).** Model the
  space of possible intended tasks; pick the question that maximally reduces
  uncertainty (expected information gain / reward signal), not the first doubt
  that surfaces. This resolves intent without costly human preference annotations
  or an external reward model, and adapts to the user's expertise level -- an
  expert gets fewer, sharper probes than a novice.

- **Coaching / real-time oversight (Socratic, 2502.17643).** Monitor an ongoing
  task for misalignments in *shared understanding* and intervene with a guiding
  question at the moment of drift, rather than a post-hoc correction. Effective
  in life-critical, collaborative settings where a wrong assumption is expensive.

- **SOP-encoded verification (MetaGPT, 2308.00352).** Bake standardized operating
  procedures into the prompt sequence so agents verify intermediate results
  against expected structure before passing work downstream -- questioning as a
  workflow gate, not an afterthought.

- **Active information gathering (Cognitive Kernel, 2409.10277).** When intent is
  clear but *facts* are missing, the analogue is to actively pull the needed
  information from real-world sources rather than hallucinate it.

## Protocol

```
resolve_intent(request, task_space, expertise):
    belief <- prior_over_tasks(request, task_space)
    while entropy(belief) > tolerance(expertise):
        q      <- argmax_q expected_info_gain(q, belief)   # sharpest probe
        answer <- ask(q)                                   # one question
        belief <- update(belief, answer)
        if drift_detected(belief, goal):                   # coaching intervene
            intervene(belief)
    return act(most_likely_task(belief))                   # proceed, no over-asking
```

Failure modes: needs a definable structured task space and intrinsic reward;
effectiveness depends on simulated-dataset quality; real-world high-variability
performance untested (2510.2741). Over-probing a clear request is itself a defect.

## Related

`deep-research` (refutation-first querying), `crystallization` (restate intent),
`reasoning` (candidate-hypothesis ranking over intended tasks).
