# memory-index

Embed-and-retrieve layer over the markdown memory store. This is the operational
counterpart to the `agentic_kg_memory` skill: that skill *describes* a Chroma-backed
semantic memory; this tool *is* one, scoped to the harness's markdown memories.

**Not a skill** — this folder has no `SKILL.md` on purpose, so it does not compete for
routing with `agentic_kg_memory` / `memory-architecture`. It's a plain CLI tool.

## Model

- **Source of truth:** the markdown files in the global memory dir `C:\Users\user\memory-bank`.
  The harness memory path (`…\.claude\projects\…\memory`) is a **junction** to it, so harness
  auto-memory and this tool share one store. Nothing here mutates meaning; the vector store
  is a derived index.
- **Index:** a Chroma collection at `<memory-dir>/.chroma/` (cosine space), served by an
  always-on service (below). Small atomic memories embed as one vector; large living docs
  are **chunked** (~4K chars, header-aware) so their tails stay searchable — a hit reports
  `file › heading`.
- **Embedder:** local Ollama `nomic-embed-text` (768-dim), reached at `http://127.0.0.1:11434`.
  No API calls, no GPU-training contention. Document/query text carries the nomic
  `search_document:` / `search_query:` task prefixes.

## Always-on service (why nothing auto-starts)

Multiple sessions/agents must share one store without each spinning up (and locking) the
on-disk DB. So Chroma runs as a Windows service that **owns** the store; every `mem` call
is a thin HTTP client.

- **Service:** `mem-chroma` — NSSM-wrapped `chroma run --path <memory>/.chroma
  --host 127.0.0.1 --port 8055`. Auto-start on boot, restart-on-crash, rotating logs in
  `logs/`. Mirrors the `phone-storage-guard` / `litellm-windows-service` conventions.
- **Install / repair:** run `register-mem-service.ps1` **elevated** (once). Configurable at
  the top of that script: `$MemDir`, `$Host_`, `$Port` (keep them in sync with the
  `MEM_CHROMA_*` / `MEM_DIR` env vars).
- **`mem.py` connects to the service automatically.** If the service is down it falls back
  to opening the local file store directly (safe: nothing else holds it then). `mem stats`
  prints `backend: service …` or `backend: local file … (service down)` so you always know.

Two services back this: **Ollama** (embeddings, already running) and **mem-chroma** (index).
Agents never start either — they just connect.

> **Gotcha:** `OLLAMA_HOST` is set to `0.0.0.0:11434` on this machine. That's a valid
> *bind* address but an invalid *connect* address — the Python client must dial
> `127.0.0.1`. The tool hardcodes that default; override with `MEM_OLLAMA_HOST`.

## Usage

```bash
python mem.py index                 # reconcile the doc index with the markdown files
python mem.py search "query" -k 5   # semantic recall (optionally --type feedback)
python mem.py stats                 # doc/log counts + per-type breakdown + hit summary
python mem.py add \                 # write a durable memory + MEMORY.md pointer + index it
    --name my_slug --type feedback \
    --description "one-line recall hook" \
    --body -                        # body from stdin ('-'), or pass inline text
python mem.py log "a worked-out bit" # cheap ephemeral write to the annealing log
python mem.py anneal --dry-run       # evict stale, under-recalled log bits
```

### Two tiers: durable docs vs the annealing log

Entries in the collection come in two kinds (see `memory-bank` skill for the tier contract):

- **docs** — durable markdown (`add` / indexed files). Curated, never anneal.
- **log** — ephemeral "worked-out bits" written by `mem log`. Cheap; not curated.

The log is a proving ground. Each `search` that surfaces a log bit at similarity ≥ 0.6
**bumps its hit count**. At **3 hits it auto-promotes** to durable markdown — global
(`~\memory-bank`) by default, or a repo's `.memory-bank` if logged with
`--scope local --repo <path>` — and the log vector is dropped. So: write to the log freely;
useful bits earn their way into durable markdown, noise anneals away. Use `search --no-count`
to browse without affecting promotion.

**Promotion is silent to the operator; the agent curates.** A promoted file carries
provenance in its frontmatter (`promoted_from: chroma-log`, `recalls: N`) and a closing body
note saying it was auto-promoted after N recalls — so an agent reading it knows to keep,
refine, or delete it. There is no user cancel prompt by design.

**Annealing is scheduled, not manual.** `register-anneal-task.ps1` (run elevated) installs
the `mem-anneal` Scheduled Task — SYSTEM principal, weekly (Sun 3 AM), logging to
`logs\anneal.log` — which runs `mem anneal` to evict log bits still under `PROMOTE_AT` hits
past the TTL (default 30d). Run `mem anneal --dry-run` anytime to preview.

### `mem` from anywhere

`mem.cmd` (cmd/pwsh) and `mem.ps1` (PowerShell) wrap the CLI: they self-locate `mem.py`
and use the `py310` interpreter that has the packages. Add this folder to `PATH` once and
just type `mem`:

```powershell
mem search "which model for local ollama"
mem add --name foo --type feedback --description "..." --body -
```

Override the interpreter with `MEM_PYTHON` if the environment moves.

`index` is content-hash incremental: unchanged files are skipped, edited files are
re-embedded, deleted files are dropped from the collection. Safe to run repeatedly.

`search` prints, per hit: cosine similarity (higher = closer), memory name, type,
description, file, and a snippet.

**Reading the score** (empirical, `nomic-embed-text`): a memory that genuinely covers
the query lands around **0.75+**; scores clustering near **~0.5** mean nothing really
matches — treat that as *absence*, not a weak hit. Don't assert "it isn't recorded"
without running a search first, but a top hit below ~0.6 is a fair basis for saying so.

## Config (env overrides)

| var | default |
|-----|---------|
| `MEM_DIR` | the project memory path |
| `MEM_OLLAMA_HOST` | `http://127.0.0.1:11434` |
| `MEM_EMBED_MODEL` | `nomic-embed-text` |

## Requirements

`chromadb`, `ollama` (python), `pyyaml`, and a running Ollama with `nomic-embed-text`
pulled (`ollama pull nomic-embed-text`). All present in the `py310` environment.
