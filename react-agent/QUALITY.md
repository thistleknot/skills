# Quality Evaluation Reference

When to read this file: during the Completion Protocol, or when assessing whether
a subtask's output meets quality standards before moving to the next subtask.

## Six-Dimension Quality Check

Evaluate every deliverable (code change, config update, new file) against these
dimensions before marking a subtask as complete.

### Safety

- Does this change introduce any security risks? (exposed secrets, injection
  vectors, permission escalation, unsafe deserialization)
- Does it modify or bypass existing safety mechanisms?
- Could it cause data loss or corruption in edge cases?
- Does it handle untrusted input defensively?

Failure here is a hard block — do not proceed.

### Completeness

- Does the change implement ALL requirements for this subtask?
- Are edge cases handled (null inputs, empty collections, boundary values)?
- Are error paths handled (not just the happy path)?
- Are all necessary imports, dependencies, and configs included?
- Is there documentation where the codebase convention requires it?

Partial completeness is acceptable only if explicitly scoped in the plan.

### Executability

- Does the code run? Have you actually executed it?
- Do tests pass? Have you actually run them?
- Does it integrate with the existing codebase without breaking other modules?
- Are all referenced files, modules, and functions accessible?
- If config changes were made, does the application start correctly?

"It should work" is not executability. Run it.

### Maintainability

- Is the change modular — can it be modified independently without cascading?
- Does it follow existing code conventions (naming, structure, patterns)?
- Is the intent of the change clear from reading the code?
- Does it avoid unnecessary coupling to other modules?
- Could another developer understand and modify this code without context?

### Cost-Awareness

- Is this the simplest implementation that satisfies the requirements?
- Does it avoid unnecessary computation, API calls, or resource consumption?
- Does it reuse existing utilities rather than reimplementing them?
- Is the scope proportional to the value delivered?

**Operational cost (context and token budget):**
- Could this operation (test run, log scan, doc fetch) be delegated to a subagent to keep verbose output out of the main context?
- Is a CLI tool available that avoids loading MCP server tool definitions for this operation?
- Is this subtask independent enough to run as a parallel subagent, reducing wall-clock time?

### Acceptance Alignment

This dimension addresses the paper's RQ2 finding that local acceptance (tests
pass, verifier approves) frequently diverges from the actual done condition
specified in the task — the most common cause of false completion.

- Does the local success signal (tests green, linter clean, verifier PASS) map
  onto **every** `completion_condition` listed in `task.md`?
- Is there a `completion_condition` in `task.md` that no local check currently
  exercises? If so, add a check that covers it.
- Have you distinguished between *local* acceptance ("my tests pass") and
  *final evaluator* acceptance ("the user's actual done condition is met")?
- Does your `evidence.md` artifact cite each `completion_condition` with a
  concrete result (output, artifact path, test line) — not a claim?

Failure here is a hard block: a task that looks locally done but fails the
actual done condition is worse than incomplete because it misleads the user.

## Rating Scale

For each dimension, rate as:

- **Good** — Fully satisfies the dimension with no concerns
- **Adequate** — Satisfies the dimension with minor gaps that don't block progress
- **Poor** — Fails the dimension; must be addressed before proceeding

A subtask is complete when all six dimensions rate Good or Adequate,
with no dimension rated Poor on Safety, Executability, or Acceptance Alignment.

## Applying the Check

In practice, this check takes 30 seconds of deliberate attention. After each
subtask, mentally walk through:

1. Safe? → no new vulnerabilities
2. Complete? → all requirements addressed
3. Executable? → actually runs and passes tests
4. Maintainable? → clean, follows conventions
5. Cost-appropriate? → not over-engineered
6. Acceptance-aligned? → local pass maps onto every stated completion condition

Log the assessment in `memory.jsonl` alongside the subtask outcome.
