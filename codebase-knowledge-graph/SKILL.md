---
name: codebase-knowledge-graph
description: >
  Codebase-oriented whole-system reasoning protocol. Use when an agent must
  understand an existing repository as an interconnected graph before editing,
  so it can distinguish foundational from incidental code, avoid duplicate
  functionality, and anticipate ripple effects across modules, files, classes,
  and functions.
status: active
last_validated: 2026-05-02
supersedes: []
validation_method: session
---

# Codebase Knowledge Graph

## Core Thesis

**Do not treat a codebase as a bag of files. Treat it as a typed graph.**

LLMs fail in large repositories for a repeatable reason: they read locally and
edit locally, but the real system behavior is determined by relationships.
Senior developers maintain a mental model of those relationships before they
change anything. This skill makes that protocol explicit.

## When to Invoke

Invoke this skill when the task involves:

- modifying an existing codebase where the change may cross module boundaries
- deciding whether to reuse, extend, or replace existing functionality
- identifying which code is foundational vs incidental before an edit
- checking ripple effects before refactors, migrations, or bug fixes
- recovering whole-repo context after context loss in a large codebase

Do **not** invoke this skill for greenfield architecture design or long-term
cross-session memory maintenance.

## Graph Model

Model the repository as a hierarchy of typed nodes with semantic edges:

- **Nodes:** module, file, class, function
- **Hierarchy edges:** contains, defines, owns
- **Behavior edges:** imports, calls, constructs, persists, configures, tests

The point is not a perfect static-analysis graph. The point is a working system
map good enough to answer:

1. What is load-bearing here?
2. What already exists that this change should extend?
3. What breaks or drifts if this node changes?

## Protocol

### 1. Build the map before proposing edits
- Start from the target area, then walk upward and outward
- Identify parent modules, sibling implementations, callers, callees, tests,
  configs, and data boundaries
- Prefer relationship discovery over line-by-line accumulation

### 2. Separate foundational from incidental code
- **Foundational:** interfaces, shared abstractions, central data models,
  routing/orchestration seams, widely reused utilities, contract-defining tests
- **Incidental:** leaf formatting, isolated helpers, thin adapters, one-off glue

Do not edit foundational code as if it were local implementation detail.

### 3. Run ripple analysis before code changes
For any proposed edit, inspect at least:

- upstream callers
- downstream dependencies
- adjacent implementations following the same pattern
- config / schema / storage boundaries
- tests that encode the intended contract

If the ripple surface is unclear, keep exploring before editing.

### 4. Resolve reuse before creation
Before adding code, answer:

- Does equivalent functionality already exist?
- Is there an established abstraction this belongs under?
- Is the current pattern intentional or accidental?

If the answer is unclear, bias toward more graph discovery, not faster writing.

### 5. Hand off to the right neighboring skill

| Need | Skill |
|---|---|
| Whole-repo relationship map before editing | `codebase-knowledge-graph` |
| Implementing or modifying code once the target seam is known | `code` |
| Designing new system structure or abstractions from first principles | `architecture` |
| Persisting evolving knowledge across sessions in a semantic memory layer | `agentic_kg_memory` |

This skill is **codebase-oriented reasoning for the current repository state**,
not a durable memory store and not a greenfield design method.

## Anti-Patterns

- treating files as independent just because they are in different directories
- generating duplicate functionality because reuse seams were not searched
- copying a pattern from one leaf without checking whether it is canonical
- editing foundational code without tracing contract edges first
- assuming local correctness implies system correctness

## Applicability Envelope

**Works well when:**
- the repository already exists and has meaningful structure to inspect
- the task touches multiple files or could affect established patterns
- the agent can search the repo for callers, implementations, tests, and configs

**Fails or degrades when:**
- the repo is tiny enough that a graph adds no value over direct inspection
- generated or vendored code dominates the tree and obscures true ownership
- the graph is inferred from too little evidence and treated as certain

**Environment assumptions:**
- repo tree and file contents are readable
- search tools can inspect imports, references, and tests
- the agent can pause implementation long enough to map the dependency surface
