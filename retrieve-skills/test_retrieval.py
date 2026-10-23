"""Retrieve-skills evaluation canaries and their deterministic contract.

| Stage | Mechanism | Contract | Req |
|---|---|---|---|
| DEFINE | Declare positive and negative retrieval cases | [mandatory] | R64 |
| GUARD | Reject a suite below three positive and two negative cases | [mandatory] | R64 |
| LIVE | Send each live case with a unique UUID-prefixed session identifier | [optional] | R65 |
| HANDOFF | Confirm every selected result names a readable non-empty SKILL.md | [mandatory] | R65 |

EARS guards:
- R1: When the deterministic contract imports this module, it shall not start a model or server.
- R2: When live evaluation is selected, every request shall receive a session identifier unique
  to that invocation and case.
- R3: When a selected result is accepted, its SKILL.md shall be a readable, non-empty file.

CLOSED:
- Model-judged scoring is excluded because the contract must be deterministic.
- The contract does not start the router, embeddings, or reranker; those belong to explicit
  offline or live evaluation.

Preconditions: The skill store and index are required only for offline/live evaluation.
Failure modes: An undersized case battery, repeated session identifier, unreachable live endpoint,
or unreadable selected SKILL.md causes evaluation failure.
"""
from __future__ import annotations

import argparse
import json
import os
import sys
import urllib.request
import uuid
from pathlib import Path

# Canary test cases: (query, expected_skill_name, description)
# These are the minimum-viable retrieval quality gates.
CANARY_TESTS = [
    ("I need systematic root-cause debugging for a failing test", "debugging",
     "debugging skill must surface for debug queries"),
    ("Register an MCP server and expose tools with FastMCP", "mcp-tool-registry",
     "MCP skill must surface for MCP server creation"),
    ("Form a falsifiable hypothesis, state what would disprove it, and test it", "hypothesis-forge",
     "hypothesis skill must surface for hypothesis-driven work"),
    ("Review my memory-bank files and organize my persistent notes", "memory-bank",
     "memory-bank skill must surface for memory management"),
    ("Draft a feature spec with EARS requirements and acceptance criteria", "spec",
     "spec skill must surface for spec/requirements work"),
]

# Negative tests: queries that should NOT return certain skills
NEGATIVE_TESTS = [
    ("what is the capital of France", "debugging",
     "off-topic query must NOT trigger debugging skill"),
    ("tell me a joke", "mcp-tool-registry",
     "off-topic query must NOT trigger MCP skill"),
]


def validate_case_coverage() -> list[str]:
    """Require the minimum deterministic retrieval-evaluation case mix.

    Returns:
        Coverage findings; an empty list means the canary set has the required mix.

    Require: CANARY_TESTS and NEGATIVE_TESTS are the declared evaluation cases.
    Guarantee: Fewer than three positive or two negative cases is a failure.
    Maintain: Case execution remains separate from coverage validation.
    Assert: The suite cannot silently shrink below its minimum coverage.
    """
    findings = []
    if len(CANARY_TESTS) < 3:
        findings.append(f"need at least 3 positive cases; found {len(CANARY_TESTS)}")
    if len(NEGATIVE_TESTS) < 2:
        findings.append(f"need at least 2 negative cases; found {len(NEGATIVE_TESTS)}")
    return findings


def validate_selected_skill_behavior(skill: dict) -> str | None:
    """Check that a selected skill can be handed to the caller for use.

    Args:
        skill: Retrieved skill record with its declared name and file path.

    Returns:
        A failure message when the selected instruction file is unusable, else None.

    Require: The record came from a positive trigger result.
    Guarantee: A positive selection points to a readable, non-empty SKILL.md.
    Maintain: The check reads the skill and never changes it.
    Assert: Retrieval cannot pass if the selected skill cannot be consumed.
    """
    path = Path(skill.get("path", ""))
    if path.name != "SKILL.md" or not path.is_file():
        return f"{skill.get('name', '<unknown>')}: selected skill path is not a SKILL.md file"
    if not path.read_text(encoding="utf-8", errors="replace").strip():
        return f"{skill.get('name', '<unknown>')}: selected SKILL.md is empty"
    return None


def test_live(base_url: str = "http://127.0.0.1:8765") -> tuple[int, int, list[str]]:
    """Evaluate the running router against the declared canary cases.

    Args:
        base_url: Router base URL selected by the ``--url`` CLI option.

    Returns:
        Counts of passed and failed cases plus human-readable failures.

    Require: The caller explicitly selects live evaluation and the endpoint is available.
    Guarantee: Each request receives an invocation-unique UUID-prefixed session identifier.
    Maintain: The function does not start or configure a server or model.
    Assert: Positive selections have a usable SKILL.md and negative exclusions hold.
    """
    passed = 0
    failed = 0
    failures = []
    run_id = uuid.uuid4().hex

    # Positive tests
    for case_index, (query, expected, desc) in enumerate(CANARY_TESTS):
        body = json.dumps(
            {"prompt": query, "session_id": f"{run_id}-positive-{case_index}"}
        ).encode()
        req = urllib.request.Request(
            f"{base_url}/route", data=body,
            headers={"Content-Type": "application/json"},
        )
        try:
            with urllib.request.urlopen(req, timeout=30) as r:
                resp = json.loads(r.read())
        except Exception as e:
            failures.append(f"FAIL {desc}: request error: {e}")
            failed += 1
            continue

        skills = [s["name"] for s in resp.get("skills", [])]
        selected = next((item for item in resp.get("skills", []) if item.get("name") == expected), None)
        if selected and not validate_selected_skill_behavior(selected):
            passed += 1
            print(f"  PASS: {desc} (got {skills})")
        else:
            failed += 1
            behavior_error = validate_selected_skill_behavior(selected) if selected else None
            detail = behavior_error or f"expected '{expected}' in {skills}"
            failures.append(f"FAIL {desc}: {detail}")
            print(f"  FAIL: {desc}: {detail}")

    # Negative tests
    for case_index, (query, must_not_have, desc) in enumerate(NEGATIVE_TESTS):
        body = json.dumps(
            {"prompt": query, "session_id": f"{run_id}-negative-{case_index}"}
        ).encode()
        req = urllib.request.Request(
            f"{base_url}/route", data=body,
            headers={"Content-Type": "application/json"},
        )
        try:
            with urllib.request.urlopen(req, timeout=30) as r:
                resp = json.loads(r.read())
        except Exception as e:
            failures.append(f"FAIL {desc}: request error: {e}")
            failed += 1
            continue

        skills = [s["name"] for s in resp.get("skills", [])]
        if must_not_have not in skills:
            passed += 1
            print(f"  PASS: {desc} (got {skills})")
        else:
            failed += 1
            failures.append(f"  FAIL: {desc}: '{must_not_have}' should NOT appear but did")
            print(f"  FAIL: {desc}: '{must_not_have}' incorrectly surfaced")

    return passed, failed, failures


def test_offline() -> tuple[int, int, list[str]]:
    """Evaluate routing directly against the local index without a running server.

    Returns:
        Counts of passed and failed cases plus human-readable failures.

    Require: ``index.db`` exists and contains indexed skills.
    Guarantee: The router is evaluated without HTTP or server startup.
    Maintain: The index and skill store are read-only.
    Assert: Positive selections have usable SKILL.md files and negative exclusions hold.
    """
    sys.path.insert(0, str(Path(__file__).parent))
    import model_backends as mb
    import router_core as rc

    db_path = Path(__file__).parent / "index.db"
    if not db_path.exists():
        return 0, 1, ["index.db not found — run indexer.py first"]

    index = rc.SkillIndex(str(db_path))
    skills, mat = index.vectors()
    if not skills:
        return 0, 1, ["index is empty"]

    embedder = mb.get_embedder()
    reranker = mb.get_reranker()
    cfg = rc.RouteConfig(top_k=34, rerank_keep=21, rerank_margin=1.5, max_accept=3)

    passed = 0
    failed = 0
    failures = []

    for query, expected, desc in CANARY_TESTS:
        result = rc.route(query, index, embedder, reranker, cfg)
        names = [r["name"] for r in result]
        selected = next((item for item in result if item.get("name") == expected), None)
        behavior_error = validate_selected_skill_behavior(selected) if selected else None
        if selected and not behavior_error:
            passed += 1
            print(f"  PASS: {desc} (got {names})")
        else:
            failed += 1
            detail = behavior_error or f"expected '{expected}', got {names}"
            failures.append(f"  FAIL: {desc}: {detail}")
            print(f"  FAIL: {desc}: {detail}")

    for query, must_not_have, desc in NEGATIVE_TESTS:
        result = rc.route(query, index, embedder, reranker, cfg)
        names = [r["name"] for r in result]
        if must_not_have not in names:
            passed += 1
            print(f"  PASS: {desc}")
        else:
            failed += 1
            failures.append(f"  FAIL: {desc}")
            print(f"  FAIL: {desc}")

    return passed, failed, failures


def main() -> None:
    """Run the selected offline or live evaluation mode from the command line.

    Require: Command-line arguments conform to the documented ``--live`` and ``--url`` options.
    Guarantee: Coverage is checked before either evaluation mode executes.
    Maintain: This entry point never starts a server or model process.
    Assert: A nonzero exit status represents coverage or evaluation failure.
    """
    parser = argparse.ArgumentParser()
    parser.add_argument("--live", action="store_true",
                        help="Test against running server (default: offline)")
    parser.add_argument("--url", default="http://127.0.0.1:8765",
                        help="Server URL for live mode")
    args = parser.parse_args()

    print(f"\n{'='*60}")
    print(f"  RETRIEVE-SKILLS UNIT TESTS ({'live' if args.live else 'offline'})")
    print(f"{'='*60}\n")

    coverage_findings = validate_case_coverage()
    if coverage_findings:
        print("Evaluation case coverage failed:")
        for finding in coverage_findings:
            print(f"  FAIL: {finding}")
        sys.exit(1)

    if args.live:
        passed, failed, failures = test_live(args.url)
    else:
        passed, failed, failures = test_offline()

    print(f"\n{'='*60}")
    print(f"  RESULTS: {passed} passed, {failed} failed")
    if failures:
        print(f"\n  FAILURES:")
        for f in failures:
            print(f"    {f}")
    print(f"{'='*60}\n")

    sys.exit(0 if failed == 0 else 1)


if __name__ == "__main__":
    main()
