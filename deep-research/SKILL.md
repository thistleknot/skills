---
name: deep-research
description: >
  Deep research framework protocol. Use when a task requires gathering
  web evidence, multi-source corroboration, or producing a claim-backed
  report before or alongside agentic harness work. Covers graph
  architecture, MCP tool suite, state flow, config, and integration
  with the dark_factory TaskSpec pipeline.
parent_skill: agentic-harness
tier: L0
status: active
last_validated: 2026-04-28
---

# Deep Research Framework

## Retrieval Tier: L0 (Web Evidence)

This skill is **L0** in the three-tier knowledge retrieval cascade:

| Tier | Skill | When to use |
|---|---|---|
| L2 | `memory-bank` / skills markdown | Try first — fast, no server needed |
| L1 | `agentic_kg_memory` / `gist-retriever` | Try if L2 misses |
| **L0** | **`deep-research`** | **Try if L1 misses — expensive, web fetch** |

Only trigger L0 when L2 and L1 have both failed to surface sufficient evidence.

### Store-back contract

After a successful L0 research run:
1. All extracted `Triplet` objects **must** be upserted into L1 (via `pgvector_upsert`)
2. If the findings are stable, reusable patterns (procedures, protocols, constraints) — promote to L2 by writing or updating a skill markdown file
3. Do not discard L0 research results without persisting them to at least L1

## When to use

- You need **multi-source corroboration** — more than one independent domain must back a claim
- You need a **structured evidence trail** — every claim must cite a `source_id` from a real fetch
- The question decomposes into **parallel subquestions** — e.g., "what is X", "how does X relate to Y"
- You're **seeding a TaskSpec** — use the report as `context` or `background` in the TaskSpec JSON
- You need **saturation detection** — stop when new evidence rate falls below `saturation_theta`

Do NOT use it for:
- Single-turn factual lookups (use a direct LLM call)
- Questions where all sources are local (use grep/glob, no web needed)
- Pure code tasks with no evidence requirement

---

## Architecture

```
question
  │
  ▼
┌─────────┐   should_dispatch?
│ planner │ ─────────────────────► [__end__] (no subquestions)
└─────────┘
     │ subquestions
     ▼
┌────────────┐   Send() per subquestion
│ dispatcher │ ──────────────────────────┐
└────────────┘                           │
                                         ▼ (parallel)
                                   ┌────────────┐
                                   │ researcher │  search → fetch → extract triplets
                                   └────────────┘
                                         │ evidence
                                         ▼
                                   ┌───────────┐
                                   │ reflector │  saturation / coverage / corroboration
                                   └───────────┘
                                         │ verdict
                          ┌──────────────┼──────────────┐
                          ▼              ▼              ▼
                       planner      dispatcher      synthesizer ──► report
                  (new subqs)     (more research)    (done)
```

### Nodes

| Node | Role | LLM | Key output |
|---|---|---|---|
| `planner` | Decomposes question into 3-7 subquestions | `PLANNER_*` | `subquestions: list[Subquestion]` |
| `dispatcher` | Fans out via `Send` | none | parallel researcher invocations |
| `researcher` | Search + fetch + triplet extraction | `RESEARCHER_*` | `evidence: list[Triplet]` |
| `reflector` | Judge saturation/coverage/corroboration | `REFLECTOR_*` | `last_reflection` verdict |
| `synthesizer` | Assembles report with claim graph | `SYNTHESIZER_*` | `report: str` (markdown) |

---

## MCP Tool Suite

Server at `http://localhost:8765/mcp` (configured via `MCP_URL`).
All six tools registered in `mcp_server/server.py`.

| Tool | Purpose | Key return |
|---|---|---|
| `searxng_search(query, max_results)` | Primary homelab search (SearXNG at `SEARXNG_URL`) | `{results: [{url, title, snippet}]}` |
| `web_search(query, max_results, recency)` | Fallback — Brave or Tavily APIs | same shape |
| `web_fetch(url)` | httpx → retry → Selenium tiered pipeline; **creates source_id** at all tiers | `{source_id, title, text, url}` |
| `pgvector_retrieve(query, top_k)` | Semantic search over prior corpus | `{chunks: [{source_id, text, score}]}` |
| `pgvector_upsert(triplets, run_id)` | Write triplets — **requires source_id** | `{upserted: int}` |
| `sqlite_scratch(thread_id, op, key, value)` | Per-thread KV scratchpad | varies |

**Critical invariant:** every `Triplet.source_id` MUST exist in the `sources` table.
The only way to produce a valid `source_id` is via `web_fetch`. Schema-enforced at upsert.

### web_fetch Fetch Pipeline

`web_fetch` uses a tiered acquisition strategy. Both tiers feed the same downstream
pipeline that extracts content and mints `source_id` — the invariant is preserved
regardless of which tier succeeds.

```
httpx GET (user-agent rotation, 10 s timeout)
  ├─ 2xx + no wall signal  →  extract, mint source_id, return
  ├─ transport / transient error  →  retry up to FETCH_RETRY_ATTEMPTS with exponential backoff
  └─ wall detected after retries  →  escalate to Selenium
                 │
                 ▼
    Selenium headless Chrome  [asyncio.to_thread + Semaphore(SELENIUM_MAX_CONCURRENCY)]
      ├─ renders page, waits for <body>
      ├─ post-render wall check  (rerun heuristics on rendered text)
      ├─ len(text) > 200 and no challenge markers  →  extract, mint source_id, return
      └─ still walled or timeout  →  ValueError  (researcher node skips URL)
```

**Wall detection heuristics** (applied at httpx tier and again after Selenium render):

| Tier | Hard triggers — always escalate/fail | Soft triggers — escalate when combined |
|---|---|---|
| HTTP status | 403, 429, 503 | — |
| Challenge markers | "Enable JavaScript", "cf-browser-verification", "Checking your browser", "verify you are human", "Bot detection", "cf-chl", "Just a moment" | — |
| Content | — | `text/html` body < 500 chars with no `<p>` or `<article>` tags |

**Selenium scope:**
- Handles: client-rendered SPAs, cookie-consent interstitials, light JS redirects.
- Does NOT bypass: Cloudflare Enterprise, DataDome, PerimeterX, CAPTCHA challenges.
- Always run via `asyncio.to_thread(_fetch_with_selenium, url)` — never block the event loop.
- Guarded by `asyncio.Semaphore(SELENIUM_MAX_CONCURRENCY)` to prevent grid exhaustion.

---

## Key Data Types (`schemas/models.py`)

```python
class Triplet(BaseModel):
    triplet_id: str        # ULID
    subquestion_id: str
    subject: str
    predicate: str
    object: str
    source_id: str         # MUST come from web_fetch — enforced at pgvector_upsert
    kind: EvidenceKind     # "observed" | "inferred"
    confidence: float      # [0.0, 1.0]
    extracted_at: datetime
    extractor_model: str

class Subquestion(BaseModel):
    subquestion_id: str    # ULID
    text: str
    status: Literal["pending", "in_progress", "satisfied", "abandoned"]
    depends_on: list[str]  # other subquestion_ids

class Claim(BaseModel):
    claim_id: str
    statement: str
    triplet_ids: list[str]   # min 1
    source_ids: list[str]    # min 1
    domain_count: int
    confidence: float
```

`ResearchState` (`schemas/state.py`):
```python
class ResearchState(TypedDict):
    run_id: str; thread_id: str; question: str
    budget_caps: BudgetCaps
    subquestions: list[Subquestion]
    evidence: Annotated[list[Triplet], operator.add]  # append-only, concurrent-safe
    claims: list[Claim]; coverage: dict[str, CoverageStat]
    saturation_window: list[float]; last_reflection: dict | None
    budget_used: BudgetSnapshot; pending_review: bool; report: str | None
```

---

## Configuration (env vars / `.env`)

### Per-role LLM endpoints
Each of the 5 roles gets independent routing — swap local vs cloud per role:

```bash
PLANNER_BASE_URL=http://127.0.0.1:8081/v1
PLANNER_MODEL=qwen3
PLANNER_API_KEY=local

RESEARCHER_BASE_URL=http://127.0.0.1:8081/v1
RESEARCHER_MODEL=qwen3
RESEARCHER_API_KEY=local

REFLECTOR_BASE_URL=http://127.0.0.1:8081/v1
REFLECTOR_MODEL=qwen3
REFLECTOR_API_KEY=local

SYNTHESIZER_BASE_URL=http://127.0.0.1:8081/v1
SYNTHESIZER_MODEL=qwen3
SYNTHESIZER_API_KEY=local
```

### Services
```bash
SEARXNG_URL=http://localhost:8888          # homelab SearXNG
MCP_URL=http://localhost:8765/mcp
PGVECTOR_DSN=postgresql://user:pass@localhost:5432/harness
SQLITE_PATH=./store/harness.sqlite
```

### Selenium fallback
```bash
SELENIUM_ENABLED=true                              # master switch; false disables tier 2 entirely
SELENIUM_REMOTE_URL=http://localhost:4444/wd/hub   # optional; uses local chromedriver if unset
SELENIUM_TIMEOUT_SECONDS=30                        # page-load + wait timeout per attempt
SELENIUM_MAX_CONCURRENCY=3                         # max parallel browser sessions
FETCH_RETRY_ATTEMPTS=2                             # httpx retry count before Selenium escalation
FETCH_RETRY_BACKOFF_SECONDS=1.5                    # base delay for exponential backoff
```

### Termination thresholds
```bash
SATURATION_THETA=0.15          # stop when novel-evidence rate < 15%
COVERAGE_MIN_DOMAINS=3         # min independent domains per subquestion
CORROBORATION_MIN_SOURCES=2    # min sources per load-bearing claim
```

### Budget caps (via `BudgetCaps` on run creation)
```python
BudgetCaps(
    max_tokens_total=1_000_000,
    max_wall_clock_seconds=1800,
    max_tool_calls=200,
    max_iterations=10,
)
```
Budget is checked before each routing decision. Overflow routes to synthesizer
(graceful termination) not crash.

---

## Invoking Programmatically

### Minimal research run
```python
import asyncio
from ulid import ULID
from graph.builder import build_graph
from schemas.models import BudgetCaps, BudgetSnapshot

async def run_research(question: str) -> str:
    graph = build_graph()
    run_id = str(ULID())
    state = {
        "run_id": run_id,
        "thread_id": run_id,
        "question": question,
        "budget_caps": BudgetCaps(),
        "subquestions": [],
        "evidence": [],
        "claims": [],
        "coverage": {},
        "saturation_window": [],
        "last_reflection": None,
        "budget_used": BudgetSnapshot(),
        "pending_review": False,
        "report": None,
    }
    result = await graph.ainvoke(state)
    return result.get("report", "")

report = asyncio.run(run_research("What are the key principles of abductive reasoning?"))
```

### Via FastAPI (control plane)
```bash
# Start the API
uvicorn app.main:app --port 8000

# Submit a task
curl -X POST http://localhost:8000/tasks \
  -H "Authorization: Bearer $HERMES_TOKEN" \
  -H "Content-Type: application/json" \
  -d '{"question": "...", "budget_overrides": {"max_iterations": 5}}'

# Stream events
curl http://localhost:8000/events \
  -H "Authorization: Bearer $OPENCLAW_TOKEN"
```

---

## Integration with Dark Factory TaskSpec

The deep research report can seed a TaskSpec's context:

```python
# 1. Run research on the domain
report = asyncio.run(run_research("Best practices for abductive reasoning datasets"))

# 2. Embed report as TaskSpec context
task_spec = {
    "task_name": "abductive-sft-dataset",
    "description": "Generate SFT dataset for abductive reasoning",
    "background": report[:2000],   # leading markdown summary
    "llm_output_schema": { ... },
    "behaviors": [...],
}
```

The triplets themselves can also become **training targets** — the researcher node already
extracts `(subject, predicate, object, source_id, confidence)` triples that match the
structure needed for the two-list entailment schema.

---

## Researcher Node: LLM Pattern

The researcher uses **streaming httpx** (not LangChain) to avoid `<think>` token overflow:

```python
payload = {
    "model": role.model,
    "stream": True,
    "messages": [{"role": "user", "content": prompt}],
    "temperature": role.temperature,
    "chat_template_kwargs": {"enable_thinking": False},   # ← disables Qwen3 reasoning mode
}
```

This is the correct pattern for local Qwen3 with `/v1/chat/completions`. Contrast with
the `/completion` endpoint pattern (triplet-abductive pipeline) which uses an empty
`<think></think>` prefix block instead.

**Use `enable_thinking: False` in `chat_template_kwargs` for `/v1/chat/completions`.**
**Use empty think block prefix for native `/completion` endpoint.**

---

## Failure Modes

| Symptom | Root cause | Fix |
|---|---|---|
| `pgvector_upsert` rejects triplets | `source_id` not in sources table | Always call `web_fetch` first; use returned `source_id` |
| Researcher returns empty evidence | SearXNG not running | Start SearXNG at `SEARXNG_URL`; framework falls back to DuckDuckGo/Wikipedia |
| Reflector always returns "continue" | JSON parse failure | Check reflector LLM output; adds `reasoning: "Failed to parse"` as signal |
| Graph loops indefinitely | Budget caps not set | Always pass explicit `BudgetCaps`; default `max_iterations=10` is the backstop |
| `<think>` tokens fill context | Qwen3 reasoning enabled | Set `chat_template_kwargs: {"enable_thinking": False}` in researcher role config |
| Planner returns 0 subquestions | LLM output not valid JSON | Check planner endpoint; `should_dispatch` routes to `__end__` cleanly |
| `pgvector` not reachable | Postgres not running | `pgvector_retrieve` degrades gracefully; `pgvector_upsert` raises — catch and log |
| Selenium fallback never activates | `SELENIUM_ENABLED=false` or unset | Set to `true`; ensure Chrome and matching chromedriver are installed |
| `chromedriver` not found | Binary missing or version mismatch | Install matching chromedriver or set `SELENIUM_REMOTE_URL` to point to a Selenium grid |
| Remote Selenium grid unreachable | Grid host down or wrong URL | Check grid health; unset `SELENIUM_REMOTE_URL` to fall back to local Chrome |
| Selenium page-load timeout | Page too slow or requires auth | Increase `SELENIUM_TIMEOUT_SECONDS`; log and skip URL after timeout |
| Selenium still returns challenge page | Modern anti-bot (Cloudflare Enterprise, DataDome, PerimeterX) | Expected — post-render wall check will reject it; log and skip URL |
| Selenium blocks asyncio event loop | Called directly without `to_thread` | Always wrap via `asyncio.to_thread(_fetch_with_selenium, url)` |
| Browser concurrency exhausted | `SELENIUM_MAX_CONCURRENCY` too low under parallel research | Increase limit or provision more Selenium grid nodes |

---

## Observability

- **LangGraph astream_events** → internal asyncio event bus → SSE at `/events`
- **Phoenix OTLP** at `PHOENIX_OTLP_ENDPOINT` (default `:6006`) for trace visualization
- **RAGAS eval** — out-of-band, reads completed runs from sqlite, writes scores back; never blocks data plane
- **Budget ledger** — every tool/LLM call writes a row: `run_id, node, tool, tokens_in, tokens_out, cost_estimate, latency_ms`

---

## Two-Plane Invariant

**Data plane** = LangGraph run. Pure functions over `ResearchState`. No I/O except tool calls and checkpointer.

**Control plane** = everything about runs. Lifecycle, budget, policy, events, scheduling, eval triggers. FastAPI + sqlite.

Never mix them. Agents read/write state only. Lifecycle management is control plane only.

---

## Perspective Diversity Pattern (STORM)

Single-thread research misses blind spots. Before dispatching subquestions, generate
**perspectives** — who would approach this question from a different angle?

```
question
  │
  ▼
perspective_generator
  ├── domain expert (e.g., "ML researcher")
  ├── practitioner (e.g., "engineer deploying this in prod")
  ├── critic (e.g., "someone who would challenge the consensus")
  └── adjacent domain (e.g., "economist looking at incentives")
  │
  ▼
planner (assigns subquestions to perspectives)
  │
  ├── perspective A → subquestions A1, A2
  ├── perspective B → subquestions B1, B2
  └── perspective C → subquestions C1
```

Each researcher carries its perspective in the system prompt. This produces
genuinely diverse evidence rather than n variants of the same search.

**When to activate:** questions with contested answers, recent rapid-change areas,
or any task where "what does the consensus say" is insufficient. Skip for narrow
factual lookups — perspectives add overhead without value there.

---

## Source Quality Hierarchy

Not all evidence is equal. Weight claims by source tier:

| Tier | Type | Weight |
|---|---|---|
| 1 | Peer-reviewed paper, official specification, primary source data | Highest |
| 2 | Official documentation, white paper, technical report from org involved | High |
| 3 | Reputable secondary coverage (major tech publication, known author) | Medium |
| 4 | Blog post, Stack Overflow, forum discussion | Low |
| 5 | Unverified claim, AI-generated content | Discard or flag |

**Corroboration rule:** a claim backed by two Tier-1 sources is near-certain.
A claim backed only by Tier-4 sources requires explicit flagging in the report.

**Recency matters:** for fast-moving fields (LLM, infra, security), a 2-year-old
Tier-1 paper may carry less weight than a recent Tier-3 source. Tag
`extracted_at` on every triplet and note staleness in the report when relevant.

**Conflict resolution:** when sources disagree, preserve both positions and note
the disagreement explicitly. Do not silently resolve toward the first source found.

---

## Per-Role Model Strategy

Each node has different performance requirements. Route accordingly:

| Node | Priority | Rationale |
|---|---|---|
| `planner` | Speed > quality | Decomposing into subquestions is a routing decision; a small model is fine |
| `researcher` | Quality + tool access | Triplet extraction from arbitrary web text needs strong instruction-following |
| `reflector` | Speed | Binary saturation verdict; a small model checking thresholds is sufficient |
| `synthesizer` | Quality | Final report generation; use best available model |

**Local vs cloud routing:** for homelab setups, researcher and synthesizer benefit
most from a capable local model (Qwen3 70B or similar). Planner and reflector can
run on a fast/small model. Per-role `BASE_URL` config makes this explicit.

**Thinking mode:** disable chain-of-thought/reasoning mode for researcher and
reflector (`enable_thinking: false` in `chat_template_kwargs` for Qwen3). The
structured output requirement means stray reasoning tokens pollute JSON parsing.
Synthesizer benefits from reasoning mode for complex multi-source synthesis.

---

## Citation Chain Integrity

Every claim in the report must be traceable back to a real fetch. The chain is:

```
Report claim
  └── Claim.triplet_ids[*]
        └── Triplet.source_id
              └── sources table row (minted by web_fetch ONLY)
```

**Invariant:** no Triplet may exist with a `source_id` not present in the `sources`
table. `pgvector_upsert` enforces this at the database layer. There is no workaround.

**Never mint source_ids manually.** The only valid source_id comes from `web_fetch`.
If a URL cannot be fetched (walled, timeout, CAPTCHA), do not create a triplet for it.
Log the skip; do not hallucinate evidence.

**Report quality signal:** count `domain_count` on the top claims. A report where
all claims come from a single domain has a corroboration failure — the reflector
should have requested more diverse sources. Check this at synthesis time.

---

## Research Anti-Patterns

| Anti-pattern | Symptom | Fix |
|---|---|---|
| Search-to-confirm | All evidence agrees with the initial hypothesis | Add a critic perspective; search for counterarguments explicitly |
| Depth-first tunnel | All evidence from one domain | Check `domain_count` at reflector; route back to planner for adjacent domains |
| Recency blindness | Synthesis relies on old sources for fast-moving topic | Filter by `extracted_at`; flag stale sources in synthesis prompt |
| Citation laundering | Claim cites a blog that cites a paper — blog is the `source_id` | Upgrade: fetch the original paper; use it as source_id instead |
| Saturation fraud | Reflector claims saturation with < 3 independent domains | `COVERAGE_MIN_DOMAINS=3` is a hard floor; override only with explicit justification |
