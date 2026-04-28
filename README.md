# skills

Reusable skill library for agentic coding, memory, retrieval, tuning, and orchestration.

Each skill lives in its own folder as `SKILL.md`. The repo is no longer just an
old `.copilot` module scaffold; it is a composable skill graph.

## Skill Graph (AST View)

Each node is a skill. Indentation encodes parent → child dependency. Peers share the same indent level.

```
skills/
├── execution/                       # plan, implement, verify
│   ├── react-agent                  # outer execution OS; drives all other skills
│   ├── reasoning                    # open-ended problem decomposition + multi-perspective analysis
│   ├── code                         # implementation standards, naming, refactor sequence
│   ├── debugging                    # error isolation, salience tiers, diagnostic strategy
│   ├── validation                   # test design, verification protocol, behavior contracts
│   └── architecture                 # system design, abstract-class planning, domain → code mapping
│
├── orchestration/                   # route work, enforce policy, manage cross-session state
│   ├── agentic-harness              # dark-task control plane; backbone = OpenClaw/Claude Code/OpenCode/Copilot CLI
│   │   ├── checklist                # LLM-as-judge validation pattern; structured findings with novelty proof
│   │   ├── continuity-log           # compact-safe session memory; distilled decisions, resume points
│   │   └── deep-research            # multi-source web evidence pipeline; LangGraph planner→researcher→synthesizer
│   └── timeout-guard                # runaway-task policy; interrupt and recovery rules
│
├── memory/                          # persist knowledge across sessions and tasks
│   ├── memory-bank                  # durable project memory (brief, context, patterns, progress)
│   │   # meta: DESCRIPTION/ARCHITECTURE/HISTORY pattern — applies to any skill folder
│   ├── todo                         # sqlite-backed task tracking with FastMCP bridge
│   ├── agentic_kg_memory            # semantic memory policy; owns graph update contract
│   │   ├── gist-retriever           # layered sparse+dense retrieval engine (BM25 + Chroma)
│   │   └── kg_ontology              # canonicalization, synset narrowing, hypernym repair
│   └── request-intent-resolution    # request-thread routing, retrieval evaluation
│
├── tuning/                          # measure, optimize, record
│   ├── hyper-parm_tuning            # methodology: what to tune, nested-CV framing
│   ├── optuna-nested-cv             # search engine: inner tune / outer unbiased estimate
│   ├── mlflow                       # experiment ledger: params, metrics, artifacts, lineage
│   ├── representation-pipeline      # representation design: raw signal → embedding space
│   └── stratified-quota-sampling    # adaptive sampling: marginal variance targeting, quota design for bounded acquisition
│
├── artifacts/                       # masterpiece outputs and information design
│   ├── gist_correlation_matrix      # sorted correlation matrix as complete relational map; two sorting approaches (orthogonal vs coverage)
│   └── spiral-radial-clustering-display  # multi-dimensional spiral visualization; GMM+HDBSCAN+ordering→UMAP 2D with Gestalt encoding
│
└── learning/                        # reinforcement learning and policy optimization
    └── deep-q-rl                    # DQN + Russian Doll MCTS for any scored discrete-action framework
```

## Key Relationships

1. `react-agent` is the outer execution OS. All other skills are invoked from inside it.
2. `agentic-harness` is the programmatic train station for coding frameworks (Claude Code, OpenCode, GitHub Copilot CLI, OpenClaw). It routes, gates, and reconciles work; each framework is a worker line.
3. `continuity-log` is a child of `agentic-harness`. It holds the compact-safe distilled state that lets the harness resume without re-deriving decisions.
4. `deep-research` is a child of `agentic-harness`. It decomposes a question into parallel subquestions, gathers web evidence via a 3-tier fetch pipeline (httpx → retry → Selenium), and synthesizes a claim-backed report seeding the harness TaskSpec.
5. `hyper-parm_tuning` defines what to optimize; `optuna-nested-cv` runs the nested search; `mlflow` records every run with lineage.
6. `agentic_kg_memory` owns graph-backed semantic memory policy. It now also carries the compiled-wiki maintenance pattern: persistent pages, ingest/query/lint loops, and write-back of durable syntheses.
7. `gist-retriever` is the retrieval sub-skill for that memory layer. It spans the access-path progression from markdown/index-first lookup through local markdown search and into the full hybrid BM25+dense pipeline.
8. `memory-bank` remains project operating memory, not compiled corpus memory. It stores project continuity while `agentic_kg_memory` stores evolving domain knowledge.
9. The supplementary comparison boundary is now explicit in the repo: **RAG/retriever** behavior belongs in `gist-retriever`, **LLM Wiki/compiler** behavior belongs in `agentic_kg_memory`, and **GBrain/operator / fat-skills orchestration** belongs on the execution/orchestration side, not in the memory branch.
10. KnowledgeWeaver is treated as a concrete implementation example of the compiler side: typed readable knowledge units plus a compiled index that can be rebuilt from canonical markdown artifacts.
11. `agentic-harness` (waterfall -> agile: topics -> plans -> specs -> tasks) is the lifecycle template for skill authoring, not just software projects.
12. `deep-q-rl` is the generalized RL framework for any scored discrete-action environment. Combines value-head Q-network, experience replay, target network, Russian Doll MCTS, AHA online mistake correction, and training-progress annealing. Derived from `thistleknot/chess-deep-q`.
13. `checklist` is a subskill of `agentic-harness`. It is the Pydantic-schema LLM-as-judge pattern: structured findings with novelty proofs, non-fatal execution, `review_required` flag, and cross-run fingerprinting via throughline Q-scores. Reference implementation: `gap_critic.py` in storywriter.
14. `gist_correlation_matrix` is the "true GIST output": sorted correlation matrix as complete relational map (N^2 cells, each encoding pairwise relationship). Two sorting strategies: **orthogonal** (information-theoretic maximization, sharp drop-off) and **coverage** (hierarchical boundary exploration, expanding bands). Outputs: interactive HTMLs with full zoom/pan/hover.
15. `spiral-radial-clustering-display` is the multi-dimensional hierarchical clustering visualization skill. Maps four layers (macro GMM + micro HDBSCAN + decorrelated ordering + hubness) into 3D feature space, projects via UMAP to 2D, encodes layers via Gestalt (position = spiral topology, color = macro, opacity = micro, size = centrality). Preserves topological structure and produces interactive Plotly HTML with full zoom/pan/hover metadata.
16. `stratified-quota-sampling` is a pragmatic acquisition strategy for resource-constrained data collection. Marginal variance targeting: within strata (e.g., acoustic clusters), sample songs that maximize feature variance. Quota design: bound acquisition budget while maximizing representativeness. Bridges deterministic clustering with probabilistic sampling.

## Repository Layout

- `<skill>\\SKILL.md` -> canonical skill contract
- `copilot-instructions.md` -> repo-wide Copilot guidance
- `request-intent-resolution\\SKILL.md` -> request-thread routing, retrieval, and evaluation skill
- `feature-catalog\\` -> supporting catalog material
- `integrate\\` -> volatile concept intake folder; candidate patterns waiting to be absorbed into live skills

## Integration Intake

- `integrate\\` is an input folder, not a branch in the live skill graph.
- Concepts staged there can inform one or more skills later, but they are not treated as first-class skills until promoted.
- The `llm-wiki` concept has been absorbed by **existing** live skills rather than promoted as its own branch:
  - `agentic_kg_memory` inherited the compiled-wiki maintenance loop, typed readable knowledge units, and canonical-artifact / rebuildable-index rule *(first pass)*
  - `gist-retriever` inherited the staged retrieval/access-path progression across markdown lookup, local markdown search, and compiled retrieval indexes *(first pass)*
  - `memory-bank` inherited the sharper boundary against corpus/wiki memory *(first pass)*
  - `agentic_kg_memory` also inherited *(second pass)*: four-tier consolidation model (working/episodic/semantic/procedural), temporal decay / Ebbinghaus forgetting, supersession as an explicit named operation, event-driven automation hooks, graph traversal for impact/discovery queries, and crystallization as a first-class wiki operation

## Design Principles

- Skills should be composable rather than monolithic.
- Policy, implementation, and tracking should be separated when they have different responsibilities.
- Root-cause fixes beat band-aids.
- Artifacts, evidence, and decisions should be persisted explicitly.
- Between compactions, preserve distilled continuity packets rather than re-deriving the same conclusions.

## Recent Direction

- Added `deep-research` as a child of `agentic-harness`: LangGraph research graph with Selenium fallback fetch pipeline.
- Reframed `agentic-harness` as the multi-framework stationmaster.
- Added `continuity-log` to preserve compact-safe reasoning products between long turns and compactions.
- Absorbed `integrate\\llm-wiki` into existing live skills instead of promoting it as a standalone branch: compiled memory behavior now lives in `agentic_kg_memory`, staged retrieval behavior in `gist-retriever`, and the project-vs-corpus boundary in `memory-bank`.
- Second-pass absorption of `integrate\\llm-wiki`: added consolidation tiers (working/episodic/semantic/procedural), temporal decay, supersession, automation hooks, graph traversal for discovery, and crystallization to `agentic_kg_memory`.
- Added `deep-q-rl` under new `learning/` section: DQN + Russian Doll MCTS pattern generalized from chess-deep-q; applies to any scored discrete-action environment.
