---
name: continuity-log
description: >
  Compact-safe working-memory protocol. Use during long or multi-turn tasks to
  persist distilled decisions, rejected approaches, blockers, and resume points
  to disk so future turns or post-compaction resumes do not repeat the same
  analysis. This is not a raw chain-of-thought capture skill.
status: active
last_validated: 2026-04-28
---

# Continuity Log Protocol

## Core Thesis

You do not need verbatim hidden thought tokens on disk.
You need **compact-safe decision packets** that preserve the outcome of thinking.

This skill exists to prevent repeated analysis after:

- context compaction
- long autonomous runs
- multi-agent handoffs
- pauses between sessions

## What This Skill Is

This skill stores:

- the current objective and scope
- decisions that were made
- alternatives that were rejected
- key evidence that justifies those decisions
- blockers, risks, and unresolved questions
- the exact resume point for the next turn

## What This Skill Is Not

Do **not** use it to store:

- raw hidden chain-of-thought
- every micro-thought or speculative branch
- sensitive data copied without need
- freeform diary entries with no operational value

Persist the **result of reasoning**, not the private scratchpad.

## Relationship to Other Skills

Treat the memory stack like this:

```text
memory-bank     -> durable project facts and long-lived context
todo            -> actionable queue and dependencies
react-agent     -> execution loop, progress, evidence
continuity-log  -> between-compaction decision packets and resume notes
agentic-harness -> run-control artifacts for multi-agent systems
```

If `memory-bank` is the project memory and `todo` is the task queue,
`continuity-log` is the compact-safe working notebook.

## Preferred File Locations

Use the narrowest scope that still survives the task boundary:

1. session-local continuity note under the session artifact folder
2. `.react_agent\\continuity.md` when `react-agent` is active
3. task-specific artifact folder if the project already has a designated evidence location

Do not scatter continuity packets across arbitrary files.

## When to Write

Write a continuity entry when:

1. a load-bearing decision is made
2. a hypothesis is disproven and should not be retried blindly
3. a long command or multi-step run produces an important result
4. context is getting full and compaction risk is rising
5. work is about to pause or hand off to another agent

If a future turn would otherwise need to reconstruct the reasoning from scratch,
write the packet now.

## Entry Format

Use a timestamped block with explicit fields:

```markdown
### 2026-04-23 19:30 - routing decision
- Objective: decide whether cluster routing should be mixture-based
- Decision: keep cluster mixture budgeting, then use MMR within each slice
- Evidence:
  - initial cosine ranking covered multiple clusters
  - single-cluster retrieval reduced recall
- Rejected alternatives:
  - single winning cluster only -> too narrow
  - equal allocation across all clusters -> too noisy
- Blockers: none
- Resume from: implement scoring contract in `agentic_kg_memory\SKILL.md`
- Artifacts: `plan.md`, `agentic_kg_memory\SKILL.md`
```

## Minimum Content Contract

Each entry should answer:

- **What problem are we solving right now?**
- **What did we decide?**
- **Why did we decide it?**
- **What did we rule out?**
- **Where should the next turn resume?**

If any of those is missing, the packet is probably too thin to prevent rework.

## Read Protocol

Before resuming a paused task:

1. read the latest continuity entry
2. reconcile it with `task.md`, `plan.md`, `progress.md`, or repo artifacts
3. confirm whether the resume point is still valid
4. append a new entry if the plan has changed

Do not overwrite prior continuity entries. Append and preserve history.

## Compression Rule

Good continuity logs are **lossy in the right way**:

- keep decisions
- keep evidence
- keep dead ends worth remembering
- drop filler
- drop internal narration

Aim for something a future agent can reload in under a minute.

## Anti-Patterns

Avoid:

- copying hidden reasoning verbatim
- logging every small branch of thought
- saving conclusions without the evidence that justified them
- overwriting old entries instead of appending
- writing packets that do not contain a clear resume point

## Minimal Output Contract

When using this skill, the final answer should make clear:

- where the continuity packet was written
- what decision or state it preserves
- what the next turn should read first