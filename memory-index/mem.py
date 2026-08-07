#!/usr/bin/env python3
"""
mem.py — embed-and-retrieve layer over the markdown memory store.

The markdown files under the memory directory remain the source of truth.
This tool maintains a Chroma vector index over them so memories can be recalled
by semantic similarity instead of grep. It also writes new memories (markdown +
MEMORY.md pointer) and indexes them in one step.

Embeddings: local Ollama `nomic-embed-text` (768-dim), no API, no GPU training
contention. See agentic_kg_memory/SKILL.md for the design this implements.

Two classes of entry share the collection:
  - docs  — durable markdown (global ~\memory-bank\*.md), indexed for recall; never anneal.
  - log   — ephemeral "worked-out bits" written cheaply via `mem log`. Each recall bumps a
            hit counter; at PROMOTE_AT hits the bit is promoted to durable markdown (global,
            or a repo's local .memory-bank); `mem anneal` evicts stale, under-recalled bits.

Usage:
    python mem.py index                       # reconcile doc index with markdown files
    python mem.py search "query" [-k 5] [--type feedback]   # recall (bumps log hit counts)
    python mem.py add  --name slug --type feedback --description "one line" --body -
    python mem.py log  "a worked-out bit" [--scope global|local --repo PATH --type reference]
    python mem.py anneal [--ttl-days 30] [--dry-run]        # evict stale under-recalled bits
    python mem.py stats

Env overrides:
    MEM_DIR           memory directory (default: the project memory path below)
    MEM_OLLAMA_HOST   ollama base url (default: http://127.0.0.1:11434)
    MEM_EMBED_MODEL   embedding model (default: nomic-embed-text)
"""
from __future__ import annotations

import argparse
import hashlib
import os
import re
import sys
import time
from pathlib import Path

import yaml

# --- config -----------------------------------------------------------------

DEFAULT_MEM_DIR = Path(
    os.environ.get(
        "MEM_DIR",
        r"C:\Users\user\.claude\projects\C--Users-user-Documents-dev-skills\memory",
    )
)
OLLAMA_HOST = os.environ.get("MEM_OLLAMA_HOST", "http://127.0.0.1:11434")
EMBED_MODEL = os.environ.get("MEM_EMBED_MODEL", "nomic-embed-text")
CHROMA_HOST = os.environ.get("MEM_CHROMA_HOST", "127.0.0.1")
CHROMA_PORT = int(os.environ.get("MEM_CHROMA_PORT", "8055"))
COLLECTION = "memories"
INDEX_FILE = "MEMORY.md"          # skipped during indexing (it is the index, not a memory)
ALLOWED_TYPES = {"user", "feedback", "project", "reference"}

# annealing-log lifecycle
PROMOTE_AT = 3            # a log bit recalled this many times promotes to durable markdown
HIT_MIN_SCORE = 0.6      # a recall only counts if similarity is at least this
ANNEAL_TTL_DAYS = 30     # under-recalled log bits older than this are eligible to anneal


# --- embedding --------------------------------------------------------------

def _client():
    from ollama import Client
    return Client(host=OLLAMA_HOST)


def embed(texts: list[str], *, is_query: bool) -> list[list[float]]:
    """Embed a list of strings with the nomic task prefix. Returns one vector each."""
    prefix = "search_query: " if is_query else "search_document: "
    c = _client()
    out = []
    for t in texts:
        r = c.embeddings(model=EMBED_MODEL, prompt=prefix + t)
        out.append(r["embedding"])
    return out


# --- markdown parsing -------------------------------------------------------

def parse_memory(path: Path) -> dict:
    """Parse a memory markdown file into {name, description, type, body, raw}."""
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
    """Text that gets embedded: description (recall hook) + body."""
    return f"{mem['description']}\n\n{mem['body']}".strip()


# --- chunking ---------------------------------------------------------------
# The embedder (nomic-embed-text) truncates at ~2K tokens (~8K chars). Small atomic
# memories embed whole; large living docs (Memory Bank AGENTS.md, progress.md, …) are
# split into header-aware chunks so their tails stay searchable. Each chunk is its own
# vector, id'd `<stem>#<n>`, and drills back to the source file + heading.

MAX_WHOLE_CHARS = 6000       # files at/under this embed as a single vector
CHUNK_TARGET_CHARS = 4000    # ~1K tokens: comfortably under the embedder's window


def chunk_markdown(text: str, target: int = CHUNK_TARGET_CHARS) -> list[tuple[str, str]]:
    """Split markdown into (chunk_text, heading) pairs, packing paragraphs to ~target.

    Groups blank-line-separated blocks, starting a new chunk when the target is hit.
    Tracks the most recent markdown header as the chunk's heading. A single oversized
    block is hard-split so no chunk blows past the embedder window.
    """
    blocks, cur = [], []
    for ln in text.split("\n"):
        if ln.strip() == "":
            if cur:
                blocks.append("\n".join(cur)); cur = []
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
        if len(b) > target * 1.5:          # oversized single block -> hard split
            flush()
            for i in range(0, len(b), target):
                piece = b[i:i + target].strip()
                if piece:
                    chunks.append((piece, heading))
            continue
        if buf and buflen + len(b) > target:
            flush()
        buf.append(b)
        buflen += len(b) + 2
    flush()
    return chunks


# --- chroma -----------------------------------------------------------------

# records which backend the last get_collection() call used, for `stats` to report.
_BACKEND = "?"


def get_collection(mem_dir: Path):
    """Prefer the always-on Chroma service; fall back to the local file store.

    The service (an NSSM-wrapped `chroma run`) OWNS the store, so many agents can
    query concurrently without SQLite lock contention. The PersistentClient fallback
    only fires when the service is unreachable — at which point nothing else holds the
    file, so opening it directly is safe.
    """
    global _BACKEND
    import chromadb
    from chromadb.config import Settings

    settings = Settings(anonymized_telemetry=False)

    # Probe the service with a plain HTTP call BEFORE constructing any chromadb client.
    # (Constructing an HttpClient against a dead port raises *and* poisons Chroma's
    # settings-keyed system cache, which then breaks the PersistentClient fallback.
    # A stdlib probe sidesteps both and only ever builds one client type per process.)
    if _service_alive():
        _BACKEND = f"service {CHROMA_HOST}:{CHROMA_PORT}"
        client = chromadb.HttpClient(host=CHROMA_HOST, port=CHROMA_PORT, settings=settings)
        return client.get_or_create_collection(
            name=COLLECTION, metadata={"hnsw:space": "cosine"}
        )

    chroma_dir = mem_dir / ".chroma"
    chroma_dir.mkdir(parents=True, exist_ok=True)
    client = chromadb.PersistentClient(path=str(chroma_dir), settings=settings)
    _BACKEND = f"local file {chroma_dir} (service down)"
    return client.get_or_create_collection(
        name=COLLECTION, metadata={"hnsw:space": "cosine"}
    )


def _service_alive() -> bool:
    """True if the Chroma service answers a heartbeat. Cheap stdlib probe, no deps."""
    import urllib.request
    url = f"http://{CHROMA_HOST}:{CHROMA_PORT}/api/v2/heartbeat"
    try:
        with urllib.request.urlopen(url, timeout=1.5) as r:
            return r.status == 200
    except Exception:
        return False


def memory_files(mem_dir: Path) -> list[Path]:
    return sorted(
        p for p in mem_dir.glob("*.md") if p.name != INDEX_FILE
    )


# --- commands ---------------------------------------------------------------

def _units_for(mem: dict, sha: str) -> list[tuple[str, str, str, dict]]:
    """Yield (id, embed_text, stored_doc, metadata) for one memory file.

    Small files -> one unit (id=stem). Large files -> one unit per chunk
    (id=stem#n), each embedded with the file's description + heading for context.
    """
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
        units.append((f"{mem['stem']}#{i}", etext, ctext,
                      {**base, "chunk": i, "heading": heading}))
    return units


def cmd_index(mem_dir: Path, verbose: bool = True) -> None:
    col = get_collection(mem_dir)
    existing = col.get()  # ids + metadatas
    # group existing DOC ids by file stem (id is either "stem" or "stem#n").
    # log entries are not files — they must never be reconciled/deleted here.
    by_stem: dict[str, list[str]] = {}
    sha_of: dict[str, str] = {}
    for i, m in zip(existing["ids"], existing["metadatas"]):
        if (m or {}).get("kind") == "log":
            continue
        stem = i.split("#", 1)[0]
        by_stem.setdefault(stem, []).append(i)
        sha_of[stem] = (m or {}).get("sha")

    files = memory_files(mem_dir)
    seen, changed = set(), []
    for p in files:
        mem = parse_memory(p)
        seen.add(mem["stem"])
        sha = content_hash(mem["raw"])
        if sha_of.get(mem["stem"]) == sha:
            continue                       # unchanged
        changed.append((mem, sha))

    # delete: removed files + every prior id of a changed file (chunk count may differ)
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

    if verbose:
        removed = len([s for s in by_stem if s not in seen])
        print(f"indexed {len(files)} file(s): {len(changed)} changed "
              f"({chunks_added} vectors), {len(files) - len(changed)} unchanged, "
              f"{removed} removed")


def cmd_search(mem_dir: Path, query: str, k: int, type_filter: str | None,
               count_hits: bool = True) -> None:
    col = get_collection(mem_dir)
    if col.count() == 0:
        print("index is empty — run `python mem.py index` first", file=sys.stderr)
        return
    qv = embed([query], is_query=True)[0]
    where = {"type": type_filter} if type_filter else None
    res = col.query(query_embeddings=[qv], n_results=min(k, col.count()), where=where)
    ids = res["ids"][0]
    if not ids:
        print("(no matches)")
        return
    metas, dists, docs = res["metadatas"][0], res["distances"][0], res["documents"][0]

    bump_ids, bump_meta, promotions = [], [], []
    for rank, (mid, meta, dist, doc) in enumerate(zip(ids, metas, dists, docs), 1):
        meta = meta or {}
        score = 1.0 - float(dist)  # cosine distance -> similarity
        is_log = meta.get("kind") == "log"
        counts = count_hits and is_log and score >= HIT_MIN_SCORE
        hits = int(meta.get("hits", 0)) + (1 if counts else 0)
        snippet = " ".join(doc.split())[:160]

        label = "log" if is_log else meta.get("type", "?")
        head = f"\n[{rank}] {score:.3f}  {meta.get('name', mid)}  ({label})"
        if is_log:
            head += f"  ·{hits}/{PROMOTE_AT} hits"
        print(head)
        if meta.get("description"):
            print(f"     {meta['description']}")
        if is_log:
            print(f"     scope: {meta.get('scope', 'global')}")
        else:
            loc = meta.get("file", mid.split("#", 1)[0] + ".md")
            heading = meta.get("heading") or ""
            if int(meta.get("chunk", -1)) >= 0 and heading:
                loc += f"  › {heading}"   # which section of a chunked doc
            print(f"     file: {loc}")
        print(f"     … {snippet}")

        if counts:
            nm = {**meta, "hits": hits, "last_hit": time.time()}
            if hits >= PROMOTE_AT:
                promotions.append((mid, nm, doc))
            else:
                bump_ids.append(mid); bump_meta.append(nm)

    if bump_ids:
        col.update(ids=bump_ids, metadatas=bump_meta)
    for mid, meta, doc in promotions:
        promote(mem_dir, col, mid, meta, doc)


def slugify(text: str, maxlen: int = 48) -> str:
    s = re.sub(r"[^a-z0-9]+", "-", text.strip().lower()).strip("-")
    return s[:maxlen].rstrip("-") or "bit"


def write_memory_file(target_dir: Path, name: str, mtype: str, description: str,
                      body: str, title: str | None = None,
                      unique: bool = False, extra_meta: dict | None = None,
                      note: str | None = None) -> Path:
    """Write one markdown memory (frontmatter + body) and append its MEMORY.md pointer.

    Shared by `add` (fixed slug, fails on collision) and promotion (unique=True, appends a
    content hash on collision so an auto-promoted bit never clobbers an existing file).
    `extra_meta` merges into the frontmatter metadata; `note` is appended to the body as a
    blockquote — used to stamp promotion provenance the reading agent can act on.
    """
    target_dir.mkdir(parents=True, exist_ok=True)
    slug = slugify(name)
    path = target_dir / f"{slug}.md"
    if path.exists():
        if not unique:
            sys.exit(f"error: {path.name} already exists — edit it or choose another name")
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
    disp = title or slug.replace("_", " ").replace("-", " ").capitalize()
    pointer = f"- [{disp}]({slug}.md) — {description.strip()}\n"
    if index_path.exists():
        cur = index_path.read_text(encoding="utf-8")
        if f"]({slug}.md)" not in cur:
            if not cur.endswith("\n"):
                cur += "\n"
            index_path.write_text(cur + pointer, encoding="utf-8")
    else:
        index_path.write_text(f"# Memory Index\n\n{pointer}", encoding="utf-8")
    return path


def cmd_add(mem_dir: Path, name: str, mtype: str, description: str,
            body: str, title: str | None) -> None:
    if mtype not in ALLOWED_TYPES:
        sys.exit(f"error: --type must be one of {sorted(ALLOWED_TYPES)}")
    path = write_memory_file(mem_dir, name.strip(), mtype, description, body, title)
    print(f"wrote {path}")
    cmd_index(mem_dir)


def cmd_log(mem_dir: Path, text: str, mtype: str, scope: str,
            repo: str | None, name: str | None, description: str | None) -> None:
    """Write an ephemeral 'worked-out bit' into the annealing log (kind=log)."""
    text = text.strip()
    if not text:
        sys.exit("error: empty log bit")
    if mtype not in ALLOWED_TYPES:
        sys.exit(f"error: --type must be one of {sorted(ALLOWED_TYPES)}")
    if scope not in ("global", "local"):
        sys.exit("error: --scope must be global or local")
    if scope == "local" and not repo:
        sys.exit("error: --scope local requires --repo <path> (the promotion target)")
    name = (name or slugify(text)).strip()
    description = (description or " ".join(text.split())[:100]).strip()
    log_id = f"log:{slugify(name)}-{content_hash(text)[:6]}"

    col = get_collection(mem_dir)
    vec = embed([f"{description}\n\n{text}".strip()], is_query=False)[0]
    col.upsert(
        ids=[log_id], embeddings=[vec], documents=[text],
        metadatas=[{
            "kind": "log", "name": name, "type": mtype, "description": description,
            "scope": scope, "repo": repo or "", "hits": 0,
            "created": time.time(), "last_hit": 0.0,
        }],
    )
    print(f"logged {log_id}  (scope={scope}, promotes at {PROMOTE_AT} recalls)")


def promote(mem_dir: Path, col, log_id: str, meta: dict, body: str) -> None:
    """Promote a recalled log bit to durable markdown, then drop it from the log."""
    scope = meta.get("scope", "global")
    repo = meta.get("repo", "")
    mtype = meta.get("type", "reference")
    if mtype not in ALLOWED_TYPES:
        mtype = "reference"
    name = meta.get("name") or slugify(body)
    desc = meta.get("description") or " ".join(body.split())[:100]

    if scope == "local" and repo:
        # centralized repo lane, per the AGENTS.md Memory Bank Protocol:
        # ~/memory-bank/projects/<repo>/  (repo = git-root basename)
        target = mem_dir / "projects" / Path(repo).name
    else:
        target, scope = mem_dir, "global"

    recalls = int(meta.get("hits", PROMOTE_AT))
    date = time.strftime("%Y-%m-%d")
    note = (f"Auto-promoted from the Chroma log after {recalls} recalls ({date}). "
            f"It earned durability by being useful more than once — but you are the curator: "
            f"if it is not worth keeping, delete this file (it drops from the index on the next "
            f"`mem index`); if it is, refine it and remove this note.")
    path = write_memory_file(
        target, name, mtype, desc, body, unique=True,
        extra_meta={"promoted_from": "chroma-log", "recalls": recalls, "promoted": date},
        note=note,
    )
    col.delete(ids=[log_id])
    print(f"     ⤴ promoted to {scope} memory ({recalls} recalls)")
    if target == mem_dir:   # global docs are served here; reindex so it's recallable as a doc
        cmd_index(mem_dir, verbose=False)


def cmd_anneal(mem_dir: Path, ttl_days: float, dry_run: bool) -> None:
    """Evict log bits that are older than the TTL and still under the promote threshold."""
    col = get_collection(mem_dir)
    data = col.get()
    now = time.time()
    cutoff = ttl_days * 86400
    evict = []
    for i, m in zip(data["ids"], data["metadatas"]):
        m = m or {}
        if m.get("kind") != "log":
            continue
        hits = int(m.get("hits", 0))
        last = max(float(m.get("created", 0)), float(m.get("last_hit", 0)))
        age = now - last
        if hits < PROMOTE_AT and age > cutoff:
            evict.append((i, m, age))

    if not evict:
        print(f"anneal: nothing stale (ttl={ttl_days:g}d, keep if ≥{PROMOTE_AT} hits or newer)")
        return
    for i, m, age in evict:
        verb = "would evict" if dry_run else "evicted"
        print(f"  {verb}: {i}  ({int(age / 86400)}d idle, {int(m.get('hits', 0))} hits)  "
              f"{(m.get('description') or '')[:60]}")
    if not dry_run:
        col.delete(ids=[i for i, _, _ in evict])
    print(f"anneal: {len(evict)} {'candidate(s) (dry-run)' if dry_run else 'evicted'}")


def cmd_stats(mem_dir: Path) -> None:
    col = get_collection(mem_dir)
    data = col.get()
    from collections import Counter
    docs = [(i, m or {}) for i, m in zip(data["ids"], data["metadatas"])
            if (m or {}).get("kind") != "log"]
    logs = [(i, m or {}) for i, m in zip(data["ids"], data["metadatas"])
            if (m or {}).get("kind") == "log"]
    doc_stems = {i.split("#", 1)[0] for i, _ in docs}
    by_type = Counter(m.get("type", "?") for _, m in docs)

    print(f"collection: {COLLECTION}  |  {len(doc_stems)} doc files "
          f"({len(docs)} vectors) + {len(logs)} log bits")
    print(f"backend: {_BACKEND}")
    print(f"store: {mem_dir / '.chroma'}")
    print(f"embedder: {EMBED_MODEL} @ {OLLAMA_HOST}")
    print("docs by type:")
    for t, n in sorted(by_type.items()):
        print(f"  {t:12s} {n}")
    if logs:
        hot = sorted(logs, key=lambda x: int(x[1].get("hits", 0)), reverse=True)[:5]
        print(f"log bits: {len(logs)} (promote at {PROMOTE_AT} recalls, "
              f"anneal <{PROMOTE_AT} hits after {ANNEAL_TTL_DAYS}d)")
        for i, m in hot:
            print(f"  {int(m.get('hits', 0))}/{PROMOTE_AT} hits  {m.get('scope','global'):6s}  "
                  f"{(m.get('description') or i)[:56]}")
    n_files = len(memory_files(mem_dir))
    if n_files != len(doc_stems):
        print(f"  ! {n_files} markdown file(s) on disk vs {len(doc_stems)} indexed "
              f"— run `index` to reconcile")


# --- cli --------------------------------------------------------------------

def main(argv: list[str] | None = None) -> None:
    try:  # Windows defaults to cp1252; memories contain →, —, …, etc.
        sys.stdout.reconfigure(encoding="utf-8")
        sys.stdin.reconfigure(encoding="utf-8")  # --body - must decode as UTF-8
    except (AttributeError, ValueError):
        pass

    ap = argparse.ArgumentParser(description="embed-and-retrieve over markdown memory")
    ap.add_argument("--memory-dir", type=Path, default=DEFAULT_MEM_DIR,
                    help="memory directory (default: project memory path / $MEM_DIR)")
    sub = ap.add_subparsers(dest="cmd", required=True)

    sub.add_parser("index", help="reconcile vector index with markdown files")

    sp = sub.add_parser("search", help="semantic recall (bumps log hit counts)")
    sp.add_argument("query")
    sp.add_argument("-k", type=int, default=5)
    sp.add_argument("--type", dest="type_filter", default=None,
                    help="filter by memory type (user/feedback/project/reference)")
    sp.add_argument("--no-count", action="store_true",
                    help="browse without counting recalls toward promotion")

    sa = sub.add_parser("add", help="write a new memory (markdown + pointer) and index it")
    sa.add_argument("--name", required=True, help="kebab/snake slug (becomes filename)")
    sa.add_argument("--type", dest="mtype", required=True)
    sa.add_argument("--description", required=True)
    sa.add_argument("--title", default=None, help="display title for MEMORY.md (default: from name)")
    sa.add_argument("--body", default="-",
                    help="memory body, or '-' to read from stdin (default)")

    sl = sub.add_parser("log", help="write an ephemeral worked-out bit to the annealing log")
    sl.add_argument("text", help="the bit, or '-' to read from stdin")
    sl.add_argument("--type", dest="mtype", default="reference")
    sl.add_argument("--scope", default="global", help="global (default) or local")
    sl.add_argument("--repo", default=None,
                    help="repo path/name for --scope local; promotes to ~/memory-bank/projects/<repo>/")
    sl.add_argument("--name", default=None, help="label (default: derived from text)")
    sl.add_argument("--description", default=None, help="recall hook (default: first line)")

    an = sub.add_parser("anneal", help="evict stale, under-recalled log bits")
    an.add_argument("--ttl-days", type=float, default=ANNEAL_TTL_DAYS)
    an.add_argument("--dry-run", action="store_true")

    sd = sub.add_parser("dream", help="distil captured session events into memories")
    sd.add_argument("--since", default=None, help="only sessions with events since 24h / 7d / 30m")
    sd.add_argument("--session", default=None, help="one session id, ignoring its watermark")
    sd.add_argument("--dry-run", action="store_true", help="print, write nothing")

    sr = sub.add_parser("review", help="approve or reject candidate memories")
    sr.add_argument("--approve", default=None, help="memory name to approve")
    sr.add_argument("--reject", default=None, help="memory name to delete")
    sr.add_argument("--all", action="store_true", help="with --approve: approve every candidate")

    sub.add_parser("stats", help="index stats")

    args = ap.parse_args(argv)
    mem_dir = args.memory_dir
    if not mem_dir.exists():
        sys.exit(f"error: memory dir not found: {mem_dir}")

    if args.cmd == "index":
        cmd_index(mem_dir)
    elif args.cmd == "search":
        cmd_search(mem_dir, args.query, args.k, args.type_filter,
                   count_hits=not args.no_count)
    elif args.cmd == "add":
        body = sys.stdin.read() if args.body == "-" else args.body
        cmd_add(mem_dir, args.name, args.mtype, args.description, body, args.title)
    elif args.cmd == "log":
        text = sys.stdin.read() if args.text == "-" else args.text
        cmd_log(mem_dir, text, args.mtype, args.scope, args.repo, args.name, args.description)
    elif args.cmd == "anneal":
        cmd_anneal(mem_dir, args.ttl_days, args.dry_run)
    elif args.cmd == "dream":
        # Imported lazily: `dream` pulls in the events store and spawns the
        # Claude CLI, neither of which the retrieval commands should need.
        import dream
        dream.cmd_dream(mem_dir, args.since, args.session, args.dry_run)
    elif args.cmd == "review":
        import review
        review.cmd_review(mem_dir, args.approve, args.reject, args.all)
    elif args.cmd == "stats":
        cmd_stats(mem_dir)


if __name__ == "__main__":
    main()
