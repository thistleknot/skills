---
name: reasoning
status: active
last_validated: 2026-04-28
description: Reasoning, orientation, and problem-solving protocol. Use when tackling an open-ended problem, design decision, analysis task, architecture question, or any task where the conclusion is non-obvious. Trigger on planning, decomposition, hypothesis evaluation, or multi-perspective analysis.
---
# Reasoning & Orientation

## Eisenhower Filter
Before decomposing, triage:
- **DO FIRST** — Urgent + Important: critical bugs, blocking issues, core functionality
- **SCHEDULE** — Important + Not Urgent: architecture, refactoring, documentation
- **DELEGATE** — Urgent + Not Important: minor fixes, style, non-critical features
- **ELIMINATE** — Neither: over-engineering, unnecessary features, gold-plating

## Perspectives
Before proposing a throughline, evaluate from these angles. Surface the strongest objections before committing.

| Hat | Focus |
|---|---|
| White | Facts only — what do we know, what's missing |
| Yellow | Value, benefit, best-case path |
| Black | Risks, failure modes — intent is to overcome, not just flag |
| Red | Gut check — what feels wrong even if premises hold |
| Green | Alternatives, different approaches |
| Blue | Process — are we solving the right problem in the right order |
| SME | Established best practice for this domain |

Dev-specific lenses: user, PM, security, critic. Apply whichever are load-bearing for the task.

Anticipate rebuttals: identify where your position is weakest before presenting it.

## Problem Solving
**Decompose** before solving: break into independent subproblems, identify dependencies, solve in topological order. State decomposition before implementing.

**Recombine** combinatorially: list available primitives and known patterns, then compose. Apply TRIZ heuristics — segmentation, taking out, local quality, asymmetry, merging, universality, nesting.

**Razors** for hypothesis selection: Occam's (simplest consistent explanation), Hickam's (multiple causes can coexist), Hanlon's (don't attribute to malice what simpler causes explain).

## Reasoning Chain
For load-bearing conclusions, walk three stages:
1. **Deductive:** do premises entail the conclusion? Classify each premise: entailment / neutral / contradictive. False(0) on load-bearing premise collapses chain.
2. **Inductive:** what pattern emerges across validated premises? Identify generalizations. Apply razors to filter.
3. **Abductive:** of remaining hypotheses, which is most plausible? State necessary conditions for the prevailing hypothesis.

## Negative Inference
Isolate by division: working vs broken, logic vs data vs environment, expected vs actual, necessary vs sufficient. Are we forcing a false dichotomy? If so, expand the output space before narrowing. Use as a scalpel — narrow scope before proposing fixes.

## OODA (Integrating Loop)
| Stage | Action |
|---|---|
| Observe | Are necessary conditions met to validate premises? |
| Orient | Do validated premises form a potential conclusion? |
| Decide | Which conclusion has strongest entailment? Formulate alternate hypothesis. |
| Act | Adopt prevailing hypothesis. Implement. |

## ReAct Sequence
Before responding: Observe (prior state) → Plan tools → Execute → Reason over results → Plan response → Respond.
<!-- consolidation:see-also:start -->
## See Also
[[debugging]]  [[react-agent]]  [[agentic_kg_memory]]
<!-- consolidation:see-also:end -->
