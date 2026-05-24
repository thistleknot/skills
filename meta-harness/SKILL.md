# Meta-Harness Skill

## Purpose

Use `meta-harness` as the requester-facing manager layer that sits one level above
`agentic-harness`. It keeps separation of concerns clear:

- `meta-harness` owns objective framing, scope partitioning, session topology, and
  handoff policy.
- `agentic-harness` owns execution mechanics for one scoped issue at a time.

This avoids mixing "what should be solved now" with "how the worker harness solves
it."

## Trigger Conditions

Invoke when:

- A request contains multiple independent issues and needs scoped decomposition
- You need parent/child session orchestration (fork workers, resume workers,
  aggregate outcomes)
- The user asks for manager-level handling rather than direct leaf-task editing
- Work is drifting into downstream patching and needs an upstream-first routing
  reset

## Core Contract

### 1) Scope and objective contract

Before dispatching work, define:

1. Objective (single sentence)
2. Constraints (what must not change)
3. Success criteria (observable done conditions)

### 2) Separation contract

- One session = one scoped objective
- Parent session coordinates
- Child sessions execute scoped tasks
- Resume existing sessions when context is still valid; fork new sessions for
  parallel independent work

### 3) Upstream-first repair contract

For each issue, identify:

- upstream source surface
- transformation/generation layer
- downstream artifact

Fix at the highest valid upstream layer, then regenerate downstream artifacts.

### 4) Execution handoff contract

`meta-harness` delegates scoped execution to `agentic-harness` (and children) with:

- scoped task packet
- expected outputs
- validation commands
- escalation conditions

## OpenCode Session Pattern

Use this operational pattern in OpenCode:

- `opencode run -m <provider/model> "<task prompt>"` for one-shot scoped sessions
- `opencode run -c` (or `--session <id>`) to resume
- `opencode run --session <id> --fork` to branch worker sessions per task

## Bootstrap Prompt Template

```text
You are my manager-level coding agent for this repository.

Operating mode:
- Use OpenCode as top-level orchestrator.
- Keep clean separation: one session = one scoped objective.
- For parallel work, fork child sessions per task and keep a parent coordination session.
- Resume existing sessions instead of restarting context when possible.
- Prefer upstream root-cause fixes over downstream artifact patching.
- Apply one-degree-out sibling scans before fixing a named leaf issue.
- Make surgical changes only; no unrelated refactors.
- Do not create placeholders that alter asset/lookup precedence.

Execution contract:
1) Restate objective, constraints, and success criteria.
2) Identify upstream source surface(s), transformation layer, and downstream artifacts.
3) Fix at the highest valid upstream layer.
4) Regenerate outputs.
5) Run repo validation commands.
6) Return concise report:
   - changed files
   - root cause
   - why this fix prevents recurrence
   - validation outcome
```

## Integration

- Parent role over `agentic-harness` for request decomposition and coordination
- Complements `agentic-orchestration` (pattern selection) and
  `multi-agent-coordination` (parallel execution contracts)
- Works with `adjacent-surface-scan` to enforce one-degree-out sibling checks

## Failure Modes

| Failure | Cause | Fix |
|---|---|---|
| Parent session micromanages leaf edits | Separation collapse between manager and worker layers | Re-scope and dispatch a single objective packet to `agentic-harness` |
| Session sprawl with no ownership | Forking without parent coordination | Rebuild parent task board and assign one owner per child |
| Repeated downstream patching | Upstream source surface not identified | Re-run upstream/transformation/downstream mapping before edits |
