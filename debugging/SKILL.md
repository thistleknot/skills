---
name: debugging
description: Debugging protocol for isolating and fixing errors. Use when an error is present, a fix is confirmed broken, or the same class of error is repeating. Covers the Iron Law, 5-phase root-cause protocol, isolation, salience tiers, diagnostic strategy, autonomous iteration, and conversation state tracking.
status: active
last_validated: 2026-04-28
supersedes: []
validation_method: session
---
# Debugging

## Iron Law

**NO FIXES WITHOUT ROOT CAUSE INVESTIGATION FIRST.**

Fixing symptoms creates whack-a-mole debugging. Every fix that doesn't address root cause makes the next bug harder to find. Find the root cause, then fix it.

Red flags that mean you're guessing:
- "Quick fix for now" — there is no "for now." Fix it right or escalate.
- Proposing a fix before tracing data flow.
- Each fix reveals a new problem elsewhere — wrong layer, not wrong code.

## Stance
Objective third-party observer. What is the objective? What contributes to unexpected results? Think through the code's original intent before suggesting changes.

## #1 Rule
If the same class of error repeats: stop patching, revisit the approach. Don't fix symptoms — fix the core issue. If quick fixes aren't working, pivot to an alternative rather than chasing the stray problem endlessly.

## Isolation Protocol
```
Zoom out → Extract (modularize) → Unit test → Zoom in → Re-apply
```
- Separate the problem; test under controlled conditions before running the full pipeline
- Never debug through an entire pipeline between fixes
- Test each layer with confirmed working artifacts (checkpointed)
- Speed runs over smoke tests — 10 records max for training loops
- MVP regression: remove errors until back to working state, then re-add incrementally

## Salience Tiers
| Priority | Target |
|---|---|
| High | Code directly touching the error line |
| Medium | Code in the execution path to the error |
| Low | Code sharing variables with the error path |
| Ignore | Code with no logical connection to the error |

## Diagnostic Strategy
1. Trace errors from the line numbers called out
2. Survey the situation — what worked, what didn't
3. Add diagnostic prints near the error; verify inputs, schema, initial conditions
4. Identify expected vs actual (examine inputs)
5. **False dichotomy check:** are we forcing a binary? If so, expand the output space

## Conversation State
- Track: same error *type* across turns vs different error *location*
- Independent events are separate base facts — do not presume causation because they appear together
- Look for common underlying conditions that enabled both

## Autonomous Iteration
Run → observe → fix → rerun without asking. Surface only true blockers:
- Missing credentials
- Ambiguous requirement
- Scope-changing architectural decision

Syntax, imports, schema, logic bugs are yours to resolve.

## Error Schema Checklist
Rogue n/a · duplicate keys · missing fields · wrong joins · off-by-one bounds · type mismatches · duplicate function definitions

## 5-Phase Root Cause Protocol

### Phase 1 — Gather Evidence
Collect context before forming any hypothesis.
1. Read error messages, stack traces, reproduction steps.
2. Trace the code path from symptom back to potential causes.
3. Check recent changes: `git log --oneline -20 -- <affected-files>` — regression = root cause is in the diff.
4. Reproduce deterministically before proceeding. If you can't reproduce, gather more evidence first.
5. Search prior investigations for the same files. Recurring bugs in the same area are an architectural smell.

Output: **"Root cause hypothesis: ..."** — a specific, testable claim.

### Phase 2 — Pattern Recognition

| Pattern | Signature | Where to look |
|---|---|---|
| Race condition | Intermittent, timing-dependent | Concurrent access to shared state |
| Nil/null propagation | NoMethodError, TypeError | Missing guards on optional values |
| State corruption | Inconsistent data, partial updates | Transactions, callbacks, hooks |
| Integration failure | Timeout, unexpected response | External API calls, service boundaries |
| Configuration drift | Works locally, fails in staging/prod | Env vars, feature flags, DB state |
| Stale cache | Shows old data, fixes on cache clear | Redis, CDN, browser cache |

Recurring bugs in the same files = architectural smell, not coincidence.

### Phase 3 — Hypothesis Testing
Before writing ANY fix, verify the hypothesis.
1. Add a temporary log or assertion at the suspected root cause. Run the reproduction. Does the evidence match?
2. If wrong: gather more evidence. Do not guess. Return to Phase 1.
3. **3-strike rule:** Three failed hypotheses → STOP. Question whether this is an architectural issue, not a bug.

### Phase 4 — Implementation
Once root cause is confirmed:
1. Fix the root cause, not the symptom. Smallest change that eliminates the actual problem.
2. Minimal diff: fewest files touched, fewest lines changed. Resist refactoring adjacent code.
3. Write a regression test that **fails** without the fix, **passes** with it.
4. Run the full test suite. No regressions allowed.
5. Fix touches >5 files → flag the blast radius and confirm before proceeding.

### Phase 5 — Verification & Report
Reproduce the original bug scenario and confirm it's fixed. This is not optional.

```
DEBUG REPORT
════════════
Symptom:         [what the user observed]
Root cause:      [what was actually wrong]
Fix:             [what was changed, with file:line references]
Evidence:        [test output proving fix works]
Regression test: [file:line of the new test]
Related:         [prior bugs in same area, architectural notes]
Status:          DONE | DONE_WITH_CONCERNS | BLOCKED
════════════
```

## Applicability Envelope

**Works well when:**
- A concrete error, stack trace, or failing test is available to anchor investigation
- The code path to the symptom is traceable (not fully black-box)
- Reproduction is achievable in a reasonable number of steps

**Fails or degrades when:**
- Intermittent failures with no reproducible trigger (use Phase 2 instrumentation instead)
- The bug requires deep domain knowledge the agent doesn't have — escalate early
- 3 hypotheses have failed — stop patching; the approach is wrong, not the hypothesis

**Environment assumptions:**
- Git history is available for regression detection
- A test runner is present or a manual reproduction path exists
