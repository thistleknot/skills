## Delegation Schema

Every agent call MUST include these fields or it will throw `SchemaError`:
- `description`: 3-5 word summary of the task (REQUIRED)
- `agent`: the agent name to delegate to
- `instructions`: full task details

## Agent Roster
This project uses a multi-agent harness. Default entrypoint is @orchestrator.

- @orchestrator — primary router, cheapest sufficient delegation
- @planner — architecture and decomposition
- @designer — signatures and stubs before implementation
- @coder — spec-packager + @aider dispatcher (no direct file edits)
- @aider — leaf executor, one bounded edit packet per call (subtask=deny)
- @pi — pure command runner, no decisions
- @handyman — mechanical file operations
- @debugger — validation and error tracing
- @scout — codebase search and mapping (disciplined, 50-line output cap; disabled in the current Gemma orchestration path)
- @explorer — codebase search built-in (undisciplined fallback; prefer @scout)
- @librarian — external research and docs
- @summarizer — context compression, triplet extraction
- @observer — visual and document interpretation
- @thinker — deep reasoning, first-principles re-approach when stuck

When in doubt, start with @orchestrator.

## Handoff Contracts

| From | To | Via | Contract |
|------|----|-----|----------|
| @orchestrator | @planner | task() | Pass full task context + task_id. Planner returns phased plan. |
| @orchestrator | @designer | task() | Pass spec + task_id. Designer returns stubs only. |
| @orchestrator | @coder | task() | Pass spec + task_id. Coder dispatches to @aider, returns combined diff summary. |
| @orchestrator | @handyman | task() | Pass exact mechanical steps + task_id. No judgment expected. |
| @orchestrator | @debugger | task() | Pass logs/error + task_id. Debugger returns diagnosis + fix recommendation. |
| @orchestrator | @aider | INVALID | Must go via @coder. Direct orch→@aider is a routing violation. |
| @coder | @aider | task() | One bounded edit packet per call. Files + acceptance criteria + exact change. |
| any | any | prompt prefix | Always include `[task_id=<id>,workspace_root=<path>]` at start of prompt. |

## Session Graph Protocol (all agents)

Every agent prompt begins with `[task_id=<id>,workspace_root=<path>] <task>`.

- **On start**: `task-graph_update_status(task_id, 'in_progress')` + `task-graph_record_heartbeat(task_id)`
- **On finish**: `task-graph_write_result(task_id, summary)` + `task-graph_update_status(task_id, 'done')`
- **On block**: `task-graph_write_result(task_id, blocker)` + `task-graph_update_status(task_id, 'blocked')`

Orchestrator additionally calls `task-graph_record_heartbeat` as its **first action every turn**.
The watchdog (heartbeat.ps1) exits when root task status = `done`. No heartbeat for 300s = stall → rotate sampler.