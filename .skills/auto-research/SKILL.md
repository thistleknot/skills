---
name: auto-research
description: >
  Digest of the autoresearch and harness-evolution literature: the shared mechanism, the
  acceptance gate, matched-budget counter-evidence, and skill-library governance. Use when
  designing or auditing a self-improving harness loop, judging whether a harness gain beats
  matched-budget sampling, or setting gate, reject-log, and skill-library rules. Trigger on
  "autoresearch", "harness evolution gain", "matched budget", "gate-only split", "library
  drift", or "is this harness gain real".
---

# Crystallized digest — Autoresearch harness evolution

as-of 2026-10-24 · source: retrieved graph evidence for query "autoresearch methodology and harness configuration" (18 arXiv sections, one community: "Agent Execution and Verification Loop")

## Current disposition

- **Mechanism: converged.** Papers agree on one loop: freeze the model, run the harness, cluster failure traces, propose small edits to one declared surface, accept only edits that improve proposer-visible tasks without hurting gate-only tasks, log every decision.
- **Payoff: contested.** Whether the loop beats spending the same budget on more samples is not settled. The one matched-budget study in this set says it does not when no unit-test verifier is available.
- **Commentary gap.** The auto-generated commentary on this retrieval gave three pro-evolution hypotheses and none against, though the counter-evidence was in the retrieved set. Treat its syllogism as one-sided.

## Question

How should an autoresearch loop configure and evolve an agent harness around a frozen model so that accepted edits are real, transferable gains rather than overfit or bought samples?

## Findings

All paper claims are [empirical:cited] to the retrieved section named.

### What gets edited

- (harness) (is) (the non-parametric scaffold around a frozen model: prompts, tools, memory, skills, guardrails, control flow, failure recovery) [observed] — Self-Harness 2606.09498 §3.1; Harness² 2610.14224 §2.1
- (harness) (decomposes into) (declared, file-mounted editable components, 5 to 9 depending on paper) [observed] — AutoDesign 5; MemoHarness 6; Harness² 8 (system prompt, guardrails, memory, skills, tool guidance, scripts, subagents, middleware); HarnessX 9-dimension typed primitives on lifecycle hooks
- (same frozen model) (performs differently under) (different harnesses) [observed] — Self-Harness §1; Rethinking 2607.12227 §1
- (harness tuned for one model) (is often suboptimal for) (another model) [observed] — Self-Harness §1; retained edits differed per backend

### The loop

- (improvement loop) (runs) (execute → cluster failure traces → propose bounded edits → regression-test → accept and merge, or log reject) [observed] — Self-Harness §3; AutoDesign 2608.13560 §3.2; HarnessX AEGIS (Digester, Planner, Evolver, Critic)
- (each proposal) (targets) (one failure mechanism, without replacing the control architecture) [observed] — Self-Harness §3
- (AutoDesign) (restricts each iteration to) (exactly one harness component, for interpretable credit assignment) [observed] — §3.2
- (Meta-Harness) (keeps) (a Pareto frontier over task performance and context cost) [observed] — via SoL-Pi 2609.20519 §4.2
- (SoL-Pi) (searches with) (a broad-to-deep funnel targeting token efficiency, with final held-out eval kept separate) [observed] — §4.2

### The acceptance gate

- (AutoDesign gate) (accepts when) (train objective improves AND dev objective does not decline) [observed] — Algorithm 1
- (gate-only split) (is never shown to) (the proposer) [observed] — Self-Harness §4.1; AutoDesign §3.2
- (rejected edits) (are logged in) (a persistent optimization record, so the next iteration tries something else) [observed] — AutoDesign record L
- (each harness edit) (should carry) (a change contract: component, target failure, predicted gain, invariants, falsifying eval, rollback) [observed] — Code as Agent Harness 2605.18747 §5.2.3 (position paper, not tested)

### Recursion and adaptivity

- (Harness²) (separates) (execution harness from improvement harness; the improvement harness updates after each task from an improvement library) [observed] — 2610.14224 §2.1
- (Harness²) (refines without correctness labels via) (behavioral contrasts: invariant and domain candidates probed against a reference run on the same task) [observed] — §2.2.1
- (Harness² authors) (state that) (contrasts do not verify correctness; stochasticity and shared model bias limit them) [observed] — §2.2.1
- (MemoHarness) (adapts) (the learned global harness once per test case, using dimension-level success/failure experience) [observed] — 2607.14159 §2.1
- (single global harness) (stalls on) (heterogeneous task sets; variant isolation restores steady gains) [observed] — HarnessX 2606.14249 §1
- (proposer) (can be) (meta-learned on held-out performance of the adapted harness) [observed] — 2609.35738 §4.2
- (harness traces) (can feed) (RL training of the model, adding gain over harness-only evolution) [observed] — HarnessX co-evolution

### Where gains land

- (Self-Harness) (improved) (all three backends on both held-in and held-out splits) [observed] — §1, Fig. 4
- (largest relative lift) (went to) (the weakest backend, roughly doubling its pass rate) [observed] — Self-Harness Fig. 4
- (harness-evolution gains) (scale inversely with) (baseline strength; near-ceiling setups gain little) [observed] — HarnessX §1

### Counter-evidence

- (harness evolution) (did not beat) (parallel sampling or sequential refinement at matched budget without unit-test feedback; it averaged slightly below the starting harness) [observed] — Rethinking 2607.12227 Fig. 1
- (per-task harness scaling) (came close to) (parallel sampling under the same protocol) [observed] — Rethinking Fig. 1
- (search/eval task overlap) (inflates) (reported harness gains) [observed] — Rethinking §1; Wang et al. via SoL-Pi §4.2
- (Self-Harness) (does not show) (a matched test-time-scaling baseline in the retrieved sections) [inferred] — may exist in unretrieved parts
- (Self-Harness held-out split) (is) (a slice of a 64-task subset, with no significance test in the retrieved text) [observed] — §4.1

### Library governance

- (unbounded skill accumulation) (degrades) (retrieval quality before task scores show it) [observed] — Library Drift study via 2609.11873 §3.5.3
- (lifecycle management) (uses) (append-only contribution log, capped active set, retirement when contribution fades, a meta-skill for authoring) [observed] — same
- (overly aggressive retirement) (performs worse than) (no governance) [observed] — same
- (filtering skill edits) (beats) (repeatedly rewriting skills from outcomes) [observed] — same
- (HDSO) (admits a skill only after) (control-vs-treatment runs on the same tasks, staged sizes, confirmation on independent tasks) [observed] — same

## Entities

| Name | arXiv / ref | Role here |
|---|---|---|
| Self-Harness | 2606.09498 | Same-model propose/evaluate/accept loop |
| Meta-Harness | Lee et al. 2026b | External proposer over harness code; performance/cost Pareto |
| AHE | Lin et al. 2026 | Observability-driven evolution of file-level components |
| MemoHarness | 2607.14159 | Per-case adaptation from diagnostic experience |
| Harness² | 2610.14224 | Recursive: execution + improvement harness, label-free |
| HarnessX / AEGIS | 2606.14249 | Typed primitives, variant isolation, GRPO co-evolution |
| AutoDesign | 2608.13560 | One component per iteration; train/dev gate |
| SoL-Pi | 2609.20519 | Token-efficiency search, broad-to-deep funnel |
| RRSI | 2609.24972 | Regularized RSI; baseline roster (Meta-Harness, AHE, TTHE, HarnessX) |
| TTHE | Nie et al. 2026 | Test-time harness evolution with agentic judge |
| Rethinking the Evaluation of Harness Evolution | 2607.12227 | Matched-budget test-time-scaling baseline study |
| Code as Agent Harness | 2605.18747 | Change-contract position |
| The Last AI Built by Humans | 2609.11873 | Survey: retention and governance (HDSO, Metis, Library Drift, Tax AI) |
| Learned proposer | 2609.35738 | Meta-learned revision rule |
| Harness Handbook | 2607.13285 | Harness as a software abstraction |
| Benchmarks | — | Terminal-Bench 2.0/2.1, GAIA, ALFWorld, WebShop, τ³-Bench, SWE-bench Verified, PosterBench |

User systems this touches [inferred mapping]:

- **web-council skill** — frozen model plus lens briefs edited by distilled lessons: a Self-Harness-shaped loop on text state
- **playbook.md lessons-learned notes** — an improvement library in the Harness² sense
- **skill-retriever MCP (thistleknot/skills)** — exposed to Library Drift
- **agentic_kg_memory arXiv retrieval** — produced this evidence set and its commentary
- **OpenCode multi-model fleet** — one harness per role and model; edits are model-specific

## Lessons

1. **Price the lottery tickets first.** Every harness-evolution gain needs a matched-budget control: parallel sampling and sequential refinement under the same feedback. Without it, a gain may be extra samples, not a better harness. Backed by: Counter-evidence.
2. **Don't grade your own homework.** Task data plays three roles: proposer-visible, gate-only, final eval. The gate split never reaches the proposer; search never touches the final eval. Backed by: The acceptance gate; search/eval overlap.
3. **Change one variable at a time.** One component per accepted edit, each with a change contract naming its kill condition and rollback. Backed by: AutoDesign; change contract.
4. **First, do no harm.** Accept only if proposer-visible tasks improve and gate-only tasks do not drop. Log every reject with its reason; that log is the CLOSED list the proposer reads. Backed by: The acceptance gate.
5. **Fix the pattern, not the instance.** Propose from clustered failure traces, never from a single failed run. Backed by: The loop.
6. **One size fits none.** Mixed task types stall a single global harness; split variants by task type or adapt per case. Backed by: HarnessX variant isolation; MemoHarness.
7. **A rising tide lifts the smallest boats most.** Expect the biggest lift on weak models and low baselines, little near ceiling. Edits are model-specific, so re-validate on every model swap. Backed by: Where gains land; What gets edited.
8. **Garbage in, garbage out.** The verifier bounds the loop. Without a trustworthy evaluator, evolution can end below where it started. Settle the evaluator before running the loop. Backed by: Counter-evidence; Harness² caveat on contrasts.
9. **A cluttered toolbox slows the work.** Cap the skill/lesson library, keep an append-only contribution log, retire by measured contribution, filter edits instead of rewriting. Over-pruning also hurts. Backed by: Library governance.
10. **Count the bill.** Track token/context cost as a second objective next to pass rate. Backed by: Meta-Harness Pareto; SoL-Pi.

## Open questions

- **Does harness evolution beat test-time scaling on held-out tasks?** Settle with: same model, budget, and feedback; arms = parallel sampling, sequential refinement, harness evolution, per-task harness scaling; fixed held-out split; with and without verifier access. Kill condition for "evolution helps": evolution ≤ parallel sampling on held-out in both feedback settings. Lean: unproven; the only matched study says no without unit tests.
- **Are label-free behavioral contrasts trustworthy?** Settle with: choose edits by contrast vs by labels, score both on a labeled held-out set. Lean: the authors say contrasts do not verify correctness.
- **Does updating the improver help later tasks?** Harness² tests this in a figure that was not retrieved. Lean: unverified here.
- **Same-model proposer vs stronger external proposer: which edits transfer better?** No head-to-head in the retrieved text.
- **Is pass-rate non-regression enough as a gate?** Code as Agent Harness argues no for safety, permissions, and cost; no tested alternative gate retrieved.
- **How large are the Self-Harness gains?** Small held-out split, no significance test, no test-time-scaling baseline in the retrieved text. Read the full paper before citing magnitudes.

## Routed deltas

Staged for skill-wiki (not applied):

- **web-council** — add a gate-only split for lens-brief edits; add a matched sampling control arm; cap and retire brief lessons by measured contribution. [inferred from the skill's description; check against its full SKILL.md]
- **Retrieval commentary generator (agentic_kg_memory)** — require at least one hypothesis that opposes the obvious answer, and surface contrary passages already in the evidence set. [observed: this commentary had none]
- **playbook.md lessons-learned** — apply Library governance: cap, contribution log, retire. [inferred]

Pipeline check for agentic_kg_memory:

- On this query all three fused seeds had community = None and term_affinity = 0, so community reweighting changed nothing, and the one detected community covered all 18 sections. Check whether reweighting is a no-op on other queries before keeping it as a stage. [observed]

## Provenance

- Evidence: retrieved passages only; papers were not re-fetched. Paper claims are cited to the retrieved section; mappings to user systems are [inferred].
- Crystallized 2026-10-24 into the "research" project.