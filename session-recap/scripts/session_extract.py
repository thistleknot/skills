#!/usr/bin/env python3
"""Extract + chunk a Claude Code session transcript for recursive summarization.

Usage:
  python session_extract.py locate  <session_id>
  python session_extract.py list    [--project <dir-name>] [--limit N]
  python session_extract.py extract <session_id> [--chunk-chars 60000]
                                    [--tool-chars 1500] [--out <dir>]
                                    [--keep-thinking]

`extract` writes chunk files (chunk-001.md ...) into an output directory and
prints a JSON manifest {session_id, source, chunks:[{path,chars,turns}], ...}.
"""
import argparse
import json
import os
import sys
import glob

PROJECTS = os.path.join(os.path.expanduser("~"), ".claude", "projects")


def find_session(session_id):
    hits = glob.glob(os.path.join(PROJECTS, "*", session_id + ".jsonl"))
    if not hits:
        # allow a bare path or a prefix of the id
        if os.path.isfile(session_id):
            return session_id
        hits = glob.glob(os.path.join(PROJECTS, "*", session_id + "*.jsonl"))
    if not hits:
        raise SystemExit("no session file found for %r under %s" % (session_id, PROJECTS))
    hits.sort(key=lambda p: os.path.getmtime(p), reverse=True)
    return hits[0]


def read_records(path):
    with open(path, encoding="utf-8", errors="replace") as fh:
        for line in fh:
            line = line.strip()
            if not line:
                continue
            try:
                yield json.loads(line)
            except ValueError:
                continue


def as_text(content):
    """Normalize a message .content into a list of (kind, text) pairs."""
    if isinstance(content, str):
        return [("text", content)]
    out = []
    for block in content or []:
        if not isinstance(block, dict):
            continue
        kind = block.get("type")
        if kind == "text":
            out.append(("text", block.get("text", "")))
        elif kind == "thinking":
            out.append(("thinking", block.get("thinking", "")))
        elif kind == "tool_use":
            inp = block.get("input", {})
            try:
                rendered = json.dumps(inp, ensure_ascii=False)
            except (TypeError, ValueError):
                rendered = str(inp)
            out.append(("tool_use", "%s %s" % (block.get("name", "?"), rendered)))
        elif kind == "tool_result":
            body = block.get("content")
            if isinstance(body, list):
                body = "\n".join(
                    b.get("text", "") for b in body if isinstance(b, dict)
                )
            out.append(("tool_result", body if isinstance(body, str) else str(body)))
    return out


def clip(text, limit):
    text = text or ""
    if limit and len(text) > limit:
        head = text[: int(limit * 0.7)]
        tail = text[-int(limit * 0.3):]
        return "%s\n...[%d chars elided]...\n%s" % (head, len(text) - limit, tail)
    return text


def build_turns(path, tool_chars, keep_thinking):
    """Yield markdown-ish turn strings in file order."""
    turns = []
    for rec in read_records(path):
        rtype = rec.get("type")
        if rtype not in ("user", "assistant"):
            continue
        if rec.get("isMeta"):
            continue
        msg = rec.get("message") or {}
        parts = []
        for kind, text in as_text(msg.get("content")):
            if kind == "thinking":
                if not keep_thinking or not text.strip():
                    continue
                parts.append("<thinking>%s</thinking>" % clip(text, tool_chars))
            elif kind == "tool_use":
                parts.append("[tool_use] %s" % clip(text, tool_chars))
            elif kind == "tool_result":
                parts.append("[tool_result] %s" % clip(text, tool_chars))
            elif text.strip():
                parts.append(text)
        if not parts:
            continue
        side = "USER" if rtype == "user" else "ASSISTANT"
        sidechain = " (subagent)" if rec.get("isSidechain") else ""
        stamp = (rec.get("timestamp") or "")[:19]
        turns.append(
            "### %s%s %s\n%s" % (side, sidechain, stamp, "\n".join(parts))
        )
    return turns


def chunk(turns, chunk_chars):
    chunks, cur, size = [], [], 0
    for turn in turns:
        if cur and size + len(turn) > chunk_chars:
            chunks.append(cur)
            cur, size = [], 0
        cur.append(turn)
        size += len(turn)
    if cur:
        chunks.append(cur)
    return chunks


def cmd_locate(args):
    print(find_session(args.session_id))


def cmd_list(args):
    pattern = os.path.join(PROJECTS, args.project or "*", "*.jsonl")
    files = sorted(glob.glob(pattern), key=os.path.getmtime, reverse=True)
    for path in files[: args.limit]:
        print("%12d  %s  %s" % (
            os.path.getsize(path),
            os.path.basename(os.path.dirname(path)),
            os.path.splitext(os.path.basename(path))[0],
        ))


def cmd_extract(args):
    path = find_session(args.session_id)
    sid = os.path.splitext(os.path.basename(path))[0]
    turns = build_turns(path, args.tool_chars, args.keep_thinking)
    groups = chunk(turns, args.chunk_chars)

    out_dir = args.out or os.path.join(
        os.path.expanduser("~"), ".claude", "recap", sid
    )
    os.makedirs(out_dir, exist_ok=True)
    for stale in glob.glob(os.path.join(out_dir, "chunk-*.md")):
        os.remove(stale)

    manifest = {
        "session_id": sid,
        "source": path,
        "project": os.path.basename(os.path.dirname(path)),
        "total_turns": len(turns),
        "total_chars": sum(len(t) for t in turns),
        "out_dir": out_dir,
        "chunks": [],
    }
    for i, group in enumerate(groups, 1):
        body = "\n\n".join(group)
        cpath = os.path.join(out_dir, "chunk-%03d.md" % i)
        with open(cpath, "w", encoding="utf-8") as fh:
            fh.write("# %s chunk %d/%d\n\n%s\n" % (sid, i, len(groups), body))
        manifest["chunks"].append(
            {"path": cpath, "chars": len(body), "turns": len(group)}
        )
    mpath = os.path.join(out_dir, "manifest.json")
    with open(mpath, "w", encoding="utf-8") as fh:
        json.dump(manifest, fh, indent=2)
    print(json.dumps(manifest, indent=2))


def main(argv=None):
    ap = argparse.ArgumentParser(description=__doc__)
    sub = ap.add_subparsers(dest="cmd", required=True)

    p = sub.add_parser("locate")
    p.add_argument("session_id")
    p.set_defaults(func=cmd_locate)

    p = sub.add_parser("list")
    p.add_argument("--project")
    p.add_argument("--limit", type=int, default=20)
    p.set_defaults(func=cmd_list)

    p = sub.add_parser("extract")
    p.add_argument("session_id")
    p.add_argument("--chunk-chars", type=int, default=60000)
    p.add_argument("--tool-chars", type=int, default=1500)
    p.add_argument("--out")
    p.add_argument("--keep-thinking", action="store_true")
    p.set_defaults(func=cmd_extract)

    args = ap.parse_args(argv)
    return args.func(args)


if __name__ == "__main__":
    sys.exit(main())
