---
name: agentic_kg_memory
description: >
  Graph-backed semantic memory and reasoning protocol. Use when extracting
  premises into a knowledge graph, retrieving evidence with BM25/NLI, updating
  memory entries from new evidence, or maintaining wiki-like throughlines that
  evolve as the graph learns.
status: active
tier: L1
last_validated: 2026-04-28
---

# Agentic KG Memory

## Retrieval Tier: L1 (Vector / Semantic)

This skill is **L1** in the three-tier knowledge retrieval cascade:

| Tier | Skill | Role |
|---|---|---|
| L2 | `memory-bank` / skills markdown | Compiled durable knowledge — try first |
| **L1** | **`agentic_kg_memory`** | **Atomic triplets and semantic pages — try if L2 misses** |
| L0 | `deep-research` | Live web evidence — last resort |

When L1 retrieval surfaces stable, reusable patterns, promote them to L2 (write or update a skill markdown file).

## Memory Scope: Global vs Repo

Each wiki page carries a `scope` field:

- `global` — cross-project facts, patterns, procedures → stored in `C:\Users\user\memory-bank\`
- `repo` — project-specific context, architecture decisions, code-level facts → stored in `[repo-root]\.memory-bank\`

Not both. If a fact is genuinely reusable across all projects, it is global. If it is specific to one codebase, it is repo-scoped.

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
- `C:\Users\user\memory-bank\chroma\`
- `C:\Users\user\memory-bank\clusters.json`
- `C:\Users\user\memory-bank\cluster_metrics.json`

The SQLite file is the sparse/metadata surface.
The Chroma directory is the dense embedding surface.

> **Scope tags**: each wiki page should carry a `scope` field — `global` or `repo`.
> Global pages belong in `C:\Users\user\memory-bank\`. Repo-specific pages belong
> in `[repo-root]\.memory-bank\`. The SQLite and Chroma backends are partitioned
> the same way: one global instance, one per active repo (started with `--memory-dir`
> on the MCP server).

### Setup actions

When running setup, do all of the following:

1. Create `C:\Users\user\memory-bank\wiki_memory.sqlite3`
2. Create or migrate the page table:
   - `bm25_text`
   - `triplet_sequence_text`
   - `embedding_ref`
   - `cluster_id`
3. Create the graph tables: `kg_nodes`, `kg_edges` (with indexes on `dst_slug` and `edge_type`)
4. Create `C:\Users\user\memory-bank\chroma\` as the Chroma persist directory
5. Build `triplet_sequence_text` from canonicalized extracted triplets in source order
6. Embed `triplet_sequence_text` and store vectors in Chroma
7. Cluster the normalized dense vectors
8. Write the winning `cluster_id` back into SQLite
9. Persist human-readable cluster outputs to:
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

## Compiled Wiki Pattern

`agentic_kg_memory` is the closest thing in this repo to the **LLM Wiki** pattern:
it compiles source material into a persistent intermediate layer rather than
re-reading raw prose from scratch on every query.

The practical split maps to a standard folder convention:

| Layer | Folder | Contents |
|---|---|---|
| 1 | `raw/` | Immutable source documents, quotes, spans, notes — never edited |
| 2 | `wiki/` | Durable synthesized pages updated as new evidence arrives |
| 3 | `derived/` | KG indexes, cluster outputs, embeddings — rebuildable from `wiki/` |

A `sources.md` file at the wiki root tracks provenance: title, URL/path, date added,
and what each source contributes. Every claim in `wiki/` must trace back to an entry
in `sources.md`.

The three layers correspond to:

1. **Raw sources** (`raw/`) — immutable source documents, quotes, spans, or notes
2. **Pages / wiki entries** (`wiki/`) — durable synthesized memory surfaces updated as new
   evidence arrives
3. **Throughlines** (`derived/throughlines/`) — the current best abductive or deductive conclusions over
   those pages

KnowledgeWeaver is a useful concretization of this pattern:

- the canonical artifact stays readable on disk
- the compiled index is secondary and rebuildable
- typed units of knowledge are allowed instead of one undifferentiated summary blob

The typed-unit idea is valuable here. A page layer may contain distinct memory forms
such as:

- `concept`
- `fact`
- `experience`
- `narrative`
- `opinion`
- `known_unknown`

This means the memory layer should accumulate:

- prior synthesis
- cross-page links
- contradictions that remain unresolved
- revised conclusions when new evidence changes the best fit

The store is not just a retrieval cache. It is a **maintained knowledge surface**
that compounds over time.

## Consolidation Tiers

Information should not stay at its entry tier forever. Promote it upward as
evidence accumulates and confidence grows.

| Tier | Label | What lives here | Lifetime |
|---|---|---|---|
| 0 | **Working memory** | Raw observations from the current session: unprocessed spans, scratch notes, transient context | Ephemeral; compressed at session end |
| 1 | **Episodic memory** | Session summaries compressed from working memory; what happened in a bounded interaction | Medium; decays if not reinforced |
| 2 | **Semantic memory** | Cross-session facts consolidated from episodes; stable claims about the domain | Long; updated but not easily erased |
| 3 | **Procedural memory** | Workflows, patterns, and decision rules extracted from repeated semantics | Longest; changes only when patterns break |

Each tier is more compressed, more confident, and longer-lived than the one below it.

### Promotion rules

Promote a memory entry one tier when:
- **Working → Episodic**: the session ends and the observation survived compression
- **Episodic → Semantic**: the same claim appears across multiple episodes with consistent support
- **Semantic → Procedural**: a cluster of semantic facts resolves to a reusable workflow or decision rule

Demotion is also valid: if a semantic claim is repeatedly contradicted, demote it back to episodic status pending re-evaluation.

### Mapping onto the existing three-tier stack

The three-tier confidence stack in this skill maps naturally:

| This skill | Consolidation tier |
|---|---|
| Triplet | Episodic (one source's grounded observations) |
| Page / wiki entry | Semantic (cross-source, cross-session compiled fact cluster) |
| Throughline | Procedural / high-confidence semantic (stable best-fit conclusion) |

Working memory (tier 0) lives in the current session context — `continuity-log` or
equivalent scratchpad — before it is compressed into triplets at session end.

## Canonical Artifact Rule

The human-readable page layer is the canonical artifact.

- markdown pages, typed wiki entries, or equivalent readable files are the source
  of truth for the compiled memory layer
- SQLite / Chroma / Postgres / pgvector indexes are compiled access structures
- those compiled indexes should be safe to delete and rebuild from the canonical
  page layer without manual knowledge repair

This keeps the memory inspectable, diffable, and versionable while still allowing
heavier retrieval backends.

## Maintenance Loop

The default operating loop is:

1. **Ingest**
   - read new source material
   - extract and normalize triplets
   - update the relevant pages rather than only appending new isolated facts
   - revise throughlines when the new evidence changes the best explanation
   - preserve contradiction and uncertainty explicitly
2. **Query**
   - retrieve the relevant pages and supporting facts
   - synthesize an answer from evidence
   - if the answer creates a durable new comparison, summary, or connection,
     file it back into the page / throughline layer instead of letting it die in chat history
3. **Lint**
   - scan for stale claims superseded by newer evidence
   - detect orphan pages with weak linkage
   - detect missing cross-references or missing entity/concept pages
   - flag unresolved conflicts and known unknowns
   - **Supersession**: when a newer claim contradicts or replaces an older one, do not just flag it — link the two claims explicitly, timestamp the supersession event, and mark the older claim stale. The old version is preserved in history but deprioritized in retrieval. This keeps the wiki self-correcting rather than just accumulating notes about contradictions.

This is the behavioral difference between a one-shot retriever and a living memory system.

## Automation Hooks

Manual ingest/query/lint loops work at small scale but should be automated.
The goal is near-zero maintenance burden for the human once the initial schema is established.

Recommended event hooks:

| Event | Action |
|---|---|
| **on_new_source** | auto-ingest, extract triplets, update graph, update index.md |
| **on_session_start** | load relevant context pages based on recent activity and current task |
| **on_session_end** | compress session observations into episodic entries, file insights back to pages |
| **on_query** | check whether the answer is worth filing back (confidence > threshold) |
| **on_memory_write** | check for contradictions with existing knowledge, trigger supersession if warranted |
| **on_schedule** | periodic lint, consolidation pass, temporal retention decay |

The human stays in the loop for curation and direction. Bookkeeping — the part that
causes people to abandon wikis — should be fully automated.

Hook fidelity scales with implementation maturity:

- **Minimal**: manual trigger, agent-assisted each step
- **Partial**: session-boundary hooks automated (start/end compression)
- **Full**: all hooks wired; the wiki tends toward health on its own

GBrain (Garry Tan, MIT) is a production reference for "Full" fidelity: 21 cron jobs
running autonomously, self-wiring entity graph, overnight citation repair and
consolidation. Its cron job taxonomy is a useful checklist when wiring the `on_schedule`
hook: `entity_enrichment`, `citation_repair`, `consolidation_pass`, `retention_decay`,
`backlink_audit`.

## Human-Readable Operating Surfaces

For small-to-medium corpora, keep two markdown-level navigation aids alongside the
structured storage:

- `index.md` — content-oriented catalog of pages, grouped by type with one-line summaries
- `log.md` — chronological ingest/query/lint journal for recent system activity

These files are not the memory identity themselves. They are **operator and agent
surfaces** that make the page/throughline layer inspectable and navigable before
heavier retrieval machinery is required.

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

The ingest pipeline has **two passes**:

### Pass 0 — Entity wiring (zero LLM calls)

Before any LLM extraction, run a fast regex/NER pass that detects known entity names
(people, organizations, places) and upserts them into the **knowledge graph** as typed
directed edges.

**Why a graph instead of BM25 for entity relations:**

BM25 over synset lemmas does approximate single-hop entity queries — if
`Alice works_at Acme` was extracted, the `bm25_index` contains `"alice person works_at
acme organization"` and "who works at Acme" surfaces it. For single-hop, BM25 is
competitive.

The graph wins on two axes:
1. **Scalability**: BM25 IDF weights drift with each new document. A graph adjacency
   table is `INSERT OR REPLACE` — append-only, no global stats, no recompute ever.
2. **Multi-hop traversal**: "who funded the companies Alice advises?" requires two hops.
   BM25 requires both entities to co-occur in a single document. A graph answers it
   natively via recursive CTE.

Your triplets already ARE edges: subject → predicate → object maps 1:1 to a typed
directed edge. The graph is a natural structural consequence of triplet extraction, not
an additional abstraction.

**Graph schema (SQLite):**

```sql
CREATE TABLE IF NOT EXISTS kg_nodes (
    slug      TEXT PRIMARY KEY,
    label     TEXT NOT NULL,
    node_type TEXT NOT NULL,  -- person|org|concept|event|place|skill
    page_ref  TEXT,           -- FK to wiki page slug if this node has a full page
    created_at TEXT DEFAULT (datetime('now'))
);

CREATE TABLE IF NOT EXISTS kg_edges (
    src_slug  TEXT NOT NULL,
    dst_slug  TEXT NOT NULL,
    edge_type TEXT NOT NULL,  -- works_at|attended|invested_in|founded|advises|mentions|implies|contradicts
    confidence REAL DEFAULT 1.0,
    polarity   TEXT DEFAULT 'affirmed',  -- affirmed|negated
    source_page TEXT,                    -- which page created this edge
    created_at  TEXT DEFAULT (datetime('now')),
    PRIMARY KEY (src_slug, dst_slug, edge_type)
);

CREATE INDEX IF NOT EXISTS idx_kg_edges_dst ON kg_edges(dst_slug, edge_type);
CREATE INDEX IF NOT EXISTS idx_kg_edges_type ON kg_edges(edge_type);
```

**Single-hop query (SQLite):**
```sql
-- Who works at Acme?
SELECT n.slug, n.label FROM kg_edges e
JOIN kg_nodes n ON e.src_slug = n.slug
WHERE e.dst_slug = 'acme' AND e.edge_type = 'works_at' AND e.polarity = 'affirmed';
```

**Multi-hop query (recursive CTE):**
```sql
-- Who funded companies that Alice advises?
WITH advised AS (
    SELECT dst_slug AS company FROM kg_edges
    WHERE src_slug = 'alice' AND edge_type = 'advises'
)
SELECT DISTINCT src_slug AS funder FROM kg_edges
WHERE dst_slug IN (SELECT company FROM advised)
  AND edge_type = 'invested_in';
```

Pass 0 populates this graph from entity co-occurrence alone (no LLM). Pass 1 enriches
it with semantically extracted predicate types and confidence.

### Pass 1 — LLM triplet extraction

After entity wiring, the LLM extraction pass runs the full semantic layer. Extracted
triplets are **written to both** the BM25 index (for semantic/fuzzy queries) and the
graph (`kg_edges`) as typed edges.

**Query routing:**
| Query type | Use |
|---|---|
| Semantic / fuzzy ("what do we know about memory?") | BM25 + vector (Chroma) |
| Relational / structural ("who works at X?", "what does Y imply?") | Graph traversal (`kg_edges`) |
| Hybrid ("what did people who work at X say about memory?") | Graph narrows candidates → BM25 re-ranks |

The high-level chain is:

`source text -> LLM extraction (with guidance-resolved synsets) -> normalized triplets -> ontology winner ids -> bm25_index column + kg_edges -> storage`

### Synset/Hypernym Resolution via Guidance

`kg_ontology` owns the synset/hypernym candidate-generation and canonicalization logic.
At this layer, the contract is only:

- extract `(subject, predicate, object, polarity, inference_type)` from source text
- send the extracted spans to [[kg_ontology]] for candidate narrowing and winner selection
- consume the returned canonical ids and BM25 enrichment when writing `kg_nodes`, `kg_edges`, and retrieval fields

See [[kg_ontology]] for the full guidance pipeline, visibility rules, and fallback policy.

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
triplet      extraction prior      -> observed/inferred + explicit confidence
page         retrieval fitness     -> objective/throughline/entity fit
throughline  runtime posterior     -> MemRL-style Q-score
```

Each tier answers a different question:

- **Triplet**: was this locally well-grounded?
- **Page**: is this memory entry a good semantic match for the current task?
- **Throughline**: has this conclusion held up under repeated use?

## Forgetting and Temporal Decay

Evidence-based scoring (reinforce/weaken) handles contradictions. Time-based
decay handles **stale-but-uncontradicted** claims — the slow rot that makes wikis
become noise over time.

Apply an Ebbinghaus-style retention model:

```text
retention(t) = e^(−t / stability)
```

Where:
- `t` is time since last access or confirmation
- `stability` increases with each reinforcement (reset and lengthened by each access)

Practical implementation over the Q-score:

```text
effective_q = q_score * retention(time_since_last_access)
```

This does not erase the stored `q_score`. It downweights the **effective retrieval
priority** at query time without destructively modifying the record.

### Decay rate by memory type

Decay rates should reflect how fast content becomes stale:

| Memory type | Decay rate |
|---|---|
| Transient bug / incident observation | Fast (days → weeks) |
| Project decision | Medium (weeks → months) |
| Architecture pattern | Slow (months → years) |
| Procedural workflow | Very slow |

### Retention reset

Every confirmed access or reinforcement resets the clock:

```text
stability_new = stability_old * growth_factor  # e.g. growth_factor = 1.5
last_accessed = now()
```

Over multiple confirmed retrievals the same claim becomes progressively harder to
forget, which mirrors how important knowledge should compound.

### Forgetting vs. deletion

Do not delete decayed memories. Instead:

- drop `effective_q` below the retrieval threshold
- mark as `status = dormant` when effective_q drops below a floor
- promote back to active if later evidence re-confirms the claim

This is the semantic equivalent of moving something to a bottom drawer: deprioritized
but recoverable.

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
confidence        # explicit extraction-time confidence, mutable as downstream evidence updates it
created_at
updated_at
```

When serializing a triplet for training or audit surfaces, emit the confidence inline with
epistemics:

```text
subject | predicate (observed, confidence=0.92) | object
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

Each extracted fact should carry an explicit confidence scalar alongside its
`observed` / `inferred` tag. If the extractor does not emit one directly, initialize it
from epistemics:

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

If the query produces a durable synthesis rather than a transient answer, promote
that synthesis back into the page / throughline layer as a new or revised memory
artifact. Querying is allowed to improve the wiki, not just read from it.

## Graph Traversal for Discovery

Standard retrieval answers "what evidence matches this query?" Graph traversal
answers "what does changing X affect?" — impact analysis and lateral discovery.

When a query concerns downstream effects, dependencies, or structural impact, use
the typed edge layer rather than (or in addition to) semantic similarity:

```text
query: "what is the impact of upgrading Redis?"

1. Locate the Redis entity node
2. Walk outward along typed edges:
   - "depends_on" → find all entities that depend on Redis
   - "uses" → find all contexts where Redis is used
   - "caused" / "fixed" → find incident or resolution nodes
3. Collect the reached nodes as candidate pages
4. Score by traversal depth + edge weight + q_score of reached pages
5. Return as a ranked evidence bundle
```

This finds connections that semantic similarity misses — things that are structurally
related but lexically distant.

### Traversal rules

- prefer typed edges over generic "relates to" edges for precision
- apply a hop budget (default: 2–3 hops) to prevent unbounded expansion
- weight outgoing edges by their confidence scores
- merge traversal candidates with semantic retrieval candidates before ranking (RRF)
- traversal is a supplement to hybrid search, not a replacement

### When to use traversal

Use graph traversal when:
- the query asks about impact, dependencies, or downstream effects
- the query asks about the history of a specific entity or decision
- keyword/semantic search returns low-quality results for a structural question
- the corpus has dense typed-relationship coverage

Use standard hybrid retrieval when:
- the query is open-ended semantic exploration
- the corpus does not have explicit typed edges yet

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

## Crystallization

Crystallization is the process of taking a completed chain of work — a research
thread, a debugging session, a multi-step analysis — and automatically distilling
it into a structured digest that becomes a first-class wiki artifact.

This is distinct from the query write-back pattern. Write-back files a single
answer. Crystallization distills an **entire session or work chain** into its
durable essence.

### Crystallization contract

A crystallization digest should capture:

1. **Question** — what was the original intent or driving question?
2. **Findings** — what did we learn? (as normalized triplets or semantic memory entries)
3. **Entities involved** — which files, concepts, people, systems were relevant?
4. **Lessons** — what decision rules or patterns emerged that should be reused?
5. **Open questions** — what remains unresolved?

### Output artifacts

A crystallization pass produces two types of artifacts:

- **Digest page** — a first-class wiki page with intent, objective, and the
  structured findings above; ingested and indexed like any other page
- **Standalone facts** — individual lessons and patterns extracted from the digest,
  filed directly as triplets or semantic memory entries that reinforce or update
  existing knowledge

### When to crystallize

Crystallize at the end of:
- a completed research thread
- a resolved debugging session
- a completed analysis or comparison task
- any multi-turn chain where the conclusions should outlive the session

Explorations are a source, just like an article or a paper. The wiki should treat
them that way: ingest the results, update the graph, strengthen or challenge existing claims.

### Crystallization vs. session compression

- **Session compression** (episodic tier) — compress raw observations from the
  current session into episodic entries; runs at session end automatically
- **Crystallization** — distill a purposeful work chain into a structured, high-quality
  digest; requires intent and judgment; produces a named, referenceable wiki artifact

Use crystallization for work chains that have a clear question and answer.
Use session compression for general activity logs.

---

## MCG Foundation — Meta Context Graph Architecture

The skill library, `agentic_kg_memory`, and `kg_ontology` collectively implement the
**Meta Context Graph (MCG)** architecture (Tekiner, 2025) applied to automated software
development instead of knowledge graph construction. Understanding this framing prevents
architectural confusion about what belongs where.

### The Dual-Graph Model

```
Domain KG (DKG)                   Context Graph (CG)
────────────────────               ─────────────────────────────────────
What exists in the world           How and why it was built
Entities + Relationships           Decisions + Patterns + Tribal Knowledge

kg_nodes, kg_edges                 decisions, patterns, tribal_knowledge
                                   tk_candidates, dialogue_turns

Owned by: kg_ontology +            Owned by: agentic_kg_memory (this skill)
          agentic_kg_memory
```

For software development, the DKG is the codebase + domain model (entities: modules,
functions, data types, APIs). The CG is everything about how the codebase was built and
how decisions were made: implementation rationale, correction patterns, architectural
choices, and the accumulated tribal knowledge about what works.

### 4-Layer Context Hierarchy (L4 → L1 precedence)

Agents apply the **most specific applicable rule first**, falling back toward universal.

| Layer | Scope | Software Dev Examples |
|---|---|---|
| **L4 Project/Runtime** | Immediate session | "This PR uses the legacy auth module naming from 2019" |
| **L3 Organisation/Team** | Team conventions | "We use trunk-based dev; feature flags over branches" |
| **L2 Industry/Domain** | Domain-specific rules | "OAuth2 PKCE required for public clients in fintech" |
| **L1 Universal/Base** | Best practices | "Dates in ISO 8601; functions under 50 lines" |

Query resolution: start at L4, fall back to L1. A new project automatically inherits
both L3 team conventions and L2 domain standards without manual configuration.
The `context_layer` field on every Decision, Pattern, and TribalKnowledge node
encodes which layer a rule belongs to.

### Three Memory Types (Tekiner → CoALA → Hu et al.)

| MCG term | CoALA type | Hu et al. form/function | Skill library component |
|---|---|---|---|
| Decision Traces | Episodic | Token-level / experiential | `agentic-harness` learnings.jsonl |
| Patterns + Tribal Knowledge | Semantic | Token-level / factual | `agentic_kg_memory` (this skill) + `skill-wiki` Pattern Store |
| Proven schemas / resolution strategies | Procedural | Token-level / experiential | The SKILL.md files themselves |
| Session state | Working | Latent / working | `continuity-log`, `memory-bank` active context |

**The key insight from cognitive science (Tulving, 1972; CoALA, arXiv:2309.02427):**
procedural memory cannot be stated as facts — it is embodied in the ability to perform
the task. The skills are procedural memory: they cannot be summarised into a prompt;
they must be invoked to have effect. RAG-retrieving skill text is a degenerate case.

**ACE (arXiv:2510.04618, ICLR 2026)** proves the quantitative case: contexts treated as
"evolving playbooks" that accumulate via generation→reflection→curation loops yield
+10.6% on agent benchmarks vs static context baselines. The Pattern Store vetting pipeline
(generate → apply 3× → reflect → curate into skill) is an implementation of this loop.

### 6-Agent Kitchen Brigade (Adapted for Software Dev)

Tekiner's original brigade is for KG construction. For software development:

| Role | MCG Original | Software Dev Equivalent |
|---|---|---|
| Document Agent | Classifies documents, finds similar projects | `react-agent` — scopes task, finds prior art |
| Schema Agent | Designs entity/relationship types | `architecture` — module boundaries, contracts |
| Extraction Agent | Pulls entities from text | `code` — implementation |
| Resolution Agent | Merges duplicates, captures overrides | `code-review` — dedup, canonicalize |
| Validation Agent | Checks quality against rules | `validation` — tests, lint, harness gate |
| Feedback Agent | Captures corrections → context graph | `agentic-harness` learnings.jsonl + Pattern Store |

The CG is the **shared memory** layer: what the Feedback Agent captures becomes the
Extraction Agent's starting point on the next task. One agent's correction is another
agent's precedent.

---

## Episodic Memory — Time-Indexed Cross-Session Recall

Episodic memory stores **what happened, when, and why** — the decision traces and
interaction records that enable an agent to learn from past sessions without re-deriving
the same conclusions.

In the MCG architecture, episodic memory is the **source material** for semantic memory:
raw episodes age and compress into patterns; patterns with sufficient reuse become
tribal knowledge; tribal knowledge is compiled into skills (procedural memory).

```
Episode (raw)  →[decay/compress]→  Pattern (semantic)  →[tenure]→  TribalKnowledge  →[compile]→  Skill
```

### Episode Schema

```python
class Episode(BaseModel):
    episode_id: str             # ULID
    session_id: str
    task_id: str | None
    timestamp: datetime
    event_type: str             # "decision", "tool_call", "correction", "reflection"
    summary: str                # ≤ 3 sentences: what happened and why
    outcome: Literal["success", "failure", "partial", "unknown"]
    entities_involved: list[str]   # canonical entity names (via kg_ontology)
    tags: list[str]
    raw_ref: str | None         # pointer to full turn transcript (cold storage)
```

### Storage and Retrieval

Episodes are stored in the `agentic_kg_memory` sqlite backend under the `episodes`
namespace. Retrieval uses BM25 + time-decay weighting:

```python
def retrieve_episodes(
    query: str,
    entity_filter: list[str] = None,
    since: datetime = None,
    top_k: int = 10,
) -> list[Episode]:
    """
    Retrieves episodes matching the query.
    Time-decay weight: w = score * exp(-lambda * days_since_episode)
    Default lambda = 0.05 (half-life ~14 days for raw episodes).
    """
```

The `since` filter enables session-scoped recall (e.g., "what did we try in this session
on this task?") while the full index enables cross-session learning.

### Episode → Pattern Compression

A pattern is a compressed generalisation extracted from multiple episodes with the same
outcome. The compression trigger is the Pattern Store vetting pipeline (see `skill-wiki`):

1. An episode with `outcome=failure` is tagged as a `tk_candidate`
2. After 3 similar episodes share the same entity set and failure mode, they are
   compressed into a `Pattern` node in the CG
3. The pattern's `bm25_text` includes the entity names, tags, and a compressed summary

### Relationship to continuity-log

`continuity-log` is a **session-scoped** distillation (the compact-safe packet for a
single turn sequence). Episodic memory is **cross-session** and time-indexed. They feed
the same downstream pipeline:

```
continuity-log (session distillation)
    │
    └──► episodes table (cross-session index)
              │
              └──► pattern compression → tk_candidates → tribal_knowledge → skills
```

### Evidence

- CoALA arXiv:2309.02427: episodic memory as the dedicated store for past experiences;
  distinct from semantic (generalised facts) and procedural (how-to)
- MemGPT arXiv:2310.08560: paging semantics — episodes in slow storage, retrieved on demand
- ExpeL (2024): cross-task experience extraction from episode logs → generalised skills

### Entity Identity Sub-Layer (kg_ontology)

The DKG requires entity resolution: `"SOW"`, `"Statement of Work"`, and `"sow"` must
collapse to a single canonical node. `kg_ontology` handles this via:

- **Synset expansion**: `"provider"` → WordNet synset → canonical form
- **Hypernym injection**: inject `provider → organization → legal_entity` chain into `bm25_text`
- **Cross-entity BM25**: entity alignment occurs via BM25 at query time — no graph traversal

This approach scales to millions of nodes at sub-100ms query latency. Without it, the
DKG accumulates duplicate nodes and resolution errors that compound across every document.

`agentic_kg_memory` (this skill) handles CG retrieval and semantic memory policy.
`kg_ontology` handles DKG entity identity. They are complementary layers, not alternatives.

### Academic Foundation

| Source | Key contribution |
|---|---|
| Tekiner (2025), "Meta Knowledge Graphs (Context Graphs)" | Dual-graph architecture; 4-layer hierarchy; kitchen brigade; tribal knowledge lifecycle |
| Hu et al. (2025), arXiv:2512.13564 | Forms (token-level / parametric / latent), functions (factual / experiential / working), dynamics taxonomy |
| Shinn et al. (2023), Reflexion | Episodic memory via verbal self-reflection; short-term trajectory vs long-term feedback memory |
| Packer et al. (2023), MemGPT arXiv:2310.08560 | Hierarchical memory management; L4→L1 paging metaphor |
| Zhao et al. (2024), ExpeL | Cross-task experiential learning from past episode pools |
| Yao et al. (2023), CoALA arXiv:2309.02427 | Cognitive architecture: modular working/episodic/semantic/procedural memory |
| Zhang et al. (2026), ACE arXiv:2510.04618 | Evolving playbooks: generation→reflection→curation; +10.6% agents, +8.6% finance |


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

## KG Ontology (Sub-skill)

`kg_ontology` owns entity/predicate canonicalization, synset/hypernym candidate narrowing,
BM25 hypernym injection, layer separation, and ontology anti-patterns.
`agentic_kg_memory` consumes those ontology winners for triplet storage, retrieval,
pages, and throughlines.

Do not let pages, objectives, or throughlines invent their own node identities.
See [[kg_ontology]] for the full connection map, canonicalization contract,
visibility rules, and fallback policy.

---

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
<!-- consolidation:see-also:start -->
## See Also
[[kg_ontology]]  [[gist-retriever]]  [[agentic-harness]]
<!-- consolidation:see-also:end -->
