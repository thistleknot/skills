---
name: speckit
description: "GitHub Spec Kit (specify CLI) entry point: bootstrap a project with `specify init`, then drive spec-driven development through the speckit-* skills in order (constitution, specify, clarify, plan, tasks, analyze, implement). Use when the user says spec-kit, speckit, /speckit-*, .specify, or wants constitution/spec/plan/tasks files for a feature."
---

# speckit — Spec Kit as a first-class SDD workflow

Source of truth: github.com/github/spec-kit (CLI installed with `uv tool install` from a clone; check `specify version`). The ten `speckit-*` skills beside this one are the stock command set, copied unmodified from `specify init --integration claude`.

## Bootstrap a project (once per repo)

```
specify init --here --force --non-interactive --ignore-agent-tools --integration claude
specify init --here --force --non-interactive --ignore-agent-tools --integration codex --integration-options="--skills"
```

This writes `.specify/` (templates, PowerShell scripts, workflow, `memory/constitution.md`) into the repo. Every speckit-* skill calls `.specify/scripts/powershell/*.ps1` from the repo root, so a repo without `.specify/` cannot run them. The per-harness skill copies (`.claude/skills/speckit-*`, `.agents/skills/speckit-*`) are redundant with the global store; delete them from the project if both load.

## Order

1. `speckit-constitution` — project principles, written to `.specify/memory/constitution.md`.
2. `speckit-specify` — feature spec (what and why, no stack).
3. `speckit-clarify` — resolve `[NEEDS CLARIFICATION]` markers.
4. `speckit-plan` — technical plan and design artifacts.
5. `speckit-tasks` — dependency-ordered task list.
6. `speckit-analyze` — read-only cross-artifact consistency check. Optional: `speckit-checklist`.
7. `speckit-implement` — execute tasks. `speckit-taskstoissues`, `speckit-converge` follow stock behavior.

Invocation prefix differs by harness: `/speckit-plan` in Claude Code, `$speckit-plan` in Codex.

## Seams with the local SDD rules

- Local gate (`spec_gate.py`) and `spec-*` skills use `.spec/`. Spec Kit uses `.specify/` and `specs/<NNN-feature>/`. They are separate lifecycles; the gate does NOT read `.specify/`.
- Constitution conflict: Spec Kit's `.specify/memory/constitution.md` is per project and non-negotiable inside its commands; it does not replace `~/.harness/constitution.md`. Keep both; do not copy one over the other.
- Notation (EARS, Given/When/Then) lives in the `spec` skill; use it inside a speckit spec when requirements need testable clauses.
