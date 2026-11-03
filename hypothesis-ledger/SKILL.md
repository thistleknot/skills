---
name: hypothesis-ledger
description: >
  Track multiple competing, evolving hypotheses at the todo tier. Each hypothesis is a
  statement (the "description") with premises (the key-values) that get validated or
  refuted as evidence accrues, until the hypothesis reaches a disposition — accepted,
  refuted, superseded by a rival, or parked. Encodes Analysis of Competing Hypotheses
  (discriminating evidence beats confirming evidence) plus premise→conclusion entailment
  (a hypothesis is supported only when its required premise set is fully entailed).
  Use when a debugging session, research thread, or investigation has more than one live
  theory and you need to iterate them to a defensible verdict instead of anchoring on the
  first guess. Upstream: hypothesis-forge (forms the hypothesis). Downstream: agentic_kg_memory
  throughlines / memory-bank (an accepted disposition promotes to durable belief).
tier: L1
status: staged
last_validated: 2026-07-03
validation_method: design
---

# Hypothesis Ledger

A working-tier tracker for **several hypotheses at once**. Each is a running account: a
claim, the premises it depends on, the evidence for and against, and a lifecycle that ends
in a disposition. It is to hypotheses what `todo` is to tasks — but the unit of progress is
*evidence weighed against premises*, not *work done*.

## When to use

- A debugging session where the root cause is unclear and 2+ candidates are live
- A research or design question with competing explanations you must adjudicate
- Any investigation where you risk anchoring on the first plausible theory
- After `hypothesis-forge` hands you one or two candidates and you need to run them to ground

## When NOT to use

- A single obvious hypothesis with a one-step test → just test it
- Forming the hypothesis from a vague problem → that is `hypothesis-forge`
- Tracking *work items* → `todo`. A ledger entry is a claim under test, not a task.
- Producing structured judge findings over one artifact → `checklist`
- Persisting a settled conclusion → promote it out (see Promotion, below)

---

## Core model

Three nested records. Keep premises atomic — one claim each — so evidence binds cleanly.

```
Hypothesis                          # the "todo": a description with key-values under it
  id            str
  statement     str                 # the claim / disposition under test
  status        active | accepted | refuted | superseded | parked
  standing      0.0..1.0            # rolled up from premises + un-rebutted contrary evidence
  premises      [Premise]           # the key-values beneath the description
  disposition   Disposition | null  # set only on a terminal status
  superseded_by id | null           # the rival that beat this one
  supersedes    [id]                # rivals this one beat
  history       [Event]             # APPEND-ONLY; never rewrite

Premise
  key           str                 # short handle, e.g. "timing", "null-deref"
  claim         str                 # atomic sub-claim
  necessity     required | supporting   # required = must hold for entailment
  state         open | supported | refuted | assumed | contested
  evidence      [evidence_id]

Evidence                            # one shared pool; a datum can bear on many hypotheses
  id            str
  observation   str
  polarity      supports | contradicts | neutral
  bears_on      [{hypothesis_id, premise_key}]
  discriminates bool                # does it distinguish RIVALS, or merely confirm one?
  strength      weak | moderate | strong
  source        str
```

### The entailment rule (what "supported" means)

A hypothesis is **fully entailed** — and only then eligible for `accepted` — when:

1. every `required` premise is `supported`,
2. no `required` premise is `refuted` or `contested`, and
3. the contrary-evidence pass has run and every discriminating contradiction is rebutted.

`supporting` premises raise `standing` but are never load-bearing for entailment. A single
refuted `required` premise collapses the hypothesis — it must be **revised** (reword the
premise/hypothesis) or the hypothesis **abandoned**. Partial support keeps it `active`.

---

## Lifecycle

```
        ┌─────────── revise (reword statement / add / split / drop premises) ──────────┐
        v                                                                               │
   propose ──► decompose ──► gather evidence ──► evaluate ──►(loop)                      │
     │            (premises)      (bind to        (update premise                        │
     │                            premises)        states, standing) ───────────────────┘
     │                                                   │
     │                                                   ├─ required set fully entailed ─► ACCEPTED
     │                                                   ├─ required premise refuted ─────► REFUTED
     │                                                   ├─ a rival dominates the ACH ─────► SUPERSEDED (→ rival)
     └─ fork a rival at any time (ACH) ──────────────────┴─ evidence stalls / out of scope ► PARKED (revivable)
```

**Operations**
- **propose** — create a hypothesis from a hunch or a `hypothesis-forge` output.
- **decompose** — list the `required` premises whose conjunction would entail it. This is the
  "fully entailed set" you are trying to close. Add `supporting` premises as corroboration.
- **gather** — attach evidence to premises with an explicit `polarity`. Deliberately seek
  *disconfirming* evidence for your leading hypothesis (the contrary pass).
- **evaluate** — update premise `state` from its evidence; recompute `standing`.
- **revise** — reword the statement or restructure premises when evidence reshapes the theory.
  Append the change to `history`; never silently rewrite.
- **fork** — spawn a rival hypothesis. Rivals share the evidence pool (see ACH).
- **close** — set a terminal status + `Disposition{verdict, rationale, entailed}`.

The only non-terminal status is `active`. Every entry should be moving toward a disposition;
an entry with no premise-state change across several evaluate passes is a smell — park it or
kill it.

---

## Competing hypotheses — the ACH matrix

Track rivals in one **evidence × hypothesis** matrix. Score each cell:

|                         | H1 | H2 | H3 |
|-------------------------|----|----|----|
| E1 (discriminating)     | ✓  | ✗  | ✗  |
| E2 (discriminating)     | ✗  | ✓  | –  |
| E3 (merely confirming)  | ✓  | ✓  | ✓  |

`✓` consistent · `✗` inconsistent · `–` not applicable.

**Heuer's rule — rank by fewest inconsistencies, not most confirmations.** Confirming
evidence (E3) is nearly worthless because it fits everything; the work is in the
**discriminating** rows. A rival with many `✓`s but one un-rebutted `✗` on a *required*
premise is weaker than a rival with fewer `✓`s and zero inconsistencies. When one hypothesis
is inconsistency-free and its required set is entailed while every rival carries a live `✗`,
mark the rivals `superseded_by` it. Prefer evidence that *splits* rivals over evidence that
*raises* one.

---

## Evidence discipline

- **Polarity is mandatory.** Every datum is logged as supports / contradicts / neutral for a
  named premise. "I found something relevant" is not a ledger entry.
- **Run the contrary pass before accepting.** Mirror `hypothesis-forge`'s adversarial step:
  dedicate a search to refuting your leader. Confirmation bias is the default failure mode.
- **Weight by discrimination, then strength.** A `strong`+`discriminates` datum moves the
  ledger; a `strong` but non-discriminating datum barely does.
- **Assumed ≠ supported.** A premise you are taking on faith is `assumed`; it caps `standing`
  and must be flagged in the disposition if it was never actually tested.

---

## Storage & rendering

The record model is storage-agnostic. Pick the lane that fits the run:

- **Per-investigation JSON/JSONL** (`hypotheses.json`) — canonical, diffable, tool-friendly.
- **Markdown block** for a session or a `memory-bank` file — human-readable rendering:

```markdown
### H2 — "the 0.0.0.0 host is a bind addr the client can't dial"   [active · standing 0.8]
- [x] required · client-connect-fails: py client raised ConnectError to 0.0.0.0   (E1 strong ✓)
- [x] required · server-binds-ok: curl 127.0.0.1:11434 returns 200               (E2 strong ✓)
- [ ] required · fix-holds: switching client to 127.0.0.1 succeeds               (open)
- rival: H1 "ollama is down" — superseded (E2 ✗ against it)
```

- **SQLite / the `todo` store** when you want cross-session querying — one row per hypothesis,
  premises + evidence as child tables. Treat it as the todo skill's evidence-bearing sibling.

Whatever the lane: `history` is append-only (same rule as `memory-bank`).

---

## Promotion — where a disposition goes

A ledger is **working memory**; do not let a settled verdict die in it.

- **accepted** → promote the disposition to durable belief: a `memory-bank` system-pattern
  (if cross-project) or an `agentic_kg_memory` **throughline** (the durable, Q-scored form of
  exactly this "competing conclusions" model). A one-line worked-out result can also go to the
  Chroma log via `mem log` and earn promotion by recall.
- **refuted / superseded** → keep the disposition + rationale so the dead theory is not
  re-litigated; this is a lesson-learned, not a deletion.
- **parked** → leave revivable with the blocking gap named.

---

## Anti-patterns

- **Anchoring** — one hypothesis, no rivals. If you can't name a competitor, you are not
  analyzing, you are confirming.
- **Confirmation stacking** — piling up `✓` confirming evidence while ignoring the
  discriminating rows.
- **Silent rewrite** — editing a statement or premise without a `history` event.
- **Zombie entries** — `active` forever with no premise-state movement. Park or kill.
- **Fat premises** — a premise bundling several claims so evidence can't bind cleanly.
  Split it.
- **Accepting on corroboration** — declaring victory before the required set is entailed and
  the contrary pass has run.

---

## Minimal output contract

When using this skill, report:
- the live hypotheses and each one's status + standing
- which premise states changed this pass, and the evidence that moved them
- for any close: the verdict, whether the required set was entailed, and the rationale
- the current ACH leader and which discriminating evidence would most change the ranking

<!-- consolidation:see-also:start -->
## See Also
[[hypothesis-forge]]  [[agentic_kg_memory]]  [[checklist]]  [[reasoning]]  [[causal-inference]]  [[todo]]  [[uncertainty-quantification]]
<!-- consolidation:see-also:end -->
