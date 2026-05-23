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
- **pi** — lightweight delegated external harness; use when the outer orchestrator should hand off one bounded scene to a second harness that stays lighter than the main control plane
- **aider** — leaf executor; best for manager-directed one-shot editing with a chosen model and prompt, including as a worker inside `pi`
- **Copilot agent / Copilot CLI** — currently grounded here as a skill/authoring surface, not yet as a verified harness runtime substrate
- **Claude Code** — treat as provisional until direct evidence is gathered in this repo; do not hard-code stronger claims from analogy alone

## Working Rules
- skills choose substrates; adapters invoke substrates
- provider bridges normalize endpoints; they do not decide policy
- prefer first-party contracts and replaceable adapters over adopting an external runtime as the project identity
- when evidence is indirect, mark it provisional instead of smuggling it in as fact

## Integration Rule
- Do not stop at a comparison matrix. A backend stack only counts as integrated when the harness resolves it into a run-visible contract.
- The harness should record at least these lanes per run:
  - **orchestrator lane** — default current recommendation: `opencode`
  - **delegated external-harness lane** — default current recommendation: `pi`
  - **leaf-agent lane** — default current recommendation: `aider`
- Each lane should bind through the model registry to a concrete endpoint/model pair, then serialize that binding into state, logs, or CLI output so the active stack is inspectable.
- Runtime choice remains configurable, but the default split should be explicit rather than implied.

## Model Sizing by Reasoning Load

Assign models by **reasoning load**, not task importance.

| Phase | Model size | Rationale |
|---|---|---|
| Planning, architecture, ambiguous requirements | Large model | Reasoning-heavy; context matters; errors here cascade |
| Implementation after plan is locked | Smaller / cheaper model | Pattern-completion task; thinking is already done |
| Leaf code edits (manager-directed) | Open-source / local (Ollama, Qwen) | Viable for execution steps; not validated for planning |

Rules:
- Once a plan exists, the implementation sub-agent needs to fill in a known shape — not reason about trade-offs
- Local models (e.g., `qwen2.5-coder`, `qwen3.5`) are cost-effective for leaf tasks; not validated for planning decisions
- Never route planning work to the cheap model to save tokens; the cascade cost of a bad plan exceeds the token savings

## Default Recommendation
- Use `opencode` / `claw-code` when you need orchestration
- Use `pi` when the orchestrator should delegate a bounded sub-harness instead of a single worker call
- Use `aider` when a manager or delegated harness needs a leaf code executor
- Keep `openclaw`, Copilot, and Claude Code in the comparison set with explicit confidence labels
<!-- consolidation:see-also:start -->
## See Also
[[agentic-harness]]  [[pi]]  [[codebase-knowledge-graph]]  [[code]]
<!-- consolidation:see-also:end -->
