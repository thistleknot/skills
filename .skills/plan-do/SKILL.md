---
name: plan-do
description: Research and critique a problem, write a sequenced plan with evidence and tracked actions in the workspace .tmp files, then execute the plan while reporting remaining work. Use when the user asks for a plan-and-execute workflow with ongoing burndown.
metadata:
  short-description: Research, plan, execute, and track work
---

# Plan and Do

Turn a problem into an evidence-based plan, then carry it through to completion. Keep the reasoning, approved sequence, issue receipts, and live task state visible in the workspace's `.tmp` folder.

## Use this workflow when

- The user asks to research or critique a problem, propose a fix, and do the work.
- The work spans multiple steps or responses and needs a visible burndown.

For a simple one-step request, act directly unless the user asks for these tracking files. Use [task-breakdown](../task-breakdown/SKILL.md) when the task is already designed and only needs implementation tasks.

## Establish the evidence

1. Restate the observed problem and the intended outcome.
2. Inspect the relevant artifacts and gather evidence that can support or falsify likely explanations.
3. Separate observed facts from assumptions. Explain the problem in those terms.
4. Critique the proposed approach, explanations, and assumptions. Compare viable alternatives; use TRIZ and Six Thinking Hats when they reveal materially different options.
5. Choose a fix that satisfies the surviving evidence and constraints. Record why rejected options fail.

Do not turn a weak premise into a requirement. If evidence changes the problem statement, update the plan before proceeding.

## Track the work

Use the current workspace's `.tmp` directory and preserve existing material:

- `plan.md` — the high-level objective, dependency order, acceptance conditions, and chosen approach. Create it when absent. After execution starts, treat the approved sequence as read-only; if evidence requires a change, record the reason in `critique.md` and revise the plan before continuing.
- `critique.md` — append dated evidence receipts: issue, observation/source, effect on the hypothesis or plan, and disposition. Preserve earlier entries.
- `critique-todo.md` — actionable items derived from the plan and receipts. Each item moves through `OPEN` → `DOING` → `DONE`; update the existing item instead of creating duplicates.

If a file already exists, read it before editing. Keep unrelated work intact. Do not claim completion from a written plan or a diagnosis alone; execute the authorized items and verify their acceptance conditions.

## Report progress

At each response during execution, give a concise burndown: completed items, remaining open or doing items, the current blocker if any, and the next action. Keep the list synchronized with `critique-todo.md`. Close the work only when the planned acceptance conditions are verified or a real external blocker is documented.
