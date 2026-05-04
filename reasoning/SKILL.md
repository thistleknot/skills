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

## Latent Knowledge Activation
Before formalizing, activate domain knowledge that may already be available but not
yet surfaced explicitly. This goes hand in hand with the latent-knowledge prompt
sections in `AGENTS.md` / `copilot-instructions`.

- What do I know about this domain that was not explicitly mentioned?
- What deeper patterns or principles connect to this question?
- Which concepts from adjacent domains are relevant?
- What unstated implications follow from what I already know?
- What contradictions or tensions exist in this knowledge space?
- What parties interact and how (entities <-> predicates)?
- What were relevant conditions prior to this point?
- How would I explain this to someone with no background knowledge?
- If I were to create a knowledge graph, what nodes would be connected?

Use this before decomposition when the user gives a partial prompt, assumes shared
context, or is asking about a domain with hidden structure.

## Map-Reduce Grouping
Before formalizing, when the domain is messy or unclear:

1. List the ground-level ideas that come to mind first.
2. Start with the leaves: the small, concrete items you notice before you know the category names.
3. Then identify the branches: the larger groups or dimensions those leaves belong to.
4. Clean up duplicates and split apart ideas that were bundled together.
5. Group leaves that belong together.
6. Name the branches based on what the grouped leaves have in common.
7. If bigger patterns appear, grow the branches into a nested structure.
8. Note overlaps, outliers, and missing pieces, then refine the structure.
9. If a leaf belongs on more than one branch, say so instead of forcing it into one place.
10. Answer from the structure you built, not from the raw list.

Use this when the input is flat, overlapping, or mixed together. Skip it when the
domain already has a fixed structure you need to follow.

### Top-down Mode
Use this when the material is too large, partially lost, or easier to understand
from its governing structure than from its fragments.

- Review the whole first, or the largest surviving slice.
- Identify the core concepts, constraints, and load-bearing items.
- Rank them by structural importance.
- If the system is damaged, reconstruct the conceptual skeleton from breadcrumbs:
  artifacts, interfaces, assumptions, decisions, and outputs.
- Backfill details only after the trunk is stable.
- Remap the material across useful dimensions such as dependency, function, risk,
  chronology, or abstraction.
- Separate observed structure from inferred reconstruction.
- Refactor from the ranked map, not from raw sprawl.

### Statistical Partitioning
Use this when the space is measurable and you need principled boundaries for
chunking, review, or refactoring.

- Measure a feature that may reveal structure.
- Choose a center that matches the distribution.
- Prefer median for skewed, heavy-tailed, or noisy data.
- Estimate spread with a robust statistic.
- Prefer MAD when outliers would distort standard deviation.
- Use the median as a first partition.
- It provides a balanced split and a stable zoomed-out view of the space.
- Derive candidate boundaries from center and spread.
- Under roughly normal assumptions, `1.4826 * MAD` gives a sigma-like scale.
- Under strong skew, transform first, then estimate boundaries in the transformed space.
- Define the decision class before choosing the cutoff.
- Typical range, anomaly band, chunk boundary, and hard exclusion need different thresholds.
- Validate against the actual task.
- Keep the partition only if it improves structure, chunking, or recovery.
- Do not force this method where the shape disagrees.
- Multimodal or categorical structure may require clustering, factor analysis, or explicit grouping instead.

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
