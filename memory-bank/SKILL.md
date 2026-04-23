---
name: memory-bank
description: >
  Operational project memory for long-running work. Use when reading or updating
  project brief, product context, active context, system patterns, tech context,
  and progress so work survives session resets and resumes cleanly.
---

# Memory Bank

## Scope Boundary

This skill is for **project and session continuity**.

It is not the semantic-memory graph.

Use `memory-bank` for:
- project onboarding
- restoring context after a reset
- current focus, blockers, and next steps
- architecture and stack decisions
- progress checkpoints across sessions

Do **not** use `memory-bank` for:
- triplet extraction
- corpus retrieval
- NLI premise validation
- throughline ranking
- graph edge reinforcement

Those belong to `agentic_kg_memory`.

## Canonical Files

Read and maintain these six files:

1. `projectbrief.md`
2. `productContext.md`
3. `activeContext.md`
4. `systemPatterns.md`
5. `techContext.md`
6. `progress.md`

## What Each File Stores

### `projectbrief.md`
- project purpose
- hard requirements
- out-of-scope boundaries

### `productContext.md`
- why the project exists
- user-facing goals
- success criteria from the operator's point of view

### `activeContext.md`
- current focus
- recent changes
- active decisions
- immediate next steps

### `systemPatterns.md`
- architecture
- design patterns
- component relationships
- implementation constraints that keep recurring

### `techContext.md`
- stack
- dependencies
- environment assumptions
- setup commands and technical constraints

### `progress.md`
- what works
- what remains
- known issues
- milestone history

## Read Protocol

At task start:
- read all six files
- build a coherent picture before acting
- treat missing files as a memory gap that should be repaired

## Write Protocol

Update the memory bank when:
- a significant feature or fix lands
- an architectural decision changes
- a blocker is discovered or resolved
- the resume point for a future session changes
- the user explicitly asks to update memory

## Writing Rules

- Keep entries factual and concise
- Append dated milestones rather than rewriting history away
- Prefer stable operating context over transient scratch notes
- Capture decisions and their consequences, not just actions taken
- Record resume points explicitly so a future session can restart quickly

## Relation to KG Memory

The split is:

- `memory-bank` = **project operating memory**
- `agentic_kg_memory` = **semantic evidence memory**

`memory-bank` tells you:
- what project you are in
- what changed recently
- what matters next

`agentic_kg_memory` tells you:
- what the evidence says
- how pages and throughlines cluster
- which conclusions are currently strongest

If needed, the memory bank can reference page IDs, throughline IDs, or corpus
artifacts, but it should not become the graph itself.

## Anti-Patterns

Avoid:
- storing corpus triplets in the memory bank
- using progress.md as a retrieval index
- mixing project-state notes with evidence-level conclusions
- rewriting history instead of appending milestone context
- keeping only chat-local context when a stable file belongs in memory-bank

## Minimal Output Contract

When using this skill, report:
- which memory-bank files were read or updated
- what project-state fact changed
- what the new resume point is
- any blocker or decision that future sessions must inherit
