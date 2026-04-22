---
name: debugging
description: Debugging protocol for isolating and fixing errors. Use when an error is present, a fix is confirmed broken, or the same class of error is repeating. Covers isolation, salience tiers, diagnostic strategy, autonomous iteration, and conversation state tracking.
---
# Debugging

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
