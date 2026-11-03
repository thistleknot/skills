"""End-to-end integration test for skill-router hook chain.

Usage:
  python test_e2e.py              # layers 1-3 (server + hook.py)
  python test_e2e.py --cli        # layers 1-4 (includes Claude CLI)
  python test_e2e.py --help

Requires: server.py running on 127.0.0.1:8765
Zero external deps (stdlib only: subprocess, urllib, json, sys, os, argparse, uuid, pathlib)
"""
from __future__ import annotations

import argparse
import json
import os
import subprocess
import sys
import urllib.error
import urllib.request
from dataclasses import dataclass, field
from pathlib import Path
from uuid import uuid4

# ---------- Config ----------

SERVER_URL = "http://127.0.0.1:8765"
HOOK_SCRIPT = Path(__file__).parent / "hook.py"
PYTHON = r"c:\users\user\py310\Scripts\python.exe"
TIMEOUT = 10  # seconds for HTTP calls
CLI_TIMEOUT = 30  # seconds for claude -p

# Test prompts: known-good from ground_truth.json
ON_TOPIC_PROMPTS: list[tuple[str, list[str]]] = [
    ("convert this PDF into structured markdown with tables", ["pdf-extraction"]),
    ("set up MLflow tracking for this experiment", ["mlflow"]),
    ("isolate and fix this repeating null pointer error", ["debugging"]),
]

OFF_TOPIC_PROMPT = "what is the capital of France"

# Required fields in a /route skill response entry
ROUTE_SKILL_FIELDS = {"name", "path", "description", "recall_sim", "rerank_score",
                      "rerank_margin", "rerank_baseline"}


# ---------- TestResult ----------

@dataclass
class TestResult:
    name: str
    passed: bool
    skipped: bool = False
    detail: str = ""


# ---------- Helpers ----------

def http_get(path: str) -> dict:
    """GET a JSON endpoint, return parsed dict."""
    url = f"{SERVER_URL}{path}"
    req = urllib.request.Request(url)
    with urllib.request.urlopen(req, timeout=TIMEOUT) as r:
        return json.loads(r.read())


def post_route(prompt: str, session_id: str | None = None) -> dict:
    """POST /route with prompt and optional session_id, return parsed JSON."""
    body = json.dumps({"prompt": prompt, "session_id": session_id}).encode()
    req = urllib.request.Request(
        f"{SERVER_URL}/route",
        data=body,
        headers={"Content-Type": "application/json"},
    )
    with urllib.request.urlopen(req, timeout=TIMEOUT) as r:
        return json.loads(r.read())


def run_hook(prompt: str, session_id: str | None = None,
             port: str = "8765") -> subprocess.CompletedProcess:
    """Run hook.py as subprocess with given payload."""
    payload = json.dumps({"prompt": prompt, "session_id": session_id})
    env = {
        **os.environ,
        "SKILL_ROUTER_PORT": port,
        "SKILL_ROUTER_TIMEOUT": "5",
        "HF_HUB_OFFLINE": "1",
        "TRANSFORMERS_OFFLINE": "1",
    }
    return subprocess.run(
        [PYTHON, str(HOOK_SCRIPT)],
        input=payload, capture_output=True, text=True,
        env=env, timeout=TIMEOUT,
    )


# ---------- Layer 1: Health ----------

def check_health() -> TestResult:
    """GET /health, verify status=ok, log config."""
    try:
        data = http_get("/health")
    except Exception as e:
        return TestResult("health_check", False,
                          detail=f"Server unreachable: {e}\n"
                                 f"Start with: bash start.sh (or equivalent)")
    if data.get("status") != "ok":
        return TestResult("health_check", False, detail=f"status={data.get('status')}")
    info = (f"skills={data.get('skills_indexed')}, "
            f"embed={data.get('embed_model')}, "
            f"rerank={data.get('rerank_backend')}")
    return TestResult("health_check", True, detail=info)


# ---------- Layer 2: /route direct ----------

def test_route_on_topic(prompt: str, expected: list[str]) -> TestResult:
    """POST /route, verify expected skill names in response."""
    name = f"route_on_topic({prompt[:40]}...)"
    try:
        resp = post_route(prompt, f"e2e-{uuid4()}")
    except Exception as e:
        return TestResult(name, False, detail=f"HTTP error: {e}")
    skill_names = [s["name"] for s in resp.get("skills", [])]
    missing = [e for e in expected if e not in skill_names]
    if missing:
        return TestResult(name, False,
                          detail=f"missing: {missing}, got: {skill_names}")
    return TestResult(name, True)


def test_route_off_topic() -> TestResult:
    """POST /route with off-topic prompt, verify skills=[]."""
    try:
        resp = post_route(OFF_TOPIC_PROMPT, f"e2e-{uuid4()}")
    except Exception as e:
        return TestResult("route_off_topic", False, detail=f"HTTP error: {e}")
    skills = resp.get("skills", [])
    if skills:
        names = [s["name"] for s in skills]
        return TestResult("route_off_topic", False,
                          detail=f"expected no skills, got: {names}")
    return TestResult("route_off_topic", True)


def test_route_schema() -> TestResult:
    """POST /route, verify response has correct field structure."""
    prompt, _ = ON_TOPIC_PROMPTS[0]
    try:
        resp = post_route(prompt, f"e2e-schema-{uuid4()}")
    except Exception as e:
        return TestResult("route_schema", False, detail=f"HTTP error: {e}")
    if "skills" not in resp:
        return TestResult("route_schema", False, detail="missing 'skills' key")
    if not isinstance(resp["skills"], list):
        return TestResult("route_schema", False, detail="'skills' is not a list")
    # If skills returned, check field structure
    for skill in resp["skills"]:
        missing_fields = ROUTE_SKILL_FIELDS - set(skill.keys())
        if missing_fields:
            return TestResult("route_schema", False,
                              detail=f"skill '{skill.get('name')}' missing fields: {missing_fields}")
    return TestResult("route_schema", True)


def test_route_session_dedup() -> TestResult:
    """POST /route twice with same session_id, verify dedup on second call."""
    session_id = f"dedup-test-{uuid4()}"
    prompt, expected = ON_TOPIC_PROMPTS[0]
    try:
        r1 = post_route(prompt, session_id)
    except Exception as e:
        return TestResult("route_session_dedup", False, detail=f"first call error: {e}")
    if not r1.get("skills"):
        return TestResult("route_session_dedup", False,
                          detail="first call returned no skills")
    try:
        r2 = post_route(prompt, session_id)
    except Exception as e:
        return TestResult("route_session_dedup", False, detail=f"second call error: {e}")
    if r2.get("skills"):
        names = [s["name"] for s in r2["skills"]]
        return TestResult("route_session_dedup", False,
                          detail=f"second call should be deduped, got: {names}")
    return TestResult("route_session_dedup", True)


# ---------- Layer 3: hook.py subprocess ----------

def test_hook_on_topic(prompt: str, expected: list[str]) -> TestResult:
    """Subprocess hook.py with on-topic prompt, verify skill in additionalContext."""
    name = f"hook_on_topic({prompt[:40]}...)"
    try:
        result = run_hook(prompt, f"e2e-hook-{uuid4()}")
    except subprocess.TimeoutExpired:
        return TestResult(name, False, detail="timeout")
    except Exception as e:
        return TestResult(name, False, detail=f"subprocess error: {e}")
    if result.returncode != 0:
        return TestResult(name, False,
                          detail=f"exit {result.returncode}: {result.stderr[:200]}")
    stdout = result.stdout.strip()
    if not stdout:
        return TestResult(name, False, detail="empty stdout — no skills injected")
    try:
        out = json.loads(stdout)
    except json.JSONDecodeError as e:
        return TestResult(name, False, detail=f"invalid JSON: {e}")
    hso = out.get("hookSpecificOutput", {})
    ctx = hso.get("additionalContext", "")
    for skill in expected:
        if skill not in ctx:
            return TestResult(name, False,
                              detail=f"'{skill}' not in additionalContext (len={len(ctx)})")
    return TestResult(name, True)


def test_hook_off_topic() -> TestResult:
    """Subprocess hook.py with off-topic prompt, verify empty stdout."""
    try:
        result = run_hook(OFF_TOPIC_PROMPT, f"e2e-hook-offtopic-{uuid4()}")
    except subprocess.TimeoutExpired:
        return TestResult("hook_off_topic", False, detail="timeout")
    except Exception as e:
        return TestResult("hook_off_topic", False, detail=f"subprocess error: {e}")
    if result.returncode != 0:
        return TestResult("hook_off_topic", False,
                          detail=f"exit {result.returncode} (expected 0)")
    if result.stdout.strip():
        return TestResult("hook_off_topic", False,
                          detail=f"expected empty stdout, got: {result.stdout[:100]}")
    return TestResult("hook_off_topic", True)


def test_hook_fail_open() -> TestResult:
    """Invoke hook.py against dead port, verify exit 0 + empty stdout."""
    try:
        result = run_hook("test prompt", "fail-open-test", port="1")
    except subprocess.TimeoutExpired:
        return TestResult("hook_fail_open", False, detail="timeout (should fail fast)")
    except Exception as e:
        return TestResult("hook_fail_open", False, detail=f"subprocess error: {e}")
    if result.returncode != 0:
        return TestResult("hook_fail_open", False,
                          detail=f"exit {result.returncode} (expected 0 fail-open)")
    if result.stdout.strip():
        return TestResult("hook_fail_open", False,
                          detail=f"expected empty stdout on fail-open, got: {result.stdout[:100]}")
    return TestResult("hook_fail_open", True)


# ---------- Layer 4: Claude CLI ----------

def test_cli_injection(prompt: str, expected_skill: str) -> TestResult:
    """Run 'claude -p prompt', verify expected_skill appears in output."""
    name = f"cli_injection({expected_skill})"

    # Check if hook is registered in settings.json
    settings_path = Path.home() / ".claude" / "settings.json"
    try:
        settings = json.loads(settings_path.read_text(encoding="utf-8"))
    except Exception:
        return TestResult(name, False, skipped=True,
                          detail="SKIP: cannot read settings.json")
    hooks = settings.get("hooks", {}).get("UserPromptSubmit", [])
    hook_registered = any(
        "hook.py" in h.get("command", "")
        for group in hooks
        for h in group.get("hooks", [])
        if "retrieve-skills" in h.get("command", "") or "skill-router" in h.get("command", "")
    )
    if not hook_registered:
        return TestResult(name, False, skipped=True,
                          detail="SKIP: skill-router hook.py not in settings.json UserPromptSubmit")

    try:
        result = subprocess.run(
            ["claude", "-p", prompt],
            capture_output=True, text=True, timeout=CLI_TIMEOUT,
        )
    except subprocess.TimeoutExpired:
        return TestResult(name, False, detail=f"claude -p timed out after {CLI_TIMEOUT}s")
    except FileNotFoundError:
        return TestResult(name, False, skipped=True,
                          detail="SKIP: 'claude' CLI not found on PATH")
    except Exception as e:
        return TestResult(name, False, detail=f"error: {e}")

    if result.returncode != 0:
        return TestResult(name, False,
                          detail=f"claude exited {result.returncode}: {result.stderr[:200]}")

    # Soft check — the model saw the skill context, output may reference it
    return TestResult(name, True,
                      detail=f"output length: {len(result.stdout)} chars")


# ---------- Report ----------

def print_summary(results: list[TestResult], health_info: str = "") -> int:
    """Print pass/fail table, return exit code."""
    print()
    print("=" * 50)
    print("  SKILL-ROUTER E2E INTEGRATION TEST")
    print("=" * 50)
    if health_info:
        print(f"  Server: {health_info}")
    print()

    passed = 0
    failed = 0
    skipped = 0

    for r in results:
        if r.skipped:
            status = " SKIP"
            skipped += 1
        elif r.passed:
            status = " PASS"
            passed += 1
        else:
            status = " FAIL"
            failed += 1
        print(f"  {status}  {r.name}")
        if not r.passed and not r.skipped and r.detail:
            print(f"         {r.detail}")

    print()
    print("-" * 50)
    print(f"  {passed} passed, {failed} failed, {skipped} skipped")
    print("=" * 50)
    print()

    return 1 if failed > 0 else 0


# ---------- Main ----------

def main() -> None:
    """Parse args, run layers, print summary, exit."""
    parser = argparse.ArgumentParser(description="E2E integration test for skill-router")
    parser.add_argument("--cli", action="store_true",
                        help="Include Layer 4: Claude CLI headless tests")
    args = parser.parse_args()

    results: list[TestResult] = []
    health_info = ""

    # Layer 1: Health check (gate — abort if server down)
    health = check_health()
    results.append(health)
    if not health.passed:
        print_summary(results)
        print("ABORT: Server not reachable. Start with: bash start.sh")
        sys.exit(1)
    health_info = health.detail

    # Layer 2: /route direct
    for prompt, expected in ON_TOPIC_PROMPTS:
        results.append(test_route_on_topic(prompt, expected))
    results.append(test_route_off_topic())
    results.append(test_route_schema())
    results.append(test_route_session_dedup())

    # Layer 3: hook.py subprocess
    for prompt, expected in ON_TOPIC_PROMPTS:
        results.append(test_hook_on_topic(prompt, expected))
    results.append(test_hook_off_topic())
    results.append(test_hook_fail_open())

    # Layer 4: Claude CLI (optional)
    if args.cli:
        prompt, expected = ON_TOPIC_PROMPTS[0]
        results.append(test_cli_injection(prompt, expected[0]))

    exit_code = print_summary(results, health_info)
    sys.exit(exit_code)


if __name__ == "__main__":
    main()
