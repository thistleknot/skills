---
name: pi
description: Lightweight external harness substrate. Use when an outer orchestrator such as opencode or agentic-harness should delegate a bounded subproblem to a second harness that stays lighter than the main control plane and can expose aider-like internal workers.
status: active
last_validated: 2026-05-22
supersedes: []
validation_method: session
---
# Pi

## Role
`pi` is a **delegated external harness**, not the top-level policy engine.

- **Outer orchestrator** (`opencode`, `agentic-harness`, or similar) keeps global plan ownership.
- **Pi** receives one bounded task packet, runs a lighter internal harness for that packet, and returns a structured result.
- **Leaf executors inside Pi** can be `aider` or other narrow workers.

Think of the runtime stack as:

```text
opencode / agentic-harness
    -> pi
        -> aider / local worker subagents
```

## When to Use
- The outer harness should keep project-wide policy, but a subproblem deserves its own short-horizon harness.
- You want an **outside agent harness** under `opencode` without giving that child harness repo-wide autonomy.
- You want `aider`-style workers, but grouped behind a callable harness surface instead of invoking each worker directly.

## Working Contract
- Keep `pi` **light**. It should not become a second heavyweight orchestrator with its own sprawling control plane.
- The caller must provide:
  - explicit objective
  - artifact target or return shape
  - stop condition
  - allowed tool/runtime envelope
- `pi` must return a **structured work result**, not only prose.
- `pi` may spawn internal role lanes (`developer`, `qa`, `critic`, `runner`) when that decomposition is local to the assigned subproblem.

## Composition Rules
- The outer orchestrator owns:
  - story selection
  - cross-story routing
  - approval policy
  - final synthesis
- `pi` owns:
  - subtask-local planning
  - bounded execution loop
  - internal worker coordination
  - artifact handoff back to the caller
- `aider` remains a **leaf executor**, even when invoked through `pi`.

## Default Position in the Stack
- **orchestrator lane** — `opencode`
- **delegated external-harness lane** — `pi`
- **leaf-agent lane** — `aider`

Use this three-lane stack when the outer manager should stay clean while the delegated harness manages a self-contained implementation or verification scene.

## Do Not Do This
- Do not let `pi` silently take over project-wide orchestration from the parent harness.
- Do not collapse `pi` and `aider` into one role. `pi` is the mini-harness; `aider` is one possible worker inside it.
- Do not describe `pi` as integrated unless the resolved `opencode -> pi -> aider` stack is visible in state, logs, or emitted artifacts.

<!-- consolidation:see-also:start -->
## See Also
[[agentic-harness]]  [[substrate-selection]]  [[agentic-design-patterns]]
<!-- consolidation:see-also:end -->
