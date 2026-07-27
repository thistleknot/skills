---
name: code-localization
description: >
  Use when an agent must find the *right place* in a large codebase to act --
  which files/functions cause an issue, where a bottleneck lives, or where a
  feature should be generated. Covers graph-guided localization, repository
  planning graphs, performance-bottleneck localization, and goal-plan-action
  error localization for agents.
status: active
last_validated: 2026-07-27
---

# Code Localization

Distilled from arXiv 2503.09089 (LocAgent), 2509.16198 (RPG / ZeroRepo),
2511.0609 (SWE-fficiency), 2510.08847 (Agent GPA), 2512.18552 (Self-play SWE-RL),
2602.02751 (Strategy Auctions for small agents).

## When to Use

- An agent needs to identify the specific files/functions relevant to a GitHub
  issue, bug, or optimization before editing -- localization is the gate on the
  whole downstream fix.
- You are generating or navigating a large repository and need structured
  planning of where code belongs.
- You need to localize *where an agent's own reasoning failed* (goal vs plan vs
  action) to target improvement.

**Do NOT use when** the target file is already known or the codebase is small
enough to read directly -- graph construction is overhead there. Reality check:
SOTA agents still localize optimization opportunities poorly (< 0.15x expert
speedup on SWE-fficiency, 2511.0609); expect assistance, not a solved problem.

## Core Concepts

- **Graph-guided localization (LocAgent, 2503.09089).** Parse the codebase into a
  directed heterogeneous graph (files, classes, functions, imports as typed
  nodes/edges) and let an LLM agent do multi-hop reasoning over it. Reaches
  ~92.7% file-level accuracy and lifts GitHub issue resolution ~12% (Pass@10) at
  low cost. The graph is what turns "search" into "navigate".

- **Repository Planning Graph (RPG, 2509.16198).** For *generating* repositories,
  a graph-driven plan gives consistent long-horizon structure -- where each
  module lives and how they relate -- which in turn accelerates later
  localization and improves coherence, scale, and test accuracy.

- **Bottleneck localization (SWE-fficiency, 2511.0609).** Performance work is a
  localization problem too: find the hot path, reason about execution across
  functions, then patch. Agents struggle most at the *localize-the-bottleneck*
  and *reason-across-functions* steps, less at editing.

- **Error localization for agents (Agent GPA, 2510.08847).** Evaluate an agent on
  Goal-Plan-Action alignment with LLM-judges that agree with humans, so failures
  are pinned to the goal, the plan, or the action -- localizing the defect in the
  agent's own trajectory for targeted fixes.

- **Self-improvement over real repos (2512.18552, 2602.02751).** Self-play SWE-RL
  injects and repairs bugs in sandboxed repos (no human labels) to train
  localization+repair; strategy auctions coordinate small agents to cut reliance
  on the largest model while keeping localization quality.

## Protocol

```
localize_and_act(repo, issue):
    G     <- build_hetero_graph(repo)          # files/funcs/imports as typed graph
    cands <- multi_hop_reason(G, issue)        # LLM navigates, not greps
    if perf_task:
        cands <- rank_by_hot_path(profile(repo), cands)   # bottleneck first
    patch <- edit(cands)                        # narrowest change that resolves
    gpa   <- eval_goal_plan_action(patch, issue)          # localize own errors
    if gpa.fail: refocus(gpa.failed_stage)      # goal / plan / action
    return validate(patch)                       # tests + (perf) expert-speedup
```

Failure modes: graph parsing cost grows with repo size; correctness of edits
remains hard; long-horizon performance reasoning is far from expert level.

## Related

`reasoning` (multi-hop hypothesis ranking), `kg_ontology` (heterogeneous graph
construction), `long-horizon-attention` (sustaining state across a repo-scale
task).
