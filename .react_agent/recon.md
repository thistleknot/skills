# Recon

## Current Request
Absorb the useful behaviors from the llm-wiki concept into the live skills, rather than treating llm-wiki as only a placement/classification question.

## Entities Involved
- llm-wiki concept source (originally staged under `integrate\llm-wiki\SKILL.md`)
- `agentic_kg_memory\SKILL.md` — strongest ownership fit for compiled wiki memory behavior
- `gist-retriever\SKILL.md` — ownership fit for lightweight markdown/index-first retrieval progression
- `memory-bank\SKILL.md` — ownership fit for the boundary clarification against compiled corpus memory
- `README.md` — published explanation of how the pattern is absorbed into existing skills

## Observed Boundaries
- `agentic_kg_memory` already owns pages/wiki entries, throughlines, retrieval/update loop, and evolving evidence-backed conclusions.
- `gist-retriever` already owns retrieval mechanics, hybrid sparse+dense search, cluster routing, and fallback behavior.
- `memory-bank` already states that it is project/session continuity, not semantic memory, but it does not yet explicitly contrast itself with compiled wiki/corpus memory.
- `integrate\` is explicitly documented in `README.md` as a volatile concept-intake folder, not a live branch.
- After absorption, the live repo should no longer depend on the staged `integrate\llm-wiki` path.

## llm-wiki Features Worth Absorbing
- compiled persistent knowledge layer between raw sources and query-time retrieval
- ingest loop that updates existing pages rather than re-deriving everything per query
- query results as durable write-back artifacts
- lint/health-check loop for contradictions, stale claims, orphan pages, and missing cross-links
- lightweight `index.md` / `log.md` operating surfaces for human/agent navigation
- small-to-medium markdown-first retrieval before heavier hybrid retrieval is needed
- optional local markdown search engine progression (`qmd`-style), not as the primary ontology/memory contract

## Dependency Map
1. Feature ownership map must stabilize first.
2. `agentic_kg_memory` and `memory-bank` should be updated before `README.md`, because README should describe real ownership, not intended ownership.
3. `gist-retriever` can be updated after the ownership map and before the final README sync.
4. Validation is doc-structure and diff based; there are no discovered repo tests tied to these markdown skill files.

## Surprises / Contradictions
- The earlier plan was wrong because it framed the task as placement-only.
- A top-level `llm-wiki` directory still exists in the repo root as leftover scaffolding from the earlier mistaken promotion, even though the live file was removed. It may need cleanup if it remains empty.
- The repo worktree is already dirty: `README.md` is modified, `.react_agent\` is new, and `integrate\` is untracked.
