---
name: long-horizon-attention
description: >
  Use when an agent or LLM must sustain reasoning over a long, growing, or
  noise-filled context and keeps losing the thread -- multi-step tool chains,
  extended histories, chaotic retrieved passages, or "needle in a distracting
  haystack" prompts. Separates tactical execution from strategic oversight and
  active context organization so critical evidence is not overlooked as the
  horizon extends.
status: active
last_validated: 2026-07-27
---

# Long-Horizon Attention

Distilled from arXiv 2311.08734 (Thread of Thought), 2503.18852 (Self-Organizing
Graph Reasoning), 2510.0879 (COMPASS), 2601.01576 (OpenNovelty), with memory
angles from 2410.03642 and 2402.11592.

## When to Use

Reach for this when the failure is *loss of coherence across length*, not lack of
knowledge:

- A distracting or chaotic context (many retrieved chunks, overheard chatter,
  irrelevant history) drowns the relevant facts.
- A task needs sustained reasoning across many tool calls and the agent forgets
  earlier evidence or gets distracted mid-chain.
- Extended histories exceed what raw attention keeps salient, so critical
  evidence is silently dropped.

**Do NOT use when** the context fits comfortably and the model simply lacks the
fact (that is retrieval/knowledge), or when a single-shot prompt already answers
correctly. Adding a hierarchy here only buys latency.

## Core Concepts

- **Thread of Thought (ThoT).** A plug-and-play prompting move: walk the chaotic
  context piece by piece, summarizing and carrying forward a running "thread"
  before answering, instead of attending to the whole blob at once. Integrates
  with existing prompting techniques and models (Zhou et al. 2023).

- **Separation of concerns (COMPASS).** Split the agent into three specialized
  roles rather than one monolithic loop, which lifted long-horizon accuracy by
  up to ~20% (2510.0879):
  1. *Tactical execution* -- does the next concrete step / tool call.
  2. *Strategic oversight* -- checks the step against the overall goal.
  3. *Context organization* -- curates the growing history, delegable to a
     smaller/cheaper model, so the expensive reasoner sees a clean working set.

- **Evolving context as a managed artifact.** Treat the history as state to be
  reorganized, not an append-only log. Post-training can teach a small model to
  do the curation cheaply (test-time scalable).

- **Critical-state discovery (2503.18852).** Self-organizing reasoning graphs
  drift toward a critical state that sustains continuous discovery; structural
  vs semantic entropy balance is the signal that adaptation is still alive rather
  than collapsed.

- **Grounding against drift (OpenNovelty, 2601.01576).** For long analytical
  tasks, anchor each claim in retrieved evidence with explicit citations so the
  long chain stays auditable and does not hallucinate its own premises.

## Protocol

```
sustain_long_horizon(task, context):
    thread <- ""                       # ThoT running summary
    working_set <- organize(context)   # cheap model curates; drop noise
    loop until goal_met or budget_out:
        step   <- tactical(working_set, thread)     # execute next action
        thread <- thread + summarize(step_result)   # carry evidence forward
        if strategic_check(thread, goal) == drift:  # oversight role
            working_set <- reorganize(context, thread)  # re-surface evidence
        ground(step_result)            # cite retrieved support; flag unsupported
    return synthesize(thread)
```

Known failure modes (state them, do not mask): compounding errors across steps
persist; hierarchy does not fully eliminate hallucination or coherence loss on
SOTA models; the specialized framework may not generalize to every domain
(2510.0879).

## Related

`reasoning` (top-down reconstruction), `crystallization` (salient-fact
distillation for the running thread), `extractive-context-pruning` (what to drop
from the working set).
