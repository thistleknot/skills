---
name: agentic_kg_memory
description: Architecture and operating protocol for agentic memory built from a retrieved knowledge graph. Use when defining or updating wiki-memory entries, intent/objective routing, throughlines, entity bags, merge rules, and judge-driven memory updates.
---
# Agentic KG Memory

## Core Thesis
The memory layer is not generic chat history. It is a persistent, structured wiki built from retrieved graph evidence and updated by an LLM judge.

- Organize memory by **intent first**
- Normalize what the user is trying to accomplish as an **objective**
- Keep a weighted **entity bag** as supporting evidence, not as the primary key
- Save **throughlines** as the compressed thematic spine associated with the objective
- Separate **semantic fit** from **usage counts**
- Let the judge decide whether to **update**, **merge**, or **create**

## Canonical Memory Shape
Each wiki entry should carry:

1. `intent`
2. `objective`
3. `throughlines`
4. `entity_bag`
5. `fit_score`
6. `read_count`
7. `confirmed_read_count`
8. `update_count`
9. `wiki_summary`
10. `history`

Example:

```json
{
  "intent": "compare-philosophies",
  "objective": "contrast the ethical throughlines of two thinkers",
  "throughlines": [
    "virtue ethics versus value transvaluation",
    "moral framework comparison through recurring themes"
  ],
  "entity_bag": {
    "aristotle": 0.92,
    "nietzsche": 0.88,
    "ethics": 0.71,
    "virtue": 0.66
  },
  "fit_score": 0.81,
  "read_count": 14,
  "confirmed_read_count": 9,
  "update_count": 4,
  "wiki_summary": "Prior queries focused on ethical contrast, especially virtue and value frameworks.",
  "history": []
}
```

## Field Semantics

### Intent
- Intent is a mutually exclusive routing label for the downstream use case.
- Retrieve candidate wiki entries by intent first.
- If multiple stored intents are not truly exclusive, repair the taxonomy.

### Objective
- Objective is the normalized statement of what the query is trying to accomplish under that intent.
- Objectives are also treated as mutually exclusive sets.
- If two objectives are judged non-exclusive, merge them rather than keeping parallel duplicates.

### Throughlines
- Throughlines are the saved conceptual spine of the entry.
- They are associated with the objective, not stored as unrelated notes.
- A query can refine or add throughlines when the judge says the new evidence sharpens the objective rather than changing it.

### Entity Bag
- The entity bag is weighted supporting evidence between intent and objective.
- It is not the primary key.
- The judge may add, remove, or reweight entities if doing so improves fit.

### Fit Score
- `fit_score` is the semantic quality and reuse fitness of the entry.
- It is judge-derived.
- Score updates should be monotonic: only increase when the new query and retrieved evidence improve fit.

### Counts
- `read_count` measures retrieval frequency
- `confirmed_read_count` measures how often the entry contributed to a confirmed useful answer
- `update_count` measures how often the entry absorbed new useful variance

Counts are utility signals, not correctness.

### Wiki Summary
- The wiki summary is the recursive free-form explanation of what this entry has learned so far.
- It should stay aligned with the objective and throughlines.

## Retrieval and Update Loop
When using this skill, follow this order:

1. Normalize or restate the incoming query
2. Classify the mutually exclusive intent
3. Retrieve candidate wiki entries by intent
4. Use throughlines and objective text as the primary semantic match surface
5. Use entity bag overlap as supporting evidence
6. Ask the judge whether the query fits an existing objective
7. If yes, update the entry
8. If two entries are not mutually exclusive, merge them
9. If no candidate fits, create a new entry

The organizing principle is:

`query -> intent -> objective -> throughlines -> entity_bag -> fit_score`

## Judge Contract
The judge should return a structured decision, not prose only.

Required outputs:

- `matched_entry_id` or `null`
- `intent_fit`
- `objective_fit`
- `throughline_fit`
- `context_precision`
- `context_recall`
- `proposed_objective`
- `proposed_throughlines`
- `entity_bag_updates`
- `proposed_summary`
- `merge_candidates`
- `fit_score_delta`
- `decision`
- `decision_reason`

Valid decisions:
- `update`
- `merge`
- `create`
- `reject`

## Update Rules
Apply these gates:

1. **Intent gate** — compare inside predicted intent unless intent confidence is low
2. **Objective gate** — update only if the query is not mutually exclusive with the objective
3. **Throughline gate** — update throughlines only if they sharpen the same objective rather than creating drift
4. **Entity gate** — use entity bag changes as support, not as sole authority
5. **Score gate** — increase `fit_score` only when fit improves
6. **Count gate** — increment counts based on actual retrieval/use/update events
7. **Merge gate** — merge non-exclusive entries into the higher-fit survivor
8. **Create gate** — create a new entry if fit is low rather than corrupting an old one

## Score Interpretation
Do not collapse all quality into one popularity number.

Keep at least two categories:

1. **Semantic quality**
   - `fit_score`
   - derived from the judge, typically from RAGAS-style `context_precision` and `context_recall`

2. **Behavioral utility**
   - `read_count`
   - `confirmed_read_count`
   - `update_count`

If a single retrieval ranking score is needed later, derive it from both:

`rank_score = fit_score + a*log1p(confirmed_read_count) + b*log1p(update_count)`

But do not replace semantic quality with raw counts.

## Throughline Policy
Throughlines should be persisted explicitly.

- They belong to the objective
- They summarize recurring thematic resolution
- They can be a list, not just one string
- Keep them stable enough to be reusable, but updateable when the judge finds a sharper abstraction

Use throughlines when:
- ranking candidate memory entries
- explaining why an objective matched
- deciding whether two objectives should merge

## Merge Policy
Merge when:
- intents are the same or judged compatible
- objectives are not mutually exclusive
- throughlines are compatible or reconcilable
- the merged entry is cleaner than keeping two partial duplicates

When merging:
- keep the higher `fit_score` survivor
- union and reweight the entity bag
- combine or compress throughlines
- sum counts where appropriate
- append a merge record to history

## History Policy
History should record:
- query snapshot or identifier
- action taken: `read`, `update`, `merge`, `create`, `reject`
- before/after objective or throughlines if changed
- `fit_score_delta`
- count increments
- rationale

History is for auditability, not ranking.

## Anti-Patterns
Avoid these:

- using entity overlap as the primary key
- replacing `fit_score` with raw read count
- updating objectives on weak evidence
- merging entries just because they share entities
- treating throughlines as disposable prose instead of structured memory
- lowering semantic score due to one noisy query instead of refusing the update

## Minimal Output Contract
When using this skill, the final answer should report:

- the chosen intent
- the matched or created objective
- any throughline changes
- any entity bag changes
- whether the action was update, merge, create, or reject
- any `fit_score` change
- any count increments
- the reasoning for the decision
