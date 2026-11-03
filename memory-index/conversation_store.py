"""| Stage | Mechanism | Contract |
| IDENTIFY | Resolve canonical workspace/common-repository URI | [mandatory] R1 |
| CAPTURE | Append source observations to existing volleys | [mandatory] R2 |
| DERIVE | Version scoped records and rebuildable FTS rows | [mandatory] R2-R4 |
| RECALL | Filter authorized scope before BM25 and source opening | [mandatory] R5-R8 |

Spec: ~/.harness/docs/playbooks/memory-and-harness-integration.md R1-R8.
CLOSED: basename authorization, recall-triggered promotion and another memory DB.
Preconditions: caller supplies workspace context for project recall; SQLite FTS5.
Failures: invalid context, provenance, bounds or writes raise; hook callers own fail-open.

Global conversation store: one append-only table tagged by (harness, project, session).

Purpose: provide cross-harness conversational continuity. The hot window is a
filtered view (last N volleys per harness+project); everything older is RAG-retrievable
via the Chroma index with Ebbinghaus decay weighting.

Preconditions: SQLite at ~/memory-bank/conversations.sqlite3; parent dir exists.
Failure modes: any write failure returns False without raising (same contract as events_store).
"""
from __future__ import annotations

import hashlib
import json
import math
import os
import re
import sqlite3
import subprocess
import time
from dataclasses import dataclass, field
from pathlib import Path
from typing import Optional
from urllib.parse import unquote, urlparse

# --- Config -----------------------------------------------------------------

DEFAULT_DB_NAME = "conversations.sqlite3"
DEFAULT_HOT_WINDOW = 13
PROMOTE_AT = 3
HIT_MIN_SCORE = 0.6
INITIAL_STABILITY = 7.0  # days; doubles on each retrieval
GROWTH_FACTOR = 1.5
DORMANT_FLOOR = 0.1  # effective_score below this -> dormant
ANNEAL_RETENTION_DAYS = 30  # dormant longer than this -> purgeable

MEMORY_SCHEMA = """
CREATE TABLE IF NOT EXISTS memory_records (
    memory_id TEXT PRIMARY KEY, name TEXT NOT NULL, type TEXT NOT NULL,
    description TEXT NOT NULL, project_uri TEXT NOT NULL, scope TEXT NOT NULL,
    session_id TEXT NOT NULL, harness_id TEXT NOT NULL, raw_id TEXT NOT NULL,
    source_ref TEXT NOT NULL, origin TEXT NOT NULL, epistemic TEXT NOT NULL,
    memory_function TEXT NOT NULL, status TEXT NOT NULL DEFAULT 'active',
    body TEXT NOT NULL, created_at REAL NOT NULL, updated_at REAL NOT NULL
);
CREATE INDEX IF NOT EXISTS idx_memory_scope ON memory_records(project_uri, scope, session_id, status);
CREATE TABLE IF NOT EXISTS memory_revisions (
    revision_id INTEGER PRIMARY KEY, memory_id TEXT NOT NULL, raw_id TEXT NOT NULL,
    action TEXT NOT NULL, metadata TEXT NOT NULL, timestamp REAL NOT NULL
);
CREATE TABLE IF NOT EXISTS memory_outcomes (
    outcome_id TEXT PRIMARY KEY, memory_id TEXT NOT NULL, outcome TEXT NOT NULL,
    evidence_ref TEXT NOT NULL, timestamp REAL NOT NULL
);
CREATE VIRTUAL TABLE IF NOT EXISTS memory_fts USING fts5(memory_id UNINDEXED, body, description);
"""


def project_identity(workspace_root: str) -> str:
    """Resolve a stable full-path identity, sharing Git worktrees within a project.

    Args:
        workspace_root: Existing absolute directory or local file URI.
    Returns:
        Normalized common repository root URI, or the non-Git workspace URI.
    Require: absolute caller-supplied workspace; never use the server's CWD.
    Guarantee: equal basenames do not imply equal project identity.
    Maintain: worktree-local paths remain separate from the project identity.
    Assert: invalid/missing workspace context raises before any read.
    """
    if not workspace_root:
        raise ValueError('workspace_root is required for project recall')
    if workspace_root.startswith('file:'):
        parsed = urlparse(workspace_root)
        if parsed.netloc not in ('', 'localhost'):
            raise ValueError('workspace URI must be local')
        workspace_root = unquote(parsed.path)
        if os.name == 'nt':
            workspace_root = workspace_root.lstrip('/')
    path = Path(workspace_root).expanduser()
    if not path.is_absolute() or not path.is_dir():
        raise ValueError('workspace_root must name an existing absolute directory')
    path = path.resolve()
    result = subprocess.run(['git', '-C', str(path), 'rev-parse', '--path-format=absolute', '--git-common-dir'],
                            capture_output=True, text=True, timeout=5, check=False)
    if result.returncode == 0:
        common = Path(result.stdout.strip()).resolve()
        path = common.parent if common.name == '.git' else common
    return Path(os.path.normcase(str(path))).as_uri()


def redact_memory(content: str) -> str:
    """Redact credential-shaped values from derived retrieval content.

    Require: text originates in a retained raw observation.
    Guarantee: common API key/password assignments and token strings are masked.
    Maintain: raw observations remain unchanged.
    Assert: this deterministic filter does not certify arbitrary text as secret-free.
    """
    content = re.sub(r'(?i)\b(api[_-]?key|password|access[_-]?token|secret)\b(\s*[:=]\s*)[\"\']?[^\s\"\',;]+', r'\1\2[REDACTED]', content)
    return re.sub(r'\b(?:sk-[A-Za-z0-9_-]{16,}|gh[pousr]_[A-Za-z0-9_]{20,})\b', '[REDACTED]', content)


def write_record(conn: sqlite3.Connection, name: str, body: str, *, mtype: str = 'reference',
                 description: str = '', workspace_root: str | None = None,
                 scope: str = 'project', session_id: str = '', harness_id: str = 'mcp',
                 source_ref: str = '', origin: str = 'dialogue', epistemic: str = 'inferred',
                 memory_function: str = 'factual', memory_id: str | None = None,
                 allow_unknown: bool = False) -> str:
    """Append raw evidence and atomically version one scoped derived memory.

    Require: explicit scope, bounded nonempty content and source metadata.
    Guarantee: raw observation, revision and searchable sanitized record survive.
    Maintain: updates never overwrite an earlier raw source or revision.
    Assert: only migration may retain unknown scope; working state cannot be shared.
    """
    scope = {'local': 'project', 'global': 'shared'}.get(scope, scope)
    if scope not in {'project', 'session', 'shared', 'unknown'} or (scope == 'unknown' and not allow_unknown):
        raise ValueError('scope must be project, session or shared')
    if not name.strip() or not body.strip() or len(body) > 65536:
        raise ValueError('memory requires a name and 1..65536 content characters')
    if origin not in {'dialogue', 'tool', 'document', 'inferred'} or epistemic not in {'observed', 'inferred'}:
        raise ValueError('invalid origin or epistemic classification')
    if memory_function not in {'factual', 'experiential', 'procedural', 'working'}:
        raise ValueError('invalid memory_function')
    if memory_function == 'working':
        if scope in {'shared', 'unknown'} or not session_id:
            raise ValueError('working state requires project/session scope and session_id')
        scope = 'session'
    if scope == 'session' and not session_id:
        raise ValueError('session scope requires session_id')
    project = project_identity(workspace_root or '') if scope in {'project', 'session'} else ''
    source_ref = source_ref.strip() or f'mcp:{harness_id}:{session_id or "unspecified"}'
    identity = json.dumps([project, scope, session_id if scope == 'session' else '', name], ensure_ascii=False)
    memory_id = memory_id or 'm:' + hashlib.sha256(identity.encode()).hexdigest()[:24]
    old = conn.execute('SELECT * FROM memory_records WHERE memory_id=?', (memory_id,)).fetchone()
    if scope == 'shared' and mtype == 'project':
        raise ValueError('project task memory cannot be shared; use an explicitly reusable memory type')
    if old and ((old['project_uri'], old['scope']) != (project, scope) or (scope == 'session' and old['session_id'] != session_id)):
        raise ValueError('an update cannot change memory scope, project or session')
    clean = redact_memory(body.strip())
    if old and old['body'] == clean and old['source_ref'] == source_ref and old['status'] == 'active' and old['type'] == mtype and old['description'] == redact_memory(description) and old['origin'] == origin and old['epistemic'] == epistemic and old['memory_function'] == memory_function:
        return memory_id
    raw = append_volley(conn, harness_id, project or 'unscoped', session_id or 'memory', 'memory', body)
    if raw is None:
        raise RuntimeError('raw observation could not be persisted')
    now = time.time()
    values = (memory_id, name, mtype, redact_memory(description), project, scope, session_id,
              harness_id, raw.volley_id, source_ref, origin, epistemic, memory_function,
              'active', clean, old['created_at'] if old else now, now)
    with conn:
        conn.execute('INSERT OR REPLACE INTO memory_records VALUES (?,?,?,?,?,?,?,?,?,?,?,?,?,?,?,?,?)', values)
        conn.execute('DELETE FROM memory_fts WHERE memory_id=?', (memory_id,))
        conn.execute('INSERT INTO memory_fts VALUES (?,?,?)', (memory_id, clean, redact_memory(description)))
        conn.execute('INSERT INTO memory_revisions(memory_id,raw_id,action,metadata,timestamp) VALUES (?,?,?,?,?)',
                     (memory_id, raw.volley_id, 'update' if old else 'add', json.dumps(dict(zip(('memory_id','name','type','description','project_uri','scope','session_id','harness_id','raw_id','source_ref','origin','epistemic','memory_function','status','body','created_at','updated_at'), values))), now))
    return memory_id


def scope_clause(workspace_root: str | None, session_id: str, scope: str) -> tuple[str, list]:
    """Build authorization before ranking or opening a source.

    Require: project context for normal recall; shared scope is explicit.
    Guarantee: unknown/retired records never enter ordinary recall.
    Maintain: working records belong to the matching session and project.
    Assert: audit is a separate operation, not a recall fallback.
    """
    if scope in {'shared', 'global'}:
        return "r.status='active' AND r.scope='shared'", []
    if scope not in {'project', 'local', 'project_shared', 'session'}:
        raise ValueError('recall scope must be project_shared, project, session or shared')
    project = project_identity(workspace_root or '')
    local = "(r.project_uri=? AND (r.scope='project' OR (r.scope='session' AND r.session_id=?)))"
    params = [project, session_id]
    if scope == 'session':
        if not session_id:
            raise ValueError('session scope requires session_id')
        local = "(r.project_uri=? AND r.scope='session' AND r.session_id=?)"
    if scope == 'project_shared':
        local = f"({local} OR r.scope='shared')"
    return "r.status='active' AND " + local, params


def search_records(conn: sqlite3.Connection, query: str, *, workspace_root: str | None = None,
                   session_id: str = '', scope: str = 'project_shared', k: int = 5,
                   mtype: str | None = None) -> list[dict]:
    """Return authorized BM25 hits without changing memory state.

    Require: k is 1..20; context satisfies scope_clause.
    Guarantee: retrieval cannot increment recalls or promote a record.
    Maintain: punctuation is quoted rather than executed as FTS syntax.
    Assert: empty lexical queries return no matches.
    """
    if not 1 <= k <= 20:
        raise ValueError('k must be between 1 and 20')
    clause, params = scope_clause(workspace_root, session_id, scope)
    words = re.findall(r'\w+', query, flags=re.UNICODE)[:64]
    if not words:
        return []
    expression = ' OR '.join('"' + w.replace('"', '""') + '"' for w in words)
    if mtype:
        clause += ' AND r.type=?'
        params.append(mtype)
    rows = conn.execute('SELECT r.*,bm25(memory_fts) AS score FROM memory_fts JOIN memory_records r ON r.memory_id=memory_fts.memory_id WHERE memory_fts MATCH ? AND ' + clause + ' ORDER BY score,r.memory_id LIMIT ?', [expression, *params, k]).fetchall()
    return [dict(row) for row in rows]


def open_record(conn: sqlite3.Connection, memory_id: str, *, workspace_root: str | None = None,
                session_id: str = '', scope: str = 'project_shared', limit: int = 6000) -> dict | None:
    """Open the authorized immutable source span with provenance.

    Require: limit is 1..6000 and the source is authorized in this context.
    Guarantee: source access repeats the search authorization.
    Maintain: raw records are never modified; credentials are redacted on output.
    Assert: inaccessible IDs return no content.
    """
    if not 1 <= limit <= 6000:
        raise ValueError('limit must be between 1 and 6000')
    clause, params = scope_clause(workspace_root, session_id, scope)
    row = conn.execute('SELECT r.*,v.content AS raw_content FROM memory_records r JOIN volleys v ON v.volley_id=r.raw_id WHERE r.memory_id=? AND ' + clause, [memory_id, *params]).fetchone()
    if row is None:
        return None
    result = dict(row)
    result['body'] = redact_memory(result.pop('raw_content'))[:limit]
    return result


def retire_record(conn: sqlite3.Connection, memory_id: str, evidence_ref: str, **context) -> None:
    """Hide a derived record while preserving raw evidence and history.

    Require: authorized current record and a retirement evidence pointer.
    Guarantee: subsequent ordinary search/open cannot expose it.
    Maintain: only derived visibility changes.
    Assert: retirement cannot authorize a foreign project.
    """
    record = open_record(conn, memory_id, **context)
    if not record or not evidence_ref.strip():
        raise ValueError('retirement requires an authorized memory and evidence_ref')
    with conn:
        conn.execute("UPDATE memory_records SET status='retired',updated_at=? WHERE memory_id=?", (time.time(), memory_id))
        conn.execute('INSERT INTO memory_revisions(memory_id,raw_id,action,metadata,timestamp) VALUES (?,?,?,?,?)',
                     (memory_id, record['raw_id'], 'retire', json.dumps({'evidence_ref': evidence_ref}), time.time()))


def record_feedback(conn: sqlite3.Connection, memory_id: str, outcome_id: str, outcome: str,
                    evidence_ref: str, **context) -> dict:
    """Record idempotent explicit helpful/harmful outcome evidence.

    Require: authorized memory, stable outcome ID and an evidence pointer.
    Guarantee: duplicate identical feedback is counted once.
    Maintain: feedback never promotes or rewrites a memory.
    Assert: conflicting reuse of an outcome ID raises.
    """
    if outcome not in {'helpful', 'harmful'} or not outcome_id.strip() or not evidence_ref.strip():
        raise ValueError('feedback requires helpful/harmful, outcome_id and evidence_ref')
    if not open_record(conn, memory_id, **context):
        raise ValueError('memory is not authorized in this scope')
    previous = conn.execute('SELECT * FROM memory_outcomes WHERE outcome_id=?', (outcome_id,)).fetchone()
    if previous and (previous['memory_id'], previous['outcome'], previous['evidence_ref']) != (memory_id, outcome, evidence_ref):
        raise ValueError('outcome_id already belongs to different evidence')
    with conn:
        conn.execute('INSERT OR IGNORE INTO memory_outcomes VALUES (?,?,?,?,?)', (outcome_id, memory_id, outcome, evidence_ref, time.time()))
    return dict(conn.execute("SELECT SUM(outcome='helpful') helpful,SUM(outcome='harmful') harmful FROM memory_outcomes WHERE memory_id=?", (memory_id,)).fetchone())

SCHEMA = """
CREATE TABLE IF NOT EXISTS volleys (
    volley_id       TEXT PRIMARY KEY,
    harness_id      TEXT NOT NULL,
    project_slug    TEXT NOT NULL,
    session_id      TEXT NOT NULL,
    seq             INTEGER NOT NULL,
    role            TEXT NOT NULL,
    content         TEXT NOT NULL,
    timestamp       REAL NOT NULL,
    provider_meta_hash TEXT,
    UNIQUE (harness_id, project_slug, session_id, seq)
);

CREATE INDEX IF NOT EXISTS idx_volleys_project_ts
    ON volleys (project_slug, timestamp DESC);
CREATE INDEX IF NOT EXISTS idx_volleys_harness_project
    ON volleys (harness_id, project_slug, timestamp DESC);
"""


@dataclass
class Volley:
    volley_id: str
    harness_id: str
    project_slug: str
    session_id: str
    seq: int
    role: str
    content: str
    timestamp: float
    provider_meta_hash: Optional[str] = None


# --- Connection -------------------------------------------------------------


def default_db_path() -> Path:
    return Path.home() / "memory-bank" / DEFAULT_DB_NAME


def connect(db_path: Path | None = None) -> sqlite3.Connection:
    """Open or create the conversation store.

    Require: parent directory exists.
    Guarantee: schema is current on return.
    """
    path = db_path or default_db_path()
    path.parent.mkdir(parents=True, exist_ok=True)
    conn = sqlite3.connect(str(path), timeout=10)
    conn.row_factory = sqlite3.Row
    conn.execute("PRAGMA journal_mode=WAL")
    conn.executescript(SCHEMA)
    conn.executescript(MEMORY_SCHEMA)
    return conn


# --- Write ------------------------------------------------------------------


def append_volley(
    conn: sqlite3.Connection,
    harness_id: str,
    project_slug: str,
    session_id: str,
    role: str,
    content: str,
    provider_meta_hash: str | None = None,
    timestamp: float | None = None,
) -> Volley | None:
    """Append one conversational volley. Returns the Volley or None on failure.

    Seq is auto-incremented per (harness, project, session).
    """
    ts = timestamp or time.time()
    try:
        with conn:
            row = conn.execute(
                "SELECT MAX(seq) FROM volleys WHERE harness_id=? AND project_slug=? AND session_id=?",
                (harness_id, project_slug, session_id),
            ).fetchone()
            seq = (row[0] + 1) if row[0] is not None else 0

            sig = hashlib.sha256(
                f"{harness_id}:{project_slug}:{session_id}:{seq}:{ts}".encode()
            ).hexdigest()[:16]
            volley_id = f"v:{project_slug}:{session_id}:{seq}:{sig}"

            conn.execute(
                """INSERT INTO volleys (volley_id, harness_id, project_slug, session_id, seq, role, content, timestamp, provider_meta_hash)
                   VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?)""",
                (volley_id, harness_id, project_slug, session_id, seq, role, content, ts, provider_meta_hash),
            )
        return Volley(volley_id, harness_id, project_slug, session_id, seq, role, content, ts, provider_meta_hash)
    except Exception:
        return None


# --- Read -------------------------------------------------------------------


def get_hot_window(
    conn: sqlite3.Connection,
    harness_id: str,
    project_slug: str,
    limit: int = DEFAULT_HOT_WINDOW,
) -> list[Volley]:
    """Return the N most recent volleys for (harness, project), newest first."""
    rows = conn.execute(
        """SELECT * FROM volleys
           WHERE harness_id=? AND project_slug=?
           ORDER BY timestamp DESC, seq DESC
           LIMIT ?""",
        (harness_id, project_slug, limit),
    ).fetchall()
    return [_row_to_volley(r) for r in reversed(rows)]  # return in chronological order


def get_project_volleys(
    conn: sqlite3.Connection,
    project_slug: str,
    since: float | None = None,
    limit: int = 100,
) -> list[Volley]:
    """Return volleys for a project across all harnesses (for cross-harness RAG)."""
    if since:
        rows = conn.execute(
            """SELECT * FROM volleys
               WHERE project_slug=? AND timestamp >= ?
               ORDER BY timestamp DESC LIMIT ?""",
            (project_slug, since, limit),
        ).fetchall()
    else:
        rows = conn.execute(
            """SELECT * FROM volleys
               WHERE project_slug=?
               ORDER BY timestamp DESC LIMIT ?""",
            (project_slug, limit),
        ).fetchall()
    return [_row_to_volley(r) for r in reversed(rows)]


def volley_count(conn: sqlite3.Connection, project_slug: str | None = None) -> int:
    """Total volley count, optionally filtered by project."""
    if project_slug:
        row = conn.execute("SELECT COUNT(*) FROM volleys WHERE project_slug=?", (project_slug,)).fetchone()
    else:
        row = conn.execute("SELECT COUNT(*) FROM volleys").fetchone()
    return row[0]


def _row_to_volley(row: sqlite3.Row) -> Volley:
    return Volley(
        volley_id=row["volley_id"],
        harness_id=row["harness_id"],
        project_slug=row["project_slug"],
        session_id=row["session_id"],
        seq=row["seq"],
        role=row["role"],
        content=row["content"],
        timestamp=row["timestamp"],
        provider_meta_hash=row["provider_meta_hash"],
    )


# --- Ebbinghaus Decay -------------------------------------------------------


def effective_score(
    similarity: float,
    last_retrieved_at: float,
    stability: float,
    now: float | None = None,
) -> float:
    """Compute decay-weighted score: similarity * exp(-elapsed_days / stability).

    Require: stability > 0.
    Guarantee: returns value in [0, similarity].
    """
    now = now or time.time()
    elapsed_days = (now - last_retrieved_at) / 86400.0
    if elapsed_days <= 0:
        return similarity
    decay = math.exp(-elapsed_days / max(stability, 0.01))
    return similarity * decay


def is_dormant(
    last_retrieved_at: float,
    stability: float,
    now: float | None = None,
    floor: float = DORMANT_FLOOR,
) -> bool:
    """True if effective_score would be below the dormant floor at max similarity."""
    return effective_score(1.0, last_retrieved_at, stability, now) < floor


def grow_stability(current: float) -> float:
    """Increase stability after a confirmed retrieval."""
    return current * GROWTH_FACTOR


# --- Lane Classification ---------------------------------------------------


def classify_lane(content: str, meta: dict | None = None) -> str:
    """Classify a promoted observation into the correct durable lane.

    Returns one of: 'memory-bank', 'specs-proposal', 'steering-proposal', 'skill-candidate'.
    Uses keyword heuristics; LLM classification is a stretch goal.
    """
    lower = content.lower()
    meta = meta or {}

    # Spec-level signals
    spec_signals = ["requirement", "acceptance criteria", "shall", "must not",
                    "design decision", "architecture", "task:", "blocked:"]
    if any(s in lower for s in spec_signals):
        return "specs-proposal"

    # Steering/policy signals
    steering_signals = ["policy:", "rule:", "always:", "never:", "constraint:",
                        "gate:", "enforce", "steering"]
    if any(s in lower for s in steering_signals):
        return "steering-proposal"

    # Skill/procedure signals
    skill_signals = ["procedure:", "workflow:", "protocol:", "steps:",
                     "when to use:", "how to:", "pattern:"]
    if any(s in lower for s in skill_signals):
        return "skill-candidate"

    # Default: memory-bank (facts, decisions, observations)
    return "memory-bank"
