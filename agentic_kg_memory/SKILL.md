---
name: agentic_kg_memory
description: >
  Graph-backed semantic memory and reasoning protocol. Use when extracting
  premises into a knowledge graph, retrieving evidence with BM25/NLI, updating
  memory entries from new evidence, or maintaining wiki-like throughlines that
  evolve as the graph learns.
---

# Agentic KG Memory

## Scope Boundary

This skill is for **memory architecture**, **retrieval**, and **evolving
graph-backed conclusions**.

Filter out control-flow or orchestration taxonomies that are orthogonal here:
- StateFlow
- ADAS
- DSPy
- AWM

Those may be useful elsewhere, but they are not the memory model.

This skill owns:
- triplet extraction and evidence storage
- intent/objective-centered memory pages
- BM25 narrowing and NLI or judge-based validation
- reinforce/weaken/add memory evolution
- throughlines as retrievable meta-memory
- runtime quality updates on conclusions

## Core Thesis

The graph stores facts. The memory layer stores what those facts mean together.

The clean architecture is a **three-tier memory stack**:

1. **Triplets** — local premises and provenance
2. **Pages / wiki entries** — objective-centered memory clusters
3. **Throughlines** — competing abductive conclusions over those clusters

The page is not a summary blob. It is a durable memory surface that links:

`intent -> objective -> supporting premises -> throughlines`

## Why These Papers Matter

### MemRL
MemRL is the strongest validation of this design.

- Its two-phase retrieval validates the existing intuition that semantic match
  and memory quality should both contribute to ranking.
- Its runtime update rule turns confidence from a one-time prior into a learned
  posterior:

```text
Q_new <- Q_old + α(r - Q_old)
```

Here `r` can come from downstream NLI or judge signal:
- entailment -> reinforce
- contradiction -> weaken
- neutral -> weak update or no-op, depending on policy

### A-MEM
A-MEM validates that two-stage memory linking is load-bearing:

1. candidate narrowing
2. connection-quality judgment

In this skill that becomes:

1. BM25 or intent/objective narrowing
2. NLI / judge validation of whether the memory should connect, update, or fork

### Neuro-symbolic memory evolution
The reinforce / weaken / add rule maps directly onto KG maintenance:

```text
if sim(new_observation, existing_memory) > τ_pos: reinforce
elif sim(new_observation, existing_memory) < τ_neg: weaken
else: add new memory
```

That is more principled than a binary merge-or-add policy and supports partial
contradiction cleanly.

### Generative Agents
Their recency + importance + relevance framing matters most at the page or
throughline layer.

- Recency is optional for static corpora
- Recency becomes useful for sequential corpora such as scenes, incidents, or
  evolving case files

## Canonical Memory Shape

Each **page / wiki entry** should carry:

1. `page_id`
2. `intent`
3. `objective`
4. `entity_bag`
5. `supporting_triplets`
6. `fit_score`
7. `read_count`
8. `confirmed_read_count`
9. `update_count`
10. `wiki_summary`
11. `throughlines`
12. `history`

Example:

```json
{
  "page_id": "page_042",
  "intent": "compare-philosophies",
  "objective": "contrast the ethical throughlines of two thinkers",
  "entity_bag": {
    "aristotle": 0.92,
    "nietzsche": 0.88,
    "ethics": 0.71
  },
  "supporting_triplets": ["t_18", "t_44", "t_51"],
  "fit_score": 0.81,
  "read_count": 14,
  "confirmed_read_count": 9,
  "update_count": 4,
  "wiki_summary": "Prior queries focused on ethical contrast, especially virtue and value frameworks.",
  "throughlines": ["th_7", "th_9"],
  "history": []
}
```

## Throughlines Are the Meta-Layer

The page answers: **what evidence clusters together?**

The throughline answers: **what is the graph trying to tell us?**

A throughline is a materialized syllogism: a first-class claim whose provenance
points back to the triplets and pages that support it.

It is not a flattened summary. It is a retrievable, updateable conclusion that
can itself serve as a premise later.

### Throughline Schema

```text
throughline_id   TEXT PRIMARY KEY
page_id          TEXT
claim_text       TEXT   # mutable, LLM-rewritten as evidence accumulates
supporting_fks   LIST   # triplet_ids and/or page_ids
q_score          REAL   # runtime-learned trust score
status           TEXT   # active | competing | deprecated
created_at       DATETIME
updated_at       DATETIME
history          JSON
```

### Throughline Update Cycle

```text
new triplet arrives
    |
    v
retrieve affected pages / throughlines
    |
    +- if hit:
    |    LLM reads old throughline + new evidence
    |    decision: reinforce / refine / contradict
    |    if refine: rewrite claim_text
    |    q_score <- q_score + α(r - q_score)
    |
    +- if no hit:
         keep in candidate pool until density threshold supports a new throughline
```

The roles are separate:
- **LLM** updates what the throughline says
- **Q-score** updates how much to trust it

### Competing Throughlines

Do not force one conclusion too early.

Multiple throughlines may coexist over the same evidence cluster. They compete
by `q_score`. The highest score is the current best abductive explanation, not
the permanent winner.

## Three-Tier Confidence Stack

```text
triplet      extraction prior      -> observed/inferred + mutable confidence
page         retrieval fitness     -> objective/throughline/entity fit
throughline  runtime posterior     -> MemRL-style Q-score
```

Each tier answers a different question:

- **Triplet**: was this locally well-grounded?
- **Page**: is this memory entry a good semantic match for the current task?
- **Throughline**: has this conclusion held up under repeated use?

## Triplet Layer

The atom is still the semantic triplet `(S, P, O)` with provenance.

Minimum fields:

```text
triplet_id
subject_signal
predicate_signal
object_signal
span_id
doc_id
epistemics        # observed | inferred
confidence        # mutable, not write-once
created_at
updated_at
```

### Triplet Confidence

Use extraction-time priors, but do not freeze them forever.

A minimal prior:
- observed -> `1.0`
- inferred -> `0.5`

Then update confidence with downstream evidence:

```text
confidence_new <- confidence_old + α(r_nli - confidence_old)
```

If retrieving a triplet repeatedly supports correct entailment, confidence rises.
If it repeatedly contributes to contradiction, confidence falls.

## Retrieval and Update Loop

Follow this order:

1. Normalize the incoming query
2. Classify the **intent**
3. Retrieve candidate **pages** by intent first
4. Rank by objective text and throughline fit
5. Use entity-bag overlap as supporting evidence, not the primary key
6. BM25-narrow supporting triplets
7. Run NLI or judge validation on the narrowed set
8. Decide whether to reinforce, refine, merge, create, or reject
9. Update page and throughline state
10. Persist score updates and history

The organizing chain is:

`query -> intent -> objective/page -> triplets -> NLI/judge -> throughline update`

## Ranking Surface

The retrieval surface is deliberately layered.

### Candidate narrowing
- BM25 over triplet or page text fields
- intent routing
- objective and throughline semantic similarity

### Quality weighting
MemRL-style blending should inform page or throughline ranking:

```text
score = (1 - λ) * sim(query, objective_or_throughline) + λ * q_value
```

For triplets, a simpler blended or multiplicative surface is fine:

```text
triplet_score = bm25_score * confidence
```

Use the simple version first. Add the learned component where repeated usage
provides stable reward.

## Intent, Objective, and Entity Bag Policy

### Intent
- Intent is the top-level routing label
- It should be mutually exclusive for downstream use
- If two intents are not exclusive in practice, repair the taxonomy

### Objective
- Objective is the normalized statement of what the query is trying to accomplish
- Objectives should also be treated as mutually exclusive within an intent
- If two stored objectives are really the same task, merge them

### Entity Bag
- The entity bag is supporting evidence between triplets and pages
- It is not the primary key
- Add, remove, or reweight entities only when doing so improves fit

## Judge Contract

The judge must return structure, not prose only.

Required outputs:
- `matched_page_id` or `null`
- `intent_fit`
- `objective_fit`
- `throughline_fit`
- `triplet_fit`
- `context_precision`
- `context_recall`
- `proposed_objective`
- `entity_bag_updates`
- `triplet_updates`
- `throughline_updates`
- `fit_score_delta`
- `q_score_delta`
- `decision`
- `decision_reason`

Valid decisions:
- `reinforce`
- `refine`
- `merge`
- `create`
- `reject`
- `contradict`

## Merge and Evolution Policy

### Reinforce
Use when new evidence supports an existing triplet, page, or throughline.

Effects:
- raise confidence or q-score
- increment counts
- append provenance

### Refine
Use when the old memory is mostly right but needs a better formulation.

Effects:
- rewrite objective, wiki summary, or throughline claim text
- keep lineage in history
- only increase trust if the refined memory fits better

### Weaken / contradict
Use when new evidence cuts against the existing memory without fully invalidating
the surrounding page.

Effects:
- lower confidence or q-score
- preserve both the old memory and the contradiction trail
- avoid forced collapse

### Add new memory
Use when evidence is too dissimilar for reinforcement and too incompatible for
safe merge.

### Merge
Merge when:
- intents are compatible
- objectives are not mutually exclusive
- throughlines are reconcilable
- the merged survivor is cleaner than parallel duplicates

When merging:
- keep the higher-fit page
- union and reweight entity bags
- merge supporting triplets
- preserve competing throughlines if they are still meaningfully distinct
- append a merge record to history

## History Policy

History should record:
- query snapshot or ID
- action: `read`, `reinforce`, `refine`, `merge`, `create`, `reject`, `contradict`
- before/after objective or throughline text if changed
- confidence or q-score deltas
- count increments
- rationale

History is for auditability, not ranking.

## Anti-Patterns

Avoid:
- treating entity overlap as the primary key
- storing triplets as write-once forever
- collapsing throughlines into one summary too early
- replacing semantic quality with popularity counts
- merging memories just because they mention the same entities
- updating conclusions without preserving provenance
- importing control-flow frameworks into the memory model

## Minimal Output Contract

When using this skill, report:
- chosen intent
- matched or created page/objective
- triplet changes
- throughline changes
- whether the action was reinforce, refine, merge, create, reject, or contradict
- fit-score and q-score changes
- rationale for the decision
