"""| Stage | Mechanism | Contract |
| CAPTURE | Append raw evidence to incumbent SQLite volleys | [mandatory] R1-R3 |
| RECALL | Authorize scope, BM25 rank and open bounded source spans | [mandatory] R4-R8 |
| SERVE | Expose original and scoped tools through stateless MCP | [mandatory] R17 |

Spec: ~/.harness/docs/playbooks/memory-and-harness-integration.md.
CLOSED: recall-triggered promotion, semantic-only default, basename authorization.
Preconditions: caller workspace context; existing pinned FastMCP runtime.
Failures: invalid context/provenance/write errors propagate; dense is optional and off.
"""
from __future__ import annotations

import hashlib
import json
import os
import sys
import time
from pathlib import Path

import yaml
from starlette.responses import JSONResponse
from fastmcp import FastMCP

import conversation_store as convstore
sys.path.insert(0, str(Path.home() / '.harness'))
from specs.event_ingestion import PromotionRouter

# --- config -----------------------------------------------------------------

MEM_DIR = Path(os.environ.get("MEM_DIR", os.path.expanduser("~/memory-bank")))
OLLAMA_HOST = os.environ.get("MEM_OLLAMA_HOST", "http://127.0.0.1:11434")
EMBED_MODEL = os.environ.get("MEM_EMBED_MODEL", "nomic-embed-text")
POLICY_FILE = Path.home() / '.harness/harness.json'
POLICY = json.loads(POLICY_FILE.read_text(encoding='utf-8')).get('memory', {}) if POLICY_FILE.exists() else {}
DENSE_ENABLED = bool(POLICY.get('dense_enabled', False))
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
        "Scoped evidence memory; pass absolute workspace_root and session_id. Search, then open_memory before citing. "
        "Use search_memory to recall relevant context, log_memory to jot ephemeral bits "
        "with explicit scope; recall is read-only. Use memory_feedback for measured outcomes and add_memory for "
        "durable entries. The store is at ~/memory-bank/."
    ),
)


# --- Health endpoint for liveness probes ------------------------------------

@mcp.custom_route('/health', methods=['GET'])
async def health(_):
    """Report SQLite health without model calls; errors remain visible."""
    conn = _get_conv_conn()
    return JSONResponse({'status': 'ok', 'count': conn.execute('SELECT COUNT(*) FROM memory_records').fetchone()[0],
                         'store': str(MEM_DIR / 'conversations.sqlite3'), 'dense_enabled': DENSE_ENABLED})

# --- Chroma (in-process PersistentClient) -----------------------------------

_col = None


def get_collection():
    global _col
    if _col is None:
        # Dense retrieval is opt-in; keep the default SQLite path independent
        # of optional vector-store packages and their runtime compatibility.
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

    prefix = "search_query: " if is_query else "search_document: "
    from ollama import Client
    c = Client(host=OLLAMA_HOST)
    return [c.embeddings(model=EMBED_MODEL, prompt=prefix + t)["embedding"] for t in texts]


# --- Helpers ported from mem.py ---------------------------------------------




def content_hash(raw: str) -> str:
    return hashlib.sha256(raw.encode("utf-8")).hexdigest()






def memory_files(mem_dir: Path) -> list[Path]:
    """Require: deployment root; Guarantee: deterministic durable sources, excluding generated continuity archives."""
    excluded = {'.chroma', 'handoffs', 'compaction-backups'}
    return sorted(p for p in mem_dir.rglob('*.md') if p.name != INDEX_FILE and not excluded.intersection(p.parts))










# --- MCP Tools --------------------------------------------------------------


@mcp.tool()
def search_memory(query: str, k: int = 5, type: str | None = None, workspace_root: str | None = None,
                  session_id: str = '', scope: str = 'project_shared', dense: bool = False) -> str:
    """Search scoped evidence; pass workspace_root/session_id and open hits before citing.

    Require: k 1..20 and absolute workspace for project recall.
    Guarantee: scope filtering before BM25; reads do not promote or count recalls.
    Maintain: at most 6000 excerpt characters; raw evidence remains unchanged.
    Assert: no authorized evidence means abstain, not invent an answer.
    """
    conn = _get_conv_conn()
    context = dict(workspace_root=workspace_root, session_id=session_id, scope=scope)
    hits = convstore.search_records(conn, query, k=k, mtype=type, **context)
    if dense:
        if not DENSE_ENABLED:
            raise ValueError('dense_enabled is false in ~/.harness/harness.json')
        data = get_collection().query(query_embeddings=embed([query], True), n_results=k)
        scores = {hit['memory_id']: 1 / (61 + i) for i, hit in enumerate(hits)}
        records = {hit['memory_id']: hit for hit in hits}
        for rank, mid in enumerate(data['ids'][0]):
            hit = convstore.open_record(conn, mid, **context)
            if hit and (not type or hit['type'] == type):
                records[mid] = hit
                scores[mid] = scores.get(mid, 0) + 1 / (61 + rank)
        hits = [records[mid] for mid in sorted(scores, key=lambda mid: (-scores[mid], mid))[:k]]
    budget = MAX_WHOLE_CHARS
    lines = []
    for hit in hits:
        excerpt = hit['body'][:min(600, budget)]
        if not excerpt:
            break
        lines.append(_render_evidence(hit, excerpt))
        budget -= len(excerpt)
    return '\n\n'.join(lines) or '(no authorized matches; abstain or refine query)'


@mcp.tool()
def log_memory(content: str, scope: str = 'project', repo: str | None = None, type: str = 'reference',
               workspace_root: str | None = None, session_id: str = '', harness_id: str = 'mcp',
               source_ref: str = '', origin: str = 'dialogue', epistemic: str = 'inferred',
               memory_function: str = 'factual') -> str:
    """Record scoped evidence; repo/local remain compatibility aliases.

    Require: caller workspace and valid type; shared scope is explicit.
    Guarantee: append raw evidence and a versioned sanitized lexical record.
    Maintain: no embedding call or automatic promotion.
    Assert: conflicting context is rejected.
    """
    if type not in ALLOWED_TYPES:
        raise ValueError('invalid memory type')
    if repo and workspace_root and convstore.project_identity(repo) != convstore.project_identity(workspace_root):
        raise ValueError('repo and workspace_root identify different projects')
    mid = convstore.write_record(_get_conv_conn(), 'log-' + content_hash(content)[:16], content,
        mtype=type, description=' '.join(content.split())[:100], workspace_root=workspace_root or repo,
        scope=scope, session_id=session_id, harness_id=harness_id, source_ref=source_ref,
        origin=origin, epistemic=epistemic, memory_function=memory_function)
    return f'Logged {mid}; explicit outcome evidence, not recall count, governs promotion.'


@mcp.tool()
def add_memory(name: str, type: str, description: str, body: str, workspace_root: str | None = None,
               session_id: str = '', scope: str = 'project', harness_id: str = 'mcp',
               source_ref: str = '', origin: str = 'dialogue', epistemic: str = 'inferred',
               memory_function: str = 'factual') -> str:
    """Add durable evidence to the existing SQLite store.

    Require: valid type and explicit caller context.
    Guarantee: raw source and revision survive in durable storage.
    Maintain: existing positional API and inferred/observed distinction.
    Assert: no model or vector backend is required.
    """
    if type not in ALLOWED_TYPES:
        raise ValueError('invalid memory type')
    mid = convstore.write_record(_get_conv_conn(), name, description if body == '-' else body,
        mtype=type, description=description, workspace_root=workspace_root, session_id=session_id,
        scope=scope, harness_id=harness_id, source_ref=source_ref, origin=origin,
        epistemic=epistemic, memory_function=memory_function)
    return f'Added durable memory {mid}'


@mcp.tool()
def index_memory(dense: bool = False, include_legacy_vectors: bool = False) -> str:
    """Snapshot legacy sources without rewriting originals or guessing their project.

    Require: explicit dense enablement before embedding.
    Guarantee: idempotent imports; unknown scope remains audit-only.
    Maintain: original files, vector records and raw snapshots survive.
    Assert: metadata, never prose or basename, supplies scope.
    """
    if dense and not DENSE_ENABLED:
        raise ValueError('dense_enabled is false in canonical harness policy')
    conn = _get_conv_conn()
    count = 0
    source_count = 0
    metadata_errors = 0
    chunk_chars = 60000
    for path in memory_files(MEM_DIR):
        raw = path.read_text(encoding='utf-8')
        if not raw.strip():
            continue
        parts = raw.split('---', 2) if raw.startswith('---') else []
        front = {}
        if len(parts) == 3:
            try:
                parsed = yaml.safe_load(parts[1]) or {}
                if not isinstance(parsed, dict):
                    metadata_errors += 1
                else:
                    front = parsed
            except yaml.YAMLError:
                metadata_errors += 1
        meta = front.get('metadata') or {}
        if not isinstance(meta, dict):
            metadata_errors += 1
            front = {}
            meta = {}
        mtype = str(meta.get('type') or front.get('type') or 'reference')
        legacy_scope = meta.get('scope')
        scope = {'local': 'project', 'global': 'shared' if meta.get('shared') is True else 'unknown'}.get(legacy_scope, legacy_scope or 'unknown')
        if legacy_scope == 'user' and mtype == 'user':
            scope = 'shared'
        workspace = meta.get('workspace_root') or meta.get('repo')
        if scope in {'project', 'session'} and (not workspace or not Path(workspace).is_dir()):
            scope = 'unknown'
        if scope not in {'project', 'session', 'shared', 'unknown'}:
            scope = 'unknown'
            metadata_errors += 1
        offsets = range(0, len(raw), chunk_chars)
        for start in offsets:
            end = min(start + chunk_chars, len(raw))
            body = raw[start:end]
            source = path.resolve().as_uri() + f'#chars={start}:{end}'
            mid = convstore.write_record(conn, str(front.get('name') or path.stem), body,
                mtype=mtype, description=str(front.get('description') or ''),
                workspace_root=workspace, scope=scope, session_id=str(meta.get('session_id') or ''),
                harness_id=str(meta.get('harness_id') or 'legacy'), source_ref=source,
                origin='document', epistemic=str(meta.get('epistemic') or 'inferred'),
                memory_id=('file:user-shared:' if legacy_scope == 'user' and mtype == 'user' else 'file:') + content_hash(f'{path.resolve()}#{start}:{end}')[:24], allow_unknown=True)
            count += 1
            if dense and scope != 'unknown':
                record = conn.execute('SELECT * FROM memory_records WHERE memory_id=?', (mid,)).fetchone()
                get_collection().upsert(ids=[mid], documents=[record['body']], embeddings=embed([record['body']], False),
                    metadatas=[{'project_uri': record['project_uri'], 'scope': scope}])
        source_count += 1
    if include_legacy_vectors:
        data = get_collection().get(include=['documents', 'metadatas'])
        for mid, body, meta in zip(data['ids'], data['documents'], data['metadatas']):
            if body:
                convstore.write_record(conn, str((meta or {}).get('name') or mid), body, scope='unknown',
                    source_ref=f'chroma:{mid}', origin='document', memory_id='legacy:' + content_hash(mid)[:24], allow_unknown=True)
                count += 1
    return f'Indexed {count} records from {source_count} markdown sources; metadata_errors={metadata_errors}; unknown scope is audit-only; dense={dense}'


# --- Conversation Store Tools ------------------------------------------------

_conv_conn = None


def _get_conv_conn():
    """Require: configured MEM_DIR; Guarantee: private deployments retain private SQLite state."""
    global _conv_conn
    if _conv_conn is None:
        _conv_conn = convstore.connect(MEM_DIR / 'conversations.sqlite3')
    return _conv_conn


@mcp.tool()
def append_volley(role: str, content: str, harness_id: str, project_slug: str, session_id: str,
                  provider_meta_hash: str | None = None, workspace_root: str | None = None) -> str:
    """Require: caller workspace; Guarantee: raw conversation keyed by canonical identity, not display slug."""
    identity = convstore.project_identity(workspace_root or '')
    v = convstore.append_volley(_get_conv_conn(), harness_id, identity, session_id, role, content, provider_meta_hash)
    if v is None:
        raise RuntimeError('raw capture failed')
    return f'Appended {v.volley_id} (project={identity})'


@mcp.tool()
def get_hot_window(harness_id: str, project_slug: str, limit: int = 13,
                   workspace_root: str | None = None, session_id: str = '') -> str:
    """Require: workspace, session, limit 1..20; Guarantee: current-session context only, at most 6000 characters."""
    identity = convstore.project_identity(workspace_root or '')
    if not session_id or not 1 <= limit <= 20:
        raise ValueError('session_id and limit 1..20 are required')
    rows = _get_conv_conn().execute('SELECT * FROM volleys WHERE harness_id=? AND project_slug=? AND session_id=? AND role!=? ORDER BY timestamp DESC,seq DESC LIMIT ?',
        (harness_id, identity, session_id, 'memory', limit)).fetchall()
    return '\n'.join(f"[{r['role']}] {convstore.redact_memory(r['content'])[:400]}" for r in reversed(rows))[:6000] or '(no current-session history)'


@mcp.tool()
def get_project_history(project_slug: str, limit: int = 20, workspace_root: str | None = None) -> str:
    """Require: workspace and limit 1..20; Guarantee: bounded project evidence labeled historical, not current assignment."""
    if not 1 <= limit <= 20:
        raise ValueError('limit must be 1..20')
    identity = convstore.project_identity(workspace_root or '')
    rows = convstore.get_project_volleys(_get_conv_conn(), identity, limit=limit)
    return ('Historical evidence, not the current assignment:\n' + '\n'.join(
        f'[{v.volley_id}] [{v.harness_id}/{v.session_id}] {convstore.redact_memory(v.content)[:300]}' for v in rows))[:6000]


@mcp.tool()
def anneal_memory(dry_run: bool = True, retention_days: int = 30) -> str:
    """Report stale session records; explicit apply changes visibility without deleting evidence.

    Require: positive retention period; apply is explicit.
    Guarantee: append visibility revisions; preserve raw observations.
    Maintain: no maintenance as a recall side effect.
    Assert: durable/shared records are not purged.
    """
    if retention_days <= 0:
        raise ValueError('retention_days must be positive')
    conn = _get_conv_conn()
    rows = conn.execute("SELECT * FROM memory_records WHERE status='active' AND scope='session' AND updated_at<?", (time.time()-retention_days*86400,)).fetchall()
    if not dry_run:
        with conn:
            for row in rows:
                conn.execute("UPDATE memory_records SET status='dormant' WHERE memory_id=?", (row['memory_id'],))
                conn.execute('INSERT INTO memory_revisions(memory_id,raw_id,action,metadata,timestamp) VALUES (?,?,?,?,?)',
                    (row['memory_id'], row['raw_id'], 'dormant', json.dumps({'retention_days': retention_days}), time.time()))
    return f'Anneal {"dry run" if dry_run else "applied"}: {len(rows)} stale session records; raw evidence retained'


@mcp.tool()
def memory_stats() -> str:
    """Require: local SQLite; Guarantee: counts and policy without embedding or inference."""
    conn = _get_conv_conn()
    return json.dumps({'store': str(MEM_DIR / 'conversations.sqlite3'),
        'memories': {r[0]: r[1] for r in conn.execute('SELECT scope,COUNT(*) FROM memory_records GROUP BY scope')},
        'raw_volleys': convstore.volley_count(conn), 'dense_enabled': DENSE_ENABLED}, sort_keys=True)



def _render_evidence(record: dict, excerpt: str) -> str:
    """Require: authorized record; Guarantee: quoted evidence includes identity, scope and source pointers."""
    return (f"[{record['memory_id']}] {record['name']} | {record['scope']} | {record['epistemic']}\n"
            f"source={record['source_ref']} raw={record['raw_id']} project={record['project_uri']} "
            f"session={record['session_id']} harness={record['harness_id']} origin={record['origin']} timestamp={record['updated_at']}\n"
            f"<quoted-evidence>\n{excerpt}\n</quoted-evidence>")


@mcp.tool()
def open_memory(memory_id: str, workspace_root: str | None = None, session_id: str = '',
                scope: str = 'project_shared', limit: int = 6000) -> str:
    """Require: authorized scope and limit 1..6000; Guarantee: bounded immutable source span with provenance."""
    record = convstore.open_record(_get_conv_conn(), memory_id, workspace_root=workspace_root, session_id=session_id, scope=scope, limit=limit)
    return _render_evidence(record, record['body']) if record else '(source unavailable in this scope; abstain)'


@mcp.tool()
def update_memory(memory_id: str, body: str, source_ref: str, workspace_root: str | None = None,
                  session_id: str = '', scope: str = 'project_shared') -> str:
    """Require: authorized memory and source_ref; Guarantee: append a revision without overwriting raw evidence."""
    conn = _get_conv_conn()
    r = convstore.open_record(conn, memory_id, workspace_root=workspace_root, session_id=session_id, scope=scope)
    if not r or not source_ref.strip():
        raise ValueError('authorized memory and source_ref required')
    convstore.write_record(conn, r['name'], body, mtype=r['type'], description=r['description'],
        workspace_root=workspace_root, scope=r['scope'], session_id=r['session_id'], harness_id=r['harness_id'],
        source_ref=source_ref, origin=r['origin'], epistemic=r['epistemic'], memory_function=r['memory_function'], memory_id=memory_id)
    return f'Updated {memory_id}; prior evidence retained'


@mcp.tool()
def retire_memory(memory_id: str, evidence_ref: str, workspace_root: str | None = None,
                  session_id: str = '', scope: str = 'project_shared') -> str:
    """Require: authorized memory and evidence; Guarantee: hide derived memory, preserve raw/revision history."""
    convstore.retire_record(_get_conv_conn(), memory_id, evidence_ref, workspace_root=workspace_root, session_id=session_id, scope=scope)
    return f'Retired {memory_id}; raw evidence retained'


@mcp.tool()
def memory_feedback(memory_id: str, outcome_id: str, outcome: str, evidence_ref: str,
                    workspace_root: str | None = None, session_id: str = '', scope: str = 'project_shared') -> str:
    """Require: stable outcome ID and measured evidence; Guarantee: idempotent helpful/harmful feedback without promotion."""
    conn = _get_conv_conn()
    context = dict(workspace_root=workspace_root, session_id=session_id, scope=scope)
    result = convstore.record_feedback(conn, memory_id, outcome_id, outcome, evidence_ref, **context)
    record = convstore.open_record(conn, memory_id, **context)
    proposal = PromotionRouter().classify(record['body'], {'event_id': record['raw_id']})
    result.update(proposal_lane=proposal.lane.value, promotion_allowed=False)
    return json.dumps(result)


@mcp.tool()
def audit_memory(limit: int = 20) -> str:
    """Require: limit 1..100; Guarantee: metadata-only list of unresolved legacy scope, without promotion."""
    if not 1 <= limit <= 100:
        raise ValueError('limit must be 1..100')
    rows = _get_conv_conn().execute("SELECT memory_id,name,source_ref,scope FROM memory_records WHERE scope='unknown' ORDER BY memory_id LIMIT ?", (limit,)).fetchall()
    return json.dumps([dict(r) for r in rows])


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
        mcp.run(transport="streamable-http", host="127.0.0.1", port=args.port,
                stateless_http=True)
