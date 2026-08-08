# LLM Wiki Pattern Topology

**Source:** `/root/.copilot/skills/integrate/llm-wiki.txt`  
**Lineage:** Andrej Karpathy's original **LLM Wiki** idea, extended in the source file with production lessons from `agentmemory`  
**Purpose:** A pattern for building a persistent, compounding LLM-maintained knowledge system that sits between raw sources and downstream answers. The wiki is not retrieval-only memory; it is a maintained knowledge artifact with lifecycle rules, structure, automation, and outputs.

---

## Topology Overview

```text
SOURCE LAYER ───────────────────────────────────────────────────────────────────
  raw sources
       │
       ├── articles, papers, transcripts, notes, images, data files
       └── immutable source-of-truth collection

COMPILATION LAYER ──────────────────────────────────────────────────────────────
  ingest ──► wiki pages ──► index.md
                │             │
                │             └── catalog / entry surface for human and agent lookup
                │
                ├── entity pages
                ├── concept pages
                ├── summaries / syntheses
                └── log.md (append-only chronology of ingests, queries, lint)

CONTROL LAYER ──────────────────────────────────────────────────────────────────
  schema document (AGENTS.md / CLAUDE.md)
       │
       ├── page conventions
       ├── ingest / query / lint workflows
       ├── quality standards
       ├── contradiction handling
       └── privacy / sharing rules

MEMORY LIFECYCLE LAYER ─────────────────────────────────────────────────────────
  working memory
       ▼
  episodic memory
       ▼
  semantic memory
       ▼
  procedural memory
       │
       ├── confidence scoring
       ├── supersession
       └── retention / forgetting

STRUCTURE + RETRIEVAL LAYER ───────────────────────────────────────────────────
  entity extraction ──► typed knowledge graph ──► graph traversal
         │                         │
         ├── BM25                  ├── vector search
         └──────────────► hybrid search / RRF fusion ◄──────────────┘

AUTOMATION + QUALITY LAYER ────────────────────────────────────────────────────
  event hooks
       ├── on new source
       ├── on session start / end
       ├── on query worth filing
       ├── on memory write
       └── on schedule
  +
  quality scoring / self-healing / contradiction resolution

COLLABORATION + GOVERNANCE LAYER ──────────────────────────────────────────────
  mesh sync
  shared vs private scopes
  work coordination
  sensitive-data filtering
  audit trail
  reversible bulk operations

OUTPUT LAYER ──────────────────────────────────────────────────────────────────
  markdown pages
  comparison tables
  timelines
  dependency graphs
  slide decks
  structured exports
  briefs
```

---

## Feature Inventory

### FOUNDATIONAL MODEL

**`raw sources`**  
Immutable inputs. Articles, papers, transcripts, notes, images, and data files remain the underlying source of truth. The LLM reads them but does not rewrite them.

**`wiki pages`**  
The maintained artifact layer. The LLM creates and updates summaries, entity pages, concept pages, syntheses, and cross-references so knowledge compounds instead of being re-derived on each query.

**`schema document`**  
The operating contract that turns a generic LLM into a disciplined wiki maintainer. It defines structure, workflows, standards, contradiction handling, and governance rules.

### CORE OPERATIONS

**`ingest`**  
Processes a new source into the wiki. Reads the source, extracts key information, updates affected pages, updates the index, and logs the operation.

**`query`**  
Answers against the maintained wiki rather than against raw sources alone. Valuable answers can themselves be filed back into the wiki as new artifacts.

**`lint`**  
Periodic health-check pass. Finds contradictions, stale claims, orphan pages, missing links, and data gaps; suggests or performs repairs.

### NAVIGATION + LOGGING

**`index.md`**  
Human-readable content catalog. Works as a first-pass directory and lookup surface at small-to-moderate scale.

**`log.md`**  
Append-only chronological record of ingests, queries, and maintenance operations. Useful both for agent continuity and human auditability.

**`optional CLI/search tools`**  
The source mentions local search tooling such as `qmd` once the index becomes too large to be the primary search surface.

### MEMORY LIFECYCLE

**`confidence scoring`**  
Every fact should carry strength-of-belief metadata based on support count, recency, and contradiction state.

**`supersession`**  
Newer or stronger knowledge should explicitly supersede stale claims rather than merely coexisting with them.

**`forgetting / retention decay`**  
Old, weak, or unreinforced knowledge should fade in priority over time so the wiki does not become a junk drawer.

**`consolidation tiers`**  
The source extends the original wiki with four tiers:
- working memory
- episodic memory
- semantic memory
- procedural memory

This turns the wiki from a flat store into a compaction pipeline.

### STRUCTURE + RETRIEVAL

**`entity extraction`**  
Ingest should produce structured entities rather than prose only.

**`typed relationships`**  
Links such as `uses`, `depends on`, `contradicts`, `caused`, `fixed`, and `supersedes` carry more value than undifferentiated wikilinks.

**`knowledge graph`**  
Pages are for reading; the graph is for navigation and discovery. The graph augments the wiki rather than replacing it.

**`hybrid search`**  
The scaled retrieval model in the source combines:
- BM25
- vector similarity
- graph traversal

and fuses them with reciprocal rank fusion.

### AUTOMATION + QUALITY

**`event-driven hooks`**  
The source proposes automatic triggers for ingest, context loading, session compression, contradiction checks, and scheduled maintenance.

**`quality scoring`**  
Generated content should be scored for structure, citation quality, and consistency before it becomes trusted wiki state.

**`self-healing`**  
Lint should do more than report. It should repair broken cross-references, mark stale claims, and move the system back toward health.

**`contradiction resolution`**  
The system should not only flag conflicts but also propose or enact likely resolutions based on recency, authority, and support.

### COLLABORATION + GOVERNANCE

**`mesh sync`**  
Parallel agents or users should be able to merge observations into a shared wiki.

**`shared vs private scopes`**  
Some knowledge remains personal; some promotes into shared team knowledge.

**`work coordination`**  
Minimal coordination prevents duplicate effort when multiple agents touch the same knowledge base.

**`privacy and governance`**  
Sensitive data must be filtered on ingest. All operations should be auditable, and bulk operations should be reversible.

### CRYSTALLIZATION + OUTPUTS

**`crystallization`**  
Completed research, debugging, or analysis threads can be distilled into durable digest pages plus extracted lessons.

**`output formats beyond markdown`**  
The wiki is the store, not the only output format. Tables, timelines, dependency graphs, slide decks, briefs, and structured exports all sit downstream of the same maintained knowledge base.

### IMPLEMENTATION SPECTRUM

**`minimal viable wiki`**  
Raw sources + wiki pages + index + schema.

**`lifecycle-enhanced wiki`**  
Adds confidence, supersession, and retention controls.

**`structured wiki`**  
Adds entity extraction, typed relationships, and a graph.

**`automated / scaled / collaborative wiki`**  
Adds hooks, hybrid search, quality scoring, shared-private scoping, and coordination.

---

## Dependency Graph (edges)

```text
raw sources ──► ingest ──► wiki pages
schema document ──► ingest
schema document ──► query
schema document ──► lint

wiki pages ──► index.md
wiki pages ──► log.md
wiki pages ──► entity extraction
entity extraction ──► knowledge graph
knowledge graph ──► graph traversal

BM25 ─┐
vector search ─┼──► hybrid search / RRF fusion ──► query
graph traversal ─┘

working memory ──► episodic memory ──► semantic memory ──► procedural memory
confidence scoring ──► semantic memory
supersession ──► semantic memory
retention decay ──► semantic memory

new source event ──► ingest
session start event ──► context loading
session end event ──► episodic compression
query event ──► crystallization check
memory write event ──► contradiction check / supersession
scheduled event ──► lint / consolidation / retention decay

wiki pages ──► markdown output
wiki pages ──► tables / timelines / graphs / slide decks / exports / briefs
```

---

## Phase–Feature Matrix

| Phase | Features | Role |
|---|---|---|
| Source capture | raw sources, attachments, clipper workflow | canonical input |
| Knowledge compilation | ingest, wiki pages, index.md, log.md | maintained artifact layer |
| Control plane | schema document | operating contract |
| Lifecycle management | confidence, supersession, forgetting, consolidation tiers | keeps knowledge healthy over time |
| Structure | entity extraction, typed relationships, graph | enables richer navigation |
| Retrieval | index lookup, BM25, vector, graph traversal, hybrid fusion | finds relevant state at scale |
| Maintenance | lint, self-healing, contradiction resolution | repairs and audits |
| Automation | hooks on source/session/query/write/schedule | reduces manual bookkeeping |
| Collaboration | mesh sync, shared/private scopes, work coordination | multi-user / multi-agent viability |
| Governance | filtering, audit trail, reversible bulk ops | safety and accountability |
| Compounding outputs | crystallization, markdown + non-markdown outputs | turns work into durable artifacts |

---

## Harness Adaptation Notes

1. **Already absorbed into live skills:** the local skill library README already records that the `llm-wiki` concept was folded into existing skills rather than promoted as a standalone branch.
2. **Best fit for compiled knowledge behavior:** `agentic_kg_memory` owns the compiler-side knowledge model, including the second-pass ideas from the source such as consolidation tiers, temporal decay, supersession, automation hooks, graph traversal, and crystallization.
3. **Best fit for retrieval behavior:** `gist-retriever` owns the staged access path from markdown/index lookup into hybrid retrieval.
4. **Best fit for project-vs-corpus boundary:** `memory-bank` carries the sharper separation between operating memory and compiled corpus memory.
5. **Best fit for governance/lifecycle promotion:** `skill-wiki` remains the promotion/governance side of the library, not the corpus store itself.
6. **Not a standalone new branch by default:** this source reads more like an architectural parent concept than a single self-contained operational skill.

---

## Bottom-Line Classification

- **Core pattern:** compiled wiki between raw sources and answers
- **Load-bearing innovations over vanilla RAG:** persistence, lifecycle management, graph structure, hybrid retrieval, automation
- **Most reusable concepts:** consolidation tiers, supersession, crystallization, graph-augmented retrieval, event-driven maintenance
- **Best local mapping:** `agentic_kg_memory` + `gist-retriever` + `memory-bank`, with governance handled separately
