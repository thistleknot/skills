---
name: spec-status
description: Show the spec-driven state of this repo — active spec, phase, approvals, declared scope, remaining tasks, and whether the gate is bypassed.
disable-model-invocation: true
argument-hint: "(no arguments)"
allowed-tools: Bash(python C:/Users/user/.claude/hooks/spec_state.py *) Read
---

# /spec-status

Report where the spec workflow stands.

```
python C:/Users/user/.claude/hooks/spec_state.py status
```

Output covers: spec root, bypass state, the ACTIVE pointer, and per spec its kind,
phase, approval stamps (`requirements+ design- tasks-`), declared scope, and count
of unchecked tasks.

## Reading it

| You see | It means |
|---|---|
| `not spec-driven` | No `.spec/` here. The gate is inactive — run `/spec-init` to arm it |
| `Bypassed: YES` | `.spec/BYPASS` exists or `SPEC_GATE=off`. Edits are unchecked. Say this plainly; a silently disarmed gate is the worst state to be in |
| `ACTIVE: (unset)` | The gate infers the spec only if exactly one has reached `implement`. Two or more is ambiguous and everything is denied |
| `phase=implement` | Source edits are unlocked, limited to the declared scope |

If the operator is blocked by the gate and does not know why, run this first — the
deny message names the missing approval, and this names everything else.
