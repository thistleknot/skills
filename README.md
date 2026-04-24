# skills

Reusable skill library for agentic coding, memory, retrieval, tuning, and orchestration.

Each skill lives in its own folder as `SKILL.md`. The repo is no longer just an
old `.copilot` module scaffold; it is a composable skill graph.

## Current Skill Graph

| Layer | Skills | Role |
|---|---|---|
| Execution | `react-agent`, `reasoning`, `code`, `debugging`, `validation`, `architecture` | General planning, implementation, debugging, verification |
| Orchestration | `agentic-harness`, `continuity-log` | Multi-agent control plane and compact-safe working memory |
| Memory / retrieval | `memory-bank`, `todo`, `agentic_kg_memory`, `gist-retriever`, `kg_ontology`, `request-intent-resolution` | Durable project memory, semantic retrieval, ontology control, and request-thread routing |
| Tuning / experiment tracking | `hyper-parm_tuning`, `optuna-nested-cv`, `mlflow`, `representation-pipeline` | Methodology, search engine, experiment ledger, representation design |

## Key Relationships

1. `react-agent` is the outer execution OS.
2. `agentic-harness` is the programmatic train station / control plane for coding frameworks like Claude Code, OpenCode, and GitHub Copilot CLI.
3. `continuity-log` is the compact-safe working-memory layer. It stores distilled decisions, rejected paths, blockers, and resume points. It is **not** a raw hidden chain-of-thought dump.
4. `hyper-parm_tuning` defines what to optimize, `optuna-nested-cv` runs the search, and `mlflow` records params, metrics, artifacts, and lineage.
5. `agentic_kg_memory` owns semantic memory policy, `gist-retriever` owns the layered retrieval engine, and `kg_ontology` owns canonicalization and ontology narrowing.
6. `memory-bank` and `todo` are the durable project-memory surfaces that support the rest of the stack.

## Repository Layout

- `<skill>\\SKILL.md` -> canonical skill contract
- `copilot-instructions.md` -> repo-wide Copilot guidance
- `request-intent-resolution\\SKILL.md` -> request-thread routing, retrieval, and evaluation skill
- `feature-catalog\\` -> supporting catalog material

## Design Principles

- Skills should be composable rather than monolithic.
- Policy, implementation, and tracking should be separated when they have different responsibilities.
- Root-cause fixes beat band-aids.
- Artifacts, evidence, and decisions should be persisted explicitly.
- Between compactions, preserve distilled continuity packets rather than re-deriving the same conclusions.

## Recent Direction

- Added `mlflow` as the experiment-ledger skill.
- Reframed `agentic-harness` as the multi-framework stationmaster.
- Added `continuity-log` to preserve compact-safe reasoning products between long turns and compactions.
