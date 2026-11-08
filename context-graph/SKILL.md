---
name: context-graph
description: >
  Decision-trace memory for an agent harness: record what was chosen and why
  (trace), capture the human's outcome verdict (upvote/correct), auto-draft a
  rule candidate from each correction delta, and retrieve proven
  schemas/patterns/rules L4-first (project -> org -> industry -> universal)
  before the next decision. SQLite-backed, no LLM needed for tracing.
  Use when wiring cross-run decision memory into a pipeline (dark-factory
  nodes, feature chains), reviewing whether a correction became a permanent
  rule, or choosing between decision-memory substrates (meta-context-graph
  SQLite vs Neo4j MKG vs memory-index evidence store). Cross-reference:
  agent-long-term-memory owns the gate this stratum must pass (R2/R12/R14);
  memory-index owns evidence recall; agentic_kg_memory owns the semantic KG.
status: draft
last_validated: 2026-11-08
validation_method: source inspection (meta-context-graph repo + programmatic API docs; no live gate run)
---

# Context Graph (decision memory stratum)

## Verdict

Adopted as ONE memory stratum only: **decision/experiential memory** — what was
chosen, why, and whether the human agreed. It does NOT replace evidence recall
(memory-index), the semantic KG (agentic_kg_memory), or the Neo4j MKG
(mkg-recall). No retrieval-quality claim is made until it passes the
agent-long-term-memory gate (R2: beat BM25-over-raw at matched reader/judge/k).

## The loop

    act -> trace(step, proposal, choice, rationale, confidence)
         -> human verdict (upvote | correct)
         -> correction delta auto-drafts a rule candidate (TribalKnowledge)
         -> human review (mcg review) approves pending candidates
         -> next run retrieves approved rules L4-first before acting

Retrieval scope layering — read the most specific that has an answer, fall
back toward L1:

    L4 project/runtime  "this batch uses legacy naming"
    L3 organisation     "Provider means vendor in our contracts"
    L2 industry         "'Provider' is regulated in healthcare"
    L1 universal        "dates are ISO 8601"

## Protocol

1. **Before deciding** (design, schema, plan synthesis, any typed TDR):
   `session.retrieve(query)` — read proven schemas, patterns, approved rules,
   similar projects. Apply them as constraints, not suggestions.
2. **After deciding**: `session.trace(...)` with the proposal, the choice, the
   rationale, and a confidence. Trace is LLM-free and cheap — never skip it.
3. **On human correction**: `session.correct(trace_id, corrected_choice,
   rationale)` — the delta becomes a rule candidate automatically. Never
   hand-edit the store to simulate this.
4. **Rules only exist after human review** (`mcg review` / `pending_candidates`).
   An unreviewed candidate is not guidance. Provenance (who validated) is the
   poisoning defense (R9) — model confidence is not.
5. **Admission** (R14): a rule enters durable shared scope only after it recurs
   on 3+ independent projects or passes a control-vs-treatment run. Recall
   count is not recurrence.

## Integration surfaces

- Programmatic (preferred): `from mcg.session import KnowledgeSession` —
  `retrieve / trace / upvote / correct / pending_candidates`. No LLM required.
- CLI: `mcg process | stats | query | correct | review | upvote`.
- Store: SQLite at `~/.mcg/mcg.db` (env `MCG_DB`). Two graphs side by side:
  domain KG (what exists) + context graph (how and why it was built).
- Dark-factory harness wiring: wrap `design`, `spec`, and plan-synthesis nodes
  — retrieve before the LLM call, trace after it; UAT/review corrections call
  `correct` with the review note as rationale. sw-design Stage 0 TDRs cite
  trace ids as their provenance.

## Boundaries

- Owns: the decision-trace loop and the rule-candidate review flow.
- Does not own: memory-gate decisions (`agent-long-term-memory`), evidence
  recall (`memory-index`), semantic KG extraction (`agentic_kg_memory`),
  in-repo decision records (sw-design DDSE — TDRs are per-project; this is the
  cross-project memory behind them).
- Not an MCP server yet. Promote to a registered MCP tool in `~/.mcp` only
  after the stratum earns its seat in a live run.

## Known limits

- No LLM-free retrieval-quality evidence: MCG ships no control arms. Until the
  gate runs, treat `retrieve` hits as advisory context, never as fact.
- Multi-hop conflict resolution between an L4 override and an L3 rule is
  unsolved (R10) — newest-or-more-specific wins by convention, not by proof.
- Its document-processing pipeline (classify -> extract -> resolve) is
  redundant here; use this harness's own pipelines and keep only the
  context-graph layer.
