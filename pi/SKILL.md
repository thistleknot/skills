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

## Lessons Learned

### Pi is a runner, not a planner (2026-05-22)
The moment pi gets decision logic — routing, conditionals, multi-step plans — it becomes a second orchestrator and the stack collapses. Strip it back to: receive command, execute, return stdout. That's the entire contract.

### Pi is the right tool for smoke tests (2026-05-22)
When you need to verify a CLI tool is wired correctly (e.g., `opencode run`, `aider`, a shell script), use pi to execute the probe and return raw output. The outer harness (orchestrator or watchdog) interprets the result. Pi doesn't judge whether the result is good.

### `opencode run --config` does not exist (2026-05-22)
`opencode run` has no `--config` flag. Config is discovered by walking up from the process working directory to the nearest `opencode.json`. Fix: `Set-Location` to the directory containing `opencode.json` before invoking `opencode run`, or use `--dir` to set the workspace path.

### Subagents cannot be invoked as primary CLI agents (2026-05-22)
`opencode run --agent aider` falls back to the default agent with a warning: "aider is a subagent, not a primary agent." Subagents (those with `subtask=deny` or no primary-agent flag) are only reachable via `subtask`/`task()` dispatch from *inside* a running session. Pi can call them; the CLI cannot target them directly.

### The `read` tool may be unavailable depending on permission config (2026-05-22)
Even with `"read": "allow"` in the agent permission block, the `read` tool was absent from the available tool list inside the session. The correct tool name inside opencode sessions appears to be `bash` (via `cat`) or `read_session`, not `read`. Always verify available tools on first turn before assuming file-read is accessible.

<!-- consolidation:see-also:start -->
## See Also
[[agentic-harness]]  [[substrate-selection]]  [[agentic-design-patterns]]
<!-- consolidation:see-also:end -->
