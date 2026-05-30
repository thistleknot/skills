## Delegation Schema

Every agent call MUST include these fields or it will throw `SchemaError`:
- `description`: 3-5 word summary of the task (REQUIRED)
- `agent`: the agent name to delegate to
- `instructions`: full task details

## Agent Roster
This project uses a multi-agent harness. Default entrypoint is @orchestrator.

- @orchestrator â€” primary router, gemma orchestrator lane, cheapest sufficient delegation
- @planner â€” high-effort planning lane (oracle / planner)
- @fixer â€” multi-file implementation packetizer (fixer / coder)
- @aider â€” leaf executor, one bounded edit packet per call (subtask=deny)
- @pi â€” inner harness loop / smoke-test runner
- @patcher â€” exact hotfix / known-file mutation agent
- @handyman â€” mechanical file operations
- @debugger â€” validation and error tracing
- @scout â€” disciplined first-pass codebase search and mapping
- @researcher â€” 3-hop web/docs/files evidence gathering (absorbs librarian)
- @summarizer â€” SPO triplet extraction / context compression
- @observer â€” visual inspection and audit
- @thinker â€” first-principles fallback when stuck

Legacy docs still exist for `@designer`, `@explorer`, and `@librarian`, but the
active OMO-Slim hierarchy shown in `hierarchy.mmd` / `hierarchy.svg` routes through
planner/oracle, scout, and researcher instead. `@scout` is active again; only the
legacy explorer lane remains disabled.

## Launch Rail

- Top-level OpenCode sessions must start with `--agent orchestrator` or via
  `heartbeat.ps1` (which already defaults to `orchestrator`).
- Bare `opencode run ...` falls back to the default `build` agent and will not
  use the custom hierarchy shown in the diagram.
- `run_aider.ps1` exists specifically to enter the orchestrator lane and then
  force an `AIDER DIRECT` handoff to `@aider`.
- `run_orchestrator_lanes.ps1` opens two top-level orchestrator sessions side by
  side so Gemma and `deepseek-v4-flash` can be compared in separate tabs/windows.
- `heartbeat.ps1` now acts as a Gemma-orchestrator contract guard: it launches
  sessions in JSON mode, detects unavailable-tool `read`, Unix `cat` in
  PowerShell, and empty `write` payloads, then retries with an explicit runtime
  tool contract instead of waiting for a generic stall timeout.
- @orchestrator â€” primary router, cheapest sufficient delegation
- @planner â€” architecture and decomposition
- @designer â€” signatures and stubs before implementation
- @coder â€” spec-packager + @aider dispatcher (no direct file edits)
- @aider â€” leaf executor, one bounded edit packet per call (subtask=deny)
- @pi â€” pure command runner, no decisions
- @handyman â€” mechanical file operations
- @debugger â€” validation and error tracing
- @scout â€” codebase search and mapping (disciplined, 50-line output cap; disabled in the current Gemma orchestration path)
- @explorer â€” codebase search built-in (undisciplined fallback; prefer @scout)
- @librarian â€” external research and docs
- @summarizer â€” context compression, triplet extraction
- @observer â€” visual and document interpretation
- @thinker â€” deep reasoning, first-principles re-approach when stuck

When in doubt, start with @orchestrator.

## Launch Rail

- Top-level OpenCode sessions should start with `--agent orchestrator` or via
  `heartbeat.ps1` (which already defaults to `orchestrator`).
- `heartbeat.ps1` now acts as a Gemma-orchestrator contract guard: it launches
  sessions in JSON mode, detects unavailable-tool `read`, Unix `cat` in
  PowerShell, and empty `write` payloads, then retries with an explicit runtime
  tool contract instead of waiting for a generic stall timeout.

## Handoff Contracts

| From | To | Via | Contract |
|------|----|-----|----------|
| @orchestrator | @planner | task() | Pass full task context + task_id. Planner returns phased plan or spec-ready decomposition. |
| @orchestrator | @fixer | task() | Pass bounded implementation packet + task_id. Fixer breaks multi-file work into aider packets when needed. |
| @orchestrator | @patcher | task() | Pass exact file + exact mutation. Patcher edits first and reruns immediately when the task is a known-file hotfix. Skip scout when the file is already known. |
| @orchestrator | @pi | task() | Pass one bounded inner-loop objective. Pi routes only inside the local loop. |
| @orchestrator | @handyman | task() | Pass exact mechanical steps + task_id. No judgment expected. |
| @orchestrator | @debugger | task() | Pass logs/error + task_id. Debugger returns `FAILURE_CLASS`, confidence, repair surface, and the next route. |
| @orchestrator | @scout | task() | Pass one bounded search objective. Scout returns a compact file/dir contract, not prose. |
| @orchestrator | @researcher | task() | Pass evidence objective. Researcher gathers raw sources, then routes them through summarizer or into thinker when the stuck problem needs evidence-backed reframing. |
| @orchestrator | @observer | task() | Pass screenshots / visual artifacts + task_id. Observer extracts layout/text and returns structured findings. |
| @orchestrator | @thinker | task() | Pass debugger-classified `logic` failures plus compressed evidence. Thinker is signal-gated, not retry-count-gated. |
| @orchestrator | @aider | `run_aider.ps1` / AIDER DIRECT | Valid only for the explicit direct-leaf lane. The top-level OpenCode process must still be `--agent orchestrator`. |
| @fixer | @aider | task() | One bounded edit packet per call. Files + acceptance criteria + exact change. |
| @researcher | @summarizer | task() | Raw evidence in, compact triplets/evidence pack out. |
| @summarizer | @thinker | task() | Compressed evidence pack in, first-principles reframe out. |
| @orchestrator | @debugger | task() | Pass logs/error + task_id. Debugger returns diagnosis + fix recommendation. |
| @orchestrator | @aider | INVALID | Must go via @coder. Direct orchâ†’@aider is a routing violation. |
| @coder | @aider | task() | One bounded edit packet per call. Files + acceptance criteria + exact change. |
| any | any | prompt prefix | Always include `[task_id=<id>,workspace_root=<path>]` at start of prompt. |

## Session Graph Protocol (all agents)

Every agent prompt begins with `[task_id=<id>,workspace_root=<path>] <task>`.

- **On start**: `task-graph_update_status(task_id, 'in_progress')` + `task-graph_record_heartbeat(task_id)`
- **On finish**: `task-graph_write_result(task_id, summary)` + `task-graph_update_status(task_id, 'done')`
- **On block**: `task-graph_write_result(task_id, blocker)` + `task-graph_update_status(task_id, 'blocked')`

Orchestrator additionally calls `task-graph_record_heartbeat` as its **first action every turn**.
The watchdog (`heartbeat.ps1`) exits when root task status = `done`. It now treats either **no heartbeat for 300s** or **4x consecutive verbatim stdout repeats** as a stall, then rotates sampler + seed before resuming the same root task.
The watchdog (heartbeat.ps1) exits when root task status = `done`. No heartbeat for 300s = stall â†’ rotate sampler.
For Gemma orchestrator sessions, the watchdog also treats deterministic contract failures as repairable stalls: unavailable `read`, PowerShell shell-dialect mismatches like multi-file `cat`, and empty `write` payloads trigger a corrected retry with an explicit runtime tool contract.