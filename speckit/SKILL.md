---
name: speckit
description: "GitHub Spec Kit (specify CLI) entry point: bootstrap a project with `specify init`, then drive spec-driven development through the speckit-* skills in order (constitution, specify, clarify, plan, tasks, analyze, implement). Use when the user says spec-kit, speckit, /speckit-*, .specify, or wants constitution/spec/plan/tasks files for a feature."
---

# speckit — Spec Kit as a first-class SDD workflow

Source of truth: github.com/github/spec-kit (CLI installed with `uv tool install` from a clone; check `specify version`). The ten `speckit-*` skills beside this one are the stock command set, copied unmodified from `specify init --integration claude`.

## Unified process, host-specific delivery (CURRENT 2026-11-02)

Run one Spec Kit lifecycle for the project: constitution → specify → clarify → plan → tasks → analyze → implement. Keep the specification and task artifacts canonical; adapt only how each host installs, invokes, and verifies the skills.

- Claude Code uses its plugin mechanism and `/plugin` commands where the workflow is distributed as a plugin.
- Codex does not use Claude's `/plugin` command. It discovers skill folders from `$HOME/.agents/skills` and repository `.agents/skills`; invoke a skill by `$skill-name`, `/skills`, or task intent as the host supports. The current [Codex skills guide](https://developers.openai.com/codex/skills) owns its exact paths and commands.
- For AI Unified Process, the current [Tessl guide](https://github.com/AI-Unified-Process/marketplace/blob/main/docs/installation/tessl.md) supports `tessl init --agent codex`, then `tessl install ai-unified-process/aiup-core` plus the project’s selected layer packages and dependencies. The [manual guide](https://github.com/AI-Unified-Process/marketplace/blob/main/docs/installation/other-agents.md) says to copy or symlink whole skill folders into the host’s scanned location and translate each plugin’s MCP configuration; `~/.codex/skills` from the screenshot is not the current documented Codex skill path.
- Start the host in the target project and make a small intent-level request, such as creating the requirements catalog from `docs/vision.md`. Confirm it discovered the expected skill and read the project input before calling setup complete.
- Verify the installed skill through that host's own discovery surface and a small intent-level request. A shared MCP retrieval index proves index visibility only; it does not prove Codex's native skill files were installed or discovered.

This keeps the phase sequence common while making the delivery adapter-specific; a host's command syntax is not a second lifecycle.

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
