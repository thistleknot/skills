---
name: multi-agent-coordination
description: >
  Multi-agent team patterns for autonomous software development: peer-to-peer
  agent messaging, plan-approval gates, shared task ownership with file-locks,
  dynamic sub-agent spawning. Use when a task exceeds single-agent context or
  requires parallel specialised work streams. Covers topology selection,
  communication protocols, conflict resolution, and observability.
status: active
last_validated: 2026-04-28
---

# Multi-Agent Coordination

## When to Use

Use multi-agent coordination — not a single agent with more context — when:

- The task naturally decomposes into **independent sub-problems** that can run in parallel
- Different sub-problems require **different expertise** (coding, testing, security, docs)
- **Context would overflow** a single agent's window for the full task
- **Verification by a peer** is required before a sub-result is accepted (reviewer != author)

Do **not** use when:
- Tasks are sequentially dependent and benefit from shared context → use `agentic-harness` pipeline
- A single agent with tool access is sufficient → cheaper and simpler
- Coordination overhead would exceed the parallelism benefit (rule of thumb: < 3 agents = overkill for multi-agent)

---

## Topology Selection

Choose the topology before wiring agents:

| Topology | Shape | Best for |
|---|---|---|
| **Orchestrator → Workers** | Hub-and-spoke | Tasks with clear decomposition; orchestrator assigns, workers execute |
| **Pipeline** | Linear chain | Sequential transformation: spec → code → test → review |
| **Peer Network** | Fully connected | Open-ended exploration; agents propose + critique each other |
| **Hierarchical** | Tree | Epic → story → task breakdown; each level specialises |

The **Orchestrator → Workers** topology is the default for software development:
one orchestrator holds the plan and task list; specialised workers execute leaf tasks.

---

## Communication Protocol

### Mailbox Pattern (recommended)

Each agent owns a named inbox. Messages are structured and timestamped.

```python
class AgentMessage(BaseModel):
    msg_id: str           # ULID
    sender: str           # agent name
    recipient: str        # agent name or "broadcast"
    subject: str          # task_id or topic
    body: str             # instruction or result
    requires_ack: bool    # whether sender blocks waiting for reply
    sent_at: datetime

class AgentMailbox:
    """
    Require: agent_name is unique across the team.
    Guarantee: messages are delivered in FIFO order per sender.
    Maintain: inbox is append-only; processed messages are archived, not deleted.
    """
    def post(self, msg: AgentMessage) -> None: ...
    def receive(self, recipient: str) -> list[AgentMessage]: ...
    def ack(self, msg_id: str) -> None: ...
```

### Plan-Approval Gate

Before any worker begins a sub-task, the orchestrator must **approve the plan**:

```
worker proposes plan → orchestrator reviews → approve / reject with feedback
```

This gate prevents workers from charging down the wrong path. Keep it lightweight:
the plan is a 3-5 bullet checklist, not a prose essay. Reject if scope creep is detected.

---

## Shared Task List with Ownership

All agents read from and write to a shared task registry. Each task has exactly one owner.

```python
class TaskStatus(str, Enum):
    PENDING   = "pending"
    CLAIMED   = "claimed"     # owner set, not started
    IN_FLIGHT = "in_flight"   # actively being worked
    BLOCKED   = "blocked"     # dependency not met
    DONE      = "done"
    FAILED    = "failed"

class SharedTask(BaseModel):
    task_id: str
    title: str
    description: str
    depends_on: list[str]     # task_ids that must be DONE first
    owner: str | None         # agent name; None = unclaimed
    status: TaskStatus
    result_ref: str | None    # path/URL of the artifact produced
    lock_token: str | None    # optimistic lock; set on claim
```

**File-lock protocol:**

```python
def claim_task(registry, task_id: str, agent_name: str) -> bool:
    """Optimistic lock: CAS on lock_token. Returns True if claimed."""
    token = str(ULID())
    updated = registry.cas(
        task_id,
        expected={"owner": None, "status": TaskStatus.PENDING},
        new={"owner": agent_name, "status": TaskStatus.CLAIMED, "lock_token": token},
    )
    return updated
```

Never allow two agents to write to the same file simultaneously. Enforce this via the
task registry: each file path appears in at most one `IN_FLIGHT` task at a time.

---

## Dynamic Agent Spawning

Spawn sub-agents when the orchestrator detects a task that exceeds its own capabilities
or context budget:

```
orchestrator estimates task complexity
    │
    ├─ complexity < threshold  →  execute directly
    └─ complexity ≥ threshold  →  spawn specialist agent
                                      │
                                      ├─ pass: task description + relevant context slice
                                      ├─ receive: result_ref + structured summary
                                      └─ return result to orchestrator task registry
```

**Spawning contract:**
- The spawned agent receives a **bounded context slice** — not the full orchestrator context
- The spawned agent returns a **structured result** (pydantic model), not prose
- The orchestrator verifies the result passes its acceptance criteria before marking the task DONE

---

## Conflict Resolution

When two agents produce conflicting results for the same concern:

1. **Merge if compatible** — combine non-overlapping contributions
2. **Escalate to orchestrator** — orchestrator adjudicates using the original task spec
3. **Vote if peer network** — majority verdict; orchestrator breaks ties
4. **Re-run with explicit constraints** — if conflict is due to ambiguous spec, clarify and re-issue

Never silently drop a conflict. Log it in the team's shared `decisions.log`.

---

## Observability

Every agent action must be observable. Minimum instrumentation:

| Event | What to log |
|---|---|
| Task claimed | `agent_name`, `task_id`, timestamp |
| Plan proposed / approved / rejected | `task_id`, plan summary, verdict |
| Message sent | `msg_id`, `sender`, `recipient`, `subject` |
| Task completed | `task_id`, `result_ref`, elapsed_ms |
| Task failed | `task_id`, `error_class`, `error_msg` |
| Conflict detected | `task_id`, conflicting agents, resolution action |

Write to a shared `team.log` (append-only). The orchestrator reads this log to detect
stalled agents and re-assign tasks if an agent has been `IN_FLIGHT` for > `stall_timeout`.

---

## Anti-Patterns

| Anti-pattern | Consequence | Fix |
|---|---|---|
| Agents write to shared files without locks | Race conditions, corrupt output | File-lock via task registry |
| Orchestrator accumulates all worker context | Context overflow at orchestrator | Structured result summaries only; full artifacts go to `result_ref` |
| No plan-approval gate | Workers execute wrong plans | Gate every sub-task before execution |
| Workers send unstructured prose results | Orchestrator cannot parse results reliably | Mandate pydantic result schemas |
| Agents spawn agents that spawn agents unboundedly | Exponential cost | Set `max_spawn_depth` ≤ 2 |

---

## Evidence

- Claude Code multi-agent (Anthropic, 2025): orchestrator + parallel subagents; context window partitioning
- Society of Agents (SoA) arXiv:2404.02183: +5% HumanEval with peer-review topology
- Microsoft A2A protocol: agent-to-agent message routing standard (2025)
- Data Interpreter arXiv:2402.18679: +25% InfiAgent-DABench with hierarchical task graph decomposition