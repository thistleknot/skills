# Ingestion pipeline — full detail

Entry point: `python scripts/ingest_skills.py` (idempotent, re-runnable; see
its module docstring for the exact CLI).

## 1. Chunking

Docling's `DocumentConverter().convert()` reads each `skills_master/<topic>/
<slug>.md` file directly (verified against Docling's docs — `convert()`
accepts markdown by extension, not just PDFs; no OCR/VLM stage needed here,
unlike the PDF-sourced books this corpus was originally built from). One
document per file. The `HybridChunker` is constructed with an **explicit**
`HuggingFaceTokenizer` (MiniLM, `max_tokens=1900`) — NOT the bare
`HybridChunker()` default, whose token budget has no relationship to nomic's
2048-token embedder context. MiniLM-as-proxy with margin under 2048 matches
the sibling `book_units_pgvector_ingest.py`'s tactic. The chunker's
tokenizer-aware merge (`merge_peers=True`) keeps each chunk under that budget
while respecting the file's own `## ...` section boundaries where possible
(Docling's chunker is heading-aware, so a chunk rarely straddles two `##`
sections unless a single section is large — e.g. a long Python code block).

Frontmatter (name/description/topic/sources/merged_slugs) is regex-parsed
**once per file before chunking**, and KG extraction + chunking run on the
frontmatter-stripped body — so source book names and chunk-ref numbers never
become graph nodes. The parsed frontmatter is stored in each chunk's
`cmetadata` as `skill_name`, `skill_description`, `source_books`,
`merged_slugs`. This is metadata about the *skill*, not the chunk — every chunk
from one file shares it.

## 2. Embedding

Model: `nomic-embed-text` via Ollama (`http://localhost:11434/api/embeddings`),
`search_document: ` prefix on index, `search_query: ` prefix at retrieval
time (nomic-embed-text-v1.5 is task-prefixed — see `book_units_pgvector_
ingest.py`'s `DOC_PREFIX` constant for the exact convention this reuses).
768-dim. One retry on transient failure; a hard failure raises rather than
silently skipping a chunk — a missing vector is worse than a stopped run,
per the same reasoning `book_units_pgvector_ingest.py` documents.

**Why nomic over jina for this corpus**: matches the existing ingest
pipeline's proven choice. jina was considered and explicitly rejected —
2048-token context is enough for any single skill-file chunk here (the
source files are already capped at a few hundred lines each), and nomic
embeds noticeably faster locally with no external API dependency.

## 3. KG entity extraction

This stage borrows [[kg_ontology]]'s SPO-extraction shape but **deliberately
DEPARTS from its synset-canonical identity contract**. Read the identity rule
below before touching anything here.

### Canonical identity — normalized surface span (NOT synset)

The **canonical entity id is the normalized surface span**: ASCII-folded,
lowercased, spaces->underscores (`ridge_regression`, `gradient_descent`). This
IS the graph node identity in neo4j. Rationale: WordNet mis-resolves ML terms
("ridge regression" -> "mountain ridge"), which would poison the graph; the
whole design intent is domain-correct entities as the retrieval backbone. This
is a conscious departure from `kg_ontology`, whose synset-canonical ids do not
survive contact with a technical ML corpus.

WordNet synsets/hypernyms are kept **only as enrichment tokens** for plain
single common words (stored as `enrich_tokens` in metadata), never as identity.
There is **no per-triplet synset-selection LLM call** — that stage was removed.

### Stage A — triplet extraction (the single LLM call per chunk)

One Ollama `/api/chat` call per chunk extracts raw SPO facts:
`{"subject": "...", "predicate": "...", "object": "..."}` per fact, zero or
more facts per chunk (a purely definitional chunk may yield zero — a valid
outcome, not an error). Object may be `null` for intransitive/stative
predicates. Qwen3 thinking is suppressed (`/no_think` in the prompt + top-level
`think:false` in the request body) per [[ollama-structured]]. This is the ONLY
KG LLM call in the pipeline.

### spaCy named-entity extraction (separate, no LLM)

Run spaCy's NER over the (frontmatter-stripped) chunk body independently. Noise
labels (CARDINAL, ORDINAL, DATE, TIME, PERCENT, MONEY, QUANTITY, etc.) and
numeric / book-name entities are **filtered out** so they never reach the graph.
Surviving entities get their normalized surface span as canonical identity (same
rule as above) and feed the neo4j graph as `Entity` nodes.

### Cost/scale note

One LLM call per chunk (not per triplet — the removed synset-selection stage
was the per-triplet cost). At 1,467 files × several chunks each this is still a
real batch job (thousands of LLM calls under docling GPU contention — 3 files
took >9.5 min), not a quick script. Use a local Ollama model (see
[[litellm-windows-service]], [[ollama-structured]]). Batch and checkpoint
(sqlite load-if-exists) so a killed run resumes instead of re-processing.

## 4. Storage — PGVector `cmetadata`

Chunks are stored via langchain `PGVector` (collection `data_science_skills`,
`OllamaEmbeddings(model="nomic-embed-text")`, connection
`postgresql+psycopg://langchain:langchain@localhost:5432/langchain`). Each chunk
is a langchain `Document` — `page_content` is the chunk body, and **all KG /
entity / frontmatter data lives in the `cmetadata` JSONB column**. There is NO
custom `data_science_skills` table, no `bm25_sparse` column, no `dss_*` tables;
PGVector owns and manages its own schema (`langchain_pg_collection`,
`langchain_pg_embedding`).

Representative `cmetadata` shape per chunk:
```json
{
  "skill_slug": "probability-stats/median",
  "topic": "probability-stats",
  "chunk_index": 3,
  "header_path": ["Key mechanics"],
  "skill_name": "median",
  "skill_description": "...",
  "source_books": ["..."],
  "merged_slugs": ["..."],
  "triplets": [
    {"subject": "ridge regression", "predicate": "penalizes", "object": "large coefficients"}
  ],
  "entities": ["ridge_regression", "gradient_descent"],
  "spacy_entities": [{"text": "ReLU", "label": "PRODUCT", "canonical_id": "relu"}],
  "enrich_tokens": ["regularization", "penalty"]
}
```

## 5. Entity co-occurrence graph — neo4j (`dss-neo4j`)

The graph lives in a **dedicated neo4j container**, NOT in postgres. Bolt
`localhost:7688`, browser `localhost:7475`, auth disabled, compose file
`docker/neo4j-compose.yml`, started with
`docker compose -f docker/neo4j-compose.yml up -d`.

Node/edge model:
```
(Chunk {id, skill_slug})-[:HAS_ENTITY]->(Entity {id})
(Chunk)-[:OF_SKILL]->(Skill {slug, topic, tags})
(Entity)-[:IN_SKILL]->(Skill)
(Entity)-[:CO_OCCURS {weight}]-(Entity)
```

`Entity.id` and `Chunk.id` are normalized surface spans / chunk ids (see section
3). Build rule: for every chunk, every pair of distinct canonical entities that
co-occur in that chunk increments the `CO_OCCURS.weight` between them by 1
(normalized ordering, consistent). This implements "all entities in a chunk
connect to each other," which trivially includes "connects through the
predicate" (subject and object of a triplet always co-occur).

A chunk's **graph-density score** = `SUM(weight)` over all `CO_OCCURS` edges
touching any of that chunk's entities, normalized by entity count (avoids
rewarding chunks just for mentioning more things). Treat the normalization as
tunable, not fixed.

## 6. Tags

Per skill (`skill_slug`): the top-N most frequent canonical entities across that
skill's chunks become its tags (N default 5, tunable), stored on the `Skill`
node in neo4j (`Skill.tags`). Recomputed on each ingestion run (cheap relative
to the LLM extraction stage, so no incremental-update complexity needed).

## Service registration

See `litellm-windows-service`'s SKILL.md for the full NSSM procedure this
reuses verbatim (portable nssm.exe acquisition, the `-File`-not`-Command`
elevation trap, `PYTHONIOENCODING`/`PYTHONUTF8` requirement, the
service-reports-Running-before-port-listens verification loop, rollback).
The only substitution is the target executable and args — see
`scripts/register-service.ps1`, which is `litellm-windows-service`'s
`register-litellm-service.ps1` with `$LiteLLM`/`$Config`/`$Port`/`$Svc`
retargeted to this skill's `mcp_server.py`.
