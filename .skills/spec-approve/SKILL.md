---
name: spec-approve
description: Operator approval of the active spec's current phase. This is the human gate that lets the workflow move forward.
disable-model-invocation: true
argument-hint: "[requirements|design|tasks]"
allowed-tools: Bash(python C:/Users/user/.claude/hooks/spec_state.py *) Read
---

# /spec-approve $ARGUMENTS

Stamp the current phase as approved. **Only the operator can invoke this.**

## Why this file exists as a separate command

The phase stamp lives in `state.json`, which `spec_gate.py` refuses to let any
`Edit` or `Write` call touch. The only documented route to an approval is this
command, and `disable-model-invocation: true` means the model can never trigger
it. That is what makes the gate a gate rather than a suggestion: progression
requires a human keystroke.

## Steps

1. Show the operator what they are approving. Print the artifact for the current
   phase so the decision is made against the text, not against a summary:

   ```
   python C:/Users/user/.claude/hooks/spec_state.py status
   ```

   Then read the phase's artifact and surface anything you think is weak —
   requirements that are untestable, a design with no failure modes, tasks with no
   verification. Say it before the stamp, not after.

2. Stamp it:

   ```
   python C:/Users/user/.claude/hooks/spec_state.py approve $ARGUMENTS
   ```

   With no argument it approves whatever phase the spec is currently in. It refuses
   if the artifact for that phase does not exist yet.

3. Tell the operator the next step: `/spec-next` to advance and draft, or — if
   `tasks` was just approved — `/spec-next` once more to reach `implement` and
   unlock source edits.

## Approval is not advancement

Approving stamps the phase; it does not move it. `/spec-next` moves it. Keeping
them separate means an approval can never be inferred from progress, or progress
from an approval.
