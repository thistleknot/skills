---
name: skill-wiki
description: >
  Living skill library lifecycle governor. Invoke when: authoring a new skill
  from integrate/ intake; updating a skill with new evidence; crystallizing
  session learnings into a staged draft; promoting a staged concept to an
  active skill; marking a skill or section as superseded; or running a
  periodic library health sweep. NOT for project state (→ memory-bank) or
  evidence storage (→ agentic_kg_memory). This is the editorial pipeline,
  not the storage layer.
status: active
last_validated: 2026-04-28
supersedes: []
validation_method: session
---

# Skill Wiki — Living Skill Library Protocol

## Core Thesis

**Stop re-deriving behavioral contracts. Skills should compound.**

Every session, every research aggregation, every production failure is evidence.
Evidence strengthens or weakens existing contracts and occasionally promotes new ones.
The skill library is the **procedural memory layer** of the agent's cognitive architecture
(CoALA taxonomy: working / episodic / semantic / **procedural**). It needs the same
lifecycle machinery as a knowledge wiki.

The LLM-wiki insight (Karpathy) applied to skills: RAG retrieves and forgets; a
compiled skill library accumulates and compounds. The bottleneck is maintenance —
`skill-wiki` eliminates that bottleneck.

**Ownership boundary:**

| Concern | Skill |
|---|---|
| Skill promotion, supersession, crystallization routing | `skill-wiki` (this skill) |
| Evidence storage in semantic graph | `agentic_kg_memory` |
| Session / project continuity | `memory-bank` |
| Distilled reasoning between compactions | `continuity-log` |

---

## Skill Anatomy

Every `SKILL.md` has three layers:

```
Contract       — behavioral protocol: when to invoke, what to do, how to exit
Applicability  — when it works, when it fails, environment assumptions
Sidecars       — HISTORY.md (changes + supersession), EVIDENCE.md (grounding citations)
```

`SKILL.md` stays lean — **it is the behavioral contract, not the wiki page**.
Evidence and change history live in sidecars so the contract remains invocable
without wading through provenance.

### SKILL.md Frontmatter

Add these optional fields to any skill:

```yaml
status: active           # raw | staged | active | superseded
last_validated: YYYY-MM-DD
supersedes: []           # prior skill names this replaced
superseded_by: null      # set when this skill is retired
validation_method: benchmark | production | community | session | theoretical
```

### Applicability Envelope (add to every SKILL.md)

```markdown
## Applicability Envelope

**Works well when:**
- ...conditions under which the skill's contract is reliable

**Fails or degrades when:**
- ...conditions that break the skill's assumptions

**Environment assumptions:**
- ...tools, runtime, models this skill assumes are available
```

Skills are **conditional protocols, not universal facts**. Without this envelope
the agent cannot self-correct when a skill misfires in an out-of-envelope context.

---

## Lifecycle Stages

```
Session observation
       ↓  write to pattern store if novel + actionable
Pattern store (vector)  ← raw behavioral patterns; NOT yet a skill
       ↓  application_count ≥ 3 AND confidence ≥ 6 (promotion gate)
integrate/staged/       ← draft SKILL.md; ≥1 EVIDENCE.md entry; human review required
       ↓  promotion gate passed (Evidence Tiers, see below)
skills/<branch>/        ← active skill; evidence accumulates via EVIDENCE.md + HISTORY.md
       ↓  superseded by newer skill or absorbed into parent
status: superseded      ← frontmatter updated; file preserved; superseded_by: set
```

`integrate/` is the evidence corpus. Never delete from it.

---

## Pattern Store (Pre-Staged Vetting Layer)

The pattern store is a **vector store buffer** that sits between raw session observations
and the `integrate/staged/` draft pipeline. Its job is to vet patterns by replication
before they touch any skill file.

**MCG alignment (Tekiner, 2025):** The pattern store implements the CG `patterns` table
and `tk_candidates` lifecycle from the Meta Context Graph architecture. In MCG terms:
- **Pattern store entries** = CG `patterns` nodes (token-level / semantic memory)
- **Pending entries with < 3 applications** = `tk_candidates` (status: pending)
- **Entries passing the promotion gate** = `tribal_knowledge` (status: active)
- **Promoted skills** = procedural memory compilation (CoALA procedural tier)
- **Decay mechanism** = schema evolution / staleness detection (Tekiner §"Handling schema evolution")

This is also an implementation of the **ACE evolving-playbook loop** (arXiv:2510.04618,
ICLR 2026): generation (observation) → reflection (application_count + failure_count
tracking) → curation (promotion gate or prune). ACE reports +10.6% on agent benchmarks
for systems that apply this loop to operational context.

**The invariant:** a pattern that has only been useful once is an anecdote. Three
independent applications in different contexts is the minimum signal for a behavioral claim.

### What belongs in the pattern store

A **pattern** is a specific behavioral rule, not a general observation:
- Good: *"When gate command times out, check file existence first to avoid 83s→1.2s regression"*
- Bad: *"Gates can time out"* (observation, not actionable rule)
- Good: *"Parallel specialist reviewers with fingerprint dedup catch more issues than single-pass review"*
- Bad: *"Reviews are good"*

Entries must be extractable as `when [context], do [action]` or `in [situation], [approach] works because [mechanism]`.

### Schema

```json
{
  "id": "<sha256 of pattern_text + skill_context>",
  "pattern": "when X, do Y — 1-3 sentences max",
  "skill_context": "agentic-harness",
  "type": "procedure | heuristic | anti-pattern | template",
  "application_count": 0,
  "retrieval_count": 0,
  "failure_count": 0,
  "last_applied": null,
  "last_retrieved": null,
  "created_at": "ISO-8601",
  "confidence": 7.0,
  "source_sessions": []
}
```

`application_count` — times the agent explicitly chose this pattern for the current task.
`retrieval_count` — times the pattern was returned by vector search (passive; includes non-use).
`failure_count` — times applied and the outcome was negative. Deducts immediately.

Only `application_count` counts toward the tenure threshold. Retrieval alone does not.

### Confidence decay

```
confidence(t) = initial_confidence × e^(-λ × months_since_last_applied)
λ = 0.1   (≈ 10% decay per month without application)

effective_confidence = confidence(t) - (failure_count × 1.5)
```

Decay represents *not validated recently*, not *wrong*. A niche pattern that is rarely
triggered but correct when triggered should decay slowly — not because it's used
infrequently but because it hasn't been *refuted*.

Failures deduct immediately and compound the decay signal. A pattern applied 3 times
and failed twice has a meaningful confidence crater before decay even runs.

### Prune threshold

```
prune_if: effective_confidence < 2.0 AND application_count < 3
```

**Never prune if `application_count ≥ 3`.** That entry is a promotion candidate, not
a stale record. Move it to `integrate/staged/` instead of deleting it.

**Never prune because of retrieval count alone.** A pattern that is frequently
retrieved but never applied is a recall-precision problem (wrong embedding), not
a stale pattern. Fix the embedding before pruning.

### Promotion gate (pattern store → staged draft)

```
application_count  ≥ 3
effective_confidence ≥ 6.0
success_rate (applications - failures) / applications ≥ 0.67
NOT already covered by an existing active skill section
```

On gate pass: auto-generate a draft SKILL.md excerpt in `integrate/staged/`.
**Human review required before crystallization into an active skill.** The automation
surfaces candidates; it never self-promotes.

### Backend

The pattern store uses the same `agentic_kg_memory` sqlite + BM25 + cosine similarity
infrastructure, under a dedicated `patterns` namespace/collection. It is **not** the
semantic knowledge graph (which holds domain facts and entity relationships). These
are operational patterns — behavioral rules about what to do, not facts about a domain.

Pattern query at skill invocation:
```
SELECT top-3 patterns WHERE skill_context = current_skill
  ORDER BY relevance DESC
  FILTER effective_confidence >= 4.0
```

Surface as: `"Candidate pattern (confidence N/10, used M times): [pattern text]"`
Agent decides whether to apply. Application must be explicit — record `was_applied: true`
if used, `was_applied: false` if retrieved but not applied.

---

## Intake Protocol

When absorbing content from `integrate/` (repos, research outputs, session logs):

1. **Extract behavioral patterns** — what should an agent *do* with this?
   Avoid documenting facts; extract decision rules and protocols.
2. **Route to existing vs new** — does this extend an existing skill, or warrant a new one?
   Prefer extending. Only create a new skill folder if no existing skill can absorb
   the pattern without losing coherence.
3. **Write a draft** in `integrate/staged/<concept-name>/SKILL.md`
4. **Attach evidence** — one entry in `integrate/staged/<concept-name>/EVIDENCE.md`
5. **Run the promotion gate** — if passed, move to a live skill folder

---

## Promotion Gate

Promotion from `staged/` → active requires at least **one of**:
- One Tier-1 or Tier-2 evidence item **and** one local validation (session where it worked)
- Two independent Tier-1–3 items from **distinct** source types (no double-counting)

### Evidence Tiers

| Tier | Source type | Example |
|---|---|---|
| 1 | Production benchmark with reported metric | SWE-bench +9.1pp; DABench +25% |
| 2 | Production tool adoption | Claude Code; Cursor; Devin; GitHub Copilot |
| 3 | Community corpus pattern | awesome-copilot (3+ independent skill implementations) |
| 4 | Session crystallization | Used successfully in ≥1 verified session |
| 5 | Theoretical | arXiv paper without empirical benchmark result |

One source cited three times is one evidence item, not three.
Track `contradiction_count` in EVIDENCE.md — high contradictions depress confidence
in specific claims.

---

## Session Crystallization

At the end of any session where a skill was invoked and produced a notable outcome:

1. **Was the outcome verified?** If not, do not crystallize. Invocation count ≠ evidence.
2. **What new behavioral pattern emerged?** Capture the specific rule, not the instance.
3. **What failed?** Capture failure conditions for the Applicability Envelope update.
4. **Does this contradict the existing contract?** If yes, flag as supersession candidate.
5. **Where does this land?**
   - New pattern for existing skill → `integrate/staged/<skill-name>-YYYYMMDD.md`
   - New pattern needing a new skill → `integrate/staged/<new-skill-name>/`
   - Contradiction of existing contract → same as above, with explicit `supersedes:` marker

**Crystallization always writes to `staged/` first.** Promotion to a live skill is a
deliberate subsequent act. This gate prevents invocation-count-based drift: a skill
used many times incorrectly must not self-canonize its failure mode.

---

## Supersession Protocol

Skills contain conditional protocols, not universal facts. Supersession happens more
often at **section level** than at whole-skill level.

**Section-level supersession (most common):**
1. Update the live SKILL.md contract clause directly — SKILL.md always shows the
   current truth, never contains strikethrough history.
2. Record in `HISTORY.md`: date, which section, what changed, why, evidence citation.
3. Update `EVIDENCE.md` with the new citation.

**Whole-skill supersession:**
1. Set `superseded_by: <new-skill-name>` in the old skill's frontmatter.
2. Set `status: superseded`.
3. Record in old skill's `HISTORY.md`: date, reason, replacement pointer.
4. Update README.md skill graph.

---

## Sidecar Conventions

Following the repo's existing pattern (DESCRIPTION.md, ARCHITECTURE.md, HISTORY.md):

### `HISTORY.md` — changelog and supersession record

```markdown
## YYYY-MM-DD — <brief title>
**Changed:** <what behavioral contract changed>
**Reason:** <evidence or session that drove the change>
**Evidence:** <citation — tier + source + claim>
**Supersedes:** <specific prior behavior, if applicable>
```

### `EVIDENCE.md` — grounding citations for behavioral contracts

```markdown
## Evidence Index

| Tier | Source | Claim | Contract section grounded |
|---|---|---|---|
| 1 | arXiv:XXXX.XXXXX | <claim with metric> | <section name> |
```

**When to add sidecars:**
- Skill has been updated at least once (HISTORY.md needed for supersession record)
- Skill is being promoted from staged to active (EVIDENCE.md required)
- Skill has been used in 3+ sessions (crystallization history worth preserving)

---

## Periodic Library Sweep

Run a library sweep when:
- A new research aggregation or intake session completes
- Any active skill has `last_validated` > 90 days ago
- A skill is invoked and its applicability envelope is violated

**Sweep steps:**
1. For each active skill with stale `last_validated`:
   check whether benchmarks or production tools have moved;
   update `EVIDENCE.md`; update `last_validated`.
2. For each item in `integrate/staged/`:
   check whether the promotion gate is now met.
3. For each skill with `status: superseded`:
   verify `superseded_by` skill covers the old use case.

---

## Applicability Envelope

**Works well when:**
- A new source (repo, paper, session output) has been added to `integrate/` and needs routing
- A skill has been used and produced a surprising outcome worth capturing in the pattern store
- A pattern store entry has reached the tenure threshold and needs surfacing for human review
- A skill is visibly stale (contracts reference deprecated tools or outdated patterns)
- It is time for a periodic library sweep (> 3 months since last sweep)

**Fails or degrades when:**
- Session crystallization is attempted without a verified outcome (amplifies noise)
- Used to bypass the promotion gate ("promote this because it seems right" without evidence)
- Applied mid-session while a skill is actively in use (edit-during-invocation conflict)
- Pattern store entries are promoted without human review (automation surfaces, humans crystallize)

**Environment assumptions:**
- `integrate/` folder exists and is writable
- `agentic_kg_memory` sqlite + vector infrastructure is available for the pattern store backend
- Git history is available for dating changes
- The agent can read existing SKILL.md files before modifying them
<!-- consolidation:see-also:start -->
## See Also
[[agentic_kg_memory]]  [[agentic-harness]]  [[react-agent]]  [[procedural-memory]]  [[memory-bank]]
<!-- consolidation:see-also:end -->
