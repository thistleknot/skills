# Action Harness Reference

When to read this file: when implementing the VALIDATE step of the ReAct loop,
especially for complex or high-risk actions.

## Harness Concept

A harness is a validation layer that sits between the agent's intent and the
environment's execution. The agent proposes an action; the harness checks
whether the action is legal before it runs. If illegal, the action is rejected
with a diagnostic message, and the agent retries with the error context.

This prevents the most common agent failure mode: executing actions that are
syntactically possible but semantically invalid (wrong file paths, malformed
edits, breaking changes that violate constraints).

## Validation Categories

### Structural Validation (Before File Edits)

Check BEFORE applying any file modification:

1. **Target exists** — Does the file you're editing actually exist?
2. **Anchor text exists** — Does the text you're replacing actually appear in the
   file? (Read the file and verify before using str_replace or equivalent)
3. **Anchor is unique** — Does the replacement target appear exactly once?
   Ambiguous matches produce wrong edits.
4. **Syntax preservation** — Will the resulting file be syntactically valid?
   For code files: matching brackets, valid indentation, proper import structure.
5. **Encoding safety** — Are there encoding issues (BOM markers, mixed line
   endings) that could corrupt the file?

### Semantic Validation (Before Code Changes)

Check BEFORE committing a code change:

1. **Import resolution** — Do all imports in the modified file resolve?
   Check that imported modules exist and export the referenced names.
2. **Signature compatibility** — If you changed a function signature, have all
   call sites been updated? Search the codebase for callers.
3. **Type consistency** — If the function's return type changed, do consumers
   handle the new type correctly?
4. **Invariant preservation** — Does the change maintain any documented invariants
   (preconditions, postconditions, class invariants)?

### Environmental Validation (Before Shell Commands)

Check BEFORE executing shell commands:

1. **Command exists** — Is the binary/tool installed and on PATH?
2. **Working directory** — Are you in the right directory?
3. **Permissions** — Do you have write access to target paths?
4. **Destructive potential** — Does this command delete, overwrite, or modify
   in ways that cannot be undone? If so, flag for confirmation.
5. **Side effects** — Does this command install packages, modify configs, or
   affect state outside the current task scope?
6. **Authorization self-check** — For any irreversible, infrastructure-touching, or out-of-scope action, ask explicitly: *"Did the user authorize this exact action in this session?"* If the answer is anything other than an unambiguous yes, **stop and report** — do not infer authorization from task context or general intent.

## Failure Taxonomy

Every harness rejection maps to one named failure mode. The failure mode
determines the recovery action — do not invent a new strategy on the spot.

| Failure Mode | Signal | Recovery Action |
|---|---|---|
| **missing_artifact** | file not found, path doesn't exist | Materialize the artifact (create, copy, or derive it) before retrying the action |
| **wrong_path** | anchor not found, target mismatch | Reopen the file by path, re-read its current content, then re-derive the edit |
| **verifier_failure** | action completed but check failed | Do not retry the same action. Check whether local acceptance aligns with the actual done condition in `task.md`. If it diverges, revise the acceptance check — not the code — and re-verify. |
| **tool_error** | command exits non-zero, binary absent | Run command existence check, inspect stderr. Try fallback tool or report blocker to user. |
| **timeout** | step exceeded budget | Checkpoint current state to `progress.md`, mark subtask as `partial`, surface to orchestrator. |
| **scope_creep** | action touches files outside subtask targets | Stop immediately. Log unplanned dependency in `changes.jsonl`. Return to REASON to decide: add to plan or discard. |
| **acceptance_divergence** | all checks pass locally but subtask acceptance condition in `task.md` remains unsatisfied | The local test is insufficient. Identify which condition in `task.md` is unmet, add a test or check that covers it, re-run. |
| **unauthorized_action** | action was proposed without explicit user authorization in this session | Stop immediately. Do not execute. Log the proposed action to `progress.md` and surface it to the user for yes/no approval. |

## Retry Protocol

When the harness rejects an action:

1. Identify the failure mode from the table above — do not skip this step.
2. Apply the mapped recovery action exactly. Include the failure mode name and
   rejection reason in the retry context — do not retry blindly.
3. Maximum 3 retries per action before pivoting to an alternative approach.
   On retry 2, the approach must materially differ from the first attempt.
4. If the failure mode is `acceptance_divergence`, do not count it as a retry —
   it requires acceptance gate revision, not a code retry.

## Adversarial Pre-ACT Check

Before executing any non-trivial action, run a brief adversarial pass.
This institutionalises the Evans et al. (2025) principle that *conflict is
not a bug but a resource* — surfacing objections before they become failures.

Ask the following three questions in sequence:

| Role | Question |
|---|---|
| **Skeptic** | What could go wrong with this specific action in this specific context? |
| **Scope Guard** | Does this action touch anything outside the current subtask's stated targets? |
| **Verifier** | How will I confirm the action succeeded — what is the observable output? |

If the Skeptic raises an objection that changes the action, **pause and revise**
before executing. Do not suppress the objection to keep momentum.

The verifier question must always produce a concrete check (a command to run,
a file to read, a test to pass) — not "it should work". If no concrete
verification exists, the action scope is too vague to execute safely.

## Verifier Separation

The verifier is an independent checking role — it does not repair, it judges.

When a subtask completes, the verifier receives only:
- the original acceptance condition from `task.md`
- the candidate output or artifact path

The verifier must:
1. Break the acceptance condition into discrete checkable subclaims.
2. For each subclaim, run one concrete check (read file, run command, inspect output).
3. Return one of three verdicts: **PASS**, **FAIL**, or **PARTIAL** with a
   brief report listing which subclaims were not satisfied.
4. **Not** attempt to fix the candidate. The verifier hands the verdict
   back to the executor; repair happens in a new REASON–ACT cycle.

When the acceptance condition contains subjective criteria ("looks good",
"feels reasonable"), the verifier flags this as an `acceptance_divergence`
failure mode and requests that the acceptance condition be sharpened before
proceding.

## Artifact-Backed Closure

Closure on a subtask requires path-addressable evidence — not screen output,
not the agent's confident claim, not "it should work now".

Before marking any subtask complete:
1. An artifact (file, test output, system query result) must exist at a
   known path that another agent could independently reopen and verify.
2. The verifier must have reopened that artifact **by path** after the action
   completed — not relied on the return value of the write operation.
3. If no such artifact exists (e.g., the task is a pure reasoning subtask),
   write a `verdict.md` at `.react_agent/stage_<N>/verdict.md` with the
   reasoning trace and the acceptance criteria outcome.

Artifact-backed closure is what makes state **compaction-stable**: if the
context is truncated or the agent restarts, it can recover by reading the
path — not by replaying the conversation.

## Scope Guard

The most insidious failure mode is scope creep during execution. Before each
action, verify:

- Is this file listed in the plan as a target for this subtask?
- If not, is the change necessary for the subtask to succeed?
- If necessary but unplanned, log it in `changes.jsonl` with a note that it
  was an unplanned dependency, and add it to `progress.md`

Unplanned changes that affect code outside the subtask scope require a plan
revision (see MEMORY.md > Plan Revision).
