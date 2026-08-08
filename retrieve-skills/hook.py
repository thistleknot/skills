#!/usr/bin/env python3
"""UserPromptSubmit hook: forwards the prompt to the local skill-router server
and emits accepted skills as additionalContext.

Purpose: the thin, zero-dependency edge of the RAG gate. All model work lives
in the server; this script must never add meaningful latency or break a prompt.

Preconditions: server listening on 127.0.0.1:$SKILL_ROUTER_PORT (default 8765);
registered under hooks.UserPromptSubmit in settings.json.

Failure modes: ANY error — bad stdin, server down, timeout, malformed response —
results in exit 0 with no stdout (fail-open: no skills injected, prompt
proceeds untouched). Errors are appended to hook.log next to this script.
"""
import json
import os
import sys
import time
import urllib.request

HERE = os.path.dirname(os.path.abspath(__file__))
LOG = os.path.join(HERE, "hook.log")


def _log(msg: str) -> None:
    try:
        with open(LOG, "a") as f:
            f.write(f"{time.strftime('%Y-%m-%dT%H:%M:%S')} {msg}\n")
    except OSError:
        pass


def build_context(skills: list) -> str:
    """Render accepted skills as an injection block.

    Guarantee: empty string when no skills; body mode wraps content in
    <skill> tags; pointer mode emits one line per skill with the path to read.
    """
    if not skills:
        return ""
    blocks = []
    for s in skills:
        if s.get("body"):
            blocks.append(f'<skill name="{s["name"]}">\n{s["body"]}\n</skill>')
        else:
            blocks.append(
                f"- {s['name']}: {s['description']}"
                f" (full instructions: read {s['path']})"
            )
    header = (
        "Skills selected by retrieval for this prompt "
        "(apply if relevant; ignore otherwise):"
    )
    return header + "\n" + "\n".join(blocks)


def main() -> int:
    try:
        payload = json.load(sys.stdin)
    except Exception:
        return 0
    prompt = (payload.get("prompt") or "").strip()
    if not prompt:
        return 0
    port = os.environ.get("SKILL_ROUTER_PORT", "8765")
    timeout = float(os.environ.get("SKILL_ROUTER_TIMEOUT", "15.0"))
    body = json.dumps(
        {"prompt": prompt, "session_id": payload.get("session_id")}
    ).encode()
    req = urllib.request.Request(
        f"http://127.0.0.1:{port}/route",
        data=body,
        headers={"Content-Type": "application/json"},
    )
    try:
        with urllib.request.urlopen(req, timeout=timeout) as r:
            resp = json.load(r)
    except Exception as e:
        _log(f"route failed (fail-open, no skills): {e}")
        return 0
    try:
        ctx = build_context(resp.get("skills", []))
        if ctx:
            print(
                json.dumps(
                    {
                        "hookSpecificOutput": {
                            "hookEventName": "UserPromptSubmit",
                            "additionalContext": ctx,
                        }
                    }
                )
            )
    except Exception as e:
        _log(f"render failed (fail-open): {e}")
    return 0


if __name__ == "__main__":
    sys.exit(main())
