---
name: auto-ingest
description: >
  On-demand and background PDF enrichment pipeline for the arxiv_rag corpus.
  Use when a retrieval session needs full extracted methods for top papers,
  when checking whether papers have been enriched, or when queuing papers for
  background VLM + methods processing. Owns ingest_daemon.py, ingest_mcp.py,
  and the enrichment state in checkpoints/ingest_service.db.
status: active
last_validated: 2026-05-02
---

# Auto-Ingest Skill

## Scope Boundary

This skill owns **Phase 3-5 enrichment** of the arxiv_rag PDF pipeline.

It owns:
- Background ingestion daemon (`ingest_daemon.py`)
- MCP server for queue inspection and retrieval augmentation (`ingest_mcp.py`)
- SQLite checkpoint state (`checkpoints/ingest_service.db`)
- On-demand eager extraction wired into `arxiv_pipeline/run.py --extract`

It does **not** own:
- Phase 1 (docling PDF → MD) — run separately before the pipeline
- Phase 2 (base64 → CSV, `post_process_md-csv.py`) — run before daemon
- The retrieval ranking pipeline (`arxiv_retriever.py`, `arxiv_pipeline/`)
- The pgvector ingest pipeline (`ingest_master.py`, `ingest_daemon.py`)

The MCP server is read-only + queue-only. It never runs VLM calls inline
(those are too slow for a synchronous MCP response). The daemon does the work.

---

## Pipeline Concept

Five phases turn a raw PDF into an enriched Markdown with pseudocode:

| Phase | Script | Input → Output | Typical time |
|-------|--------|----------------|-------------|
| 1 | `docling` (external) | `.pdf` → `.md` (with base64 images) | 30-60 s |
| 2 | `post_process_md-csv.py` | `.md` → `.md` (tokens) + `.csv` (base64) | 2-5 s |
| 0† | (daemon inline) | `.md` old tags → `.md` new tags | <1 s |
| 3 | `vlm_describe.py` | `.csv` → `.csv` + `description` column | 1-5 min |
| 4 | `reinsert_descriptions.py` | `.md` + `.csv` → `.md` (descriptions embedded) | 2-5 s |
| 5 | `extract_methods.py` | `.md` → `_methods.md` | 20-60 s |

†Phase 0 is an internal normalisation step the daemon applies to legacy
files that used the old `<image N>` (space) tag format instead of the
current `<image_N>` (underscore) format.

**Completion signal**: `papers/post_processed/<stem>_methods.md` exists.
If this file is absent the paper has not completed the new pipeline.

---

## Paths (load-bearing)

```
Repo root  : C:\Users\user\arxiv_id_lists\
Post-proc  : C:\Users\user\arxiv_id_lists\papers\post_processed\
Daemon     : C:\Users\user\arxiv_id_lists\ingest_daemon.py
MCP server : C:\Users\user\arxiv_id_lists\ingest_mcp.py
DB         : C:\Users\user\arxiv_id_lists\checkpoints\ingest_service.db
Main CSV   : C:\Users\user\arxiv_id_lists\papers\post_processed\arxiv_data_with_analysis_cleaned.csv
Python     : C:\Users\user\py310\Scripts\python.exe
```

---

## Setup Mode

Invoke setup when this skill is first installed or after the repo moves.

### Setup actions

1. Confirm `ingest_daemon.py` and `ingest_mcp.py` exist in the repo root
2. Confirm `checkpoints/` directory exists (daemon creates it on first run)
3. Register `auto-ingest` MCP server in `C:\Users\user\.copilot\mcp-config.json`
4. Add the startup line to `C:\Users\user\start_mcp.ps1`
5. Confirm `fastmcp` is importable; install if missing:
   `C:\Users\user\py310\Scripts\python.exe -m pip install fastmcp`

### MCP registration snippet

Add to `C:\Users\user\.copilot\mcp-config.json` under `"mcpServers"`:

```json
"auto-ingest": {
  "type": "local",
  "command": "C:\\Users\\user\\py310\\Scripts\\python.exe",
  "args": ["C:\\Users\\user\\arxiv_id_lists\\ingest_mcp.py"]
}
```

### Starting the background daemon

The daemon is a **long-running process** separate from the MCP server.
Start it in a detached PowerShell window or as a scheduled task:

```powershell
# Run in background, process one batch every 60 seconds
Start-Process powershell -ArgumentList `
  "-NoExit -Command `"cd C:\Users\user\arxiv_id_lists; C:\Users\user\py310\Scripts\python.exe ingest_daemon.py --poll 60`"" `
  -WindowStyle Minimized

# Or: single batch of up to 10 papers and exit
C:\Users\user\py310\Scripts\python.exe ingest_daemon.py --once --limit 10

# Check queue without processing anything
C:\Users\user\py310\Scripts\python.exe ingest_daemon.py --status
```

### start_mcp.ps1 addition

After starting memory-bank (9001) and todo (9002), add port 9005:

```powershell
# Auto-ingest MCP server (HTTP mode for Codex / external agents)
$ingestPid = (Get-NetTCPConnection -LocalPort 9005 -ErrorAction SilentlyContinue).OwningProcess
if (-not $ingestPid) {
    Start-Process python -ArgumentList `
        "C:\Users\user\arxiv_id_lists\ingest_mcp.py --port 9005" `
        -WindowStyle Hidden
    Write-Host "auto-ingest MCP started on :9005"
}
```

---

## MCP Server Scaffold

`C:\Users\user\arxiv_id_lists\ingest_mcp.py` — synthesize from this if missing.

```python
#!/usr/bin/env python3
"""
Auto-Ingest MCP server for arxiv_rag.

Exposes queue inspection and methods retrieval tools so agentic sessions
can check enrichment state and read extracted methods without needing
direct filesystem access.

Preconditions:
    - checkpoints/ingest_service.db exists (created by ingest_daemon.py)
    - papers/post_processed/ is accessible at REPO_ROOT
    - fastmcp installed in active Python environment
Postconditions:
    - Tools available via stdio (Copilot CLI) or HTTP :PORT/mcp (Codex)
Failure modes:
    - Missing DB: tools return 'daemon not yet started' message
    - Missing _methods.md: get_methods returns None; check_papers shows state
"""

import argparse
import csv as csv_module
import sqlite3
import sys
from pathlib import Path

if hasattr(sys.stdout, "reconfigure"):
    sys.stdout.reconfigure(encoding="utf-8", errors="replace")

from fastmcp import FastMCP

REPO_ROOT = Path(r"C:\Users\user\arxiv_id_lists")
POST_PROCESSED = REPO_ROOT / "papers" / "post_processed"
DB_PATH = REPO_ROOT / "checkpoints" / "ingest_service.db"

mcp = FastMCP("auto-ingest")


def _open_db(repo_root: str | None = None) -> sqlite3.Connection | None:
    """Open ingest DB, return None if not yet initialised."""
    db = Path(repo_root) / "checkpoints" / "ingest_service.db" if repo_root else DB_PATH
    if not db.is_file():
        return None
    conn = sqlite3.connect(str(db), timeout=10)
    conn.row_factory = sqlite3.Row
    return conn


def _norm(paper_id: str) -> str:
    """Normalise paper_id: '1806.07366' → '1806_07366'."""
    return paper_id.strip().replace(".", "_")


def _methods_path(paper_id: str, repo_root: str | None = None) -> Path:
    base = Path(repo_root) / "papers" / "post_processed" if repo_root else POST_PROCESSED
    stem = _norm(paper_id)
    return base / f"{stem}_methods.md"


@mcp.tool()
def ingest_status(repo_root: str | None = None) -> str:
    """
    Return a summary of the ingestion queue from the daemon checkpoint DB.

    Args:
        repo_root: Absolute path to the arxiv_rag repo root.
                   Defaults to C:\\Users\\user\\arxiv_id_lists.
    Returns:
        Human-readable counts by state (pending, done, error, running).
    """
    conn = _open_db(repo_root)
    if conn is None:
        return "Daemon checkpoint DB not found. Run ingest_daemon.py --status first."
    try:
        rows = conn.execute(
            "SELECT state, COUNT(*) AS n FROM papers GROUP BY state ORDER BY state"
        ).fetchall()
        total = sum(r["n"] for r in rows)
        lines = [f"Ingest queue ({total} total):"]
        for r in rows:
            lines.append(f"  {r['state']:12s} {r['n']}")
        return "\n".join(lines)
    finally:
        conn.close()


@mcp.tool()
def check_papers(paper_ids: list[str], repo_root: str | None = None) -> str:
    """
    Check enrichment state for a list of paper IDs.

    Args:
        paper_ids: List of arXiv IDs in any format ('1806.07366' or '1806_07366').
        repo_root: Absolute path to the arxiv_rag repo root.
    Returns:
        JSON-like mapping of paper_id → state ('done', 'pending', 'error', 'unknown').
        'done' means _methods.md exists. 'unknown' means not yet registered with daemon.
    """
    conn = _open_db(repo_root)
    results: dict[str, str] = {}

    for pid in paper_ids:
        stem = _norm(pid)
        mp = _methods_path(pid, repo_root)
        if mp.is_file():
            results[pid] = "done"
            continue
        if conn is not None:
            row = conn.execute(
                "SELECT state FROM papers WHERE paper_id = ?", (stem,)
            ).fetchone()
            results[pid] = row["state"] if row else "unknown"
        else:
            results[pid] = "unknown"

    if conn:
        conn.close()

    lines = [f"Paper enrichment states ({len(paper_ids)} checked):"]
    for pid, state in results.items():
        lines.append(f"  {pid:20s} {state}")
    return "\n".join(lines)


@mcp.tool()
def get_methods(paper_id: str, repo_root: str | None = None) -> str:
    """
    Read and return the extracted _methods.md content for a paper.

    Args:
        paper_id: arXiv ID ('1806.07366' or '1806_07366').
        repo_root: Absolute path to the arxiv_rag repo root.
    Returns:
        Full _methods.md content, or an error message if not yet extracted.
    """
    mp = _methods_path(paper_id, repo_root)
    if not mp.is_file():
        return (
            f"No _methods.md for {paper_id}. "
            "Paper has not completed the enrichment pipeline. "
            "Run ingest_daemon.py or use queue_papers() to schedule it."
        )
    return mp.read_text(encoding="utf-8")


@mcp.tool()
def queue_papers(
    paper_ids: list[str],
    priority: float = 1.0,
    repo_root: str | None = None,
) -> str:
    """
    Add papers to the ingestion queue for the background daemon to process.

    Papers with _methods.md already present are silently skipped.
    Papers already in the DB retain their existing state.

    Args:
        paper_ids: List of arXiv IDs to queue.
        priority:  Priority weight (higher = processed sooner). Default 1.0.
        repo_root: Absolute path to the arxiv_rag repo root.
    Returns:
        Summary of how many were queued, skipped (done), or could not be found.
    """
    base = Path(repo_root) / "papers" / "post_processed" if repo_root else POST_PROCESSED
    conn = _open_db(repo_root)
    if conn is None:
        return (
            "Daemon checkpoint DB not found. "
            "Run `python ingest_daemon.py --status` once to initialise it."
        )

    queued = skipped_done = not_found = already_queued = 0
    from datetime import datetime

    for pid in paper_ids:
        stem = _norm(pid)
        mp = _methods_path(pid, repo_root)
        if mp.is_file():
            skipped_done += 1
            continue
        md = base / f"{stem}.md"
        csv_p = base / f"{stem}.csv"
        if not md.is_file() or not csv_p.is_file():
            not_found += 1
            continue
        existing = conn.execute(
            "SELECT state FROM papers WHERE paper_id = ?", (stem,)
        ).fetchone()
        if existing:
            # Bump priority but keep state
            conn.execute(
                "UPDATE papers SET priority = MAX(priority, ?), updated_at = ? "
                "WHERE paper_id = ?",
                (priority, datetime.utcnow().isoformat(), stem),
            )
            already_queued += 1
        else:
            conn.execute(
                "INSERT INTO papers "
                "(paper_id, md_path, csv_path, priority, state, updated_at) "
                "VALUES (?,?,?,?,'pending',?)",
                (
                    stem,
                    str(md),
                    str(csv_p),
                    priority,
                    datetime.utcnow().isoformat(),
                ),
            )
            queued += 1

    conn.commit()
    conn.close()
    return (
        f"Queue update: {queued} newly queued, {already_queued} already queued "
        f"(priority updated), {skipped_done} already done, {not_found} not found on disk."
    )


@mcp.tool()
def list_errors(limit: int = 10, repo_root: str | None = None) -> str:
    """
    List papers stuck in the error state with their last error message.

    Args:
        limit:     Max rows to return (default 10).
        repo_root: Absolute path to the arxiv_rag repo root.
    Returns:
        Table of paper_id and truncated error message.
    """
    conn = _open_db(repo_root)
    if conn is None:
        return "Daemon checkpoint DB not found."
    try:
        rows = conn.execute(
            "SELECT paper_id, error_msg, updated_at FROM papers "
            "WHERE state = 'error' ORDER BY updated_at DESC LIMIT ?",
            (limit,),
        ).fetchall()
        if not rows:
            return "No papers in error state."
        lines = [f"{'paper_id':<22} {'updated':<22} error"]
        lines.append("-" * 80)
        for r in rows:
            msg = (r["error_msg"] or "")[:60].replace("\n", " ")
            lines.append(f"{r['paper_id']:<22} {(r['updated_at'] or '')[:19]:<22} {msg}")
        return "\n".join(lines)
    finally:
        conn.close()


if __name__ == "__main__":
    parser = argparse.ArgumentParser()
    parser.add_argument("--port", type=int, default=None, help="HTTP port (omit for stdio)")
    args = parser.parse_args()

    if args.port:
        mcp.run(transport="streamable-http", host="0.0.0.0", port=args.port, path="/mcp")
    else:
        mcp.run()
```

---

## Tool Reference

| Tool | When to call | Returns |
|------|-------------|---------|
| `ingest_status(repo_root)` | Session start — surface background progress | Text summary of queue counts |
| `check_papers(paper_ids, repo_root)` | After retrieval — verify which top papers are enriched | Per-paper state map |
| `get_methods(paper_id, repo_root)` | When injecting methods into a synthesis | Full `_methods.md` text |
| `queue_papers(paper_ids, priority, repo_root)` | After retrieval — schedule unenriched papers | Queue result summary |
| `list_errors(limit, repo_root)` | Debugging — find stuck papers | Error table |

---

## Agentic Session Integration

### Standard retrieval + enrichment flow

After retrieving top-K papers (e.g. via `arxiv_pipeline/run.py`):

```
1. call check_papers(top_k_ids)
2. for each paper where state == 'done':
       call get_methods(paper_id) → inject into synthesis
3. for each paper where state != 'done':
       call queue_papers([paper_id], priority=2.0)
       note in synthesis: "methods pending enrichment"
```

### On-demand eager extraction (retrieval with --extract flag)

`arxiv_pipeline/run.py --extract` runs the enrichment pipeline **synchronously**
for the top 3 papers before assembling the report. It calls `ingest_daemon.py`
as a subprocess via `_run_on_demand_extraction()` in `arxiv_pipeline/run.py`.
This path bypasses the MCP server and is appropriate when the user is waiting
for a complete report (expected latency: 5-18 min for 1-3 papers).

Use the MCP server for:
- Non-blocking queue inspection
- Background work visibility across sessions
- Reading pre-computed methods content

Use `--extract` for:
- Synchronous on-demand enrichment within a single retrieval session
- When the user explicitly asks for "full paper" quality results

### `repo_root` parameter

Always pass:
```
repo_root = "C:\\Users\\user\\arxiv_id_lists"
```
The default is hardcoded to the same value, but explicit is safer if the
working directory changes.

---

## Operating Rules

1. **Check before queuing**: call `check_papers` before `queue_papers`. No point
   queuing papers that already have `_methods.md`.

2. **Daemon must be running for queued work to execute**. The MCP server only
   manages the queue. Start the daemon separately:
   ```
   python ingest_daemon.py --poll 60
   ```

3. **Error reset**: papers in `error` state will not be retried automatically.
   To reset an errored paper, update its state in the DB directly:
   ```python
   conn.execute("UPDATE papers SET state='pending', error_msg=NULL WHERE paper_id=?", (stem,))
   ```
   Or delete the row and let the daemon re-register it on the next scan.

4. **Priority scale**: utility scores from the main CSV are typically 0–5.
   Use `priority=10.0` when queuing papers you want processed next.

5. **Stale running state**: if the daemon was killed mid-paper, that paper
   may be stuck in `state='running'`. `ingest_daemon.py --status` will show
   this. The daemon resets `running` → `pending` on its next scan.

---

## Known Constraints

- Phase 3 (VLM) requires Ollama at `192.168.3.17:11434` with `qwen3-vl:2b` loaded.
  If Ollama is down, Phase 3 errors and the paper remains in the error state.
- Phase 5 (methods) requires copilot-proxy at `localhost:8069`.
  If the proxy is down, Phase 5 errors.
- The 1606 papers in `post_processed/` as of 2026-05-02 all use the old
  `<image N>` (space) tag format. Phase 0 normalisation handles these.
  New papers produced by the current `run_pipeline.bat` use `<image_N>` and
  skip Phase 0 automatically.
- VLM throughput: ~1-5 min per paper depending on image count.
  Full backlog (~1600 papers) takes 80-160 hours of continuous daemon runtime.
<!-- consolidation:see-also:start -->
## See Also
[[pdf-extraction]]
<!-- consolidation:see-also:end -->
