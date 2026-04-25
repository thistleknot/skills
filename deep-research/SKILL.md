---
name: deep-research
description: >
  Deep research framework protocol. Use when a task requires gathering
  web evidence, multi-source corroboration, or producing a claim-backed
  report before or alongside agentic harness work. Covers graph
  architecture, MCP tool suite, state flow, config, and integration
  with the dark_factory TaskSpec pipeline.
parent_skill: agentic-harness
---

# Deep Research Framework

## When to use

Use this framework (not a one-shot LLM call) when:

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
| `web_fetch(url)` | Fetch + extract content; **creates source_id** | `{source_id, title, text, url}` |
| `pgvector_retrieve(query, top_k)` | Semantic search over prior corpus | `{chunks: [{source_id, text, score}]}` |
| `pgvector_upsert(triplets, run_id)` | Write triplets — **requires source_id** | `{upserted: int}` |
| `sqlite_scratch(thread_id, op, key, value)` | Per-thread KV scratchpad | varies |

**Critical invariant:** every `Triplet.source_id` MUST exist in the `sources` table.
The only way to produce a valid `source_id` is via `web_fetch`. Schema-enforced at upsert.

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
| pgvector not reachable | Postgres not running | `pgvector_retrieve` degrades gracefully; `pgvector_upsert` raises — catch and log |

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
