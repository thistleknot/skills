---
name: spec-init
description: Arm the current repository for spec-driven development by creating the .spec/ tree and its steering docs. Run once per repo.
disable-model-invocation: true
argument-hint: "(no arguments)"
allowed-tools: Bash(python C:/Users/user/.claude/hooks/spec_state.py *) Read Glob Grep Edit Write
---

# /spec-init

Make this repository spec-driven. After this runs, `spec_gate.py` denies edits to
source files until a spec reaches the approved `implement` phase.

## Steps

1. Confirm the working directory is the repo the operator means. If `git rev-parse
   --show-toplevel` disagrees with cwd, say so and stop — arming the wrong repo is
   annoying to undo.

2. Scaffold the tree:

   ```
   python C:/Users/user/.claude/hooks/spec_state.py init
   ```

   This creates `.spec/steering/`, `.spec/specs/`, stub steering docs, and adds
   `.spec/BYPASS` to `.gitignore`.

3. Fill in the three steering docs from what the repo actually contains — read
   before writing, do not invent:

   | File | Holds |
   |---|---|
   | `.spec/steering/product.md` | Purpose, who uses it, key capabilities |
   | `.spec/steering/tech.md` | Languages, frameworks, constraints, banned deps |
   | `.spec/steering/structure.md` | Directory layout, naming, architectural decisions |

   Derive these from the codebase, `README`, `CLAUDE.md`, and manifest files. Mark
   anything you inferred rather than observed. These are project-wide context that
   every later spec inherits, so a wrong entry here propagates.

4. Report what was created and tell the operator the gate is now live, naming the
   escape hatch: `touch .spec/BYPASS` or `SPEC_GATE=off`.

## Then

`/spec-new <name>` opens the first spec. Until one reaches `implement`, source
edits in this repo are denied.
