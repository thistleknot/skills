---
name: tdd-agent
description: >
  Test-driven development as distinct agentic phases: Red (write failing tests),
  Green (implement until tests pass), Refactor (improve without breaking tests).
  Use when building features or fixing bugs where correctness is verifiable via
  tests. Covers phase contracts, test-first design, coverage gates, and harness
  integration. Complements validation (which covers general test design).
status: active
last_validated: 2026-04-28
---

# TDD Agent

## When to Use

Use this skill — not a write-then-test workflow — when:

- Correctness can be specified as executable assertions before the implementation exists
- You are implementing a new feature, fixing a known bug, or refactoring existing logic
- The acceptance criteria can be expressed as unit, integration, or property-based tests
- You want an agent-verifiable stop condition ("tests pass" is a binary gate)

Do **not** use when:
- Output is inherently subjective (UI aesthetics, prose quality) — use `evaluator-optimizer`
- The domain is too novel to specify tests before exploring the solution space
- You are in pure research / spike mode (write tests after the spike to lock in the result)

---

## Phase Contract

### Phase 1 — Red: Write Failing Tests

**Goal:** specify the behaviour before implementing it.

Contract:
```
Require: acceptance criteria exist (from spec, ticket, or docstring)
Guarantee: at least one test file exists; all new tests FAIL on current codebase
Maintain: no production code is changed in this phase
Assert: run test suite; confirm new tests are RED (failing), existing tests still GREEN
```

Rules:
- Write the simplest test that would fail for the right reason (not an import error)
- Cover the happy path first; add edge cases after Green
- Test names must describe the behaviour: `test_checkout_rejects_expired_card`, not `test_checkout_3`
- One assertion per test where possible — multiple assertions obscure which behaviour failed
- If you cannot write a failing test, the acceptance criteria are too vague → go back and clarify

### Phase 2 — Green: Implement Until Tests Pass

**Goal:** make the failing tests pass with the simplest correct implementation.

Contract:
```
Require: failing tests from Phase 1 exist and are understood
Guarantee: all Phase 1 tests are GREEN; no previously-passing tests are broken
Maintain: production code is written only to satisfy tests — no speculative additions
Assert: run full test suite; zero regressions; new tests pass
```

Rules:
- Write the **minimum** code that makes the tests pass — resist adding features not tested
- "Fake it till you make it" is acceptable in early iterations; the Refactor phase cleans it up
- If making a test pass requires breaking another test, stop — the design is conflicted → revisit

### Phase 3 — Refactor: Improve Without Breaking

**Goal:** improve code quality without changing observable behaviour.

Contract:
```
Require: all tests are GREEN after Phase 2
Guarantee: all tests remain GREEN after Refactor; no new tests are added in this phase
Maintain: semantics are unchanged; only structure, naming, and duplication change
Assert: run full test suite after every non-trivial refactor step
```

Rules:
- Remove duplication first (extract method / extract class)
- Improve naming second (replace temporal/positional names with intent names)
- Restructure third (move responsibility to the right owner)
- Run tests after each step — not just at the end of Refactor
- If a refactor reveals a new requirement, stop, exit Refactor, and start a new Red phase

---

## Phase Transition Protocol

```
[Red] → test_count_failing > 0 AND test_count_passing_unchanged
   ↓
[Green] → all_target_tests_passing AND regression_count == 0
   ↓
[Refactor] → no_new_tests_added AND all_tests_still_green
   ↓
[Done] or [new Red] for next behaviour
```

Never skip Red. Writing tests after the implementation defeats the design benefit of TDD:
tests written after tend to test what the code does, not what it should do.

---

## Test-First Design Benefit

Writing tests first forces a public API decision before implementation. If the test is
awkward to write, the API is awkward to use. This is signal, not noise — refactor the API
before implementing it.

Signs of a poor design discovered in Red:
- Test setup requires constructing many unrelated objects → high coupling
- Test must access private state to assert anything → wrong abstraction boundary
- Test is hard to name concisely → the behaviour being specified is incoherent

---

## Coverage Gate

A coverage gate is a binary pipeline gate, not a metric to optimize:

```python
COVERAGE_THRESHOLD = 0.80   # 80% line coverage minimum

def coverage_gate(coverage_report: CoverageReport) -> bool:
    """
    Returns True (pass) only when line coverage meets threshold.
    Blocks merge if False.
    """
    if coverage_report.line_coverage < COVERAGE_THRESHOLD:
        uncovered = coverage_report.uncovered_lines()
        raise CoverageGateFailure(
            f"Coverage {coverage_report.line_coverage:.0%} < {COVERAGE_THRESHOLD:.0%}. "
            f"Uncovered paths: {uncovered[:5]}"
        )
    return True
```

Coverage alone does not verify correctness. A test that calls code without asserting
anything yields 100% coverage and zero value. Coverage gate + assertion density together
are more meaningful.

---

## Anti-Gaming Protocol

AI agents can pass tests by **modifying the tests** rather than implementing the feature. This is not theoretical — it is a predictable optimization under context pressure.

Detection:
```python
# In the green_node, after implementation completes:
def detect_test_tampering(test_files: list[str], run_git_diff: Callable) -> bool:
    """
    Returns True (tampered) if any test file was modified during the Green phase.
    Require: baseline git SHA captured at start of Green phase.
    Guarantee: any test file touched in this phase is flagged, not silently accepted.
    """
    for path in test_files:
        diff = run_git_diff(path, from_sha=green_phase_start_sha)
        if diff:
            return True
    return False
```

Rules:
- Capture a git SHA at the **start of Green phase**
- After Green completes, diff all test files against that SHA
- If any test file was modified: halt, flag as tampered, return to Red with the tampering logged
- The structural validation sub-agent (see `agent-governance`) must have **no knowledge** of the implementation spec — it checks structural properties only (no hard-coded values, test coverage, schema validity)

## Agentic Harness Integration

Wire TDD as three harness nodes:

```
spec_node
    │ acceptance_criteria
    ▼
red_node          → writes test files; asserts new tests fail
    │ failing_test_paths
    ▼
green_node        → implements; asserts all new tests pass, no regressions
    │ passing_test_result
    ▼
refactor_node     → improves structure; asserts tests still green
    │ clean_test_result
    ▼
coverage_gate     → fails pipeline if coverage < threshold
```

Each node produces a structured result:

```python
class PhaseResult(BaseModel):
    phase: Literal["red", "green", "refactor"]
    tests_added: list[str]        # file paths
    tests_passing: int
    tests_failing: int
    regressions: int
    notes: str
```

On regression detection in `green_node`: halt, log the failing test, return to `red_node`
with the regression test as context.

---

## Failure Modes

| Symptom | Root cause | Fix |
|---|---|---|
| Tests pass immediately in Red | Tests are not actually asserting the new behaviour | Tighten assertions; verify failure before continuing |
| Green phase bloats with features | Agent adds speculative code | Constrain: implement only what makes the specific failing test pass |
| Refactor breaks tests | Refactor changed semantics | Revert to last green; break the refactor into smaller steps |
| Regression in Green | Implementation interacts with existing code | Add characterization test for the regression, then fix |
| Coverage gate always passes trivially | Tests call code but assert nothing | Add assertion density check (≥ 1 assert per test) |

---

## Evidence

- Devin TDD mode: +9.1 percentage points on SWE-bench Verified vs non-TDD mode (Cognition, 2025)
- Self-debugging arXiv:2304.05128: execution-feedback loop (overlaps Green phase) +12% on TransCoder
- Kent Beck, "Test-Driven Development: By Example" (2002): canonical Red-Green-Refactor origin

---

## Paired Feature Testing in Red-Green-Refactor

When adding extensible features (see `git-workflow/SKILL.md § Paired/Dimensional Feature Testing`), adapt the phase contract to test both base and variant:

### Red Phase: Failing Tests for Base + Variant

Instead of a single happy-path test, write two failing tests:

```python
def test_base_unit_available_immediately():
    """Base units render without prerequisites."""
    unit_a = Unit(name="Rifleman", tech_required=None)
    assert unit_a in available_units()

def test_tech_gated_unit_hidden_until_unlocked():
    """Tech-gated units only appear after tech is learned."""
    unit_b = Unit(name="LaserSoldier", tech_required="laser_tech")
    
    # Before tech: hidden
    assert unit_b not in available_units(techs=[])
    
    # After tech: visible
    assert unit_b in available_units(techs=["laser_tech"])
```

Both tests FAIL on current code. This is the signal that the feature does not yet exist.

### Green Phase: Implement Base + Variant Behavior

Implement both:
1. Base: Standard unit always available (simple case)
2. Variant: Check tech prerequisites before showing unit (gating logic)

Do not implement one without the other — both must pass together.

```python
def available_units(techs: list[str]) -> list[Unit]:
    """Return units available given current tech list."""
    return [u for u in ALL_UNITS if u.tech_required is None or u.tech_required in techs]
```

**Key:** this single implementation satisfies both tests. No duplication. The variant logic emerges from the data model.

### Refactor Phase: No Changes if Tests Already Pass

If Green passes and both tests are clear, Refactor may be minimal. The paired tests have already validated the design:
- Base behaviour works
- Variant behaviour works
- Gating logic is correct

Only refactor if: (1) code clarity needed, (2) duplication found, (3) naming could be clearer.

**Do NOT refactor to "optimize" if it risks the paired-test contract.**

---
- `validation` skill: complementary — covers test design methodology; this skill encodes lifecycle contract
<!-- consolidation:see-also:start -->
## See Also
[[synthetic-data]]  [[react-agent]]  [[model-size-reduction]]
<!-- consolidation:see-also:end -->
