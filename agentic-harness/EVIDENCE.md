# Agentic Harness — Evidence Index

Grounding citations for behavioral contracts in `agentic-harness/SKILL.md`.

## Evidence Index

| Tier | Source | Claim | Contract Section Grounded |
|---|---|---|---|
| 2 | Anthropic Claude Code docs | Pipeline-routing, sub-agent delegation, plan-approval gates, and file-locking are production-validated in Claude Code agent sessions | Backbone operating model |
| 2 | OpenClaw (production use) | Terminal-native tool execution + search→inspect→edit→run→verify is the minimum viable harness backbone | Backbone operating model |
| 2 | OpenCode (production) | Branch/worktree awareness and artifact production at known paths are required for parallel agent runs without collision | Branch and worktree awareness |
| 2 | GitHub Copilot CLI (production) | Critic-gated completion (not "looks good" completion) and checkpointed plan/todo/state tracking are validated harness behaviors | Backbone operating model |
| 3 | awesome-copilot: `structured-autonomy-plan/generate/implement` | Plan→Generate→Implement trinity with sub-agent routing is a community-validated harness lifecycle | Task lifecycle |
| 4 | Session crystallization + in-skill patterns (`TaskSpec`, `ChecklistOutput`, critic verdicts) | When planner/router/critic/verifier boundaries carry schema-bound payloads instead of reparsed prose, harness state stays inspectable and truncation/ambiguity bugs become easier to detect and localize | Structured responses as the default wire format |
| 3 | awesome-copilot: `gem-orchestrator` agent | Orchestrator that delegates all execution to specialized agents (never executes directly) validates the coordinator role separation | Coordinator pattern |
| 3 | awesome-copilot: `ai-team-orchestration` skill | Producer + specialized sub-agents with human-as-message-bus is a community-validated multi-agent pattern | Backbone operating model |
| 4 | Session crystallization: gap_critic.py (storywriter) | `checklist` sub-skill is independently reusable outside the harness context; warrants standalone promotion | Checklist integration points |
| 4 | Session crystallization: multiple projects | coherence sentinel (False→True gate) is necessary; premature completion is the #1 harness failure mode across all tested projects | Coherence gate |
| 4 | Session crystallization: agentic-harness used across OpenClaw and Copilot CLI | Multi-framework stationmaster framing holds; the harness contract is framework-agnostic | Programmatic train station thesis |
| 5 | Anthropic Building Effective Agents (blog) | Orchestrator-workers is one of 5 canonical agentic patterns; the harness embodies this at the control-plane level | Programmatic train station thesis |
| 3 | `stanfordnlp/dspy` optimizer + refine docs | Metric/reward-bound compile-refine loops with trace-aware optimization and explicit error budgets are reusable evaluation patterns for LM programs | Evaluation stack |
| 3 | `zou-group/textgrad` README + evaluation docs | Natural-language loss functions, textual-gradient update loops, noisy-objective hygiene, and sandbox caution are reusable evaluation patterns for harness repair loops | Evaluation stack |

## Contradiction Count: 0

No known contradictions as of 2026-04-28.
