Crystallize the following completed work chain using the crystallization skill protocol.

## Work chain summary

This session converged on the architecture for integrating ActiveGraph (yoheinakajima/activegraph) 
as a shared-state substrate into an existing OpenCode multi-agent harness.

---

## Question

How do OpenCode's multi-role agents (orchestrator, coder, reviewer, debugger, researcher) 
coordinate through a shared graph substrate instead of passing context through a direct call chain?

---

## Produce a digest with these fields

**Question** — as stated above

**Findings** — distill to durable claims, not chronology:
- ActiveGraph is an event-sourced reactive graph runtime; agents mutate a shared graph 
  and react to mutations rather than calling each other directly
- The graph is not replacing the call chain — it replaces context-passing. 
  Orchestrator still drives sequencing.
- Integration pattern: orchestrator writes job + assignee to graph → calls agent → 
  agent reads own assignment from graph → writes output to graph → orchestrator reads result
- Handoff signal = object status transition on the graph (task.status=review_ready, etc.)
- No agent needs to know any other agent exists; they only have a read/write contract with the graph
- Tekiner's meta context graph is the persistent layer across sessions: 
  what was decided, corrected, learned — with provenance. The session graph (ActiveGraph) 
  is ephemeral; the context graph is durable.
- Code as Agent Harness (arXiv 2605.18747) frames code as the operational substrate for 
  multi-agent coordination; consistent shared state is the named open challenge this architecture solves.
- The fork-and-diff capability (branch at any historical event, diff against parent) is the 
  immediate concrete win for hypothesis testing without manual revert.

**Entities involved**
- ActiveGraph (yoheinakajima/activegraph, v1.0, MIT, Python 3.11+, SQLite/Postgres)
- OpenCode multi-agent harness (orchestrator, coder, reviewer, debugger, researcher roles)
- Tekiner context graph (four metadata categories: technical, business, operational, decision)
- arXiv 2605.18747 — Code as Agent Harness (Ning et al., May 2026)
- ActiveGraph primitives: Graph, Behavior, RelationBehavior, Patch, Frame, Fork, EventLog
- Existing stack: pgvector, Chroma, skill-wiki, agentic_kg_memory

**Lessons** — reusable decision rules extracted from this chain:
1. The graph replaces context-passing, not orchestration. Keep the orchestrator as the sequencer.
2. Each agent's contract: Require(graph object exists, status correct) → Execute → 
   Guarantee(output written to graph, status updated) → no direct agent-to-agent calls.
3. Status transitions are the inter-agent protocol. Design the status state machine before 
   writing any agent logic.
4. The session graph is ephemeral. The context graph is durable. Keep them separate; 
   extract patterns from session graph to context graph on session end.
5. Relation behaviors (logic on typed edges, not endpoints) handle dependency unblocking 
   without a coordinator — use for task dependency chains.
6. Fork-and-diff is the mechanism for "try approach A vs B" without manual revert. 
   Wire this into the coder→reviewer loop.
7. The dispatcher (who spawns the correct agent for a given graph event) lives in the 
   orchestrator skill, not distributed across agents.

**Open questions**
- Exact schema for the session graph object types and status state machine for this specific 
  skill set (orchestrator/coder/reviewer/debugger/researcher)
- How to handle concurrent agent writes with optimistic concurrency (patch rejection protocol)
- Context graph schema: which of Tekiner's four metadata categories map to which 
  learned artifact types in this harness
- Whether the orchestrator dispatch loop belongs in a standalone skill or inline in the 
  orchestrator agent's SKILL.md
- Integration with existing Chroma + pgvector memory stack: does the session graph 
  replace or sit alongside current Chroma layer

---

## Routing

- Send the digest page → agentic_kg_memory
- Send entity triplets → agentic_kg_memory  
- If any lesson warrants a change to an existing live skill contract → flag for skill-wiki staged draft
- Flag open question #4 (orchestrator dispatch loop) for a follow-on skill-creator pass