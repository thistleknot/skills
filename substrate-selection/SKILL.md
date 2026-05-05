---
name: substrate-selection
description: Runtime substrate selection protocol. Use when deciding which external coding runtime should sit behind the harness. Keep orchestrators separate from leaf executors, keep skills separate from adapters, and only encode claims that are grounded in verified docs or local runs.
status: active
last_validated: 2026-04-29
supersedes: []
validation_method: session
---
# Substrate Selection

## Role Split
- **Orchestrator substrate** — owns planning, exploration, session flow, and delegated work
- **Leaf executor** — performs manager-directed code edits or narrow execution tasks
- **Skill surface** — teaches policy and routing, not runtime invocation

## Current Working Matrix
- **opencode** — orchestrator substrate; strongest fit for planning/exploration and delegated subtask framing
- **claw-code** — orchestration/runtime candidate; interactive controller with provider routing
- **openclaw** — keep in scope as a gateway/control-plane or monitoring candidate, not the default coding substrate
- **aider** — leaf executor; best for manager-directed one-shot editing with a chosen model and prompt
- **Copilot agent / Copilot CLI** — currently grounded here as a skill/authoring surface, not yet as a verified harness runtime substrate
- **Claude Code** — treat as provisional until direct evidence is gathered in this repo; do not hard-code stronger claims from analogy alone
- **Pi** — unresolved; do not encode architectural claims until the exact project/runtime is identified

## Working Rules
- skills choose substrates; adapters invoke substrates
- provider bridges normalize endpoints; they do not decide policy
- prefer first-party contracts and replaceable adapters over adopting an external runtime as the project identity
- when evidence is indirect, mark it provisional instead of smuggling it in as fact

## Integration Rule
- Do not stop at a comparison matrix. A backend stack only counts as integrated when the harness resolves it into a run-visible contract.
- The harness should record at least two lanes per run:
  - **orchestrator lane** — default current recommendation: `opencode`
  - **leaf-agent lane** — default current recommendation: `aider`
- Each lane should bind through the model registry to a concrete endpoint/model pair, then serialize that binding into state, logs, or CLI output so the active stack is inspectable.
- Runtime choice remains configurable, but the default split should be explicit rather than implied.

## Default Recommendation
- Use `opencode` / `claw-code` when you need orchestration
- Use `aider` when a manager needs a leaf code executor
- Keep `openclaw`, Copilot, Claude Code, and Pi in the comparison set with explicit confidence labels
<!-- consolidation:see-also:start -->
## See Also
[[agentic-harness]]  [[agentic-design-patterns]]  [[build-observability]]
<!-- consolidation:see-also:end -->
