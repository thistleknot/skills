---
name: build-observability
description: >
  Live build observability protocol for agentic systems. Invoke when long-running
  agent execution needs a normalized runs/events/commands model, a build dashboard,
  a runtime collector, and trace enrichment that feeds memory and decision graphs.
status: active
last_validated: 2026-05-02
supersedes: []
validation_method: session
---

# Build Observability

## Purpose

Use this skill when instrumenting an agentic system so build progress becomes
visible, auditable, and queryable while the run is still alive.

This is **run-centric observability**, not generic infra telemetry. The contract
is to answer: what is running, what just happened, what changed, what artifacts
exist, who did it, and how the run ended.

## Core Contract

### 1. Normalize runtime state into `runs`, `events`, and `commands`

Treat these as the portable backbone:

- `runs` — one row per top-level or child agent run; carries stage, status,
  owner, timestamps, parent/child linkage, and deploy outcome
- `events` — timeline facts emitted during a run: stage transitions, file
  changes, artifact creation, decisions, handoffs, retries, and failures
- `commands` — executable command lifecycle: queued, started, streaming,
  succeeded, failed, cancelled, or timed out

Minimum shape:

```text
runs(
  run_id, parent_run_id, task_id, owner, status, current_stage,
  started_at, finished_at, deploy_outcome
)

events(
  event_id, run_id, timestamp, event_type, stage, status, owner,
  summary, file_path, artifact_path, command_id
)

commands(
  command_id, run_id, owner, argv, cwd, lifecycle_state,
  started_at, finished_at, exit_code
)
```

Keep the core schema normalized and stable. Add aux tables only when a query
surface cannot be expressed cleanly from event projections.

### 2. Make the dashboard answer operator questions, not just show logs

The dashboard surface should expose:

- current stage
- timeline of major events
- live/recent command activity
- changed files
- artifact list
- sub-agent hierarchy
- deploy outcome

If a human cannot reopen the run and answer those questions quickly, the schema
or projection layer is incomplete.

### 3. Use a runtime collector that projects local runtime artifacts into the schema

Do not bind the skill to one agent framework's storage layout.

Use a collector adapter that:

1. reads agent-owned runtime files, transcripts, logs, or session metadata
2. derives canonical run/event/command facts from them
3. projects those facts into the observability schema
4. leaves source files as the raw audit trail

The OpenClaw-specific collector is a pattern, not a portability target. Rebuild
the adapter for the local runtime instead of hard-coding foreign paths.

### 4. Enrich traces so observability can feed memory and decision layers

Operational telemetry is more useful when it carries decision context.

Enrich projected events with:

- decision summaries
- task or story identifiers
- artifact references
- branch/worktree or session identifiers
- feature IDs when a run implements or updates a known feature

This turns a run log into source material for episodic memory and context-graph
systems: what happened, when, and why.

### 5. Default to SQLite; use Postgres when shared or remote access is needed

- **SQLite first** for local harnesses, single-operator sessions, and checkpointed
  observability that should work without extra services
- **Postgres when available** for multi-user dashboards, remote API surfaces,
  or cross-process readers/writers

The storage backend may change; the `runs/events/commands` contract should not.

## Integration Boundaries

### Relation to `agentic-harness`

`agentic-harness` owns execution, control flow, gating, retries, and artifact
production. `build-observability` reads that control-plane exhaust and renders it
queryable. Do not replace harness control logic with the observability layer.

### Relation to `feature-catalog`

`feature-catalog` is the implementation ledger: what exists, what files map to
which features, and what architectural decisions were taken. `build-observability`
records what a specific run changed and produced. Link runs to feature IDs when
possible; do not collapse the feature ledger into transient run data.

### Relation to memory / context-graph systems

Observability traces are episodic inputs. Decision-bearing events can be promoted
into memory-side stores or graph nodes after the run, but the live observability
store remains the operational record of execution.

## Recommended Projection Pattern

```text
runtime files / transcripts / logs
        ↓
collector adapter
        ↓
canonical run + event + command facts
        ↓
sqlite or postgres store
        ↓
dashboard / API / downstream memory enrichment
```

Keep the collector append-friendly and idempotent. Replaying the same source
material should update or de-duplicate by stable runtime IDs, not fork phantom runs.

## Anti-Patterns

- Porting a framework-specific collector path as if it were universal
- Mixing decision events, file changes, and command lifecycle into one opaque log blob
- Making Postgres mandatory for a local-only harness
- Treating the dashboard as a pretty log viewer instead of an operator surface
- Storing only raw transcripts with no projection into queryable run state

## Applicability Envelope

**Works well when:**
- A harness or agent runtime emits session files, transcripts, logs, or command records
- Humans need live visibility into stage progression, file changes, artifacts, or deploy status
- A local-first stack wants SQLite now with a path to Postgres later
- Decision traces should later feed episodic memory or context-graph layers

**Fails or degrades when:**
- The runtime emits no durable artifacts to collect from
- Runs cannot be assigned stable IDs or parent/child relationships
- The system needs infra metrics/APM rather than build/run observability
- The collector is tightly coupled to one foreign runtime layout and cannot be adapted

**Environment assumptions:**
- The agent system already has an execution backbone such as `agentic-harness`
- Runtime artifacts exist at known paths or via a known session API
- A local SQL store is available; shared deployments may additionally provide Postgres
<!-- consolidation:see-also:start -->
## See Also
[[agentic-harness]]  [[agentic_kg_memory]]  [[react-agent]]  [[skill-wiki]]  [[memory-bank]]
<!-- consolidation:see-also:end -->
