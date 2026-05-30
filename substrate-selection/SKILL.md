---
name: substrate-selection
description: Runtime substrate selection protocol. Use when deciding which external coding runtime should sit behind the harness. Keep orchestrators separate from leaf executors, keep skills separate from adapters, and only encode claims that are grounded in verified docs or local runs.
status: active
last_validated: 2026-05-24
supersedes: []
validation_method: session
---
# Substrate Selection

## Role Split
- **Orchestrator substrate** — owns planning, exploration, session flow, and delegated work
- **Leaf executor** — performs manager-directed code edits or narrow execution tasks
- **Skill surface** — teaches policy and routing, not runtime invocation
- **Backend adapter** — translates a scoped task packet into runtime-specific message,
  file, or graph emission without exposing that transport contract to the orchestrator

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

## Provider vs Harness Delta

Do not confuse a **model/provider delta** with a **harness/runtime delta**.

- A first-party runtime such as GitHub Copilot CLI may bundle stronger session,
  tool, checkpoint, and recovery behavior around the model.
- A provider-routed stack such as OpenRouter + OpenCode may expose similar models
  while still lacking those runtime guarantees by default.
- Therefore: if behavior quality differs, first ask whether the missing capability
  lives in the harness contract rather than in the model itself.

Working rule:

1. treat provider choice and harness choice as separate axes
2. do not assume model parity implies workflow parity
3. when moving from a first-party runtime to a provider-routed runtime, make the
   missing harness features explicit and reconstruct them in skills/config rather
   than blaming the provider generically

## Compensating Controls for Weaker Provider-Routed Stacks

When the cheaper or weaker substrate is OpenRouter-backed or otherwise lacks the
same first-party runtime behavior, shore up the harness explicitly:

- use stricter role split between orchestrator, delegated harness, and leaf editor
- require structured response packets instead of freeform progress prose
- add bounded retries, timeout guards, and restart/reseed policies
- require observable progress signals: stdout, file diff, heartbeat, or steerable
  intermediate state
- classify silent bounded-edit runs as harness stalls and escalate instead of
  waiting indefinitely
- preserve source-of-truth and acceptance criteria so a stronger/manual fallback
  can resume from the same boundary

The default stance is: **rebuild missing runtime guarantees in the harness before
concluding that the provider/model gap is the whole problem.**

## Integration Rule
- Do not stop at a comparison matrix. A backend stack only counts as integrated when the harness resolves it into a run-visible contract.
- The harness should record at least these lanes per run:
  - **orchestrator lane** — default current recommendation: `opencode`
  - **delegated external-harness lane** — default current recommendation: `pi`
  - **leaf-agent lane** — default current recommendation: `aider`
- Each lane should bind through the model registry to a concrete endpoint/model pair, then serialize that binding into state, logs, or CLI output so the active stack is inspectable.
- Runtime choice remains configurable, but the default split should be explicit rather than implied.
- Where a runtime such as OpenCode requires `--agent` launches plus backend-graph,
  file, or message emission, hide that behind a backend adapter. The orchestrator
  should emit a scoped task packet; the adapter owns the concrete transport.
- If the orchestrator has to hand-build message files or backend graph artifacts,
  the substrate boundary has leaked and the integration is incomplete.

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
- When comparing OpenRouter/OpenCode against GitHub Copilot CLI, separate:
  - **model quality delta**
  - **runtime/harness delta**
  - **which compensating controls are already present in the skills/config**
<!-- consolidation:see-also:start -->
## See Also
[[agentic-harness]]  [[pi]]  [[codebase-knowledge-graph]]  [[code]]
<!-- consolidation:see-also:end -->
