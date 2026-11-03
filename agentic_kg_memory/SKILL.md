---
name: agentic_kg_memory
description: >
  Graph-backed semantic memory and reasoning protocol. Use when extracting
  premises into a knowledge graph, retrieving evidence with BM25/NLI, updating
  memory entries from new evidence, or maintaining wiki-like throughlines that
  evolve as the graph learns.
metadata:
  status: active
  tier: L1
  last_validated: '2026-11-02'
---

# Agentic KG Memory

## Retrieval Tier: L1 (Structured memory; dense retrieval optional)

This skill is **L1** in the three-tier knowledge retrieval cascade:

| Tier | Skill | Role |
|---|---|---|
| L2 | `memory-bank` / skills markdown | Compiled durable knowledge — try first |
| **L1** | **`agentic_kg_memory`** | **Atomic triplets and semantic pages; lexical baseline, dense/graph optional** |
| L0 | `deep-research` | Live web evidence — last resort |

**Admission and durability.** Retrieval and citation counts are diagnostic only: they record
what was searched or referenced, not whether it helped. Recall MUST NOT change admission
counters, promote, or retire a memory. Admission to shared or durable scope follows
`agent-long-term-memory` R14: recurrence on at least three independent tasks or a
control-versus-treatment pass, with source evidence retained. This skill describes graph
extraction and evidence use; it does not authorize automatic promotion.

## Memory Scope: Global vs Repo

Wiki-page scope labels map to the active `memory-index` scope contract:

| Wiki label | `memory-index` scope | Required context |
|---|---|---|
| `global` | `shared` | Explicitly reusable across projects; no project URI. |
| `repo` | `project` | Exact normalized workspace URI. |
| session-only candidate | `session` | Exact workspace URI and session ID. |

A page has one scope. These wiki labels are not persisted as a parallel scope enum: graph edges copy the canonical `project_uri`, `scope`, and `session_id` snapshot from their source memory record, and `memory-index` remains the authorization authority.

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
- outcome-based utility semantics for conclusions, with score updates gated on a verified memory-index binding
- source-backed conclusion synthesis for final answers

## Setup Boundary

This skill is design guidance; no graph writer, graph-table migration, or graph traversal runtime is wired into the active `memory-index` MCP. Its scoped SQLite store and `search_memory` / `open_memory` / `memory_feedback` tools remain the incumbent storage and authorization path. Do not create a second `wiki_memory.sqlite3` database or a new Chroma collection for graph memory.

The legacy `memory-index/mem.py` Chroma CLI is a separate tool whose log can promote after repeated searches. That recall-count behavior is not the admission contract for graph memories and MUST NOT be used for graph admission. Use the `memory-index` MCP scope/open/feedback contract and `agent-long-term-memory` R14 instead.

If setup is requested, first produce a code-level spec and migration plan to extend the incumbent store. Preserve lexical retrieval as the baseline; dense retrieval and graph traversal stay optional and off unless separately enabled and validated. The earlier standalone-store recipe is preserved in [the dated archive](history/2026-11-02-superseded-graph-setup.md).

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

Information may be represented at progressively more structured tiers as evidence accumulates.
These transformations do not themselves admit an item into shared or durable scope; admission
follows `agent-long-term-memory` R14. Recall or citation counts do not satisfy that gate.

| Tier | Label | What lives here | Lifetime |
|---|---|---|---|
| 0 | **Working memory** | Raw observations from the current session: unprocessed spans, scratch notes, transient context | Ephemeral; compressed at session end |
| 1 | **Episodic memory** | Session summaries compressed from working memory; what happened in a bounded interaction | Medium; decays if not reinforced |
| 2 | **Semantic memory** | Cross-session facts consolidated from episodes; stable claims about the domain | Long; updated but not easily erased |
| 3 | **Procedural memory** | Workflows, patterns, and decision rules extracted from repeated semantics | Longest; changes only when patterns break |

Each tier is more compressed, more confident, and longer-lived than the one below it.

### Promotion rules

Derive a candidate representation one tier when:
- **Working → Episodic**: the session ends and the observation survived compression
- **Episodic → Semantic**: the same claim appears across multiple episodes with consistent support
- **Semantic → Procedural**: a cluster of semantic facts resolves to a reusable workflow or decision rule

Before a candidate enters shared or durable scope, apply R14 independently of these
representational steps. Retrieval frequency, citations, or model confidence alone are not
admission evidence.

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

### Wired implementation (Claude Code, 2026-07-29)

The abstract events below are now backed by real harness hooks, registered in
`~/.claude/settings.json`:

| Claude Code hook | Script | Role |
|---|---|---|
| SessionStart | `~/.claude/hooks/membank.py` | injects the six-file bank, then the most recent approved **user**-scope memories (recency-ordered — there is no prompt to rank against) |
| SessionStart, UserPromptSubmit, PreToolUse, PostToolUse, Stop, SessionEnd | `~/.claude/hooks/log_event.py` | appends every event to `~/memory-bank/events.sqlite3` |
| UserPromptSubmit | `~/.claude/hooks/membank.py` | prompt-ranked recall of reviewed memories, deduped per session |

Capture store (`memory-index/events_store.py`) — MKG's `[:NEXT]` graph chain
becomes `prev_event_id` + `seq`:

```
sessions(session_id PK, project_slug, cwd, started_at, ended_at, last_dreamed_at)
events(event_id PK, session_id, prev_event_id, seq, event_name, timestamp,
       project_slug, tool_name, tool_use_id, subagent_type, tool_input, tool_response,
       tool_error, prompt, last_assistant_message, model, source, git_branch,
       is_sidechain, origin)
injections(session_id, memory_name, injected_at)
```

`tool_use_id` is load-bearing, not decoration: a tool *result* carries no tool name,
only the id of the call it answers, so without it nothing can pair a `PostToolUse` with
its `PreToolUse`. Schema changes go through `_migrate()` (additive `ALTER TABLE` only) —
`CREATE TABLE IF NOT EXISTS` silently does nothing to an existing table.

**The store is a cache, not primary data.** `mem backfill`
(`memory-index/backfill.py`) reconstructs events from Claude Code's own transcripts at
`~/.claude/projects/*/*.jsonl`, keyed on each record's `uuid` so re-running is a no-op.
This is what makes the tier disposable in the annealing sense: Chroma rebuilds from
markdown, events rebuild from transcripts, and only markdown is authored. An empty store
is a cache miss.

Reconstruction is richer than live capture — a transcript covers the session's whole
history, including before the hooks existed (measured: 12,802 events rebuilt for a
session where the hook had 126). It cannot recover `SessionStart`/`SessionEnd` `source`
or `stop_hook_active`, which distillation does not read.

Distillation is `mem dream` (`memory-index/dream.py`), exposed to agents as the
`distil_sessions` tool on the `memory-bank` FastMCP server (`~/.copilot/memory_mcp.py`,
registered in the skills repo's `.mcp.json` alongside `memory_status`,
`rebuild_event_cache`, and `recall`). **No scheduler:** the agent calls it when work
finishes. Mechanics include a per-session watermark, extraction behind a recursion guard,
and contradiction checks against indexed evidence. A distillation result remains a candidate;
it does not enter shared or durable scope without R14 admission. `mem dream` automatic
approval remains off unless explicitly enabled, and that flag does not replace admission
evidence. Raw-event retention follows the current memory-index contract.

Retrieval frequency does not determine survival or admission. Durable/shared admission follows
R14 and retains source evidence; raw-event retention follows the memory-index contract.

Provenance and what was deliberately not ported:
`.reference/meta-knowledge-graph/NOTES.md`.

Three things capture does NOT do, on purpose: it stores no transcripts (prompts
and assistant messages already carry the dialog, once each); it never blocks a
session (every failure path returns quietly); and it makes no judgment about
value, which is exactly what lets it be lossless.

**Silent-failure sweep.** Because capture never blocks, it can die completely while
every session still looks normal — the failure mode where silence and health are
indistinguishable. `events_store.capture_health()` is therefore *polled* once per
session by `membank.py` (nothing can fire on a non-event) and prints a loud line when
the store is missing, unwritable, or empty. The same sweep reports distillation staleness and
cache overrun, since an un-run distiller is silent in exactly the same way.

The write probe is `PRAGMA user_version = <its current value>`. Two cheaper probes
were measured against a genuinely read-only file and **both reported false health**:
`connect()` (no write happens once the tables exist) and `BEGIN IMMEDIATE` (SQLite
defers the lock until a statement writes). A probe that cannot fail is worse than no
probe — see memory `write-probe-must-be-able-to-fail`.

**Delegation is first-class, sub-sessions are not.** `subagent_type` is promoted to its
own column and delegations render as `DELEGATED to <type>, returned/FAILED: ...` in the
distillation corpus, so task patterns about which subagent suits which job are learnable.
A subagent *sub-session* is deliberately absent because the data does not exist: measured
across 973 transcripts / 204,732 records, `isSidechain` is `False` everywhere while 1,196
`Agent` invocations are present — the transcript holds the invocation and its report,
never the internal steps. MKG's `HAS_SUBAGENT` lane depends on seeing those steps.

Still open: the dream pass does not extract triplets into `kg_nodes`/`kg_edges`.
Any future `q_score` or `stability` updates require explicit outcome receipts; recall alone
cannot update them. Decay remains `mem anneal`'s TTL behavior; no Ebbinghaus schedule is live.

Recommended event hooks:

| Event | Action |
|---|---|
| **on_new_source** | auto-ingest, extract triplets, update graph, update index.md |
| **on_session_start** | load relevant context pages based on recent activity and current task — **wired**: `membank.py` |
| **on_session_end** | compress session observations into episodic entries, file insights back to pages — **wired**: `log_event.py` captures, `mem dream` compresses |
| **on_query** | retain a source-linked candidate if the answer may be worth filing; do not admit it based on query confidence or retrieval |
| **on_memory_write** | check for contradictions with existing knowledge, trigger supersession if warranted; also run write-time Jaccard dedup against `isLatest=true` entries — if `sim > τ_merge` (default 0.7), supersede the old entry rather than creating a standalone duplicate: bump `version`, set `parentId`, mark old `isLatest=false` |
| **on_schedule** | periodic lint, consolidation pass, temporal retention decay |

### Overnight Synthesis Recipe

**Partially implemented** as `mem dream` (2026-07-29). Steps 1 and 2 are live:
sessions are batched off `events.sqlite3` by watermark, and `lessons-learned` rows
are folded in as corrections — once per run under a reserved `__lessons__`
watermark, not once per session, since the corrections are not evidence about any
one session. Steps 3–5 (source diff, in-place wiki reinforce/refine, `q_score` and
`stability` persistence) are still unimplemented; `mem dream` writes new memory
files with a `supersedes:` pointer rather than editing pages in place.

The `on_schedule` hook should run a nightly synthesis pass in this order:

1. **Session batch** — collect all episodic entries from sessions since the last synthesis run
2. **Correction integration** — pull all `event_type: "correction"` episodes (and `lessons-learned` rows updated since last run) from the interval; these are the primary self-improvement signal
3. **Source diff** — check each connector/source document for changes; re-ingest changed pages against the relevant wiki pages
4. **Wiki update** — for each affected page, run the ingest→reinforce/refine loop in place; record supersession events for any claim that changes; do not append blindly
5. **Persist** — retain source-backed candidate revisions; update utility scores or stability clocks only from explicit outcome receipts

This converts raw session history into a progressively better starting context. Each nightly pass makes the wiki a stronger signal for the next day's tasks. Token cost of prior sessions is the investment; the wiki's improved recall and fewer dead-end turns are the return. Brain (Perplexity, 2026) reports +25% answer correctness on seen tasks and −13% cost on history-dependent tasks from this loop.

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

NLI or a judge may classify whether source evidence entails, is neutral to, or
contradicts a candidate conclusion. Those labels update the conclusion's evidence
state only through an explicit, reversible evidence revision; they are not task-utility
rewards and MUST NOT change `q_score`. A downstream task outcome may update utility
only through the separate, measured feedback contract below.

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

### Pass 0 — Entity candidate discovery (zero LLM calls)

Before relation extraction, a fast matcher or NER pass may identify candidate entity spans.
Pass 0 may resolve known aliases to existing canonical entities, but it MUST NOT create
relationship edges from mention co-occurrence. Entity mentions are evidence of presence in a
source, not evidence that the entities relate to one another.

#### GLiNER2 entity extraction

Run GLiNER2 for entity extraction in every memory-graph ingestion. Install local
inference with `pip install "gliner2[local]"` and load checkpoints through
`AutoExtractor`. Use `fastino/gliner2.5-base-v1` for English by default; use
`fastino/gliner2.5-small-v1` on CPU-constrained systems and `fastino/gliner2.5-multi-v1`
for multilingual text. The small checkpoint remains the required extractor when it
is selected; it is not a reason to skip entity extraction. Resolve installation or
checkpoint-loading failures before ingestion; do not silently bypass this stage.

Define a domain-specific entity schema with descriptions that separate adjacent types.
Request spans and confidence scores. Tune thresholds against labeled examples, and
retain the model/checkpoint, schema, source reference, span, and score with each result.

Treat every output as a **candidate surface span**:

- Verify each returned offset against the exact input text.
- Send source-grounded candidates through `kg_ontology` for canonical identity; write
  graph nodes only after canonicalization. Never use raw extractor strings as node IDs
  or write candidate mentions directly as graph edges.
- Relation extraction is also candidate generation. Preserve head/tail spans and
  relation type, then validate the relation against its source before producing an
  affirmed or negated triplet. GLiNER2 relation output does not replace the Pass 1
  triplet contract or its polarity and inference labels.
- Continue running entity extraction while refining the schema and thresholds; only
  source-grounded spans proceed to ontology resolution, and only canonicalized entities
  proceed to graph writes.
- Co-occurrence may propose candidate pairs for later review, but it MUST NOT be stored as an
  asserted relation. Every asserted edge must be supported by a validated relation in its
  source and retain that source span, canonical endpoint IDs, polarity, and inference type.

**Current disposition (2026-11-01):** GLiNER2 is the required entity-extraction
stage. On three skill excerpts, `fastino/gliner2.5-base-v1` found the skill names,
`kg_ontology`, SQLite, BM25, and Chroma with source spans. The same trial exposed
type errors (`raw traces` labeled as a data store and `repository graph` labeled as
a data store), so entity types and thresholds still need corpus-specific validation.
The small checkpoint missed SQLite and Chroma in the same sample. Relation extraction
also returned broad or missing links; it remains candidate-only and does not replace
the Pass 1 triplet contract. See the [official GLiNER2 model and API guide](https://github.com/fastino-ai/GLiNER2/blob/main/README.md).

**When graph traversal may help:**

BM25 remains the default retrieval baseline for source passages and single-hop queries. A graph
is a candidate route when a question requires joining multiple source-backed relations, such
as finding funders of companies that a named person advises. That capability depends on the
correctness and provenance of every edge in the path; graph traversal is not presumed to beat
BM25, diversified BM25, or full context.

Keep graph-assisted retrieval and graph-assisted reading separate:

- **Retrieval** uses a query to follow validated graph relations and propose relevant source
  passages. It changes which passages enter the candidate set.
- **Reading** starts from passages already retrieved and opened, then organizes their claims,
  support, contradictions, and unresolved links. It does not make an unsupported relation
  true merely because a path can be drawn.
- In either route, return source references for every traversed relation, open those source
  spans, and base answer claims on the opened evidence. If a path is incomplete or sources
  conflict, report the gap or conflict instead of silently filling it.

Graph retrieval is optional and stays off by default until it beats the relevant lexical
control at the same reader, judge, and context budget on held-out cases.

**StructMem (2604.21748) middle path**: if full graph construction is too costly, use
*dual-perspective extraction* + *periodic consolidation* as a lightweight alternative:
extract both a **factual entry** (what happened) and a **relational entry** (how it
binds to participants / prior events) from each event, then periodically consolidate
semantically related events within temporal windows. This achieves structured reasoning
without explicit entity resolution or graph traversal overhead (see `cognitive-taxonomy`
§7 for the full flat–structured–graph spectrum).

Your triplets already ARE edges: subject → predicate → object maps 1:1 to a typed
directed edge. The graph is a natural structural consequence of triplet extraction, not
an additional abstraction.

**Graph schema (SQLite):**

```sql
CREATE TABLE IF NOT EXISTS kg_nodes (
    slug      TEXT PRIMARY KEY,           -- canonical entity ID from kg_ontology
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
    inference_type TEXT NOT NULL,        -- observed|inferred
    source_ref TEXT NOT NULL,            -- stable original document/source identifier
    memory_id TEXT NOT NULL,              -- memory-index source record ID
    project_uri TEXT NOT NULL DEFAULT '', -- authorization snapshot; empty for shared scope
    scope TEXT NOT NULL,                  -- project|session|shared; unknown is audit-only
    session_id TEXT NOT NULL DEFAULT '',  -- set for session-scoped sources
    source_version TEXT NOT NULL,         -- immutable memory-index raw_id for this record
    source_sha256 TEXT NOT NULL,          -- hash of exact UTF-8 text returned by open_memory
    source_char_count INTEGER NOT NULL,    -- complete opened text length after redaction
    span_start INTEGER NOT NULL,          -- zero-based Unicode code-point offset
    span_end   INTEGER NOT NULL,          -- exclusive end offset
    created_at  TEXT DEFAULT (datetime('now')),
    PRIMARY KEY (
        src_slug, dst_slug, edge_type, source_ref, memory_id, source_version,
        source_sha256, span_start, span_end, polarity, inference_type
    ),
    CHECK (scope IN ('project', 'session', 'shared')),
    CHECK ((scope = 'session' AND session_id <> '') OR (scope <> 'session' AND session_id = '')),
    CHECK (source_char_count BETWEEN 1 AND 6000),
    CHECK (span_start >= 0 AND span_end > span_start AND span_end <= source_char_count),
    CHECK (polarity IN ('affirmed', 'negated')),
    CHECK (inference_type IN ('observed', 'inferred'))
);

CREATE INDEX IF NOT EXISTS idx_kg_edges_dst ON kg_edges(dst_slug, edge_type);
CREATE INDEX IF NOT EXISTS idx_kg_edges_type ON kg_edges(edge_type);
```

**Source, scope, and schema compatibility contract:** This is a proposed schema revision,
not a claim about a deployed table. `source_ref` identifies the original document;
`memory_id` binds the edge to its scope-authorized record in `memory-index`; `source_version`
is that record's immutable raw ID. `source_sha256` hashes the exact UTF-8 bytes returned by
`open_memory` after its built-in redaction, and `source_char_count` records that complete
returned text length. Graph source records MUST fit the 6000-character open limit; larger
sources must be split into deterministic chunks before graph admission. Record the complete
source character count at ingestion, before opening. Reject a body whose length differs from
that count; a body at the limit is admissible only when the ingestion receipt proves the
complete source chunk is exactly that length.
Hash exact returned bytes before decoding. Offsets are zero-based Unicode code-point positions
into that same returned text with an exclusive end; do not normalize line endings or Unicode
before slicing. A consumer MUST verify raw ID, hash, count, bounds, and extracted span before
using the edge.

`project_uri`, `scope`, and `session_id` are authorization-filter snapshots copied from
`memory-index`; they are not the authorization authority. Exclude `unknown` and stale-scope
rows. Before ranking or traversing a candidate edge, apply the caller's workspace/session
scope using the `memory-index` R5/R7 contract, then call `open_memory` with the same context.
Only successfully opened sources whose raw ID, hash, and character count still match may enter
an authorized source-ID set for graph ranking/traversal. If a source is inaccessible, changed, or outside
scope, exclude it and any path that depends on it. Scope-specific records have distinct
`memory_id` values, so out-of-scope evidence cannot overwrite an authorized row.

The expanded primary key allows the same source span to retain distinct polarity and
inference classifications, and lets changed source versions coexist. Before any runtime
migration, define and version the migration in the owning implementation spec. Migration may
backfill a memory ID/version/hash only when the exact source and span are recoverable and
verified; otherwise preserve the old row in an audit-only legacy table and exclude it from
traversal. Use a transaction and backup, verify row counts and identities, and never guess
provenance. No live schema migration is authorized by this skill edit.

The caller creates a request-local `authorized_memory_ids(memory_id PRIMARY KEY)` table
only after each candidate source passes the scope filter, `open_memory`, raw-ID, and hash
checks above. Graph queries join that set before traversal or ranking.

**Single-hop query (SQLite):**
```sql
-- Who works at Acme?
SELECT n.slug, n.label, e.source_ref, e.source_version, e.source_sha256,
       e.span_start, e.span_end, e.polarity, e.inference_type FROM kg_edges e
JOIN kg_nodes n ON e.src_slug = n.slug
WHERE e.dst_slug = 'acme' AND e.edge_type = 'works_at' AND e.polarity = 'affirmed'
  AND e.memory_id IN (SELECT memory_id FROM authorized_memory_ids);
```

**Multi-hop query (recursive CTE):**
```sql
-- Who funded companies that Alice advises?
WITH advised AS (
    SELECT src_slug AS advisor, dst_slug AS company, source_ref, source_version,
           source_sha256, span_start, span_end, polarity, inference_type
    FROM kg_edges
    WHERE src_slug = 'alice' AND edge_type = 'advises' AND polarity = 'affirmed'
      AND memory_id IN (SELECT memory_id FROM authorized_memory_ids)
)
SELECT f.src_slug AS funder, a.company,
       a.source_ref AS advises_source, a.source_version AS advises_version,
       a.source_sha256 AS advises_sha256, a.span_start AS advises_start,
       a.span_end AS advises_end, a.polarity AS advises_polarity,
       a.inference_type AS advises_inference, f.source_ref AS funding_source,
       f.source_version AS funding_version, f.source_sha256 AS funding_sha256,
       f.span_start AS funding_start, f.span_end AS funding_end,
       f.polarity AS funding_polarity, f.inference_type AS funding_inference
FROM advised a
JOIN kg_edges f ON f.dst_slug = a.company
WHERE f.edge_type = 'invested_in' AND f.polarity = 'affirmed'
  AND f.memory_id IN (SELECT memory_id FROM authorized_memory_ids);
```

Pass 0 discovers entity spans and candidate canonical IDs only. Pass 1 may produce relation
candidates; only source-validated, canonicalized relations become graph edges. Each edge keeps
its own source span so repeated or conflicting evidence is not collapsed into one row.

### Pass 1 — LLM triplet extraction

After entity candidate discovery, the LLM extraction pass may propose relations. Validated,
canonicalized triplets are indexed for lexical retrieval and may also be written to the graph
as typed edges with source span, polarity, and inference status retained.

**Query routing:**
| Query type | Use |
|---|---|
| Semantic / fuzzy ("what do we know about memory?") | BM25 by default; dense retrieval only when the incumbent memory-index config enables it and its gate passes |
| Relational / structural ("who works at X?", "what does Y imply?") | Optional graph arm after matched-control gate; return and open source spans |
| Hybrid ("what did people who work at X say about memory?") | Optional validated graph candidates → BM25 re-ranks; lexical control stays available |

The high-level chain is:

`source text -> candidate extraction -> source validation -> ontology winner ids -> BM25 index; optional provenance-bearing kg_edges`

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
7. `update_count`
8. `wiki_summary`
9. `throughlines`
10. `bm25_text`
11. `triplet_sequence_text`
12. `embedding_ref`
13. `cluster_id`
14. `history`

Read and retrieval counters are not page state: recall must not change counters or admission.
Use the memory-index `memory_feedback` receipt for explicit helpful/harmful outcomes, with its
outcome ID and evidence reference.

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
q_score          REAL   # score derived only from explicit outcome-feedback receipts
outcome_count    INT    # evaluated, deduplicated outcome receipts; never retrieval count
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
    |    retain candidate evidence; q_score changes only from outcome feedback
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
retain source refs and candidate evidence; q_score unchanged
    |
    v
LLM critic pass (see below)
    |
    +- no deficiency found:   claim_text unchanged (accept as-is)
    +- gap identified:        claim_text refined to shore up the deficiency
    +- contradiction:         retain the contradicting source; q_score unchanged until outcome feedback
```

**The old score is always the prior.** Only explicit, deduplicated outcome receipts may update
it; retrieved premise matches and LLM critique alone do not change the score.

The roles are separate:
- **Q-score** updates only from explicit outcome-feedback receipts with evidence references
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

**If accept:** retain the source-supported conclusion candidate. Do not update `q_score` from
retrieval or model acceptance; a score update requires an explicit outcome-feedback receipt.

**If revise:** the LLM may propose revised wording with its evidence and rationale. Model
confidence alone does not update `q_score` or admit the revised conclusion.

The revision confidence is an ephemeral review aid. It does not update `q_score`,
which measures task utility only, and it does not establish truth or admission.

### Minimal score update

```text
q_new <- q_old + α(r - q_old)
```

`q_score` is downstream task utility, not epistemic confidence or entailment. A feedback
receipt is `helpful` or `harmful` only when an observed task outcome and its evidence reference
support that judgment. The current `memory_feedback` contract accepts those two outcomes and
requires a stable outcome ID and evidence reference; it does not accept neutral/mixed and does
not directly identify a throughline. Therefore, unless a durable throughline-to-`memory_id`
binding is defined and verified, no `memory_feedback` receipt may update a throughline
`q_score`.

Entailment, neutrality, and contradiction describe a source's relation to a candidate claim.
They MUST be stored as evidence classification and MUST NOT be mapped to helpful/harmful
rewards. Search, retrieval, source opening, entailment labels, or citation alone MUST NOT
update `q_score` or an outcome counter. Feedback IDs remain idempotent.

If a verified throughline-to-memory binding is later implemented, define `q_score` on
[0, 1], map `helpful` to `r = 1` and `harmful` to `r = 0`, and use a running mean:

```text
outcome_count += 1
α = 1 / outcome_count
q_new <- q_old + α(r - q_old)
```

A neutral/mixed outcome is not accepted by the current memory feedback API and must not
be fabricated as either class. Until the binding and update path are implemented and
validated, leave `q_score` and `outcome_count` unchanged. Afterward, `q_score` reflects the
mean of accepted, deduplicated helpful/harmful task outcomes, never retrieval frequency.

Do not use retrieval frequency as a utility signal.

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
6. preserve the survivor's prior `q_score`; a score update requires an explicit outcome receipt

Do **not** merge contradictory claims just because they touch the same entities.

### Competing Throughlines

Do not force one conclusion too early.

Multiple throughlines may coexist over the same evidence cluster. Do not rank
truth or explanatory support by `q_score`: it measures downstream task utility only.
Compare competing claims using their source evidence, entailment, contradiction,
source independence, and version freshness. Keep task utility as a separate signal;
without an explicit throughline-to-memory binding and a valid feedback receipt, leave
`q_score` unchanged.

This is the escape hatch that keeps the living graph from becoming a headache:

- equivalent claims -> merge
- genuinely different claims -> keep as competing
- disproven claims -> deprecate, do not erase history

## Three-Tier Confidence Stack

```text
triplet      extraction prior      -> observed/inferred + explicit confidence
page         retrieval fitness     -> objective/throughline/entity fit
throughline  outcome-feedback score -> MemRL-style Q-score
```

Each tier answers a different question:

- **Triplet**: was this locally well-grounded?
- **Page**: is this memory entry a good semantic match for the current task?
- **Throughline**: has this conclusion received helpful or harmful outcome feedback?

## Forgetting and Temporal Decay

Evidence-based scoring (reinforce/weaken) handles contradictions. Time-based
decay handles **stale-but-uncontradicted** claims — the slow rot that makes wikis
become noise over time.

Apply an Ebbinghaus-style retention model:

```text
retention(t) = e^(−t / stability)
```

Where:
- `t` is time since last explicit outcome feedback, not retrieval
- `stability` may change only from explicit outcome feedback; a read does not reset it

Practical implementation over the Q-score:

```text
effective_q = q_score * retention(time_since_last_feedback)
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

Retrieval alone does not reinforce a memory, change its counters, or reset its decay clock.
Where a lifecycle uses feedback, only an explicit outcome receipt can supply that signal.

```text
stability_new = stability_old * growth_factor  # only from explicit outcome feedback
last_feedback_at = now()
```

Repeated explicit helpful outcomes may affect a lifecycle score when that lifecycle defines
and validates the scoring rule. Search or citation frequency alone never does.

### Forgetting vs. deletion

Do not delete decayed memories. Instead:

- drop `effective_q` below the retrieval threshold
- mark as `status = dormant` when effective_q drops below a floor
- propose reactivation when new source evidence supports the claim; apply it as an append-only revision

This is the semantic equivalent of moving something to a bottom drawer: deprioritized
but recoverable.

### Coding Session Decay Schedule (SimpleMem Concrete Parameters)

Operationalizes the Ebbinghaus model above for coding session observations. Units are **sessions**, not wall time.

| Memory granularity | Half-life (sessions) | Prune trigger |
|---|---|---|
| File-level action (`modified X`, `added Y`) | 3 | Explicit review after 6 sessions without useful outcome feedback |
| Function / class decision | 7 | Explicit review after 14 sessions without useful outcome feedback |
| Bug / error pattern | 5 | Explicit review after 10 sessions without useful outcome feedback (bugs recur; keep longer than file actions) |
| Architectural decision | ∞ (no decay) | Manual prune only — never auto-expire |
| Procedural workflow | ∞ (no decay) | Manual prune only |

**Prune execution timing:** A lifecycle may mark a record for explicit review after its stated interval. It MUST NOT retire or delete the record solely because it was not retrieved; retirement follows the append-only memory-index contract. This schedule is a review heuristic, not an implemented prune procedure.

Architectural and workflow entries are assigned `half_life = float('inf')` — they never age into the prune window.

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

If the query produces a potentially durable synthesis rather than a transient answer, retain it
as a source-linked candidate for a new or revised page / throughline. Admit it to shared or
durable scope only after it meets R14; querying alone does not promote memory.

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
4. Rank candidate pages by traversal depth and edge weight; any task-utility score may
   affect retrieval priority only when its meaning and binding are verified
5. Return a ranked evidence bundle with source provenance; ranking is not evidence support
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

Use graph traversal as a separate, optional retrieval arm only after its matched-control gate
passes. During evaluation, include it only for cases where the graph is expected to matter:
- the query asks about impact, dependencies, or downstream effects
- the query asks about the history of a specific entity or decision
- the corpus has validated typed-relationship coverage

Use standard hybrid retrieval when:
- the query is open-ended semantic exploration
- graph retrieval has not passed its matched-control gate
- the corpus does not have validated typed edges for the query

### HyDE query translation

The dense query should not always be the raw user string.

Prefer a translated query that states the target memory in the form the store is
meant to retrieve:

- intended objective
- likely entities
- likely predicates
- likely throughline shape

This HyDE-style text is what you embed for cluster routing and dense retrieval.

### Structured Query Expansion

Before embedding the translated query, run structured expansion to maximize recall across phrasings:

```xml
<expansion>
  <reformulations>
    <query>semantically diverse rephrasing 1</query>
    <query>semantically diverse rephrasing 2</query>
    <query>semantically diverse rephrasing 3</query>
  </reformulations>
  <temporal>
    <query>time-concretized version if applicable</query>
  </temporal>
  <entities>
    <entity>extracted entity name 1</entity>
    <entity>extracted entity name 2</entity>
  </entities>
</expansion>
```

Schema: `{original, reformulations[], temporalConcretizations[], entityExtractions[]}`

- Generate 3–5 reformulations capturing different facets: paraphrase, domain-specific restatement, abstract/concrete variants
- Temporal concretization: if the query mentions time ("recently", "last week"), generate a date-anchored form
- Entity extraction: capitalized non-stopword tokens + quoted phrases are zero-cost entity hints for the graph traversal leg

Execution: run only the retrieval channels enabled by their acceptance gates. BM25 remains
the mandatory lexical channel; dense retrieval and graph traversal remain separate optional
arms. During a graph evaluation, return passage references, open the source spans, and compare
against the same lexical control, reader, judge, and context budget.

### Two-Phase Compact→Expand Retrieval

When context budget is constrained, split retrieval into two phases:

**Phase 1 — compact search**: return `{id, title, type, score, timestamp}` per result — no content, minimal context cost.

**Phase 2 — expand on demand**: fetch full content only for the IDs the downstream reasoning step actually selects.

This prevents the retrieval layer from saturating the context window before the reasoning step decides which results matter. Apply when the retrieval result set could exceed ~20 full records.

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

## Crystallization Handoff

`crystallization` now owns the **distillation protocol** for completed work chains.
`agentic_kg_memory` owns what happens after that distillation is handed off into the
semantic memory surface.

This remains distinct from the query write-back pattern. Write-back files a single
answer. Crystallization hands this skill an **entire work-chain digest** plus any
standalone facts or lessons extracted from it.

### Expected digest shape

When ingesting a crystallized work chain, expect:

1. **Question** — the original intent or driving question
2. **Findings** — normalized triplets or semantic memory entries
3. **Entities involved** — files, concepts, people, systems, or tools
4. **Lessons** — reusable decision rules or patterns
5. **Open questions** — what remains unresolved

### Ingested artifact types

The `crystallization` handoff may produce:

- **Digest page** — a first-class wiki page with intent, objective, and structured findings; ingest and index it like any other page
- **Standalone facts** — individual lessons and patterns extracted from the digest, filed directly as triplets or semantic memory entries that reinforce or update existing knowledge

Explorations are a source, just like an article or a paper. The wiki should treat
them that way: ingest the results, update the graph, strengthen or challenge existing claims.

### Crystallization vs. session compression

- **Session compression** (episodic tier) — compress raw observations from the current session into episodic entries; runs at session end automatically
- **Crystallization** — distill a purposeful work chain into a structured, high-quality digest via `crystallization`; ingest the resulting artifact here

Use `crystallization` for work chains that have a clear question and answer.
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

**Work memory vs. user memory.** The CG is *work memory* in Brain's sense (Perplexity,
2026): its object is the agent's work (what it did, what failed, what corrections were
made), and its purpose is performance — helping the agent get better at the job. This
is the axis that separates it from user-profile memory (preferences, tastes, working
style). Every entry in the CG should trace back to a session, file, or correction
source — not to a user attribute.

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

### Corrections as the Primary Self-Improvement Signal

The `event_type: "correction"` episode is the highest-value entry in the episodic store.
A correction records what the agent produced that was wrong or insufficient, what the
user or validator changed it to, and the source (session id + file or connector reference).

Every correction must be logged with a `source_ref` linking to the session and artifact
so the overnight synthesis pass can route it to the relevant wiki pages. This closes the
loop: corrections are not just logged — they feed the next synthesis cycle and
progressively eliminate dead ends. An agent that cannot log its corrections cannot
improve across sessions.

Practical convention: log the failed attempt as `outcome = "failure"` and create a
second episode with `event_type = "correction"` and `outcome = "success"` for the fix.
The Pattern Store vetting pipeline then has both halves of the learning signal. High
recurrence of the same `(symptom, root_cause)` pair means the wiki has not yet absorbed
the lesson — the overnight pass should force a page update on the next run.

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

The active `memory-index` MCP currently serves scoped SQLite lexical retrieval; its dense
flag is optional and was observed off on 2026-11-02. Do not assume a derived Chroma triplet
collection exists. `gist-retriever` may supply an optional dense lane only when its own
incumbent implementation and matched-control gate support it; graph traversal stays off by
default under this skill's graph-admission rule.

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

A future storage split may keep page rows and `bm25_text` in the incumbent SQLite store,
with an optional dense index linked by stable IDs. This is a design proposal, not a deployed
backend or permission to create a second store. If approved later, extend `memory-index`
under a versioned implementation spec and keep dense indexing disabled until its gate passes.
Do not duplicate the source-of-truth pages in a new database.

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

## Three-View Indexing and Intent-Aware Retrieval (SimpleMem Pattern)

Proposed design only: a future atomic memory unit could use three representations. The active
`memory-index` contract remains lexical by default, and this section does not enable dense
retrieval or graph traversal.

| View | Backend | Purpose |
|---|---|---|
| Dense | 1024-d vector (LanceDB or Chroma) | Semantic similarity |
| Sparse | BM25 inverted index | Lexical and keyword match |
| Symbolic | Metadata tags (entity type, timestamp, provenance) | Structured filter |

If all three views are implemented and pass their gates, retrieve in parallel and fuse with
RRF. Until then, use the enabled lexical path and do not imply unavailable views are active.

### Write-time synthesis

Consolidate related fragments on write, not in a background job:
1. Resolve coreferences and anchor timestamps to absolute values before storage
2. Run online semantic synthesis: check for related fragments (Jaccard or cosine > τ) and consolidate on-the-fly
3. Memory topology stays compact immediately — no cleanup debt accumulates

**Write-time consolidation is synchronous. Background workers handle decay/prune only.**

### Intent-aware retrieval planning

Rather than fixed-depth search, retrieval scope is LLM-reasoned from query intent:

```
query
    → LLM generates retrieval plan:
        depth (single-hop → minimal; multi-hop temporal → expanded)
        views required (dense only vs. dense + BM25 + symbolic)
        expansion strategy (narrow vs. broad)
    → parallel multi-view retrieval
    → RRF fusion
    → result
```

SimpleMem benchmark: 43.24% F1 with 30× fewer tokens than full-context (LoCoMo-10). Intent-aware depth consistently beats fixed-k across diverse query types.

### Lossless drill-down chain

Every abstraction must trace deterministically to source evidence:

```
Throughline / persona (tier 3 — procedural)
    → Page / scenario (tier 2 — semantic)
        → Triplet / atom (tier 1 — episodic)
            → Source span / raw conversation (tier 0 — working memory)
```

A query at any tier must be able to retrieve the full evidence chain below it. If drill-down is broken at any link, the memory system is opaque. Maps to: `SPO triplet → BIO-tagged span → raw source`.

Reference: SimpleMem (aiming-lab/SimpleMem). Omni-SimpleMem variant adds text/image/audio/video unified memory with KG augmentation (SOTA LoCoMo F1=0.613, +47%).

## Design Rationale — Indexing Decisions

> Consolidated from the retired `semantic-memory` skill. These are the *why* behind the
> triplet index: how S/P/O are normalized, how source text is addressed, and how the
> domain vocabulary is frozen. The mechanics elsewhere in this skill assume these choices.

### Two-Sided Index: Signal Left, Source Right

The index is two-sided. The **left side is derived structured signal**; the **right side is
source text**. S, P, O do not exist as text on the left — only as derived signal (lemma,
synset, hypernym). The actual text lives exclusively on the right, addressed by span offsets.

```
LEFT SIDE (index signal)                       RIGHT SIDE (source)
─────────────────────────────────────────      ───────────────────────
triplet_id    TEXT PK                          doc_id       TEXT PK
subj_lemma    TEXT                             title        TEXT
pred_lemma    TEXT                             abstract     TEXT
obj_lemma     TEXT                             utility      TEXT  <- highest NLI signal
subj_synset   TEXT (1st sense only)            sentence_id  TEXT PK
pred_synset   TEXT (1st sense only)            span_start   INT   (char/token offset)
obj_synset    TEXT (1st sense only)            span_end     INT   (char/token offset)
subj_hypernym TEXT (1st order only)            actual_text  TEXT  <- retrieved on hit
obj_hypernym  TEXT (1st order only)
pos_tags      TEXT (S/P/O roles)
spacy_labels  TEXT (NER on S, O)
epistemics    TEXT ('O' observed | 'I' inferred)
confidence    REAL (default O=1.0, I=0.5)
span_id       TEXT FK -> right-side span
doc_id        TEXT FK -> right-side doc
```

**The triplet is the extraction event, not a stored string.** At retrieval: BM25 hits the
left index → ranked triplet IDs → follow span FKs → pull `actual_text` from the right.
Nothing is reconstructed; the pointer is direct.

### Why the normalization choices

- **Lemma with suffixes retained, not hard lemmatization.** Hard lemmatization loses
  morphological signal BM25 can exploit. "Shooting" and "shoot" stay distinct enough to
  weight, but inflection is normalized.
- **1st synset only, not full expansion.** Full synset expansion at index time causes
  crosstalk — "shoot" pre-expands to "discharge/fire/release," so a query for "discharge"
  hits documents that aren't about it. Index lean; expand at query time. 1st sense =
  dominant sense = enough for precision without noise.
- **1st-order hypernym only.** Full hypernym chains dilute specificity: `shoot → kill →
  act → event` — by the third hop the document is lost.
- **Synsets are index-side; hypernyms are query-side.** Synsets collapse vocabulary at
  ingest ("kill/shoot/assassinate" → one synset edge) — this *is* the normalization step.
  Hypernyms expand taxonomically at query time ("violence" → hits kill/shoot synsets).
- **Stop words are kept.** BM25's IDF discounts them automatically; stripping them manually
  is redundant and removes signal BM25 would have handled.
- **Predicates are head-verb lemma only.** "was shot by" → "shoot"; auxiliaries and
  prepositions are not load-bearing. Synset normalization handles predicate synonym collapse
  — check synset coverage on predicates specifically, or "kill" and "shoot" become different
  edges (predicate crosstalk).

### Prebuilt Domain Vocabulary — freeze before production ingest

Build once from a representative sample, then freeze:

1. Run extraction over ~200–500 documents.
2. Collect all 1st-synset + 1st-hypernym hits.
3. Manually review thin/wrong sense mappings (domain jargon WordNet misses).
4. Patch with domain extensions (e.g. arXiv: "transformer," "attention," "latent space").
5. Freeze — subsequent ingest validates against it; misses/low-confidence senses FLAG for
   an LLM correction pass on flagged terms only, then re-enter lookup.

Why: closes the vocabulary (coverage gaps visible before ingest), makes query expansion
deterministic (same list at ingest and query time — no drift), and bounds index size.

### Field weighting for the right side

`utility > predicate > subject/object > title > abstract`. Utility is author-stated purpose —
highest signal for NLI premise matching. Abstract is noisy and long; title is clean but narrow.
For corpora without an explicit utility field (novels, news), substitute a first-sentence
summary or author-extracted claim — don't leave it null.

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
[[agentic-harness]]  [[skill-wiki]]  [[reasoning]]
<!-- consolidation:see-also:end -->
