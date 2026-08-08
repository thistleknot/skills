# OpenClaw Feature Topology

**Source:** `openclaw/openclaw` @ `b79548b1165d78d9a50951455db6c981a0c28268`  
**Clone:** `/tmp/openclaw-openclaw-20260502`  
**Purpose:** A local-first agent control plane that unifies sessions, tools, skills, sandboxes, plugins, channels, and external harness runtimes behind one long-lived gateway. For migration purposes, the most salient value is not the chat-surface breadth; it is the reusable control-plane architecture around agent execution.

---

## Topology Overview

```text
CONTROL PLANE LAYER ───────────────────────────────────────────────────────────
  gateway daemon
       │
       ├── typed WebSocket API
       ├── request/response + event stream
       ├── config validation + hot reload
       └── one long-lived authority for sessions, tools, channels, and events

AGENT ISOLATION LAYER ─────────────────────────────────────────────────────────
  agent
       │
       ├── workspace
       ├── agentDir (auth profiles, model registry, per-agent config)
       ├── session store
       └── bindings from channels/accounts/peers into isolated agent brains

SESSION + ORCHESTRATION LAYER ─────────────────────────────────────────────────
  session model
       │
       ├── per-session serialized run loop
       ├── transcript persistence
       ├── session tools (list/history/send/spawn/yield/status)
       ├── subagent orchestration
       └── background task ledger for detached work

HARNESS BRIDGE LAYER ──────────────────────────────────────────────────────────
  native runtime paths
  +
  ACP external-harness path
       │
       ├── claude
       ├── codex
       ├── copilot
       ├── cursor
       ├── gemini
       ├── opencode
       ├── pi
       └── other ACPX-backed harness ids

SKILLS + PROMPT LAYER ─────────────────────────────────────────────────────────
  AgentSkills-compatible skill loader
       │
       ├── precedence across workspace / personal / managed / bundled roots
       ├── per-agent allowlists
       ├── load-time gating by env/bin/config/OS
       ├── skill registry / install / update flow
       └── skill workshop / migration from Codex skill roots

PLUGIN / EXTENSION LAYER ──────────────────────────────────────────────────────
  plugin SDK
       │
       ├── provider registration
       ├── harness registration
       ├── tool / command registration
       ├── gateway methods / hooks / services
       ├── memory supplements / UI descriptors / runtime lifecycle hooks
       └── bundle adapters for Codex / Claude / Cursor ecosystems

SAFETY + EXECUTION LAYER ──────────────────────────────────────────────────────
  sandbox abstraction
       │
       ├── modes: off / non-main / all
       ├── scopes: agent / session / shared
       ├── backends: docker / ssh / openshell
       ├── browser sandbox
       └── elevated-tool escape path

RELIABILITY LAYER ─────────────────────────────────────────────────────────────
  lane queue + write locks
  model/auth failover
  task reconciliation
  compaction / pruning / maintenance

AUTOMATION LAYER ──────────────────────────────────────────────────────────────
  cron
  webhooks
  heartbeat
  hooks
  task notifications

EXPERIENCE LAYER ──────────────────────────────────────────────────────────────
  multi-channel inbox
  device pairing / nodes
  web/admin surfaces
  voice / canvas / mobile
```

---

## Feature Inventory

### CONTROL PLANE

**`gateway daemon`**  
One long-lived host-local control plane that owns messaging surfaces, sessions, tools, and events. It is the central authority rather than a thin CLI wrapper.

**`typed WebSocket API`**  
Requests, responses, and server-push events move over a typed WS protocol. Clients, nodes, and admin surfaces connect to the same gateway instead of inventing per-surface integration logic.

**`OpenClaw App SDK`**  
External apps, dashboards, CI jobs, IDE extensions, and scripts can connect via `@openclaw/sdk` to run agents, stream events, inspect sessions, invoke tools, and manage approvals.

**Migration value:** very high. This is one of the clearest transferable patterns for any agentic harness that wants a stable runtime boundary between embedded logic and external clients.

### AGENT ISOLATION

**`multi-agent routing`**  
An agent is a full scoped brain with its own workspace, auth profiles, model registry, and sessions. Bindings deterministically route incoming work to the correct agent.

**`per-agent workspace + state`**  
Each agent gets:
- workspace files
- `agentDir`
- session store
- auth profile store

This prevents cross-talk and makes persona/runtime boundaries explicit.

**Migration value:** very high. The concept generalizes cleanly to opencode, Pi, aider, and other harnesses that need multiple isolated working personas or tenants.

### SESSION MODEL

**`session routing model`**  
OpenClaw routes messages into sessions based on source type: DMs, groups, rooms, cron jobs, hooks, and nodes. Different sources get different isolation semantics.

**`session lifecycle + maintenance`**  
Sessions support daily reset, idle reset, manual reset, transcript storage, pruning, and bounded maintenance over time.

**`session tools`**  
Built-in agent tools provide cross-session introspection and orchestration:
- `sessions_list`
- `sessions_history`
- `sessions_send`
- `sessions_spawn`
- `sessions_yield`
- `subagents`
- `session_status`

**Migration value:** extremely high. This is a reusable execution contract for multi-session agent systems, not something specific to chat apps.

### AGENT LOOP + CONCURRENCY

**`serialized agent loop`**  
A run is the authoritative intake → prompt assembly → model inference → tool execution → persistence path, with lifecycle and stream events.

**`lane-aware command queue`**  
Runs are serialized per session and then capped globally through queue lanes. This avoids session races while still allowing bounded cross-session concurrency.

**`session write locks`**  
Transcript writes are guarded by explicit write locks in addition to queueing, catching out-of-band writers and preserving session consistency.

**Migration value:** extremely high. The queue/write-lock split is a strong pattern for any tool-using agent runtime with persisted transcripts.

### HARNESS BRIDGING

**`ACP agents`**  
OpenClaw has an explicit external-harness path via ACP/acpx. It can spawn and manage harness sessions for:
- `claude`
- `codex`
- `copilot`
- `cursor`
- `gemini`
- `opencode`
- `openclaw`
- `pi`
- additional ACPX-backed harnesses

**`runtime split: native vs ACP`**  
The system distinguishes native embedded runtimes from ACP-wrapped external harnesses instead of pretending every agent runtime is the same.

**`bound persistent harness sessions`**  
ACP sessions can be bound to a conversation/thread, steered, cancelled, resumed, and tracked as background tasks.

**Migration value:** highest-priority. This is directly relevant to your agentic-harness work because it shows how to normalize heterogeneous runtimes under one orchestration surface.

### SKILLS SYSTEM

**`AgentSkills-compatible skill loader`**  
Skills are directories with `SKILL.md`. OpenClaw supports multiple skill roots with deterministic precedence.

**`skill precedence + allowlists`**  
Skill location precedence and skill visibility are separate controls. An agent may see only an allowlisted subset of the winning skill definitions.

**`load-time skill gating`**  
Skills can be filtered by binary availability, env vars, config paths, OS, and related metadata before they ever reach the prompt.

**`skill install/update ecosystem`**  
ClawHub and local install/update flows make skills a first-class distribution surface, not a static prompt folder.

**`Codex skill migration`**  
OpenClaw explicitly supports inventorying and copying Codex skills into the current workspace.

**Migration value:** extremely high. The precedence/gating/allowlist model is broadly reusable.

### PLUGIN / EXTENSION SYSTEM

**`plugin SDK`**  
The typed in-process contract for providers, channels, tools, hooks, commands, services, UI descriptors, memory supplements, and runtime lifecycle hooks.

**`registerAgentHarness(...)` seam**  
The SDK includes an experimental low-level harness registration surface, which is especially relevant for migrating external runtimes into a common manager.

**`narrow import subpaths`**  
The SDK pushes small, explicit subpaths rather than a giant mutable barrel, reducing startup cost and circular coupling.

**`host hooks for workflow plugins`**  
Plugins can project session state, inject next-turn context, enforce trusted tool policy, register UI descriptors, and own scheduler jobs.

**Migration value:** very high. This is the extension seam story you would want when porting OpenClaw-like capabilities into a different harness.

### BUNDLE COMPATIBILITY

**`plugin bundles`**  
OpenClaw can ingest Codex-, Claude-, and Cursor-compatible bundle layouts and map them into native skills, hooks, MCP config, and LSP defaults.

**`selective mapping instead of full emulation`**  
Bundles are treated as narrower-trust content packs rather than as full native plugins.

**Migration value:** very high. This is a concrete interoperability pattern for pulling ecosystems together without demanding total rewrite.

### SAFETY / SANDBOXING

**`sandbox modes / scopes / backends`**  
Tool execution can be sandboxed by mode (`off`, `non-main`, `all`), scope (`agent`, `session`, `shared`), and backend (`docker`, `ssh`, `openshell`).

**`remote-canonical vs mirror workspace models`**  
OpenShell adds a strong distinction between local-canonical mirrored workspaces and remote-canonical sandboxes.

**`browser sandbox`**  
OpenClaw can optionally sandbox browser control separately, including CDP restrictions and observer access handling.

**Migration value:** very high. This is one of the strongest portable operational features in the repo.

### RELIABILITY / FAILOVER

**`model failover + auth profile rotation`**  
Failures are handled in two stages:
1. auth profile rotation within a provider
2. model fallback across configured candidates

**`selection source policy`**  
The fallback rules depend on why the model was selected: configured default, job primary, auto override, or explicit user session override.

**`cooldowns / disables / persistence`**  
The system records provider failures, cooldowns, and billing disables as durable runtime state rather than keeping retry logic implicit in one request loop.

**Migration value:** high. The operational logic is reusable even if the exact provider catalog is not.

### BACKGROUND ORCHESTRATION

**`background task ledger`**  
Detached work becomes a first-class tracked record with queued/running/terminal lifecycle and delivery policy. This covers ACP runs, subagents, cron jobs, and CLI operations.

**`push-based completion delivery`**  
Task completion is notification-driven rather than forcing the user into manual polling loops.

**`runtime-aware reconciliation`**  
Task maintenance checks runtime ownership and durable logs before declaring work lost.

**Migration value:** very high. This is broadly useful for agentic harnesses with detached work.

### AUTOMATION

**`cron scheduler`**  
Built into the gateway, with persistent jobs, isolated runs, delivery control, and model/tool overrides.

**`webhooks`**  
External triggers can enqueue work or directly run agent flows through authenticated hooks.

**`hooks`**  
There are both internal gateway hooks and plugin hooks across prompt, tool, lifecycle, and gateway boundaries.

**Migration value:** high. The scheduling and hook model is portable even if the messaging delivery surfaces are not.

### OPENCLAW-SPECIFIC EXPERIENCE LAYER

**`multi-channel inbox + DM pairing`**  
Strong product feature, but less central to harness migration unless the destination runtime also wants messaging-surface orchestration.

**`nodes / voice / canvas / mobile`**  
Interesting and powerful, but mostly outside the core agentic-harness migration target.

**Migration value:** partial / low for your current intent.

---

## Dependency Graph (edges)

```text
gateway daemon ──► typed WS protocol
typed WS protocol ──► App SDK / CLI / web UI / nodes

gateway daemon ──► session routing
session routing ──► session store
session store ──► session tools
session tools ──► subagents / ACP sessions / task ledger

agent loop ──► per-session queue lane
agent loop ──► transcript write lock
agent loop ──► prompt assembly
prompt assembly ──► skills snapshot

skills roots ──► precedence resolution
precedence resolution ──► allowlists + gating
allowlists + gating ──► effective prompt skill set

plugin SDK ──► providers / channels / tools / hooks / services / harnesses
bundle adapters ──► skills / MCP / hooks / settings / LSP defaults

ACP backend ──► external harness sessions
external harness sessions ──► background task ledger

sandbox config ──► docker / ssh / openshell backends
openshell ──► mirror mode / remote-canonical mode

auth profiles ──► provider rotation
provider rotation ──► model fallback
model fallback ──► persisted session override state

cron / webhooks / hooks ──► detached runs
detached runs ──► task notifications / reconciliation / cleanup
```

---

## Phase–Feature Matrix

| Phase | Features | Migration value |
|---|---|---|
| Control plane | gateway daemon, typed WS API, App SDK | Very high |
| Agent isolation | per-agent workspaces, agentDir, bindings | Very high |
| Session execution | session model, session tools, subagents | Extremely high |
| Concurrency safety | queue lanes, write locks, serialized loop | Extremely high |
| External harness integration | ACP agents, runtime split, bound sessions | Extremely high |
| Skill system | AgentSkills loader, precedence, gating, allowlists | Extremely high |
| Extensibility | plugin SDK, harness registration, host hooks | Very high |
| Ecosystem interop | Codex/Claude/Cursor bundle mapping | Very high |
| Safety | sandbox modes/scopes/backends, browser sandbox | Very high |
| Reliability | auth rotation, model failover, durable runtime state | High |
| Automation | cron, hooks, webhooks, task ledger | High |
| Product surfaces | channels, nodes, voice, canvas | Partial |

---

## Harness Adaptation Notes

1. **Highest-priority patterns to migrate into opencode / pi / aider-like harnesses:** gateway-style control plane, session tools, subagent/task ledger, queue/write-lock model, skills precedence/gating, and sandbox backend abstraction.
2. **Most relevant OpenClaw bridge feature:** ACP sessions as a normalized wrapper over heterogeneous external harnesses. This is the clearest reusable pattern for a multi-runtime manager.
3. **Strong interoperability idea:** bundle mapping for Codex / Claude / Cursor ecosystems. It lowers migration cost by translating content packs into native features instead of demanding full rewrites.
4. **Strong safety idea:** separate policy axes for location, visibility, tool profile, sandbox mode, sandbox scope, and plugin allowlists. OpenClaw avoids collapsing these into one coarse “safe/unsafe” switch.
5. **Strong runtime idea:** treat detached work as first-class tracked tasks with delivery, cleanup, and reconciliation rather than as anonymous background processes.
6. **Less relevant to immediate harness migration:** the huge multi-channel inbox, consumer/mobile node surfaces, voice wake, and canvas UX. They matter to OpenClaw as a product, but they are not the main transferable substrate for your harness work.

---

## Bottom-Line Classification

- **Most portable control-plane features:** gateway protocol, App SDK, session model, session tools, subagent/task ledger, sandbox abstraction
- **Most portable harness features:** ACP external harness path, plugin `registerAgentHarness` seam, bundle interoperability, skill precedence/gating
- **Most portable reliability features:** queue lanes, write locks, auth rotation, model fallback, runtime-aware reconciliation
- **Mostly OpenClaw-specific product surfaces:** chat-channel breadth, device nodes, voice, canvas, mobile companion features
