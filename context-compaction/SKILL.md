---
name: context-compaction
description: >
  Active context-window management for long agentic runs: tiered memory eviction,
  automatic summarization triggers, and pre/post-compaction lifecycle hooks.
  Use when a session approaches its context limit or when resuming a long-running
  task across turns. Complements continuity-log (which distills decisions);
  this skill manages the mechanics of eviction and rehydration.
status: active
last_validated: 2026-04-28
---

# Context Compaction

## When to Use

Use this skill when:

- A session is approaching its context window limit (token count > 70% of model max)
- Resuming a long-running task where prior turns must be summarized without losing critical state
- Designing a harness that will run for many turns autonomously and must not degrade gracefully
- Building a MemGPT-style tiered storage system (fast → slow → archive)

Do **not** use for:
- Short sessions (< 30 turns) — the overhead exceeds the benefit
- Deciding *what* to remember (that is `continuity-log`); this skill covers *how* to evict and rehydrate

---

## Tiered Memory Model (MemGPT-inspired)

```
┌─────────────────────────────────────────────────┐
│  In-context (fast) — active working memory       │  Token cost: high
│  Current task state, recent tool calls, plan    │  Freshness: immediate
└───────────────────┬─────────────────────────────┘
                    │ evict on overflow
                    ▼
┌─────────────────────────────────────────────────┐
│  External (slow) — persistent summarized store   │  Token cost: low at rest
│  Compacted turn summaries, decision log,        │  Freshness: at recall
│  artifact references, open questions            │
└───────────────────┬─────────────────────────────┘
                    │ archive on expiry / low access frequency
                    ▼
┌─────────────────────────────────────────────────┐
│  Archive — cold storage                          │  Token cost: none
│  Raw turn transcripts, full tool call logs      │  Freshness: offline
└─────────────────────────────────────────────────┘
```

The in-context tier holds only what is needed for the current reasoning step. Everything
else is pushed to external storage and recalled on demand.

---

## Context Budget

**Hard budget: compacted instructions + memories ≤ ~4k tokens at session start.**

- Copilot instructions + AGENTS.md injection is the baseline cost — keep it compact.
- Memory reads at session start must be *targeted*, not bulk dumps.
  - Do **not** call `list_memory()` or equivalent without a specific question.
  - Use the L2→L1→L0 cascade: grep/index lookup first, BM25 second, full read last.
- Each list item in any CompactionPacket field is one sentence max — this is also the
  storage unit in the broader framework (atomic list elements, never chunked documents).

If instructions + memories exceed 4k tokens before any task work begins, compact memory
before proceeding.

---

## Compaction Triggers

| Trigger | Threshold | Action |
|---|---|---|
| Token budget | > 70% of model max | Run PreCompact hook; emit compact summary |
| Turn count | > N turns without compaction | Force compaction |
| Task boundary | On entering a new major task phase | Compact prior phase; rehydrate only what the new phase needs |
| Explicit signal | Agent emits `COMPACT_NOW` sentinel | Immediate compaction |

---

## PreCompact Hook Contract

Before a compaction fires, the PreCompact hook collects the most valuable state to
preserve. This hook runs **in-context** while there is still room.

```python
class CompactionPacket(BaseModel):
    """
    The distilled state to carry across a context boundary.
    Require: written before context limit is reached.
    Guarantee: on reload, the agent can resume without re-deriving these items.
    """
    session_id: str
    task_summary: str               # ≤ 3 sentences: what the task is and current phase
    decisions: list[str]            # key decisions made; each ≤ 1 sentence
    open_questions: list[str]       # unresolved; each ≤ 1 sentence
    artifacts: list[ArtifactRef]    # files/objects produced; path + one-line description
    next_steps: list[str]           # ordered; top-3 immediate actions
    do_not_redo: list[str]          # approaches already tried and failed
    compacted_at: datetime

class ArtifactRef(BaseModel):
    path: str
    description: str
    status: Literal["complete", "partial", "needs_review"]
```

The `do_not_redo` list is the most frequently missed field. Without it, agents repeat
failed approaches after compaction.

---

## PostCompact Hook Contract

After compaction, the PostCompact hook rehydrates the agent's context from the
`CompactionPacket`. It must restore enough state for the agent to continue without
the user re-explaining the task.

```python
def build_rehydration_prompt(packet: CompactionPacket) -> str:
    """
    Constructs the system prompt suffix injected after compaction.
    Guarantee: agent can answer 'what am I doing and what's next?' from this alone.
    """
    lines = [
        f"## Resumed Session (compacted at {packet.compacted_at})",
        f"**Task:** {packet.task_summary}",
        "",
        "**Decisions made:**",
        *[f"- {d}" for d in packet.decisions],
        "",
        "**Open questions:**",
        *[f"- {q}" for q in packet.open_questions],
        "",
        "**Artifacts produced:**",
        *[f"- {a.path} [{a.status}]: {a.description}" for a in packet.artifacts],
        "",
        "**Do NOT redo (already tried and failed):**",
        *[f"- {x}" for x in packet.do_not_redo],
        "",
        "**Next steps:**",
        *[f"{i+1}. {s}" for i, s in enumerate(packet.next_steps)],
    ]
    return "\n".join(lines)
```

---

## Claude Code Compaction Integration

Claude Code fires compaction hooks via `CLAUDE.md` entries:

```markdown
## Hooks

### PreCompact
Before any context compaction:
1. Write a CompactionPacket to `.session/compact_{timestamp}.json`
2. Log current task phase and top-3 blockers

### PostCompact
After context compaction:
1. Read the most recent `.session/compact_*.json`
2. Inject rehydration prompt as the first user message in the new context
3. Confirm: "Resumed from compact at {timestamp}. Current task: {summary}"
```

---

## Relationship to continuity-log

| Concern | Skill |
|---|---|
| *What* to preserve across turns | `continuity-log` |
| *When* to compact and *how* to evict/rehydrate | `context-compaction` (this skill) |
| Long-term project state (survives session resets) | `memory-bank` |

These three work as a stack: `memory-bank` is the disk, `context-compaction` is the OS
pager, and `continuity-log` is the programmer deciding what to write to disk.

---

## Failure Modes

| Symptom | Root cause | Fix |
|---|---|---|
| Agent loses task state after compaction | PreCompact hook not fired | Check trigger threshold; force PreCompact before limit |
| Agent redoes failed approaches | `do_not_redo` not populated | Make `do_not_redo` a required field in CompactionPacket |
| Rehydration prompt is too long to fit | Summary not compressed enough | Enforce ≤ 3 sentences for `task_summary`; ≤ 1 sentence per list item |
| Artifact references are stale after compaction | Files moved/renamed | Use relative paths from repo root; validate on rehydration |
| Compaction fires too early | Threshold set too low | 70% is conservative; raise to 80% if false-positive rate is high |

---

## Evidence

- MemGPT arXiv:2310.08560: OS-inspired hierarchical memory (fast/slow/archive) with paging semantics
- Claude Code: PreCompact/PostCompact hook lifecycle documented in Claude Code CLAUDE.md conventions
- CoALA arXiv:2309.02427: working memory eviction to episodic store as a cognitive architecture primitive
<!-- consolidation:see-also:start -->
## See Also
[[memory-architecture]]  [[memory-bank]]  [[continuity-log]]  [[agentic_kg_memory]]  [[agentic-harness]]
<!-- consolidation:see-also:end -->
