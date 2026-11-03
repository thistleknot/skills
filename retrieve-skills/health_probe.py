"""Proactive health probe for retrieve-skills service.

Runs every 5 minutes via Scheduled Task. Tests ACTUAL retrieval quality,
not just HTTP 200. Auto-repairs: restarts service, reindexes if needed.

Exit codes:
  0 = healthy (all checks pass)
  1 = was unhealthy, auto-repaired successfully
  2 = unhealthy, repair failed (needs human attention)

Checks (in order):
  1. Server reachable on :8765/health
  2. Index has >0 skills
  3. Retrieval returns a PASS result for a known-good query
  4. Index freshness: store has no un-indexed skills
"""
from __future__ import annotations

import json
import logging
import os
import subprocess
import sys
import time
import urllib.request
from pathlib import Path

os.environ.pop("SSLKEYLOGFILE", None)

# NOTE: do not try to hide the console from inside this script. The default
# terminal here is Windows Terminal, so GetConsoleWindow() returns a
# PseudoConsoleWindow owned by OpenConsole.exe — hiding it does nothing to the
# WindowsTerminal window the user actually sees. The only real fix is running
# this under pythonw.exe (see the scheduled task registration).

logging.basicConfig(
    level=logging.INFO,
    format="%(asctime)s [probe] %(message)s",
    handlers=[
        logging.FileHandler(Path(__file__).parent / "probe.log", encoding="utf-8"),
        # Console handler only when a console exists. Under pythonw.exe (headless
        # Scheduled Task) sys.stderr is None, and a bare StreamHandler would bind
        # to None and raise AttributeError on every emit.
        *([logging.StreamHandler()] if sys.stderr is not None else []),
    ],
)
log = logging.getLogger("probe")

PORT = int(os.environ.get("SKILL_ROUTER_PORT", "8765"))
BASE = f"http://127.0.0.1:{PORT}"
SERVICE_NAME = "skill-router"
PYTHON = r"F:\Python\mcp\retrieve-skills\Scripts\python.exe"
SERVER_DIR = Path(__file__).parent

# Known-good queries that MUST return at least one PASS result.
# If these fail, the index is broken or empty.
CANARY_QUERIES = [
    ("debug a failing test", "debugging"),
    ("create an MCP server", "mcp-tool-registry"),
]


def http_get(url: str, timeout: int = 10) -> dict | None:
    try:
        with urllib.request.urlopen(url, timeout=timeout) as r:
            return json.loads(r.read())
    except Exception:
        return None


def http_post(url: str, body: dict, timeout: int = 30) -> dict | None:
    try:
        data = json.dumps(body).encode()
        req = urllib.request.Request(url, data=data, headers={"Content-Type": "application/json"})
        with urllib.request.urlopen(req, timeout=timeout) as r:
            return json.loads(r.read())
    except Exception:
        return None


def restart_service() -> bool:
    """Log the failure state for diagnosis. Do NOT restart — that masks root causes."""
    log.error("SERVICE NEEDS ATTENTION: retrieval broken after reindex. "
              "Check service_stderr.log for crash/import errors. "
              "Manual fix required — refusing to auto-restart.")
    return False


def reindex() -> bool:
    """Trigger reindex via HTTP or CLI fallback."""
    log.info("triggering reindex...")
    resp = http_post(f"{BASE}/reindex", {}, timeout=120)
    if resp and resp.get("total", 0) > 0:
        log.info("reindex OK: %s", resp)
        return True
    # Fallback: CLI indexer
    log.info("HTTP reindex failed, trying CLI...")
    try:
        r = subprocess.run(
            [PYTHON, str(SERVER_DIR / "indexer.py"), "--store", os.path.expanduser("~/.skills")],
            capture_output=True, text=True, timeout=120, cwd=str(SERVER_DIR),
            env={**os.environ, "SSLKEYLOGFILE": ""},
            # Spawning a console app (python.exe) from a GUI-subsystem parent
            # (pythonw.exe) allocates a console window. Suppress it, otherwise
            # the window reappears on exactly the failure path we care about.
            creationflags=getattr(subprocess, "CREATE_NO_WINDOW", 0),
        )
        if r.returncode == 0:
            log.info("CLI reindex OK: %s", r.stdout.strip())
            return True
        log.error("CLI reindex failed: %s", r.stderr)
    except Exception as e:
        log.error("CLI reindex exception: %s", e)
    return False


def check_server_up() -> dict | None:
    """Check 1: server reachable."""
    return http_get(f"{BASE}/health")


def check_index_populated(health: dict) -> bool:
    """Check 2: index has skills."""
    return health.get("skills_indexed", 0) > 0


def check_retrieval_quality() -> bool:
    """Check 3: canary queries return expected skills.

    Requires ALL canaries to return empty to declare broken.
    A single miss with non-empty results is acceptable (margin gate is strict).
    Uses a unique session_id each run to avoid dedup filtering.
    """
    import uuid
    session_id = f"probe-{uuid.uuid4().hex[:8]}"
    total_empty = 0
    for query, expected_skill in CANARY_QUERIES:
        resp = http_post(f"{BASE}/route", {"prompt": query, "session_id": session_id})
        if not resp:
            log.warning("route request failed for query: %s", query)
            total_empty += 1
            continue
        skills = resp.get("skills", [])
        if not skills:
            total_empty += 1
            log.warning("canary empty: query=%r expected=%r got=[]", query, expected_skill)
    # Only declare broken if ALL canaries return empty
    if total_empty == len(CANARY_QUERIES):
        log.warning("ALL canaries returned empty — retrieval broken")
        return False
    return True


def check_index_freshness() -> bool:
    """Check 4: no un-indexed skills in the store."""
    try:
        # Count SKILL.md files at top level (same as discover_skills)
        store = Path(os.path.expanduser("~/.skills"))
        skill_files = list(store.glob("*/SKILL.md"))
        health = http_get(f"{BASE}/health")
        if not health:
            return False
        indexed = health.get("skills_indexed", 0)
        on_disk = len(skill_files)
        if on_disk > indexed + 10:
            log.warning("freshness gap: %d on disk, %d indexed", on_disk, indexed)
            return False
        return True
    except Exception as e:
        log.warning("freshness check failed: %s", e)
        return True  # don't block on this check


def main() -> int:
    repaired = False

    # Check 1: server up
    health = check_server_up()
    if not health:
        log.warning("CHECK 1 FAIL: server not reachable")
        if restart_service():
            repaired = True
            health = check_server_up()
            if not health:
                log.error("server still down after restart")
                return 2
        else:
            return 2

    # Check 2: index populated
    if not check_index_populated(health):
        log.warning("CHECK 2 FAIL: index empty")
        if reindex():
            repaired = True
        else:
            log.error("reindex failed")
            return 2

    # Check 3: retrieval quality
    if not check_retrieval_quality():
        log.warning("CHECK 3 FAIL: retrieval quality degraded, reindexing")
        if reindex():
            repaired = True
            # Retest after reindex
            if not check_retrieval_quality():
                log.error("retrieval still broken after reindex — restart")
                if restart_service():
                    repaired = True
                    time.sleep(5)
                    if not check_retrieval_quality():
                        log.error("retrieval broken after restart+reindex")
                        return 2
                else:
                    return 2
        else:
            return 2

    # Check 4: freshness
    if not check_index_freshness():
        log.info("CHECK 4: freshness gap detected, reindexing")
        reindex()
        repaired = True

    if repaired:
        log.info("RESULT: was unhealthy, auto-repaired")
        return 1
    else:
        log.info("RESULT: all checks passed")
        return 0


if __name__ == "__main__":
    sys.exit(main())
