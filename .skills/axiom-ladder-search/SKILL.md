---
name: axiom-ladder-search
status: active
last_validated: 2026-09-05
description: >
  Round-based parameter search for expensive, human-judged systems. Sample ONE
  axiom, rank the top 3, make those winners fixed BASES, then cross them against
  a DIFFERENT axiom -- expanding into new dimensions each round rather than
  drilling the winner's own axis. Carries winners forward re-run under identical
  conditions so "did we improve" is answerable. Use when each evaluation is slow
  or costly (image/video generation, model training, physical process tuning),
  the quality bar is a human eye rather than a metric, and a full cartesian grid
  is unaffordable. Covers proving an axis is live before sweeping it, ablation
  when parameters look inert, iso-cost banding to trade one resource against
  another fairly, and why an automated score is a second opinion. Trigger on
  "grid search", "sweep these settings", "top 3 then expand", "partition the
  variance", "which parameter matters", or a sweep whose cells come back
  identical.
---

# Axiom ladder search

A search protocol for spaces where **each cell costs real time and the judge is a
human eye**. A full cartesian grid over five parameters at four levels is 1024
runs; at 30 seconds each that is eight hours to answer a question that three
rounds of nine cells can answer in twenty minutes.

The name: each round samples one *axiom* — one dimension of the space — and the
winners climb a ladder of rounds, gathering evidence as they go.

## The loop

An **axiom set** is a group of parameters belonging to one component. Rounds
advance through the sets in order of how much structure they add, and a new
COMPONENT is only introduced once the previous one's parameters are settled:

```
round 1   axiom set 1 -- the core sampler        -> rank, human picks top 3
round 2   axiom set 2 -- the next parameter group -> rank, picks top 3
round 3   axiom set 3 -- a SECOND sampler stage   -> rank, picks top 3
round 4   axiom set 4 -- a ControlNet / guard layer
          ...
          every round carries the previous winners forward, re-run
```

Ordering matters: adding a component while the one beneath it is still unsettled
means a bad result indicts neither. Settle the base, then add structure on top of
a base you trust.

Within a round, the previous winners are the bases **for the exploit cells only**,
and the new axiom set is what varies — expansion into a new dimension, never
drilling the winner's own axis. Every factor still carries levels according to its
status (see *Conditional closure*); nothing is ever frozen outright.

Stated as the operator does:

```
select top 3
expand next dimension, sampling top-3 params + new params  (by MMR)
repeat for each axiom set
```

**MMR is what guarantees maximum spread within each axiom set** — it is the
selection criterion, not an implementation detail. Picking the winners and then
sampling their cross-product any other way either clusters (re-rendering one
neighbourhood) or spreads uniformly into regions already rejected. See
"Select by MMR" below.

**Expansion, not drilling.** Round 2 must cross the winners against a dimension
you have *not* varied. Stepping a winner up and down its own axis refines a curve
you already have points on, discovers nothing new, and silently asserts that
everything you froze is irrelevant. Drill a single axis only at the end, once the
space is mapped and you are closing on an optimum.

**Carry the winners forward, re-run.** Every round re-renders the previous
winners alongside the new candidates under identical conditions. "Did we improve"
cannot be answered against remembered numbers from a previous round — lighting,
seed, prompt and code have all moved. A carried winner is the only honest
baseline, and it costs one cell.

**Hold everything else, including the stochastic parts.** One seed, one prompt,
computed once and pinned. If the prompt is generated per cell, two cells that
differ only in sampler also differ in prompt, and the comparison measures the
prompt generator.

## Conditional closure — never freeze, only demote

**A closure is not a fact about a parameter. It is a fact about a parameter GIVEN
a recorded context.** Freeze a winner and the search becomes coordinate descent on
a non-separable objective: it converges to a local optimum and can never escape,
because a region was rejected under settings that later changed.

> **Invariant: no level is ever eliminated, only deprioritised. Every round keeps
> a nonzero probability of re-testing any rejected level under current
> conditions.**

### The status ladder

| status | levels carried | exit |
|---|---|---|
| **LIVE** | 3+ rungs, or all categorical levels | evidence met → NARROWED |
| **NARROWED** | 2 — champion + best challenger | unbeaten 2 rounds → DORMANT |
| **DORMANT** | 1, sits in the re-open queue | any trigger → back to NARROWED |
| **RETIRED** | 1, permanent | only after an ablation proves the axis inert |

One step per round, in either direction. **Nothing goes LIVE → DORMANT in a
single round** — that is the premature-closure mistake in its exact form.

### Evidence required to demote LIVE → NARROWED

All four. Any one failing blocks the demotion.

1. **Exposure** — every level has ≥ 4 renders, and `max/min exposure ≤ 2.0`
2. **Matched pairs** — ≥ 3 pairs differing in this factor alone, ≥ 2/3 agreeing
3. **Context breadth** — the champion won under ≥ 2 settings of every other LIVE
   factor in the set, especially its coupled partner
4. **Seed audit** — at the moment of closure only, re-render champion and
   challenger on a second pinned seed. If the ranking flips, the closure is void.
   Two cells, paid once per closure, not per round.

**Two agreeing picks is one matched pair — an anecdote.** A real case: a sampler
was about to be closed on 8 exposures vs the challenger's 4, win rates 0.25 vs
0.00, one matched pair, no seed audit. The resolving experiment overturned it.

### The closure card

Every closure writes one record. It is the licence later rounds check.

```
factor:        sampler
status:        NARROWED
champion:      lcm          challenger: euler_ancestral
held-context:  scheduler=beta  steps in {6,12}  denoise in {.33,.87}  seed=4242
evidence:      exposure 8/4 (ratio 2.0, AT LIMIT) | matched pairs 1 (BELOW 3)
               context breadth FAIL (one steps value) | seed audit NOT RUN
re-open if:    steps changes | a second sampler stage is added | plateau
```

Keep failed cards. A card recording *why* a region is still open is more useful
than a deleted one.

### Re-open triggers — any one promotes the factor a step

- **T1 Context drift** — a factor named in `held-context` moved more than one rung
- **T2 New component** — a new axiom set consuming the same resource (a second
  sampler re-opens steps/cfg/denoise; a guard layer re-opens cfg/denoise)
- **T3 Baseline beat** — a carried winner outranks the whole new sheet; the round
  added nothing and the closure that shaped it is suspect
- **T4 Plateau** — two rounds of "these all look the same"
- **T5 Staleness** — DORMANT and untested for 3 rounds gets one free cell
- **T6 Retro-invalidation** — a bug fix or model change **voids** every closure
  whose held-context touched it. Not re-queued: voided. The measurement never
  meant what it appeared to.

## Interactions — closed jointly or not at all

Declare physically coupled pairs up front. Members of a coupled pair are **never
closed independently**.

```
sampler x steps      sampler x cfg      steps x denoise
steps x resolution   cfg x guard strength
```

### Conditioned ladders

For a coupled pair, levels are conditioned on the partner, not shared absolutes:

```
steps ::= { native(sampler), native x1.5, native x2 }
```

This matters more than it looks. Testing `lcm` and an ancestral sampler on a
shared ladder of `{6, 12}` measures *"which sampler tolerates 6 steps"* — that is
one sampler's home range, and the other never gets a fair trial. A conditioned
ladder gives each equal **relative** effort. Report the cost multiplier alongside:
a win at 4x cost has to be worth 4x.

### The 2x2 corner probe — 4 cells

When the prior is silent on whether A and B interact, place a corner block:
`A ∈ {champion, challenger} × B ∈ {champion, challenger}`, everything else pinned.
From the full ranking:

```
S_parallel = rank(A1B1) + rank(A2B2)
S_crossed  = rank(A1B2) + rank(A2B1)
interaction if |S_parallel - S_crossed| >= 4     (on a 12-cell sheet)
```

If it fires, bind A and B into one joint axis for every later round. Four cells
buys an answer to a question that otherwise silently poisons everything after it.

**Free signal:** if two cells differing only in A rank adjacently in one context
and far apart in another, A interacts with whatever differs between the contexts.
That falls out of a full ranking at no cost.

## Before you sweep: prove the axis is live

**A grid whose cells agree to three significant figures is a broken instrument,
not a tie.** Check, in this order:

1. **Does the axis reach the output?** Change the *upstream* stage's seed and diff
   the result exactly — pixels, bytes, values. Zero difference means that stage is
   disconnected and every planned cell is void.
2. **Are you measuring the real output?** Not a preview, a debug view, or an
   intermediate. Collecting "all outputs" and taking the first is how a hint map
   gets scored instead of a render.
3. **Are the values legal?** Read declared bounds from the schema rather than
   deriving them arithmetically. A value the server rejects is a failed run, not a
   setting.

## When the parameters look inert: ablate, do not sweep harder

If the knobs genuinely do not move the result, the fault is **structural**.
Rebuild from the minimum and re-add ONE component per stage:

```
A   the simplest thing that could work      -- does the core work at all?
B   A + exactly one component               -- any difference is attributable to it
C   B + exactly one more
```

Two components added together are two hypotheses fused into one, and a failure
there indicts neither. Include a **negative control** — a cell expected to fail —
so a clean sheet cannot be mistaken for an inert test.

This is how a destructive component gets found. A guard that made results *worse
as its strength rose* is a bad input, not too much guidance; a stage that changes
nothing when its upstream seed changes is discarding its input entirely.

## Iso-cost banding: trade one resource against another fairly

When two parameters both consume the same budget — steps and resolution, batch
and epochs, samples and depth — comparing them naively confounds quality with
compute. Compute the band where cost is constant and sample along it:

```
cost ~ steps x pixels

  128x96    12288 px   1.0x   ->  24 steps
  256x192   49152 px   4.0x   ->   6 steps
  384x288  110592 px   9.0x   ->   3 steps
```

Every cell on that band costs the same, so a winner answers *"spend the budget on
steps or on pixels?"* rather than *"which cell did I let run longest?"*. Report
the budget multiplier on every off-band cell too: a win at 4.5x cost has to be
worth 4.5x.

## Ladders, not continua

Sample each axis on a short **multiplicative ladder** rather than a linear range,
because most of these knobs act multiplicatively:

```
phi-ish   0.08  0.13  0.21  0.34  0.5  0.55  0.67  0.78  0.87  0.92
counts    3  4  6  9  12  18       (x1.5 each)
```

Ten rungs beats a continuum: it keeps the option space small enough to hold in
your head, and it makes "the two rungs either side of the winner" a well-defined
drill step. Watch for **floors and ceilings** — many parameters do nothing below
some value and destroy the result above another, and both edges are worth
locating early because they bound every later round.

## When the cross-product explodes: SAMPLE it, do not enumerate it

Late rounds stop being grids. Once winners carry several settings each and a
second stage doubles the factor count, the product blows past anything
affordable — six factors at three levels is 729 cells, six hours at 30s each.

**Do not shrink the question to fit a grid. Sample the space.**

### EVERY variable gets spread, every round

**No factor is ever held constant.** A frozen factor contributes no variance, so
it teaches nothing this round AND has no dispersion to derive levels from next
round — the error compounds. Worse, freezing silently asserts the value you
happened to pick is correct, which is exactly the assumption a search exists to
test. If a factor is in the model, perturb it; if it is not worth perturbing,
remove it from the design and say why.

This is a real, expensive failure: freeze the sampler for a whole session because
one early measurement said it did not matter, and every subsequent round tunes
the wrong knobs. When the sampler was finally perturbed it changed the output
*class*, not its quality — and the original measurement turned out to have been
taken under a since-broken configuration.

### Derive the levels by median +/- 2 MAD

Take each factor's levels from the **surviving winners' median, plus and minus
two median-absolute-deviations**. MAD over min/max because a couple of clustered
picks make min and max meaningless, while MAD reports the real dispersion:

```
MAD = median(|x - median(x)|)
levels = [median - 2*MAD, median, median + 2*MAD]   snapped to the ladder
```

Two degenerate cases, both informative rather than blocking:

- **MAD == 0** — every survivor used the same value. The human has converged on
  that factor. Do not collapse the level set to a point: keep the median and take
  the two neighbouring rungs from the standing ladder, so convergence is
  *re-tested* rather than assumed permanent.
- **CATEGORICALS have no MAD at all.** This is the hole through which a hard
  freeze sneaks back in: a sampler or scheduler name has no median and no
  deviation, so a numeric-only rule leaves it with nothing and it gets frozen by
  default. Instead: keep the champion **plus the best-ranked alternative level**,
  which is exactly NARROWED. Never fewer than two while the factor is above
  DORMANT.
- **The median collapses onto the max** — the human is clustered at the top of
  the range and dislikes the low end. Keep the sample weighted high, but still
  carry one low rung so the dislike stays falsifiable.

Clamp the resulting levels to the ladder and to any measured floor/ceiling.

### The budget is the number of cells a human will actually rank

Around **12** — the bottleneck is the eye at the end, not the GPU. Split it:

```
6  EXPLOIT     MMR over the current axiom set, anchored to the winners
3  STRUCTURE   the 2x2 corner probe, or 3 forced matched pairs
2  RE-OPEN     top of the re-open queue, rendered at CURRENT context
1  WILDCARD    uniform random over the whole legal space, ignoring the winners
--
12 ranked cells,  + 2-3 carried winners as baseline, outside the 12
```

**The re-open cells are not skippable.** They are the only mechanism by which a
wrong closure can be undone; a scheme with zero exploration budget cannot escape
a local optimum by construction. If the queue is empty they go to the
least-exposed level of any NARROWED factor.

**The wildcard** is whole-region insurance and doubles as a negative control. If
it ever ranks top-3, the exploit region is wrong and every factor widens a step.

Shift the ratio with confidence: 4/4/4 early while the space is unmapped and
interactions are unknown, 8/2/2 late once closures have real evidence behind
them. **Never let recovery reach zero.**

### Select by MMR

The candidate pool each round is `winning params x new dimension levels`. Two
things must hold of the cells you pick from it: they should sit **near what
already won**, and they should be **far from each other**, so the round covers
ground instead of re-rendering one neighbourhood.

That is Maximal Marginal Relevance:

```
pick = argmax over remaining candidates c of
         lambda * relevance(c, winners)
       - (1 - lambda) * max similarity(c, already_picked)
```

- **relevance** — closeness to the endorsed region: how much of `c` is shared
  with, or adjacent to, a winner.
- **similarity** — distance to the nearest already-selected cell, same metric.
- **lambda ~ 0.5-0.7** — lower explores harder, higher exploits the winners.

For mixed parameter types, distance is the mean of per-factor distances:
normalised absolute difference for numerics, 0/1 for categoricals.

**This is the whole reason the loop works.** Selecting winners then expanding is
only meaningful if the expansion stays anchored to the winners while spreading
inside that region. MMR does both in one criterion.

**Latin hypercube is the wrong tool here** and is worth naming as such: it
balances *levels* but is **blind to the winners**, spreading uniformly across
regions the human has already rejected. It answers "did I cover the space?" when
the question is "did I cover the space *that won*?".

### Exposure ratio, not just coverage

MMR optimises spread, not balance, so it will happily under-sample a level.
Before rendering, print factor x level x count and apply:

```
reject the selection if any factor's  max/min exposure ratio > 2.0
```

Repair by force-swapping the most redundant selected cell — the one with the
smallest distance to another pick — onto the starved level.

Zero-coverage is the obvious failure; **under-coverage is the common and
dangerous one.** A level that lost on 4 exposures while the champion had 8 did
not lose, it was under-sampled: win rates of 0.25 vs 0.00 on unequal samples are
not distinguishable, and closing on them is how a search convinces itself of
something it never tested.

### No near-duplicate samples

Put a **hard minimum distance** between selected cells — roughly one factor's
worth, `1 / n_factors`. Two cells that differ in a single factor are the same
experiment run twice as soon as that factor turns out to be inert, and you will
not know it is inert until after you have paid for both.

This is not hypothetical. A Latin hypercube produced two cells identical in 5 of
6 factors, differing only in resolution — and resolution had no visible effect at
that setting, so they rendered as the same picture and took two slots on a
12-cell sheet.

**Exact equality is the wrong bar.** Checking that parameter dicts differ passes
happily on a pair one step apart. Check DISTANCE, and reject below the floor.

Three follow-through rules:

- If the floor exhausts the pool, **return fewer cells and say so** rather than
  padding with near-duplicates to hit a target count.
- **De-duplicate the CARRIED WINNERS against the design too**, not just the
  design against itself. A carried baseline whose settings already appear as a
  design cell renders byte-identical and wastes a slot — and it is easy to miss,
  because the two come from different code paths. Check the union.
- After rendering, assert the OUTPUTS differ. If two cells with different
  parameters produce identical artefacts, the differing parameters are inert or
  disconnected — report that as a finding, not as two results.

Add the **carried winners** as explicit extra cells on top of the selection —
they are not part of the design, they are the baseline.

### Sample size

Around **12** — enough that each level of each factor is seen a few times, few
enough that a human can rank the sheet in one pass. The eye is the bottleneck,
not the GPU.

## Ranking

**Surface the artefacts. Both rankers score every cell. Fuse with RRF, human
preference dominant.**

```
score(cell) = w_human / (k + rank_human) + w_auto / (k + rank_auto)     k = 60
w_human = 2.0    w_auto = 1.0     exact ties broken by the human rank
```

- **Human** ranks or tiers the whole sheet and marks a top 3, flagging any
  comparison that is a coin-flip.
- **Auto** ranks by the metric composite.
- A cell the human did not rank contributes only its auto term.

Why both: the metrics catch what the eye skips over — a lost transparency key, a
collapsed palette — and the eye catches everything the metrics do not model.
Where they disagree, that gap is information about the scoring function, and the
scoring function is what changes. **The human wins.**

### Rank everything, do not just pick

Same renders, far more signal. A full ordering (or A/B/C/D tiers with ties) makes
matched pairs, exposure-normalised win rates and the corner probe computable for
free from images already paid for. **Picking a top 3 discards exactly the
information that makes a closure defensible** — it is what let two agreeing picks
look like convergence.

Explicit ties are also the cheapest inertness detector: if every comparison
varying factor A is flagged coin-flip, A is a candidate for ablation, not tuning.

Record a **reason word** per top cell — "sharper", "muddier", "wrong colour".
Two winners that win for different reasons are two different optima and both
should be carried; two that win for the same reason are one optimum sampled
twice.

### Distinguishability

Two levels differ only if **each has ≥ 4 exposures AND the win-rate gap ≥ 0.4**,
or **≥ 3 matched pairs agree**. Below that the honest answer is "insufficient
exposure", not a winner.

If you score, weight a **disqualifying** property as a MULTIPLIER, not one term
among many — an output that fails a hard requirement is worthless however well it
scores elsewhere, and an additive score will happily rank it mid-table.

## Failure modes this exists to prevent

| Symptom | Real cause | Check |
|---|---|---|
| All cells identical | axis disconnected from output | seed-diff the upstream stage |
| Cells identical to 3 s.f. | scoring the wrong artefact | assert the output node, not "first output" |
| Sweep after sweep inert | a destructive component upstream | ablate from minimum |
| A "measured" prior that misleads | measured under a since-broken config | retire and re-measure |
| Winner cannot be reproduced | winners never re-run | carry forward every round |
| Cheap config never tried | one dimension frozen all session | expand, do not drill |
| Winner wins in one context only | closed on a coupled axis | conditioned ladder plus corner probe |
| A level lost on 4 exposures | under-sampled, not worse | exposure ratio <= 2.0, or 3 matched pairs |
| Search plateaus and will not improve | greedy local optimum, no exploration budget | 2 re-open plus 1 wildcard cell each round |
| A categorical got frozen silently | the MAD rule is numeric-only | categoricals keep champion plus best alternative |
| Two picks agreed, so it converged | one matched pair is an anecdote | all four closure tests, or stay LIVE |
