---
name: spec-new
description: Open a new feature or bugfix spec and draft its first artifact (requirements.md in EARS, or bugfix.md). Sets it as the active spec.
disable-model-invocation: true
argument-hint: "<name> [--fix] [--scope GLOB ...]"
allowed-tools: Bash(python C:/Users/user/.claude/hooks/spec_state.py *) Read Glob Grep Write Edit
---

# /spec-new $ARGUMENTS

Open a spec and draft its first artifact. This is phase 1 of 3.

## Lanes

| Invocation | Lane | First artifact |
|---|---|---|
| `/spec-new user-login` | feature | `requirements.md` — user stories + EARS acceptance criteria |
| `/spec-new npe-on-save --fix` | bugfix | `bugfix.md` — current / expected / unchanged behavior |

## Steps

1. Create the record:

   ```
   python C:/Users/user/.claude/hooks/spec_state.py new $ARGUMENTS
   ```

   Names are lowercase kebab-case. `--scope 'src/api/**/*.py'` declares which files
   the spec will authorize; omit it for unrestricted, and prefer declaring it once
   you know — an unscoped spec unlocks the whole repo.

2. Read `.spec/steering/*.md` first. Every spec inherits that context; a spec that
   contradicts steering is a defect in one of the two, and you should say which.

3. **Draft the artifact using the `spec` skill.** Invoke it — do not improvise
   notation. It owns EARS conditional clauses, the four spec layers, and the
   rendered-artifact format. This skill owns the *lifecycle*; `spec` owns the
   *grammar*. Write the result to:

   - feature: `.spec/specs/<name>/requirements.md`
   - bugfix: `.spec/specs/<name>/bugfix.md`

4. State in one line which spec layer governs (Requirements / Structural /
   Behavioral / Rendered), per CLAUDE.md §7.

5. Stop. Do **not** draft design.md, and do **not** touch source. Report what you
   wrote and that the operator must review it and run `/spec-approve requirements`.

## The gate

You cannot approve your own work — `/spec-approve` is operator-only by the same
`disable-model-invocation` field that governs this file. Phase advancement without
a human stamp is the exact failure this workflow exists to prevent.
