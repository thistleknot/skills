---
name: evidence-first-exploration
description: Discover how an opaque system actually works by forming falsifiable theses from measured evidence, instead of asserting mechanisms that sound right. Use this whenever you are probing a system you cannot read the source of or whose behavior surprises you — reverse-engineering an undocumented API or binary, automating a GUI, driving an emulator or game, debugging "my fix didn't take", or any time you have already tried two or more fixes that failed, a null result is guiding your conclusions, or you catch yourself explaining WHY something can't work rather than testing whether it does. Also use it proactively before a long probe campaign, to design one-variable batteries and decide what observation would falsify you.
---

# Evidence-First Exploration

## The failure this exists to prevent

You probe a system, get a null result, and explain it with a mechanism that
sounds authoritative — "clicks can't reach it, the widget polls the cursor" —
and that explanation quietly becomes a fact you build on. Every later
observation gets bent to fit. You stop testing the thing that would kill it.

A confident wrong model is far more expensive than an admitted unknown, because
it *forecloses the correct line of attack*. The cost is measured in days.

The antidote is not caution. It is making your beliefs **cheap to kill**.

## The core discipline

Separate three things that feel identical when you're moving fast:

| | what it is | how to write it |
|---|---|---|
| **Observation** | what you measured | "36 clicks produced 0 pixel change" |
| **Thesis** | your current best explanation | "candidate: only the first click registers" |
| **Mechanism** | *why* you think that happens | "guess: a grab is never released" |

Observations are durable. Theses are provisional. Mechanisms are usually the
first thing to be wrong — and they are exactly what gets asserted as fact.

State theses like this, every time:

> **Thesis:** clicks are scaled by 0.8 before hit-testing.
> **Rests on:** two selections landing one row off, consistently.
> **Falsified if:** sending capture×1.25 does *not* hit the intended row.

If you cannot name the observation that would kill your belief, you do not have
a thesis. You have a preference.

## Build a model, not a lookup table

The strong temptation in an opaque system is to accumulate per-state trivia:
this button is at (216,590), that list needs index 3. That's a bandit strategy —
it treats every screen as an unrelated puzzle.

The environment does not reset between states. There is one transition function
underneath, and the useful artifact is a short list of **laws** that hold
everywhere:

- a coordinate transform between what you observe and what you send
- an input protocol (ordering, state that must be cleared between actions)
- alternate channels that bypass the normal path entirely
- how to decode an observation into "what just happened"
- what persists across state changes, and what recompiles fresh

Per-state details are *derived* from the laws, not independent facts.

**A law is only real if it predicts a state you have never visited.** A law
confirmed only where it was discovered is a guess with good PR. So record each
law with its honest scope:

```
L1  send = observed × 1.25
    evidence: predicted a target BEFORE running; it hit
    scope:    claimed global — CONFIRMED in one panel, UNTESTED elsewhere
```

That scope line is the most valuable thing in the file. It tells the next
person exactly where to aim to break you.

## Explore as tree search, not as poking

Treat it as MCTS/minimax rather than a bandit:

- **Nodes** are states, **edges** are actions.
- The reward is **sparse** — it only pays when you reach the next preferable
  state on the path to the goal. Everything else is a rollout returning zero.
- **Make replay-from-root cheap and deterministic.** This is the highest-leverage
  investment in the whole endeavor. If returning to any known state takes one
  command and you can *prove* you landed there, you can explore fearlessly.
- **Backtracking is a legal move.** When state gets dirty, replay to a node you
  trust rather than reasoning about the mess.
- **Expand deliberately.** From a node, list untried edges, take the one most
  likely to reach the next preferable state, and record the outcome — including
  the failures, which prune the tree.

Keep the frontier explicit. Knowing "there is exactly one unreached node" focuses
effort better than a vague sense of progress.

## Design the probe before you run it

**Vary one thing.** If a battery changes position *and* timing *and* state, its
result teaches nothing. Same target, same coordinates, only "before scroll" vs
"after scroll" differs.

**State the prediction first.** A probe with no prediction can't surprise you,
and surprise is the only thing that updates a model. Writing "row 1 should need
(625,300)" before running converts a lucky hit into evidence.

**Beware the null result.** A zero is the most over-interpreted observation in
existence, because it's consistent with *many* models: the action didn't land,
it landed and did nothing, it landed somewhere else, or something upstream ate
it. Never let a null result alone establish a law.

> Worked example — the trap in its natural habitat:
> A 36-point click sweep returned zero response at every point. Conclusion drawn:
> "clicks never work here; the toolkit ignores synthetic input." That became
> load-bearing and blocked the correct approach for hours.
> The truth: clicks worked fine, but **only the first one registered** — the
> first click grabbed a control that was never released, and the sweep had burned
> its one live click on empty space before reaching anything clickable.
> The 36 zeros were real. The law derived from them was backwards.
> What broke it: a user insisting the opposite, and one battery that varied a
> single dimension.

## Decode observations quantitatively

"It looks the same" is not a measurement. Build a cheap decoder that maps a
numeric signal to a semantic class, so that *nothing happened* is distinguishable
from *the input never arrived*:

```
0 px changed      input never landed (or a modal swallowed it)
~5k               one row selected / a control enabled
~78k              a list scrolled
~180k             a panel opened or closed
~477k             whole screen — a crash or blank, NOT a UI response
```

The magnitudes matter more than the pictures. The decoder above turned
ambiguous screenshots into a reliable signal and made every later probe faster
to interpret. Build the equivalent for your domain — byte counts, response
sizes, log-line classes, exit codes.

## When falsified, revise the thesis — not the symptom

The reflex after a failed prediction is to patch around it. Resist: a patch on a
dead thesis produces a system that works by coincidence and fails later for
reasons no one can reconstruct.

Instead, ask what the failure implies about the *model*:

- guess A: "the button state latches; release anywhere clears it" → tested,
  falsified
- guess B: "the grab is held at the **previous** position, so the release must be
  posted **there**" → tested, confirmed, and the fix followed directly

Two revisions is a reasonable budget. After that, **park it**: write down what
you tried, what you observed, and the workaround, then pivot to another edge.
Parked-with-a-workaround is a legitimate outcome. Grinding is not.

## Record a supervised dataset, and keep the failures

The output of exploration is not prose. It's a dataset:

```
STATE     where you were (a node)
ACTION    exactly what you did (as sent, not as intended)
OBSERVED  the measurement — delta, log line, exit code. Not a vibe.
IMPLIES   the law it supports, or the thesis it FALSIFIED
```

**Keep the falsified records.** They are the highest-signal rows in the file,
because they encode which confident beliefs to stop trusting. A log of only
successes teaches style; a log containing "I believed X for three hours and here
is the measurement that killed it" teaches calibration. Most exploration
transcripts quietly drop their dead ends, which is precisely why they don't
compound into anything.

## Verify you are testing what you think you are testing

Before trusting any result, confirm the artifact under test is the one you
changed. This class of error is silent and devastating: a stale binary, a cached
module, a shadowed config, a second copy on the path, a build that emits to a
different target than the one being launched.

The check is usually trivial — assert a unique marker from your change is
actually present in the running artifact — and it belongs in your harness as a
preflight, not as something you remember to do. A campaign run against a stale
build produces confident conclusions about code that was never executed.

## Red flags

Stop and re-derive when you notice:

- explaining *why* something can't work, rather than testing whether it does
- a mechanism from documentation or memory being cited as an observed finding
- a null result carrying a whole conclusion
- your third patch to keep one thesis alive
- a user's counter-model being explained away instead of tested
- "it seems like it worked" with no measurement behind it
- one observed change treated as proof of causation — rerun it controlled first
