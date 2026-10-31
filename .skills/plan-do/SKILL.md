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

## Required reasoning sequence

Keep these steps visible in the work; do not collapse them into a generic plan:

1. **Research the problem.** Inspect the user's artifacts and the surrounding domain. For data problems, examine both datasets and their relationship before proposing a fix. Retrieve evidence that can distinguish competing explanations.
2. **Explain the problem.** Describe what is happening, for whom, and why it matters. Separate observed facts from inferred causes and state the user's intended outcome.
3. **Critique the approach, explanations, and assumptions.** Identify weak premises, missing evidence, tradeoffs, and evidence that would falsify each live explanation.
4. **Analyze the options.** Compare genuinely different approaches. Use the TRIZ utility belt to reshape the problem and Bono's Six Thinking Hats to inspect facts, concerns, risks, benefits, alternatives, and process. Include an option that challenges the obvious answer when one is plausible.
5. **Suggest a solution.** Choose an approach that addresses every surviving premise and satisfies the user's goal. Explain why it follows from the evidence and why rejected options do not.

Do not turn a weak premise into a requirement. If research changes the problem statement, repeat the affected reasoning steps and update the plan before proceeding.

## Track the work

Use the current workspace's `.tmp` directory and preserve existing material:

- `plan.md` — the high-level objective, dependency order, acceptance conditions, and chosen approach. Create it when absent. After execution starts, treat the approved sequence as read-only; if evidence requires a change, record the reason in `critique.md` and revise the plan before continuing.
- `critique.md` — append dated evidence receipts: issue, observation/source, effect on the hypothesis or plan, and disposition. Preserve earlier entries.
- `critique-todo.md` — actionable items derived from the plan and receipts. Each item moves through `OPEN` → `DOING` → `DONE`; update the existing item instead of creating duplicates.

If a file already exists, read it before editing. Keep unrelated work intact. Do not claim completion from a written plan or a diagnosis alone; execute the authorized items and verify their acceptance conditions.

## Report progress

At each response during execution, give a concise burndown: completed items, remaining open or doing items, the current blocker if any, and the next action. Keep the list synchronized with `critique-todo.md`. Close the work only when the planned acceptance conditions are verified or a real external blocker is documented.
