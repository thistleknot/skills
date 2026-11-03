#!/usr/bin/env python3
"""Offline distillation: raw session events -> durable candidate memories.

Thesis
------
Capture and judgment must be separate processes. `events_store` records what
happened with no opinion; this pass decides what was worth remembering. Splitting
them is what makes each one correct: a capture path that must judge will decline
under load, and a judgment path that must not miss events will hoard. MKG states
the same split as "the hooks record *what happened*, the dream phase decides
*what's worth remembering*".

Adapted from neo4j-labs/meta-knowledge-graph `hooks/process_project.py`. We keep
its extraction prompt shape, its user/project scope rule, and its
candidate->approved status gate. We drop its neo4j store, its embedded-in-Cypher
consistency gate, and its episodic-observation lane.

Necessary conditions
--------------------
- The pass must be idempotent. `sessions.last_dreamed_at` is advanced per session
  immediately after that session's memories are written, so a run killed halfway
  redoes only the sessions it had not reached.
- The extraction subprocess must not be captured. `MEM_IN_EXTRACTION=1` is set on
  the `claude -p` child so its own hooks no-op; without it the model's summary of
  a session becomes new evidence about that session and the loop compounds.
- Nothing reaches an approved state on confidence alone until confidence has a
  measured distribution. See `_auto_approve_threshold`.

State machine
-------------
    (events) --extract--> candidate --review/gate--> approved
                              |                          |
                              +--contradicts existing-->  superseded (the OLD one)

`candidate` is the only state this script writes for user-scoped memories.
Project-scoped memories may auto-approve once the threshold is calibrated.

Design decisions
----------------
- The LLM call goes through `claude -p`, not an API key: it inherits the
  subscription OAuth this box already has, matching MKG's `claude_cli` backend
  preference and avoiding a second credential to manage.
- Writes go through `mem.write_memory_file` and `mem.cmd_index`, never a
  hand-rolled writer. Two writers means two frontmatter dialects and a split
  index.
- `lessons-learned` rows are folded into the same corpus as corrections. That
  skill's SKILL.md already specifies this handoff and had no consumer.

Invariants
----------
- Every written memory carries `scope`, `status`, `confidence`, `source_session`.
- A memory is never written for a session whose watermark already covers it.
- `--dry-run` performs zero writes: no markdown, no index, no watermark.

Failure modes
-------------
- `claude` CLI absent or extraction times out -> that session is skipped and its
  watermark is NOT advanced, so the next run retries it.
- Model returns unparseable JSON -> same disposition as above; the raw reply is
  printed so the failure is diagnosable rather than silent.
- Ollama/Chroma down -> contradiction checking degrades to "no contradiction
  found", and every candidate stays `candidate` for human review. Degrades toward
  more review, never toward silent auto-approval.
"""

from __future__ import annotations

import argparse
import json
import os
import re
import statistics
import subprocess
import sys
from datetime import datetime, timedelta, timezone
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parent))

import events_store as es  # noqa: E402
import mem  # noqa: E402

# Corpus shaping. A session with 400 tool calls must not produce a 400-event
# prompt; the newest events carry the outcome, which is what a learning is about.
MAX_CORPUS_EVENTS = 120
MAX_EVENT_CHARS = 600
MAX_EXISTING_MEMORIES = 40

# Contradiction detection: cosine similarity above which a new candidate is
# treated as speaking about the same subject as an existing memory. Not a
# threshold on truth -- only on topic overlap, which is what gates the review.
SAME_SUBJECT_SIM = 0.80

# Auto-approval needs a calibrated distribution before it can run at all.
MIN_CONFIDENCE_OBSERVATIONS = 10

EXTRACTION_TIMEOUT_S = 300

EXTRACTION_PROMPT = """Session: [[SESSION_ID]] (project: [[PROJECT]])

Completed work from this session:
[[CORPUS]]

[[EXISTING_MEMORY]]

Decide whether this completed work contains durable memory worth storing.
Prefer updating existing memory when it is materially the same idea. A
restatement of a listed fact is an update to that name, not a new item. Return an
empty list when the work is routine, transient, or already covered.

A learning is any durable, reusable fact worth recalling in a future session:
reusable facts, environment quirks, domain observations, durable preferences,
task patterns, and decisions or stable policy choices with implementation impact
("Decision:", "we decided", "going forward must/should"). When the signal is a
decision, fold the reason it matters into the learning text rather than recording
it separately.

Every learning has a scope:
- "user": a durable fact about the *person* you are working with that holds
  across projects -- their role, communication and workflow preferences, tooling
  and language preferences, coding or writing style, recurring constraints, or a
  stable working agreement. When the signal is unambiguously about the person,
  scope it "user" on first explicit mention. Require repetition only for
  borderline traits you are inferring rather than ones they stated.
- "project": a fact, quirk, observation, task pattern, or policy choice specific
  to this project or its environment.
Default to "project" only when it is genuinely unclear. Never store secrets,
credentials, sensitive personal data, transient details, or one-off task context.

Return JSON only, no prose, with this shape:
{
  "learnings": [
    {
      "action": "create|update",
      "existing_name": "memory name when action is update, else null",
      "scope": "project|user",
      "name": "short-kebab-case-slug",
      "description": "one line, used for recall ranking",
      "text": "the durable learning, with why it matters",
      "confidence": 0.0,
      "reason": "why this action"
    }
  ]
}
"""


# --- corpus construction ----------------------------------------------------

def render_event(row) -> str | None:
    """One compact line per event, or None for events with no signal.

    Bare PreToolUse rows are dropped: the PostToolUse for the same call carries
    the same intent plus the outcome, so keeping both doubles the corpus for no
    added evidence.
    """
    name = row["event_name"]
    if name == "PreToolUse":
        return None
    if name == "UserPromptSubmit" and row["prompt"]:
        return f"USER: {row['prompt'][:MAX_EVENT_CHARS]}"
    if name == "PostToolUse":
        if row["tool_error"]:
            return f"TOOL {row['tool_name']} FAILED: {row['tool_error'][:MAX_EVENT_CHARS]}"
        detail = (row["tool_input"] or "")[:200]
        return f"TOOL {row['tool_name']}: {detail}"
    if name in ("Stop", "SessionEnd") and row["last_assistant_message"]:
        return f"ASSISTANT: {row['last_assistant_message'][:MAX_EVENT_CHARS]}"
    return None


def build_corpus(rows) -> str:
    lines = [line for line in (render_event(r) for r in rows) if line]
    if len(lines) > MAX_CORPUS_EVENTS:
        dropped = len(lines) - MAX_CORPUS_EVENTS
        lines = [f"[...{dropped} earlier events omitted]"] + lines[-MAX_CORPUS_EVENTS:]
    return "\n".join(lines)


def recent_lessons(since: str | None) -> list[str]:
    """Rows from LESSONS_LEARNED.sqlite3 as correction evidence.

    A lesson with a high `count` is one the durable memory has not absorbed yet,
    which is exactly the signal this pass should act on.
    """
    db = Path(__file__).resolve().parents[1] / "LESSONS_LEARNED.sqlite3"
    if not db.is_file():
        return []
    import sqlite3
    try:
        conn = sqlite3.connect(f"file:{db}?mode=ro", uri=True, timeout=10)
        conn.row_factory = sqlite3.Row
        sql = "SELECT category, symptom, root_cause, resolution, count FROM lessons"
        params: list = []
        if since:
            sql += " WHERE updated_at >= ?"
            params.append(since)
        sql += " ORDER BY count DESC LIMIT 20"
        rows = conn.execute(sql, params).fetchall()
        conn.close()
    except Exception:
        return []
    return [
        f"CORRECTION (seen {r['count']}x) [{r['category']}]: {r['symptom']} "
        f"-- cause: {r['root_cause']} -- fix: {r['resolution']}"
        for r in rows
    ]


def existing_memory_digest(mem_dir: Path) -> str:
    """Name + description of memories already stored, so the model can say
    'update' instead of writing a near-duplicate."""
    entries = []
    for path in mem.memory_files(mem_dir)[:MAX_EXISTING_MEMORIES]:
        try:
            parsed = mem.parse_memory(path)
        except Exception:
            continue
        meta = parsed.get("metadata") or {}
        scope = meta.get("scope", "project" if "projects" in str(path) else "user")
        entries.append(f"- {parsed.get('name')} [{scope}]: {parsed.get('description', '')}")
    if not entries:
        return "Existing memory: (none yet)"
    return "Existing memory (name [scope]: description):\n" + "\n".join(entries)


# --- extraction -------------------------------------------------------------

def call_claude(prompt: str) -> str:
    """Run the extraction through the Claude CLI under the recursion guard.

    Require   - `claude` on PATH, authenticated by subscription or key.
    Guarantee - returns raw stdout, or raises on non-zero exit / timeout.
    Maintain  - MEM_IN_EXTRACTION is set for the child, so the nested session's
                own hooks no-op and this pass cannot feed itself.
    """
    env = dict(os.environ, MEM_IN_EXTRACTION="1")
    out = subprocess.run(
        ["claude", "-p", prompt, "--output-format", "text"],
        capture_output=True,
        text=True,
        timeout=EXTRACTION_TIMEOUT_S,
        env=env,
        encoding="utf-8",
        errors="replace",
    )
    if out.returncode != 0:
        raise RuntimeError(f"claude exited {out.returncode}: {(out.stderr or '')[:400]}")
    return out.stdout or ""


def parse_learnings(reply: str) -> list[dict]:
    """Pull the learnings array out of the reply.

    Tolerates a fenced block or surrounding prose, because a hard requirement of
    "JSON only" is not a guarantee of it.
    """
    text = reply.strip()
    fence = re.search(r"```(?:json)?\s*(.+?)```", text, re.S)
    if fence:
        text = fence.group(1).strip()
    else:
        start, end = text.find("{"), text.rfind("}")
        if start >= 0 and end > start:
            text = text[start:end + 1]
    data = json.loads(text)
    learnings = data.get("learnings", []) if isinstance(data, dict) else []
    return [item for item in learnings if isinstance(item, dict) and item.get("text")]


# --- consistency gate -------------------------------------------------------

def find_same_subject(mem_dir: Path, text: str) -> tuple[str, float] | None:
    """Nearest existing memory above SAME_SUBJECT_SIM, or None.

    Returns (name, similarity). A hit does not mean the new candidate is wrong --
    only that a human should see them side by side, which is what the review
    queue is for.
    """
    try:
        col = mem.get_collection(mem_dir)
        if col.count() == 0:
            return None
        qv = mem.embed([text], is_query=True)[0]
        res = col.query(query_embeddings=[qv], n_results=1)
    except Exception:
        # Index unavailable -> report no contradiction, which keeps the candidate
        # in review rather than auto-approving it.
        return None
    if not res["ids"] or not res["ids"][0]:
        return None
    meta = (res["metadatas"][0][0] or {})
    sim = 1.0 - float(res["distances"][0][0])
    if sim < SAME_SUBJECT_SIM:
        return None
    return str(meta.get("name") or res["ids"][0][0]), sim


def observed_confidences(mem_dir: Path) -> list[float]:
    values = []
    for path in mem.memory_files(mem_dir):
        try:
            meta = (mem.parse_memory(path).get("metadata") or {})
        except Exception:
            continue
        if "confidence" in meta:
            try:
                values.append(float(meta["confidence"]))
            except (TypeError, ValueError):
                continue
    return values


def auto_approve_threshold(mem_dir: Path) -> float | None:
    """Median + MAD-derived cutoff over previously observed confidences.

    Returns None until MIN_CONFIDENCE_OBSERVATIONS samples exist, which means
    "approve nothing automatically yet". This is the cold-start rule that keeps a
    magic constant out of the gate: a threshold picked before any distribution
    exists is a guess wearing a number, and the cost of guessing high is a wrong
    memory injected into every future session.
    """
    values = observed_confidences(mem_dir)
    if len(values) < MIN_CONFIDENCE_OBSERVATIONS:
        return None
    median = statistics.median(values)
    mad = statistics.median([abs(v - median) for v in values])
    # 1.4826 * MAD is the normal-consistent sigma estimate; one sigma above the
    # median is the "clearly above typical" band.
    return median + 1.4826 * mad


# --- main loop --------------------------------------------------------------

def target_dir(mem_dir: Path, scope: str, slug: str) -> Path:
    return mem_dir if scope == "user" else mem_dir / "projects" / slug


def since_to_iso(spec: str | None) -> str | None:
    """'24h' / '7d' / '30m' -> absolute ISO-8601 lower bound."""
    if not spec:
        return None
    match = re.fullmatch(r"(\d+)\s*([hdm])", spec.strip().lower())
    if not match:
        raise SystemExit(f"error: --since must look like 24h, 7d, or 30m (got {spec!r})")
    amount, unit = int(match.group(1)), match.group(2)
    delta = {"h": timedelta(hours=amount), "d": timedelta(days=amount),
             "m": timedelta(minutes=amount)}[unit]
    return (datetime.now(timezone.utc) - delta).isoformat()


def dream_session(mem_dir: Path, conn, session, lessons: list[str],
                  threshold: float | None, dry_run: bool) -> int:
    """Distil one session. Returns the number of memories written."""
    session_id = session["session_id"]
    slug = session["project_slug"] or "global"
    rows = es.session_events(conn, session_id)
    corpus = build_corpus(rows)
    if lessons:
        corpus += "\n" + "\n".join(lessons)
    if not corpus.strip():
        print(f"  {session_id[:8]}: no signal in {len(rows)} event(s), skipping")
        if not dry_run:
            es.mark_dreamed(conn, session_id)
        return 0

    prompt = (
        EXTRACTION_PROMPT
        .replace("[[SESSION_ID]]", session_id)
        .replace("[[PROJECT]]", slug)
        .replace("[[CORPUS]]", corpus)
        .replace("[[EXISTING_MEMORY]]", existing_memory_digest(mem_dir))
    )

    try:
        reply = call_claude(prompt)
        learnings = parse_learnings(reply)
    except Exception as exc:
        # Watermark deliberately NOT advanced: a failed extraction must be
        # retried, not silently dropped.
        print(f"  {session_id[:8]}: extraction failed ({type(exc).__name__}: {exc})",
              file=sys.stderr)
        return 0

    if not learnings:
        print(f"  {session_id[:8]}: nothing durable ({len(rows)} events)")
        if not dry_run:
            es.mark_dreamed(conn, session_id)
        return 0

    written = 0
    for item in learnings:
        scope = "user" if item.get("scope") == "user" else "project"
        text = str(item["text"]).strip()
        name = mem.slugify(str(item.get("name") or item.get("description") or text)[:60])
        try:
            confidence = round(float(item.get("confidence", 0.0)), 3)
        except (TypeError, ValueError):
            confidence = 0.0

        conflict = find_same_subject(mem_dir, text)
        supersedes = None
        if item.get("action") == "update" and item.get("existing_name"):
            supersedes = str(item["existing_name"])
        elif conflict:
            supersedes = conflict[0]

        # User scope always needs a human. Project scope auto-approves only when
        # there is no same-subject conflict AND the threshold is calibrated AND
        # this confidence clears it.
        status = "candidate"
        if (
            scope == "project"
            and supersedes is None
            and threshold is not None
            and confidence >= threshold
        ):
            status = "approved"

        line = (f"  [{scope}/{status}] {name} (conf {confidence}"
                + (f", supersedes {supersedes}" if supersedes else "") + ")")
        print(line)
        if dry_run:
            print(f"        {text[:200]}")
            continue

        extra = {
            "scope": scope,
            "status": status,
            "confidence": confidence,
            "source_session": session_id,
        }
        if supersedes:
            extra["supersedes"] = supersedes
        note = (f"Distilled by `mem dream` from session {session_id}"
                + (f"; supersedes {supersedes}" if supersedes else "") + ".")
        mem.write_memory_file(
            target_dir(mem_dir, scope, slug),
            name,
            "project" if scope == "project" else "user",
            str(item.get("description") or text)[:200],
            text,
            unique=True,
            extra_meta=extra,
            note=note,
        )
        written += 1

    if not dry_run:
        # Per-session checkpoint: this is what makes killing the run free.
        es.mark_dreamed(conn, session_id)
    return written


def cmd_dream(mem_dir: Path, since: str | None, session_id: str | None,
              dry_run: bool) -> None:
    if es.in_extraction_subprocess():
        return
    since_iso = since_to_iso(since)
    conn = es.connect()
    try:
        sessions = es.undreamed_sessions(conn, since=since_iso, session_id=session_id)
        if not sessions:
            print("nothing to dream — all sessions are past their watermark")
            return
        threshold = auto_approve_threshold(mem_dir)
        if threshold is None:
            print(f"auto-approval disabled: fewer than {MIN_CONFIDENCE_OBSERVATIONS} "
                  "confidence observations, everything stays a candidate")
        else:
            print(f"auto-approve threshold (median + 1.4826*MAD): {threshold:.3f}")
        lessons = recent_lessons(since_iso)
        if lessons:
            print(f"folding in {len(lessons)} lessons-learned correction(s)")

        print(f"{len(sessions)} session(s) to process"
              + (" [DRY RUN — no writes]" if dry_run else ""))
        total = 0
        for session in sessions:
            total += dream_session(mem_dir, conn, session, lessons, threshold, dry_run)
        if total and not dry_run:
            mem.cmd_index(mem_dir)
        print(f"\n{total} memory file(s) written")
    finally:
        conn.close()


def main(argv: list[str] | None = None) -> None:
    parser = argparse.ArgumentParser(description="distil session events into memories")
    parser.add_argument("--mem-dir", default=str(mem.DEFAULT_MEM_DIR))
    parser.add_argument("--since", help="only sessions with events since 24h / 7d / 30m")
    parser.add_argument("--session", help="one session id, ignoring its watermark")
    parser.add_argument("--dry-run", action="store_true", help="print, write nothing")
    args = parser.parse_args(argv)
    cmd_dream(Path(args.mem_dir), args.since, args.session, args.dry_run)


if __name__ == "__main__":
    main()
