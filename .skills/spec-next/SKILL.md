---
name: spec-next
description: Advance the active spec to its next phase and draft that artifact — design.md, then tasks.md. Refuses if the current phase is unapproved.
disable-model-invocation: true
argument-hint: "(no arguments)"
allowed-tools: Bash(python C:/Users/user/.claude/hooks/spec_state.py *) Read Glob Grep Write Edit
---

# /spec-next

Move the active spec one phase forward and draft the artifact that phase owns.

`requirements|bugfix → design → tasks → implement`

## Steps

1. Check where you are:

   ```
   python C:/Users/user/.claude/hooks/spec_state.py status
   ```

2. Advance:

   ```
   python C:/Users/user/.claude/hooks/spec_state.py advance
   ```

   This **fails** if the current phase is unapproved. That failure is the gate
   working, not an error to route around — report it and stop. The operator runs
   `/spec-approve` when they are satisfied with the current artifact.

3. Draft the artifact for the new phase. Read the prior artifacts first; each phase
   builds on the one before, and a design that does not trace to a requirement is
   the defect this ordering exists to catch.

   **`design` → `.spec/specs/<name>/design.md`**
   Architecture, components and their contracts (Require / Guarantee / Maintain /
   Assert), data shapes, sequence of operations, and the decisions taken with their
   rationale. Name the incumbent code you intend to extend — per the anti-sprawl
   Gate A, a design that creates where an incumbent exists is a defect.

   **`tasks` → `.spec/specs/<name>/tasks.md`**
   A markdown checklist of discrete, independently verifiable steps:

   ```markdown
   - [ ] Add `resolve_active` to spec_paths.py with the sole-candidate fallback
   - [ ] Extend the battery with three scope-violation probes
   ```

   Each task names the file it touches and how it will be verified. Order them so
   dependencies come first. Use the `spec` skill for notation.

4. Reaching `implement` unlocks source edits for the declared scope. Say so
   explicitly when it happens, and restate the scope.

5. Stop after drafting. Approval is the operator's.
