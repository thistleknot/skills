---
name: crystallization
description: >
  Distill a completed work chain into a durable digest page plus reusable
  lessons: the downstream crystallization step that turns finished work into
  a reusable artifact organized around a clear question. Use when a research
  thread, debugging session, comparison, or multi-turn analysis has a clear
  question and answer that should outlive the session. Cross-reference:
  `skill-wiki` routes procedural promotion decisions; `agentic_kg_memory`
  ingests the resulting digest and facts.
metadata:
  status: active
  last_validated: 2026-05-09
  validation_method: session
---

# Crystallization

## When to Use

Use this skill when:

- a research thread has converged and the conclusions should become a durable digest
- a debugging session produced reusable lessons rather than just a one-off fix
- a comparison or analysis task reached a stable answer with named tradeoffs
- a multi-turn work chain has a clear question, findings, and unresolved edges that should outlive the session

Do **not** use this skill when:

- you are filing a single answer back into memory -> use the query write-back path in `agentic_kg_memory`
- you are compressing a generic activity log without a load-bearing question -> use session compression / continuity artifacts instead
- you are promoting or superseding a skill contract directly -> route the procedural delta through `skill-wiki`
- the outcome is still unverified or speculative

---

## Scope Boundary and Paired Skills

This skill owns the **distillation protocol** for completed work chains.

Completed exploration is valid source material here. A debugging thread,
research pass, root-cause analysis, or design exploration should be treated
like any other source artifact once it has a real question and a stable
outcome.

It owns:

- deciding whether a work chain is crystallization-ready
- the canonical digest shape: question, findings, entities, lessons, open questions
- conversion of a completed work chain into durable artifacts
- routing the resulting artifacts to the correct downstream surface

It does **not** own:

- skill promotion gates, staged drafts, or supersession workflow -> `skill-wiki`
- semantic graph storage, page ingestion, triplet reinforcement, or throughline updates -> `agentic_kg_memory`
- project continuity, todo tracking, or session resumability -> `memory-bank` / `continuity-log` / `todo`

---

## Core Principles of Compounding Crystallization

- **Exploration as a first-class source**: treat completed engineering loops as
  evidence-bearing inputs, not disposable session exhaust
- **Continuous value compounding**: convert transient operational knowledge
  into durable digest pages plus reusable lessons
- **Closed-loop feedback**: let downstream owners ingest the digest and its
  extracted facts so future work starts from reinforced or challenged claims
  instead of rediscovering the same answer from scratch

---

## Crystallization Protocol

1. **Verify the chain is complete enough to distill.** If the outcome is unverified, still changing, or blocked on a load-bearing unknown, stop. Crystallization of noise is worse than missing memory.
2. **Name the driving question.** State the original intent in one sentence. If the work chain has no stable question, it is probably session compression, not crystallization. This is the **intent** anchor.
3. **Normalize the findings.** Convert conclusions into durable claims, triplets, or structured bullet facts rather than chronology. This is the **discovery** anchor.
4. **List the relevant entities and artifacts.** Files, systems, concepts, datasets, tools, or people touched by the chain should be explicit so the digest can be linked later. This is the **ecosystem** anchor.
5. **Extract lessons.** Pull out reusable decision rules, anti-patterns, and boundary conditions that should survive the specific instance. This is the **heuristic** anchor.
6. **State open questions.** Capture what remains unresolved so future work starts from the real frontier instead of a fake sense of closure.
7. **Route the artifacts.** Send semantic facts and digest pages to `agentic_kg_memory`; send reusable skill-contract deltas to `skill-wiki`. Save each extracted lesson to the **lesson store** with initial confidence 0.6 (fingerprint-dedup'd on content — if a matching lesson exists, reinforce: `confidence += 0.1 × (1 − confidence)` rather than creating a duplicate).

The four anchors are the minimum stable extraction skeleton for completed
exploration threads:

- intent
- discovery
- ecosystem
- heuristic

---

## Output Artifacts

A crystallization pass produces one or both of these:

- **Digest page** — a named, referenceable work-chain artifact containing question, findings, entities, lessons, and open questions
- **Standalone facts / lessons** — extracted claims or decision rules that can be filed independently of the full digest

The digest is the readable compiled artifact. The extracted facts and lessons
are the distillate that downstream owners may use to strengthen, weaken, merge,
or challenge existing claims.

Minimum digest fields:

1. **Question**
2. **Findings**
3. **Entities involved**
4. **Lessons**
5. **Open questions**

---

## Routing Rules

| Artifact kind                                     | Destination                                          |
| ------------------------------------------------- | ---------------------------------------------------- |
| Work-chain digest page                            | `agentic_kg_memory`                                  |
| Standalone semantic facts or triplets             | `agentic_kg_memory`                                  |
| Reusable procedure that should alter a live skill | `skill-wiki` staged draft / skill update             |
| Extracted lessons                                 | lesson store (confidence-scored, dedup'd)            |
| Generic project continuity note                   | `memory-bank` or `continuity-log`                    |
| Single answer write-back                          | `agentic_kg_memory` query write-back, not this skill |

Rule: crystallization is the **distill step**, not the final storage system.

Closed-loop compounding shape:

`raw exploration stream -> structured digest -> extracted facts/lessons -> downstream wiki or graph updates`

---

## Crystallization vs Adjacent Operations

| Operation           | Purpose                                                         | Owner                                     |
| ------------------- | --------------------------------------------------------------- | ----------------------------------------- |
| Query write-back    | store one answer or claim                                       | `agentic_kg_memory`                       |
| Session compression | compress broad activity into episodic memory                    | `agentic_kg_memory` / continuity surfaces |
| Crystallization     | distill a purposeful work chain into durable digest + lessons   | `crystallization`                         |
| Skill promotion     | decide whether a reusable lesson changes the live skill library | `skill-wiki`                              |

---

## Example

A completed investigation into whether a runtime prompt should be merged into a downstream memory workflow is crystallization material:

- question: should the runtime prompt and downstream digest protocol be merged?
- finding: no, runtime workflow owns the prompt and crystallization stays downstream
- entities: workflow skill, `skill-wiki`, `agentic_kg_memory`
- lesson: keep runtime contracts separate from retrospective digests
- open question: whether the downstream digest deserves a standalone live skill

That digest belongs here. If the lesson changes the skill library, hand the procedural delta to `skill-wiki`; if it should become wiki memory, hand the digest to `agentic_kg_memory`.

---

## Dead Ends — Do Not Use

### Crystallizing before verification

If the work chain has not reached a verified outcome, crystallization canonizes noise and makes later correction harder.

### Dumping raw chronology into the digest

A timestamped activity log is session compression, not crystallization. The digest must contain the durable structure, not every intermediate step.

### Letting one skill own both distillation and storage

Folding crystallization entirely into `skill-wiki` or `agentic_kg_memory` hides the routing boundary. `crystallization` should own the protocol, while the downstream skills own promotion and storage.

---

## Applicability Envelope

**Works well when:**

- the work chain has a clear question and a stable answer
- conclusions are strong enough to survive beyond the current session
- both semantic outputs and reusable procedural lessons need clean routing

**Fails or degrades when:**

- the underlying work is still unresolved
- the output is just a generic activity log
- the digest omits boundary conditions, making future reuse overconfident

**Environment assumptions:**

- the agent can inspect the completed work chain and its artifacts
- `skill-wiki` and `agentic_kg_memory` are available as downstream homes
- the session has enough evidence to distinguish durable lessons from incidental chronology

---

## Lesson Lifecycle

Lessons extracted from a crystallization digest carry a confidence that compounds or decays — they are not binary (stored or not):

| Event                        | Effect on confidence                                                       |
| ---------------------------- | -------------------------------------------------------------------------- |
| Initial save from crystal    | 0.6                                                                        |
| Initial save (manual)        | 0.5                                                                        |
| Re-encounter / reinforcement | `confidence += 0.1 × (1 − confidence)`                                     |
| Weekly decay sweep           | `confidence -= decayRate × weeks_since_baseline` (default rate: 0.05/week) |
| Soft-delete threshold        | `confidence < 0.1` AND `reinforcements == 0`                               |

**Fingerprint deduplication**: two lessons with the same normalized content map to the same ID. A re-save reinforces rather than duplicating. Recall scoring: `score = confidence × term_relevance × recency_boost`.

This is the Ebbinghaus spaced-repetition model applied to lessons: frequently re-encountered lessons compound toward confidence 1.0; never-revisited lessons decay and eventually disappear.

## Auto-Crystallize Trigger

Periodic automated crystallization avoids requiring manual triggering after every work chain:

1. Scan done work chains / action sets where `crystallizedInto = null`
2. Filter to chains older than N days (default: 7)
3. Group by `parentId → project → "_ungrouped"`
4. For each group with ≥2 done items: trigger crystallization
5. Each crystal's extracted `lessons[]` trigger `lesson-save` automatically

The grouping heuristic keeps related work chains together — same parent task or same project — rather than crystallizing every isolated action as its own digest.
<!-- consolidation:see-also:start -->
## See Also
[[synthetic-data]]  [[checklist]]  [[agentic-harness]]
<!-- consolidation:see-also:end -->
