"""Self-contained memory MCP server with in-process Chroma PersistentClient.

No external service dependencies. Embeds via Ollama nomic-embed-text on demand.
Replaces: mem-chroma service + mem_mcp.py subprocess wrapper.

Usage in mcp.json:
  "memory-index": {
    "command": "c:/users/user/py310/Scripts/python.exe",
    "args": ["c:/users/user/.claude/skills/.skills/memory-index/mem_server.py"]
  }
"""
from __future__ import annotations

import hashlib
import os
import re
import sys
import time
from collections import Counter
from pathlib import Path

import yaml
from fastmcp import FastMCP

# --- config -----------------------------------------------------------------

MEM_DIR = Path(os.environ.get("MEM_DIR", os.path.expanduser("~/memory-bank")))
OLLAMA_HOST = os.environ.get("MEM_OLLAMA_HOST", "http://127.0.0.1:11434")
EMBED_MODEL = os.environ.get("MEM_EMBED_MODEL", "nomic-embed-text")
COLLECTION = "memories"
INDEX_FILE = "MEMORY.md"
ALLOWED_TYPES = {"user", "feedback", "project", "reference", "pattern", "decision"}
PROMOTE_AT = 3
HIT_MIN_SCORE = 0.6
MAX_WHOLE_CHARS = 6000
CHUNK_TARGET_CHARS = 4000

# --- FastMCP ----------------------------------------------------------------

mcp = FastMCP(
    "memory-index",
    instructions=(
        "Semantic memory over the memory-bank markdown store + annealing Chroma log. "
        "Use search_memory to recall relevant context, log_memory to jot ephemeral bits "
        "that may promote to durable markdown after repeated recall, and add_memory for "
        "durable entries. The store is at ~/memory-bank/."
    ),
)


# --- Health endpoint for liveness probes ------------------------------------

@mcp.custom_route("/health", methods=["GET"])
async def health(_):
    from starlette.responses import JSONResponse
    col = get_collection()
    return JSONResponse({"status": "ok", "collection": COLLECTION, "count": col.count(),
                         "store": str(MEM_DIR / ".chroma"), "embed_model": EMBED_MODEL})

# --- Chroma (in-process PersistentClient) -----------------------------------

_col = None


def get_collection():
    global _col
    if _col is None:
        import chromadb
        from chromadb.config import Settings

        store = MEM_DIR / ".chroma"
        store.mkdir(parents=True, exist_ok=True)
        client = chromadb.PersistentClient(
            path=str(store), settings=Settings(anonymized_telemetry=False)
        )
        _col = client.get_or_create_collection(
            name=COLLECTION, metadata={"hnsw:space": "cosine"}
        )
    return _col


# --- Embedding (Ollama) -----------------------------------------------------


def embed(texts: list[str], is_query: bool) -> list[list[float]]:
    from ollama import Client

    prefix = "search_query: " if is_query else "search_document: "
    c = Client(host=OLLAMA_HOST)
    return [c.embeddings(model=EMBED_MODEL, prompt=prefix + t)["embedding"] for t in texts]


# --- Helpers ported from mem.py ---------------------------------------------


def parse_memory(path: Path) -> dict:
    raw = path.read_text(encoding="utf-8")
    fm, body = {}, raw
    if raw.startswith("---"):
        parts = raw.split("---", 2)
        if len(parts) == 3:
            try:
                fm = yaml.safe_load(parts[1]) or {}
            except yaml.YAMLError:
                fm = {}
            body = parts[2].lstrip("\n")
    meta = fm.get("metadata") or {}
    return {
        "stem": path.stem,
        "name": str(fm.get("name") or path.stem),
        "description": str(fm.get("description") or "").strip().strip('"'),
        "type": str(meta.get("type") or "unknown"),
        "body": body.strip(),
        "raw": raw,
    }


def content_hash(raw: str) -> str:
    return hashlib.sha256(raw.encode("utf-8")).hexdigest()


def doc_text(mem: dict) -> str:
    return f"{mem['description']}\n\n{mem['body']}".strip()


def chunk_markdown(text: str, target: int = CHUNK_TARGET_CHARS) -> list[tuple[str, str]]:
    blocks, cur = [], []
    for ln in text.split("\n"):
        if ln.strip() == "":
            if cur:
                blocks.append("\n".join(cur))
                cur = []
        else:
            cur.append(ln)
    if cur:
        blocks.append("\n".join(cur))

    chunks: list[tuple[str, str]] = []
    buf: list[str] = []
    buflen = 0
    heading = ""

    def flush():
        nonlocal buf, buflen
        joined = "\n\n".join(buf).strip()
        if joined:
            chunks.append((joined, heading))
        buf, buflen = [], 0

    for b in blocks:
        first = b.splitlines()[0].strip() if b.splitlines() else ""
        if first.startswith("#"):
            heading = first.lstrip("#").strip()
        if len(b) > target * 1.5:
            flush()
            for i in range(0, len(b), target):
                piece = b[i : i + target].strip()
                if piece:
                    chunks.append((piece, heading))
            continue
        if buf and buflen + len(b) > target:
            flush()
        buf.append(b)
        buflen += len(b) + 2
    flush()
    return chunks


def memory_files(mem_dir: Path) -> list[Path]:
    return sorted(p for p in mem_dir.glob("*.md") if p.name != INDEX_FILE)


def slugify(text: str, maxlen: int = 48) -> str:
    s = re.sub(r"[^a-z0-9]+", "-", text.strip().lower()).strip("-")
    return s[:maxlen].rstrip("-") or "bit"


def _units_for(mem: dict, sha: str) -> list[tuple[str, str, str, dict]]:
    base = {
        "kind": "doc",
        "name": mem["name"],
        "type": mem["type"],
        "description": mem["description"],
        "file": f"{mem['stem']}.md",
        "sha": sha,
    }
    whole = doc_text(mem)
    if len(whole) <= MAX_WHOLE_CHARS:
        return [(mem["stem"], whole, whole, {**base, "chunk": -1, "heading": ""})]
    units = []
    for i, (ctext, heading) in enumerate(chunk_markdown(mem["body"])):
        etext = f"{mem['description']} [{heading}]\n{ctext}".strip()
        units.append(
            (f"{mem['stem']}#{i}", etext, ctext, {**base, "chunk": i, "heading": heading})
        )
    return units


def write_memory_file(
    target_dir: Path, name: str, mtype: str, description: str, body: str,
    unique: bool = False, extra_meta: dict | None = None, note: str | None = None,
) -> Path:
    target_dir.mkdir(parents=True, exist_ok=True)
    slug = slugify(name)
    path = target_dir / f"{slug}.md"
    if path.exists():
        if not unique:
            raise ValueError(f"{path.name} already exists")
        slug = f"{slug}-{content_hash(body)[:6]}"
        path = target_dir / f"{slug}.md"

    fm = {
        "name": slug,
        "description": description.strip(),
        "metadata": {"node_type": "memory", "type": mtype, **(extra_meta or {})},
    }
    front = yaml.safe_dump(fm, sort_keys=False, allow_unicode=True, width=10**9).strip()
    body_out = body.strip()
    if note:
        body_out += f"\n\n> _{note}_"
    path.write_text(f"---\n{front}\n---\n\n{body_out}\n", encoding="utf-8")

    index_path = target_dir / INDEX_FILE
    pointer = f"- [{slug.replace('-', ' ').capitalize()}]({slug}.md) — {description.strip()}\n"
    if index_path.exists():
        cur = index_path.read_text(encoding="utf-8")
        if f"]({slug}.md)" not in cur:
            if not cur.endswith("\n"):
                cur += "\n"
            index_path.write_text(cur + pointer, encoding="utf-8")
    else:
        index_path.write_text(f"# Memory Index\n\n{pointer}", encoding="utf-8")
    return path


def promote(col, log_id: str, meta: dict, body: str) -> str:
    scope = meta.get("scope", "global")
    repo = meta.get("repo", "")
    mtype = meta.get("type", "reference")
    if mtype not in ALLOWED_TYPES:
        mtype = "reference"
    name = meta.get("name") or slugify(body)
    desc = meta.get("description") or " ".join(body.split())[:100]

    if scope == "local" and repo:
        target = MEM_DIR / "projects" / Path(repo).name
    else:
        target = MEM_DIR

    recalls = int(meta.get("hits", PROMOTE_AT))
    date = time.strftime("%Y-%m-%d")
    note = (
        f"Auto-promoted from the Chroma log after {recalls} recalls ({date}). "
        f"Curator: keep, refine, or delete."
    )
    path = write_memory_file(
        target, name, mtype, desc, body, unique=True,
        extra_meta={"promoted_from": "chroma-log", "recalls": recalls, "promoted": date},
        note=note,
    )
    col.delete(ids=[log_id])
    return f"Promoted to {path}"


# --- MCP Tools --------------------------------------------------------------


@mcp.tool()
def search_memory(query: str, k: int = 5, type: str | None = None) -> str:
    """Search the memory store by semantic similarity.

    query: natural language search query
    k: max results to return (default 5)
    type: optional filter by entry type (e.g. 'feedback', 'reference', 'pattern')
    Returns ranked memory entries with relevance scores.
    """
    col = get_collection()
    if col.count() == 0:
        return "Index is empty — call index_memory() first."
    qv = embed([query], is_query=True)[0]
    where = {"type": type} if type else None
    res = col.query(query_embeddings=[qv], n_results=min(k, col.count()), where=where)
    ids = res["ids"][0]
    if not ids:
        return "(no matches)"

    metas, dists, docs = res["metadatas"][0], res["distances"][0], res["documents"][0]
    lines = []
    promotions = []

    for rank, (mid, meta, dist, doc) in enumerate(zip(ids, metas, dists, docs), 1):
        meta = meta or {}
        score = 1.0 - float(dist)
        is_log = meta.get("kind") == "log"
        counts = is_log and score >= HIT_MIN_SCORE
        hits = int(meta.get("hits", 0)) + (1 if counts else 0)
        snippet = " ".join(doc.split())[:160]

        label = "log" if is_log else meta.get("type", "?")
        line = f"[{rank}] {score:.3f}  {meta.get('name', mid)}  ({label})"
        if is_log:
            line += f"  {hits}/{PROMOTE_AT} hits"
        lines.append(line)
        if meta.get("description"):
            lines.append(f"     {meta['description']}")
        lines.append(f"     {snippet}")

        if counts:
            nm = {**meta, "hits": hits, "last_hit": time.time()}
            if hits >= PROMOTE_AT:
                promotions.append((mid, nm, doc))
            else:
                col.update(ids=[mid], metadatas=[nm])

    for mid, meta, doc in promotions:
        msg = promote(col, mid, meta, doc)
        lines.append(f"  >> {msg}")

    return "\n".join(lines)


@mcp.tool()
def log_memory(
    content: str, scope: str = "global", repo: str | None = None, type: str = "reference"
) -> str:
    """Log an ephemeral worked-out bit to the annealing Chroma store.

    Cheap to write. Bits recalled >= 3 times auto-promote to durable markdown.
    Under-recalled bits anneal away over time.

    content: the thing you learned/worked out
    scope: 'global' or 'local' (local requires repo path)
    repo: repo path for local-scope entries
    type: entry type tag (default 'reference')
    """
    content = content.strip()
    if not content:
        return "Error: empty content"
    if type not in ALLOWED_TYPES:
        return f"Error: type must be one of {sorted(ALLOWED_TYPES)}"
    if scope == "local" and not repo:
        return "Error: scope=local requires repo path"

    name = slugify(content)
    description = " ".join(content.split())[:100]
    log_id = f"log:{name}-{content_hash(content)[:6]}"

    col = get_collection()
    vec = embed([f"{description}\n\n{content}".strip()], is_query=False)[0]
    col.upsert(
        ids=[log_id],
        embeddings=[vec],
        documents=[content],
        metadatas=[
            {
                "kind": "log",
                "name": name,
                "type": type,
                "description": description,
                "scope": scope,
                "repo": repo or "",
                "hits": 0,
                "created": time.time(),
                "last_hit": 0.0,
            }
        ],
    )
    return f"Logged {log_id} (scope={scope}, promotes at {PROMOTE_AT} recalls)"


@mcp.tool()
def add_memory(name: str, type: str, description: str, body: str) -> str:
    """Add a durable memory entry (markdown + vector index).

    Creates a markdown file and indexes it in Chroma.

    name: slug for the entry (becomes filename)
    type: category (e.g. 'feedback', 'reference', 'pattern', 'decision')
    description: one-line summary
    body: full content (use '-' to read from the description)
    """
    if type not in ALLOWED_TYPES:
        return f"Error: type must be one of {sorted(ALLOWED_TYPES)}"
    if body == "-":
        body = description

    try:
        path = write_memory_file(MEM_DIR, name.strip(), type, description, body)
    except ValueError as e:
        return f"Error: {e}"

    # Index the new file
    mem = parse_memory(path)
    sha = content_hash(mem["raw"])
    units = _units_for(mem, sha)
    vecs = embed([u[1] for u in units], is_query=False)
    col = get_collection()
    col.upsert(
        ids=[u[0] for u in units],
        embeddings=vecs,
        documents=[u[2] for u in units],
        metadatas=[u[3] for u in units],
    )
    return f"Wrote {path} and indexed ({len(units)} vectors)"


@mcp.tool()
def index_memory() -> str:
    """Reconcile the Chroma vector index with the markdown files on disk.

    Run after editing memory-bank markdown files directly to keep the
    vector index in sync.
    """
    col = get_collection()
    existing = col.get()
    by_stem: dict[str, list[str]] = {}
    sha_of: dict[str, str] = {}
    for i, m in zip(existing["ids"], existing["metadatas"]):
        if (m or {}).get("kind") == "log":
            continue
        stem = i.split("#", 1)[0]
        by_stem.setdefault(stem, []).append(i)
        sha_of[stem] = (m or {}).get("sha")

    files = memory_files(MEM_DIR)
    seen: set[str] = set()
    changed: list[tuple[dict, str]] = []
    for p in files:
        mem = parse_memory(p)
        seen.add(mem["stem"])
        sha = content_hash(mem["raw"])
        if sha_of.get(mem["stem"]) == sha:
            continue
        changed.append((mem, sha))

    delete_ids = [i for stem, ids in by_stem.items() if stem not in seen for i in ids]
    for mem, _ in changed:
        delete_ids.extend(by_stem.get(mem["stem"], []))
    if delete_ids:
        col.delete(ids=delete_ids)

    chunks_added = 0
    if changed:
        units = [u for mem, sha in changed for u in _units_for(mem, sha)]
        vecs = embed([u[1] for u in units], is_query=False)
        col.upsert(
            ids=[u[0] for u in units],
            embeddings=vecs,
            documents=[u[2] for u in units],
            metadatas=[u[3] for u in units],
        )
        chunks_added = len(units)

    removed = len([s for s in by_stem if s not in seen])
    return (
        f"Indexed {len(files)} files: {len(changed)} changed ({chunks_added} vectors), "
        f"{len(files) - len(changed)} unchanged, {removed} removed"
    )


@mcp.tool()
def memory_stats() -> str:
    """Show memory store statistics: entry counts, types, promotion candidates."""
    col = get_collection()
    data = col.get()
    docs = [(i, m or {}) for i, m in zip(data["ids"], data["metadatas"]) if (m or {}).get("kind") != "log"]
    logs = [(i, m or {}) for i, m in zip(data["ids"], data["metadatas"]) if (m or {}).get("kind") == "log"]
    doc_stems = {i.split("#", 1)[0] for i, _ in docs}
    by_type = Counter(m.get("type", "?") for _, m in docs)

    lines = [
        f"Collection: {COLLECTION}",
        f"Docs: {len(doc_stems)} files ({len(docs)} vectors) + {len(logs)} log bits",
        f"Store: {MEM_DIR / '.chroma'}",
        f"Embedder: {EMBED_MODEL} @ {OLLAMA_HOST}",
        "Types:",
    ]
    for t, n in sorted(by_type.items()):
        lines.append(f"  {t:12s} {n}")
    if logs:
        hot = sorted(logs, key=lambda x: int(x[1].get("hits", 0)), reverse=True)[:5]
        lines.append(f"Log: {len(logs)} bits (promote at {PROMOTE_AT} recalls)")
        for i, m in hot:
            lines.append(f"  {int(m.get('hits', 0))}/{PROMOTE_AT}  {(m.get('description') or i)[:56]}")

    n_files = len(memory_files(MEM_DIR))
    if n_files != len(doc_stems):
        lines.append(f"  ! {n_files} files on disk vs {len(doc_stems)} indexed — run index_memory()")
    return "\n".join(lines)


if __name__ == "__main__":
    import argparse

    parser = argparse.ArgumentParser(description="Memory MCP server")
    parser.add_argument("--port", type=int, default=8055,
                        help="HTTP port (default: 8055)")
    parser.add_argument("--stdio", action="store_true",
                        help="Run in stdio mode instead of HTTP")
    args = parser.parse_args()

    if args.stdio:
        mcp.run(transport="stdio")
    else:
        mcp.run(transport="streamable-http", host="127.0.0.1", port=args.port)
