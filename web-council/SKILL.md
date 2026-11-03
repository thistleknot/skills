---
name: web-council
description: "Web-council protocol: three adviser lenses (critique, pipeline-restructure, next-question) each propose from evolving ledger-stored briefs, every proposal is grounded by live web search with at least one refutation-first query, the agent arbitrates and logs, and scored arm outcomes are distilled into one-line lessons that edit the lens briefs (durable text state, frozen model — no gradients, no RL, no learning claim beyond brief edits). Convene during live runs at every crown/verdict checkpoint, on Below-Expectations events, and before entering novel territory."
---

# Web Council — search-grounded advisers for a running experiment

The council turns web search from an ad-hoc rescue into a standing instrument: it convenes
WHILE work is running, produces search-grounded proposals, and leaves a decision trail. It is
a protocol, not a daemon — the agent convenes it, the agent decides. Proposals NEVER launch
compute directly.

The council's job is falsification, not validation. A round where every proposal comes back
"confirmed" is a warning sign (self-confirming queries), not a success. The strongest rounds
occasionally kill something the project believes.

## What improves over rounds

The council is an optimizer, not a ritual. What updates what, using what signal: external
run outcomes (arm result vs its pre-registered bar) edit lens briefs (text). Nothing else
updates — no model weights, no gradients, no RL. Its policy — the thing that must improve —
is three tunable variables, all stored in the ledger, all updated by outcomes:

- **Lens briefs** — the evolving per-lens proposal instructions (initialized from this
  file's adviser section, then edited by one-line miss-lessons from scored outcomes).
- **Query patterns** — which search formulations produced load-bearing evidence vs noise.
- **Convening cadence** — how often rounds are worth their search budget.

The objective is the ledger's accepted-arm hit rate plus discovery rate (proposals that
changed the plan, not just validated it). Sample sizes are small (tens of rounds per
project), so the update rule is verbal, not numeric: each scored outcome is distilled into
a one-line lesson that edits the responsible lens's brief — a written lesson, not a
gradient or reward signal of any kind (Reflexion-lineage, but the mechanism is plainly:
text edits text; the model stays frozen). Fitting bandit statistics or policy gradients to n≈10
delayed rewards is noise-fitting; a written lesson is the highest-information update
available at this scale. Measurement without update is the named failure mode: a hit rate
that is tracked but never changes behavior is a scoreboard, not learning.

## When to convene

- **Live-run checkpoints**: every confirmed crown, epoch verdict, plateau signal, or arm
  verdict of an active training/optimization run — the council informs the run in flight.
- **Below-Expectations events**: mandatory. A grading miss without a council round is a
  process violation.
- **Novel territory**: before committing to an approach the project has not tried (new
  algorithm family, new representation, new tooling), one round scopes what is known.
- NOT on every tick. A round costs ~3–6 searches/fetches; convene at decision points, not
  heartbeats.

## The three advisers

Each adviser is a lens, not a library — do NOT install or invoke TextGrad, DSPy, or any
framework these lenses are reminiscent of. Each lens is adopted in turn and MUST end in a
concrete, searchable proposal (a claim the web can support or refute), not vibes.

The briefs below are the INITIAL policy only. Once a project's ledger contains a
"Lens briefs (evolving)" section, advisers propose from those evolved briefs, not from
this file. This file seeds round 1; the ledger owns every round after.

For higher independence, the lenses MAY be run as separate subagents with isolated contexts
(each receives only the one-line run context and its lens brief, not the other lenses'
proposals or the project's current beliefs). Prefer this on high-stakes rounds; single-agent
role-play is acceptable for routine checkpoints but shares one set of priors across all
three lenses — treat its unanimity as weaker evidence.

1. **Critique lens.** "What is the weakest load-bearing assumption in what we're doing
   right now, and what would the literature say about it?"
   Output: one falsifiable critique + the search that would test it.
   (Example that paid: "the raw-net ceiling is fundamental" → searchless-chess evidence
   showed it's capacity/target-bound → queued a capacity arm.)
2. **Pipeline-restructure lens.** "If the pipeline itself were the tunable program, which
   stage would we recompose, reorder, or re-target?" Output: one pipeline change + the search
   for prior art doing it. (Example that paid: expert-iteration literature independently
   validated a compound value target already in use — converted a guess into a grounded
   design.)
3. **Next-question lens.** "Which question, if answered, most changes the plan?"
   Output: the highest-information query itself, run immediately. (Example that paid:
   NNUE accumulator/lazy-eval/futility searches turned an efficiency hunch into a
   spec'd merge.)

## The round protocol

0. **Reconcile the ledger and update the policy before proposing.**
   - Read the council ledger's open entries. For each previously **accepted** proposal whose
     arm has since resolved, record the outcome as **hit** (the arm beat its bar or changed
     the plan as predicted) or **miss**, attributed to the lens that proposed it. Update the
     running **accepted-arm hit rate** (overall and per-lens) in the ledger header.
   - **Apply the update rule.** Every scored MISS must produce a miss-lesson: one line
     diagnosing what in the proposing lens's reasoning failed (wrong assumption class, query
     that confirmed instead of refuted, evidence misread, constraint missed), applied as an
     edit to that lens's brief in the ledger's "Lens briefs (evolving)" section. Every
     scored HIT may reinforce: note the proposal pattern or query formulation that paid, so
     the lens repeats it. A miss with no brief edit requires an explicit one-line
     justification ("no generalizable lesson: <why>") — silence is a process violation.
   - **Adjust cadence by the scorecard.** Once ≥5 arms are scored: hit rate holding above
     chance → keep cadence; decayed toward chance → halve the convening cadence AND widen
     framing, because the council is burning searches on vibes.
   - Note open **held** and **vetoed** entries. A re-proposal of a held or vetoed item is
     permitted ONLY when citing new evidence (a new source, a new run result) — name it
     explicitly. Re-litigation without new evidence is a process violation.
1. State the run/decision context in one line (current metric, current bar, open question).
2. Each adviser proposes (three proposals total, one per lens), **from its evolved brief
   in the ledger** (falling back to this file's seed brief only if the ledger has no
   evolved version yet). A proposal that merely restates something already queued or
   already believed must say so — it can still be worth grounding, but it counts as
   validation, not discovery, in the round summary.
3. **Search every proposal — refutation-first.**
   - For each proposal, the FIRST query attempts to refute it: phrase it to surface failure
     modes, negative results, and alternatives ("why X fails", "X negative results",
     "limitations of X", "alternatives to X"), not to confirm it. Supporting searches come
     second, and only if the refutation attempt survives.
   - The proposer formulating its own confirming query is the protocol's known bias; the
     refutation-first rule exists to counter it. One additional fetch is allowed when a
     result is load-bearing and needs a primary source.
4. Arbitrate each proposal to exactly one verdict:
   - **accepted** — becomes a QUEUED single-variable arm or a spec input; never stacked onto
     a running arm. Record the prediction the arm must satisfy, so step 0 can later score
     hit/miss without hindsight fitting.
   - **held** — sound but sequenced behind a pending verdict; say what unblocks it.
   - **vetoed** — name the violated constraint (e.g. banned data source, budget cap,
     replicate-before-invent) or the refuting evidence. A veto is a success of the
     protocol, not a failure.
5. **Log the round** to the project's council ledger (e.g. `data/council.md`): date/context,
   each proposal (and which lens produced it), its refutation query and result, its
   supporting evidence (with sources), its verdict and reason, and — for accepted proposals
   — the scoreable prediction. The ledger carries three standing sections the round must
   keep current: a header with overall and per-lens hit rates, a **"Lens briefs (evolving)"**
   section holding each lens's current brief (the policy under optimization), and the
   round entries themselves.
6. Report to the operator: verdicts first, evidence second, sources linked at the end. If
   all three proposals survived refutation AND all three validated existing beliefs, say so
   plainly — flag the round as low-information rather than presenting unanimity as strength.

## Hard rules

- Proposals inform; the agent decides; the operator owns final runs.
- One accepted proposal = one future single-variable arm. The council never justifies
  stacking changes.
- Project constraints outrank any search result (banned data sources, compute/time caps,
  from-scratch requirements). Cite the constraint when vetoing.
- Every empirical claim in a verdict carries its source. No source, no claim — mark it
  as the thing the NEXT round should search.
- Every proposal gets a refutation-first query before any supporting query. A round with
  zero refutation attempts is invalid — redo the searches, don't ship the verdicts.
- The ledger is read-write: step 0 (reconcile, score, update briefs, check held/vetoed) is
  mandatory, not optional. A round that skips step 0 is a process violation.
- Reward without update is forbidden: a scored miss must edit the responsible lens's brief
  or carry an explicit no-lesson justification. Brief edits are appends and refinements —
  never delete a lens's core question, only sharpen how it's pursued.
- Brief drift guard: if a lens's evolved brief has grown past ~10 lines, consolidate it —
  merge overlapping lessons, drop lessons contradicted by later outcomes. The brief is a
  policy, not a scrapbook.
- If two consecutive rounds produce no accepted or held proposal, widen the advisers'
  framing (adjacent domains, older literature, negative results) before convening a third.
- If two consecutive rounds produce ONLY validations of existing plans (no discovery, no
  veto, no revision), the queries are confirmation-shaped — tighten the refutation-first
  discipline or switch to subagent-isolated lenses before convening a third.