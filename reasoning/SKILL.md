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

---

## Map-Reduce Grouping

Use when the input is flat, overlapping, or mixed. Skip when the domain already has a fixed structure you need to follow.

1. **Start with leaves** — the small, concrete items you notice before you know the category names
2. **Clean duplicates** — split bundled ideas apart; normalize names
3. **Group leaves** — cluster items that belong together into candidate branches
4. **Name the branches** — based on what the grouped leaves have in common
5. **Handle overlaps** — if a leaf belongs on more than one branch, say so; never force it into one
6. **Handle gaps** — missing leaves reveal unmodeled dimensions; missing branches reveal unlabeled territory
7. **Grow nested structure** — if bigger patterns appear, nest branches under them
8. **Answer from the structure** — not from the raw flat list

---

## Schema Translation (map-reduce cross-system mapping)

A specialized application of map-reduce: first *extract* each schema independently (map phase — reduce a corpus of variants down to its stable dimension set), then *translate* across systems (reduce phase — collapse A→B mappings into a schema contract). Do not map directly between systems — extract each schema first, then translate.

### Pattern

1. **Build schema A** via 3-way diff: compare a base against three derived variants. The intersection of differences is the stable dimension set; the union is the full record set.
2. **Build schema B** the same way using its own three variants.
3. **Map A → B dimensions**, handling:

   | Relationship | Example |
   |---|---|
   | 1:1 rename | Advances → Advances |
   | Subtype | Wonders are Improvements cell index range 68+, not a separate dimension |
   | Gap | Leaders (Civ2) → no CTP2 equivalent |
   | Many-to-one | Events (Civ2 scripting) → SLIC (CTP2) |
   | B-only | Tile Improvements (no Civ2 source; needs proxy art) |

4. **Translate records through the schema contract** — never ad-hoc LLM improvisation per record.

**Why 3-way?** Two variants can share a coincidental overlap. Three independent variants triangulate which structural differences are intentional vs. noise.

### Game modding example: Civ2 → CTP2 total-conversion scenario

**Schema A (Civ2)** — from diffing base Civ2 (Test of Time edition) against MoMJR, Mars, and Heroes of Might and Magic:
- Stable dimensions: Units, Advances, City Improvements, Terrain, Governments, Orders, Leaders
- `Improvements.bmp` encodes both Improvements *and* Wonders in one grid — split point is the `@IMPROVE` entry count (index 0–N = improvements, N+1–end = wonders); do not split by pixel content
- Caravan commodities / trade data → maps to Goods
- Events (Civ2 scripting) → SLIC (documented by extracting file: class/function headers + constant labels, then letting an LLM transpose the logic)
- Civilopedia / label text → Concepts

**Schema B (CTP2)** — from diffing AE mod against LOTR, Cradles, and Ages of Man:
- Confirms Wonders as a subtype of Improvements (same entity type, different cell-index range)
- New dimension absent from Civ2: Tile Improvements (needs proxy TGA mappings)

**What unlocked everything:** dropping manual LLM patching in favor of a formal schema contract layer. Once dimensions and records were defined, image parsing, CLI patching, and schema translation could all route through a single Python wrapper — auto-ingesting a total conversion mod as a scenario.

### Uncertain mappings

Not every dimension has a clean translation. If the relationship is unclear (e.g., Civ2 Events may be epoch/age-tied rather than general scripting), flag it as uncertain in the schema contract rather than forcing a premature mapping. Classify it as:

- **Deferred** — translation logic is unknown; needs more evidence from the target mod's actual usage
- **Conditional** — depends on a structural question (e.g., "are Events purely scripted triggers, or do they map to CTP2 Ages?") that must be answered before records can translate

Don't unblock downstream translation on a deferred mapping — mask it out until the mapping is resolved.

### Mask / inherit pattern

When a dimension exists in the source but has no equivalent in the target:

1. **Mask it** — exclude those records from the active translation pass; they don't crash anything because they're simply absent
2. **Inherit non-contradictory records** — if the dimension partially survives (e.g., some Leader traits map to government effects), pull the genre-compatible records through and mark the rest masked
3. **Never drop silently** — masked records must be tracked in the schema contract so a future pass can revisit them when a target analog is found or invented

"Non-genre-contradictory" means: the record wouldn't break the fiction of the target game if it appeared there, even if the target game has no native concept for it.

### Incremental validation

Translate and test one record per dimension first before committing the whole dimension. Sequence:

1. Enable 1 record for dimension D → load-confirm (game starts, no crash, record renders correctly)
2. Enable the full dimension → load-confirm again
3. If the full-dimension load fails, halve the enabled set and bisect to isolate the bad record
4. Once the dimension is stable, codify it into the CLI/UI wrapper as a locked translation unit

The CLI wrapper is the terminal artifact: every stable dimension becomes a committed entry point so the tool accumulates coverage incrementally. When all dimensions are codified, the wrapper can auto-ingest a new source mod without any manual LLM intervention per record.

<!-- consolidation:see-also:start -->
## See Also
[[agentic_kg_memory]]  [[skill-wiki]]  [[memory-bank]]
<!-- consolidation:see-also:end -->
