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
- preprocessing source text into KG-ready triplets
- triplet extraction and evidence storage
- intent/objective-centered memory pages
- BM25 narrowing and NLI or judge-based validation
- reinforce/weaken/add memory evolution
- throughlines as retrievable meta-memory
- runtime quality updates on conclusions
- source-backed conclusion synthesis for final answers

## Setup Mode

If the user invokes **`agentic_kg_memory setup`**, treat that as a storage and
retrieval installation request.

### Required paths

Use these explicit paths on this machine:

- `C:\Users\user\memory-bank\wiki_memory.sqlite3`
- `C:\Users\user\.copilot\chroma\memory-bank\`
- `C:\Users\user\memory-bank\clusters.json`
- `C:\Users\user\memory-bank\cluster_metrics.json`

The SQLite file is the sparse/metadata surface.
The Chroma directory is the dense embedding surface.

### Setup actions

When running setup, do all of the following:

1. Create `C:\Users\user\memory-bank\wiki_memory.sqlite3`
2. Create or migrate a page table that includes:
   - `bm25_text`
   - `triplet_sequence_text`
   - `embedding_ref`
   - `cluster_id`
3. Create `C:\Users\user\.copilot\chroma\memory-bank\` as the Chroma persist directory
4. Build `triplet_sequence_text` from canonicalized extracted triplets in source order
5. Embed `triplet_sequence_text` and store vectors in Chroma
6. Cluster the normalized dense vectors
7. Write the winning `cluster_id` back into SQLite
8. Persist human-readable cluster outputs to:
   - `C:\Users\user\memory-bank\clusters.json`
   - `C:\Users\user\memory-bank\cluster_metrics.json`

### Evaluation outputs

The setup step is not complete until it persists:

- cluster count
- clustering method
- normalization method
- `bss`
- `tss`
- `bss_tss_ratio`

If the system has only the design and no fitted clustering run yet, say so plainly.

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

## Preprocessing Contract

Before retrieval, pages, or throughlines exist, source text must be converted into
triplets. That preprocessing step belongs to `agentic_kg_memory`.

The high-level chain is:

`source text -> LLM extraction (with guidance-resolved synsets) -> normalized triplets -> ontology winner ids -> bm25_index column -> storage`

### Synset/Hypernym Resolution via Guidance

**Stage 1: Base triplet extraction**
- LLM generates: `{ "subject": str, "predicate": str, "object": str, "polarity": "affirmed"|"negated", "inference_type": "observed"|"inferred" }`

**Stage 2: Guidance-driven synset selection**
- For each word in each element (subject, predicate, object):
  - Retrieve top-5 word2vec neighbors
  - Include the word itself as the 6th candidate
  - Look up first-level hypernym for each synset via NLTK
  - Format as candidate tuples: `[(synset_id, first_hypernym_id), ...]`
- Present candidates to LLM with guidance constraints
- LLM selects best synset + hypernym tuple per word (or abstains if confidence low)
- Result: `subject_synset_hypernym_tuples`, `predicate_synset_hypernym_tuples`, `object_synset_hypernym_tuples` as lists of `[synset_id, hypernym_id]` pairs

**Stage 3: BM25 index construction**
- Extract lemmas from all selected synsets and hypernyms (strip `.pos.##` suffixes)
- Flatten into space-separated text: `"subject_lemma subject_hypernym_lemma predicate_lemma ... object_lemma object_hypernym_lemma"`
- Store as `bm25_index` column for layer 2 KG memory retrieval

**Example:**
```json
{
  "subject": "love",
  "predicate": "be",
  "object": "madness",
  "subject_synset_hypernym_tuples": [["love.n.01", "feeling.n.01"]],
  "predicate_synset_hypernym_tuples": [["be.v.01", "exist.v.01"]],
  "object_synset_hypernym_tuples": [["madness.n.01", "state.n.01"]]
}
```
→ `bm25_index: "love feeling be exist madness state"`

### Source-to-triplet extraction

The default extraction mode should stay simple and controllable.

Use a Pydantic model that asks the LLM for **comma-separated strings** rather than
free-form prose.

One workable contract is:

```python
from pydantic import BaseModel


class TripletExtraction(BaseModel):
    subjects_csv: str    # e.g. "Alice, Bob, meeting"
    predicates_csv: str  # e.g. "attended, skipped, was_held"
    objects_csv: str     # e.g. "meeting, conference, office"
    polarity_csv: str    # e.g. "affirmed, negated, affirmed"
    inference_csv: str   # e.g. "observed, inferred, observed"
    throughline: str     # local abductive best-fit from THIS source alone
```

**`polarity`** captures what the source text actually asserts — a **stable property of the text**:
- `affirmed` — the text states the triplet holds
- `negated` — the text explicitly denies or limits the triplet ("Alice did NOT attend")

`negated` serves the same purpose as a `qualifications` field: it records what the source
explicitly contradicts or constrains. This is knowable at ingestion time from the text alone.

**`inference_type`** captures how the triplet was derived:
- `observed` — directly stated in the source
- `inferred` — derived from the source via a stated logical chain

**What is NOT stored at ingestion: entailment direction.**

Do not split premises into `entailed_premises` / `not_entailed_premises` at ingestion.
Entailment is a relation between a premise and a **specific conclusion** — and at ingestion
time you only have one source's throughline. At retrieval you have N sources and a query;
the entailment direction is entirely different. Labeling at ingestion bakes in a reasoning
direction that may be wrong for every query that follows.

The ingestion contract is: premises: `[str]` tagged `[observed]` / `[inferred]`, with
`polarity` capturing what the text explicitly commits to or denies. Nothing more.
Entailment chains emerge at query time, not indexing time.

**`throughline`** is a local, per-document abductive summary — the best-fit hypothesis
that explains the affirmed/negated triplets in this source. It is **not** a cross-document
conclusion. Global deductive reasoning happens in a later cross-page pass.

Interpretation rule:

1. split each csv field on commas
2. trim whitespace
3. align by position (all five csv fields must have equal element count)
4. drop empty rows
5. send each `(subject, predicate, object, polarity, inference_type)` tuple into ontology normalization

This keeps extraction cheap, deterministic, and easy to repair.

### Extraction rules

- extract triplets directly from the **source text**
- keep source order
- prefer short normalized spans over long prose phrases
- preserve named entities before aggressive collapse
- do **not** apply cross-document deduction during extraction — the extractor reads one source;
  deductive/syllogistic reasoning over multiple sources belongs to the throughline reasoning pass
- store provenance so every triplet still points back to the original source span
- negated triplets are first-class facts; do not drop them or flatten polarity

### Why this preprocessing matters

This is the load-bearing step that makes the later retrieval design possible:

- `bm25_text` can be built from the normalized lexical surface
- `triplet_sequence_text` can be built from the ordered triplets
- ontology can resolve canonical ids before graph storage
- pages and throughlines can operate on normalized evidence rather than raw prose

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
12. `bm25_text`
13. `triplet_sequence_text`
14. `embedding_ref`
15. `cluster_id`
16. `history`

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
  "bm25_text": "contrast the ethical throughlines of two thinkers virtue value frameworks",
  "triplet_sequence_text": "aristotle [SEP] argue_for [SEP] virtue [SEP] nietzsche [SEP] challenge [SEP] morality [SEP] ethics [SEP] concern [SEP] flourishing",
  "embedding_ref": "chroma://memory-bank/page_042",
  "cluster_id": "cluster_03",
  "throughlines": ["th_7", "th_9"],
  "history": []
}
```

### Retrieval columns

Use a deliberately hybrid storage surface rather than a single retrieval field.

- `bm25_text` = sparse lexical field for BM25 or equivalent inverted-index retrieval
- `triplet_sequence_text` = dense semantic field built from the extracted triplets in
  document order, concatenated with `[SEP]` tokens
- `embedding_ref` = pointer to the stored vector for `triplet_sequence_text`
- `cluster_id` = routing label derived from the dense embedding space

The dense field should be built from **normalized extracted triplets in textual order**:

```text
subject_1 [SEP] predicate_1 [SEP] object_1 [SEP] subject_2 [SEP] predicate_2 [SEP] object_2 ...
```

Do not shuffle triplets. Their order in the source text is part of the signal.

## Throughlines Are the Meta-Layer

The page answers: **what evidence clusters together?**

The throughline answers: **what is the graph trying to tell us?**

A throughline is a materialized syllogism: a first-class claim whose provenance
points back to the triplets and pages that support it.

It is not a flattened summary. It is a retrievable, updateable conclusion that
can itself serve as a premise later.

**Two levels of throughline:**

- **Local throughline** (extracted inline per document) — the abductive best-fit
  conclusion from the affirmed and negated triplets in a single source. Cheap to
  produce; lives in `TripletExtraction.throughline`.
- **Global throughline** (derived cross-page by the reasoning layer) — the deductive
  conclusion that holds across multiple pages. Produced by applying syllogistic
  chains: if pages P1 and P2 both affirm premises A→B and B→C, the global
  throughline can conclude A→C. This is where polarity tension across sources
  surfaces: if P1 affirms X and P2 negates X, the global layer must record the
  conflict, not resolve it silently.

This is where the **living updateable graph** should live.

Do **not** make the raw triplet layer carry all the mutability burden.
Keep the triplets as the source-grounded fact layer, and let the throughline
layer absorb:

- rewritten conclusions
- trust-score updates
- merges of equivalent claims
- branching into competing claims when evidence conflicts

### Throughline Schema

```text
throughline_id   TEXT PRIMARY KEY
page_id          TEXT
claim_text       TEXT   # mutable, LLM-rewritten only when evidence warrants refine
thesis_fingerprint TEXT # frozenset hash of normalized supporting_fks — dedup key
supporting_fks   LIST   # source_ids, triplet_ids, and/or page_ids that entailed this conclusion
source_fks       LIST   # concrete user-visible provenance used for the claim
fact_fks         LIST   # normalized facts/triplets supporting the claim
q_score          REAL   # runtime-learned trust score; always updated from prior, never reset
visit_count      INT    # total confirmed retrievals; use as frequency signal or for α=1/n decay
merge_score      REAL   # how strongly this aligns with another candidate claim
status           TEXT   # active | competing | deprecated | merged
merged_into      TEXT   # nullable canonical survivor id
canonical        BOOL   # whether this is the current canonical phrasing
created_at       DATETIME
updated_at       DATETIME
history          JSON
```

### Storage rule

If you want this to stay manageable, store throughlines as **rows or nodes attached
to page ids**, not as direct replacements for triplets.

That gives you:

- stable fact storage
- mutable conclusion storage
- explicit provenance
- easier merge and rollback semantics

The graph remains "living" because the conclusion layer evolves, not because the
raw evidence layer keeps getting rewritten destructively.

### Thesis Identity and Deduplication

**The identity of a throughline is its premise set, not its claim text.**

`thesis_fingerprint = frozenset(normalize(supporting_fks))`

- If an inference pass produces a conclusion whose entailing premise set matches
  an existing throughline's fingerprint → **update**, do not insert.
- If no match → create a new throughline node.

This prevents duplicate theses drifting apart when the same premises are retrieved
under different queries. The premise grouping is the canonical key.

**Defer to current claim text**: a score update alone does not rewrite `claim_text`.
The existing phrasing is canonical until evidence explicitly warrants a refine.
Score and text are updated on independent triggers.

### Inference-Time Entailment and Write-Back

Entailment is never pre-computed at ingestion. It is evaluated at inference time,
against a specific candidate conclusion, over a flat retrieved premise set.

```text
query
    |
    v
retrieve all relevant premises flat (BM25 + dense; no entailment pre-tagged)
    |
    v
for each candidate conclusion / throughline:
    classify each premise: {entails | neutral | contradicts}
    |
    v
entailing_premises = {p for p in retrieved if classify(p, conclusion) == entails}
    |
    v
fingerprint = frozenset(normalize(entailing_premises))
    |
    +- fingerprint matches existing throughline:
    |    update q_score (see below)
    |    if evidence warrants: refine claim_text
    |
    +- no match:
          create new throughline node
          supporting_fks = entailing_premises
          q_score = initial prior
```

The conclusion node ties the entailing premises together. No direct cross-premise
edges are needed — the shared pointer to the conclusion is the connection.
Premises that were retrieved but classified neutral or contradicting are not tagged
to the conclusion (contradicting premises may receive a polarity edge instead).

### Throughline Update Cycle

```text
inference pass completes
    |
    v
fingerprint match found
    |
    v
q_score <- q_old + α(r - q_old)    ← score always updated; prior never reset
visit_count += 1
    |
    v
LLM critic pass (see below)
    |
    +- no deficiency found:   claim_text unchanged (accept as-is)
    +- gap identified:        claim_text refined to shore up the deficiency
    +- contradiction:         q_score driven down; status → competing or deprecated
```

**The old score is always the prior.** Repeated confirmation of the same premise set
compounds the score asymptotically toward 1. Contradiction drives it down from
wherever it currently stands. The score is never discarded or restarted.

The roles are separate:
- **Q-score** updates on every retrieval that includes this premise set
- **LLM** intervenes only when it can identify a specific deficiency in the existing claim

### LLM Critic Prompt Contract

The LLM has full agency on a fingerprint match. It sees the existing conclusion
and the new entailing premises and decides autonomously whether the existing
conclusion is sufficient or whether a revised synthesis is warranted.

```text
SYSTEM:
You are reasoning over an existing conclusion and new supporting evidence.
Decide whether the existing conclusion adequately captures the new premises.
If it does, accept it. If you can produce a meaningfully better synthesis,
generate a revised conclusion and score your confidence in the improvement.
Do not revise for trivial rephrasing — only when the revision genuinely
adds coverage or corrects a misrepresentation.

USER:
Existing conclusion:
  "{claim_text}"

New premises confirmed to support this conclusion:
  {new_entailing_premises}

Output format:
  verdict: accept | revise
  claim_text: <existing conclusion if accept, revised conclusion if revise>
  revision_score: <float 0–1 reflecting your confidence in the revised conclusion, null if accept>
  rationale: <one sentence, null if accept>
```

**If accept:** score update proceeds mechanically — `q_new = q_old + α(r - q_old)`.

**If revise:** `revision_score` from the LLM becomes `r` in the update.
A high-confidence revision (`revision_score ≈ 1`) drives the score up sharply.
A tentative revision (`revision_score ≈ 0.5`) produces a conservative update.
The prior `q_old` is always preserved as the anchor — the revision score
shifts it, it does not replace it.

This keeps the score grounded in accumulated history while allowing the LLM's
own quality judgment to inform how much a revision moves the needle.

### Minimal score update

```text
q_new <- q_old + α(r - q_old)
```

Where `r` is the latest evidence outcome:

- support / entailment -> positive reward
- neutral / mixed -> weak or zero reward
- contradiction -> negative reward or sharp downweight

**Emergent frequency scoring.** With fixed α and binary `r=1` on every confirmation,
this update converges monotonically toward 1 — making `q_score` a de-facto
confirmation counter. That is useful: frequently retrieved and confirmed premise sets
naturally accumulate higher scores, surfacing the most-used thesis positions.

**To separate frequency from strength**, track `visit_count` alongside `q_score`
and use a decaying learning rate `α = 1 / visit_count`:

```text
visit_count += 1
α = 1 / visit_count
q_new <- q_old + α(r - q_old)    ← running average; converges to mean(r) over all visits
```

Under this regime:
- `q_score` reflects average entailment strength across all retrievals
- `visit_count` reflects raw frequency independently
- A thesis confirmed 100× with weak signal and one confirmed 5× with strong signal
  are distinguishable; with fixed α they would conflate

Use fixed α when frequency IS the signal you want. Use `α = 1/n` when you want
mean strength and frequency as separate queryable dimensions.

You do not need an elaborate learned merger before this becomes useful.

### Mergeable conclusion rule

Conclusions should be mergeable, but only at the conclusion layer.

Use a merge when:

- two claims are semantically equivalent or differ only in phrasing
- their evidence is compatible (overlapping or identical `supporting_fks`)
- keeping both would create duplicate conclusions rather than real alternatives

When merging:

1. choose a canonical survivor
2. union the `source_fks`, `fact_fks`, and `supporting_fks`
3. preserve both prior phrasings in `history`
4. mark the loser as `status = merged`
5. set `merged_into` on the loser
6. update the survivor's `q_score` from the combined evidence

Do **not** merge contradictory claims just because they touch the same entities.

### Competing Throughlines

Do not force one conclusion too early.

Multiple throughlines may coexist over the same evidence cluster. They compete
by `q_score`. The highest score is the current best abductive explanation, not
the permanent winner.

This is the escape hatch that keeps the living graph from becoming a headache:

- equivalent claims -> merge
- genuinely different claims -> keep as competing
- disproven claims -> deprecate, do not erase history

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

### Dense triplet representation

In addition to local triplet rows, maintain a **retrieval-time concatenated
representation** for the surrounding unit you want to retrieve (page, chunk, or
article). Build it by:

1. extracting canonicalized triplets in source order
2. normalizing each `(S, P, O)` to the ontology winner ids
3. concatenating them with `[SEP]` separators
4. embedding the resulting string

This gives you:

- a sparse lexical column for BM25
- a dense semantic column for embedding search

Use both. Do not make dense retrieval replace sparse retrieval outright.

### Triplets as the semantic compressor

Before adding another heavy summarizer, treat the triplet layer itself as the
first semantic compression step.

The ordered triplets are already a kind of structured auto-encoding of the source:

- they discard most irrelevant syntax
- they preserve actor / relation / target structure
- they are stable enough to support sparse and dense retrieval together

So the default dense object should usually be the **ordered triplet sequence**,
not a second LLM-generated semantic summary unless you can show a clear gain.

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
3. Write a HyDE-style translated query for the target evidence or throughline
4. Embed that translated query
5. Route into the nearest semantic cluster (and optionally adjacent clusters)
6. Retrieve candidate **pages** by intent first
7. Run sparse retrieval over `bm25_text`
8. Run dense retrieval over `triplet_sequence_text` embeddings
9. Fuse sparse, dense, and quality signals
10. Use entity-bag overlap as supporting evidence, not the primary key
11. BM25-narrow supporting triplets
12. Run NLI or judge validation on the narrowed set
13. Build a user-visible evidence packet of retrieved sources and extracted facts
14. Decide whether to reinforce, refine, merge, create, or reject
15. Update page and throughline state
16. Persist score updates, cluster metadata, and history

The organizing chain is:

`query -> intent -> HyDE query -> cluster -> sparse+dense retrieval -> triplets -> sources+facts -> NLI/judge -> throughline update`

### HyDE query translation

The dense query should not always be the raw user string.

Prefer a translated query that states the target memory in the form the store is
meant to retrieve:

- intended objective
- likely entities
- likely predicates
- likely throughline shape

This HyDE-style text is what you embed for cluster routing and dense retrieval.

## Final Answer Contract

The sparse/dense/cluster representation is **guidance for retrieval**, not the
final user-facing answer.

When the LLM produces the final response, it should expose:

1. the **retrieved sources**
2. the **facts extracted from those sources**
3. the **updated conclusion** written from that evidence

The user should see the evidence surface, not just the rewritten throughline.

### Conclusion synthesis rule

The conclusion is produced from:

`retrieved source -> extracted facts -> LLM synthesis -> updated conclusion`

Do not present `bm25_text`, `triplet_sequence_text`, `embedding_ref`, or
`cluster_id` as if they are the evidence itself. They are retrieval machinery.

### User-visible response shape

At minimum, the final answer should contain:

- `sources`: the retrieved source ids, titles, spans, or citations actually used
- `facts`: the normalized facts or triplets grounded in those sources
- `conclusion`: the LLM's updated synthesis from those sources and facts

If the answer updates an existing throughline, the rewritten conclusion should still
point back to the concrete sources that justified the update.

### Throughline update rule

The throughline is the current best conclusion, but it should be revised from
retrieved evidence rather than treated as a source in isolation.

- sources remain the provenance
- facts remain the normalized evidence layer
- the throughline/conclusion is the current synthesis over that evidence
- score updates and merges happen on the throughline record, not on the cited sources

## Ranking Surface

The retrieval surface is deliberately layered.

### Candidate narrowing
- BM25 over triplet or page text fields
- dense similarity over `triplet_sequence_text` embeddings
- cluster routing from HyDE query embeddings
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

### Dual-column retrieval contract

Treat sparse and dense retrieval as separate columns with separate jobs:

- **Sparse** (`bm25_text`) catches exact lexical overlap, rare names, and sharp token cues
- **Dense** (`triplet_sequence_text` embedding) catches paraphrase, reordered wording,
  and semantic proximity across triplet bundles

Dense text should be the ordered `[SEP]`-joined triplet string, not a loose summary.
The point is to embed the extracted semantic structure directly.

### Cluster routing

Dense retrieval should also maintain a cluster layer.

- build embeddings from `triplet_sequence_text`
- min-max normalize or otherwise normalize features before final vector normalization
- L2-normalize vectors before clustering when the geometry is directional
- cluster the dense space
- store `cluster_id` beside the sparse and dense retrieval fields

At query time:

1. embed the HyDE-translated query
2. derive its nearest cluster
3. retrieve primarily within that cluster
4. optionally expand to neighboring clusters when recall is too low

The cluster is a routing aid, not the memory identity.

### Soft cluster routing, not hard gating

Do **not** retrieve only from a single winning cluster.

That creates a recall trap: if the nearest cluster is slightly wrong, you miss
useful evidence in nearby or minority clusters.

Better pattern:

1. run a **global seed retrieval** across all clusters with cosine similarity
2. inspect the cluster distribution of the top-ranked seeds
3. allocate retrieval budget across clusters from that distribution
4. run in-cluster retrieval with diversity control
5. keep a small global backstop outside the selected clusters

This makes clusters a prior, not a prison.

### Budget allocation rule

One workable strategy is:

- turn the top global seed scores into a softened cluster distribution
- allocate per-cluster budget roughly in proportion to that distribution
- enforce a minimum floor so minority clusters with real signal still get sampled

That is close to what you proposed and is a good default.

### In-cluster retrieval

Within each selected cluster, use something like **MMR** or another diversity-aware
retriever so the cluster budget does not collapse onto near-duplicates.

Good pattern:

- cluster-level budget for recall
- MMR within cluster for diversity
- one small global tail for surprise recall

### Global backstop

Always keep a few non-cluster-restricted results in the final candidate pool.

This is the simplest guardrail against:

- bad cluster assignment
- underfit clustering
- novel cross-cluster queries
- evidence that legitimately spans more than one semantic region

### Retrieval ownership

This routing policy belongs to the retrieval layer, not the ontology layer.

- `kg_ontology` decides canonical ids
- `agentic_kg_memory` decides cluster budgets, MMR, and recall/backstop policy

If you later turn your GIST retriever into a dedicated skill, it should sit here
as the retrieval implementation surface rather than inside ontology.

That skill is now `gist-retriever`.

- `agentic_kg_memory` defines the retrieval policy and memory-update contract
- `gist-retriever` implements the layered retrieval engine
- `kg_ontology` supplies canonical ids but does not own retrieval budgets

### Retrieval sub-skill

Treat `gist-retriever` as a **sub-skill within `agentic_kg_memory`**.

Use it when `agentic_kg_memory` needs a concrete retrieval implementation for:

- BM25 + dense seed gathering
- RRF fusion
- L2 triplet expansion
- cluster-mixture budgeting
- MMR within cluster slices
- ColBERT reranking

In this repo, that sub-skill should default to the **derived Chroma triplet space**,
not a pgvector dependency.

### Why graph-based clustering is reasonable

Do not assume semantic memory is nicely spherical.

Graph-based methods such as spectral clustering are often a better fit than plain
KMeans because semantic neighborhoods can be curved, chained, or density-shaped
rather than round blobs. The transferable point is:

- cluster by connectivity structure in embedding space
- do not treat Euclidean centroid distance as the only geometry that matters

### Cluster evaluation contract

If clustering is fitted, persist:

- `bss`
- `tss`
- `bss_tss_ratio`
- cluster sizes
- the chosen cluster count

The final `bss_tss_ratio` belongs in `C:\Users\user\memory-bank\cluster_metrics.json`.

Treat these cluster metrics as **diagnostics**, not as the default winner metric
for quote-embedding retrieval systems. The real selection target should stay on
retrieval quality unless clustering has been shown to materially improve it.

In that setting, the better tuning surface is usually the retrieval architecture:

1. broad-pool size
2. GIST utility vs diversity weight
3. graph path weight / hop budget
4. local community threshold or expansion budget inside layer 2
5. entity-overlap bonus
6. whether local grouping is enabled at all

The weak point is that local clustering can still help summarize or organize the
retrieved evidence after recall has already been won.

### Storage guidance

One workable storage split is:

- SQLite or equivalent for page rows, triplet metadata, counts, scores, and `bm25_text`
- Chroma or another vector store for `triplet_sequence_text` embeddings
- a shared `page_id` / `embedding_ref` seam between the two

Keep the sparse and dense surfaces linked, not duplicated blindly.

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
- merge equivalent throughlines at the conclusion layer
- preserve competing throughlines if they are still meaningfully distinct
- append a merge record to history

### Throughline-specific merge policy

For conclusions specifically:

- merge **equivalent** claims
- keep **competing** claims side by side
- deprecate **collapsed or disproven** claims

That lets the graph remain updateable without pretending every new conclusion
must overwrite the old one.

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
