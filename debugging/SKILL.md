---
name: debugging
description: Debugging protocol for isolating and fixing errors. Use when an error is present, a fix is confirmed broken, or the same class of error is repeating. Covers the Iron Law, 5-phase root-cause protocol, isolation, salience tiers, diagnostic strategy, autonomous iteration, and conversation state tracking.
status: active
last_validated: 2026-05-24
supersedes: []
validation_method: session
---
# Debugging

## Iron Law

**NO FIXES WITHOUT ROOT CAUSE INVESTIGATION FIRST.**

Fixing symptoms creates whack-a-mole debugging. Every fix that doesn't address root cause makes the next bug harder to find. Find the root cause, then fix it.

Red flags that mean you're guessing:
- "Quick fix for now" â€” there is no "for now." Fix it right or escalate.
- Proposing a fix before tracing data flow.
- Each fix reveals a new problem elsewhere â€” wrong layer, not wrong code.

## Canonical Axioms

> *"Most bugs are a result of the execution state not being exactly what you think it is."*
> â€” John Carmack

> *"Debugging is twice as hard as writing the code in the first place. Therefore, if you write the code as cleverly as possible, you are, by definition, not smart enough to debug it."*
> â€” Kernighan's Law

> **McDonald's First Law:** The number of ways code can fail is theoretically infinite.
> Corollary: Assume your code is the problem until quantifiably proven otherwise. For every bug found in a library, find a hundred in your own code first.

> **MCVE principle:** When hitting a difficult problem, replicate it in a fresh environment with as little code and as few dependencies as possible. Add details back in until it fails. Whatever you last added is almost certainly part of the cause.

## Stance
Objective third-party observer. What is the objective? What contributes to unexpected results? Think through the code's original intent before suggesting changes.

**Assume nothing.** Nine times out of ten, the bug hides in the one area you think you can take for granted. Check the values of all variables involved. Read stack traces completely. Never withhold evidence from anyone helping you debug.

## #1 Rule
If the same class of error repeats: stop patching, revisit the approach. Don't fix symptoms â€” fix the core issue. If quick fixes aren't working, pivot to an alternative rather than chasing the stray problem endlessly.

## Isolation Protocol
```
Zoom out â†’ Extract (modularize) â†’ Unit test â†’ Zoom in â†’ Re-apply
```
- Separate the problem; test under controlled conditions before running the full pipeline
- Never debug through an entire pipeline between fixes
- Test each layer with confirmed working artifacts (checkpointed)
- Speed runs over smoke tests â€” 10 records max for training loops
- MVP regression: remove errors until back to working state, then re-add incrementally

## Seed-Breadcrumb-Fanout Protocol (Dimension-Aware Fix)

Avoid whack-a-mole debugging. When you encounter a defect:

1. **Seed**: Identify the concrete failing instance (file, line, element).
2. **Breadcrumb**: Trace the pattern's lineage: find the definition, template, shared module, or base class that produced it. Search for similar patterns across the codebase using grep/glob to find all siblings.
3. **Fanout**: Apply the fix to **all** siblings/peers in the identified dimension simultaneously. Verify consistency across the set.

**Example**: Incorrect unit icon `GameIcons/Archer.png` appears in `data/units/archer.json`. Search for `"Archer.png"` or `"unit_icon"` across the repo, and fix every matching definitionâ€”not just the one you saw.

**Rule**: If a bug appears in one place, assume it exists in its dimension until proven otherwise. Fix the set, not the symptom.

## Hierarchical Repair-Surface Selection

Do not assume the failing artifact is the correct repair surface.

- First identify the **highest layer** that can eliminate the whole defect class:
  artifact, function, module, subsystem, orchestrator, harness, or policy.
- A downstream artifact can be used as a **proxy unit test** for a higher-layer
  fix. This is often the correct move when the visible symptom is produced by
  orchestration drift rather than local artifact logic.
- If the same artifact keeps failing in slightly different ways after local
  patching, suspect the parent layer that generates, routes, or validates it.
- Patch the owning layer first; then rerun the downstream artifact to confirm
  the failure class is gone.
- Prefer parser, generator, orchestrator, harness, or policy fixes over
  hand-editing downstream artifacts.
- Allow a narrow downstream edit only when:
  1. the higher-level path is unavailable or itself broken
  2. the downstream artifact is the explicit repair target
  3. a narrow unblock is required and the higher-level fix is not yet ready

Example pattern:

1. downstream batch/script/artifact visibly fails
2. repeated orchestrator output loops on shell choice / route choice / retry
3. root cause lives in the harness or orchestrator policy
4. the artifact remains the regression test, but not the primary edit target

This keeps debugging from collapsing into symptom repair.

Cross-reference: `agentic-harness` covers the harness-specific version of this
rule and owns the separate `Silent Bounded-Edit Stall Protocol`.

## Salience Tiers
| Priority | Target |
|---|---|
| High | Code directly touching the error line |
| Medium | Code in the execution path to the error |
| Low | Code sharing variables with the error path |
| Ignore | Code with no logical connection to the error |

## Diagnostic Strategy
1. Trace errors from the line numbers called out
2. Survey the situation â€” what worked, what didn't
3. Add diagnostic prints near the error; verify inputs, schema, initial conditions
4. Identify expected vs actual (examine inputs)
5. **False dichotomy check:** are we forcing a binary? If so, expand the output space

## Conversation State
- Track: same error *type* across turns vs different error *location*
- Independent events are separate base facts â€” do not presume causation because they appear together
- Look for common underlying conditions that enabled both

## Autonomous Iteration
Run â†’ observe â†’ fix â†’ rerun without asking. Surface only true blockers:
- Missing credentials
- Ambiguous requirement
- Scope-changing architectural decision

Syntax, imports, schema, logic bugs are yours to resolve.

## Error Schema Checklist
Rogue n/a Â· duplicate keys Â· missing fields Â· wrong joins Â· off-by-one bounds Â· type mismatches Â· duplicate function definitions

## 5-Phase Root Cause Protocol

### Phase 1 â€” Gather Evidence
Collect context before forming any hypothesis.
1. Read error messages, stack traces, reproduction steps.
2. Trace the code path from symptom back to potential causes.
3. Check recent changes: `git log --oneline -20 -- <affected-files>` â€” regression = root cause is in the diff.
4. Reproduce deterministically before proceeding. If you can't reproduce, gather more evidence first.
5. Search prior investigations for the same files. Recurring bugs in the same area are an architectural smell.

**Multi-component systems:** when the error traverses multiple layers (CIâ†’buildâ†’signing, APIâ†’serviceâ†’DB),
add diagnostic instrumentation at EACH component boundary before forming any hypothesis:
```
for each boundary:
  - log what enters the component
  - log what exits the component
  - verify env/config propagation
  - check state at that layer
run once to learn WHERE it breaks, then investigate that specific layer
```
This reveals the failing layer precisely instead of thrashing across all of them.

Output: **"Root cause hypothesis: ..."** â€” a specific, testable claim.

### Phase 2 â€” Pattern Recognition

| Pattern | Signature | Where to look |
|---|---|---|
| Race condition | Intermittent, timing-dependent | Concurrent access to shared state |
| Nil/null propagation | NoMethodError, TypeError | Missing guards on optional values |
| State corruption | Inconsistent data, partial updates | Transactions, callbacks, hooks |
| Integration failure | Timeout, unexpected response | External API calls, service boundaries |
| Configuration drift | Works locally, fails in staging/prod | Env vars, feature flags, DB state |
| Stale cache | Shows old data, fixes on cache clear | Redis, CDN, browser cache |

Recurring bugs in the same files = architectural smell, not coincidence.

### Phase 3 â€” Hypothesis Testing
Before writing ANY fix, verify the hypothesis.
1. Add a temporary log or assertion at the suspected root cause. Run the reproduction. Does the evidence match?
2. If wrong: gather more evidence. Do not guess. Return to Phase 1.
3. **3-strike rule:** Three failed hypotheses â†’ STOP. Question whether this is an architectural issue, not a bug.
   Signals it's architectural: each fix reveals new coupling in a different place; fixes require massive refactoring; symptoms migrate but don't resolve. If this pattern appears, discuss architecture before attempting fix #4.

### Phase 4 â€” Implementation
Once root cause is confirmed:
1. Fix the root cause, not the symptom. Smallest change that eliminates the actual problem.
2. Minimal diff: fewest files touched, fewest lines changed. Resist refactoring adjacent code.
3. Write a regression test that **fails** without the fix, **passes** with it.
4. Run the full test suite. No regressions allowed.
5. Fix touches >5 files â†’ flag the blast radius and confirm before proceeding.

### Phase 5 â€” Verification & Report
Reproduce the original bug scenario and confirm it's fixed. This is not optional.

---

## Subtractive Git-Walk Protocol

**Trigger:** silent crash or no-stack-trace regression where (a) a last-known-good commit exists,
(b) multiple changes have landed since then, and (c) the symptom has no direct error output to anchor
standard Phase 1 investigation.

The O(n) git-walk and the O(1) lessons-learned register lookup are two halves of the same protocol.
Always attempt the register lookup first â€” it converts the walk into a constant-time operation when
the symptom class has been seen before.

### Step 1 â€” Get the Diff Set

```bash
git log --oneline <last-known-good>..HEAD
```

Produces an ordered list of candidate commits, most recent first.

### Step 2 â€” Fast-Path: Lessons-Learned Register First

Before walking any commit, scan the project's lessons-learned register
(e.g., `HARNESS.md` gotcha list, or equivalent) for the symptom signature.

- **Match found** â†’ go directly to that fix. Skip the walk entirely.
- **No match** â†’ proceed to Step 3.

The register converts O(n commits) investigation into O(1) lookup.

### Step 3 â€” Rank Commits by Subsystem Overlap

For each commit, ask: does this change touch the subsystem where the symptom manifests?
Sort by overlap. Higher overlap = higher prior probability of cause.

### Step 4 â€” Negative Inference Walk (highest overlap first)

For each candidate commit, apply the negative inference question:

> *"If this commit were reverted, would the symptom disappear?"*

Not: *"could this be the cause?"* â€” that accepts too many candidates.
The negative framing forces elimination, not confirmation.

### Step 5 â€” Stop at First Confirmed Causal Commit

Do not continue walking back once root cause is confirmed.
Reverting subsequent commits is scope creep, not debugging.

### Step 6 â€” Register the Pattern (mandatory)

After fixing, append the root cause as a new entry in the lessons-learned register:

```
symptom signature:  <what was observed, not what was expected>
root cause:         <the specific commit / code change>
fix applied:        <what was changed to resolve it>
subsystem:          <which area of the codebase / pipeline>
```

This is **not optional cleanup**. The register is the accelerant for the next agent or developer
facing the same symptom class. Each entry reduces the expected walk length of all future sessions.

---

## Self-Repair (Autonomous Fix-Run-Retry)

Self-repair is the execution-feedback loop that closes the debugging cycle without human
input. It is Phase 4 + Phase 5 run in a tight retry loop.

**When to use:** the failure mode is deterministic (same input â†’ same error), the error
is machine-readable, and the fix space is bounded (syntax/logic errors, test failures,
import errors). Do NOT use self-repair for architectural issues or ambiguous requirements.

### Contract

```
Require: a reproducible failure (test output, exception, lint error)
Guarantee: either the failure is resolved OR max_attempts is reached and the failure
           is surfaced with a structured diagnostic
Maintain: each attempt produces a strictly different fix (no repeating patches)
Assert: run the full test suite after each fix attempt; track attempt_count
```

### Loop Protocol

```python
class RepairAttempt(BaseModel):
    attempt_num: int
    error_class: str          # e.g. "ImportError", "AssertionError", "SyntaxError"
    error_message: str
    hypothesis: str           # what the fix targets
    patch_summary: str        # what changed
    result: Literal["pass", "fail", "new_error"]
    new_error_class: str | None

def self_repair_loop(run_fn, fix_fn, max_attempts: int = 5) -> RepairReport:
    """
    run_fn: callable that runs the task and returns (success, error_output)
    fix_fn: callable(error_output, history) -> patch; applies fix and returns summary
    """
    history: list[RepairAttempt] = []
    for i in range(max_attempts):
        success, error_output = run_fn()
        if success:
            return RepairReport(resolved=True, attempts=history)

        patch_summary = fix_fn(error_output, history)
        history.append(RepairAttempt(
            attempt_num=i,
            error_class=classify_error(error_output),
            error_message=error_output[:500],
            hypothesis=derive_hypothesis(error_output, history),
            patch_summary=patch_summary,
            result="unknown",
        ))

        # Pivot rule: same error class 3 times -> stop, escalate
        recent_classes = [a.error_class for a in history[-3:]]
        if len(set(recent_classes)) == 1 and len(recent_classes) == 3:
            return RepairReport(resolved=False, reason="plateau", attempts=history)

    return RepairReport(resolved=False, reason="max_attempts", attempts=history)
```

### Pivot Rule in Self-Repair

If the **same error class** appears 3 consecutive times, the patch strategy is wrong.
Stop the loop and escalate to a human or invoke `reasoning` for a deeper decomposition.
Never exceed `max_attempts` without surfacing the structured `RepairReport`.

### Evidence

- Self-debugging arXiv:2304.05128: execution-feedback loop +12% on TransCoder/MBPP
- Devin (Cognition, 2025): runâ†’observeâ†’patchâ†’rerun is the core SWE-agent loop
- Claude Code: autonomous tool-call retry on error is native; this formalizes the contract
DEBUG REPORT
â•â•â•â•â•â•â•â•â•â•â•â•
Symptom:         [what the user observed]
Root cause:      [what was actually wrong]
Fix:             [what was changed, with file:line references]
Evidence:        [test output proving fix works]
Regression test: [file:line of the new test]
Related:         [prior bugs in same area, architectural notes]
Status:          DONE | DONE_WITH_CONCERNS | BLOCKED
â•â•â•â•â•â•â•â•â•â•â•â•
```

## Applicability Envelope

**Works well when:**
- A concrete error, stack trace, or failing test is available to anchor investigation
- The code path to the symptom is traceable (not fully black-box)
- Reproduction is achievable in a reasonable number of steps

**Fails or degrades when:**
- Intermittent failures with no reproducible trigger (use Phase 2 instrumentation instead)
- The bug requires deep domain knowledge the agent doesn't have â€” escalate early
- 3 hypotheses have failed â€” stop patching; the approach is wrong, not the hypothesis

**Environment assumptions:**
- Git history is available for regression detection
- A test runner is present or a manual reproduction path exists
<!-- consolidation:see-also:start -->
## See Also
[[representation-pipeline]]  [[validation]]  [[causal-inference]]  [[agentic-harness]]
<!-- consolidation:see-also:end -->
