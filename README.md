# skills

Reusable skill library for agentic coding, memory, retrieval, tuning, and orchestration.

Each skill lives in its own folder as `SKILL.md`. The repo is no longer just an
old `.copilot` module scaffold; it is a composable skill graph.

Use this README as the canonical folder map before adding, moving, or wiring a
skill. The AST below should match the live folders in this repository.

## Skill Graph (AST View)

Each node is a skill. Indentation encodes parent → child dependency. Peers share the same indent level.

```
skills/
├── execution/                       # plan, implement, verify
│   ├── react-agent                  # outer execution OS; drives all other skills
│   ├── reasoning                    # open-ended problem decomposition + multi-perspective analysis
│   │   └── causal-inference         # LLM→DoWhy→LLM architecture; Pearl's ladder (association/intervention/counterfactual); causal discovery, do-calculus, SCM via DoWhy + causal-learn
│   ├── codebase-knowledge-graph     # current-repo whole-system map; foundational vs incidental code; ripple analysis before edits
│   ├── code                         # implementation standards, naming, refactor sequence
│   │   └── design-patterns          # GoF / contract / relationship-shape companion to code
│   ├── code-extraction              # extract source files + configs into copy-paste-ready markdown artifact (docling-style)
│   ├── diagnostic-scanner           # language-aware compiler/linter scanning; errors/warnings grouped by severity
│   ├── schema-induction             # cross-instance schema discovery via pairwise contrast (Aristotelian diairesis); constants vs variable dims; CRISP-DM data understanding analog
│   ├── test-planner                 # coverage-aware test plan generation (green/yellow/red status); regression detection
│   ├── doc-synthesizer              # AST-based documentation with Mermaid dependency/data-flow diagrams
│   ├── debugging                    # error isolation, salience tiers, diagnostic strategy, self-repair loop
│   ├── validation                   # test design, verification protocol, behavior contracts
│   │   └── uncertainty-quantification  # 3-tier UQ protocol (fast/standard/thorough); semantic entropy, SelfCheckGPT, conformal prediction, LM-Polygraph; abstain/escalate table
│   ├── architecture                 # system design, abstract-class planning, domain → code mapping
│   ├── tdd-agent                    # Red→Green→Refactor as distinct agentic phases; test-first design contract
│   │   └── program-synthesis        # LLM-assisted formal verification + proof-assisted coding; AutoVerus 3-phase loop; escalation from tdd-agent for unbounded/security properties
│   ├── autoresearch                 # autonomous iterative hill-climbing: scorer + proposer + git/sqlite checkpoint loop
│   ├── cua-desktop-agent            # autonomous desktop automation via VLM perception loop; vision-based retry for legacy/API-less applications
│   └── react-fastapi-sqlite         # full-stack scaffold: React (TanStack Query) + FastAPI (SQLModel ORM) + SQLite; SPA + REST backend
│
├── orchestration/                   # route work, enforce policy, manage cross-session state
│   ├── agentic-design-patterns      # LangGraph workflow shape, router/gate topology, manager/BA/dev/QA rooms
│   ├── agentic-harness              # dark-task control plane; backbone = OpenClaw/Claude Code/OpenCode/Copilot CLI; structured-response contracts + HTP
│   │   ├── checklist                # LLM-as-judge validation pattern; structured findings with novelty proof
│   │   ├── continuity-log           # compact-safe session memory; distilled decisions, resume points
│   │   └── deep-research            # multi-source web evidence pipeline; LangGraph planner→researcher→synthesizer
│   ├── openspec-workflow            # spec-driven change lifecycle with OpenSpec artifacts and Fabro handoff
│   │   ├── openspec-propose         # create proposal/design/spec/tasks for a new change
│   │   ├── openspec-explore         # think/discover mode around an OpenSpec change or idea
│   │   ├── openspec-apply-change    # implement tasks from an OpenSpec change
│   │   └── openspec-archive-change  # archive a completed OpenSpec change
│   ├── fabro-create-workflow        # author Fabro `.fabro` + `.toml` workflows from natural-language requirements
│   ├── substrate-selection          # runtime substrate policy: OpenCode / claw-code / aider / provider boundary
│   ├── evaluator-optimizer          # LLM-generates→LLM-critiques→LLM-regenerates loop; MBR selection; stopping criteria
│   │   └── prompt-optimization      # automatic prompt self-improvement; DSPy (MIPROv2), TextGrad (text-space gradients), OPRO, APE; labeled-trainset → MIPROv2 vs no-trainset → TextGrad decision tree
│   ├── multi-agent-coordination     # peer messaging, plan-approval gates, task ownership, dynamic spawning
│   ├── agent-governance             # safety rails, tool-access policy, audit trail, trust tiers, secrets scan
│   ├── security-review              # STRIDE-A, OWASP Top 10, data-flow tracing, secret/CVE detection
│   ├── build-observability          # run-centric observability contract: runs/events/commands, collectors, dashboards, trace enrichment
│   ├── timeout-guard                # runaway-task policy; interrupt and recovery rules
│   ├── git-workflow                 # branch strategy (test→dev→main), push gates, LLM verification protocol with headless-browser checks
│   ├── validation-artifacts         # mandatory proof protocol: training loss curves, holdout metrics, test logs, visual diffs, API benchmarks, script outputs — "seeing is believing"
│   ├── skill-wiki                   # living skill library lifecycle; intake → staged → active → superseded governance
│   ├── skill-sync                   # LLM-assisted merge for diverged skill copies across local/remote mirrors; cron-safe
│   └── consolidation                # triplet-based pairwise correlation + greedy chain decomposition → merge/xref/migrate prescriptions
│
├── memory/                          # persist knowledge across sessions and tasks
│   ├── memory-bank                  # durable project memory (brief, context, patterns, progress)
│   │   # meta: DESCRIPTION/ARCHITECTURE/HISTORY pattern — applies to any skill folder
│   ├── todo                         # sqlite-backed task tracking with FastMCP bridge
│   ├── cognitive-taxonomy           # unified memory classification: implicit/explicit/agentic paradigms; forms/functions/dynamics; System 1 vs 2 routing
│   ├── memory-architecture          # canonical 5-layer memory stack design: 4 templates (factual KB, personal assistant, autonomous agent, research); inter-layer routing; entity/procedure/query flows
│   ├── agentic_kg_memory            # MCG Context Graph side: semantic memory policy, retrieval, patterns, tribal knowledge, episodic memory
│   │   ├── kg_ontology              # MCG DKG entity-identity layer: synset/hypernym BM25 canonicalization
│   │   └── gist-retriever           # layered sparse+dense retrieval engine (BM25 + Chroma)
│   ├── crystallization              # distill completed work chains into digest pages + reusable lessons; hand off semantic outputs to agentic_kg_memory and procedural deltas to skill-wiki
│   ├── semantic-search-enrichment   # retrieval augmentation: query expansion, metadata boosting, semantic reranking
│   ├── context-compaction           # active context-window management: tiered eviction, pre/post-compaction hooks
│   ├── mcp-tool-registry            # MCP tool registration, discovery, routing, ACI design
│   ├── request-intent-resolution    # request-thread routing, retrieval evaluation
│   └── feature-catalog              # local SQLite feature inventory for implemented capabilities and file mappings
│
├── tuning/                          # measure, optimize, record
│   ├── optuna-nested-cv             # search engine + methodology primer: inner tune / outer unbiased estimate
│   ├── hyper-parm_tuning            # superseded predecessor; canonical home for Weighted Stage Allocation pattern
│   ├── agentic-hyperparm            # behavioral knob tuning for agentic systems; instantiates Stage Allocation for L1-L4 layers
│   ├── class-balancing              # log inverse freq → Box-Cox normalize → ratio weights for imbalanced classifiers
│   ├── stratified-quota-sampling    # coverage-bounded no-replacement sampler; Box-Cox tiers + quota allocation
│   │   └── synthetic-data           # LLM-generated training data; 8 paradigms (Self-Instruct/Evol-Instruct/GLAN/Magpie/UltraFeedback/FireAct/distilabel); 6 mandatory quality gates; handoff to stratified-quota-sampling + class-balancing
│   ├── cluster-quantized-knn        # O(1) approximate distance for KNN via cluster-quantization; fast interactive retrieval
│   ├── mad-dynamic-batching         # MAD-gated token-aware dynamic batching for variable-length training data; quantile partitioning
│   ├── median-bifurcation           # universal median-cut pattern: choose axis → produce both sides → drop unwanted half; 2^n epistemic cells at zero labeling cost; data-level contrastive learning
│   ├── mlflow                       # experiment ledger: params, metrics, artifacts, lineage
│   ├── model-size-reduction         # checkpoint slimming for HF models: dtype cast, layer drop, LoRA extraction, DARE/TIES/DELLA; architecture-agnostic state_dict path
│   ├── generalization-theory        # signal-vs-noise training-dynamics lens via eNTK; diagnose memorization, grokking, and noisy-preference fine-tunes
│   └── representation-pipeline      # representation design: raw signal → embedding space
│
├── artifacts/                       # masterpiece outputs and information design
│   ├── documentation                # choose canonical doc vs changelog vs timestamped fixes-applied artifact
│   ├── response-style               # voice preservation, anti-cliche prose, user-facing coherence
│   ├── business-writing             # professional document writing: resume, cover letter, portfolio; triplet bullets, spice gradient
│   ├── gist_correlation_matrix      # sorted correlation matrix as complete relational map; two sorting approaches (orthogonal vs coverage)
│   ├── nearest-neighbor-chain       # greedy path-cover decomposition of a similarity matrix into variable-length semantic chains; τ selection; chaining = semantic thread
│   └── spiral-radial-clustering-display  # multi-dimensional spiral visualization; GMM+HDBSCAN+ordering→UMAP 2D with Gestalt encoding
│
├── learning/                        # reinforcement learning and policy optimization
│   ├── deep-q-rl                    # DQN + Russian Doll MCTS for any scored discrete-action framework; code-rl extension; SPO/DPO offline preference optimization
│   ├── active-inference             # Bayesian POMDP agents via Free Energy Principle; EFE-driven tool selection; pymdp; use when no reward function + partial observability
│   ├── continual-learning           # non-forgetting agents; EWC, GEM/A-GEM, PackNet, O-LoRA/InfLoRA, DARE, LwF, MemRL; absorbs integrate/MemRL
│   └── siamese_from_correlation_matrix  # derive metric-learning pairs directly from embedding/correlation structure
│
└── pipelines/                       # end-to-end domain workflows (invoke sub-skills as needed)
    ├── auto-ingest                  # on-demand and background PDF enrichment for arxiv_rag corpus; VLM methods extraction
    └── pdf-extraction               # docling→base64 strip→VLM→reinsert→methods; table enhancement with tabula+camelot+VLM fusion; classifier training via class-balancing
```

## Key Relationships

1. `react-agent` is the outer execution OS. All other skills are invoked from inside it.
2. `design-patterns` is the code-facing pattern selector. `code` owns edit mechanics; `design-patterns` chooses the relationship shape and contract.
3. `agentic-design-patterns` chooses LangGraph workflow shape and role topology. It is where routing, prompt chaining, parallel sectioning, voting, orchestrator-workers, evaluator-optimizer, and bounded autonomous loops belong.
4. `substrate-selection` decides which runtime sits behind the graph or harness boundary: OpenCode, claw-code, aider, or another provider surface. Current integrated default: `opencode` for the orchestrator lane, `aider` for the leaf-agent lane.
5. `agentic-harness` is the programmatic train station for coding frameworks (Claude Code, OpenCode, GitHub Copilot CLI, OpenClaw). It routes, gates, and reconciles work; each framework is a worker line, and the resolved runtime stack should be visible in state/logs rather than hidden in helper code.
6. `continuity-log` is a child of `agentic-harness`. It holds the compact-safe distilled state that lets the harness resume without re-deriving decisions.
7. `deep-research` is a child of `agentic-harness`. It decomposes a question into parallel subquestions, gathers web evidence via a 3-tier fetch pipeline (httpx → retry → Selenium), and synthesizes a claim-backed report seeding the harness TaskSpec.
8. `optuna-nested-cv` is now self-contained: the Methodology Primer (what to optimize, preconditions, layerwise decomp, structured search, sampler policy) was absorbed from `hyper-parm_tuning` (now superseded). `mlflow` records every run with lineage.
9. `agentic_kg_memory` is the **CG (Context Graph) side** of the MCG architecture: semantic memory policy, patterns, tribal knowledge, retrieval. `kg_ontology` is the **DKG entity-identity layer**: synset/hypernym BM25 canonicalization that prevents duplicate nodes without graph topology traversal. They are complementary layers, not alternatives — do not merge them again.
10. `gist-retriever` is the retrieval sub-skill for that memory layer. It spans the access-path progression from markdown/index-first lookup through local markdown search and into the full hybrid BM25+dense pipeline.
11. `memory-bank` remains project operating memory, not compiled corpus memory. It stores project continuity while `agentic_kg_memory` stores evolving domain knowledge.
12. The supplementary comparison boundary is now explicit in the repo: **RAG/retriever** behavior belongs in `gist-retriever`, **LLM Wiki/compiler** behavior belongs in `agentic_kg_memory`, and **GBrain/operator / fat-skills orchestration** belongs on the execution/orchestration side, not in the memory branch.
13. KnowledgeWeaver is treated as a concrete implementation example of the compiler side: typed readable knowledge units plus a compiled index that can be rebuilt from canonical markdown artifacts.
14. `agentic-harness` (waterfall -> agile: topics -> plans -> specs -> tasks) is the lifecycle template for skill authoring, not just software projects.
15. `deep-q-rl` is the generalized RL framework for any scored discrete-action environment. Combines value-head Q-network, experience replay, target network, Russian Doll MCTS, AHA online mistake correction, and training-progress annealing. Includes Code-RL (RL from test-execution feedback) and SPO/offline preference optimization (reward-weighted SFT, DPO) with reward design rules, generation parameter pitfalls, and epoch validation protocol. Derived from `thistleknot/chess-deep-q`.
16. `checklist` is a subskill of `agentic-harness`. It is the Pydantic-schema LLM-as-judge pattern: structured findings with novelty proofs, non-fatal execution, `review_required` flag, and cross-run fingerprinting via throughline Q-scores. Reference implementation: `gap_critic.py` in storywriter.
17. `gist_correlation_matrix` is the "true GIST output": sorted correlation matrix as complete relational map (N^2 cells, each encoding pairwise relationship). Two sorting strategies: **orthogonal** (information-theoretic maximization, sharp drop-off) and **coverage** (hierarchical boundary exploration, expanding bands). Outputs: interactive HTMLs with full zoom/pan/hover.
18. `spiral-radial-clustering-display` is the multi-dimensional hierarchical clustering visualization skill. Maps four layers (macro GMM + micro HDBSCAN + decorrelated ordering + hubness) into 3D feature space, projects via UMAP to 2D, encodes layers via Gestalt (position = spiral topology, color = macro, opacity = micro, size = centrality). Preserves topological structure and produces interactive Plotly HTML with full zoom/pan/hover metadata.
19. `feature-catalog` is the local implementation ledger: a SQLite feature catalog for tracking what the project already ships and where it lives.
20. `siamese_from_correlation_matrix` is the metric-learning companion to the embedding-analysis branch: it turns correlation structure into contrastive supervision.
21. `skill-wiki` is the meta-skill governing the living skill library lifecycle. It owns the intake pipeline, promotion gates, supersession rules, sidecar conventions (EVIDENCE.md, HISTORY.md, scripts/ examples), and the periodic sweep that keeps skills consistent over time. It routes verified work chains into `crystallization` when the output is a digest, and handles staged skill-contract updates when the output is a library change. It is NOT memory storage (→ `agentic_kg_memory`) and NOT project state (→ `memory-bank`).
22. `documentation` decides which durable doc artifact to update: canonical README/spec, cumulative changelog, or a timestamped fixes-applied note.
23. `response-style` governs user-facing prose: voice preservation, anti-cliche writing, and answer coherence. Harness-state coherence remains with `agentic-harness`.
24. `class-balancing` is a general-purpose class weight protocol. It computes log inverse frequency per class, applies Box-Cox normalization to tame the distribution tail, clips negatives, and normalizes to ratios for use as `class_weight` in sklearn or `weight` in PyTorch CrossEntropyLoss. Used anywhere labeled data has heavy class imbalance — layout element classification, NER, retrieval judgment labeling.
25. `stratified-quota-sampling` owns fixed-budget coverage schedulers: Box-Cox tiering, quota allocation, and no-replacement sampling from an imbalanced pool. Pair it with `class-balancing` when quota selection alone still leaves residual label skew inside the loss, and with `optuna-nested-cv` when sample fraction, quota ratios, or tier weighting are part of the tuning contract.
26. `pdf-extraction` is the end-to-end PDF→enriched-Markdown pipeline workflow: docling→base64 strip→VLM image description→reinsert→methods extraction (5 phases via `run_pipeline.bat`). Includes a table enhancement sub-pipeline: docling JSON bboxes→pymupdf crop→tabula+camelot extraction→VLM fusion→patched Markdown. The layout classifier uses `class-balancing` for training. Standalone workflow skill; not a child of `agentic-harness`.
27. `openspec-workflow` is the spec-driven product/change lifecycle skill. Its companion action skills (`openspec-propose`, `openspec-explore`, `openspec-apply-change`, `openspec-archive-change`) are command-shaped entry points into the same OpenSpec operating model.
28. `fabro-create-workflow` is the Fabro graph/run-config authoring companion. It can support `openspec-workflow` when a repo needs a new Fabro pipeline, but it is also usable as a standalone workflow-design skill.
29. `agentic-harness` now has an explicit evaluation mix: `checklist` for structured audit artifacts, DSPy-derived metric/reward compile-refine patterns when scoring is explicit, and TextGrad-derived textual-loss loops when the critic must explain how to improve text/code/prompts. Optimizer scores inform repair; artifact-backed verification still decides completion.
30. `codebase-knowledge-graph` is the current-repository relationship-mapping protocol. It builds the typed module/file/class/function graph and the foundational-vs-incidental distinction that should exist before `code`, `debugging`, or `validation` edits proceed.
31. `code-extraction` extracts source files + configs from any project into a unified markdown artifact (docling-style: parse → normalize → markdown + JSON metadata). Supports multi-language detection (Python, Go, Rust, Swift, Java, JS/TS via markers or 8+ source files). Output feeds `codebase-knowledge-graph`, `documentation`, and LLM context assembly.
32. `diagnostic-scanner` invokes language-appropriate tools (mypy/pylint, go vet, cargo check, swiftc, eslint, etc.) and normalizes errors/warnings by severity and category. Produces fix prompts ready for LLM remediation. Output feeds `validation` and `code` for structured violation handling.
33. `model-size-reduction` owns post-training checkpoint reduction: dtype casting, layer dropping, LoRA extraction, and DARE/TIES/DELLA sparsification directly against Hugging Face `state_dict`s. `continual-learning` still owns DARE as a lifelong-learning merge pattern; use `model-size-reduction` when the goal is footprint, portability, or architecture-agnostic checkpoint surgery.
34. `generalization-theory` is the training-dynamics diagnostic lens for signal-vs-noise partitioning, grokking delay, and noisy-preference memorization. It helps choose intervention surfaces across data, architecture, and optimizer design, but it does not own the tuning/search loop (`optuna-nested-cv`) or long-horizon forgetting control (`continual-learning`).
35. `test-planner` generates coverage-aware test plans with status flags (🟢 GREEN=DONE, 🟡 YELLOW=PARTIAL, 🔴 RED=MISSING). Proposes concrete scenarios by test level (smoke/unit/integration/e2e/regression) and detects regression subjects via git diff. Output feeds `tdd-agent` for test-driven implementation and `validation` for coverage verification.
36. `doc-synthesizer` parses project structure via AST (Python focus; all languages via markers), builds dependency graphs, and generates Mermaid diagrams for module dependencies and data flow. Output feeds `documentation`, `codebase-knowledge-graph`, and architecture review. URI fetch/crawl extensible for Phase 2.
37. `build-observability` is the run-centric observability layer for agentic execution. `agentic-harness` owns control flow and retries; `build-observability` projects runtime exhaust into normalized `runs/events/commands` records and operator-facing dashboard views.
38. `react-fastapi-sqlite` is the full-stack application scaffold skill: React frontend (with TanStack Query for server-state caching), FastAPI backend (with SQLModel ORM layer), and SQLite file-based database. Use when building SPAs with Python REST backends, configuring client-side data fetching and invalidation patterns, or structuring domain-driven CRUD operations. Output: production-ready project layout with separation of concerns (api/ → hooks/ → pages/components/ hierarchy). Integrates with `code` for implementation standards and `validation` for integration testing.
39. `git-workflow` is the branch strategy and LLM safety protocol for this repository. Enforces test→dev→main push gates, requires LLM verification against last known working commit before each push, and pairs `code` verification (git diff checks) with `headless-browser-verification` screenshots for web frontend changes. Prevents accidental pushes to main by requiring explicit user approval at each stage.

40. `cognitive-taxonomy` is the **reference skill for all memory decisions**. It synthesizes four peer-reviewed papers into a unified classification system: implicit/explicit/agentic paradigms, forms/functions/dynamics taxonomy, biological-artificial crosswalk, and neuro-symbolic System 1 vs System 2 dual-process reasoning. Use it to classify memory patterns, route queries correctly, diagnose underperformance (why is vector-only failing?), and design new memory architectures. It's a pure reference skill (no code changes) that sits above all memory subsystems (`agentic_kg_memory`, `procedural-memory`, `continuity-log`, `context-compaction`).

41. `memory-architecture` is the **canonical design reference for agent memory systems**. Implements the Meta Context Graph layered stack with 4 concrete templates: (1) factual knowledge base (Implicit→Explicit→Working), (2) personal assistant with memory (adds Episodic), (3) autonomous agent (adds Procedural), (4) research/knowledge synthesis pipeline. Each template includes full 5-layer architecture, entity anchor flow, procedure discovery flow, query routing lifecycle, and anti-patterns. Use when designing a new agent with memory, evaluating existing systems for gaps, onboarding developers. Depends on `cognitive-taxonomy` for classification; feeds into `procedural-memory`, `agentic_kg_memory`, `context-compaction` for implementation.

42. `validation-artifacts` enforces the principle **"seeing is believing"** by making validation proof mandatory, not optional. Before any skill claims "validation passed", this skill demands reproducible artifacts: training loss curves + eval metrics on holdout sets, predictions + confusion matrices, test execution logs with exit codes, before/after screenshots + visual diffs, API request/response samples + latency profiles, script execution examples with outputs. Used by `validation`, `checklist`, `tdd-agent`, `debugging`, `git-workflow` to prevent "trust me" claims. Integrates with `headless-browser-verification` (UI artifacts) and `security-review` (security validation artifacts).

43. `skill-sync` is the **LLM-assisted merge protocol for diverged skill copies** across master and local/remote mirrors. Distinct from `skill-wiki` (governance: intake/staging/lifecycle) — `skill-sync` is operational: when both master and a mirror have independently changed since the last commit, it classifies the case (no-op / fast-forward / conflict), applies deterministic fast-forwards automatically, and routes true conflicts to an LLM merge that incorporates both sets of changes without dropping content from either side. Mechanically executed by `sync_skills.ps1`. MERGE-CONFLICT markers flag unresolved sections for human review before commit.

44. `consolidation` is the **triplet-based document consolidation pipeline** for living knowledge bases and skill libraries. Extracts subject-predicate-object triplets from each document, computes a pairwise Jaccard similarity matrix (or NLI-based soft Jaccard for semantic matching), runs **greedy nearest-neighbor chain decomposition** (single-linkage chaining) to group related documents, and emits a sorted report with prescriptions: MERGE (≥0.8), migrate (0.5–0.8), xref (0.3–0.5). Groups are sorted by chain length descending — largest clusters first. Sits above `gist_correlation_matrix` (matrix builder) and feeds prescriptions into `skill-wiki` (governance) and `skill-sync` (mechanical merge). Use when the library has grown by ≥5 new entries, semantic search returns contradictory results, or a scheduled consolidation run is due.

45. `nearest-neighbor-chain` is the **greedy path-cover chain decomposition sub-skill** shared by `consolidation` and any other consumer that needs to partition a similarity matrix into semantic groups. It walks pairs sorted by descending score, extends only chain endpoints (no branching), and emits variable-length chains sorted by length descending. Singletons are docs with no above-τ neighbours. The "chaining effect" of single-linkage is intentional: each chain is a semantic thread; a chain break is a topic boundary. `gist_correlation_matrix` produces the matrix; `nearest-neighbor-chain` decomposes it; `consolidation` adds triplet extraction and MERGE/migrate/xref prescriptions on top.

46. `prompt-optimization` is the **automatic prompt self-improvement skill**. A child of `evaluator-optimizer` that applies optimization algorithms — not manual rewriting. Labeled trainset + multi-step → DSPy MIPROv2 (Bayesian joint instruction+demo search). No trainset + differentiable loss → TextGrad (text-space gradient descent). Demos only → APE. Single instruction → OPRO. `agentic-harness` invokes this when a module's loss metric is stable but prompt quality is the bottleneck. Absorbs `integrate/dspy.md` and `integrate/textgrad.md`.

47. `uncertainty-quantification` is the **LLM output confidence protocol**. A child of `validation` for measuring when a model knows vs. doesn't know. Three-tier protocol: Tier 1 = fast (logprobs/verbal, <0.1s), Tier 2 = standard (N=3–5 consistency samples), Tier 3 = thorough (N≥10 + conformal prediction). Semantic entropy (arXiv:2302.09664) outperforms token-level entropy. Always use Tier 3 minimum for irreversible actions. Libraries: `selfcheckgpt`, `lm-polygraph`. Feeds `checklist` for audit trails and `uncertainty-quantification` threshold gates in `agent-governance`.

48. `causal-inference` is the **LLM→DoWhy→LLM causal reasoning chain**. A child of `reasoning`. LLMs hallucinate on formal do-calculus (near-random; arXiv:2306.05836) — all estimation routes through DoWhy, not the LLM. Three-phase protocol: LLM proposes DAG → causal-learn validates (PC/FCI/GES) → DoWhy identifies+estimates. LLM only interprets results. Counterfactual queries use `dowhy.counterfactual_outcomes`. Libraries: `dowhy`, `causal-learn`, `econml`, `pywhy-llm` (experimental).

49. `synthetic-data` is the **LLM-generated training data pipeline**. A child of `stratified-quota-sampling`. Eight paradigms ordered by fidelity: Self-Instruct → Evol-Instruct → GLAN → Magpie → Self-Play → Persona-driven → Task-specific → Preference. Six mandatory quality gates in order: dedup → schema → LLM judge → IFD → coverage → safety. Model collapse risk (arXiv:2305.17493): requires a strong fixed teacher (GPT-4/Llama-3-70B), never train-on-own-outputs without mixing real data. Clean three-stage handoff: `synthetic-data` → `stratified-quota-sampling` → `class-balancing`. Library: `argilla-io/distilabel`.

50. `continual-learning` is the **non-forgetting agent training protocol**. Sits in `learning/` alongside `deep-q-rl`. Prevents catastrophic forgetting when a model must learn a new task without erasing prior skills. Six approaches by compute budget: EWC (regularization, cheapest) → LwF (distillation) → GEM/A-GEM (episodic memory constraint) → PackNet (parameter isolation) → O-LoRA/InfLoRA (LoRA orthogonalization) → MemRL (frozen backbone + episodic Q-value memory, ICML 2026). `procedural-memory` EMA (β=0.9) is intentionally aligned with single-sample EWC. Absorbs `integrate/MemRL` (arXiv:2601.03192). Libraries: Avalanche, Mammoth, HuggingFace PEFT.

51. `program-synthesis` is the **formal verification + proof-assisted coding skill**. A child of `tdd-agent` — `tdd-agent` escalates here when the property is unbounded, security-critical, or requires exhaustive correctness guarantees. AutoVerus (arXiv:2409.13082): 91.3% on 150 Verus tasks using GPT-4o + Rust ghost code, ~$37 total. EvalPlus (arXiv:2305.01210): pass@k drops 19–28% with exhaustive testing vs. HumanEval — all `tdd-agent` benchmarks should use EvalPlus. Three-phase loop: generate → verify (formal checker) → repair (RLEF feedback). Integration: `tdd-agent` handles empirical tests; `program-synthesis` handles formal properties.

52. `active-inference` is the **Bayesian POMDP agent skill** based on the Free Energy Principle. Sits in `learning/` as a complement to `deep-q-rl`, not a replacement. Use when: partial observability (can't see full state), no clean scalar reward (prefer EFE preferences), principled tool selection (epistemic value drives info-gathering before committing to action). EFE decomposes into epistemic value (info gain) + pragmatic value (reach preferred obs) — no reward design needed. Russian Doll MCTS ≈ Sophisticated Inference: both use tree search; EFE replaces Q-value as node score. Library: `inferactively-pymdp`. Use `deep-q-rl` when full observability + `evaluate(state)` exists.

53. `median-bifurcation` is the **universal median-cut discriminative signal skill**. Any useful distinction a model or system must learn is a binary median cut. Three-step protocol: choose partition axis → produce both sides explicitly (hard negatives baked in, not mined post-hoc) → drop unwanted partition at inference. Applied recursively, n bifurcations yield 2^n epistemic cells at zero additional labeling cost. This is data-level contrastive learning: the loss sees ordinary cross-entropy; discriminative pressure comes from the data layout. Inspired by ANOVA factorial designs and k-means via median divisions. `mad-dynamic-batching` is a concrete instantiation for token-length distributions.

## MCG Foundation — The Conceptual Backbone

The skill library is an implementation of the **Meta Context Graph (MCG)** architecture
(Tekiner, 2025; Hu et al. arXiv:2512.13564) applied to automated software development.
MCG is the glue that ties gstack (fat operational patterns) to llm-wiki (compiled living
knowledge): both are instantiated here as the skills themselves (procedural memory) and
the Pattern Store vetting pipeline (tribal knowledge lifecycle).

The full MCG system comprises two complementary graphs:

| MCG Component | Software Dev Equivalent | Skill |
|---|---|---|
| Domain KG — entities & relationships | Codebase / domain model | `agentic_kg_memory` + `kg_ontology` |
| DKG entity identity layer | Symbol/module canonicalization | `kg_ontology` |
| Context Graph — decision traces (episodic) | learnings.jsonl, per-task rationale | `agentic-harness` |
| CG patterns (semantic) | Pattern Store pending → tenure | `skill-wiki` |
| CG tribal knowledge (semantic) | Pattern Store promoted entries | `skill-wiki` → skill files |
| CG procedural schemas | **The SKILL.md files themselves** — model-agnostic, slot-in primitives | This whole library |
| L4 Runtime state | Session / active context | `continuity-log`, `memory-bank` |
| L3 Organisation conventions | Team / project norms | `memory-bank` project brief |
| L2 Industry / domain | Domain KG per project | `agentic_kg_memory` |
| L1 Universal best practices | Base skill library | This repo |

**The skills are procedural memory** (CoALA taxonomy, arXiv:2309.02427). They cannot be
summarized into a prompt and RAG-retrieved with equal effect — they must be invoked. This
is the distinction between a great chef's accumulated technique and a recipe book. The
Pattern Store vetting pipeline (3 applications → promote) implements the tribal knowledge
lifecycle from MCG: `tk_candidates` → reviewed → `tribal_knowledge` (active rule) →
compiled into a skill.

For the full architecture, see `agentic_kg_memory/SKILL.md § MCG Foundation`.

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
  - `agentic_kg_memory` also inherited *(second pass)*: four-tier consolidation model (working/episodic/semantic/procedural), temporal decay / Ebbinghaus forgetting, supersession as an explicit named operation, event-driven automation hooks, and graph traversal for impact/discovery queries. The crystallization protocol was later promoted into the standalone `crystallization` skill, while `agentic_kg_memory` kept digest-ingestion and graph-update semantics
- The `fat-skills` concept is **explicitly closed by absorption**, not left partial and not promoted as a standalone skill:
  - `skill-wiki` owns the library-level lifecycle that a monolithic "fat skills" wrapper would otherwise have covered: intake, staged vetting, promotion, supersession, and periodic consistency sweeps
  - `agentic-harness` owns the execution-side orchestration layer: train-station routing, hierarchical task planning, critic / optimizer loops, and multi-framework runtime reconciliation
  - Repo-wide routing guidance lives at the library surface (`README.md` + `copilot-instructions.md`), so invocation policy is documented across the graph rather than hidden inside one umbrella node
  - Memory and policy concerns stay split across their live homes: `memory-bank` / `continuity-log` for project and runtime continuity, `agentic_kg_memory` for compiled semantic memory, and `agent-governance` for policy / audit / trust rails
- The `dev-pipeline` concept is **explicitly closed by absorption**, not left partial and not promoted as a standalone skill:
  - `react-agent` owns the outer autonomous execute / observe / verify loop
  - `openspec-workflow` and its action skills own the spec-driven change lifecycle
  - `code`, `tdd-agent`, `debugging`, and `validation` own implementation, test-first change, bug isolation, and verification
  - `agentic-harness` owns multi-stage pipeline orchestration, HTP, evaluation / repair loops, and the absorbed autoship-style control-plane behavior
  - `documentation`, `agent-governance`, `security-review`, `mcp-tool-registry`, and `fabro-create-workflow` cover the supporting release / safety / tooling lanes that would otherwise be bundled into a generic "dev pipeline" skill

### North-Star Disposition Audit

Use this README as the live-skill audit source of truth for the concepts that were still unresolved in `integrate/compiled.md`. They are now fully dispositioned through promotion into the live graph or explicit absorption into existing skills.

| `integrate/compiled.md` concept | Live disposition |
|---|---|
| `build-observability` | **live skill** → `build-observability` |
| `codebase-knowledge-graph` | **live skill** → `codebase-knowledge-graph` |
| `fat-skills` | **closed by absorption** → `skill-wiki` + `agentic-harness` + repo routing guidance + memory / governance split |
| `dev-pipeline` | **closed by absorption** → `react-agent` + `openspec-workflow` + execution skills + `agentic-harness` + supporting release / safety lanes |

## Design Principles

- Skills should be composable rather than monolithic.
- Policy, implementation, and tracking should be separated when they have different responsibilities.
- Root-cause fixes beat band-aids.
- Artifacts, evidence, and decisions should be persisted explicitly.
- Between compactions, preserve distilled continuity packets rather than re-deriving the same conclusions.
- AI makes completeness cheap: always choose the complete implementation over the shortcut.

## Living Skill Library

Skills compound over time. Each skill accumulates evidence (EVIDENCE.md) and changelog history (HISTORY.md) alongside its behavioral contract (SKILL.md). The governance lifecycle is:

```
integrate/          ← raw intake (awesome-copilot, gstack, llm-wiki, etc.)
integrate/staged/   ← validated concepts awaiting promotion
<skill>/SKILL.md    ← active behavioral contract (status: active)
<superseded>        ← retired skills (status: superseded, superseded_by: <name>)
```

Promotion gate: one Tier-1/2 evidence item + one local validation, OR two independent Tier-1–3 items from distinct source types. See `skill-wiki/SKILL.md` for the full governance contract.

SKILL.md frontmatter fields:
```yaml
status: active          # raw | staged | active | superseded
last_validated: YYYY-MM-DD
supersedes: []
superseded_by: null
validation_method: benchmark | production | community | session | theoretical
```

## Automated Software Development Pipeline

This library is optimized for automated software development. Skill-to-pipeline stage mapping:

| Stage | Skill(s) |
|---|---|
| Understand intent, decompose | `reasoning`, `architecture` |
| Explore requirements before formalizing a change | `openspec-explore`, `reasoning` |
| Draft OpenSpec artifacts for a new change | `openspec-propose`, `openspec-workflow` |
| Execute multi-step task autonomously | `react_agent` |
| Map an existing repo as a whole system before editing | `codebase-knowledge-graph` |
| Generate / modify code | `code` |
| Test-driven implementation | `tdd-agent` |
| Isolate and fix bugs | `debugging` |
| Autonomous fix-run-retry loop | `debugging` (self-repair section) |
| Verify behavior, write tests | `validation` |
| Implement tasks from a spec-driven change | `openspec-apply-change`, `openspec-workflow` |
| Finalize/archive a completed spec-driven change | `openspec-archive-change`, `openspec-workflow` |
| Author Fabro workflow graphs and run configs | `fabro-create-workflow` |
| Produce README / changelog / fixes-applied docs | `documentation` |
| Iterative output quality improvement | `evaluator-optimizer` |
| Autonomous hill-climbing on a metric | `autoresearch` |
| Orchestrate multi-stage pipeline | `agentic-harness` |
| Make live run/build state queryable | `build-observability` |
| Optimizer-style evaluation and refinement | `agentic-harness` (DSPy/TextGrad evaluation stack), `checklist` |
| Hierarchical task decomposition | `agentic-harness` (HTP section) |
| Coordinate multiple agents | `multi-agent-coordination` |
| Agent safety rails and policy | `agent-governance` |
| AI checks as CI merge gates | `agent-governance` (agent-as-ci-gate section) |
| Security scanning and threat modeling | `security-review` |
| Context window management and compaction | `context-compaction` |
| MCP tool registration and routing | `mcp-tool-registry` |
| Offline batch eval, regression detection | `checklist` (eval-pipeline section) |
| Hyperparameter search / training | `optuna-nested-cv`, `mlflow` |
| Imbalanced classifier class weights | `class-balancing` |
| PDF→enriched-Markdown pipeline | `pdf-extraction` |
| Semantic knowledge retrieval | `agentic_kg_memory`, `gist-retriever` |
| Cross-session episodic recall | `agentic_kg_memory` (episodic section) |
| RL from code execution feedback | `deep-q-rl` (code-rl section) |
| SPO / DPO / offline preference optimization | `deep-q-rl` (SPO section) |
| Reward function design, binary vs graded rewards | `deep-q-rl` (SPO section) |
| Project state and continuity | `memory-bank`, `continuity-log` |
| Web research and grounding | `deep-research` |
| Skill library governance | `skill-wiki` |
| Rewrite or polish user-facing prose / tone | `response-style` |

## Recent Direction

- **2026-05-09**: Promoted `crystallization` into a standalone live skill. `skill-wiki` now owns routing and staged skill-library deltas, `crystallization` owns the actual work-chain distillation protocol, and `agentic_kg_memory` owns digest ingestion and graph updates.
- **2026-05-02**: Promoted `build-observability` and `codebase-knowledge-graph` from unresolved `integrate/compiled.md` concepts into live skills. `build-observability` now owns the normalized `runs/events/commands` observability contract and projection/dashboard pattern; `codebase-knowledge-graph` now owns current-repo whole-system mapping, foundational-vs-incidental classification, and ripple analysis before edits.
- **2026-05-09**: Imported `model-size-reduction` and `generalization-theory` from the local research/wiki intake. `model-size-reduction` now owns architecture-agnostic Hugging Face checkpoint slimming and delta sparsification; `generalization-theory` now owns the eNTK signal-vs-noise diagnostic lens for memorization, grokking, and noisy-preference fine-tuning.
- **2026-05-02**: Explicitly closed the `fat-skills` and `dev-pipeline` umbrella concepts by absorption rather than promotion. `fat-skills` is now documented as split across `skill-wiki`, `agentic-harness`, repo-level routing guidance, and the existing memory / governance surfaces; `dev-pipeline` is documented as split across `react-agent`, `openspec-workflow`, the execution skills, and `agentic-harness`.
- **2026-05-02**: Grounded the `agentic-harness` evaluation lane in `DSPy` and `TextGrad`. Added `integrate/dspy.md` and `integrate/textgrad.md`, extended `integrate/compiled.md` with `optimizer-driven-evaluation`, and updated the live `agentic-harness` skill to distinguish structured audit (`checklist`) from metric/reward compile-refine loops (DSPy) and textual-loss refinement loops (TextGrad).
- **2026-05-02**: Added `class-balancing` (log inverse freq → Box-Cox → ratio weights for imbalanced classifiers) and `pdf-extraction` (full docling pipeline + table enhancement via tabula+camelot+VLM fusion). `hyper-parm_tuning` now frames Weighted Stage Allocation as the canonical cross-skill pattern; `agentic-hyperparm` is the agent-specific instantiation. `arxiv-bridge` was updated with CLI flags and a sequential-only warning.
- Imported the portable OpenSpec/Fabro skill family as live agent skills: `openspec-workflow`, `openspec-propose`, `openspec-explore`, `openspec-apply-change`, `openspec-archive-change`, and `fabro-create-workflow`. Current rollout is agent-only first; any dark-factory pipeline promotion remains a separate second pass.
- **Wave 3 Pareto additions** (Tier 3, scores 6–9): `autoresearch` (new skill); `context-engineering` section → `code`; `eval-pipeline` section → `checklist`; `agent-as-ci-gate` full protocol → `agent-governance`; `code-rl` section → `deep-q-rl`. All 15 Pareto candidates now implemented.
- **Super System Prompt extraction finished**: added `documentation` (timestamped-vs-cumulative doc strategy) and `response-style` (voice preservation, anti-cliche prose, user-facing coherence).
- **Wave 2 Pareto additions** (Tier 2, scores 12–16): `context-compaction`, `security-review`, `mcp-tool-registry` (new skills); `self-repair` section → `debugging`; `hierarchical-task-planning` section → `agentic-harness`; `episodic-memory` section → `agentic_kg_memory`.
- **Wave 1 Pareto additions** (Tier 1, all score ≥ 20): `evaluator-optimizer`, `multi-agent-coordination`, `tdd-agent`, `agent-governance`. Fills the largest gaps: iterative generation loop, team topology, test-first lifecycle, and safety rails.
- **MCG grounding pass**: Grounded the full skill library in the Meta Context Graph (MCG) architecture (Tekiner 2025, Hu et al. arXiv:2512.13564, CoALA arXiv:2309.02427, ACE arXiv:2510.04618). Added MCG Foundation section to README, MCG Architecture section to `agentic_kg_memory/SKILL.md`, and MCG terminology alignment to `skill-wiki` Pattern Store.
- **Restored `kg_ontology` to `status: active`**: The prior merge into `agentic_kg_memory` was architecturally wrong. `kg_ontology` owns the DKG entity-identity layer (synset/hypernym BM25 canonicalization); `agentic_kg_memory` owns the CG retrieval side. Two distinct MCG concerns.
- Added `deep-research` as a child of `agentic-harness`: LangGraph research graph with Selenium fallback fetch pipeline.
- Reframed `agentic-harness` as the multi-framework stationmaster.
- Added `continuity-log` to preserve compact-safe reasoning products between long turns and compactions.
- Absorbed `integrate\\llm-wiki` into existing live skills instead of promoting it as a standalone branch: compiled memory behavior now lives in `agentic_kg_memory`, staged retrieval behavior in `gist-retriever`, and the project-vs-corpus boundary in `memory-bank`.
- Second-pass absorption of `integrate\\llm-wiki`: added consolidation tiers (working/episodic/semantic/procedural), temporal decay, supersession, automation hooks, graph traversal for discovery, and an initial crystallization contract to `agentic_kg_memory`. That protocol has since been promoted into the standalone `crystallization` skill.
- Added `deep-q-rl` under new `learning/` section: DQN + Russian Doll MCTS pattern generalized from chess-deep-q; applies to any scored discrete-action environment.
- Merged `hyper-parm_tuning` → `optuna-nested-cv`: Methodology Primer section (preconditions checklist, layerwise decomposition, structured search protocol, sampler policy for LLM judges, search space type guide). `hyper-parm_tuning` is now `status: superseded`.
- Fattened `agentic-harness` with gstack-derived patterns: Learnings Compounding (learnings.jsonl schema, 4 persistence layers), Automated Dev Pipeline (Autoship state machine), Review Army (7 specialists + adaptive ceremony), Context Compaction During Long Runs.
- Fattened `deep-research` with research epistemology: Perspective Diversity (STORM), Source Quality Hierarchy (5-tier), Per-Role Model Strategy, Citation Chain Integrity, Research Anti-Patterns.
- Added Pattern Store vetting mechanism to `skill-wiki/SKILL.md`: vector store as pre-skill staging, 3-application tenure threshold, confidence decay formula (`e^(-0.1 × months)`), prune gate, promotion pipeline → `integrate/staged/`.
- All live and retained-historical `SKILL.md` files now carry `status:` governance frontmatter. `hyper-parm_tuning` remains the preserved superseded predecessor.
- Added `design-patterns`, `agentic-design-patterns`, and `substrate-selection` as distinct skills so code pattern choice, LangGraph workflow shape, and runtime selection no longer collapse into `agentic-harness`.
- Absorbed `integrate/gstack` ETHOS: "Boil the Lake" (completeness is cheap with AI) into `code/SKILL.md`; "Search Before Building" (3-layer knowledge taxonomy) into `code/SKILL.md`.
- Absorbed `integrate/gstack/investigate` Iron Law (no fix without root cause) and 5-phase debugging protocol into `debugging/SKILL.md`.
- Added Skill Routing section to `copilot-instructions.md` mapping request types to skills (pattern from gstack CLAUDE.md).
- Added `## Applicability Envelope` to `agentic-harness/SKILL.md` and `debugging/SKILL.md` as template for all live skills.
- Living Skill Library infrastructure: `integrate/README.md`, `integrate/staged/README.md`, `agentic-harness/EVIDENCE.md`, `agentic-harness/HISTORY.md`.
- Added "Living Skill Library" lifecycle documentation and "Automated Software Development Pipeline" mapping to `README.md`.
