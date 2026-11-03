#!/usr/bin/env python3
"""Rebuild the event store from Claude Code transcripts.

Thesis
------
This is what demotes `events.sqlite3` from primary data to a **cache**. Before this
existed, an event not captured by the hook was gone forever, which made the store the
one irreplaceable thing in a memory architecture whose whole premise is that raw tiers
are disposable and derived tiers are regenerable. Chroma rebuilds from markdown via
`mem index`; the event store now rebuilds from transcripts via `mem backfill`. Nothing
in the stack is load-bearing on its own persistence any more.

The consequence worth stating plainly: an empty or deleted store is no longer a data
loss event, it is a cache miss.

Source of truth
---------------
`~/.claude/projects/<slug>/<session_id>.jsonl` -- one JSON record per line, written by
Claude Code itself. Records used:

| Transcript record | Reconstructed event |
|---|---|
| `type=user`, string content | `UserPromptSubmit` (prompt) |
| `type=assistant`, `tool_use` block | `PreToolUse` (tool_name, tool_use_id, tool_input, subagent_type) |
| `type=user`, `tool_result` block | `PostToolUse` (joined to its call by tool_use_id) |
| `type=assistant`, `text` block | `Stop` (last_assistant_message) |

`tool_use_id` is what makes the join possible, and is the column this pass needed that
the original schema lacked -- a result carries no tool name, only the id of the call it
answers.

Design decisions
----------------
- **Identity comes from the transcript's own `uuid`**, not a payload hash. Re-running
  the backfill is therefore a no-op rather than a duplicate, and two backfills of the
  same transcript agree exactly.
- **A session that already has hook-captured events is skipped** unless `--overwrite`.
  Hook rows and transcript rows describe the same events under different id schemes, so
  mixing them in one session would double-count evidence. Rebuild replaces a session
  wholesale; it never interleaves.
- **`origin` distinguishes the two.** `hook` rows were captured live; `transcript` rows
  were reconstructed. Anything reasoning about completeness needs to tell them apart,
  because reconstruction cannot recover what the transcript does not record.

What reconstruction cannot recover
----------------------------------
`SessionStart`/`SessionEnd` and their `source` (startup vs clear vs compact),
`stop_hook_active`, and the exact hook-payload hashes. Tool *content* is fully present.
So a rebuilt session is complete for distillation purposes and lossy for lifecycle
forensics -- which is the right trade, since distillation is what reads this.

Failure modes
-------------
- Transcript dir absent -> reports zero candidates, exits 0.
- Malformed line -> skipped, counted, and reported rather than aborting the file.
- Session in the store but no transcript on disk -> left alone; this pass never deletes
  what it cannot rebuild.
"""

from __future__ import annotations

import argparse
import json
import sys
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parent))

import events_store as es  # noqa: E402

TRANSCRIPT_ROOT = Path.home() / ".claude" / "projects"


def transcripts() -> dict[str, Path]:
    """session_id -> newest transcript file for it.

    A session id can appear under more than one project dir (the cwd moved); the most
    recently modified file is the one that saw the end of the session.
    """
    found: dict[str, Path] = {}
    if not TRANSCRIPT_ROOT.is_dir():
        return found
    for path in TRANSCRIPT_ROOT.glob("*/*.jsonl"):
        sid = path.stem
        prior = found.get(sid)
        if prior is None or path.stat().st_mtime > prior.stat().st_mtime:
            found[sid] = path
    return found


def _text_of(content) -> str | None:
    """Flatten a tool_result content payload to text."""
    if content is None:
        return None
    if isinstance(content, str):
        return content
    if isinstance(content, list):
        parts = []
        for block in content:
            if isinstance(block, dict) and block.get("type") == "text":
                parts.append(str(block.get("text") or ""))
            elif isinstance(block, dict):
                parts.append(json.dumps(block, default=str))
            else:
                parts.append(str(block))
        return "\n".join(p for p in parts if p)
    return json.dumps(content, default=str)


def parse_transcript(path: Path) -> tuple[list[dict], int]:
    """Reconstruct ordered event dicts from one transcript. Returns (events, skipped)."""
    events: list[dict] = []
    tool_names: dict[str, str] = {}   # tool_use_id -> tool_name, for the result join
    delegations: dict[str, str | None] = {}  # tool_use_id -> subagent_type
    skipped = 0

    with open(path, "r", encoding="utf-8", errors="replace") as handle:
        for line in handle:
            line = line.strip()
            if not line:
                continue
            try:
                rec = json.loads(line)
            except json.JSONDecodeError:
                skipped += 1
                continue
            if not isinstance(rec, dict):
                skipped += 1
                continue

            kind = rec.get("type")
            if kind not in ("user", "assistant"):
                continue
            uuid = rec.get("uuid")
            if not uuid:
                continue

            base = {
                "uuid": uuid,
                "timestamp": rec.get("timestamp"),
                "cwd": rec.get("cwd"),
                "git_branch": rec.get("gitBranch"),
                "is_sidechain": 1 if rec.get("isSidechain") else 0,
            }
            message = rec.get("message") or {}
            content = message.get("content")
            model = message.get("model")

            if kind == "user" and isinstance(content, str):
                if content.strip():
                    events.append({**base, "event_name": "UserPromptSubmit",
                                   "prompt": content})
                continue

            if not isinstance(content, list):
                continue

            for index, block in enumerate(content):
                if not isinstance(block, dict):
                    continue
                btype = block.get("type")

                if btype == "tool_use":
                    tool_id = block.get("id")
                    name = block.get("name")
                    if tool_id and name:
                        tool_names[str(tool_id)] = str(name)
                    if tool_id and name in es.DELEGATION_TOOLS:
                        delegations[str(tool_id)] = es.subagent_type_of(
                            name, block.get("input"))
                    events.append({
                        **base,
                        # A single assistant message can hold several tool_use blocks,
                        # so the record uuid alone is not unique -- index disambiguates.
                        "uuid": f"{uuid}#{index}",
                        "event_name": "PreToolUse",
                        "tool_name": name,
                        "tool_use_id": tool_id,
                        "subagent_type": es.subagent_type_of(name, block.get("input")),
                        "tool_input": json.dumps(block.get("input"), default=str)
                        if block.get("input") is not None else None,
                        "model": model,
                    })

                elif btype == "tool_result":
                    tool_id = str(block.get("tool_use_id") or "")
                    body = _text_of(block.get("content"))
                    is_error = bool(block.get("is_error"))
                    events.append({
                        **base,
                        "uuid": f"{uuid}#{index}",
                        "event_name": "PostToolUse",
                        "tool_name": tool_names.get(tool_id),
                        "tool_use_id": tool_id or None,
                        # Carried from the matching tool_use: a result names neither the
                        # tool nor the subagent, only the id of the call it answers.
                        "subagent_type": delegations.get(tool_id),
                        "tool_response": None if is_error else body,
                        "tool_error": body if is_error else None,
                    })

                elif btype == "text" and kind == "assistant":
                    text = str(block.get("text") or "")
                    if text.strip():
                        events.append({
                            **base,
                            "uuid": f"{uuid}#{index}",
                            "event_name": "Stop",
                            "last_assistant_message": text,
                            "model": model,
                        })

    events.sort(key=lambda e: (e.get("timestamp") or "", e["uuid"]))
    return events, skipped


def write_session(conn, session_id: str, path: Path, events: list[dict],
                  dry_run: bool) -> int:
    """Insert a reconstructed session as one contiguous, chained run."""
    slug = es.project_slug(str(events[0].get("cwd")) if events else None)
    if dry_run:
        return len(events)

    with conn:
        conn.execute(
            """
            INSERT INTO sessions (session_id, project_slug, cwd, started_at)
            VALUES (?, ?, ?, ?)
            ON CONFLICT(session_id) DO UPDATE SET
                project_slug = COALESCE(excluded.project_slug, sessions.project_slug),
                cwd          = COALESCE(excluded.cwd, sessions.cwd)
            """,
            (session_id, slug, events[0].get("cwd"), events[0].get("timestamp")),
        )
        prev_id = None
        for seq, event in enumerate(events):
            event_id = f"{session_id}:transcript:{event['uuid']}"
            conn.execute(
                """
                INSERT OR IGNORE INTO events (
                    event_id, session_id, prev_event_id, seq, event_name, timestamp,
                    project_slug, tool_name, tool_use_id, subagent_type, tool_input,
                    tool_response, tool_error, prompt, last_assistant_message, model,
                    source, git_branch, is_sidechain, origin
                ) VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?)
                """,
                (
                    event_id, session_id, prev_id, seq,
                    event["event_name"], event.get("timestamp") or "",
                    None if event["event_name"] in es.PROJECT_NEUTRAL_EVENTS else slug,
                    event.get("tool_name"), event.get("tool_use_id"),
                    event.get("subagent_type"),
                    es._truncate(event.get("tool_input")),
                    es._truncate(event.get("tool_response")),
                    es._truncate(event.get("tool_error")),
                    es._truncate(event.get("prompt")),
                    es._truncate(event.get("last_assistant_message")),
                    event.get("model"), None,
                    event.get("git_branch"), event.get("is_sidechain"),
                    "transcript",
                ),
            )
            prev_id = event_id
    return len(events)


def cmd_backfill(session_id: str | None, overwrite: bool, dry_run: bool,
                 limit: int | None) -> None:
    available = transcripts()
    if not available:
        print(f"no transcripts found under {TRANSCRIPT_ROOT}")
        return

    conn = es.connect()
    try:
        counts = {
            row["session_id"]: (row["n"], row["origin"])
            for row in conn.execute(
                "SELECT session_id, COUNT(*) AS n, MIN(origin) AS origin "
                "FROM events GROUP BY session_id"
            )
        }

        targets = [session_id] if session_id else sorted(available)
        if session_id and session_id not in available:
            print(f"no transcript on disk for session {session_id}")
            return

        planned, skipped_existing = [], 0
        for sid in targets:
            existing, _origin = counts.get(sid, (0, None))
            if existing and not overwrite:
                skipped_existing += 1
                continue
            planned.append(sid)
        if limit:
            planned = planned[:limit]

        print(f"{len(available)} transcript(s) on disk; {skipped_existing} session(s) "
              f"already populated (use --overwrite to rebuild those); "
              f"{len(planned)} to process"
              + (" [DRY RUN]" if dry_run else ""))

        total_events, total_skipped_lines, rebuilt = 0, 0, 0
        for sid in planned:
            events, bad_lines = parse_transcript(available[sid])
            total_skipped_lines += bad_lines
            if not events:
                continue
            if overwrite and not dry_run:
                with conn:
                    conn.execute("DELETE FROM events WHERE session_id = ?", (sid,))
            written = write_session(conn, sid, available[sid], events, dry_run)
            total_events += written
            rebuilt += 1
            print(f"  {sid[:8]}  {written:5d} events  "
                  f"{available[sid].parent.name[:34]}")

        print(f"\n{rebuilt} session(s), {total_events} events"
              + (" (nothing written)" if dry_run else " written"))
        if total_skipped_lines:
            print(f"{total_skipped_lines} unparseable transcript line(s) skipped")
    finally:
        conn.close()


def main(argv: list[str] | None = None) -> None:
    parser = argparse.ArgumentParser(
        description="rebuild the event store from Claude Code transcripts")
    parser.add_argument("--session", default=None, help="one session id")
    parser.add_argument("--overwrite", action="store_true",
                        help="rebuild sessions that already have events")
    parser.add_argument("--dry-run", action="store_true")
    parser.add_argument("--limit", type=int, default=None,
                        help="process at most N sessions")
    args = parser.parse_args(argv)
    cmd_backfill(args.session, args.overwrite, args.dry_run, args.limit)


if __name__ == "__main__":
    main()
