---
name: arxiv-bridge
description: >
  Upstream arXiv paper discovery layer for scientific/academic queries.
  Bridges local corpus retrieval with live Semantic Scholar and arXiv Atom APIs.
  Use when the local CSV/pgvector corpus may not have the most relevant recent
  papers, or when the user's query warrants fresh upstream discovery.
parent_skill: deep-research
tier: L0-supplement
status: active
last_validated: 2026-05-02
---

# arXiv Bridge Subskill

## Purpose

When a query is **scientific or arxiv-related**, this subskill extends the local
3-layer retrieval stack with live upstream search:

1. **Semantic Scholar** (semantic ranking, citation counts, arXiv IDs) — primary
2. **arXiv Atom API** (BM25 keyword, free, no auth) — fallback when S2 unavailable/rate-limited
3. **Local CSV deduplication** — marks papers already in corpus (`local=True`)
4. **SQLite utility cache** — so each novel paper is scored (via LLM or citation proxy) at most once

## Trigger Conditions

Invoke this subskill when ALL of the following hold:

- Topic is scientific / academic / research-oriented (arxiv, papers, methods, models, benchmarks)
- Local retrieval (`run.py`) returns < 5 results, OR user explicitly wants fresh papers
- The user's question can benefit from papers published after the local corpus snapshot

Do NOT invoke for:
- Finance, news, current events (no arXiv relevance)
- Pure code or engineering questions
- Questions where the local corpus is already known to be current

---

## Architecture

```
user query
    │
    ▼
bridge_search(query, limit=20)
    │
    ├── [1] Semantic Scholar API   ──► ranked candidates (semantic)
    │   api.semanticscholar.org/graph/v1/paper/search
    │   fields: title, abstract, externalIds, year, citationCount
    │   free tier: 100 req/5 min (no key), 1 req/sec (with key)
    │
    ├── [fallback] arXiv Atom API  ──► BM25 results (keyword)
    │   export.arxiv.org/api/query
    │   fields: ti: (title), abs: (abstract)
    │   free, no auth, 3s inter-request polite delay
    │
    ├── deduplicate on normalised arxiv_id
    │
    ├── score: utility × relevance
    │   utility = local CSV value OR SQLite cache OR citation_count proxy
    │   relevance = linear decay from rank position (1.0 → 0.1)
    │   composite = utility × relevance → sort descending
    │
    └── tag each result: local=True/False, source="s2"|"arxiv_api"|"local"|"cached"
```

---

## Implementation

**File:** `C:\Users\user\arxiv_id_lists\arxiv_bridge.py`

**Main entry point:**
```python
from arxiv_bridge import bridge_search, BridgeResult

results: list[BridgeResult] = bridge_search(
    query="agentic memory",
    limit=20,     # max candidates per upstream source
    verbose=True, # print progress to stdout
)

# Each BridgeResult has:
# .arxiv_id, .title, .abstract, .year, .citation_count
# .utility_score, .relevance_score, .composite
# .source, .local, .pdf_url
```

**CLI flags (via `arxiv_pipeline/run.py`):**

```bash
# Bridge search + utility derivation + full tiered extraction
python arxiv_pipeline\run.py "agentic memory" --bridge --bridge_derive 5 --extract --output _report.md

# --bridge          enable upstream arXiv/S2 search and CSV injection before retriever
# --bridge_derive N derive LLM utility for the first N novel (uncached) papers (default: 0 = citation proxy only)
# --extract         run tiered full-pipeline extraction on top papers after retrieval
# --output FILE     write syllogism report to FILE (default: results.md)
```

**⚠️ Run sequentially, not in parallel.** Concurrent instances cause:
- GPU memory contention (3× model loads competing on same device)
- S2/arXiv API rate-limit collisions
- copilot-proxy LLM timeout under concurrent load

**CLI test (bridge module standalone):**
```bash
cd C:\Users\user\arxiv_id_lists
C:\Users\user\py310\Scripts\python.exe arxiv_bridge.py "agentic memory" --limit 20 --top-k 10
```

---

## Utility Cache

- **Location:** `checkpoints/utility_cache.db`
- **Schema:** `(arxiv_id TEXT PK, title TEXT, utility REAL, citation_count INT, cached_at TEXT)`
- **Cold-start proxy:** `min(5.0, 0.5 + log1p(citations) / log1p(5000) * 4.5)`
  - 0 cites → 0.5, 50 cites → 2.5, 1000 cites → 4.5, 5000 cites → 5.0
- Papers already in local CSV use the CSV `utility` column directly
- LLM-derived utility (when available) should be written back: `_cache_utility(aid, title, score, cites, conn)`

---

## Integration with run.py (On-Demand Extraction)

After `bridge_search`, novel papers (`.local=False`) can be fed into the tiered
extraction pipeline in `arxiv_pipeline/run.py`:

```python
from arxiv_bridge import bridge_search
from arxiv_pipeline.run import _run_on_demand_extraction

results = bridge_search("agentic memory", limit=20)
novel = [r for r in results if not r.local]

# Top-3 novel → full VLM pipeline (if _methods.md missing)
# Remainder → text-only Phase 5 (no _methods.md written to disk)
# See: EXTRACT_EAGER_BASE, EXTRACT_EAGER_EXTENDED, EXTRACT_MIN_FULL in run.py
```

**Tiered extraction rules (from run.py):**
- `EXTRACT_EAGER_BASE = 3` — eager full-pipeline window when any top-3 missing `_methods.md`
- `EXTRACT_EAGER_EXTENDED = 5` — when all top-3 already have `_methods.md`
- `EXTRACT_MIN_FULL = 2` — floor: always achieve at least 2 fully-enriched results
- Papers outside eager set → `_extract_methods_text_only()` → prepends `⚠️ Text-only extraction`
- `_methods.md` on disk = only ever from full VLM-enriched pipeline (invariant)

---

## Integration with deep-research

When the deep-research planner identifies a scientific/academic query, the
researcher node should call `bridge_search` as an additional evidence source
alongside `searxng_search` / `web_fetch`:

```python
# In researcher node — supplement searxng with arxiv bridge
from arxiv_bridge import bridge_search

bridge_results = bridge_search(query=subquestion.text, limit=20)
for r in bridge_results[:5]:
    # Convert to candidate evidence; use arXiv abstract PDF as source
    # web_fetch(r.pdf_url or f"https://arxiv.org/abs/{r.arxiv_id}")
    # → mints source_id for pgvector_upsert
```

**Source quality tier:** arXiv papers are Tier 1 (peer-reviewed preprints). Assign
`confidence=0.85` by default; lower to `0.70` for very recent (< 3 months old)
or uncited papers.

---

## Semantic Scholar API Key

Without an API key the free tier allows 100 req/5 min (often rate-limited under
bulk use). With a free API key: 1 req/sec.

Get a key at: https://www.semanticscholar.org/product/api#api-key

Set it as an environment variable:
```bash
set SEMANTIC_SCHOLAR_API_KEY=your_key_here
# or in .env
SEMANTIC_SCHOLAR_API_KEY=your_key_here
```

The bridge reads `os.environ.get("SEMANTIC_SCHOLAR_API_KEY", "")` automatically.

---

## Normalised arXiv ID

All IDs are normalised to dot form without version suffix:
- `2601_09113` → `2601.09113`
- `2601.09113v2` → `2601.09113`
- `http://arxiv.org/abs/2601.09113v3` → `2601.09113`

Deduplication and CSV lookup both use this canonical form.

---

## Rate Limits & Polite Delays

| Source | Limit (no key) | Limit (with key) | Delay applied |
|---|---|---|---|
| Semantic Scholar | 100 req/5 min | 1 req/sec | 1.0s post-call |
| arXiv Atom API | ~3 req/sec | n/a | 3.0s post-call |

If S2 returns 429, the bridge automatically falls back to arXiv Atom API.
If both fail, `bridge_search` returns `[]` with a printed warning.

---

## Known Limitations

1. **Citation count = 0 on arXiv fallback** — the Atom API does not return citation counts.
   Cold-start utility defaults to 0.50 for all results, so relevance rank is the only
   discriminator. Once S2 is available (API key or retry), cached counts improve scoring.

2. **No full-text from bridge** — `bridge_search` returns title + abstract only.
   Full-text (PDF) requires a subsequent `web_fetch` or the Phase 1-5 pipeline.

3. **Local utility not backfilled** — if a paper is not in the local CSV and has never
   been LLM-scored, utility_proxy ≈ citation-count proxy. Set up the ingest daemon
   (`ingest_daemon.py`) to backfill LLM utility scores over time.

4. **S2 only indexes papers with abstracts** — very new preprints (< 1 week) may not
   appear. arXiv Atom fallback has better recency coverage.
<!-- consolidation:see-also:start -->
## See Also
[[auto-ingest]]  [[pdf-extraction]]  [[deep-research]]
<!-- consolidation:see-also:end -->
