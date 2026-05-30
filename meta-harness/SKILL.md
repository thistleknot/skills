# Meta-Harness Skill

## Purpose

Use `meta-harness` as the requester-facing **master control-plane orchestrator**
that sits one level above `agentic-harness`. It keeps separation of concerns clear:

- `meta-harness` owns objective framing, scope partitioning, session topology, and
  handoff policy.
- `agentic-harness` owns execution mechanics for one scoped issue at a time.
- substrate adapters and backend graphs own transport details such as file emission,
  message serialization, and runtime-specific resume plumbing.

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

Do not invoke when:

- The task is a single bounded leaf fix that one worker can complete directly
- You are already inside a spawned OpenCode worker session for that same scope

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

Before execution starts, the receiving orchestrator or worker must perform a
**repeat-back handshake**:

1. restate the task packet in its own words
2. restate any load-bearing definitions, constraints, and done conditions
3. receive an implicit or explicit match on that restatement before acting

If the receiver cannot restate the packet faithfully, the protocol is underspecified
and execution should not proceed yet.

`meta-harness` does **not** manage backend graph files, transport envelopes, or
runtime-specific message plumbing directly. It emits a scoped task packet and
expects the substrate/harness adapter to translate that packet into the correct
backend-graph or runtime-specific wire format behind the scenes.

### 5) Anti-recursion contract (OpenCode)

- `meta-harness` may choose OpenCode as a substrate only at the parent/orchestrator
  boundary.
- Once inside an OpenCode-managed spawned session, do not call `opencode` again from
  that child session.
- Nested `opencode` invocations inside an active OpenCode worker are treated as a
  stall-risk control-flow violation.

Required fallback when nested launch is detected:

1. Stop the nested attempt.
2. Continue execution with native tools in the current session (search/edit/run).
3. If a new OpenCode run is truly required, start it only from the top-level parent
   session, not from a child worker.

## OpenCode Session Pattern

Use this operational pattern in OpenCode:

- `opencode run -m <provider/model> "<task prompt>"` for one-shot scoped sessions
- `opencode run -c` (or `--session <id>`) to resume
- `opencode run --session <id> --fork` to branch worker sessions per task

Backend rule:

- If OpenCode's `--agent` path or a converged backend graph requires writing to a
  file or message surface, that emission belongs to the adapter layer behind
  `agentic-harness` / `substrate-selection`, not to the orchestrator prompt.
- The orchestrator should act as if it is sending a scoped task packet into a
  stable backend contract; it should not script transport details itself.

Where/when routing rule:

- Use `meta-harness` in the top-level manager session to decide and launch OpenCode
  scoped work.
- Use `agentic-harness` in child sessions for implementation/verification mechanics.
- Do not route child workers back through `opencode run ...`; that recursion is
  forbidden because it causes avoidable stalls.

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
- Relies on `substrate-selection` to hide runtime-specific backend graph and
  file/message emission details behind a stable execution adapter

## Failure Modes

| Failure | Cause | Fix |
|---|---|---|
| Parent session micromanages leaf edits | Separation collapse between manager and worker layers | Re-scope and dispatch a single objective packet to `agentic-harness` |
| Session sprawl with no ownership | Forking without parent coordination | Rebuild parent task board and assign one owner per child |
| Repeated downstream patching | Upstream source surface not identified | Re-run upstream/transformation/downstream mapping before edits |
