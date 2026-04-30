---
name: documentation
description: "Documentation strategy and artifact-selection protocol. Use when updating README/changelog/docs, choosing timestamped vs cumulative records, or producing validation and fixes-applied artifacts after substantive changes."
status: active
last_validated: 2026-04-30
supersedes: []
validation_method: session
---
# Documentation

## Contract

Documentation should match the change surface. Update the canonical document
first; create a new markdown artifact only when the change genuinely needs its
own durable record.

This skill governs **artifact choice and structure**, not code comments or
docstrings. `code` owns docstrings; this skill owns README/changelog/fix-note
decisions.

## When to Invoke

Invoke this skill when the task involves:

- updating `README.md`, release notes, changelogs, migration notes, or skill docs
- deciding between a cumulative changelog and a timestamped record
- producing a discrete validation or fixes-applied document after a large change
- documenting "what changed / what remains" for handoff or review

## Decision Order

Choose the smallest durable artifact that matches the need:

1. **Canonical doc first** — update the source of truth already used by the repo
   (`README`, spec, AGENTS, existing skill docs, existing ops docs).
2. **Cumulative changelog** — use `CHANGELOG.md` when the repo already keeps a
   running history and the update is routine or incremental.
3. **Timestamped file** — use `FIXES_APPLIED_YYYY-MM-DD.md` or
   `CHANGES_YYYY-MM-DD.md` only when an isolated record is genuinely useful.

## When Timestamped Files Win

Timestamped files are the right choice when at least one of these is true:

- a breakthrough session landed several critical fixes
- the change is a large architectural refactor or spans many files
- the user asked for a discrete "what was fixed / what is implemented" checklist
- parallel sessions need isolated records instead of one shared changelog

## When a Cumulative Changelog Wins

Prefer a single changelog when:

- the updates are routine or small
- the project benefits from one searchable chronological narrative
- the repo already relies on `CHANGELOG.md` as the public history surface

## Documentation Lifecycle

1. Update the canonical doc or changelog in the same change that alters behavior.
2. If a timestamped file is warranted, keep it focused on that session only.
3. If many timestamped files accumulate, consolidate them into a changelog or a
   `docs/changes/` structure the repository already uses.
4. Retire stale or duplicate records once the durable canonical document has
   absorbed the lasting information.

## Format Rules

- Lead with **impact**: what now works, what changed, what remains.
- Include exact commands, paths, or commit refs when they materially improve
  traceability.
- Use checklists for validation only when a checklist is actually the clearest
  shape.
- Prefer ASCII-safe markers unless the repo already uses Unicode status icons.
- Keep docs scoped: one document should answer one question well.

## Guardrails

- Do **not** create planning or scratch markdown by default; use the session
  workspace or structured trackers for that.
- Do **not** duplicate the same update across README, changelog, and timestamped
  notes unless each serves a different audience.
- Do **not** let documentation drift from real commands, file names, or current
  architecture.

## Output Checklist

Before you stop, confirm:

1. The chosen documentation artifact matches the size and purpose of the change.
2. The doc reflects the current code, commands, and paths exactly.
3. The reader can tell what changed, what now works, and what still remains.
