# Build Observability — Evidence Index

Grounding citations for behavioral contracts in `build-observability/SKILL.md`.

## Evidence Index

| Tier | Source | Claim | Contract Section Grounded |
|---|---|---|---|
| 3 | `integrate/compiled.md` | `build-observability` should cover normalized `runs / events / commands`, dashboard surface, runtime projection, trace enrichment, and sqlite/postgres storage policy | Core contract |
| 3 | `integrate/sundai-hacker-feature-topology.md` | The strongest reusable artifact is the clean observability schema and dashboard surface; the OpenClaw runtime collector is valuable as a pattern but not portable as-is | Schema backbone; dashboard; collector boundary |
| 3 | `integrate/sundai-hacker-feature-topology.md` | `agent-build-observatory` exposes current stage, timeline, command activity, changed files, artifacts, sub-agent hierarchy, and deploy outcomes, with Postgres when `DATABASE_URL` is set and SQLite fallback otherwise | Dashboard surface; storage policy |
| 4 | `agentic-harness/SKILL.md` | The harness is the execution/control layer that already tracks tasks, artifacts, branch/worktree state, and gating; observability should read from that layer, not replace it | Relation to `agentic-harness` |
| 4 | `feature-catalog/SKILL.md` | `feature-catalog` is a SQLite implementation ledger mapping features, files, and architectural decisions; run observability should link to it without collapsing into it | Relation to `feature-catalog` |
| 4 | `agentic_kg_memory/SKILL.md` | Episodic memory stores what happened, when, and why via decision traces; enriched observability events can serve as upstream episodic inputs | Trace enrichment and memory feedback |

## Contradiction Count: 0

No known contradictions as of 2026-05-02.
