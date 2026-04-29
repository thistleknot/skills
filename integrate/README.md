# integrate/ — Skill Library Intake Pipeline

Raw source material and staged draft skills awaiting absorption into the live skill graph.

## Pipeline

```
integrate/raw/          ← drop any source: link, file, note, research output, clone
       ↓  skill-wiki intake protocol (extract behavioral patterns)
integrate/staged/       ← draft SKILL.md + ≥1 EVIDENCE.md entry; awaiting promotion
       ↓  skill-wiki promotion gate
skills/<branch>/        ← active live skills in the main skill graph
```

**Rule:** Never delete from `integrate/`. It is the evidence corpus. Sources here
are cited by EVIDENCE.md files in live skills.

## Current Contents

| Item | Type | Status | Notes |
|---|---|---|---|
| `awesome-copilot/` | Community corpus (git clone) | Active reference | github.com/github/awesome-copilot; ~200 skills, ~200 agents, 6 hook bundles, 60+ plugins. `git pull` periodically. |
| `llm-wiki/` | Research + production patterns | Absorbed | Karpathy LLM-wiki + agentmemory lessons. Absorbed into: `agentic_kg_memory` (memory lifecycle, graph layer, hybrid search, automation hooks, crystallization, consolidation tiers), `gist-retriever` (staged retrieval access-path progression), `memory-bank` (project vs corpus boundary). Kept as source reference. |
| `staged/` | Draft skill concepts | Active staging area | Concepts extracted from raw sources; see `staged/README.md` for promotion criteria. |

## How to Add to the Pipeline

1. **Drop a source** into `integrate/raw/<source-name>/` — any format, no structure required.
   A link in a `.md` file is sufficient.

2. **Run the intake protocol** (see `skill-wiki/SKILL.md`):
   - Extract behavioral patterns (what should an agent *do*?)
   - Route to an existing skill or identify a new one needed
   - Write draft `SKILL.md` into `integrate/staged/<concept-name>/`

3. **Attach evidence** — write `integrate/staged/<concept-name>/EVIDENCE.md` with at least one
   entry citing the source.

4. **Check the promotion gate** — one Tier-1/2 item + local validation, or two independent
   Tier-1–3 items from distinct source types.

5. **Promote** — move the folder to a live skill location, update `README.md` skill graph,
   add `HISTORY.md` inaugural entry.

## Aggregation Sessions

Periodic aggregation sessions (like the 2026-04-28 awesome-copilot inventory) surface gap
candidates from intake sources. Outputs land in `staged/` or directly extend live skills.

The gap candidates from the 2026-04-28 session are documented in the session plan at
`~/.copilot/session-state/702de814-*/plan.md`. Tier-1 candidates by score:
`evaluator-optimizer` (25), `multi-agent-coordination` (25), `tdd-agent` (20),
`agent-governance` (20). See plan for full Pareto table.
