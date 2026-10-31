---
name: recursive-harness-self-improvement
description: >
  Procedure for evolving an agent harness (hooks, skills, middleware, control flow around a
  frozen model) from its own failure traces, with a noise-band and held-out gate on every
  edit. Use when proposing harness, hook, or skill edits from traces, when gating a harness
  change, or when asked to make a harness improve itself. Trigger on "recursive
  self-improvement", "harness evolution", "improve the harness from failures", "gate this
  harness edit", or "held-out check for a harness change".
digest: recursive-harness-self-improvement
date: 2026-10-23
status: crystallized (literature-sourced; no local experiment run)
mode: retrieved-context
supersedes: none
route: agentic_kg_memory (digest + triplets), skill-wiki (procedural delta below)
---

# Digest: Recursive Self-Improvement of Agent Harnesses

## Current implementation disposition

CURRENT 2026-10-24: the offline-first runner is implemented in ~/.harness/eval/rsi.
It supports mine, dry/default run, explicit budgeted execute, verdict, decisions,
and acceptance-gated promotion/export. Implementation is not an effectiveness
result; no model campaign has run. Memory uses the scoped caller contract in
agent-long-term-memory. Prior literature findings below remain supporting evidence.

## 1. Question

How should an agent harness (prompts, tools, memory, middleware, control flow around a frozen model) be designed so it improves itself, and the improving process improves too, without overfitting, regressing, or drifting?

## 2. Findings

Readiness check: the literature has converged on a shared loop and a shared failure mode, so the chain is distillable. Single-source numbers stay in the papers; only direction is kept here.

### 2a. Shared loop (every system below instantiates it)

```
run harness -> collect traces + outcomes
  -> mine/cluster failures (evidence)
  -> propose bounded edits (each tied to a failure mechanism)
  -> validate (regression, held-out, repeat runs)
  -> accept only non-regressing edits -> new harness
  -> log decision + evidence (rejections are data too)
```

### 2b. Systems, by what they change about the loop

| System | Distinguishing move | Improver itself updated? |
|---|---|---|
| Self-Harness | Same model proposes edits to its own harness; acceptance = non-regression on held-in + held-out | No |
| Meta-Harness | Proposer reads full source, scores, traces of all prior candidates via filesystem (no lossy summaries) | Retains search experience |
| AHE | Component = file; per-edit manifest of predicted fixes/regressions, checked next round, failed edits reverted; git commit per round | No |
| TTHE / HarnessX | Test-time evolution on unlabeled batches / typed modular primitives | No |
| DGM | Archive of agents, open-ended branching, empirical (not proof) validation | Coding skill doubles as self-modification skill |
| Hyperagents (DGM-H) | Meta-level modification procedure is itself editable | Yes, and gains transfer across domains |
| Harness 2 | Label-free; contrastive Propose-Probe-Compose per task, then an "improvement harness" library updated across the task stream | Yes (library of adopted harnesses + lessons) |
| RRSI | Regularizes the loop: annealed edit budget, leakage screening, noise-band acceptance, complexity-aware acceptance, pruning | Controls only |
| Gated QD (HarnessBank) | Gene-bank grid by component x failure type; validity / activation / significance gates | Archive diversity |
| DarwinX | Population + recombination; preserve-and-extend selection (gain somewhere, bounded regression elsewhere) | Archive of lineages |

### 2c. Two recursion levels (Harness 2 framing, generalizes the table)

- Level 1 (task-level): improve the execution harness for the current work.
- Level 2 (harnessing-level): improve the thing that does Level 1 (retained components, lessons on when/why they worked). Hyperagents goes one step further and makes the meta procedure editable code.

### 2d. Failure modes that recur across papers

- Evolve-set overfitting: reused evaluation set -> gains on it, not on out-of-distribution tasks (RRSI documents this in published baselines).
- Noise-chasing: one lucky run promoted (Gated QD adds significance gates for this).
- Complexity accretion: score up on evolve set, mechanism unchanged, tokens up.
- Search collapse / path dependence: single lineage, early edits dominate (DGM archive, DarwinX population).
- Cross-task interference: a fix for one task family breaks another.
- Model specificity: harnesses evolved for one model often lose value on another; cross-family transfer is inconsistent across papers.
- Self-prediction asymmetry (AHE): the loop predicts its fixes far better than its regressions, so regressions slip through unless measured.
- Non-additive edits: stacking individually good edits gives diminishing returns.
- Metric gaming: self-modifying agents have been observed cheating on the objective (DGM reports); one DarwinX trial showed answer lookup.
- Same-suite optimization and scoring measures an upper bound, not generalization.

### 2e. What actually drove gains (direction only)

- Gains concentrated in tools, middleware, and long-term memory/skills (verification and artifact-contract skills); system-prompt-only edits were weak or negative in AHE.
- Small, auditable, targeted edits beat broad rewrites.
- Richer access to raw history for the proposer beat compressed feedback (Meta-Harness).

### 2f. Contested

- Cross-model transfer: AHE and RRSI report evolved harnesses helping other base models; HarnessBank reports gains often lost or reversed when transplanted; DarwinX's procedure fell below a neutral baseline on one base model.
- Label-free vs labeled: Harness 2 reports gains from behavioral contrasts alone; RRSI and Gated QD argue that noisy or reused feedback is the main source of false gains, which label-free contrast does not remove.

## 3. Entities

- Concepts: harness, execution harness vs improvement harness, task-level vs harnessing-level recursion, change contract, acceptance rule, regression suite, evolve/held-in/held-out split, archive, gene bank, leakage screening, noise band.
- Systems: Self-Harness, Meta-Harness, AHE, TTHE, HarnessX, Harness 2, RRSI, HarnessBank (Gated QD), DarwinX, DGM, Hyperagents (DGM-H), STOP, Harness-Zero, harness learning (RL-trained proposer), NLAH/IHR.
- Surveys: Code as Agent Harness (change contracts, canary, rollback); The Last AI Built by Humans (selective retention, library drift, governed deployment).
- Benchmarks: Terminal-Bench 2.x, SWE-bench Verified, Polyglot, WorkBuddy, JobBench, Harvey LAB, EngDesign.

## 4. Triplets (for agentic_kg_memory)

- [Self-Harness] --proposes edits to--> [its own harness] ; gate = non-regression on held-in and held-out
- [Meta-Harness] --gives proposer--> [source + scores + traces of all prior candidates]
- [AHE] --pairs each edit with--> [predicted fixes/regressions manifest] ; failed edits --are--> [reverted]
- [Harness 2] --updates--> [improvement harness] --after--> [each task]
- [Hyperagents] --makes editable--> [meta-level modification procedure]
- [RRSI] --counters--> [evolve-set overfitting, noise-chasing, complexity accretion]
- [DarwinX] --admits child if--> [gains somewhere AND regressions bounded]
- [HarnessBank] --screens candidates with--> [validity, activation, significance gates]
- [Library drift] --degrades--> [retrieval quality of unbounded skill libraries]
- [Evolved harness] --is--> [model-specific] (partial transfer only)

## 5. Lessons (generalized, reusable)

1. Treat every harness edit as a code change to a safety-critical runtime: component, target failure, predicted effect, preserved invariants, falsifier, rollback. (Matches this user's spec-first contract.)
2. Edit one component per candidate late in the search; bundle only early. Attribution beats speed once gains get small. (Annealed edit budget.)
3. Accept on stability, not on best-so-far: candidate must beat the measured noise band, and repeated runs beat single runs.
4. Gate three ways before trusting a pass: the edit fired (activation), the infrastructure was clean (validity), and the gain is statistically real (significance).
5. Always hold out a split the proposer never sees; never score the final claim on the split used to select.
6. Screen diffs for benchmark-specific content before evaluating (leakage critic).
7. Charge complexity: an edit that raises cost must buy measured gain; prune components with no gain over a window.
8. Keep rejected edits as negative evidence; log provenance so the next proposer does not retry them.
9. Keep an archive or population, not one lineage; accept children that preserve prior wins while adding new ones.
10. Give the proposer raw traces, not only summaries; summaries are for navigation, not for evidence.
11. Cap and age skill libraries; retire entries whose measured contribution fades; over-aggressive retirement is also harmful.
12. Do not assume a harness transfers across models; re-run the loop per model or test transfer explicitly.
13. Improver-level recursion is where compounding lives, but it is also where Goodhart bites hardest: lock evaluator and benchmark protocol while the improver changes.
14. Humans keep final acceptance for production harnesses; pass-rate non-regression alone is too weak a gate for high-stakes changes.

## 6. Open questions

- Does label-free (contrastive) improvement hold up where behavior differences do not track correctness (shared model bias)?
- How to predict regressions, not just fixes (AHE shows this is the weak side)?
- Does improver-level recursion keep compounding past a few rounds, or saturate into the evolve set?
- Safety: guardrails for objective gaming and permission-boundary erosion are incomplete in every surveyed prototype.
- Gains on same-suite evaluation vs. true held-out are mixed in reporting; independent replication is thin.
- Interaction between weight updates and harness evolution is unstudied in the surveyed work (RRSI scopes to frozen models; harness-learning RL trains the proposer).

## 7. Routing

| Artifact | Destination |
|---|---|
| This digest + triplets | agentic_kg_memory (not reachable from this session; file is the hand-off) |
| Procedural delta: add "harness-evolution gate checklist" (lessons 1-8) to the user's dev-harness / playbook workflow | skill-wiki staged draft |
| Continuity note | none; no live task state here |

## Provenance

Retrieved context (graph RAG): Harness 2, Self-Harness, RRSI baselines, Code as Agent Harness, The Last AI Built by Humans, harness learning, NLAH, Harness-Zero.
Web-filled gaps: Meta-Harness (arXiv 2603.28052), AHE (2604.25850), RRSI (2609.24972), DGM (2505.22954), Hyperagents (2603.19461), Gated Semantic QD (2607.13683), DarwinX (2608.07545). Source tiers: retrieved-context findings are [observed] at retrieved-chunk tier; web-filled findings are [observed] at fetched-summary tier (small-model summaries of abstracts/full text), not primary text. Section 2a loop and section 5 lessons are [inferred] syntheses. Not independently replicated.

## Procedure: harness-evolution gate

<!-- Added 2026-10-23 for the ~/.harness round-01 campaign. Body above is unchanged. -->

Literature grounding runs before any candidate is written and is never a gate input. Query the graph's `GET {graph}/search?query=…&k=5&mode=hybrid` (default `http://192.168.3.122:8780`, env `ARXIV_RAG_API_URL`). `/search` runs a local embedder and cross-encoder and makes no LLM call; `/agent` does, so it stays out of the loop. Run two phrasings per failure mechanism and one opposing-hypothesis phrasing ("X does not beat Y at matched budget"). Require at least two distinct `doc_id`s; if one paper fills all results, rerun with `k=10` and dedupe. Quote each cited passage and check it supports the claim, because rank 1 is not evidence. Log every query and its `doc_id#section_idx` hits to the round's `evidence.jsonl`, including hits that argue against the candidate. If the graph is unreachable, record grounding as NOT TESTED and proceed; the gate does not depend on it.

Gate every candidate edit in this order. A failed gate is a finding, not a retry.

1. Change contract: component, target failure class, mechanism, predicted fixes and breaks, preserved invariants, falsifier, rollback command. No contract, no run.
2. Validity: every battery item returns non-empty output with no error. Otherwise the round is NOT TESTED.
3. Activation: the edit fired on target items. Otherwise NOT TESTED.
4. Target held-in: fixes ≥5 with 0 breaks, or fixes ≥7 with ≤1 break, AND net fixes above the A/A noise band. Why these bars: at n=8 a paired sign test gives 4-0 p=0.0625 (cannot pass), 5-0 p=0.031, 7-1 p=0.035.
5. Guard classes: breaks ≤ their A/A band.
6. Gate-only held-out: net ≥0 and drop no larger than its A/A band. Never shown to the proposer. Passing it is not certification: one round, 4 items.
7. Report Δtokens and Δseconds. Accept is the operator's call.
8. Matched budget: beat baseline-k on net fixes beyond the A/A band. baseline-k = best-of-k by checker, with k = ceil(candidate tokens per item ÷ baseline tokens per item). Failing this means the gain is bought samples: reject and log it as such.
9. Reject log: append every reject (candidate, gate failed, numbers) to the round's `rejects.jsonl`. The proposer reads it as the CLOSED list.
10. Library: a candidate adds at most one skill per round. Log its contribution append-only. No retirement in round 1.

Memory-stage edits (retrieval, scoping, consolidation, session-start recall) use `C:\Users\user\.skills\agent-long-term-memory\SKILL.md` as their component gate. A memory stage must first beat no-memory and BM25-over-raw at matched reader and budget (its R2). A cheaper fix that removes the stage counts as a candidate.

Payoff is contested. One matched-budget study found harness evolution did not beat parallel sampling without unit-test feedback. Read `C:\Users\user\.skills\auto-research\SKILL.md` (Counter-evidence) before claiming any gain.

Evaluator lock: the battery and checkers are hashed. Results with different hashes are never compared. Winners are re-run each round, not compared to remembered numbers.
