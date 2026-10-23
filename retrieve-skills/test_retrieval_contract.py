"""Deterministic ownership contract for the retrieve-skills canary suite.

| Stage | Mechanism | Contract | Req |
|---|---|---|---|
| LOAD | Import sibling canaries without starting router dependencies | [mandatory] | R64, R65 |
| GUARD | Exercise the minimum case-count guard | [mandatory] | R64 |
| HANDOFF | Require selected SKILL.md paths to be readable and non-empty | [mandatory] | R65 |
| ISOLATE | Capture mocked live request session identifiers | [mandatory] | R65 |

EARS guards:
- R1: Contract tests shall import the sibling canary module rather than a home-directory path.
- R2: Contract tests shall use mocked HTTP and shall not start a server or model.
- R3: A live invocation shall use unique UUID-prefixed session identifiers for every case.

CLOSED:
- Live retrieval quality is excluded from this module because it depends on the external router.

Preconditions: The sibling ``test_retrieval.py`` module exists.
Failure modes: Missing case coverage, unusable selected skill instructions, TLS environment mutation,
or repeated session identifiers fail the deterministic suite.
"""
from __future__ import annotations

import importlib.util
import json
import os
import sys
import uuid
from pathlib import Path


CANARY_FILE = Path(__file__).with_name("test_retrieval.py")


def load_canaries():
    """Load a fresh sibling canary module without relying on a user-home path.

    Returns:
        The imported canary module.

    Require: ``test_retrieval.py`` is adjacent to this contract test.
    Guarantee: The module receives a unique import name and executes only its import-time code.
    Maintain: The loader does not start retrieval services or models.
    Assert: A missing module spec fails immediately.
    """
    module_name = f"retrieve_skill_canaries_{uuid.uuid4().hex}"
    spec = importlib.util.spec_from_file_location(module_name, CANARY_FILE)
    assert spec and spec.loader
    module = importlib.util.module_from_spec(spec)
    sys.modules[module_name] = module
    spec.loader.exec_module(module)
    return module


CANARIES = load_canaries()


def test_canary_import_preserves_sslkeylogfile_environment(monkeypatch):
    """Ensure importing evaluation helpers has no TLS environment side effect.

    Args:
        monkeypatch: Pytest fixture that restores environment state after the test.

    Require: A fresh canary import is possible from this sibling directory.
    Guarantee: ``SSLKEYLOGFILE`` retains its caller-provided value.
    Maintain: No router, model, or live request is started.
    Assert: Importing helpers is safe for callers that manage TLS diagnostics.
    """
    monkeypatch.setenv("SSLKEYLOGFILE", "contract-sentinel")

    load_canaries()

    assert os.environ["SSLKEYLOGFILE"] == "contract-sentinel"


def test_canary_suite_keeps_minimum_positive_and_negative_case_counts():
    """Prevent silent reduction below the adopted trigger-evaluation floor.

    Require: The canonical canary module is importable.
    Guarantee: At least three positive and two negative cases are required.
    Maintain: This test does not run retrieval models.
    Assert: The current case inventory satisfies its own coverage guard.
    """
    assert len(CANARIES.CANARY_TESTS) >= 3
    assert len(CANARIES.NEGATIVE_TESTS) >= 2
    assert CANARIES.validate_case_coverage() == []


def test_canary_coverage_guard_fails_when_either_case_family_shrinks(monkeypatch):
    """Prove that coverage enforcement rejects a reduced positive/negative battery.

    Args:
        monkeypatch: Pytest fixture that restores the canonical case lists.

    Require: The imported canary module exposes its two case collections.
    Guarantee: Undersized collections yield separate findings.
    Maintain: Original cases are restored after the test.
    Assert: Both minimum thresholds are actively enforced.
    """
    monkeypatch.setattr(CANARIES, "CANARY_TESTS", CANARIES.CANARY_TESTS[:2])
    monkeypatch.setattr(CANARIES, "NEGATIVE_TESTS", CANARIES.NEGATIVE_TESTS[:1])

    findings = CANARIES.validate_case_coverage()

    assert len(findings) == 2
    assert any("at least 3 positive" in finding for finding in findings)
    assert any("at least 2 negative" in finding for finding in findings)


def test_selected_skill_behavior_requires_readable_nonempty_skill_markdown(tmp_path: Path):
    """Check the deterministic behavioral handoff for a selected skill.

    Args:
        tmp_path: Pytest-owned fixture directory.

    Require: The behavior helper accepts a result record with a path.
    Guarantee: Readable non-empty SKILL.md passes; empty, absent, or wrong targets fail.
    Maintain: Only fixture files are written.
    Assert: The check is content-independent apart from non-emptiness.
    """
    skill_file = tmp_path / "sample" / "SKILL.md"
    skill_file.parent.mkdir()
    skill_file.write_text(
        "---\nname: sample\ndescription: Sample skill.\n---\nDo the task.\n",
        encoding="utf-8",
    )

    assert CANARIES.validate_selected_skill_behavior(
        {"name": "sample", "path": str(skill_file)}
    ) is None
    skill_file.write_text("", encoding="utf-8")
    assert "is empty" in CANARIES.validate_selected_skill_behavior(
        {"name": "sample", "path": str(skill_file)}
    )
    assert "not a SKILL.md" in CANARIES.validate_selected_skill_behavior(
        {"name": "sample", "path": str(tmp_path)}
    )


def test_live_requests_use_unique_uuid_prefixed_session_identifiers(monkeypatch):
    """Confirm mocked live evaluation isolates every case and invocation.

    Args:
        monkeypatch: Pytest fixture used to replace outbound HTTP.

    Require: The canary module exposes its live evaluator.
    Guarantee: Each case identifier is unique and each invocation has a distinct UUID prefix.
    Maintain: The test performs no network I/O, model loading, or server startup.
    Assert: Static or reused session identifiers fail this contract.
    """
    captured: list[str] = []

    class FakeResponse:
        """Minimal context-managed HTTP response used by the deterministic contract.

        Require: The mocked live evaluator needs an object compatible with ``urlopen`` output.
        Guarantee: The response yields a fixed empty skill collection.
        Maintain: No socket, model, or server resource exists behind this fixture.
        Assert: Unexpected caller exceptions propagate through the context manager.
        """

        def __enter__(self):
            """Return the fixture response within the request context.

            Require: The caller enters the mocked ``urlopen`` response context.
            Guarantee: The current fixture response becomes the context value.
            Maintain: The fixture has no external resources to acquire.
            Assert: Context entry cannot trigger network I/O.
            """
            return self

        def __exit__(self, exc_type, exc_value, traceback):
            """Propagate any unexpected exception from the caller.

            Require: The mocked response context has completed.
            Guarantee: Returning false preserves any caller exception.
            Maintain: The fixture has no external resources to release.
            Assert: This method never suppresses failures.
            """
            return False

        def read(self):
            """Return an empty router result without contacting a server.

            Require: The evaluator requests the mocked response payload.
            Guarantee: The payload parses as a router response with no skills.
            Maintain: No external endpoint is contacted.
            Assert: The response shape remains valid JSON bytes.
            """
            return b'{"skills": []}'

    def fake_urlopen(request, timeout):
        """Capture the request session identifier and return a local fixture response.

        Require: The evaluator supplies a JSON request body containing ``session_id``.
        Guarantee: The identifier is recorded and a deterministic response is returned.
        Maintain: The timeout is ignored because no network operation occurs.
        Assert: A missing session identifier raises during test execution.
        """
        del timeout
        captured.append(json.loads(request.data)["session_id"])
        return FakeResponse()

    monkeypatch.setattr(CANARIES.urllib.request, "urlopen", fake_urlopen)

    CANARIES.test_live("http://contract.invalid")
    first_run = captured[:]
    CANARIES.test_live("http://contract.invalid")
    second_run = captured[len(first_run):]

    expected_count = len(CANARIES.CANARY_TESTS) + len(CANARIES.NEGATIVE_TESTS)
    assert len(first_run) == expected_count
    assert len(second_run) == expected_count
    assert len(set(first_run)) == expected_count
    assert len(set(second_run)) == expected_count
    first_prefixes = {session_id.rsplit("-", 2)[0] for session_id in first_run}
    second_prefixes = {session_id.rsplit("-", 2)[0] for session_id in second_run}
    assert len(first_prefixes) == 1
    assert len(second_prefixes) == 1
    assert first_prefixes.isdisjoint(second_prefixes)
    uuid.UUID(hex=next(iter(first_prefixes)))
    uuid.UUID(hex=next(iter(second_prefixes)))
