
PS C:\Users\user\Documents\dev\skills> .\sync_skills.ps1

------------------------------------------------------------
  Reading last commit timestamp
------------------------------------------------------------
  Last commit : 05/25/2026 10:36:38
  Master      : C:\Users\user\Documents\dev\skills
  Master clean: no

------------------------------------------------------------
  Checking for skill folders missing from master
------------------------------------------------------------
  None.

------------------------------------------------------------
  Checking tracked .md files newer than last commit
------------------------------------------------------------
  [NEWER] README.md                                               2026-05-25 13:18
  [NEWER] README.md                                               2026-05-25 13:18

------------------------------------------------------------
  Reconciliation
------------------------------------------------------------

2 tracked file(s) differ from master:
  Fast-forward (mirror additive): 0
  Conflict (both sides diverged): 2
How to handle? [y=auto-apply all / n=skip all / d=review each] (default: d): y
  [CONFLICT] README.md -- invoking LLM merge

  === SKILL-SYNC LLM MERGE CONTEXT: README.md ===
  -- Base document --------------------------------------------------
# skills

Reusable skill library for agentic coding, memory, retrieval, tuning, and orchestration.

Each skill lives in its own folder as `SKILL.md`. The repo is no longer just an
old `.copilot` module scaffold; it is a composable skill graph.

Use this README as the canonical folder map before adding, moving, or wiring a
skill. The AST below should match the live folders in this repository.

## Skill Graph (AST View)

Each node is a skill. Indentation encodes parent ΓåÆ child dependency. Peers share the same indent level.

```
skills/
Γö£ΓöÇΓöÇ execution/                       # plan, implement, verify
Γöé   Γö£ΓöÇΓöÇ react-agent                  # outer execution OS; drives all other skills
Γöé   Γö£ΓöÇΓöÇ reasoning                    # open-ended problem decomposition + multi-perspective analysis
Γöé   Γöé   ΓööΓöÇΓöÇ causal-inference         # LLMΓåÆDoWhyΓåÆLLM architecture; Pearl's ladder (association/intervention/counterfactual); causal discovery, do-calculus, SCM via DoWhy + causal-learn
Γöé   Γö£ΓöÇΓöÇ codebase-knowledge-graph     # current-repo whole-system map; foundational vs incidental code; ripple analysis before edits
Γöé   Γö£ΓöÇΓöÇ code                         # implementation standards, naming, refactor sequence
Γöé   Γöé   ΓööΓöÇΓöÇ design-patterns          # GoF / contract / relationship-shape companion to code
Γöé   Γö£ΓöÇΓöÇ code-extraction              # extract source files + configs into copy-paste-ready markdown artifact (docling-style)
Γöé   Γö£ΓöÇΓöÇ diagnostic-scanner           # language-aware compiler/linter scanning; errors/warnings grouped by severity
Γöé   Γö£ΓöÇΓöÇ schema-induction             # cross-instance schema discovery via pairwise contrast (Aristotelian diairesis); constants vs variable dims; CRISP-DM data understanding analog
Γöé   Γö£ΓöÇΓöÇ test-planner                 # coverage-aware test plan generation (green/yellow/red status); regression detection
Γöé   Γö£ΓöÇΓöÇ doc-synthesizer              # AST-based documentation with Mermaid dependency/data-flow diagrams
Γöé   Γö£ΓöÇΓöÇ debugging                    # error isolation, salience tiers, diagnostic strategy, self-repair loop
Γöé   Γöé   ΓööΓöÇΓöÇ adjacent-surface-scan    # one-degree-out sibling scan when one missing item likely belongs to a local family
Γöé   Γö£ΓöÇΓöÇ validation                   # test design, verification protocol, behavior contracts
Γöé   Γöé   ΓööΓöÇΓöÇ uncertainty-quantification  # 3-tier UQ protocol (fast/standard/thorough); semantic entropy, SelfCheckGPT, conformal prediction, LM-Polygraph; abstain/escalate table
Γöé   Γö£ΓöÇΓöÇ architecture                 # system design, abstract-class planning, domain ΓåÆ code mapping
Γöé   Γö£ΓöÇΓöÇ tdd-agent                    # RedΓåÆGreenΓåÆRefactor as distinct agentic phases; test-first design contract
Γöé   Γöé   ΓööΓöÇΓöÇ program-synthesis        # LLM-assisted formal verification + proof-assisted coding; AutoVerus 3-phase loop; escalation from tdd-agent for unbounded/security properties
Γöé   Γö£ΓöÇΓöÇ autoresearch                 # autonomous iterative hill-climbing: scorer + proposer + git/sqlite checkpoint loop
Γöé   Γö£ΓöÇΓöÇ cua-desktop-agent            # autonomous desktop automation via VLM perception loop; vision-based retry for legacy/API-less applications
Γöé   ΓööΓöÇΓöÇ react-fastapi-sqlite         # full-stack scaffold: React (TanStack Query) + FastAPI (SQLModel ORM) + SQLite; SPA + REST backend
Γöé
Γö£ΓöÇΓöÇ orchestration/                   # route work, enforce policy, manage cross-session state
Γöé   Γö£ΓöÇΓöÇ meta-harness                 # requester-facing manager layer above agentic-harness; scopes objectives, forks/resumes sessions, delegates one issue at a time
Γöé   Γö£ΓöÇΓöÇ agentic-orchestration        # unified: 5-Q decision tree + live agent roster + Aider architect/editor reference impl + Anthropic pattern taxonomy
Γöé   Γö£ΓöÇΓöÇ agentic-design-patterns      # LangGraph workflow shape, router/gate topology, manager/BA/dev/QA rooms
Γöé   Γö£ΓöÇΓöÇ agentic-harness              # dark-task control plane; backbone = OpenClaw/Claude Code/OpenCode/Copilot CLI; structured-response contracts + HTP
Γöé   Γöé   Γö£ΓöÇΓöÇ checklist                # LLM-as-judge validation pattern; structured findings with novelty proof
Γöé   Γöé   Γö£ΓöÇΓöÇ continuity-log           # compact-safe session memory; distilled decisions, resume points
Γöé   Γöé   Γö£ΓöÇΓöÇ pipeline-input-review    # partition a pipeline problem to its minimal failing unit; materialise inputs before harness dispatch; hyper-focused task statements
Γöé   Γöé   ΓööΓöÇΓöÇ deep-research            # multi-source web evidence pipeline; LangGraph plannerΓåÆresearcherΓåÆsynthesizer
Γöé   Γö£ΓöÇΓöÇ openspec-workflow            # spec-driven change lifecycle with OpenSpec artifacts and Fabro handoff
Γöé   Γöé   Γö£ΓöÇΓöÇ openspec-propose         # create proposal/design/spec/tasks for a new change
Γöé   Γöé   Γö£ΓöÇΓöÇ openspec-explore         # think/discover mode around an OpenSpec change or idea
Γöé   Γöé   Γö£ΓöÇΓöÇ openspec-apply-change    # implement tasks from an OpenSpec change
Γöé   Γöé   ΓööΓöÇΓöÇ openspec-archive-change  # archive a completed OpenSpec change
Γöé   Γö£ΓöÇΓöÇ fabro-create-workflow        # author Fabro `.fabro` + `.toml` workflows from natural-language requirements
Γöé   Γö£ΓöÇΓöÇ substrate-selection          # runtime substrate policy: OpenCode / claw-code / pi / aider / provider boundary
Γöé   Γö£ΓöÇΓöÇ ollama-structured            # schema-constrained JSON from Ollama (native SDK + OpenAI compat); Qwen3 thinking suppression
Γöé   Γö£ΓöÇΓöÇ pi                           # lightweight delegated external harness; sits under opencode/agentic-harness and can host aider-like workers
Γöé   Γö£ΓöÇΓöÇ evaluator-optimizer          # LLM-generatesΓåÆLLM-critiquesΓåÆLLM-regenerates loop; MBR selection; stopping criteria
Γöé   Γöé   ΓööΓöÇΓöÇ prompt-optimization      # automatic prompt self-improvement; DSPy (MIPROv2), TextGrad (text-space gradients), OPRO, APE; labeled-trainset ΓåÆ MIPROv2 vs no-trainset ΓåÆ TextGrad decision tree
Γöé   Γö£ΓöÇΓöÇ multi-agent-coordination     # peer messaging, plan-approval gates, task ownership, dynamic spawning
Γöé   Γö£ΓöÇΓöÇ agent-governance             # safety rails, tool-access policy, audit trail, trust tiers, secrets scan
Γöé   Γö£ΓöÇΓöÇ security-review              # STRIDE-A, OWASP Top 10, data-flow tracing, secret/CVE detection
Γöé   Γö£ΓöÇΓöÇ build-observability          # run-centric observability contract: runs/events/commands, collectors, dashboards, trace enrichment
Γöé   Γö£ΓöÇΓöÇ timeout-guard                # runaway-task policy; interrupt and recovery rules
Γöé   Γö£ΓöÇΓöÇ git-workflow                 # branch strategy (testΓåÆdevΓåÆmain), push gates, LLM verification protocol with headless-browser checks
Γöé   Γö£ΓöÇΓöÇ validation-artifacts         # mandatory proof protocol: training loss curves, holdout metrics, test logs, visual diffs, API benchmarks, script outputs ΓÇö "seeing is believing"
Γöé   Γö£ΓöÇΓöÇ skill-wiki                   # living skill library lifecycle; intake ΓåÆ staged ΓåÆ active ΓåÆ superseded governance
Γöé   Γö£ΓöÇΓöÇ skill-sync                   # LLM-assisted merge for diverged skill copies across local/remote mirrors; cron-safe
Γöé   ΓööΓöÇΓöÇ consolidation                # triplet-based pairwise correlation + greedy chain decomposition ΓåÆ merge/xref/migrate prescriptions
Γöé
Γö£ΓöÇΓöÇ memory/                          # persist knowledge across sessions and tasks
Γöé   Γö£ΓöÇΓöÇ memory-bank                  # durable project memory (brief, context, patterns, progress)
Γöé   Γöé   # meta: DESCRIPTION/ARCHITECTURE/HISTORY pattern ΓÇö applies to any skill folder
Γöé   Γö£ΓöÇΓöÇ todo                         # sqlite-backed task tracking with FastMCP bridge
Γöé   Γö£ΓöÇΓöÇ cognitive-taxonomy           # unified memory classification: implicit/explicit/agentic paradigms; forms/functions/dynamics; System 1 vs 2 routing
Γöé   Γö£ΓöÇΓöÇ memory-architecture          # canonical 5-layer memory stack design: 4 templates (factual KB, personal assistant, autonomous agent, research); inter-layer routing; entity/procedure/query flows
Γöé   Γö£ΓöÇΓöÇ agentic_kg_memory            # MCG Context Graph side: semantic memory policy, retrieval, patterns, tribal knowledge, episodic memory
Γöé   Γöé   Γö£ΓöÇΓöÇ kg_ontology              # MCG DKG entity-identity layer: synset/hypernym BM25 canonicalization
Γöé   Γöé   ΓööΓöÇΓöÇ gist-retriever           # layered sparse+dense retrieval engine (BM25 + Chroma)
Γöé   Γö£ΓöÇΓöÇ crystallization              # distill completed work chains into digest pages + reusable lessons; hand off semantic outputs to agentic_kg_memory and procedural deltas to skill-wiki
Γöé   Γö£ΓöÇΓöÇ semantic-search-enrichment   # retrieval augmentation: query expansion, metadata boosting, semantic reranking
Γöé   Γö£ΓöÇΓöÇ context-compaction           # active context-window management: tiered eviction, pre/post-compaction hooks
Γöé   Γö£ΓöÇΓöÇ mcp-tool-registry            # MCP tool registration, discovery, routing, ACI design
Γöé   Γö£ΓöÇΓöÇ request-intent-resolution    # request-thread routing, retrieval evaluation
Γöé   ΓööΓöÇΓöÇ feature-catalog              # local SQLite feature inventory for implemented capabilities and file mappings
Γöé
Γö£ΓöÇΓöÇ tuning/                          # measure, optimize, record
Γöé   Γö£ΓöÇΓöÇ optuna-nested-cv             # search engine + methodology primer: inner tune / outer unbiased estimate
Γöé   Γö£ΓöÇΓöÇ hyper-parm_tuning            # superseded predecessor; canonical home for Weighted Stage Allocation pattern
Γöé   Γö£ΓöÇΓöÇ agentic-hyperparm            # behavioral knob tuning for agentic systems; instantiates Stage Allocation for L1-L4 layers
Γöé   Γö£ΓöÇΓöÇ parm-tuning-as-lp            # discrete hyperparameter tuning via linear/mixed-integer programming; orthogonal lever factorization, irreducible-ratio perturbation basis, global optimality
Γöé   Γö£ΓöÇΓöÇ class-balancing              # conditional stratification + token-equal weighting for multi-class reasoning transfer; inference pairing; temperature curriculum
Γöé   Γö£ΓöÇΓöÇ stratified-quota-sampling    # coverage-bounded no-replacement sampler; Box-Cox tiers + quota allocation
Γöé   Γöé   ΓööΓöÇΓöÇ synthetic-data           # LLM-generated training data; 8 paradigms (Self-Instruct/Evol-Instruct/GLAN/Magpie/UltraFeedback/FireAct/distilabel); 6 mandatory quality gates; handoff to stratified-quota-sampling + class-balancing
Γöé   Γö£ΓöÇΓöÇ cluster-quantized-knn        # O(1) approximate distance for KNN via cluster-quantization; fast interactive retrieval
Γöé   Γö£ΓöÇΓöÇ mad-dynamic-batching         # MAD-gated token-aware dynamic batching for variable-length training data; quantile partitioning
Γöé   Γö£ΓöÇΓöÇ median-bifurcation           # universal median-cut pattern: choose axis ΓåÆ produce both sides ΓåÆ drop unwanted half; 2^n epistemic cells at zero labeling cost; data-level contrastive learning
Γöé   Γö£ΓöÇΓöÇ mlflow                       # experiment ledger: params, metrics, artifacts, lineage
Γöé   Γö£ΓöÇΓöÇ model-size-reduction         # checkpoint slimming for HF models: dtype cast, layer drop, LoRA extraction, DARE/TIES/DELLA; architecture-agnostic state_dict path
Γöé   Γö£ΓöÇΓöÇ generalization-theory        # signal-vs-noise training-dynamics lens via eNTK; diagnose memorization, grokking, and noisy-preference fine-tunes
Γöé   Γö£ΓöÇΓöÇ representation-pipeline      # representation design: raw signal ΓåÆ embedding space
Γöé   Γö£ΓöÇΓöÇ bm25-corpus-sampling         # representative corpus sampling for BM25; log-normalΓåÆMADΓåÆYeo-JohnsonΓåÆCDF-diff quota; cascaded and proxy-Louvain rerankers
Γöé   ΓööΓöÇΓöÇ rag-eval                     # single-pass 10-metric RAG judge: qwen3.5:4b + Pydantic RAGEvalResult + macro_mean; one prompt per answer
Γöé
Γö£ΓöÇΓöÇ artifacts/                       # masterpiece outputs and information design
Γöé   Γö£ΓöÇΓöÇ documentation                # choose canonical doc vs changelog vs timestamped fixes-applied artifact
Γöé   Γö£ΓöÇΓöÇ response-style               # voice preservation, anti-cliche prose, user-facing coherence
Γöé   Γö£ΓöÇΓöÇ business-writing             # professional document writing: resume, cover letter, portfolio; triplet bullets, spice gradient
Γöé   Γö£ΓöÇΓöÇ gist_correlation_matrix      # sorted correlation matrix as complete relational map; two sorting approaches (orthogonal vs coverage)
Γöé   Γö£ΓöÇΓöÇ nearest-neighbor-chain       # greedy path-cover decomposition of a similarity matrix into variable-length semantic chains; ╧ä selection; chaining = semantic thread
Γöé   ΓööΓöÇΓöÇ spiral-radial-clustering-display  # multi-dimensional spiral visualization; GMM+HDBSCAN+orderingΓåÆUMAP 2D with Gestalt encoding
Γöé
Γö£ΓöÇΓöÇ learning/                        # reinforcement learning and policy optimization
Γöé   Γö£ΓöÇΓöÇ deep-q-rl                    # DQN + Russian Doll MCTS for any scored discrete-action framework; code-rl extension; SPO/DPO offline preference optimization
Γöé   Γö£ΓöÇΓöÇ active-inference             # Bayesian POMDP agents via Free Energy Principle; EFE-driven tool selection; pymdp; use when no reward function + partial observability
Γöé   Γö£ΓöÇΓöÇ continual-learning           # non-forgetting agents; EWC, GEM/A-GEM, PackNet, O-LoRA/InfLoRA, DARE, LwF, MemRL; absorbs integrate/MemRL
Γöé   ΓööΓöÇΓöÇ siamese_from_correlation_matrix  # derive metric-learning pairs directly from embedding/correlation structure
Γöé
ΓööΓöÇΓöÇ pipelines/                       # end-to-end domain workflows (invoke sub-skills as needed)
    Γö£ΓöÇΓöÇ auto-ingest                  # on-demand and background PDF enrichment for arxiv_rag corpus; VLM methods extraction
    ΓööΓöÇΓöÇ pdf-extraction               # doclingΓåÆbase64 stripΓåÆVLMΓåÆreinsertΓåÆmethods; table enhancement with tabula+camelot+VLM fusion; classifier training via class-balancing
```

## Key Relationships

1. `react-agent` is the outer execution OS. All other skills are invoked from inside it.
2. `design-patterns` is the code-facing pattern selector. `code` owns edit mechanics; `design-patterns` chooses the relationship shape and contract.
3. `agentic-design-patterns` chooses LangGraph workflow shape and role topology. It is where routing, prompt chaining, parallel sectioning, voting, orchestrator-workers, evaluator-optimizer, and bounded autonomous loops belong.
4. `meta-harness` is the manager layer one step above `agentic-harness`: it owns objective framing, scoped session decomposition, and parent/child coordination so request-level planning stays separate from issue-level harness execution.
5. `substrate-selection` decides which runtime sits behind the graph or harness boundary: OpenCode, claw-code, `pi`, aider, or another provider surface. Default integrated stack: `opencode` for the orchestrator lane, optional `pi` for a delegated external-harness lane, and `aider` for the leaf-agent lane. It also owns the rule that model/provider parity does not imply harness/runtime parity ΓÇö first-party surfaces like GitHub Copilot CLI may bundle stronger runtime guarantees that provider-routed OpenRouter stacks must recreate explicitly in skills/config.
6. `agentic-harness` is the programmatic train station for coding frameworks (Claude Code, OpenCode, GitHub Copilot CLI, OpenClaw). It routes, gates, and reconciles work; each framework is a worker line, and the resolved runtime stack should be visible in state/logs rather than hidden in helper code.
7. `continuity-log` is a child of `agentic-harness`. It holds the compact-safe distilled state that lets the harness resume without re-deriving decisions.
8. `deep-research` is a child of `agentic-harness`. It decomposes a question into parallel subquestions, gathers web evidence via a 3-tier fetch pipeline (httpx ΓåÆ retry ΓåÆ Selenium), and synthesizes a claim-backed report seeding the harness TaskSpec.
9. `optuna-nested-cv` is now self-contained: the Methodology Primer (what to optimize, preconditions, layerwise decomp, structured search, sampler policy) was absorbed from `hyper-parm_tuning` (now superseded). `mlflow` records every run with lineage.
10. `agentic_kg_memory` is the **CG (Context Graph) side** of the MCG architecture: semantic memory policy, patterns, tribal knowledge, retrieval. `kg_ontology` is the **DKG entity-identity layer**: synset/hypernym BM25 canonicalization that prevents duplicate nodes without graph topology traversal. They are complementary layers, not alternatives ΓÇö do not merge them again.
11. `gist-retriever` is the retrieval sub-skill for that memory layer. It spans the access-path progression from markdown/index-first lookup through local markdown search and into the full hybrid BM25+dense pipeline.
12. `memory-bank` remains project operating memory, not compiled corpus memory. It stores project continuity while `agentic_kg_memory` stores evolving domain knowledge.
13. The supplementary comparison boundary is now explicit in the repo: **RAG/retriever** behavior belongs in `gist-retriever`, **LLM Wiki/compiler** behavior belongs in `agentic_kg_memory`, and **GBrain/operator / fat-skills orchestration** belongs on the execution/orchestration side, not in the memory branch.
14. KnowledgeWeaver is treated as a concrete implementation example of the compiler side: typed readable knowledge units plus a compiled index that can be rebuilt from canonical markdown artifacts.
15. `agentic-harness` (waterfall -> agile: topics -> plans -> specs -> tasks) is the lifecycle template for skill authoring, not just software projects.
16. `deep-q-rl` is the generalized RL framework for any scored discrete-action environment. Combines value-head Q-network, experience replay, target network, Russian Doll MCTS, AHA online mistake correction, and training-progress annealing. Includes Code-RL (RL from test-execution feedback) and SPO/offline preference optimization (reward-weighted SFT, DPO) with reward design rules, generation parameter pitfalls, and epoch validation protocol. Derived from `thistleknot/chess-deep-q`.
17. `checklist` is a subskill of `agentic-harness`. It is the Pydantic-schema LLM-as-judge pattern: structured findings with novelty proofs, non-fatal execution, `review_required` flag, and cross-run fingerprinting via throughline Q-scores. Reference implementation: `gap_critic.py` in storywriter.
18. `gist_correlation_matrix` is the "true GIST output": sorted correlation matrix as complete relational map (N^2 cells, each encoding pairwise relationship). Two sorting strategies: **orthogonal** (information-theoretic maximization, sharp drop-off) and **coverage** (hierarchical boundary exploration, expanding bands). Outputs: interactive HTMLs with full zoom/pan/hover.
19. `spiral-radial-clustering-display` is the multi-dimensional hierarchical clustering visualization skill. Maps four layers (macro GMM + micro HDBSCAN + decorrelated ordering + hubness) into 3D feature space, projects via UMAP to 2D, encodes layers via Gestalt (position = spiral topology, color = macro, opacity = micro, size = centrality). Preserves topological structure and produces interactive Plotly HTML with full zoom/pan/hover metadata.
20. `feature-catalog` is the local implementation ledger: a SQLite feature catalog for tracking what the project already ships and where it lives.
21. `siamese_from_correlation_matrix` is the metric-learning companion to the embedding-analysis branch: it turns correlation structure into contrastive supervision.
22. `skill-wiki` is the meta-skill governing the living skill library lifecycle. It owns the intake pipeline, promotion gates, supersession rules, sidecar conventions (EVIDENCE.md, HISTORY.md, scripts/ examples), and the periodic sweep that keeps skills consistent over time. It routes verified work chains into `crystallization` when the output is a digest, and handles staged skill-contract updates when the output is a library change. It is NOT memory storage (ΓåÆ `agentic_kg_memory`) and NOT project state (ΓåÆ `memory-bank`).
23. `documentation` decides which durable doc artifact to update: canonical README/spec, cumulative changelog, or a timestamped fixes-applied note.
24. `response-style` governs user-facing prose: voice preservation, anti-cliche writing, and answer coherence. Harness-state coherence remains with `agentic-harness`.
25. `class-balancing` is a general-purpose class weight protocol. It computes log inverse frequency per class, applies Box-Cox normalization to tame the distribution tail, clips negatives, and normalizes to ratios for use as `class_weight` in sklearn or `weight` in PyTorch CrossEntropyLoss. Used anywhere labeled data has heavy class imbalance ΓÇö layout element classification, NER, retrieval judgment labeling.
25. `stratified-quota-sampling` owns fixed-budget coverage schedulers: Box-Cox tiering, quota allocation, and no-replacement sampling from an imbalanced pool. Pair it with `class-balancing` when quota selection alone still leaves residual label skew inside the loss, and with `optuna-nested-cv` when sample fraction, quota ratios, or tier weighting are part of the tuning contract.
26. `pdf-extraction` is the end-to-end PDFΓåÆenriched-Markdown pipeline workflow: doclingΓåÆbase64 stripΓåÆVLM image descriptionΓåÆreinsertΓåÆmethods extraction (5 phases via `run_pipeline.bat`). Includes a table enhancement sub-pipeline: docling JSON bboxesΓåÆpymupdf cropΓåÆtabula+camelot extractionΓåÆVLM fusionΓåÆpatched Markdown. The layout classifier uses `class-balancing` for training. Standalone workflow skill; not a child of `agentic-harness`.
27. `openspec-workflow` is the spec-driven product/change lifecycle skill. Its companion action skills (`openspec-propose`, `openspec-explore`, `openspec-apply-change`, `openspec-archive-change`) are command-shaped entry points into the same OpenSpec operating model.
28. `fabro-create-workflow` is the Fabro graph/run-config authoring companion. It can support `openspec-workflow` when a repo needs a new Fabro pipeline, but it is also usable as a standalone workflow-design skill.
29. `agentic-harness` now has an explicit evaluation mix: `checklist` for structured audit artifacts, DSPy-derived metric/reward compile-refine patterns when scoring is explicit, and TextGrad-derived textual-loss loops when the critic must explain how to improve text/code/prompts. Optimizer scores inform repair; artifact-backed verification still decides completion.
30. `codebase-knowledge-graph` is the current-repository relationship-mapping protocol. It builds the typed module/file/class/function graph and the foundational-vs-incidental distinction that should exist before `code`, `debugging`, or `validation` edits proceed.
31. `code-extraction` extracts source files + configs from any project into a unified markdown artifact (docling-style: parse ΓåÆ normalize ΓåÆ markdown + JSON metadata). Supports multi-language detection (Python, Go, Rust, Swift, Java, JS/TS via markers or 8+ source files). Output feeds `codebase-knowledge-graph`, `documentation`, and LLM context assembly.
32. `diagnostic-scanner` invokes language-appropriate tools (mypy/pylint, go vet, cargo check, swiftc, eslint, etc.) and normalizes errors/warnings by severity and category. Produces fix prompts ready for LLM remediation. Output feeds `validation` and `code` for structured violation handling.
33. `model-size-reduction` owns post-training checkpoint reduction: dtype casting, layer dropping, LoRA extraction, and DARE/TIES/DELLA sparsification directly against Hugging Face `state_dict`s. `continual-learning` still owns DARE as a lifelong-learning merge pattern; use `model-size-reduction` when the goal is footprint, portability, or architecture-agnostic checkpoint surgery.
34. `generalization-theory` is the training-dynamics diagnostic lens for signal-vs-noise partitioning, grokking delay, and noisy-preference memorization. It helps choose intervention surfaces across data, architecture, and optimizer design, but it does not own the tuning/search loop (`optuna-nested-cv`) or long-horizon forgetting control (`continual-learning`).
35. `test-planner` generates coverage-aware test plans with status flags (≡ƒƒó GREEN=DONE, ≡ƒƒí YELLOW=PARTIAL, ≡ƒö┤ RED=MISSING). Proposes concrete scenarios by test level (smoke/unit/integration/e2e/regression) and detects regression subjects via git diff. Output feeds `tdd-agent` for test-driven implementation and `validation` for coverage verification.
36. `doc-synthesizer` parses project structure via AST (Python focus; all languages via markers), builds dependency graphs, and generates Mermaid diagrams for module dependencies and data flow. Output feeds `documentation`, `codebase-knowledge-graph`, and architecture review. URI fetch/crawl extensible for Phase 2.
37. `build-observability` is the run-centric observability layer for agentic execution. `agentic-harness` owns control flow and retries; `build-observability` projects runtime exhaust into normalized `runs/events/commands` records and operator-facing dashboard views.
38. `react-fastapi-sqlite` is the full-stack application scaffold skill: React frontend (with TanStack Query for server-state caching), FastAPI backend (with SQLModel ORM layer), and SQLite file-based database. Use when building SPAs with Python REST backends, configuring client-side data fetching and invalidation patterns, or structuring domain-driven CRUD operations. Output: production-ready project layout with separation of concerns (api/ ΓåÆ hooks/ ΓåÆ pages/components/ hierarchy). Integrates with `code` for implementation standards and `validation` for integration testing.
39. `git-workflow` is the branch strategy and LLM safety protocol for this repository. Enforces testΓåÆdevΓåÆmain push gates, requires LLM verification against last known working commit before each push, and pairs `code` verification (git diff checks) with `headless-browser-verification` screenshots for web frontend changes. Prevents accidental pushes to main by requiring explicit user approval at each stage.

40. `cognitive-taxonomy` is the **reference skill for all memory decisions**. It synthesizes four peer-reviewed papers into a unified classification system: implicit/explicit/agentic paradigms, forms/functions/dynamics taxonomy, biological-artificial crosswalk, and neuro-symbolic System 1 vs System 2 dual-process reasoning. Use it to classify memory patterns, route queries correctly, diagnose underperformance (why is vector-only failing?), and design new memory architectures. It's a pure reference skill (no code changes) that sits above all memory subsystems (`agentic_kg_memory`, `procedural-memory`, `continuity-log`, `context-compaction`).

41. `memory-architecture` is the **canonical design reference for agent memory systems**. Implements the Meta Context Graph layered stack with 4 concrete templates: (1) factual knowledge base (ImplicitΓåÆExplicitΓåÆWorking), (2) personal assistant with memory (adds Episodic), (3) autonomous agent (adds Procedural), (4) research/knowledge synthesis pipeline. Each template includes full 5-layer architecture, entity anchor flow, procedure discovery flow, query routing lifecycle, and anti-patterns. Use when designing a new agent with memory, evaluating existing systems for gaps, onboarding developers. Depends on `cognitive-taxonomy` for classification; feeds into `procedural-memory`, `agentic_kg_memory`, `context-compaction` for implementation.

42. `validation-artifacts` enforces the principle **"seeing is believing"** by making validation proof mandatory, not optional. Before any skill claims "validation passed", this skill demands reproducible artifacts: training loss curves + eval metrics on holdout sets, predictions + confusion matrices, test execution logs with exit codes, before/after screenshots + visual diffs, API request/response samples + latency profiles, script execution examples with outputs. Used by `validation`, `checklist`, `tdd-agent`, `debugging`, `git-workflow` to prevent "trust me" claims. Integrates with `headless-browser-verification` (UI artifacts) and `security-review` (security validation artifacts).

43. `skill-sync` is the **LLM-assisted merge protocol for diverged skill copies** across master and local/remote mirrors. Distinct from `skill-wiki` (governance: intake/staging/lifecycle) ΓÇö `skill-sync` is operational: when both master and a mirror have independently changed since the last commit, it classifies the case (no-op / fast-forward / conflict), applies deterministic fast-forwards automatically, and routes true conflicts to an LLM merge that incorporates both sets of changes without dropping content from either side. Mechanically executed by `sync_skills.ps1`. MERGE-CONFLICT markers flag unresolved sections for human review before commit.

44. `consolidation` is the **triplet-based document consolidation pipeline** for living knowledge bases and skill libraries. Extracts subject-predicate-object triplets from each document, computes a pairwise Jaccard similarity matrix (or NLI-based soft Jaccard for semantic matching), runs **greedy nearest-neighbor chain decomposition** (single-linkage chaining) to group related documents, and emits a sorted report with prescriptions: MERGE (ΓëÑ0.8), migrate (0.5ΓÇô0.8), xref (0.3ΓÇô0.5). Groups are sorted by chain length descending ΓÇö largest clusters first. Sits above `gist_correlation_matrix` (matrix builder) and feeds prescriptions into `skill-wiki` (governance) and `skill-sync` (mechanical merge). Use when the library has grown by ΓëÑ5 new entries, semantic search returns contradictory results, or a scheduled consolidation run is due.

45. `nearest-neighbor-chain` is the **greedy path-cover chain decomposition sub-skill** shared by `consolidation` and any other consumer that needs to partition a similarity matrix into semantic groups. It walks pairs sorted by descending score, extends only chain endpoints (no branching), and emits variable-length chains sorted by length descending. Singletons are docs with no above-╧ä neighbours. The "chaining effect" of single-linkage is intentional: each chain is a semantic thread; a chain break is a topic boundary. `gist_correlation_matrix` produces the matrix; `nearest-neighbor-chain` decomposes it; `consolidation` adds triplet extraction and MERGE/migrate/xref prescriptions on top.

46. `prompt-optimization` is the **automatic prompt self-improvement skill**. A child of `evaluator-optimizer` that applies optimization algorithms ΓÇö not manual rewriting. Labeled trainset + multi-step ΓåÆ DSPy MIPROv2 (Bayesian joint instruction+demo search). No trainset + differentiable loss ΓåÆ TextGrad (text-space gradient descent). Demos only ΓåÆ APE. Single instruction ΓåÆ OPRO. `agentic-harness` invokes this when a module's loss metric is stable but prompt quality is the bottleneck. Absorbs `integrate/dspy.md` and `integrate/textgrad.md`.

47. `uncertainty-quantification` is the **LLM output confidence protocol**. A child of `validation` for measuring when a model knows vs. doesn't know. Three-tier protocol: Tier 1 = fast (logprobs/verbal, <0.1s), Tier 2 = standard (N=3ΓÇô5 consistency samples), Tier 3 = thorough (NΓëÑ10 + conformal prediction). Semantic entropy (arXiv:2302.09664) outperforms token-level entropy. Always use Tier 3 minimum for irreversible actions. Libraries: `selfcheckgpt`, `lm-polygraph`. Feeds `checklist` for audit trails and `uncertainty-quantification` threshold gates in `agent-governance`.

48. `causal-inference` is the **LLMΓåÆDoWhyΓåÆLLM causal reasoning chain**. A child of `reasoning`. LLMs hallucinate on formal do-calculus (near-random; arXiv:2306.05836) ΓÇö all estimation routes through DoWhy, not the LLM. Three-phase protocol: LLM proposes DAG ΓåÆ causal-learn validates (PC/FCI/GES) ΓåÆ DoWhy identifies+estimates. LLM only interprets results. Counterfactual queries use `dowhy.counterfactual_outcomes`. Libraries: `dowhy`, `causal-learn`, `econml`, `pywhy-llm` (experimental).

49. `synthetic-data` is the **LLM-generated training data pipeline**. A child of `stratified-quota-sampling`. Eight paradigms ordered by fidelity: Self-Instruct ΓåÆ Evol-Instruct ΓåÆ GLAN ΓåÆ Magpie ΓåÆ Self-Play ΓåÆ Persona-driven ΓåÆ Task-specific ΓåÆ Preference. Six mandatory quality gates in order: dedup ΓåÆ schema ΓåÆ LLM judge ΓåÆ IFD ΓåÆ coverage ΓåÆ safety. Model collapse risk (arXiv:2305.17493): requires a strong fixed teacher (GPT-4/Llama-3-70B), never train-on-own-outputs without mixing real data. Clean three-stage handoff: `synthetic-data` ΓåÆ `stratified-quota-sampling` ΓåÆ `class-balancing`. Library: `argilla-io/distilabel`.

50. `continual-learning` is the **non-forgetting agent training protocol**. Sits in `learning/` alongside `deep-q-rl`. Prevents catastrophic forgetting when a model must learn a new task without erasing prior skills. Six approaches by compute budget: EWC (regularization, cheapest) ΓåÆ LwF (distillation) ΓåÆ GEM/A-GEM (episodic memory constraint) ΓåÆ PackNet (parameter isolation) ΓåÆ O-LoRA/InfLoRA (LoRA orthogonalization) ΓåÆ MemRL (frozen backbone + episodic Q-value memory, ICML 2026). `procedural-memory` EMA (╬▓=0.9) is intentionally aligned with single-sample EWC. Absorbs `integrate/MemRL` (arXiv:2601.03192). Libraries: Avalanche, Mammoth, HuggingFace PEFT.

51. `program-synthesis` is the **formal verification + proof-assisted coding skill**. A child of `tdd-agent` ΓÇö `tdd-agent` escalates here when the property is unbounded, security-critical, or requires exhaustive correctness guarantees. AutoVerus (arXiv:2409.13082): 91.3% on 150 Verus tasks using GPT-4o + Rust ghost code, ~$37 total. EvalPlus (arXiv:2305.01210): pass@k drops 19ΓÇô28% with exhaustive testing vs. HumanEval ΓÇö all `tdd-agent` benchmarks should use EvalPlus. Three-phase loop: generate ΓåÆ verify (formal checker) ΓåÆ repair (RLEF feedback). Integration: `tdd-agent` handles empirical tests; `program-synthesis` handles formal properties.

52. `active-inference` is the **Bayesian POMDP agent skill** based on the Free Energy Principle. Sits in `learning/` as a complement to `deep-q-rl`, not a replacement. Use when: partial observability (can't see full state), no clean scalar reward (prefer EFE preferences), principled tool selection (epistemic value drives info-gathering before committing to action). EFE decomposes into epistemic value (info gain) + pragmatic value (reach preferred obs) ΓÇö no reward design needed. Russian Doll MCTS Γëê Sophisticated Inference: both use tree search; EFE replaces Q-value as node score. Library: `inferactively-pymdp`. Use `deep-q-rl` when full observability + `evaluate(state)` exists.

53. `median-bifurcation` is the **universal median-cut discriminative signal skill**. Any useful distinction a model or system must learn is a binary median cut. Three-step protocol: choose partition axis ΓåÆ produce both sides explicitly (hard negatives baked in, not mined post-hoc) ΓåÆ drop unwanted partition at inference. Applied recursively, n bifurcations yield 2^n epistemic cells at zero additional labeling cost. This is data-level contrastive learning: the loss sees ordinary cross-entropy; discriminative pressure comes from the data layout. Inspired by ANOVA factorial designs and k-means via median divisions. `mad-dynamic-batching` is a concrete instantiation for token-length distributions.

## MCG Foundation ΓÇö The Conceptual Backbone

The skill library is an implementation of the **Meta Context Graph (MCG)** architecture
(Tekiner, 2025; Hu et al. arXiv:2512.13564) applied to automated software development.
MCG is the glue that ties gstack (fat operational patterns) to llm-wiki (compiled living
knowledge): both are instantiated here as the skills themselves (procedural memory) and
the Pattern Store vetting pipeline (tribal knowledge lifecycle).

The full MCG system comprises two complementary graphs:

| MCG Component | Software Dev Equivalent | Skill |
|---|---|---|
| Domain KG ΓÇö entities & relationships | Codebase / domain model | `agentic_kg_memory` + `kg_ontology` |
| DKG entity identity layer | Symbol/module canonicalization | `kg_ontology` |
| Context Graph ΓÇö decision traces (episodic) | learnings.jsonl, per-task rationale | `agentic-harness` |
| CG patterns (semantic) | Pattern Store pending ΓåÆ tenure | `skill-wiki` |
| CG tribal knowledge (semantic) | Pattern Store promoted entries | `skill-wiki` ΓåÆ skill files |
| CG procedural schemas | **The SKILL.md files themselves** ΓÇö model-agnostic, slot-in primitives | This whole library |
| L4 Runtime state | Session / active context | `continuity-log`, `memory-bank` |
| L3 Organisation conventions | Team / project norms | `memory-bank` project brief |
| L2 Industry / domain | Domain KG per project | `agentic_kg_memory` |
| L1 Universal best practices | Base skill library | This repo |

**The skills are procedural memory** (CoALA taxonomy, arXiv:2309.02427). They cannot be
summarized into a prompt and RAG-retrieved with equal effect ΓÇö they must be invoked. This
is the distinction between a great chef's accumulated technique and a recipe book. The
Pattern Store vetting pipeline (3 applications ΓåÆ promote) implements the tribal knowledge
lifecycle from MCG: `tk_candidates` ΓåÆ reviewed ΓåÆ `tribal_knowledge` (active rule) ΓåÆ
compiled into a skill.

For the full architecture, see `agentic_kg_memory/SKILL.md ┬º MCG Foundation`.

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
| `build-observability` | **live skill** ΓåÆ `build-observability` |
| `codebase-knowledge-graph` | **live skill** ΓåÆ `codebase-knowledge-graph` |
| `fat-skills` | **closed by absorption** ΓåÆ `skill-wiki` + `agentic-harness` + repo routing guidance + memory / governance split |
| `dev-pipeline` | **closed by absorption** ΓåÆ `react-agent` + `openspec-workflow` + execution skills + `agentic-harness` + supporting release / safety lanes |

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
integrate/          ΓåÉ raw intake (awesome-copilot, gstack, llm-wiki, etc.)
integrate/staged/   ΓåÉ validated concepts awaiting promotion
<skill>/SKILL.md    ΓåÉ active behavioral contract (status: active)
<superseded>        ΓåÉ retired skills (status: superseded, superseded_by: <name>)
```

Promotion gate: one Tier-1/2 evidence item + one local validation, OR two independent Tier-1ΓÇô3 items from distinct source types. See `skill-wiki/SKILL.md` for the full governance contract.

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
| PDFΓåÆenriched-Markdown pipeline | `pdf-extraction` |
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
- **2026-05-02**: Added `class-balancing` (log inverse freq ΓåÆ Box-Cox ΓåÆ ratio weights for imbalanced classifiers) and `pdf-extraction` (full docling pipeline + table enhancement via tabula+camelot+VLM fusion). `hyper-parm_tuning` now frames Weighted Stage Allocation as the canonical cross-skill pattern; `agentic-hyperparm` is the agent-specific instantiation. `arxiv-bridge` was updated with CLI flags and a sequential-only warning.
- Imported the portable OpenSpec/Fabro skill family as live agent skills: `openspec-workflow`, `openspec-propose`, `openspec-explore`, `openspec-apply-change`, `openspec-archive-change`, and `fabro-create-workflow`. Current rollout is agent-only first; any dark-factory pipeline promotion remains a separate second pass.
- **Wave 3 Pareto additions** (Tier 3, scores 6ΓÇô9): `autoresearch` (new skill); `context-engineering` section ΓåÆ `code`; `eval-pipeline` section ΓåÆ `checklist`; `agent-as-ci-gate` full protocol ΓåÆ `agent-governance`; `code-rl` section ΓåÆ `deep-q-rl`. All 15 Pareto candidates now implemented.
- **Super System Prompt extraction finished**: added `documentation` (timestamped-vs-cumulative doc strategy) and `response-style` (voice preservation, anti-cliche prose, user-facing coherence).
- **Wave 2 Pareto additions** (Tier 2, scores 12ΓÇô16): `context-compaction`, `security-review`, `mcp-tool-registry` (new skills); `self-repair` section ΓåÆ `debugging`; `hierarchical-task-planning` section ΓåÆ `agentic-harness`; `episodic-memory` section ΓåÆ `agentic_kg_memory`.
- **Wave 1 Pareto additions** (Tier 1, all score ΓëÑ 20): `evaluator-optimizer`, `multi-agent-coordination`, `tdd-agent`, `agent-governance`. Fills the largest gaps: iterative generation loop, team topology, test-first lifecycle, and safety rails.
- **MCG grounding pass**: Grounded the full skill library in the Meta Context Graph (MCG) architecture (Tekiner 2025, Hu et al. arXiv:2512.13564, CoALA arXiv:2309.02427, ACE arXiv:2510.04618). Added MCG Foundation section to README, MCG Architecture section to `agentic_kg_memory/SKILL.md`, and MCG terminology alignment to `skill-wiki` Pattern Store.
- **Restored `kg_ontology` to `status: active`**: The prior merge into `agentic_kg_memory` was architecturally wrong. `kg_ontology` owns the DKG entity-identity layer (synset/hypernym BM25 canonicalization); `agentic_kg_memory` owns the CG retrieval side. Two distinct MCG concerns.
- Added `deep-research` as a child of `agentic-harness`: LangGraph research graph with Selenium fallback fetch pipeline.
- Reframed `agentic-harness` as the multi-framework stationmaster.
- Added `continuity-log` to preserve compact-safe reasoning products between long turns and compactions.
- Absorbed `integrate\\llm-wiki` into existing live skills instead of promoting it as a standalone branch: compiled memory behavior now lives in `agentic_kg_memory`, staged retrieval behavior in `gist-retriever`, and the project-vs-corpus boundary in `memory-bank`.
- Second-pass absorption of `integrate\\llm-wiki`: added consolidation tiers (working/episodic/semantic/procedural), temporal decay, supersession, automation hooks, graph traversal for discovery, and an initial crystallization contract to `agentic_kg_memory`. That protocol has since been promoted into the standalone `crystallization` skill.
- Added `deep-q-rl` under new `learning/` section: DQN + Russian Doll MCTS pattern generalized from chess-deep-q; applies to any scored discrete-action environment.
- Merged `hyper-parm_tuning` ΓåÆ `optuna-nested-cv`: Methodology Primer section (preconditions checklist, layerwise decomposition, structured search protocol, sampler policy for LLM judges, search space type guide). `hyper-parm_tuning` is now `status: superseded`.
- Fattened `agentic-harness` with gstack-derived patterns: Learnings Compounding (learnings.jsonl schema, 4 persistence layers), Automated Dev Pipeline (Autoship state machine), Review Army (7 specialists + adaptive ceremony), Context Compaction During Long Runs.
- Fattened `deep-research` with research epistemology: Perspective Diversity (STORM), Source Quality Hierarchy (5-tier), Per-Role Model Strategy, Citation Chain Integrity, Research Anti-Patterns.
- Added Pattern Store vetting mechanism to `skill-wiki/SKILL.md`: vector store as pre-skill staging, 3-application tenure threshold, confidence decay formula (`e^(-0.1 ├ù months)`), prune gate, promotion pipeline ΓåÆ `integrate/staged/`.
- All live and retained-historical `SKILL.md` files now carry `status:` governance frontmatter. `hyper-parm_tuning` remains the preserved superseded predecessor.
- Added `design-patterns`, `agentic-design-patterns`, and `substrate-selection` as distinct skills so code pattern choice, LangGraph workflow shape, and runtime selection no longer collapse into `agentic-harness`.
- Absorbed `integrate/gstack` ETHOS: "Boil the Lake" (completeness is cheap with AI) into `code/SKILL.md`; "Search Before Building" (3-layer knowledge taxonomy) into `code/SKILL.md`.
- Absorbed `integrate/gstack/investigate` Iron Law (no fix without root cause) and 5-phase debugging protocol into `debugging/SKILL.md`.
- Added Skill Routing section to `copilot-instructions.md` mapping request types to skills (pattern from gstack CLAUDE.md).
- Added `## Applicability Envelope` to `agentic-harness/SKILL.md` and `debugging/SKILL.md` as template for all live skills.
- Living Skill Library infrastructure: `integrate/README.md`, `integrate/staged/README.md`, `agentic-harness/EVIDENCE.md`, `agentic-harness/HISTORY.md`.
- Added "Living Skill Library" lifecycle documentation and "Automated Software Development Pipeline" mapping to `README.md`.
  -- Changes from Side A (master) -----------------------------------
diff --git "a/C:\\Users\\user\\AppData\\Local\\Temp\\tmpE7EE.tmp" "b/C:\\Users\\user\\AppData\\Local\\Temp\\tmpE7EF.tmp"
index 3588a39..78228e5 100644
--- "a/C:\\Users\\user\\AppData\\Local\\Temp\\tmpE7EE.tmp"
+++ "b/C:\\Users\\user\\AppData\\Local\\Temp\\tmpE7EF.tmp"
@@ -8,133 +8,135 @@ old `.copilot` module scaffold; it is a composable skill graph.
 Use this README as the canonical folder map before adding, moving, or wiring a
 skill. The AST below should match the live folders in this repository.

 ## Skill Graph (AST View)

-Each node is a skill. Indentation encodes parent ╬ô├Ñ├å child dependency. Peers share the same indent level.
+Each node is a skill. Indentation encodes parent ├óΓÇáΓÇÖ child dependency. Peers share the same indent level.

 ```
 skills/
-╬ô├╢┬ú╬ô├╢├ç╬ô├╢├ç execution/                       # plan, implement, verify
-╬ô├╢├⌐   ╬ô├╢┬ú╬ô├╢├ç╬ô├╢├ç react-agent                  # outer execution OS; drives all other skills
-╬ô├╢├⌐   ╬ô├╢┬ú╬ô├╢├ç╬ô├╢├ç reasoning                    # open-ended problem decomposition + multi-perspective analysis
-╬ô├╢├⌐   ╬ô├╢├⌐   ╬ô├╢├╢╬ô├╢├ç╬ô├╢├ç causal-inference         # LLM╬ô├Ñ├åDoWhy╬ô├Ñ├åLLM architecture; Pearl's ladder (association/intervention/counterfactual); causal discovery, do-calculus, SCM via DoWhy + causal-learn
-╬ô├╢├⌐   ╬ô├╢┬ú╬ô├╢├ç╬ô├╢├ç codebase-knowledge-graph     # current-repo whole-system map; foundational vs incidental code; ripple analysis before edits
-╬ô├╢├⌐   ╬ô├╢┬ú╬ô├╢├ç╬ô├╢├ç code                         # implementation standards, naming, refactor sequence
-╬ô├╢├⌐   ╬ô├╢├⌐   ╬ô├╢├╢╬ô├╢├ç╬ô├╢├ç design-patterns          # GoF / contract / relationship-shape companion to code
-╬ô├╢├⌐   ╬ô├╢┬ú╬ô├╢├ç╬ô├╢├ç code-extraction              # extract source files + configs into copy-paste-ready markdown artifact (docling-style)
-╬ô├╢├⌐   ╬ô├╢┬ú╬ô├╢├ç╬ô├╢├ç diagnostic-scanner           # language-aware compiler/linter scanning; errors/warnings grouped by severity
-╬ô├╢├⌐   ╬ô├╢┬ú╬ô├╢├ç╬ô├╢├ç schema-induction             # cross-instance schema discovery via pairwise contrast (Aristotelian diairesis); constants vs variable dims; CRISP-DM data understanding analog
-╬ô├╢├⌐   ╬ô├╢┬ú╬ô├╢├ç╬ô├╢├ç test-planner                 # coverage-aware test plan generation (green/yellow/red status); regression detection
-╬ô├╢├⌐   ╬ô├╢┬ú╬ô├╢├ç╬ô├╢├ç doc-synthesizer              # AST-based documentation with Mermaid dependency/data-flow diagrams
-╬ô├╢├⌐   ╬ô├╢┬ú╬ô├╢├ç╬ô├╢├ç debugging                    # error isolation, salience tiers, diagnostic strategy, self-repair loop
-╬ô├╢├⌐   ╬ô├╢├⌐   ╬ô├╢├╢╬ô├╢├ç╬ô├╢├ç adjacent-surface-scan    # one-degree-out sibling scan when one missing item likely belongs to a local family
-╬ô├╢├⌐   ╬ô├╢┬ú╬ô├╢├ç╬ô├╢├ç validation                   # test design, verification protocol, behavior contracts
-╬ô├╢├⌐   ╬ô├╢├⌐   ╬ô├╢├╢╬ô├╢├ç╬ô├╢├ç uncertainty-quantification  # 3-tier UQ protocol (fast/standard/thorough); semantic entropy, SelfCheckGPT, conformal prediction, LM-Polygraph; abstain/escalate table
-╬ô├╢├⌐   ╬ô├╢┬ú╬ô├╢├ç╬ô├╢├ç architecture                 # system design, abstract-class planning, domain ╬ô├Ñ├å code mapping
-╬ô├╢├⌐   ╬ô├╢┬ú╬ô├╢├ç╬ô├╢├ç tdd-agent                    # Red╬ô├Ñ├åGreen╬ô├Ñ├åRefactor as distinct agentic phases; test-first design contract
-╬ô├╢├⌐   ╬ô├╢├⌐   ╬ô├╢├╢╬ô├╢├ç╬ô├╢├ç program-synthesis        # LLM-assisted formal verification + proof-assisted coding; AutoVerus 3-phase loop; escalation from tdd-agent for unbounded/security properties
-╬ô├╢├⌐   ╬ô├╢┬ú╬ô├╢├ç╬ô├╢├ç autoresearch                 # autonomous iterative hill-climbing: scorer + proposer + git/sqlite checkpoint loop
-╬ô├╢├⌐   ╬ô├╢┬ú╬ô├╢├ç╬ô├╢├ç cua-desktop-agent            # autonomous desktop automation via VLM perception loop; vision-based retry for legacy/API-less applications
-╬ô├╢├⌐   ╬ô├╢├╢╬ô├╢├ç╬ô├╢├ç react-fastapi-sqlite         # full-stack scaffold: React (TanStack Query) + FastAPI (SQLModel ORM) + SQLite; SPA + REST backend
-╬ô├╢├⌐
-╬ô├╢┬ú╬ô├╢├ç╬ô├╢├ç orchestration/                   # route work, enforce policy, manage cross-session state
-╬ô├╢├⌐   ╬ô├╢┬ú╬ô├╢├ç╬ô├╢├ç meta-harness                 # requester-facing manager layer above agentic-harness; scopes objectives, forks/resumes sessions, delegates one issue at a time
-╬ô├╢├⌐   ╬ô├╢┬ú╬ô├╢├ç╬ô├╢├ç agentic-orchestration        # unified: 5-Q decision tree + live agent roster + Aider architect/editor reference impl + Anthropic pattern taxonomy
-╬ô├╢├⌐   ╬ô├╢┬ú╬ô├╢├ç╬ô├╢├ç agentic-design-patterns      # LangGraph workflow shape, router/gate topology, manager/BA/dev/QA rooms
-╬ô├╢├⌐   ╬ô├╢┬ú╬ô├╢├ç╬ô├╢├ç agentic-harness              # dark-task control plane; backbone = OpenClaw/Claude Code/OpenCode/Copilot CLI; structured-response contracts + HTP
-╬ô├╢├⌐   ╬ô├╢├⌐   ╬ô├╢┬ú╬ô├╢├ç╬ô├╢├ç checklist                # LLM-as-judge validation pattern; structured findings with novelty proof
-╬ô├╢├⌐   ╬ô├╢├⌐   ╬ô├╢┬ú╬ô├╢├ç╬ô├╢├ç continuity-log           # compact-safe session memory; distilled decisions, resume points
-╬ô├╢├⌐   ╬ô├╢├⌐   ╬ô├╢┬ú╬ô├╢├ç╬ô├╢├ç pipeline-input-review    # partition a pipeline problem to its minimal failing unit; materialise inputs before harness dispatch; hyper-focused task statements
-╬ô├╢├⌐   ╬ô├╢├⌐   ╬ô├╢├╢╬ô├╢├ç╬ô├╢├ç deep-research            # multi-source web evidence pipeline; LangGraph planner╬ô├Ñ├åresearcher╬ô├Ñ├åsynthesizer
-╬ô├╢├⌐   ╬ô├╢┬ú╬ô├╢├ç╬ô├╢├ç openspec-workflow            # spec-driven change lifecycle with OpenSpec artifacts and Fabro handoff
-╬ô├╢├⌐   ╬ô├╢├⌐   ╬ô├╢┬ú╬ô├╢├ç╬ô├╢├ç openspec-propose         # create proposal/design/spec/tasks for a new change
-╬ô├╢├⌐   ╬ô├╢├⌐   ╬ô├╢┬ú╬ô├╢├ç╬ô├╢├ç openspec-explore         # think/discover mode around an OpenSpec change or idea
-╬ô├╢├⌐   ╬ô├╢├⌐   ╬ô├╢┬ú╬ô├╢├ç╬ô├╢├ç openspec-apply-change    # implement tasks from an OpenSpec change
-╬ô├╢├⌐   ╬ô├╢├⌐   ╬ô├╢├╢╬ô├╢├ç╬ô├╢├ç openspec-archive-change  # archive a completed OpenSpec change
-╬ô├╢├⌐   ╬ô├╢┬ú╬ô├╢├ç╬ô├╢├ç fabro-create-workflow        # author Fabro `.fabro` + `.toml` workflows from natural-language requirements
-╬ô├╢├⌐   ╬ô├╢┬ú╬ô├╢├ç╬ô├╢├ç substrate-selection          # runtime substrate policy: OpenCode / claw-code / pi / aider / provider boundary
-╬ô├╢├⌐   ╬ô├╢┬ú╬ô├╢├ç╬ô├╢├ç ollama-structured            # schema-constrained JSON from Ollama (native SDK + OpenAI compat); Qwen3 thinking suppression
-╬ô├╢├⌐   ╬ô├╢┬ú╬ô├╢├ç╬ô├╢├ç pi                           # lightweight delegated external harness; sits under opencode/agentic-harness and can host aider-like workers
-╬ô├╢├⌐   ╬ô├╢┬ú╬ô├╢├ç╬ô├╢├ç evaluator-optimizer          # LLM-generates╬ô├Ñ├åLLM-critiques╬ô├Ñ├åLLM-regenerates loop; MBR selection; stopping criteria
-╬ô├╢├⌐   ╬ô├╢├⌐   ╬ô├╢├╢╬ô├╢├ç╬ô├╢├ç prompt-optimization      # automatic prompt self-improvement; DSPy (MIPROv2), TextGrad (text-space gradients), OPRO, APE; labeled-trainset ╬ô├Ñ├å MIPROv2 vs no-trainset ╬ô├Ñ├å TextGrad decision tree
-╬ô├╢├⌐   ╬ô├╢┬ú╬ô├╢├ç╬ô├╢├ç multi-agent-coordination     # peer messaging, plan-approval gates, task ownership, dynamic spawning
-╬ô├╢├⌐   ╬ô├╢┬ú╬ô├╢├ç╬ô├╢├ç agent-governance             # safety rails, tool-access policy, audit trail, trust tiers, secrets scan
-╬ô├╢├⌐   ╬ô├╢┬ú╬ô├╢├ç╬ô├╢├ç security-review              # STRIDE-A, OWASP Top 10, data-flow tracing, secret/CVE detection
-╬ô├╢├⌐   ╬ô├╢┬ú╬ô├╢├ç╬ô├╢├ç build-observability          # run-centric observability contract: runs/events/commands, collectors, dashboards, trace enrichment
-╬ô├╢├⌐   ╬ô├╢┬ú╬ô├╢├ç╬ô├╢├ç timeout-guard                # runaway-task policy; interrupt and recovery rules
-╬ô├╢├⌐   ╬ô├╢┬ú╬ô├╢├ç╬ô├╢├ç git-workflow                 # branch strategy (test╬ô├Ñ├ådev╬ô├Ñ├åmain), push gates, LLM verification protocol with headless-browser checks
-╬ô├╢├⌐   ╬ô├╢┬ú╬ô├╢├ç╬ô├╢├ç validation-artifacts         # mandatory proof protocol: training loss curves, holdout metrics, test logs, visual diffs, API benchmarks, script outputs ╬ô├ç├╢ "seeing is believing"
-╬ô├╢├⌐   ╬ô├╢┬ú╬ô├╢├ç╬ô├╢├ç skill-wiki                   # living skill library lifecycle; intake ╬ô├Ñ├å staged ╬ô├Ñ├å active ╬ô├Ñ├å superseded governance
-╬ô├╢├⌐   ╬ô├╢┬ú╬ô├╢├ç╬ô├╢├ç skill-sync                   # LLM-assisted merge for diverged skill copies across local/remote mirrors; cron-safe
-╬ô├╢├⌐   ╬ô├╢├╢╬ô├╢├ç╬ô├╢├ç consolidation                # triplet-based pairwise correlation + greedy chain decomposition ╬ô├Ñ├å merge/xref/migrate prescriptions
-╬ô├╢├⌐
-╬ô├╢┬ú╬ô├╢├ç╬ô├╢├ç memory/                          # persist knowledge across sessions and tasks
-╬ô├╢├⌐   ╬ô├╢┬ú╬ô├╢├ç╬ô├╢├ç memory-bank                  # durable project memory (brief, context, patterns, progress)
-╬ô├╢├⌐   ╬ô├╢├⌐   # meta: DESCRIPTION/ARCHITECTURE/HISTORY pattern ╬ô├ç├╢ applies to any skill folder
-╬ô├╢├⌐   ╬ô├╢┬ú╬ô├╢├ç╬ô├╢├ç todo                         # sqlite-backed task tracking with FastMCP bridge
-╬ô├╢├⌐   ╬ô├╢┬ú╬ô├╢├ç╬ô├╢├ç cognitive-taxonomy           # unified memory classification: implicit/explicit/agentic paradigms; forms/functions/dynamics; System 1 vs 2 routing
-╬ô├╢├⌐   ╬ô├╢┬ú╬ô├╢├ç╬ô├╢├ç memory-architecture          # canonical 5-layer memory stack design: 4 templates (factual KB, personal assistant, autonomous agent, research); inter-layer routing; entity/procedure/query flows
-╬ô├╢├⌐   ╬ô├╢┬ú╬ô├╢├ç╬ô├╢├ç agentic_kg_memory            # MCG Context Graph side: semantic memory policy, retrieval, patterns, tribal knowledge, episodic memory
-╬ô├╢├⌐   ╬ô├╢├⌐   ╬ô├╢┬ú╬ô├╢├ç╬ô├╢├ç kg_ontology              # MCG DKG entity-identity layer: synset/hypernym BM25 canonicalization
-╬ô├╢├⌐   ╬ô├╢├⌐   ╬ô├╢├╢╬ô├╢├ç╬ô├╢├ç gist-retriever           # layered sparse+dense retrieval engine (BM25 + Chroma)
-╬ô├╢├⌐   ╬ô├╢┬ú╬ô├╢├ç╬ô├╢├ç crystallization              # distill completed work chains into digest pages + reusable lessons; hand off semantic outputs to agentic_kg_memory and procedural deltas to skill-wiki
-╬ô├╢├⌐   ╬ô├╢┬ú╬ô├╢├ç╬ô├╢├ç semantic-search-enrichment   # retrieval augmentation: query expansion, metadata boosting, semantic reranking
-╬ô├╢├⌐   ╬ô├╢┬ú╬ô├╢├ç╬ô├╢├ç context-compaction           # active context-window management: tiered eviction, pre/post-compaction hooks
-╬ô├╢├⌐   ╬ô├╢┬ú╬ô├╢├ç╬ô├╢├ç mcp-tool-registry            # MCP tool registration, discovery, routing, ACI design
-╬ô├╢├⌐   ╬ô├╢┬ú╬ô├╢├ç╬ô├╢├ç request-intent-resolution    # request-thread routing, retrieval evaluation
-╬ô├╢├⌐   ╬ô├╢├╢╬ô├╢├ç╬ô├╢├ç feature-catalog              # local SQLite feature inventory for implemented capabilities and file mappings
-╬ô├╢├⌐
-╬ô├╢┬ú╬ô├╢├ç╬ô├╢├ç tuning/                          # measure, optimize, record
-╬ô├╢├⌐   ╬ô├╢┬ú╬ô├╢├ç╬ô├╢├ç optuna-nested-cv             # search engine + methodology primer: inner tune / outer unbiased estimate
-╬ô├╢├⌐   ╬ô├╢┬ú╬ô├╢├ç╬ô├╢├ç hyper-parm_tuning            # superseded predecessor; canonical home for Weighted Stage Allocation pattern
-╬ô├╢├⌐   ╬ô├╢┬ú╬ô├╢├ç╬ô├╢├ç agentic-hyperparm            # behavioral knob tuning for agentic systems; instantiates Stage Allocation for L1-L4 layers
-╬ô├╢├⌐   ╬ô├╢┬ú╬ô├╢├ç╬ô├╢├ç parm-tuning-as-lp            # discrete hyperparameter tuning via linear/mixed-integer programming; orthogonal lever factorization, irreducible-ratio perturbation basis, global optimality
-╬ô├╢├⌐   ╬ô├╢┬ú╬ô├╢├ç╬ô├╢├ç class-balancing              # conditional stratification + token-equal weighting for multi-class reasoning transfer; inference pairing; temperature curriculum
-╬ô├╢├⌐   ╬ô├╢┬ú╬ô├╢├ç╬ô├╢├ç stratified-quota-sampling    # coverage-bounded no-replacement sampler; Box-Cox tiers + quota allocation
-╬ô├╢├⌐   ╬ô├╢├⌐   ╬ô├╢├╢╬ô├╢├ç╬ô├╢├ç synthetic-data           # LLM-generated training data; 8 paradigms (Self-Instruct/Evol-Instruct/GLAN/Magpie/UltraFeedback/FireAct/distilabel); 6 mandatory quality gates; handoff to stratified-quota-sampling + class-balancing
-╬ô├╢├⌐   ╬ô├╢┬ú╬ô├╢├ç╬ô├╢├ç cluster-quantized-knn        # O(1) approximate distance for KNN via cluster-quantization; fast interactive retrieval
-╬ô├╢├⌐   ╬ô├╢┬ú╬ô├╢├ç╬ô├╢├ç mad-dynamic-batching         # MAD-gated token-aware dynamic batching for variable-length training data; quantile partitioning
-╬ô├╢├⌐   ╬ô├╢┬ú╬ô├╢├ç╬ô├╢├ç median-bifurcation           # universal median-cut pattern: choose axis ╬ô├Ñ├å produce both sides ╬ô├Ñ├å drop unwanted half; 2^n epistemic cells at zero labeling cost; data-level contrastive learning
-╬ô├╢├⌐   ╬ô├╢┬ú╬ô├╢├ç╬ô├╢├ç mlflow                       # experiment ledger: params, metrics, artifacts, lineage
-╬ô├╢├⌐   ╬ô├╢┬ú╬ô├╢├ç╬ô├╢├ç model-size-reduction         # checkpoint slimming for HF models: dtype cast, layer drop, LoRA extraction, DARE/TIES/DELLA; architecture-agnostic state_dict path
-╬ô├╢├⌐   ╬ô├╢┬ú╬ô├╢├ç╬ô├╢├ç generalization-theory        # signal-vs-noise training-dynamics lens via eNTK; diagnose memorization, grokking, and noisy-preference fine-tunes
-╬ô├╢├⌐   ╬ô├╢┬ú╬ô├╢├ç╬ô├╢├ç representation-pipeline      # representation design: raw signal ╬ô├Ñ├å embedding space
-╬ô├╢├⌐   ╬ô├╢┬ú╬ô├╢├ç╬ô├╢├ç bm25-corpus-sampling         # representative corpus sampling for BM25; log-normal╬ô├Ñ├åMAD╬ô├Ñ├åYeo-Johnson╬ô├Ñ├åCDF-diff quota; cascaded and proxy-Louvain rerankers
-╬ô├╢├⌐   ╬ô├╢├╢╬ô├╢├ç╬ô├╢├ç rag-eval                     # single-pass 10-metric RAG judge: qwen3.5:4b + Pydantic RAGEvalResult + macro_mean; one prompt per answer
-╬ô├╢├⌐
-╬ô├╢┬ú╬ô├╢├ç╬ô├╢├ç artifacts/                       # masterpiece outputs and information design
-╬ô├╢├⌐   ╬ô├╢┬ú╬ô├╢├ç╬ô├╢├ç documentation                # choose canonical doc vs changelog vs timestamped fixes-applied artifact
-╬ô├╢├⌐   ╬ô├╢┬ú╬ô├╢├ç╬ô├╢├ç response-style               # voice preservation, anti-cliche prose, user-facing coherence
-╬ô├╢├⌐   ╬ô├╢┬ú╬ô├╢├ç╬ô├╢├ç business-writing             # professional document writing: resume, cover letter, portfolio; triplet bullets, spice gradient
-╬ô├╢├⌐   ╬ô├╢┬ú╬ô├╢├ç╬ô├╢├ç gist_correlation_matrix      # sorted correlation matrix as complete relational map; two sorting approaches (orthogonal vs coverage)
-╬ô├╢├⌐   ╬ô├╢┬ú╬ô├╢├ç╬ô├╢├ç nearest-neighbor-chain       # greedy path-cover decomposition of a similarity matrix into variable-length semantic chains; Γòº├ñ selection; chaining = semantic thread
-╬ô├╢├⌐   ╬ô├╢├╢╬ô├╢├ç╬ô├╢├ç spiral-radial-clustering-display  # multi-dimensional spiral visualization; GMM+HDBSCAN+ordering╬ô├Ñ├åUMAP 2D with Gestalt encoding
-╬ô├╢├⌐
-╬ô├╢┬ú╬ô├╢├ç╬ô├╢├ç learning/                        # reinforcement learning and policy optimization
-╬ô├╢├⌐   ╬ô├╢┬ú╬ô├╢├ç╬ô├╢├ç deep-q-rl                    # DQN + Russian Doll MCTS for any scored discrete-action framework; code-rl extension; SPO/DPO offline preference optimization
-╬ô├╢├⌐   ╬ô├╢┬ú╬ô├╢├ç╬ô├╢├ç active-inference             # Bayesian POMDP agents via Free Energy Principle; EFE-driven tool selection; pymdp; use when no reward function + partial observability
-╬ô├╢├⌐   ╬ô├╢┬ú╬ô├╢├ç╬ô├╢├ç continual-learning           # non-forgetting agents; EWC, GEM/A-GEM, PackNet, O-LoRA/InfLoRA, DARE, LwF, MemRL; absorbs integrate/MemRL
-╬ô├╢├⌐   ╬ô├╢├╢╬ô├╢├ç╬ô├╢├ç siamese_from_correlation_matrix  # derive metric-learning pairs directly from embedding/correlation structure
-╬ô├╢├⌐
-╬ô├╢├╢╬ô├╢├ç╬ô├╢├ç pipelines/                       # end-to-end domain workflows (invoke sub-skills as needed)
-    ╬ô├╢┬ú╬ô├╢├ç╬ô├╢├ç auto-ingest                  # on-demand and background PDF enrichment for arxiv_rag corpus; VLM methods extraction
-    ╬ô├╢├╢╬ô├╢├ç╬ô├╢├ç pdf-extraction               # docling╬ô├Ñ├åbase64 strip╬ô├Ñ├åVLM╬ô├Ñ├åreinsert╬ô├Ñ├åmethods; table enhancement with tabula+camelot+VLM fusion; classifier training via class-balancing
+├óΓÇ¥┼ô├óΓÇ¥Γé¼├óΓÇ¥Γé¼ execution/                       # plan, implement, verify
+├óΓÇ¥ΓÇÜ   ├óΓÇ¥┼ô├óΓÇ¥Γé¼├óΓÇ¥Γé¼ react-agent                  # outer execution OS; drives all other skills
+├óΓÇ¥ΓÇÜ   ├óΓÇ¥┼ô├óΓÇ¥Γé¼├óΓÇ¥Γé¼ reasoning                    # open-ended problem decomposition + multi-perspective analysis
+├óΓÇ¥ΓÇÜ   ├óΓÇ¥ΓÇÜ   ├óΓÇ¥ΓÇ¥├óΓÇ¥Γé¼├óΓÇ¥Γé¼ causal-inference         # LLM├óΓÇáΓÇÖDoWhy├óΓÇáΓÇÖLLM architecture; Pearl's ladder (association/intervention/counterfactual); causal discovery, do-calculus, SCM via DoWhy + causal-learn
+├óΓÇ¥ΓÇÜ   ├óΓÇ¥┼ô├óΓÇ¥Γé¼├óΓÇ¥Γé¼ codebase-knowledge-graph     # current-repo whole-system map; foundational vs incidental code; ripple analysis before edits
+├óΓÇ¥ΓÇÜ   ├óΓÇ¥┼ô├óΓÇ¥Γé¼├óΓÇ¥Γé¼ code                         # implementation standards, naming, refactor sequence
+├óΓÇ¥ΓÇÜ   ├óΓÇ¥ΓÇÜ   ├óΓÇ¥ΓÇ¥├óΓÇ¥Γé¼├óΓÇ¥Γé¼ design-patterns          # GoF / contract / relationship-shape companion to code
+├óΓÇ¥ΓÇÜ   ├óΓÇ¥┼ô├óΓÇ¥Γé¼├óΓÇ¥Γé¼ code-extraction              # extract source files + configs into copy-paste-ready markdown artifact (docling-style)
+├óΓÇ¥ΓÇÜ   ├óΓÇ¥┼ô├óΓÇ¥Γé¼├óΓÇ¥Γé¼ diagnostic-scanner           # language-aware compiler/linter scanning; errors/warnings grouped by severity
+├óΓÇ¥ΓÇÜ   ├óΓÇ¥┼ô├óΓÇ¥Γé¼├óΓÇ¥Γé¼ schema-induction             # cross-instance schema discovery via pairwise contrast (Aristotelian diairesis); constants vs variable dims; CRISP-DM data understanding analog
+├óΓÇ¥ΓÇÜ   ├óΓÇ¥┼ô├óΓÇ¥Γé¼├óΓÇ¥Γé¼ test-planner                 # coverage-aware test plan generation (green/yellow/red status); regression detection
+├óΓÇ¥ΓÇÜ   ├óΓÇ¥┼ô├óΓÇ¥Γé¼├óΓÇ¥Γé¼ doc-synthesizer              # AST-based documentation with Mermaid dependency/data-flow diagrams
+├óΓÇ¥ΓÇÜ   ├óΓÇ¥┼ô├óΓÇ¥Γé¼├óΓÇ¥Γé¼ debugging                    # error isolation, salience tiers, diagnostic strategy, self-repair loop
+├óΓÇ¥ΓÇÜ   ├óΓÇ¥ΓÇÜ   ├óΓÇ¥ΓÇ¥├óΓÇ¥Γé¼├óΓÇ¥Γé¼ adjacent-surface-scan    # one-degree-out sibling scan when one missing item likely belongs to a local family
+├óΓÇ¥ΓÇÜ   ├óΓÇ¥┼ô├óΓÇ¥Γé¼├óΓÇ¥Γé¼ validation                   # test design, verification protocol, behavior contracts
+├óΓÇ¥ΓÇÜ   ├óΓÇ¥ΓÇÜ   ├óΓÇ¥ΓÇ¥├óΓÇ¥Γé¼├óΓÇ¥Γé¼ uncertainty-quantification  # 3-tier UQ protocol (fast/standard/thorough); semantic entropy, SelfCheckGPT, conformal prediction, LM-Polygraph; abstain/escalate table
+├óΓÇ¥ΓÇÜ   ├óΓÇ¥┼ô├óΓÇ¥Γé¼├óΓÇ¥Γé¼ architecture                 # system design, abstract-class planning, domain ├óΓÇáΓÇÖ code mapping
+├óΓÇ¥ΓÇÜ   ├óΓÇ¥┼ô├óΓÇ¥Γé¼├óΓÇ¥Γé¼ tdd-agent                    # Red├óΓÇáΓÇÖGreen├óΓÇáΓÇÖRefactor as distinct agentic phases; test-first design contract
+├óΓÇ¥ΓÇÜ   ├óΓÇ¥ΓÇÜ   ├óΓÇ¥ΓÇ¥├óΓÇ¥Γé¼├óΓÇ¥Γé¼ program-synthesis        # LLM-assisted formal verification + proof-assisted coding; AutoVerus 3-phase loop; escalation from tdd-agent for unbounded/security properties
+├óΓÇ¥ΓÇÜ   ├óΓÇ¥┼ô├óΓÇ¥Γé¼├óΓÇ¥Γé¼ autoresearch                 # autonomous iterative hill-climbing: scorer + proposer + git/sqlite checkpoint loop
+├óΓÇ¥ΓÇÜ   ├óΓÇ¥┼ô├óΓÇ¥Γé¼├óΓÇ¥Γé¼ cua-desktop-agent            # autonomous desktop automation via VLM perception loop; vision-based retry for legacy/API-less applications
+├óΓÇ¥ΓÇÜ   ├óΓÇ¥ΓÇ¥├óΓÇ¥Γé¼├óΓÇ¥Γé¼ react-fastapi-sqlite         # full-stack scaffold: React (TanStack Query) + FastAPI (SQLModel ORM) + SQLite; SPA + REST backend
+├óΓÇ¥ΓÇÜ
+├óΓÇ¥┼ô├óΓÇ¥Γé¼├óΓÇ¥Γé¼ orchestration/                   # route work, enforce policy, manage cross-session state
+├óΓÇ¥ΓÇÜ   ├óΓÇ¥┼ô├óΓÇ¥Γé¼├óΓÇ¥Γé¼ meta-harness                 # requester-facing manager layer above agentic-harness; scopes objectives, forks/resumes sessions, delegates one issue at a time
+├óΓÇ¥ΓÇÜ   ├óΓÇ¥┼ô├óΓÇ¥Γé¼├óΓÇ¥Γé¼ agentic-orchestration        # unified: 5-Q decision tree + live agent roster + Aider architect/editor reference impl + Anthropic pattern taxonomy
+├óΓÇ¥ΓÇÜ   ├óΓÇ¥┼ô├óΓÇ¥Γé¼├óΓÇ¥Γé¼ agentic-design-patterns      # LangGraph workflow shape, router/gate topology, manager/BA/dev/QA rooms
+├óΓÇ¥ΓÇÜ   ├óΓÇ¥┼ô├óΓÇ¥Γé¼├óΓÇ¥Γé¼ agentic-harness              # dark-task control plane; backbone = OpenClaw/Claude Code/OpenCode/Copilot CLI; structured-response contracts + HTP
+├óΓÇ¥ΓÇÜ   ├óΓÇ¥ΓÇÜ   ├óΓÇ¥┼ô├óΓÇ¥Γé¼├óΓÇ¥Γé¼ checklist                # LLM-as-judge validation pattern; structured findings with novelty proof
+├óΓÇ¥ΓÇÜ   ├óΓÇ¥ΓÇÜ   ├óΓÇ¥┼ô├óΓÇ¥Γé¼├óΓÇ¥Γé¼ continuity-log           # compact-safe session memory; distilled decisions, resume points
+├óΓÇ¥ΓÇÜ   ├óΓÇ¥ΓÇÜ   ├óΓÇ¥┼ô├óΓÇ¥Γé¼├óΓÇ¥Γé¼ pipeline-input-review    # partition a pipeline problem to its minimal failing unit; materialise inputs before harness dispatch; hyper-focused task statements
+├óΓÇ¥ΓÇÜ   ├óΓÇ¥ΓÇÜ   ├óΓÇ¥ΓÇ¥├óΓÇ¥Γé¼├óΓÇ¥Γé¼ deep-research            # multi-source web evidence pipeline; LangGraph planner├óΓÇáΓÇÖresearcher├óΓÇáΓÇÖsynthesizer
+├óΓÇ¥ΓÇÜ   ├óΓÇ¥┼ô├óΓÇ¥Γé¼├óΓÇ¥Γé¼ openspec-workflow            # spec-driven change lifecycle with OpenSpec artifacts and Fabro handoff
+├óΓÇ¥ΓÇÜ   ├óΓÇ¥ΓÇÜ   ├óΓÇ¥┼ô├óΓÇ¥Γé¼├óΓÇ¥Γé¼ openspec-propose         # create proposal/design/spec/tasks for a new change
+├óΓÇ¥ΓÇÜ   ├óΓÇ¥ΓÇÜ   ├óΓÇ¥┼ô├óΓÇ¥Γé¼├óΓÇ¥Γé¼ openspec-explore         # think/discover mode around an OpenSpec change or idea
+├óΓÇ¥ΓÇÜ   ├óΓÇ¥ΓÇÜ   ├óΓÇ¥┼ô├óΓÇ¥Γé¼├óΓÇ¥Γé¼ openspec-apply-change    # implement tasks from an OpenSpec change
+├óΓÇ¥ΓÇÜ   ├óΓÇ¥ΓÇÜ   ├óΓÇ¥ΓÇ¥├óΓÇ¥Γé¼├óΓÇ¥Γé¼ openspec-archive-change  # archive a completed OpenSpec change
+├óΓÇ¥ΓÇÜ   ├óΓÇ¥┼ô├óΓÇ¥Γé¼├óΓÇ¥Γé¼ fabro-create-workflow        # author Fabro `.fabro` + `.toml` workflows from natural-language requirements
+├óΓÇ¥ΓÇÜ   ├óΓÇ¥┼ô├óΓÇ¥Γé¼├óΓÇ¥Γé¼ substrate-selection          # runtime substrate policy: OpenCode / claw-code / pi / aider / provider boundary
+├óΓÇ¥ΓÇÜ   ├óΓÇ¥┼ô├óΓÇ¥Γé¼├óΓÇ¥Γé¼ ollama-structured            # schema-constrained JSON from Ollama (native SDK + OpenAI compat); Qwen3 thinking suppression
+├óΓÇ¥ΓÇÜ   ├óΓÇ¥┼ô├óΓÇ¥Γé¼├óΓÇ¥Γé¼ pi                           # lightweight delegated external harness; sits under opencode/agentic-harness and can host aider-like workers
+├óΓÇ¥ΓÇÜ   ├óΓÇ¥┼ô├óΓÇ¥Γé¼├óΓÇ¥Γé¼ evaluator-optimizer          # LLM-generates├óΓÇáΓÇÖLLM-critiques├óΓÇáΓÇÖLLM-regenerates loop; MBR selection; stopping criteria
+├óΓÇ¥ΓÇÜ   ├óΓÇ¥ΓÇÜ   ├óΓÇ¥ΓÇ¥├óΓÇ¥Γé¼├óΓÇ¥Γé¼ prompt-optimization      # automatic prompt self-improvement; DSPy (MIPROv2), TextGrad (text-space gradients), OPRO, APE; labeled-trainset ├óΓÇáΓÇÖ MIPROv2 vs no-trainset ├óΓÇáΓÇÖ TextGrad decision tree
+├óΓÇ¥ΓÇÜ   ├óΓÇ¥┼ô├óΓÇ¥Γé¼├óΓÇ¥Γé¼ multi-agent-coordination     # peer messaging, plan-approval gates, task ownership, dynamic spawning
+├óΓÇ¥ΓÇÜ   ├óΓÇ¥┼ô├óΓÇ¥Γé¼├óΓÇ¥Γé¼ agent-governance             # safety rails, tool-access policy, audit trail, trust tiers, secrets scan
+├óΓÇ¥ΓÇÜ   ├óΓÇ¥┼ô├óΓÇ¥Γé¼├óΓÇ¥Γé¼ security-review              # STRIDE-A, OWASP Top 10, data-flow tracing, secret/CVE detection
+├óΓÇ¥ΓÇÜ   ├óΓÇ¥┼ô├óΓÇ¥Γé¼├óΓÇ¥Γé¼ build-observability          # run-centric observability contract: runs/events/commands, collectors, dashboards, trace enrichment
+├óΓÇ¥ΓÇÜ   ├óΓÇ¥┼ô├óΓÇ¥Γé¼├óΓÇ¥Γé¼ timeout-guard                # runaway-task policy; interrupt and recovery rules
+├óΓÇ¥ΓÇÜ   ├óΓÇ¥┼ô├óΓÇ¥Γé¼├óΓÇ¥Γé¼ git-workflow                 # branch strategy (test├óΓÇáΓÇÖdev├óΓÇáΓÇÖmain), push gates, LLM verification protocol with headless-browser checks
+├óΓÇ¥ΓÇÜ   ├óΓÇ¥┼ô├óΓÇ¥Γé¼├óΓÇ¥Γé¼ validation-artifacts         # mandatory proof protocol: training loss curves, holdout metrics, test logs, visual diffs, API benchmarks, script outputs ├óΓé¼ΓÇ¥ "seeing is believing"
+├óΓÇ¥ΓÇÜ   ├óΓÇ¥┼ô├óΓÇ¥Γé¼├óΓÇ¥Γé¼ skill-wiki                   # living skill library lifecycle; intake ├óΓÇáΓÇÖ staged ├óΓÇáΓÇÖ active ├óΓÇáΓÇÖ superseded governance
+├óΓÇ¥ΓÇÜ   ├óΓÇ¥┼ô├óΓÇ¥Γé¼├óΓÇ¥Γé¼ skill-sync                   # LLM-assisted merge for diverged skill copies across local/remote mirrors; cron-safe
+├óΓÇ¥ΓÇÜ   ├óΓÇ¥ΓÇ¥├óΓÇ¥Γé¼├óΓÇ¥Γé¼ consolidation                # triplet-based pairwise correlation + greedy chain decomposition ├óΓÇáΓÇÖ merge/xref/migrate prescriptions
+├óΓÇ¥ΓÇÜ
+├óΓÇ¥┼ô├óΓÇ¥Γé¼├óΓÇ¥Γé¼ memory/                          # persist knowledge across sessions and tasks
+├óΓÇ¥ΓÇÜ   ├óΓÇ¥┼ô├óΓÇ¥Γé¼├óΓÇ¥Γé¼ memory-bank                  # durable project memory (brief, context, patterns, progress)
+├óΓÇ¥ΓÇÜ   ├óΓÇ¥ΓÇÜ   # meta: DESCRIPTION/ARCHITECTURE/HISTORY pattern ├óΓé¼ΓÇ¥ applies to any skill folder
+├óΓÇ¥ΓÇÜ   ├óΓÇ¥┼ô├óΓÇ¥Γé¼├óΓÇ¥Γé¼ todo                         # sqlite-backed task tracking with FastMCP bridge
+├óΓÇ¥ΓÇÜ   ├óΓÇ¥┼ô├óΓÇ¥Γé¼├óΓÇ¥Γé¼ cognitive-taxonomy           # unified memory classification: implicit/explicit/agentic paradigms; forms/functions/dynamics; System 1 vs 2 routing
+├óΓÇ¥ΓÇÜ   ├óΓÇ¥┼ô├óΓÇ¥Γé¼├óΓÇ¥Γé¼ memory-architecture          # canonical 5-layer memory stack design: 4 templates (factual KB, personal assistant, autonomous agent, research); inter-layer routing; entity/procedure/query flows
+├óΓÇ¥ΓÇÜ   ├óΓÇ¥┼ô├óΓÇ¥Γé¼├óΓÇ¥Γé¼ agentic_kg_memory            # MCG Context Graph side: semantic memory policy, retrieval, patterns, tribal knowledge, episodic memory
+├óΓÇ¥ΓÇÜ   ├óΓÇ¥ΓÇÜ   ├óΓÇ¥┼ô├óΓÇ¥Γé¼├óΓÇ¥Γé¼ kg_ontology              # MCG DKG entity-identity layer: synset/hypernym BM25 canonicalization
+├óΓÇ¥ΓÇÜ   ├óΓÇ¥ΓÇÜ   ├óΓÇ¥ΓÇ¥├óΓÇ¥Γé¼├óΓÇ¥Γé¼ gist-retriever           # layered sparse+dense retrieval engine (BM25 + Chroma)
+├óΓÇ¥ΓÇÜ   ├óΓÇ¥┼ô├óΓÇ¥Γé¼├óΓÇ¥Γé¼ crystallization              # distill completed work chains into digest pages + reusable lessons; hand off semantic outputs to agentic_kg_memory and procedural deltas to skill-wiki
+├óΓÇ¥ΓÇÜ   ├óΓÇ¥┼ô├óΓÇ¥Γé¼├óΓÇ¥Γé¼ semantic-search-enrichment   # retrieval augmentation: query expansion, metadata boosting, semantic reranking
+├óΓÇ¥ΓÇÜ   ├óΓÇ¥┼ô├óΓÇ¥Γé¼├óΓÇ¥Γé¼ context-compaction           # active context-window management: tiered eviction, pre/post-compaction hooks
+├óΓÇ¥ΓÇÜ   ├óΓÇ¥┼ô├óΓÇ¥Γé¼├óΓÇ¥Γé¼ mcp-tool-registry            # MCP tool registration, discovery, routing, ACI design
+├óΓÇ¥ΓÇÜ   ├óΓÇ¥┼ô├óΓÇ¥Γé¼├óΓÇ¥Γé¼ request-intent-resolution    # request-thread routing, retrieval evaluation
+├óΓÇ¥ΓÇÜ   ├óΓÇ¥ΓÇ¥├óΓÇ¥Γé¼├óΓÇ¥Γé¼ feature-catalog              # local SQLite feature inventory for implemented capabilities and file mappings
+├óΓÇ¥ΓÇÜ
+├óΓÇ¥┼ô├óΓÇ¥Γé¼├óΓÇ¥Γé¼ tuning/                          # measure, optimize, record
+├óΓÇ¥ΓÇÜ   ├óΓÇ¥┼ô├óΓÇ¥Γé¼├óΓÇ¥Γé¼ optuna-nested-cv             # search engine + methodology primer: inner tune / outer unbiased estimate
+├óΓÇ¥ΓÇÜ   ├óΓÇ¥┼ô├óΓÇ¥Γé¼├óΓÇ¥Γé¼ hyper-parm_tuning            # superseded predecessor; canonical home for Weighted Stage Allocation pattern
+├óΓÇ¥ΓÇÜ   ├óΓÇ¥┼ô├óΓÇ¥Γé¼├óΓÇ¥Γé¼ agentic-hyperparm            # behavioral knob tuning for agentic systems; instantiates Stage Allocation for L1-L4 layers
+├óΓÇ¥ΓÇÜ   ├óΓÇ¥┼ô├óΓÇ¥Γé¼├óΓÇ¥Γé¼ parm-tuning-as-lp            # discrete hyperparameter tuning via linear/mixed-integer programming; orthogonal lever factorization, irreducible-ratio perturbation basis, global optimality
+├óΓÇ¥ΓÇÜ   ├óΓÇ¥┼ô├óΓÇ¥Γé¼├óΓÇ¥Γé¼ class-balancing              # conditional stratification + token-equal weighting for multi-class reasoning transfer; inference pairing; temperature curriculum
+├óΓÇ¥ΓÇÜ   ├óΓÇ¥┼ô├óΓÇ¥Γé¼├óΓÇ¥Γé¼ stratified-quota-sampling    # coverage-bounded no-replacement sampler; Box-Cox tiers + quota allocation
+├óΓÇ¥ΓÇÜ   ├óΓÇ¥ΓÇÜ   ├óΓÇ¥ΓÇ¥├óΓÇ¥Γé¼├óΓÇ¥Γé¼ synthetic-data           # LLM-generated training data; 8 paradigms (Self-Instruct/Evol-Instruct/GLAN/Magpie/UltraFeedback/FireAct/distilabel); 6 mandatory quality gates; handoff to stratified-quota-sampling + class-balancing
+├óΓÇ¥ΓÇÜ   ├óΓÇ¥┼ô├óΓÇ¥Γé¼├óΓÇ¥Γé¼ cluster-quantized-knn        # O(1) approximate distance for KNN via cluster-quantization; fast interactive retrieval
+├óΓÇ¥ΓÇÜ   ├óΓÇ¥┼ô├óΓÇ¥Γé¼├óΓÇ¥Γé¼ mad-dynamic-batching         # MAD-gated token-aware dynamic batching for variable-length training data; quantile partitioning
+├óΓÇ¥ΓÇÜ   ├óΓÇ¥┼ô├óΓÇ¥Γé¼├óΓÇ¥Γé¼ median-bifurcation           # universal median-cut pattern: choose axis ├óΓÇáΓÇÖ produce both sides ├óΓÇáΓÇÖ drop unwanted half; 2^n epistemic cells at zero labeling cost; data-level contrastive learning
+├óΓÇ¥ΓÇÜ   ├óΓÇ¥┼ô├óΓÇ¥Γé¼├óΓÇ¥Γé¼ mlflow                       # experiment ledger: params, metrics, artifacts, lineage
+├óΓÇ¥ΓÇÜ   ├óΓÇ¥┼ô├óΓÇ¥Γé¼├óΓÇ¥Γé¼ model-size-reduction         # checkpoint slimming for HF models: dtype cast, layer drop, LoRA extraction, DARE/TIES/DELLA; architecture-agnostic state_dict path
+├óΓÇ¥ΓÇÜ   ├óΓÇ¥┼ô├óΓÇ¥Γé¼├óΓÇ¥Γé¼ generalization-theory        # signal-vs-noise training-dynamics lens via eNTK; diagnose memorization, grokking, and noisy-preference fine-tunes
+├óΓÇ¥ΓÇÜ   ├óΓÇ¥┼ô├óΓÇ¥Γé¼├óΓÇ¥Γé¼ representation-pipeline      # representation design: raw signal ├óΓÇáΓÇÖ embedding space
+├óΓÇ¥ΓÇÜ   ├óΓÇ¥┼ô├óΓÇ¥Γé¼├óΓÇ¥Γé¼ bm25-corpus-sampling         # representative corpus sampling for BM25; log-normal├óΓÇáΓÇÖMAD├óΓÇáΓÇÖYeo-Johnson├óΓÇáΓÇÖCDF-diff quota; cascaded and proxy-Louvain rerankers; BM25 correlation graph (significant correlations as edges)
+├óΓÇ¥ΓÇÜ   ├óΓÇ¥┼ô├óΓÇ¥Γé¼├óΓÇ¥Γé¼ bm25-autoencoder             # multi-view sparse bottleneck: TF-IDF + token count + char bitvec ├óΓÇáΓÇÖ TruncatedSVD z; collinearity test vs dense; music embedding matrix pattern
+├óΓÇ¥ΓÇÜ   ├óΓÇ¥┼ô├óΓÇ¥Γé¼├óΓÇ¥Γé¼ signal-modulation            # demodulate non-stationary signal (log├óΓÇáΓÇÖMAD├óΓÇáΓÇÖYeo-Johnson) ├óΓÇáΓÇÖ MACD on normalized space ├óΓÇáΓÇÖ RL band maintenance; regime-invariant threshold calibration
+├óΓÇ¥ΓÇÜ   ├óΓÇ¥ΓÇ¥├óΓÇ¥Γé¼├óΓÇ¥Γé¼ rag-eval                     # single-pass 10-metric RAG judge: qwen3.5:4b + Pydantic RAGEvalResult + macro_mean; one prompt per answer
+├óΓÇ¥ΓÇÜ
+├óΓÇ¥┼ô├óΓÇ¥Γé¼├óΓÇ¥Γé¼ artifacts/                       # masterpiece outputs and information design
+├óΓÇ¥ΓÇÜ   ├óΓÇ¥┼ô├óΓÇ¥Γé¼├óΓÇ¥Γé¼ documentation                # choose canonical doc vs changelog vs timestamped fixes-applied artifact
+├óΓÇ¥ΓÇÜ   ├óΓÇ¥┼ô├óΓÇ¥Γé¼├óΓÇ¥Γé¼ response-style               # voice preservation, anti-cliche prose, user-facing coherence
+├óΓÇ¥ΓÇÜ   ├óΓÇ¥┼ô├óΓÇ¥Γé¼├óΓÇ¥Γé¼ business-writing             # professional document writing: resume, cover letter, portfolio; triplet bullets, spice gradient
+├óΓÇ¥ΓÇÜ   ├óΓÇ¥┼ô├óΓÇ¥Γé¼├óΓÇ¥Γé¼ gist_correlation_matrix      # sorted correlation matrix as complete relational map; two sorting approaches (orthogonal vs coverage)
+├óΓÇ¥ΓÇÜ   ├óΓÇ¥┼ô├óΓÇ¥Γé¼├óΓÇ¥Γé¼ nearest-neighbor-chain       # greedy path-cover decomposition of a similarity matrix into variable-length semantic chains; ├ÅΓÇ₧ selection; chaining = semantic thread
+├óΓÇ¥ΓÇÜ   ├óΓÇ¥ΓÇ¥├óΓÇ¥Γé¼├óΓÇ¥Γé¼ spiral-radial-clustering-display  # multi-dimensional spiral visualization; GMM+HDBSCAN+ordering├óΓÇáΓÇÖUMAP 2D with Gestalt encoding
+├óΓÇ¥ΓÇÜ
+├óΓÇ¥┼ô├óΓÇ¥Γé¼├óΓÇ¥Γé¼ learning/                        # reinforcement learning and policy optimization
+├óΓÇ¥ΓÇÜ   ├óΓÇ¥┼ô├óΓÇ¥Γé¼├óΓÇ¥Γé¼ deep-q-rl                    # DQN + Russian Doll MCTS for any scored discrete-action framework; code-rl extension; SPO/DPO offline preference optimization
+├óΓÇ¥ΓÇÜ   ├óΓÇ¥┼ô├óΓÇ¥Γé¼├óΓÇ¥Γé¼ active-inference             # Bayesian POMDP agents via Free Energy Principle; EFE-driven tool selection; pymdp; use when no reward function + partial observability
+├óΓÇ¥ΓÇÜ   ├óΓÇ¥┼ô├óΓÇ¥Γé¼├óΓÇ¥Γé¼ continual-learning           # non-forgetting agents; EWC, GEM/A-GEM, PackNet, O-LoRA/InfLoRA, DARE, LwF, MemRL; absorbs integrate/MemRL
+├óΓÇ¥ΓÇÜ   ├óΓÇ¥ΓÇ¥├óΓÇ¥Γé¼├óΓÇ¥Γé¼ siamese_from_correlation_matrix  # derive metric-learning pairs directly from embedding/correlation structure
+├óΓÇ¥ΓÇÜ
+├óΓÇ¥ΓÇ¥├óΓÇ¥Γé¼├óΓÇ¥Γé¼ pipelines/                       # end-to-end domain workflows (invoke sub-skills as needed)
+    ├óΓÇ¥┼ô├óΓÇ¥Γé¼├óΓÇ¥Γé¼ auto-ingest                  # on-demand and background PDF enrichment for arxiv_rag corpus; VLM methods extraction
+    ├óΓÇ¥ΓÇ¥├óΓÇ¥Γé¼├óΓÇ¥Γé¼ pdf-extraction               # docling├óΓÇáΓÇÖbase64 strip├óΓÇáΓÇÖVLM├óΓÇáΓÇÖreinsert├óΓÇáΓÇÖmethods; table enhancement with tabula+camelot+VLM fusion; classifier training via class-balancing
 ```

 ## Key Relationships

 1. `react-agent` is the outer execution OS. All other skills are invoked from inside it.
 2. `design-patterns` is the code-facing pattern selector. `code` owns edit mechanics; `design-patterns` chooses the relationship shape and contract.
 3. `agentic-design-patterns` chooses LangGraph workflow shape and role topology. It is where routing, prompt chaining, parallel sectioning, voting, orchestrator-workers, evaluator-optimizer, and bounded autonomous loops belong.
 4. `meta-harness` is the manager layer one step above `agentic-harness`: it owns objective framing, scoped session decomposition, and parent/child coordination so request-level planning stays separate from issue-level harness execution.
-5. `substrate-selection` decides which runtime sits behind the graph or harness boundary: OpenCode, claw-code, `pi`, aider, or another provider surface. Default integrated stack: `opencode` for the orchestrator lane, optional `pi` for a delegated external-harness lane, and `aider` for the leaf-agent lane. It also owns the rule that model/provider parity does not imply harness/runtime parity ╬ô├ç├╢ first-party surfaces like GitHub Copilot CLI may bundle stronger runtime guarantees that provider-routed OpenRouter stacks must recreate explicitly in skills/config.
+5. `substrate-selection` decides which runtime sits behind the graph or harness boundary: OpenCode, claw-code, `pi`, aider, or another provider surface. Default integrated stack: `opencode` for the orchestrator lane, optional `pi` for a delegated external-harness lane, and `aider` for the leaf-agent lane. It also owns the rule that model/provider parity does not imply harness/runtime parity ├óΓé¼ΓÇ¥ first-party surfaces like GitHub Copilot CLI may bundle stronger runtime guarantees that provider-routed OpenRouter stacks must recreate explicitly in skills/config.
 6. `agentic-harness` is the programmatic train station for coding frameworks (Claude Code, OpenCode, GitHub Copilot CLI, OpenClaw). It routes, gates, and reconciles work; each framework is a worker line, and the resolved runtime stack should be visible in state/logs rather than hidden in helper code.
 7. `continuity-log` is a child of `agentic-harness`. It holds the compact-safe distilled state that lets the harness resume without re-deriving decisions.
-8. `deep-research` is a child of `agentic-harness`. It decomposes a question into parallel subquestions, gathers web evidence via a 3-tier fetch pipeline (httpx ╬ô├Ñ├å retry ╬ô├Ñ├å Selenium), and synthesizes a claim-backed report seeding the harness TaskSpec.
+8. `deep-research` is a child of `agentic-harness`. It decomposes a question into parallel subquestions, gathers web evidence via a 3-tier fetch pipeline (httpx ├óΓÇáΓÇÖ retry ├óΓÇáΓÇÖ Selenium), and synthesizes a claim-backed report seeding the harness TaskSpec.
 9. `optuna-nested-cv` is now self-contained: the Methodology Primer (what to optimize, preconditions, layerwise decomp, structured search, sampler policy) was absorbed from `hyper-parm_tuning` (now superseded). `mlflow` records every run with lineage.
-10. `agentic_kg_memory` is the **CG (Context Graph) side** of the MCG architecture: semantic memory policy, patterns, tribal knowledge, retrieval. `kg_ontology` is the **DKG entity-identity layer**: synset/hypernym BM25 canonicalization that prevents duplicate nodes without graph topology traversal. They are complementary layers, not alternatives ╬ô├ç├╢ do not merge them again.
+10. `agentic_kg_memory` is the **CG (Context Graph) side** of the MCG architecture: semantic memory policy, patterns, tribal knowledge, retrieval. `kg_ontology` is the **DKG entity-identity layer**: synset/hypernym BM25 canonicalization that prevents duplicate nodes without graph topology traversal. They are complementary layers, not alternatives ├óΓé¼ΓÇ¥ do not merge them again.
 11. `gist-retriever` is the retrieval sub-skill for that memory layer. It spans the access-path progression from markdown/index-first lookup through local markdown search and into the full hybrid BM25+dense pipeline.
 12. `memory-bank` remains project operating memory, not compiled corpus memory. It stores project continuity while `agentic_kg_memory` stores evolving domain knowledge.
 13. The supplementary comparison boundary is now explicit in the repo: **RAG/retriever** behavior belongs in `gist-retriever`, **LLM Wiki/compiler** behavior belongs in `agentic_kg_memory`, and **GBrain/operator / fat-skills orchestration** belongs on the execution/orchestration side, not in the memory branch.
 14. KnowledgeWeaver is treated as a concrete implementation example of the compiler side: typed readable knowledge units plus a compiled index that can be rebuilt from canonical markdown artifacts.
 15. `agentic-harness` (waterfall -> agile: topics -> plans -> specs -> tasks) is the lifecycle template for skill authoring, not just software projects.
@@ -142,59 +144,59 @@ skills/
 17. `checklist` is a subskill of `agentic-harness`. It is the Pydantic-schema LLM-as-judge pattern: structured findings with novelty proofs, non-fatal execution, `review_required` flag, and cross-run fingerprinting via throughline Q-scores. Reference implementation: `gap_critic.py` in storywriter.
 18. `gist_correlation_matrix` is the "true GIST output": sorted correlation matrix as complete relational map (N^2 cells, each encoding pairwise relationship). Two sorting strategies: **orthogonal** (information-theoretic maximization, sharp drop-off) and **coverage** (hierarchical boundary exploration, expanding bands). Outputs: interactive HTMLs with full zoom/pan/hover.
 19. `spiral-radial-clustering-display` is the multi-dimensional hierarchical clustering visualization skill. Maps four layers (macro GMM + micro HDBSCAN + decorrelated ordering + hubness) into 3D feature space, projects via UMAP to 2D, encodes layers via Gestalt (position = spiral topology, color = macro, opacity = micro, size = centrality). Preserves topological structure and produces interactive Plotly HTML with full zoom/pan/hover metadata.
 20. `feature-catalog` is the local implementation ledger: a SQLite feature catalog for tracking what the project already ships and where it lives.
 21. `siamese_from_correlation_matrix` is the metric-learning companion to the embedding-analysis branch: it turns correlation structure into contrastive supervision.
-22. `skill-wiki` is the meta-skill governing the living skill library lifecycle. It owns the intake pipeline, promotion gates, supersession rules, sidecar conventions (EVIDENCE.md, HISTORY.md, scripts/ examples), and the periodic sweep that keeps skills consistent over time. It routes verified work chains into `crystallization` when the output is a digest, and handles staged skill-contract updates when the output is a library change. It is NOT memory storage (╬ô├Ñ├å `agentic_kg_memory`) and NOT project state (╬ô├Ñ├å `memory-bank`).
+22. `skill-wiki` is the meta-skill governing the living skill library lifecycle. It owns the intake pipeline, promotion gates, supersession rules, sidecar conventions (EVIDENCE.md, HISTORY.md, scripts/ examples), and the periodic sweep that keeps skills consistent over time. It routes verified work chains into `crystallization` when the output is a digest, and handles staged skill-contract updates when the output is a library change. It is NOT memory storage (├óΓÇáΓÇÖ `agentic_kg_memory`) and NOT project state (├óΓÇáΓÇÖ `memory-bank`).
 23. `documentation` decides which durable doc artifact to update: canonical README/spec, cumulative changelog, or a timestamped fixes-applied note.
 24. `response-style` governs user-facing prose: voice preservation, anti-cliche writing, and answer coherence. Harness-state coherence remains with `agentic-harness`.
-25. `class-balancing` is a general-purpose class weight protocol. It computes log inverse frequency per class, applies Box-Cox normalization to tame the distribution tail, clips negatives, and normalizes to ratios for use as `class_weight` in sklearn or `weight` in PyTorch CrossEntropyLoss. Used anywhere labeled data has heavy class imbalance ╬ô├ç├╢ layout element classification, NER, retrieval judgment labeling.
+25. `class-balancing` is a general-purpose class weight protocol. It computes log inverse frequency per class, applies Box-Cox normalization to tame the distribution tail, clips negatives, and normalizes to ratios for use as `class_weight` in sklearn or `weight` in PyTorch CrossEntropyLoss. Used anywhere labeled data has heavy class imbalance ├óΓé¼ΓÇ¥ layout element classification, NER, retrieval judgment labeling.
 25. `stratified-quota-sampling` owns fixed-budget coverage schedulers: Box-Cox tiering, quota allocation, and no-replacement sampling from an imbalanced pool. Pair it with `class-balancing` when quota selection alone still leaves residual label skew inside the loss, and with `optuna-nested-cv` when sample fraction, quota ratios, or tier weighting are part of the tuning contract.
-26. `pdf-extraction` is the end-to-end PDF╬ô├Ñ├åenriched-Markdown pipeline workflow: docling╬ô├Ñ├åbase64 strip╬ô├Ñ├åVLM image description╬ô├Ñ├åreinsert╬ô├Ñ├åmethods extraction (5 phases via `run_pipeline.bat`). Includes a table enhancement sub-pipeline: docling JSON bboxes╬ô├Ñ├åpymupdf crop╬ô├Ñ├åtabula+camelot extraction╬ô├Ñ├åVLM fusion╬ô├Ñ├åpatched Markdown. The layout classifier uses `class-balancing` for training. Standalone workflow skill; not a child of `agentic-harness`.
+26. `pdf-extraction` is the end-to-end PDF├óΓÇáΓÇÖenriched-Markdown pipeline workflow: docling├óΓÇáΓÇÖbase64 strip├óΓÇáΓÇÖVLM image description├óΓÇáΓÇÖreinsert├óΓÇáΓÇÖmethods extraction (5 phases via `run_pipeline.bat`). Includes a table enhancement sub-pipeline: docling JSON bboxes├óΓÇáΓÇÖpymupdf crop├óΓÇáΓÇÖtabula+camelot extraction├óΓÇáΓÇÖVLM fusion├óΓÇáΓÇÖpatched Markdown. The layout classifier uses `class-balancing` for training. Standalone workflow skill; not a child of `agentic-harness`.
 27. `openspec-workflow` is the spec-driven product/change lifecycle skill. Its companion action skills (`openspec-propose`, `openspec-explore`, `openspec-apply-change`, `openspec-archive-change`) are command-shaped entry points into the same OpenSpec operating model.
 28. `fabro-create-workflow` is the Fabro graph/run-config authoring companion. It can support `openspec-workflow` when a repo needs a new Fabro pipeline, but it is also usable as a standalone workflow-design skill.
 29. `agentic-harness` now has an explicit evaluation mix: `checklist` for structured audit artifacts, DSPy-derived metric/reward compile-refine patterns when scoring is explicit, and TextGrad-derived textual-loss loops when the critic must explain how to improve text/code/prompts. Optimizer scores inform repair; artifact-backed verification still decides completion.
 30. `codebase-knowledge-graph` is the current-repository relationship-mapping protocol. It builds the typed module/file/class/function graph and the foundational-vs-incidental distinction that should exist before `code`, `debugging`, or `validation` edits proceed.
-31. `code-extraction` extracts source files + configs from any project into a unified markdown artifact (docling-style: parse ╬ô├Ñ├å normalize ╬ô├Ñ├å markdown + JSON metadata). Supports multi-language detection (Python, Go, Rust, Swift, Java, JS/TS via markers or 8+ source files). Output feeds `codebase-knowledge-graph`, `documentation`, and LLM context assembly.
+31. `code-extraction` extracts source files + configs from any project into a unified markdown artifact (docling-style: parse ├óΓÇáΓÇÖ normalize ├óΓÇáΓÇÖ markdown + JSON metadata). Supports multi-language detection (Python, Go, Rust, Swift, Java, JS/TS via markers or 8+ source files). Output feeds `codebase-knowledge-graph`, `documentation`, and LLM context assembly.
 32. `diagnostic-scanner` invokes language-appropriate tools (mypy/pylint, go vet, cargo check, swiftc, eslint, etc.) and normalizes errors/warnings by severity and category. Produces fix prompts ready for LLM remediation. Output feeds `validation` and `code` for structured violation handling.
 33. `model-size-reduction` owns post-training checkpoint reduction: dtype casting, layer dropping, LoRA extraction, and DARE/TIES/DELLA sparsification directly against Hugging Face `state_dict`s. `continual-learning` still owns DARE as a lifelong-learning merge pattern; use `model-size-reduction` when the goal is footprint, portability, or architecture-agnostic checkpoint surgery.
 34. `generalization-theory` is the training-dynamics diagnostic lens for signal-vs-noise partitioning, grokking delay, and noisy-preference memorization. It helps choose intervention surfaces across data, architecture, and optimizer design, but it does not own the tuning/search loop (`optuna-nested-cv`) or long-horizon forgetting control (`continual-learning`).
-35. `test-planner` generates coverage-aware test plans with status flags (Γëí╞Æ╞Æ├│ GREEN=DONE, Γëí╞Æ╞Æ├¡ YELLOW=PARTIAL, Γëí╞Æ├╢Γöñ RED=MISSING). Proposes concrete scenarios by test level (smoke/unit/integration/e2e/regression) and detects regression subjects via git diff. Output feeds `tdd-agent` for test-driven implementation and `validation` for coverage verification.
+35. `test-planner` generates coverage-aware test plans with status flags (├░┼╕┼╕┬ó GREEN=DONE, ├░┼╕┼╕┬í YELLOW=PARTIAL, ├░┼╕ΓÇ¥┬┤ RED=MISSING). Proposes concrete scenarios by test level (smoke/unit/integration/e2e/regression) and detects regression subjects via git diff. Output feeds `tdd-agent` for test-driven implementation and `validation` for coverage verification.
 36. `doc-synthesizer` parses project structure via AST (Python focus; all languages via markers), builds dependency graphs, and generates Mermaid diagrams for module dependencies and data flow. Output feeds `documentation`, `codebase-knowledge-graph`, and architecture review. URI fetch/crawl extensible for Phase 2.
 37. `build-observability` is the run-centric observability layer for agentic execution. `agentic-harness` owns control flow and retries; `build-observability` projects runtime exhaust into normalized `runs/events/commands` records and operator-facing dashboard views.
-38. `react-fastapi-sqlite` is the full-stack application scaffold skill: React frontend (with TanStack Query for server-state caching), FastAPI backend (with SQLModel ORM layer), and SQLite file-based database. Use when building SPAs with Python REST backends, configuring client-side data fetching and invalidation patterns, or structuring domain-driven CRUD operations. Output: production-ready project layout with separation of concerns (api/ ╬ô├Ñ├å hooks/ ╬ô├Ñ├å pages/components/ hierarchy). Integrates with `code` for implementation standards and `validation` for integration testing.
-39. `git-workflow` is the branch strategy and LLM safety protocol for this repository. Enforces test╬ô├Ñ├ådev╬ô├Ñ├åmain push gates, requires LLM verification against last known working commit before each push, and pairs `code` verification (git diff checks) with `headless-browser-verification` screenshots for web frontend changes. Prevents accidental pushes to main by requiring explicit user approval at each stage.
+38. `react-fastapi-sqlite` is the full-stack application scaffold skill: React frontend (with TanStack Query for server-state caching), FastAPI backend (with SQLModel ORM layer), and SQLite file-based database. Use when building SPAs with Python REST backends, configuring client-side data fetching and invalidation patterns, or structuring domain-driven CRUD operations. Output: production-ready project layout with separation of concerns (api/ ├óΓÇáΓÇÖ hooks/ ├óΓÇáΓÇÖ pages/components/ hierarchy). Integrates with `code` for implementation standards and `validation` for integration testing.
+39. `git-workflow` is the branch strategy and LLM safety protocol for this repository. Enforces test├óΓÇáΓÇÖdev├óΓÇáΓÇÖmain push gates, requires LLM verification against last known working commit before each push, and pairs `code` verification (git diff checks) with `headless-browser-verification` screenshots for web frontend changes. Prevents accidental pushes to main by requiring explicit user approval at each stage.

 40. `cognitive-taxonomy` is the **reference skill for all memory decisions**. It synthesizes four peer-reviewed papers into a unified classification system: implicit/explicit/agentic paradigms, forms/functions/dynamics taxonomy, biological-artificial crosswalk, and neuro-symbolic System 1 vs System 2 dual-process reasoning. Use it to classify memory patterns, route queries correctly, diagnose underperformance (why is vector-only failing?), and design new memory architectures. It's a pure reference skill (no code changes) that sits above all memory subsystems (`agentic_kg_memory`, `procedural-memory`, `continuity-log`, `context-compaction`).

-41. `memory-architecture` is the **canonical design reference for agent memory systems**. Implements the Meta Context Graph layered stack with 4 concrete templates: (1) factual knowledge base (Implicit╬ô├Ñ├åExplicit╬ô├Ñ├åWorking), (2) personal assistant with memory (adds Episodic), (3) autonomous agent (adds Procedural), (4) research/knowledge synthesis pipeline. Each template includes full 5-layer architecture, entity anchor flow, procedure discovery flow, query routing lifecycle, and anti-patterns. Use when designing a new agent with memory, evaluating existing systems for gaps, onboarding developers. Depends on `cognitive-taxonomy` for classification; feeds into `procedural-memory`, `agentic_kg_memory`, `context-compaction` for implementation.
+41. `memory-architecture` is the **canonical design reference for agent memory systems**. Implements the Meta Context Graph layered stack with 4 concrete templates: (1) factual knowledge base (Implicit├óΓÇáΓÇÖExplicit├óΓÇáΓÇÖWorking), (2) personal assistant with memory (adds Episodic), (3) autonomous agent (adds Procedural), (4) research/knowledge synthesis pipeline. Each template includes full 5-layer architecture, entity anchor flow, procedure discovery flow, query routing lifecycle, and anti-patterns. Use when designing a new agent with memory, evaluating existing systems for gaps, onboarding developers. Depends on `cognitive-taxonomy` for classification; feeds into `procedural-memory`, `agentic_kg_memory`, `context-compaction` for implementation.

 42. `validation-artifacts` enforces the principle **"seeing is believing"** by making validation proof mandatory, not optional. Before any skill claims "validation passed", this skill demands reproducible artifacts: training loss curves + eval metrics on holdout sets, predictions + confusion matrices, test execution logs with exit codes, before/after screenshots + visual diffs, API request/response samples + latency profiles, script execution examples with outputs. Used by `validation`, `checklist`, `tdd-agent`, `debugging`, `git-workflow` to prevent "trust me" claims. Integrates with `headless-browser-verification` (UI artifacts) and `security-review` (security validation artifacts).

-43. `skill-sync` is the **LLM-assisted merge protocol for diverged skill copies** across master and local/remote mirrors. Distinct from `skill-wiki` (governance: intake/staging/lifecycle) ╬ô├ç├╢ `skill-sync` is operational: when both master and a mirror have independently changed since the last commit, it classifies the case (no-op / fast-forward / conflict), applies deterministic fast-forwards automatically, and routes true conflicts to an LLM merge that incorporates both sets of changes without dropping content from either side. Mechanically executed by `sync_skills.ps1`. MERGE-CONFLICT markers flag unresolved sections for human review before commit.
+43. `skill-sync` is the **LLM-assisted merge protocol for diverged skill copies** across master and local/remote mirrors. Distinct from `skill-wiki` (governance: intake/staging/lifecycle) ├óΓé¼ΓÇ¥ `skill-sync` is operational: when both master and a mirror have independently changed since the last commit, it classifies the case (no-op / fast-forward / conflict), applies deterministic fast-forwards automatically, and routes true conflicts to an LLM merge that incorporates both sets of changes without dropping content from either side. Mechanically executed by `sync_skills.ps1`. MERGE-CONFLICT markers flag unresolved sections for human review before commit.

-44. `consolidation` is the **triplet-based document consolidation pipeline** for living knowledge bases and skill libraries. Extracts subject-predicate-object triplets from each document, computes a pairwise Jaccard similarity matrix (or NLI-based soft Jaccard for semantic matching), runs **greedy nearest-neighbor chain decomposition** (single-linkage chaining) to group related documents, and emits a sorted report with prescriptions: MERGE (╬ô├½├æ0.8), migrate (0.5╬ô├ç├┤0.8), xref (0.3╬ô├ç├┤0.5). Groups are sorted by chain length descending ╬ô├ç├╢ largest clusters first. Sits above `gist_correlation_matrix` (matrix builder) and feeds prescriptions into `skill-wiki` (governance) and `skill-sync` (mechanical merge). Use when the library has grown by ╬ô├½├æ5 new entries, semantic search returns contradictory results, or a scheduled consolidation run is due.
+44. `consolidation` is the **triplet-based document consolidation pipeline** for living knowledge bases and skill libraries. Extracts subject-predicate-object triplets from each document, computes a pairwise Jaccard similarity matrix (or NLI-based soft Jaccard for semantic matching), runs **greedy nearest-neighbor chain decomposition** (single-linkage chaining) to group related documents, and emits a sorted report with prescriptions: MERGE (├óΓÇ░┬Ñ0.8), migrate (0.5├óΓé¼ΓÇ£0.8), xref (0.3├óΓé¼ΓÇ£0.5). Groups are sorted by chain length descending ├óΓé¼ΓÇ¥ largest clusters first. Sits above `gist_correlation_matrix` (matrix builder) and feeds prescriptions into `skill-wiki` (governance) and `skill-sync` (mechanical merge). Use when the library has grown by ├óΓÇ░┬Ñ5 new entries, semantic search returns contradictory results, or a scheduled consolidation run is due.

-45. `nearest-neighbor-chain` is the **greedy path-cover chain decomposition sub-skill** shared by `consolidation` and any other consumer that needs to partition a similarity matrix into semantic groups. It walks pairs sorted by descending score, extends only chain endpoints (no branching), and emits variable-length chains sorted by length descending. Singletons are docs with no above-Γòº├ñ neighbours. The "chaining effect" of single-linkage is intentional: each chain is a semantic thread; a chain break is a topic boundary. `gist_correlation_matrix` produces the matrix; `nearest-neighbor-chain` decomposes it; `consolidation` adds triplet extraction and MERGE/migrate/xref prescriptions on top.
+45. `nearest-neighbor-chain` is the **greedy path-cover chain decomposition sub-skill** shared by `consolidation` and any other consumer that needs to partition a similarity matrix into semantic groups. It walks pairs sorted by descending score, extends only chain endpoints (no branching), and emits variable-length chains sorted by length descending. Singletons are docs with no above-├ÅΓÇ₧ neighbours. The "chaining effect" of single-linkage is intentional: each chain is a semantic thread; a chain break is a topic boundary. `gist_correlation_matrix` produces the matrix; `nearest-neighbor-chain` decomposes it; `consolidation` adds triplet extraction and MERGE/migrate/xref prescriptions on top.

-46. `prompt-optimization` is the **automatic prompt self-improvement skill**. A child of `evaluator-optimizer` that applies optimization algorithms ╬ô├ç├╢ not manual rewriting. Labeled trainset + multi-step ╬ô├Ñ├å DSPy MIPROv2 (Bayesian joint instruction+demo search). No trainset + differentiable loss ╬ô├Ñ├å TextGrad (text-space gradient descent). Demos only ╬ô├Ñ├å APE. Single instruction ╬ô├Ñ├å OPRO. `agentic-harness` invokes this when a module's loss metric is stable but prompt quality is the bottleneck. Absorbs `integrate/dspy.md` and `integrate/textgrad.md`.
+46. `prompt-optimization` is the **automatic prompt self-improvement skill**. A child of `evaluator-optimizer` that applies optimization algorithms ├óΓé¼ΓÇ¥ not manual rewriting. Labeled trainset + multi-step ├óΓÇáΓÇÖ DSPy MIPROv2 (Bayesian joint instruction+demo search). No trainset + differentiable loss ├óΓÇáΓÇÖ TextGrad (text-space gradient descent). Demos only ├óΓÇáΓÇÖ APE. Single instruction ├óΓÇáΓÇÖ OPRO. `agentic-harness` invokes this when a module's loss metric is stable but prompt quality is the bottleneck. Absorbs `integrate/dspy.md` and `integrate/textgrad.md`.

-47. `uncertainty-quantification` is the **LLM output confidence protocol**. A child of `validation` for measuring when a model knows vs. doesn't know. Three-tier protocol: Tier 1 = fast (logprobs/verbal, <0.1s), Tier 2 = standard (N=3╬ô├ç├┤5 consistency samples), Tier 3 = thorough (N╬ô├½├æ10 + conformal prediction). Semantic entropy (arXiv:2302.09664) outperforms token-level entropy. Always use Tier 3 minimum for irreversible actions. Libraries: `selfcheckgpt`, `lm-polygraph`. Feeds `checklist` for audit trails and `uncertainty-quantification` threshold gates in `agent-governance`.
+47. `uncertainty-quantification` is the **LLM output confidence protocol**. A child of `validation` for measuring when a model knows vs. doesn't know. Three-tier protocol: Tier 1 = fast (logprobs/verbal, <0.1s), Tier 2 = standard (N=3├óΓé¼ΓÇ£5 consistency samples), Tier 3 = thorough (N├óΓÇ░┬Ñ10 + conformal prediction). Semantic entropy (arXiv:2302.09664) outperforms token-level entropy. Always use Tier 3 minimum for irreversible actions. Libraries: `selfcheckgpt`, `lm-polygraph`. Feeds `checklist` for audit trails and `uncertainty-quantification` threshold gates in `agent-governance`.

-48. `causal-inference` is the **LLM╬ô├Ñ├åDoWhy╬ô├Ñ├åLLM causal reasoning chain**. A child of `reasoning`. LLMs hallucinate on formal do-calculus (near-random; arXiv:2306.05836) ╬ô├ç├╢ all estimation routes through DoWhy, not the LLM. Three-phase protocol: LLM proposes DAG ╬ô├Ñ├å causal-learn validates (PC/FCI/GES) ╬ô├Ñ├å DoWhy identifies+estimates. LLM only interprets results. Counterfactual queries use `dowhy.counterfactual_outcomes`. Libraries: `dowhy`, `causal-learn`, `econml`, `pywhy-llm` (experimental).
+48. `causal-inference` is the **LLM├óΓÇáΓÇÖDoWhy├óΓÇáΓÇÖLLM causal reasoning chain**. A child of `reasoning`. LLMs hallucinate on formal do-calculus (near-random; arXiv:2306.05836) ├óΓé¼ΓÇ¥ all estimation routes through DoWhy, not the LLM. Three-phase protocol: LLM proposes DAG ├óΓÇáΓÇÖ causal-learn validates (PC/FCI/GES) ├óΓÇáΓÇÖ DoWhy identifies+estimates. LLM only interprets results. Counterfactual queries use `dowhy.counterfactual_outcomes`. Libraries: `dowhy`, `causal-learn`, `econml`, `pywhy-llm` (experimental).

-49. `synthetic-data` is the **LLM-generated training data pipeline**. A child of `stratified-quota-sampling`. Eight paradigms ordered by fidelity: Self-Instruct ╬ô├Ñ├å Evol-Instruct ╬ô├Ñ├å GLAN ╬ô├Ñ├å Magpie ╬ô├Ñ├å Self-Play ╬ô├Ñ├å Persona-driven ╬ô├Ñ├å Task-specific ╬ô├Ñ├å Preference. Six mandatory quality gates in order: dedup ╬ô├Ñ├å schema ╬ô├Ñ├å LLM judge ╬ô├Ñ├å IFD ╬ô├Ñ├å coverage ╬ô├Ñ├å safety. Model collapse risk (arXiv:2305.17493): requires a strong fixed teacher (GPT-4/Llama-3-70B), never train-on-own-outputs without mixing real data. Clean three-stage handoff: `synthetic-data` ╬ô├Ñ├å `stratified-quota-sampling` ╬ô├Ñ├å `class-balancing`. Library: `argilla-io/distilabel`.
+49. `synthetic-data` is the **LLM-generated training data pipeline**. A child of `stratified-quota-sampling`. Eight paradigms ordered by fidelity: Self-Instruct ├óΓÇáΓÇÖ Evol-Instruct ├óΓÇáΓÇÖ GLAN ├óΓÇáΓÇÖ Magpie ├óΓÇáΓÇÖ Self-Play ├óΓÇáΓÇÖ Persona-driven ├óΓÇáΓÇÖ Task-specific ├óΓÇáΓÇÖ Preference. Six mandatory quality gates in order: dedup ├óΓÇáΓÇÖ schema ├óΓÇáΓÇÖ LLM judge ├óΓÇáΓÇÖ IFD ├óΓÇáΓÇÖ coverage ├óΓÇáΓÇÖ safety. Model collapse risk (arXiv:2305.17493): requires a strong fixed teacher (GPT-4/Llama-3-70B), never train-on-own-outputs without mixing real data. Clean three-stage handoff: `synthetic-data` ├óΓÇáΓÇÖ `stratified-quota-sampling` ├óΓÇáΓÇÖ `class-balancing`. Library: `argilla-io/distilabel`.

-50. `continual-learning` is the **non-forgetting agent training protocol**. Sits in `learning/` alongside `deep-q-rl`. Prevents catastrophic forgetting when a model must learn a new task without erasing prior skills. Six approaches by compute budget: EWC (regularization, cheapest) ╬ô├Ñ├å LwF (distillation) ╬ô├Ñ├å GEM/A-GEM (episodic memory constraint) ╬ô├Ñ├å PackNet (parameter isolation) ╬ô├Ñ├å O-LoRA/InfLoRA (LoRA orthogonalization) ╬ô├Ñ├å MemRL (frozen backbone + episodic Q-value memory, ICML 2026). `procedural-memory` EMA (Γò¼Γûô=0.9) is intentionally aligned with single-sample EWC. Absorbs `integrate/MemRL` (arXiv:2601.03192). Libraries: Avalanche, Mammoth, HuggingFace PEFT.
+50. `continual-learning` is the **non-forgetting agent training protocol**. Sits in `learning/` alongside `deep-q-rl`. Prevents catastrophic forgetting when a model must learn a new task without erasing prior skills. Six approaches by compute budget: EWC (regularization, cheapest) ├óΓÇáΓÇÖ LwF (distillation) ├óΓÇáΓÇÖ GEM/A-GEM (episodic memory constraint) ├óΓÇáΓÇÖ PackNet (parameter isolation) ├óΓÇáΓÇÖ O-LoRA/InfLoRA (LoRA orthogonalization) ├óΓÇáΓÇÖ MemRL (frozen backbone + episodic Q-value memory, ICML 2026). `procedural-memory` EMA (├Ä┬▓=0.9) is intentionally aligned with single-sample EWC. Absorbs `integrate/MemRL` (arXiv:2601.03192). Libraries: Avalanche, Mammoth, HuggingFace PEFT.

-51. `program-synthesis` is the **formal verification + proof-assisted coding skill**. A child of `tdd-agent` ╬ô├ç├╢ `tdd-agent` escalates here when the property is unbounded, security-critical, or requires exhaustive correctness guarantees. AutoVerus (arXiv:2409.13082): 91.3% on 150 Verus tasks using GPT-4o + Rust ghost code, ~$37 total. EvalPlus (arXiv:2305.01210): pass@k drops 19╬ô├ç├┤28% with exhaustive testing vs. HumanEval ╬ô├ç├╢ all `tdd-agent` benchmarks should use EvalPlus. Three-phase loop: generate ╬ô├Ñ├å verify (formal checker) ╬ô├Ñ├å repair (RLEF feedback). Integration: `tdd-agent` handles empirical tests; `program-synthesis` handles formal properties.
+51. `program-synthesis` is the **formal verification + proof-assisted coding skill**. A child of `tdd-agent` ├óΓé¼ΓÇ¥ `tdd-agent` escalates here when the property is unbounded, security-critical, or requires exhaustive correctness guarantees. AutoVerus (arXiv:2409.13082): 91.3% on 150 Verus tasks using GPT-4o + Rust ghost code, ~$37 total. EvalPlus (arXiv:2305.01210): pass@k drops 19├óΓé¼ΓÇ£28% with exhaustive testing vs. HumanEval ├óΓé¼ΓÇ¥ all `tdd-agent` benchmarks should use EvalPlus. Three-phase loop: generate ├óΓÇáΓÇÖ verify (formal checker) ├óΓÇáΓÇÖ repair (RLEF feedback). Integration: `tdd-agent` handles empirical tests; `program-synthesis` handles formal properties.

-52. `active-inference` is the **Bayesian POMDP agent skill** based on the Free Energy Principle. Sits in `learning/` as a complement to `deep-q-rl`, not a replacement. Use when: partial observability (can't see full state), no clean scalar reward (prefer EFE preferences), principled tool selection (epistemic value drives info-gathering before committing to action). EFE decomposes into epistemic value (info gain) + pragmatic value (reach preferred obs) ╬ô├ç├╢ no reward design needed. Russian Doll MCTS ╬ô├½├¬ Sophisticated Inference: both use tree search; EFE replaces Q-value as node score. Library: `inferactively-pymdp`. Use `deep-q-rl` when full observability + `evaluate(state)` exists.
+52. `active-inference` is the **Bayesian POMDP agent skill** based on the Free Energy Principle. Sits in `learning/` as a complement to `deep-q-rl`, not a replacement. Use when: partial observability (can't see full state), no clean scalar reward (prefer EFE preferences), principled tool selection (epistemic value drives info-gathering before committing to action). EFE decomposes into epistemic value (info gain) + pragmatic value (reach preferred obs) ├óΓé¼ΓÇ¥ no reward design needed. Russian Doll MCTS ├óΓÇ░╦å Sophisticated Inference: both use tree search; EFE replaces Q-value as node score. Library: `inferactively-pymdp`. Use `deep-q-rl` when full observability + `evaluate(state)` exists.

-53. `median-bifurcation` is the **universal median-cut discriminative signal skill**. Any useful distinction a model or system must learn is a binary median cut. Three-step protocol: choose partition axis ╬ô├Ñ├å produce both sides explicitly (hard negatives baked in, not mined post-hoc) ╬ô├Ñ├å drop unwanted partition at inference. Applied recursively, n bifurcations yield 2^n epistemic cells at zero additional labeling cost. This is data-level contrastive learning: the loss sees ordinary cross-entropy; discriminative pressure comes from the data layout. Inspired by ANOVA factorial designs and k-means via median divisions. `mad-dynamic-batching` is a concrete instantiation for token-length distributions.
+53. `median-bifurcation` is the **universal median-cut discriminative signal skill**. Any useful distinction a model or system must learn is a binary median cut. Three-step protocol: choose partition axis ├óΓÇáΓÇÖ produce both sides explicitly (hard negatives baked in, not mined post-hoc) ├óΓÇáΓÇÖ drop unwanted partition at inference. Applied recursively, n bifurcations yield 2^n epistemic cells at zero additional labeling cost. This is data-level contrastive learning: the loss sees ordinary cross-entropy; discriminative pressure comes from the data layout. Inspired by ANOVA factorial designs and k-means via median divisions. `mad-dynamic-batching` is a concrete instantiation for token-length distributions.

-## MCG Foundation ╬ô├ç├╢ The Conceptual Backbone
+## MCG Foundation ├óΓé¼ΓÇ¥ The Conceptual Backbone

 The skill library is an implementation of the **Meta Context Graph (MCG)** architecture
 (Tekiner, 2025; Hu et al. arXiv:2512.13564) applied to automated software development.
 MCG is the glue that ties gstack (fat operational patterns) to llm-wiki (compiled living
 knowledge): both are instantiated here as the skills themselves (procedural memory) and
@@ -202,29 +204,29 @@ the Pattern Store vetting pipeline (tribal knowledge lifecycle).

 The full MCG system comprises two complementary graphs:

 | MCG Component | Software Dev Equivalent | Skill |
 |---|---|---|
-| Domain KG ╬ô├ç├╢ entities & relationships | Codebase / domain model | `agentic_kg_memory` + `kg_ontology` |
+| Domain KG ├óΓé¼ΓÇ¥ entities & relationships | Codebase / domain model | `agentic_kg_memory` + `kg_ontology` |
 | DKG entity identity layer | Symbol/module canonicalization | `kg_ontology` |
-| Context Graph ╬ô├ç├╢ decision traces (episodic) | learnings.jsonl, per-task rationale | `agentic-harness` |
-| CG patterns (semantic) | Pattern Store pending ╬ô├Ñ├å tenure | `skill-wiki` |
-| CG tribal knowledge (semantic) | Pattern Store promoted entries | `skill-wiki` ╬ô├Ñ├å skill files |
-| CG procedural schemas | **The SKILL.md files themselves** ╬ô├ç├╢ model-agnostic, slot-in primitives | This whole library |
+| Context Graph ├óΓé¼ΓÇ¥ decision traces (episodic) | learnings.jsonl, per-task rationale | `agentic-harness` |
+| CG patterns (semantic) | Pattern Store pending ├óΓÇáΓÇÖ tenure | `skill-wiki` |
+| CG tribal knowledge (semantic) | Pattern Store promoted entries | `skill-wiki` ├óΓÇáΓÇÖ skill files |
+| CG procedural schemas | **The SKILL.md files themselves** ├óΓé¼ΓÇ¥ model-agnostic, slot-in primitives | This whole library |
 | L4 Runtime state | Session / active context | `continuity-log`, `memory-bank` |
 | L3 Organisation conventions | Team / project norms | `memory-bank` project brief |
 | L2 Industry / domain | Domain KG per project | `agentic_kg_memory` |
 | L1 Universal best practices | Base skill library | This repo |

 **The skills are procedural memory** (CoALA taxonomy, arXiv:2309.02427). They cannot be
-summarized into a prompt and RAG-retrieved with equal effect ╬ô├ç├╢ they must be invoked. This
+summarized into a prompt and RAG-retrieved with equal effect ├óΓé¼ΓÇ¥ they must be invoked. This
 is the distinction between a great chef's accumulated technique and a recipe book. The
-Pattern Store vetting pipeline (3 applications ╬ô├Ñ├å promote) implements the tribal knowledge
-lifecycle from MCG: `tk_candidates` ╬ô├Ñ├å reviewed ╬ô├Ñ├å `tribal_knowledge` (active rule) ╬ô├Ñ├å
+Pattern Store vetting pipeline (3 applications ├óΓÇáΓÇÖ promote) implements the tribal knowledge
+lifecycle from MCG: `tk_candidates` ├óΓÇáΓÇÖ reviewed ├óΓÇáΓÇÖ `tribal_knowledge` (active rule) ├óΓÇáΓÇÖ
 compiled into a skill.

-For the full architecture, see `agentic_kg_memory/SKILL.md Γö¼┬║ MCG Foundation`.
+For the full architecture, see `agentic_kg_memory/SKILL.md ├é┬º MCG Foundation`.

 ## Repository Layout

 - `<skill>\\SKILL.md` -> canonical skill contract
 - `copilot-instructions.md` -> repo-wide Copilot guidance
@@ -257,14 +259,14 @@ For the full architecture, see `agentic_kg_memory/SKILL.md Γö¼┬║ MCG Foundation`

 Use this README as the live-skill audit source of truth for the concepts that were still unresolved in `integrate/compiled.md`. They are now fully dispositioned through promotion into the live graph or explicit absorption into existing skills.

 | `integrate/compiled.md` concept | Live disposition |
 |---|---|
-| `build-observability` | **live skill** ╬ô├Ñ├å `build-observability` |
-| `codebase-knowledge-graph` | **live skill** ╬ô├Ñ├å `codebase-knowledge-graph` |
-| `fat-skills` | **closed by absorption** ╬ô├Ñ├å `skill-wiki` + `agentic-harness` + repo routing guidance + memory / governance split |
-| `dev-pipeline` | **closed by absorption** ╬ô├Ñ├å `react-agent` + `openspec-workflow` + execution skills + `agentic-harness` + supporting release / safety lanes |
+| `build-observability` | **live skill** ├óΓÇáΓÇÖ `build-observability` |
+| `codebase-knowledge-graph` | **live skill** ├óΓÇáΓÇÖ `codebase-knowledge-graph` |
+| `fat-skills` | **closed by absorption** ├óΓÇáΓÇÖ `skill-wiki` + `agentic-harness` + repo routing guidance + memory / governance split |
+| `dev-pipeline` | **closed by absorption** ├óΓÇáΓÇÖ `react-agent` + `openspec-workflow` + execution skills + `agentic-harness` + supporting release / safety lanes |

 ## Design Principles

 - Skills should be composable rather than monolithic.
 - Policy, implementation, and tracking should be separated when they have different responsibilities.
@@ -276,17 +278,17 @@ Use this README as the live-skill audit source of truth for the concepts that we
 ## Living Skill Library

 Skills compound over time. Each skill accumulates evidence (EVIDENCE.md) and changelog history (HISTORY.md) alongside its behavioral contract (SKILL.md). The governance lifecycle is:

 ```
-integrate/          ╬ô├Ñ├ë raw intake (awesome-copilot, gstack, llm-wiki, etc.)
-integrate/staged/   ╬ô├Ñ├ë validated concepts awaiting promotion
-<skill>/SKILL.md    ╬ô├Ñ├ë active behavioral contract (status: active)
-<superseded>        ╬ô├Ñ├ë retired skills (status: superseded, superseded_by: <name>)
+integrate/          ├óΓÇá┬É raw intake (awesome-copilot, gstack, llm-wiki, etc.)
+integrate/staged/   ├óΓÇá┬É validated concepts awaiting promotion
+<skill>/SKILL.md    ├óΓÇá┬É active behavioral contract (status: active)
+<superseded>        ├óΓÇá┬É retired skills (status: superseded, superseded_by: <name>)
 ```

-Promotion gate: one Tier-1/2 evidence item + one local validation, OR two independent Tier-1╬ô├ç├┤3 items from distinct source types. See `skill-wiki/SKILL.md` for the full governance contract.
+Promotion gate: one Tier-1/2 evidence item + one local validation, OR two independent Tier-1├óΓé¼ΓÇ£3 items from distinct source types. See `skill-wiki/SKILL.md` for the full governance contract.

 SKILL.md frontmatter fields:
 ```yaml
 status: active          # raw | staged | active | superseded
 last_validated: YYYY-MM-DD
@@ -328,11 +330,11 @@ This library is optimized for automated software development. Skill-to-pipeline
 | Context window management and compaction | `context-compaction` |
 | MCP tool registration and routing | `mcp-tool-registry` |
 | Offline batch eval, regression detection | `checklist` (eval-pipeline section) |
 | Hyperparameter search / training | `optuna-nested-cv`, `mlflow` |
 | Imbalanced classifier class weights | `class-balancing` |
-| PDF╬ô├Ñ├åenriched-Markdown pipeline | `pdf-extraction` |
+| PDF├óΓÇáΓÇÖenriched-Markdown pipeline | `pdf-extraction` |
 | Semantic knowledge retrieval | `agentic_kg_memory`, `gist-retriever` |
 | Cross-session episodic recall | `agentic_kg_memory` (episodic section) |
 | RL from code execution feedback | `deep-q-rl` (code-rl section) |
 | SPO / DPO / offline preference optimization | `deep-q-rl` (SPO section) |
 | Reward function design, binary vs graded rewards | `deep-q-rl` (SPO section) |
@@ -346,31 +348,31 @@ This library is optimized for automated software development. Skill-to-pipeline
 - **2026-05-09**: Promoted `crystallization` into a standalone live skill. `skill-wiki` now owns routing and staged skill-library deltas, `crystallization` owns the actual work-chain distillation protocol, and `agentic_kg_memory` owns digest ingestion and graph updates.
 - **2026-05-02**: Promoted `build-observability` and `codebase-knowledge-graph` from unresolved `integrate/compiled.md` concepts into live skills. `build-observability` now owns the normalized `runs/events/commands` observability contract and projection/dashboard pattern; `codebase-knowledge-graph` now owns current-repo whole-system mapping, foundational-vs-incidental classification, and ripple analysis before edits.
 - **2026-05-09**: Imported `model-size-reduction` and `generalization-theory` from the local research/wiki intake. `model-size-reduction` now owns architecture-agnostic Hugging Face checkpoint slimming and delta sparsification; `generalization-theory` now owns the eNTK signal-vs-noise diagnostic lens for memorization, grokking, and noisy-preference fine-tuning.
 - **2026-05-02**: Explicitly closed the `fat-skills` and `dev-pipeline` umbrella concepts by absorption rather than promotion. `fat-skills` is now documented as split across `skill-wiki`, `agentic-harness`, repo-level routing guidance, and the existing memory / governance surfaces; `dev-pipeline` is documented as split across `react-agent`, `openspec-workflow`, the execution skills, and `agentic-harness`.
 - **2026-05-02**: Grounded the `agentic-harness` evaluation lane in `DSPy` and `TextGrad`. Added `integrate/dspy.md` and `integrate/textgrad.md`, extended `integrate/compiled.md` with `optimizer-driven-evaluation`, and updated the live `agentic-harness` skill to distinguish structured audit (`checklist`) from metric/reward compile-refine loops (DSPy) and textual-loss refinement loops (TextGrad).
-- **2026-05-02**: Added `class-balancing` (log inverse freq ╬ô├Ñ├å Box-Cox ╬ô├Ñ├å ratio weights for imbalanced classifiers) and `pdf-extraction` (full docling pipeline + table enhancement via tabula+camelot+VLM fusion). `hyper-parm_tuning` now frames Weighted Stage Allocation as the canonical cross-skill pattern; `agentic-hyperparm` is the agent-specific instantiation. `arxiv-bridge` was updated with CLI flags and a sequential-only warning.
+- **2026-05-02**: Added `class-balancing` (log inverse freq ├óΓÇáΓÇÖ Box-Cox ├óΓÇáΓÇÖ ratio weights for imbalanced classifiers) and `pdf-extraction` (full docling pipeline + table enhancement via tabula+camelot+VLM fusion). `hyper-parm_tuning` now frames Weighted Stage Allocation as the canonical cross-skill pattern; `agentic-hyperparm` is the agent-specific instantiation. `arxiv-bridge` was updated with CLI flags and a sequential-only warning.
 - Imported the portable OpenSpec/Fabro skill family as live agent skills: `openspec-workflow`, `openspec-propose`, `openspec-explore`, `openspec-apply-change`, `openspec-archive-change`, and `fabro-create-workflow`. Current rollout is agent-only first; any dark-factory pipeline promotion remains a separate second pass.
-- **Wave 3 Pareto additions** (Tier 3, scores 6╬ô├ç├┤9): `autoresearch` (new skill); `context-engineering` section ╬ô├Ñ├å `code`; `eval-pipeline` section ╬ô├Ñ├å `checklist`; `agent-as-ci-gate` full protocol ╬ô├Ñ├å `agent-governance`; `code-rl` section ╬ô├Ñ├å `deep-q-rl`. All 15 Pareto candidates now implemented.
+- **Wave 3 Pareto additions** (Tier 3, scores 6├óΓé¼ΓÇ£9): `autoresearch` (new skill); `context-engineering` section ├óΓÇáΓÇÖ `code`; `eval-pipeline` section ├óΓÇáΓÇÖ `checklist`; `agent-as-ci-gate` full protocol ├óΓÇáΓÇÖ `agent-governance`; `code-rl` section ├óΓÇáΓÇÖ `deep-q-rl`. All 15 Pareto candidates now implemented.
 - **Super System Prompt extraction finished**: added `documentation` (timestamped-vs-cumulative doc strategy) and `response-style` (voice preservation, anti-cliche prose, user-facing coherence).
-- **Wave 2 Pareto additions** (Tier 2, scores 12╬ô├ç├┤16): `context-compaction`, `security-review`, `mcp-tool-registry` (new skills); `self-repair` section ╬ô├Ñ├å `debugging`; `hierarchical-task-planning` section ╬ô├Ñ├å `agentic-harness`; `episodic-memory` section ╬ô├Ñ├å `agentic_kg_memory`.
-- **Wave 1 Pareto additions** (Tier 1, all score ╬ô├½├æ 20): `evaluator-optimizer`, `multi-agent-coordination`, `tdd-agent`, `agent-governance`. Fills the largest gaps: iterative generation loop, team topology, test-first lifecycle, and safety rails.
+- **Wave 2 Pareto additions** (Tier 2, scores 12├óΓé¼ΓÇ£16): `context-compaction`, `security-review`, `mcp-tool-registry` (new skills); `self-repair` section ├óΓÇáΓÇÖ `debugging`; `hierarchical-task-planning` section ├óΓÇáΓÇÖ `agentic-harness`; `episodic-memory` section ├óΓÇáΓÇÖ `agentic_kg_memory`.
+- **Wave 1 Pareto additions** (Tier 1, all score ├óΓÇ░┬Ñ 20): `evaluator-optimizer`, `multi-agent-coordination`, `tdd-agent`, `agent-governance`. Fills the largest gaps: iterative generation loop, team topology, test-first lifecycle, and safety rails.
 - **MCG grounding pass**: Grounded the full skill library in the Meta Context Graph (MCG) architecture (Tekiner 2025, Hu et al. arXiv:2512.13564, CoALA arXiv:2309.02427, ACE arXiv:2510.04618). Added MCG Foundation section to README, MCG Architecture section to `agentic_kg_memory/SKILL.md`, and MCG terminology alignment to `skill-wiki` Pattern Store.
 - **Restored `kg_ontology` to `status: active`**: The prior merge into `agentic_kg_memory` was architecturally wrong. `kg_ontology` owns the DKG entity-identity layer (synset/hypernym BM25 canonicalization); `agentic_kg_memory` owns the CG retrieval side. Two distinct MCG concerns.
 - Added `deep-research` as a child of `agentic-harness`: LangGraph research graph with Selenium fallback fetch pipeline.
 - Reframed `agentic-harness` as the multi-framework stationmaster.
 - Added `continuity-log` to preserve compact-safe reasoning products between long turns and compactions.
 - Absorbed `integrate\\llm-wiki` into existing live skills instead of promoting it as a standalone branch: compiled memory behavior now lives in `agentic_kg_memory`, staged retrieval behavior in `gist-retriever`, and the project-vs-corpus boundary in `memory-bank`.
 - Second-pass absorption of `integrate\\llm-wiki`: added consolidation tiers (working/episodic/semantic/procedural), temporal decay, supersession, automation hooks, graph traversal for discovery, and an initial crystallization contract to `agentic_kg_memory`. That protocol has since been promoted into the standalone `crystallization` skill.
 - Added `deep-q-rl` under new `learning/` section: DQN + Russian Doll MCTS pattern generalized from chess-deep-q; applies to any scored discrete-action environment.
-- Merged `hyper-parm_tuning` ╬ô├Ñ├å `optuna-nested-cv`: Methodology Primer section (preconditions checklist, layerwise decomposition, structured search protocol, sampler policy for LLM judges, search space type guide). `hyper-parm_tuning` is now `status: superseded`.
+- Merged `hyper-parm_tuning` ├óΓÇáΓÇÖ `optuna-nested-cv`: Methodology Primer section (preconditions checklist, layerwise decomposition, structured search protocol, sampler policy for LLM judges, search space type guide). `hyper-parm_tuning` is now `status: superseded`.
 - Fattened `agentic-harness` with gstack-derived patterns: Learnings Compounding (learnings.jsonl schema, 4 persistence layers), Automated Dev Pipeline (Autoship state machine), Review Army (7 specialists + adaptive ceremony), Context Compaction During Long Runs.
 - Fattened `deep-research` with research epistemology: Perspective Diversity (STORM), Source Quality Hierarchy (5-tier), Per-Role Model Strategy, Citation Chain Integrity, Research Anti-Patterns.
-- Added Pattern Store vetting mechanism to `skill-wiki/SKILL.md`: vector store as pre-skill staging, 3-application tenure threshold, confidence decay formula (`e^(-0.1 Γö£├╣ months)`), prune gate, promotion pipeline ╬ô├Ñ├å `integrate/staged/`.
+- Added Pattern Store vetting mechanism to `skill-wiki/SKILL.md`: vector store as pre-skill staging, 3-application tenure threshold, confidence decay formula (`e^(-0.1 ├âΓÇö months)`), prune gate, promotion pipeline ├óΓÇáΓÇÖ `integrate/staged/`.
 - All live and retained-historical `SKILL.md` files now carry `status:` governance frontmatter. `hyper-parm_tuning` remains the preserved superseded predecessor.
 - Added `design-patterns`, `agentic-design-patterns`, and `substrate-selection` as distinct skills so code pattern choice, LangGraph workflow shape, and runtime selection no longer collapse into `agentic-harness`.
 - Absorbed `integrate/gstack` ETHOS: "Boil the Lake" (completeness is cheap with AI) into `code/SKILL.md`; "Search Before Building" (3-layer knowledge taxonomy) into `code/SKILL.md`.
 - Absorbed `integrate/gstack/investigate` Iron Law (no fix without root cause) and 5-phase debugging protocol into `debugging/SKILL.md`.
 - Added Skill Routing section to `copilot-instructions.md` mapping request types to skills (pattern from gstack CLAUDE.md).
 - Added `## Applicability Envelope` to `agentic-harness/SKILL.md` and `debugging/SKILL.md` as template for all live skills.
 - Living Skill Library infrastructure: `integrate/README.md`, `integrate/staged/README.md`, `agentic-harness/EVIDENCE.md`, `agentic-harness/HISTORY.md`.
-- Added "Living Skill Library" lifecycle documentation and "Automated Software Development Pipeline" mapping to `README.md`.
\ No newline at end of file
+- Added "Living Skill Library" lifecycle documentation and "Automated Software Development Pipeline" mapping to `README.md`.

  -- Changes from Side B (mirror) -----------------------------------
diff --git "a/C:\\Users\\user\\AppData\\Local\\Temp\\tmpE7EE.tmp" "b/C:\\Users\\user\\AppData\\Local\\Temp\\tmpE7F0.tmp"
index 3588a39..212cd25 100644
--- "a/C:\\Users\\user\\AppData\\Local\\Temp\\tmpE7EE.tmp"
+++ "b/C:\\Users\\user\\AppData\\Local\\Temp\\tmpE7F0.tmp"
@@ -8,133 +8,134 @@ old `.copilot` module scaffold; it is a composable skill graph.
 Use this README as the canonical folder map before adding, moving, or wiring a
 skill. The AST below should match the live folders in this repository.

 ## Skill Graph (AST View)

-Each node is a skill. Indentation encodes parent ╬ô├Ñ├å child dependency. Peers share the same indent level.
+Each node is a skill. Indentation encodes parent ├óΓÇáΓÇÖ child dependency. Peers share the same indent level.

 ```
 skills/
-╬ô├╢┬ú╬ô├╢├ç╬ô├╢├ç execution/                       # plan, implement, verify
-╬ô├╢├⌐   ╬ô├╢┬ú╬ô├╢├ç╬ô├╢├ç react-agent                  # outer execution OS; drives all other skills
-╬ô├╢├⌐   ╬ô├╢┬ú╬ô├╢├ç╬ô├╢├ç reasoning                    # open-ended problem decomposition + multi-perspective analysis
-╬ô├╢├⌐   ╬ô├╢├⌐   ╬ô├╢├╢╬ô├╢├ç╬ô├╢├ç causal-inference         # LLM╬ô├Ñ├åDoWhy╬ô├Ñ├åLLM architecture; Pearl's ladder (association/intervention/counterfactual); causal discovery, do-calculus, SCM via DoWhy + causal-learn
-╬ô├╢├⌐   ╬ô├╢┬ú╬ô├╢├ç╬ô├╢├ç codebase-knowledge-graph     # current-repo whole-system map; foundational vs incidental code; ripple analysis before edits
-╬ô├╢├⌐   ╬ô├╢┬ú╬ô├╢├ç╬ô├╢├ç code                         # implementation standards, naming, refactor sequence
-╬ô├╢├⌐   ╬ô├╢├⌐   ╬ô├╢├╢╬ô├╢├ç╬ô├╢├ç design-patterns          # GoF / contract / relationship-shape companion to code
-╬ô├╢├⌐   ╬ô├╢┬ú╬ô├╢├ç╬ô├╢├ç code-extraction              # extract source files + configs into copy-paste-ready markdown artifact (docling-style)
-╬ô├╢├⌐   ╬ô├╢┬ú╬ô├╢├ç╬ô├╢├ç diagnostic-scanner           # language-aware compiler/linter scanning; errors/warnings grouped by severity
-╬ô├╢├⌐   ╬ô├╢┬ú╬ô├╢├ç╬ô├╢├ç schema-induction             # cross-instance schema discovery via pairwise contrast (Aristotelian diairesis); constants vs variable dims; CRISP-DM data understanding analog
-╬ô├╢├⌐   ╬ô├╢┬ú╬ô├╢├ç╬ô├╢├ç test-planner                 # coverage-aware test plan generation (green/yellow/red status); regression detection
-╬ô├╢├⌐   ╬ô├╢┬ú╬ô├╢├ç╬ô├╢├ç doc-synthesizer              # AST-based documentation with Mermaid dependency/data-flow diagrams
-╬ô├╢├⌐   ╬ô├╢┬ú╬ô├╢├ç╬ô├╢├ç debugging                    # error isolation, salience tiers, diagnostic strategy, self-repair loop
-╬ô├╢├⌐   ╬ô├╢├⌐   ╬ô├╢├╢╬ô├╢├ç╬ô├╢├ç adjacent-surface-scan    # one-degree-out sibling scan when one missing item likely belongs to a local family
-╬ô├╢├⌐   ╬ô├╢┬ú╬ô├╢├ç╬ô├╢├ç validation                   # test design, verification protocol, behavior contracts
-╬ô├╢├⌐   ╬ô├╢├⌐   ╬ô├╢├╢╬ô├╢├ç╬ô├╢├ç uncertainty-quantification  # 3-tier UQ protocol (fast/standard/thorough); semantic entropy, SelfCheckGPT, conformal prediction, LM-Polygraph; abstain/escalate table
-╬ô├╢├⌐   ╬ô├╢┬ú╬ô├╢├ç╬ô├╢├ç architecture                 # system design, abstract-class planning, domain ╬ô├Ñ├å code mapping
-╬ô├╢├⌐   ╬ô├╢┬ú╬ô├╢├ç╬ô├╢├ç tdd-agent                    # Red╬ô├Ñ├åGreen╬ô├Ñ├åRefactor as distinct agentic phases; test-first design contract
-╬ô├╢├⌐   ╬ô├╢├⌐   ╬ô├╢├╢╬ô├╢├ç╬ô├╢├ç program-synthesis        # LLM-assisted formal verification + proof-assisted coding; AutoVerus 3-phase loop; escalation from tdd-agent for unbounded/security properties
-╬ô├╢├⌐   ╬ô├╢┬ú╬ô├╢├ç╬ô├╢├ç autoresearch                 # autonomous iterative hill-climbing: scorer + proposer + git/sqlite checkpoint loop
-╬ô├╢├⌐   ╬ô├╢┬ú╬ô├╢├ç╬ô├╢├ç cua-desktop-agent            # autonomous desktop automation via VLM perception loop; vision-based retry for legacy/API-less applications
-╬ô├╢├⌐   ╬ô├╢├╢╬ô├╢├ç╬ô├╢├ç react-fastapi-sqlite         # full-stack scaffold: React (TanStack Query) + FastAPI (SQLModel ORM) + SQLite; SPA + REST backend
-╬ô├╢├⌐
-╬ô├╢┬ú╬ô├╢├ç╬ô├╢├ç orchestration/                   # route work, enforce policy, manage cross-session state
-╬ô├╢├⌐   ╬ô├╢┬ú╬ô├╢├ç╬ô├╢├ç meta-harness                 # requester-facing manager layer above agentic-harness; scopes objectives, forks/resumes sessions, delegates one issue at a time
-╬ô├╢├⌐   ╬ô├╢┬ú╬ô├╢├ç╬ô├╢├ç agentic-orchestration        # unified: 5-Q decision tree + live agent roster + Aider architect/editor reference impl + Anthropic pattern taxonomy
-╬ô├╢├⌐   ╬ô├╢┬ú╬ô├╢├ç╬ô├╢├ç agentic-design-patterns      # LangGraph workflow shape, router/gate topology, manager/BA/dev/QA rooms
-╬ô├╢├⌐   ╬ô├╢┬ú╬ô├╢├ç╬ô├╢├ç agentic-harness              # dark-task control plane; backbone = OpenClaw/Claude Code/OpenCode/Copilot CLI; structured-response contracts + HTP
-╬ô├╢├⌐   ╬ô├╢├⌐   ╬ô├╢┬ú╬ô├╢├ç╬ô├╢├ç checklist                # LLM-as-judge validation pattern; structured findings with novelty proof
-╬ô├╢├⌐   ╬ô├╢├⌐   ╬ô├╢┬ú╬ô├╢├ç╬ô├╢├ç continuity-log           # compact-safe session memory; distilled decisions, resume points
-╬ô├╢├⌐   ╬ô├╢├⌐   ╬ô├╢┬ú╬ô├╢├ç╬ô├╢├ç pipeline-input-review    # partition a pipeline problem to its minimal failing unit; materialise inputs before harness dispatch; hyper-focused task statements
-╬ô├╢├⌐   ╬ô├╢├⌐   ╬ô├╢├╢╬ô├╢├ç╬ô├╢├ç deep-research            # multi-source web evidence pipeline; LangGraph planner╬ô├Ñ├åresearcher╬ô├Ñ├åsynthesizer
-╬ô├╢├⌐   ╬ô├╢┬ú╬ô├╢├ç╬ô├╢├ç openspec-workflow            # spec-driven change lifecycle with OpenSpec artifacts and Fabro handoff
-╬ô├╢├⌐   ╬ô├╢├⌐   ╬ô├╢┬ú╬ô├╢├ç╬ô├╢├ç openspec-propose         # create proposal/design/spec/tasks for a new change
-╬ô├╢├⌐   ╬ô├╢├⌐   ╬ô├╢┬ú╬ô├╢├ç╬ô├╢├ç openspec-explore         # think/discover mode around an OpenSpec change or idea
-╬ô├╢├⌐   ╬ô├╢├⌐   ╬ô├╢┬ú╬ô├╢├ç╬ô├╢├ç openspec-apply-change    # implement tasks from an OpenSpec change
-╬ô├╢├⌐   ╬ô├╢├⌐   ╬ô├╢├╢╬ô├╢├ç╬ô├╢├ç openspec-archive-change  # archive a completed OpenSpec change
-╬ô├╢├⌐   ╬ô├╢┬ú╬ô├╢├ç╬ô├╢├ç fabro-create-workflow        # author Fabro `.fabro` + `.toml` workflows from natural-language requirements
-╬ô├╢├⌐   ╬ô├╢┬ú╬ô├╢├ç╬ô├╢├ç substrate-selection          # runtime substrate policy: OpenCode / claw-code / pi / aider / provider boundary
-╬ô├╢├⌐   ╬ô├╢┬ú╬ô├╢├ç╬ô├╢├ç ollama-structured            # schema-constrained JSON from Ollama (native SDK + OpenAI compat); Qwen3 thinking suppression
-╬ô├╢├⌐   ╬ô├╢┬ú╬ô├╢├ç╬ô├╢├ç pi                           # lightweight delegated external harness; sits under opencode/agentic-harness and can host aider-like workers
-╬ô├╢├⌐   ╬ô├╢┬ú╬ô├╢├ç╬ô├╢├ç evaluator-optimizer          # LLM-generates╬ô├Ñ├åLLM-critiques╬ô├Ñ├åLLM-regenerates loop; MBR selection; stopping criteria
-╬ô├╢├⌐   ╬ô├╢├⌐   ╬ô├╢├╢╬ô├╢├ç╬ô├╢├ç prompt-optimization      # automatic prompt self-improvement; DSPy (MIPROv2), TextGrad (text-space gradients), OPRO, APE; labeled-trainset ╬ô├Ñ├å MIPROv2 vs no-trainset ╬ô├Ñ├å TextGrad decision tree
-╬ô├╢├⌐   ╬ô├╢┬ú╬ô├╢├ç╬ô├╢├ç multi-agent-coordination     # peer messaging, plan-approval gates, task ownership, dynamic spawning
-╬ô├╢├⌐   ╬ô├╢┬ú╬ô├╢├ç╬ô├╢├ç agent-governance             # safety rails, tool-access policy, audit trail, trust tiers, secrets scan
-╬ô├╢├⌐   ╬ô├╢┬ú╬ô├╢├ç╬ô├╢├ç security-review              # STRIDE-A, OWASP Top 10, data-flow tracing, secret/CVE detection
-╬ô├╢├⌐   ╬ô├╢┬ú╬ô├╢├ç╬ô├╢├ç build-observability          # run-centric observability contract: runs/events/commands, collectors, dashboards, trace enrichment
-╬ô├╢├⌐   ╬ô├╢┬ú╬ô├╢├ç╬ô├╢├ç timeout-guard                # runaway-task policy; interrupt and recovery rules
-╬ô├╢├⌐   ╬ô├╢┬ú╬ô├╢├ç╬ô├╢├ç git-workflow                 # branch strategy (test╬ô├Ñ├ådev╬ô├Ñ├åmain), push gates, LLM verification protocol with headless-browser checks
-╬ô├╢├⌐   ╬ô├╢┬ú╬ô├╢├ç╬ô├╢├ç validation-artifacts         # mandatory proof protocol: training loss curves, holdout metrics, test logs, visual diffs, API benchmarks, script outputs ╬ô├ç├╢ "seeing is believing"
-╬ô├╢├⌐   ╬ô├╢┬ú╬ô├╢├ç╬ô├╢├ç skill-wiki                   # living skill library lifecycle; intake ╬ô├Ñ├å staged ╬ô├Ñ├å active ╬ô├Ñ├å superseded governance
-╬ô├╢├⌐   ╬ô├╢┬ú╬ô├╢├ç╬ô├╢├ç skill-sync                   # LLM-assisted merge for diverged skill copies across local/remote mirrors; cron-safe
-╬ô├╢├⌐   ╬ô├╢├╢╬ô├╢├ç╬ô├╢├ç consolidation                # triplet-based pairwise correlation + greedy chain decomposition ╬ô├Ñ├å merge/xref/migrate prescriptions
-╬ô├╢├⌐
-╬ô├╢┬ú╬ô├╢├ç╬ô├╢├ç memory/                          # persist knowledge across sessions and tasks
-╬ô├╢├⌐   ╬ô├╢┬ú╬ô├╢├ç╬ô├╢├ç memory-bank                  # durable project memory (brief, context, patterns, progress)
-╬ô├╢├⌐   ╬ô├╢├⌐   # meta: DESCRIPTION/ARCHITECTURE/HISTORY pattern ╬ô├ç├╢ applies to any skill folder
-╬ô├╢├⌐   ╬ô├╢┬ú╬ô├╢├ç╬ô├╢├ç todo                         # sqlite-backed task tracking with FastMCP bridge
-╬ô├╢├⌐   ╬ô├╢┬ú╬ô├╢├ç╬ô├╢├ç cognitive-taxonomy           # unified memory classification: implicit/explicit/agentic paradigms; forms/functions/dynamics; System 1 vs 2 routing
-╬ô├╢├⌐   ╬ô├╢┬ú╬ô├╢├ç╬ô├╢├ç memory-architecture          # canonical 5-layer memory stack design: 4 templates (factual KB, personal assistant, autonomous agent, research); inter-layer routing; entity/procedure/query flows
-╬ô├╢├⌐   ╬ô├╢┬ú╬ô├╢├ç╬ô├╢├ç agentic_kg_memory            # MCG Context Graph side: semantic memory policy, retrieval, patterns, tribal knowledge, episodic memory
-╬ô├╢├⌐   ╬ô├╢├⌐   ╬ô├╢┬ú╬ô├╢├ç╬ô├╢├ç kg_ontology              # MCG DKG entity-identity layer: synset/hypernym BM25 canonicalization
-╬ô├╢├⌐   ╬ô├╢├⌐   ╬ô├╢├╢╬ô├╢├ç╬ô├╢├ç gist-retriever           # layered sparse+dense retrieval engine (BM25 + Chroma)
-╬ô├╢├⌐   ╬ô├╢┬ú╬ô├╢├ç╬ô├╢├ç crystallization              # distill completed work chains into digest pages + reusable lessons; hand off semantic outputs to agentic_kg_memory and procedural deltas to skill-wiki
-╬ô├╢├⌐   ╬ô├╢┬ú╬ô├╢├ç╬ô├╢├ç semantic-search-enrichment   # retrieval augmentation: query expansion, metadata boosting, semantic reranking
-╬ô├╢├⌐   ╬ô├╢┬ú╬ô├╢├ç╬ô├╢├ç context-compaction           # active context-window management: tiered eviction, pre/post-compaction hooks
-╬ô├╢├⌐   ╬ô├╢┬ú╬ô├╢├ç╬ô├╢├ç mcp-tool-registry            # MCP tool registration, discovery, routing, ACI design
-╬ô├╢├⌐   ╬ô├╢┬ú╬ô├╢├ç╬ô├╢├ç request-intent-resolution    # request-thread routing, retrieval evaluation
-╬ô├╢├⌐   ╬ô├╢├╢╬ô├╢├ç╬ô├╢├ç feature-catalog              # local SQLite feature inventory for implemented capabilities and file mappings
-╬ô├╢├⌐
-╬ô├╢┬ú╬ô├╢├ç╬ô├╢├ç tuning/                          # measure, optimize, record
-╬ô├╢├⌐   ╬ô├╢┬ú╬ô├╢├ç╬ô├╢├ç optuna-nested-cv             # search engine + methodology primer: inner tune / outer unbiased estimate
-╬ô├╢├⌐   ╬ô├╢┬ú╬ô├╢├ç╬ô├╢├ç hyper-parm_tuning            # superseded predecessor; canonical home for Weighted Stage Allocation pattern
-╬ô├╢├⌐   ╬ô├╢┬ú╬ô├╢├ç╬ô├╢├ç agentic-hyperparm            # behavioral knob tuning for agentic systems; instantiates Stage Allocation for L1-L4 layers
-╬ô├╢├⌐   ╬ô├╢┬ú╬ô├╢├ç╬ô├╢├ç parm-tuning-as-lp            # discrete hyperparameter tuning via linear/mixed-integer programming; orthogonal lever factorization, irreducible-ratio perturbation basis, global optimality
-╬ô├╢├⌐   ╬ô├╢┬ú╬ô├╢├ç╬ô├╢├ç class-balancing              # conditional stratification + token-equal weighting for multi-class reasoning transfer; inference pairing; temperature curriculum
-╬ô├╢├⌐   ╬ô├╢┬ú╬ô├╢├ç╬ô├╢├ç stratified-quota-sampling    # coverage-bounded no-replacement sampler; Box-Cox tiers + quota allocation
-╬ô├╢├⌐   ╬ô├╢├⌐   ╬ô├╢├╢╬ô├╢├ç╬ô├╢├ç synthetic-data           # LLM-generated training data; 8 paradigms (Self-Instruct/Evol-Instruct/GLAN/Magpie/UltraFeedback/FireAct/distilabel); 6 mandatory quality gates; handoff to stratified-quota-sampling + class-balancing
-╬ô├╢├⌐   ╬ô├╢┬ú╬ô├╢├ç╬ô├╢├ç cluster-quantized-knn        # O(1) approximate distance for KNN via cluster-quantization; fast interactive retrieval
-╬ô├╢├⌐   ╬ô├╢┬ú╬ô├╢├ç╬ô├╢├ç mad-dynamic-batching         # MAD-gated token-aware dynamic batching for variable-length training data; quantile partitioning
-╬ô├╢├⌐   ╬ô├╢┬ú╬ô├╢├ç╬ô├╢├ç median-bifurcation           # universal median-cut pattern: choose axis ╬ô├Ñ├å produce both sides ╬ô├Ñ├å drop unwanted half; 2^n epistemic cells at zero labeling cost; data-level contrastive learning
-╬ô├╢├⌐   ╬ô├╢┬ú╬ô├╢├ç╬ô├╢├ç mlflow                       # experiment ledger: params, metrics, artifacts, lineage
-╬ô├╢├⌐   ╬ô├╢┬ú╬ô├╢├ç╬ô├╢├ç model-size-reduction         # checkpoint slimming for HF models: dtype cast, layer drop, LoRA extraction, DARE/TIES/DELLA; architecture-agnostic state_dict path
-╬ô├╢├⌐   ╬ô├╢┬ú╬ô├╢├ç╬ô├╢├ç generalization-theory        # signal-vs-noise training-dynamics lens via eNTK; diagnose memorization, grokking, and noisy-preference fine-tunes
-╬ô├╢├⌐   ╬ô├╢┬ú╬ô├╢├ç╬ô├╢├ç representation-pipeline      # representation design: raw signal ╬ô├Ñ├å embedding space
-╬ô├╢├⌐   ╬ô├╢┬ú╬ô├╢├ç╬ô├╢├ç bm25-corpus-sampling         # representative corpus sampling for BM25; log-normal╬ô├Ñ├åMAD╬ô├Ñ├åYeo-Johnson╬ô├Ñ├åCDF-diff quota; cascaded and proxy-Louvain rerankers
-╬ô├╢├⌐   ╬ô├╢├╢╬ô├╢├ç╬ô├╢├ç rag-eval                     # single-pass 10-metric RAG judge: qwen3.5:4b + Pydantic RAGEvalResult + macro_mean; one prompt per answer
-╬ô├╢├⌐
-╬ô├╢┬ú╬ô├╢├ç╬ô├╢├ç artifacts/                       # masterpiece outputs and information design
-╬ô├╢├⌐   ╬ô├╢┬ú╬ô├╢├ç╬ô├╢├ç documentation                # choose canonical doc vs changelog vs timestamped fixes-applied artifact
-╬ô├╢├⌐   ╬ô├╢┬ú╬ô├╢├ç╬ô├╢├ç response-style               # voice preservation, anti-cliche prose, user-facing coherence
-╬ô├╢├⌐   ╬ô├╢┬ú╬ô├╢├ç╬ô├╢├ç business-writing             # professional document writing: resume, cover letter, portfolio; triplet bullets, spice gradient
-╬ô├╢├⌐   ╬ô├╢┬ú╬ô├╢├ç╬ô├╢├ç gist_correlation_matrix      # sorted correlation matrix as complete relational map; two sorting approaches (orthogonal vs coverage)
-╬ô├╢├⌐   ╬ô├╢┬ú╬ô├╢├ç╬ô├╢├ç nearest-neighbor-chain       # greedy path-cover decomposition of a similarity matrix into variable-length semantic chains; Γòº├ñ selection; chaining = semantic thread
-╬ô├╢├⌐   ╬ô├╢├╢╬ô├╢├ç╬ô├╢├ç spiral-radial-clustering-display  # multi-dimensional spiral visualization; GMM+HDBSCAN+ordering╬ô├Ñ├åUMAP 2D with Gestalt encoding
-╬ô├╢├⌐
-╬ô├╢┬ú╬ô├╢├ç╬ô├╢├ç learning/                        # reinforcement learning and policy optimization
-╬ô├╢├⌐   ╬ô├╢┬ú╬ô├╢├ç╬ô├╢├ç deep-q-rl                    # DQN + Russian Doll MCTS for any scored discrete-action framework; code-rl extension; SPO/DPO offline preference optimization
-╬ô├╢├⌐   ╬ô├╢┬ú╬ô├╢├ç╬ô├╢├ç active-inference             # Bayesian POMDP agents via Free Energy Principle; EFE-driven tool selection; pymdp; use when no reward function + partial observability
-╬ô├╢├⌐   ╬ô├╢┬ú╬ô├╢├ç╬ô├╢├ç continual-learning           # non-forgetting agents; EWC, GEM/A-GEM, PackNet, O-LoRA/InfLoRA, DARE, LwF, MemRL; absorbs integrate/MemRL
-╬ô├╢├⌐   ╬ô├╢├╢╬ô├╢├ç╬ô├╢├ç siamese_from_correlation_matrix  # derive metric-learning pairs directly from embedding/correlation structure
-╬ô├╢├⌐
-╬ô├╢├╢╬ô├╢├ç╬ô├╢├ç pipelines/                       # end-to-end domain workflows (invoke sub-skills as needed)
-    ╬ô├╢┬ú╬ô├╢├ç╬ô├╢├ç auto-ingest                  # on-demand and background PDF enrichment for arxiv_rag corpus; VLM methods extraction
-    ╬ô├╢├╢╬ô├╢├ç╬ô├╢├ç pdf-extraction               # docling╬ô├Ñ├åbase64 strip╬ô├Ñ├åVLM╬ô├Ñ├åreinsert╬ô├Ñ├åmethods; table enhancement with tabula+camelot+VLM fusion; classifier training via class-balancing
+├óΓÇ¥┼ô├óΓÇ¥Γé¼├óΓÇ¥Γé¼ execution/                       # plan, implement, verify
+├óΓÇ¥ΓÇÜ   ├óΓÇ¥┼ô├óΓÇ¥Γé¼├óΓÇ¥Γé¼ react-agent                  # outer execution OS; drives all other skills
+├óΓÇ¥ΓÇÜ   ├óΓÇ¥┼ô├óΓÇ¥Γé¼├óΓÇ¥Γé¼ reasoning                    # open-ended problem decomposition + multi-perspective analysis
+├óΓÇ¥ΓÇÜ   ├óΓÇ¥ΓÇÜ   ├óΓÇ¥ΓÇ¥├óΓÇ¥Γé¼├óΓÇ¥Γé¼ causal-inference         # LLM├óΓÇáΓÇÖDoWhy├óΓÇáΓÇÖLLM architecture; Pearl's ladder (association/intervention/counterfactual); causal discovery, do-calculus, SCM via DoWhy + causal-learn
+├óΓÇ¥ΓÇÜ   ├óΓÇ¥┼ô├óΓÇ¥Γé¼├óΓÇ¥Γé¼ codebase-knowledge-graph     # current-repo whole-system map; foundational vs incidental code; ripple analysis before edits
+├óΓÇ¥ΓÇÜ   ├óΓÇ¥┼ô├óΓÇ¥Γé¼├óΓÇ¥Γé¼ code                         # implementation standards, naming, refactor sequence
+├óΓÇ¥ΓÇÜ   ├óΓÇ¥ΓÇÜ   ├óΓÇ¥ΓÇ¥├óΓÇ¥Γé¼├óΓÇ¥Γé¼ design-patterns          # GoF / contract / relationship-shape companion to code
+├óΓÇ¥ΓÇÜ   ├óΓÇ¥┼ô├óΓÇ¥Γé¼├óΓÇ¥Γé¼ code-extraction              # extract source files + configs into copy-paste-ready markdown artifact (docling-style)
+├óΓÇ¥ΓÇÜ   ├óΓÇ¥┼ô├óΓÇ¥Γé¼├óΓÇ¥Γé¼ diagnostic-scanner           # language-aware compiler/linter scanning; errors/warnings grouped by severity
+├óΓÇ¥ΓÇÜ   ├óΓÇ¥┼ô├óΓÇ¥Γé¼├óΓÇ¥Γé¼ schema-induction             # cross-instance schema discovery via pairwise contrast (Aristotelian diairesis); constants vs variable dims; CRISP-DM data understanding analog
+├óΓÇ¥ΓÇÜ   ├óΓÇ¥┼ô├óΓÇ¥Γé¼├óΓÇ¥Γé¼ test-planner                 # coverage-aware test plan generation (green/yellow/red status); regression detection
+├óΓÇ¥ΓÇÜ   ├óΓÇ¥┼ô├óΓÇ¥Γé¼├óΓÇ¥Γé¼ doc-synthesizer              # AST-based documentation with Mermaid dependency/data-flow diagrams
+├óΓÇ¥ΓÇÜ   ├óΓÇ¥┼ô├óΓÇ¥Γé¼├óΓÇ¥Γé¼ debugging                    # error isolation, salience tiers, diagnostic strategy, self-repair loop
+├óΓÇ¥ΓÇÜ   ├óΓÇ¥ΓÇÜ   ├óΓÇ¥ΓÇ¥├óΓÇ¥Γé¼├óΓÇ¥Γé¼ adjacent-surface-scan    # one-degree-out sibling scan when one missing item likely belongs to a local family
+├óΓÇ¥ΓÇÜ   ├óΓÇ¥┼ô├óΓÇ¥Γé¼├óΓÇ¥Γé¼ validation                   # test design, verification protocol, behavior contracts
+├óΓÇ¥ΓÇÜ   ├óΓÇ¥ΓÇÜ   ├óΓÇ¥ΓÇ¥├óΓÇ¥Γé¼├óΓÇ¥Γé¼ uncertainty-quantification  # 3-tier UQ protocol (fast/standard/thorough); semantic entropy, SelfCheckGPT, conformal prediction, LM-Polygraph; abstain/escalate table
+├óΓÇ¥ΓÇÜ   ├óΓÇ¥┼ô├óΓÇ¥Γé¼├óΓÇ¥Γé¼ architecture                 # system design, abstract-class planning, domain ├óΓÇáΓÇÖ code mapping
+├óΓÇ¥ΓÇÜ   ├óΓÇ¥┼ô├óΓÇ¥Γé¼├óΓÇ¥Γé¼ tdd-agent                    # Red├óΓÇáΓÇÖGreen├óΓÇáΓÇÖRefactor as distinct agentic phases; test-first design contract
+├óΓÇ¥ΓÇÜ   ├óΓÇ¥ΓÇÜ   ├óΓÇ¥ΓÇ¥├óΓÇ¥Γé¼├óΓÇ¥Γé¼ program-synthesis        # LLM-assisted formal verification + proof-assisted coding; AutoVerus 3-phase loop; escalation from tdd-agent for unbounded/security properties
+├óΓÇ¥ΓÇÜ   ├óΓÇ¥┼ô├óΓÇ¥Γé¼├óΓÇ¥Γé¼ autoresearch                 # autonomous iterative hill-climbing: scorer + proposer + git/sqlite checkpoint loop
+├óΓÇ¥ΓÇÜ   ├óΓÇ¥┼ô├óΓÇ¥Γé¼├óΓÇ¥Γé¼ cua-desktop-agent            # autonomous desktop automation via VLM perception loop; vision-based retry for legacy/API-less applications
+├óΓÇ¥ΓÇÜ   ├óΓÇ¥ΓÇ¥├óΓÇ¥Γé¼├óΓÇ¥Γé¼ react-fastapi-sqlite         # full-stack scaffold: React (TanStack Query) + FastAPI (SQLModel ORM) + SQLite; SPA + REST backend
+├óΓÇ¥ΓÇÜ
+├óΓÇ¥┼ô├óΓÇ¥Γé¼├óΓÇ¥Γé¼ orchestration/                   # route work, enforce policy, manage cross-session state
+├óΓÇ¥ΓÇÜ   ├óΓÇ¥┼ô├óΓÇ¥Γé¼├óΓÇ¥Γé¼ meta-harness                 # requester-facing manager layer above agentic-harness; scopes objectives, forks/resumes sessions, delegates one issue at a time
+├óΓÇ¥ΓÇÜ   ├óΓÇ¥┼ô├óΓÇ¥Γé¼├óΓÇ¥Γé¼ agentic-orchestration        # unified: 5-Q decision tree + live agent roster + Aider architect/editor reference impl + Anthropic pattern taxonomy
+├óΓÇ¥ΓÇÜ   ├óΓÇ¥┼ô├óΓÇ¥Γé¼├óΓÇ¥Γé¼ agentic-design-patterns      # LangGraph workflow shape, router/gate topology, manager/BA/dev/QA rooms
+├óΓÇ¥ΓÇÜ   ├óΓÇ¥┼ô├óΓÇ¥Γé¼├óΓÇ¥Γé¼ agentic-harness              # dark-task control plane; backbone = OpenClaw/Claude Code/OpenCode/Copilot CLI; structured-response contracts + HTP
+├óΓÇ¥ΓÇÜ   ├óΓÇ¥ΓÇÜ   ├óΓÇ¥┼ô├óΓÇ¥Γé¼├óΓÇ¥Γé¼ checklist                # LLM-as-judge validation pattern; structured findings with novelty proof
+├óΓÇ¥ΓÇÜ   ├óΓÇ¥ΓÇÜ   ├óΓÇ¥┼ô├óΓÇ¥Γé¼├óΓÇ¥Γé¼ continuity-log           # compact-safe session memory; distilled decisions, resume points
+├óΓÇ¥ΓÇÜ   ├óΓÇ¥ΓÇÜ   ├óΓÇ¥┼ô├óΓÇ¥Γé¼├óΓÇ¥Γé¼ pipeline-input-review    # partition a pipeline problem to its minimal failing unit; materialise inputs before harness dispatch; hyper-focused task statements
+├óΓÇ¥ΓÇÜ   ├óΓÇ¥ΓÇÜ   ├óΓÇ¥ΓÇ¥├óΓÇ¥Γé¼├óΓÇ¥Γé¼ deep-research            # multi-source web evidence pipeline; LangGraph planner├óΓÇáΓÇÖresearcher├óΓÇáΓÇÖsynthesizer
+├óΓÇ¥ΓÇÜ   ├óΓÇ¥┼ô├óΓÇ¥Γé¼├óΓÇ¥Γé¼ openspec-workflow            # spec-driven change lifecycle with OpenSpec artifacts and Fabro handoff
+├óΓÇ¥ΓÇÜ   ├óΓÇ¥ΓÇÜ   ├óΓÇ¥┼ô├óΓÇ¥Γé¼├óΓÇ¥Γé¼ openspec-propose         # create proposal/design/spec/tasks for a new change
+├óΓÇ¥ΓÇÜ   ├óΓÇ¥ΓÇÜ   ├óΓÇ¥┼ô├óΓÇ¥Γé¼├óΓÇ¥Γé¼ openspec-explore         # think/discover mode around an OpenSpec change or idea
+├óΓÇ¥ΓÇÜ   ├óΓÇ¥ΓÇÜ   ├óΓÇ¥┼ô├óΓÇ¥Γé¼├óΓÇ¥Γé¼ openspec-apply-change    # implement tasks from an OpenSpec change
+├óΓÇ¥ΓÇÜ   ├óΓÇ¥ΓÇÜ   ├óΓÇ¥ΓÇ¥├óΓÇ¥Γé¼├óΓÇ¥Γé¼ openspec-archive-change  # archive a completed OpenSpec change
+├óΓÇ¥ΓÇÜ   ├óΓÇ¥┼ô├óΓÇ¥Γé¼├óΓÇ¥Γé¼ fabro-create-workflow        # author Fabro `.fabro` + `.toml` workflows from natural-language requirements
+├óΓÇ¥ΓÇÜ   ├óΓÇ¥┼ô├óΓÇ¥Γé¼├óΓÇ¥Γé¼ substrate-selection          # runtime substrate policy: OpenCode / claw-code / pi / aider / provider boundary
+├óΓÇ¥ΓÇÜ   ├óΓÇ¥┼ô├óΓÇ¥Γé¼├óΓÇ¥Γé¼ ollama-structured            # schema-constrained JSON from Ollama (native SDK + OpenAI compat); Qwen3 thinking suppression
+├óΓÇ¥ΓÇÜ   ├óΓÇ¥┼ô├óΓÇ¥Γé¼├óΓÇ¥Γé¼ pi                           # lightweight delegated external harness; sits under opencode/agentic-harness and can host aider-like workers
+├óΓÇ¥ΓÇÜ   ├óΓÇ¥┼ô├óΓÇ¥Γé¼├óΓÇ¥Γé¼ evaluator-optimizer          # LLM-generates├óΓÇáΓÇÖLLM-critiques├óΓÇáΓÇÖLLM-regenerates loop; MBR selection; stopping criteria
+├óΓÇ¥ΓÇÜ   ├óΓÇ¥ΓÇÜ   ├óΓÇ¥ΓÇ¥├óΓÇ¥Γé¼├óΓÇ¥Γé¼ prompt-optimization      # automatic prompt self-improvement; DSPy (MIPROv2), TextGrad (text-space gradients), OPRO, APE; labeled-trainset ├óΓÇáΓÇÖ MIPROv2 vs no-trainset ├óΓÇáΓÇÖ TextGrad decision tree
+├óΓÇ¥ΓÇÜ   ├óΓÇ¥┼ô├óΓÇ¥Γé¼├óΓÇ¥Γé¼ multi-agent-coordination     # peer messaging, plan-approval gates, task ownership, dynamic spawning
+├óΓÇ¥ΓÇÜ   ├óΓÇ¥┼ô├óΓÇ¥Γé¼├óΓÇ¥Γé¼ agent-governance             # safety rails, tool-access policy, audit trail, trust tiers, secrets scan
+├óΓÇ¥ΓÇÜ   ├óΓÇ¥┼ô├óΓÇ¥Γé¼├óΓÇ¥Γé¼ security-review              # STRIDE-A, OWASP Top 10, data-flow tracing, secret/CVE detection
+├óΓÇ¥ΓÇÜ   ├óΓÇ¥┼ô├óΓÇ¥Γé¼├óΓÇ¥Γé¼ build-observability          # run-centric observability contract: runs/events/commands, collectors, dashboards, trace enrichment
+├óΓÇ¥ΓÇÜ   ├óΓÇ¥┼ô├óΓÇ¥Γé¼├óΓÇ¥Γé¼ timeout-guard                # runaway-task policy; interrupt and recovery rules
+├óΓÇ¥ΓÇÜ   ├óΓÇ¥┼ô├óΓÇ¥Γé¼├óΓÇ¥Γé¼ git-workflow                 # branch strategy (test├óΓÇáΓÇÖdev├óΓÇáΓÇÖmain), push gates, LLM verification protocol with headless-browser checks
+├óΓÇ¥ΓÇÜ   ├óΓÇ¥┼ô├óΓÇ¥Γé¼├óΓÇ¥Γé¼ validation-artifacts         # mandatory proof protocol: training loss curves, holdout metrics, test logs, visual diffs, API benchmarks, script outputs ├óΓé¼ΓÇ¥ "seeing is believing"
+├óΓÇ¥ΓÇÜ   ├óΓÇ¥┼ô├óΓÇ¥Γé¼├óΓÇ¥Γé¼ skill-wiki                   # living skill library lifecycle; intake ├óΓÇáΓÇÖ staged ├óΓÇáΓÇÖ active ├óΓÇáΓÇÖ superseded governance
+├óΓÇ¥ΓÇÜ   ├óΓÇ¥┼ô├óΓÇ¥Γé¼├óΓÇ¥Γé¼ skill-sync                   # LLM-assisted merge for diverged skill copies across local/remote mirrors; cron-safe
+├óΓÇ¥ΓÇÜ   ├óΓÇ¥ΓÇ¥├óΓÇ¥Γé¼├óΓÇ¥Γé¼ consolidation                # triplet-based pairwise correlation + greedy chain decomposition ├óΓÇáΓÇÖ merge/xref/migrate prescriptions
+├óΓÇ¥ΓÇÜ
+├óΓÇ¥┼ô├óΓÇ¥Γé¼├óΓÇ¥Γé¼ memory/                          # persist knowledge across sessions and tasks
+├óΓÇ¥ΓÇÜ   ├óΓÇ¥┼ô├óΓÇ¥Γé¼├óΓÇ¥Γé¼ memory-bank                  # durable project memory (brief, context, patterns, progress)
+├óΓÇ¥ΓÇÜ   ├óΓÇ¥ΓÇÜ   # meta: DESCRIPTION/ARCHITECTURE/HISTORY pattern ├óΓé¼ΓÇ¥ applies to any skill folder
+├óΓÇ¥ΓÇÜ   ├óΓÇ¥┼ô├óΓÇ¥Γé¼├óΓÇ¥Γé¼ todo                         # sqlite-backed task tracking with FastMCP bridge
+├óΓÇ¥ΓÇÜ   ├óΓÇ¥┼ô├óΓÇ¥Γé¼├óΓÇ¥Γé¼ cognitive-taxonomy           # unified memory classification: implicit/explicit/agentic paradigms; forms/functions/dynamics; System 1 vs 2 routing
+├óΓÇ¥ΓÇÜ   ├óΓÇ¥┼ô├óΓÇ¥Γé¼├óΓÇ¥Γé¼ memory-architecture          # canonical 5-layer memory stack design: 4 templates (factual KB, personal assistant, autonomous agent, research); inter-layer routing; entity/procedure/query flows
+├óΓÇ¥ΓÇÜ   ├óΓÇ¥┼ô├óΓÇ¥Γé¼├óΓÇ¥Γé¼ agentic_kg_memory            # MCG Context Graph side: semantic memory policy, retrieval, patterns, tribal knowledge, episodic memory
+├óΓÇ¥ΓÇÜ   ├óΓÇ¥ΓÇÜ   ├óΓÇ¥┼ô├óΓÇ¥Γé¼├óΓÇ¥Γé¼ kg_ontology              # MCG DKG entity-identity layer: synset/hypernym BM25 canonicalization
+├óΓÇ¥ΓÇÜ   ├óΓÇ¥ΓÇÜ   ├óΓÇ¥ΓÇ¥├óΓÇ¥Γé¼├óΓÇ¥Γé¼ gist-retriever           # layered sparse+dense retrieval engine (BM25 + Chroma)
+├óΓÇ¥ΓÇÜ   ├óΓÇ¥┼ô├óΓÇ¥Γé¼├óΓÇ¥Γé¼ crystallization              # distill completed work chains into digest pages + reusable lessons; hand off semantic outputs to agentic_kg_memory and procedural deltas to skill-wiki
+├óΓÇ¥ΓÇÜ   ├óΓÇ¥┼ô├óΓÇ¥Γé¼├óΓÇ¥Γé¼ semantic-search-enrichment   # retrieval augmentation: query expansion, metadata boosting, semantic reranking
+├óΓÇ¥ΓÇÜ   ├óΓÇ¥┼ô├óΓÇ¥Γé¼├óΓÇ¥Γé¼ context-compaction           # active context-window management: tiered eviction, pre/post-compaction hooks
+├óΓÇ¥ΓÇÜ   ├óΓÇ¥┼ô├óΓÇ¥Γé¼├óΓÇ¥Γé¼ mcp-tool-registry            # MCP tool registration, discovery, routing, ACI design
+├óΓÇ¥ΓÇÜ   ├óΓÇ¥┼ô├óΓÇ¥Γé¼├óΓÇ¥Γé¼ request-intent-resolution    # request-thread routing, retrieval evaluation
+├óΓÇ¥ΓÇÜ   ├óΓÇ¥ΓÇ¥├óΓÇ¥Γé¼├óΓÇ¥Γé¼ feature-catalog              # local SQLite feature inventory for implemented capabilities and file mappings
+├óΓÇ¥ΓÇÜ
+├óΓÇ¥┼ô├óΓÇ¥Γé¼├óΓÇ¥Γé¼ tuning/                          # measure, optimize, record
+├óΓÇ¥ΓÇÜ   ├óΓÇ¥┼ô├óΓÇ¥Γé¼├óΓÇ¥Γé¼ optuna-nested-cv             # search engine + methodology primer: inner tune / outer unbiased estimate
+├óΓÇ¥ΓÇÜ   ├óΓÇ¥┼ô├óΓÇ¥Γé¼├óΓÇ¥Γé¼ hyper-parm_tuning            # superseded predecessor; canonical home for Weighted Stage Allocation pattern
+├óΓÇ¥ΓÇÜ   ├óΓÇ¥┼ô├óΓÇ¥Γé¼├óΓÇ¥Γé¼ agentic-hyperparm            # behavioral knob tuning for agentic systems; instantiates Stage Allocation for L1-L4 layers
+├óΓÇ¥ΓÇÜ   ├óΓÇ¥┼ô├óΓÇ¥Γé¼├óΓÇ¥Γé¼ parm-tuning-as-lp            # discrete hyperparameter tuning via linear/mixed-integer programming; orthogonal lever factorization, irreducible-ratio perturbation basis, global optimality
+├óΓÇ¥ΓÇÜ   ├óΓÇ¥┼ô├óΓÇ¥Γé¼├óΓÇ¥Γé¼ class-balancing              # conditional stratification + token-equal weighting for multi-class reasoning transfer; inference pairing; temperature curriculum
+├óΓÇ¥ΓÇÜ   ├óΓÇ¥┼ô├óΓÇ¥Γé¼├óΓÇ¥Γé¼ stratified-quota-sampling    # coverage-bounded no-replacement sampler; Box-Cox tiers + quota allocation
+├óΓÇ¥ΓÇÜ   ├óΓÇ¥ΓÇÜ   ├óΓÇ¥ΓÇ¥├óΓÇ¥Γé¼├óΓÇ¥Γé¼ synthetic-data           # LLM-generated training data; 8 paradigms (Self-Instruct/Evol-Instruct/GLAN/Magpie/UltraFeedback/FireAct/distilabel); 6 mandatory quality gates; handoff to stratified-quota-sampling + class-balancing
+├óΓÇ¥ΓÇÜ   ├óΓÇ¥┼ô├óΓÇ¥Γé¼├óΓÇ¥Γé¼ cluster-quantized-knn        # O(1) approximate distance for KNN via cluster-quantization; fast interactive retrieval
+├óΓÇ¥ΓÇÜ   ├óΓÇ¥┼ô├óΓÇ¥Γé¼├óΓÇ¥Γé¼ mad-dynamic-batching         # MAD-gated token-aware dynamic batching for variable-length training data; quantile partitioning
+├óΓÇ¥ΓÇÜ   ├óΓÇ¥┼ô├óΓÇ¥Γé¼├óΓÇ¥Γé¼ median-bifurcation           # universal median-cut pattern: choose axis ├óΓÇáΓÇÖ produce both sides ├óΓÇáΓÇÖ drop unwanted half; 2^n epistemic cells at zero labeling cost; data-level contrastive learning
+├óΓÇ¥ΓÇÜ   ├óΓÇ¥┼ô├óΓÇ¥Γé¼├óΓÇ¥Γé¼ mlflow                       # experiment ledger: params, metrics, artifacts, lineage
+├óΓÇ¥ΓÇÜ   ├óΓÇ¥┼ô├óΓÇ¥Γé¼├óΓÇ¥Γé¼ model-size-reduction         # checkpoint slimming for HF models: dtype cast, layer drop, LoRA extraction, DARE/TIES/DELLA; architecture-agnostic state_dict path
+├óΓÇ¥ΓÇÜ   ├óΓÇ¥┼ô├óΓÇ¥Γé¼├óΓÇ¥Γé¼ generalization-theory        # signal-vs-noise training-dynamics lens via eNTK; diagnose memorization, grokking, and noisy-preference fine-tunes
+├óΓÇ¥ΓÇÜ   ├óΓÇ¥┼ô├óΓÇ¥Γé¼├óΓÇ¥Γé¼ representation-pipeline      # representation design: raw signal ├óΓÇáΓÇÖ embedding space
+├óΓÇ¥ΓÇÜ   ├óΓÇ¥┼ô├óΓÇ¥Γé¼├óΓÇ¥Γé¼ bm25-corpus-sampling         # representative corpus sampling for BM25; log-normal├óΓÇáΓÇÖMAD├óΓÇáΓÇÖYeo-Johnson├óΓÇáΓÇÖCDF-diff quota; cascaded and proxy-Louvain rerankers; BM25 correlation graph (significant correlations as edges)
+├óΓÇ¥ΓÇÜ   ├óΓÇ¥┼ô├óΓÇ¥Γé¼├óΓÇ¥Γé¼ bm25-autoencoder             # multi-view sparse bottleneck: TF-IDF + token count + char bitvec ├óΓÇáΓÇÖ TruncatedSVD z; collinearity test vs dense; music embedding matrix pattern
+├óΓÇ¥ΓÇÜ   ├óΓÇ¥ΓÇ¥├óΓÇ¥Γé¼├óΓÇ¥Γé¼ rag-eval                     # single-pass 10-metric RAG judge: qwen3.5:4b + Pydantic RAGEvalResult + macro_mean; one prompt per answer
+├óΓÇ¥ΓÇÜ
+├óΓÇ¥┼ô├óΓÇ¥Γé¼├óΓÇ¥Γé¼ artifacts/                       # masterpiece outputs and information design
+├óΓÇ¥ΓÇÜ   ├óΓÇ¥┼ô├óΓÇ¥Γé¼├óΓÇ¥Γé¼ documentation                # choose canonical doc vs changelog vs timestamped fixes-applied artifact
+├óΓÇ¥ΓÇÜ   ├óΓÇ¥┼ô├óΓÇ¥Γé¼├óΓÇ¥Γé¼ response-style               # voice preservation, anti-cliche prose, user-facing coherence
+├óΓÇ¥ΓÇÜ   ├óΓÇ¥┼ô├óΓÇ¥Γé¼├óΓÇ¥Γé¼ business-writing             # professional document writing: resume, cover letter, portfolio; triplet bullets, spice gradient
+├óΓÇ¥ΓÇÜ   ├óΓÇ¥┼ô├óΓÇ¥Γé¼├óΓÇ¥Γé¼ gist_correlation_matrix      # sorted correlation matrix as complete relational map; two sorting approaches (orthogonal vs coverage)
+├óΓÇ¥ΓÇÜ   ├óΓÇ¥┼ô├óΓÇ¥Γé¼├óΓÇ¥Γé¼ nearest-neighbor-chain       # greedy path-cover decomposition of a similarity matrix into variable-length semantic chains; ├ÅΓÇ₧ selection; chaining = semantic thread
+├óΓÇ¥ΓÇÜ   ├óΓÇ¥ΓÇ¥├óΓÇ¥Γé¼├óΓÇ¥Γé¼ spiral-radial-clustering-display  # multi-dimensional spiral visualization; GMM+HDBSCAN+ordering├óΓÇáΓÇÖUMAP 2D with Gestalt encoding
+├óΓÇ¥ΓÇÜ
+├óΓÇ¥┼ô├óΓÇ¥Γé¼├óΓÇ¥Γé¼ learning/                        # reinforcement learning and policy optimization
+├óΓÇ¥ΓÇÜ   ├óΓÇ¥┼ô├óΓÇ¥Γé¼├óΓÇ¥Γé¼ deep-q-rl                    # DQN + Russian Doll MCTS for any scored discrete-action framework; code-rl extension; SPO/DPO offline preference optimization
+├óΓÇ¥ΓÇÜ   ├óΓÇ¥┼ô├óΓÇ¥Γé¼├óΓÇ¥Γé¼ active-inference             # Bayesian POMDP agents via Free Energy Principle; EFE-driven tool selection; pymdp; use when no reward function + partial observability
+├óΓÇ¥ΓÇÜ   ├óΓÇ¥┼ô├óΓÇ¥Γé¼├óΓÇ¥Γé¼ continual-learning           # non-forgetting agents; EWC, GEM/A-GEM, PackNet, O-LoRA/InfLoRA, DARE, LwF, MemRL; absorbs integrate/MemRL
+├óΓÇ¥ΓÇÜ   ├óΓÇ¥ΓÇ¥├óΓÇ¥Γé¼├óΓÇ¥Γé¼ siamese_from_correlation_matrix  # derive metric-learning pairs directly from embedding/correlation structure
+├óΓÇ¥ΓÇÜ
+├óΓÇ¥ΓÇ¥├óΓÇ¥Γé¼├óΓÇ¥Γé¼ pipelines/                       # end-to-end domain workflows (invoke sub-skills as needed)
+    ├óΓÇ¥┼ô├óΓÇ¥Γé¼├óΓÇ¥Γé¼ auto-ingest                  # on-demand and background PDF enrichment for arxiv_rag corpus; VLM methods extraction
+    ├óΓÇ¥ΓÇ¥├óΓÇ¥Γé¼├óΓÇ¥Γé¼ pdf-extraction               # docling├óΓÇáΓÇÖbase64 strip├óΓÇáΓÇÖVLM├óΓÇáΓÇÖreinsert├óΓÇáΓÇÖmethods; table enhancement with tabula+camelot+VLM fusion; classifier training via class-balancing
 ```

 ## Key Relationships

 1. `react-agent` is the outer execution OS. All other skills are invoked from inside it.
 2. `design-patterns` is the code-facing pattern selector. `code` owns edit mechanics; `design-patterns` chooses the relationship shape and contract.
 3. `agentic-design-patterns` chooses LangGraph workflow shape and role topology. It is where routing, prompt chaining, parallel sectioning, voting, orchestrator-workers, evaluator-optimizer, and bounded autonomous loops belong.
 4. `meta-harness` is the manager layer one step above `agentic-harness`: it owns objective framing, scoped session decomposition, and parent/child coordination so request-level planning stays separate from issue-level harness execution.
-5. `substrate-selection` decides which runtime sits behind the graph or harness boundary: OpenCode, claw-code, `pi`, aider, or another provider surface. Default integrated stack: `opencode` for the orchestrator lane, optional `pi` for a delegated external-harness lane, and `aider` for the leaf-agent lane. It also owns the rule that model/provider parity does not imply harness/runtime parity ╬ô├ç├╢ first-party surfaces like GitHub Copilot CLI may bundle stronger runtime guarantees that provider-routed OpenRouter stacks must recreate explicitly in skills/config.
+5. `substrate-selection` decides which runtime sits behind the graph or harness boundary: OpenCode, claw-code, `pi`, aider, or another provider surface. Default integrated stack: `opencode` for the orchestrator lane, optional `pi` for a delegated external-harness lane, and `aider` for the leaf-agent lane. It also owns the rule that model/provider parity does not imply harness/runtime parity ├óΓé¼ΓÇ¥ first-party surfaces like GitHub Copilot CLI may bundle stronger runtime guarantees that provider-routed OpenRouter stacks must recreate explicitly in skills/config.
 6. `agentic-harness` is the programmatic train station for coding frameworks (Claude Code, OpenCode, GitHub Copilot CLI, OpenClaw). It routes, gates, and reconciles work; each framework is a worker line, and the resolved runtime stack should be visible in state/logs rather than hidden in helper code.
 7. `continuity-log` is a child of `agentic-harness`. It holds the compact-safe distilled state that lets the harness resume without re-deriving decisions.
-8. `deep-research` is a child of `agentic-harness`. It decomposes a question into parallel subquestions, gathers web evidence via a 3-tier fetch pipeline (httpx ╬ô├Ñ├å retry ╬ô├Ñ├å Selenium), and synthesizes a claim-backed report seeding the harness TaskSpec.
+8. `deep-research` is a child of `agentic-harness`. It decomposes a question into parallel subquestions, gathers web evidence via a 3-tier fetch pipeline (httpx ├óΓÇáΓÇÖ retry ├óΓÇáΓÇÖ Selenium), and synthesizes a claim-backed report seeding the harness TaskSpec.
 9. `optuna-nested-cv` is now self-contained: the Methodology Primer (what to optimize, preconditions, layerwise decomp, structured search, sampler policy) was absorbed from `hyper-parm_tuning` (now superseded). `mlflow` records every run with lineage.
-10. `agentic_kg_memory` is the **CG (Context Graph) side** of the MCG architecture: semantic memory policy, patterns, tribal knowledge, retrieval. `kg_ontology` is the **DKG entity-identity layer**: synset/hypernym BM25 canonicalization that prevents duplicate nodes without graph topology traversal. They are complementary layers, not alternatives ╬ô├ç├╢ do not merge them again.
+10. `agentic_kg_memory` is the **CG (Context Graph) side** of the MCG architecture: semantic memory policy, patterns, tribal knowledge, retrieval. `kg_ontology` is the **DKG entity-identity layer**: synset/hypernym BM25 canonicalization that prevents duplicate nodes without graph topology traversal. They are complementary layers, not alternatives ├óΓé¼ΓÇ¥ do not merge them again.
 11. `gist-retriever` is the retrieval sub-skill for that memory layer. It spans the access-path progression from markdown/index-first lookup through local markdown search and into the full hybrid BM25+dense pipeline.
 12. `memory-bank` remains project operating memory, not compiled corpus memory. It stores project continuity while `agentic_kg_memory` stores evolving domain knowledge.
 13. The supplementary comparison boundary is now explicit in the repo: **RAG/retriever** behavior belongs in `gist-retriever`, **LLM Wiki/compiler** behavior belongs in `agentic_kg_memory`, and **GBrain/operator / fat-skills orchestration** belongs on the execution/orchestration side, not in the memory branch.
 14. KnowledgeWeaver is treated as a concrete implementation example of the compiler side: typed readable knowledge units plus a compiled index that can be rebuilt from canonical markdown artifacts.
 15. `agentic-harness` (waterfall -> agile: topics -> plans -> specs -> tasks) is the lifecycle template for skill authoring, not just software projects.
@@ -142,59 +143,59 @@ skills/
 17. `checklist` is a subskill of `agentic-harness`. It is the Pydantic-schema LLM-as-judge pattern: structured findings with novelty proofs, non-fatal execution, `review_required` flag, and cross-run fingerprinting via throughline Q-scores. Reference implementation: `gap_critic.py` in storywriter.
 18. `gist_correlation_matrix` is the "true GIST output": sorted correlation matrix as complete relational map (N^2 cells, each encoding pairwise relationship). Two sorting strategies: **orthogonal** (information-theoretic maximization, sharp drop-off) and **coverage** (hierarchical boundary exploration, expanding bands). Outputs: interactive HTMLs with full zoom/pan/hover.
 19. `spiral-radial-clustering-display` is the multi-dimensional hierarchical clustering visualization skill. Maps four layers (macro GMM + micro HDBSCAN + decorrelated ordering + hubness) into 3D feature space, projects via UMAP to 2D, encodes layers via Gestalt (position = spiral topology, color = macro, opacity = micro, size = centrality). Preserves topological structure and produces interactive Plotly HTML with full zoom/pan/hover metadata.
 20. `feature-catalog` is the local implementation ledger: a SQLite feature catalog for tracking what the project already ships and where it lives.
 21. `siamese_from_correlation_matrix` is the metric-learning companion to the embedding-analysis branch: it turns correlation structure into contrastive supervision.
-22. `skill-wiki` is the meta-skill governing the living skill library lifecycle. It owns the intake pipeline, promotion gates, supersession rules, sidecar conventions (EVIDENCE.md, HISTORY.md, scripts/ examples), and the periodic sweep that keeps skills consistent over time. It routes verified work chains into `crystallization` when the output is a digest, and handles staged skill-contract updates when the output is a library change. It is NOT memory storage (╬ô├Ñ├å `agentic_kg_memory`) and NOT project state (╬ô├Ñ├å `memory-bank`).
+22. `skill-wiki` is the meta-skill governing the living skill library lifecycle. It owns the intake pipeline, promotion gates, supersession rules, sidecar conventions (EVIDENCE.md, HISTORY.md, scripts/ examples), and the periodic sweep that keeps skills consistent over time. It routes verified work chains into `crystallization` when the output is a digest, and handles staged skill-contract updates when the output is a library change. It is NOT memory storage (├óΓÇáΓÇÖ `agentic_kg_memory`) and NOT project state (├óΓÇáΓÇÖ `memory-bank`).
 23. `documentation` decides which durable doc artifact to update: canonical README/spec, cumulative changelog, or a timestamped fixes-applied note.
 24. `response-style` governs user-facing prose: voice preservation, anti-cliche writing, and answer coherence. Harness-state coherence remains with `agentic-harness`.
-25. `class-balancing` is a general-purpose class weight protocol. It computes log inverse frequency per class, applies Box-Cox normalization to tame the distribution tail, clips negatives, and normalizes to ratios for use as `class_weight` in sklearn or `weight` in PyTorch CrossEntropyLoss. Used anywhere labeled data has heavy class imbalance ╬ô├ç├╢ layout element classification, NER, retrieval judgment labeling.
+25. `class-balancing` is a general-purpose class weight protocol. It computes log inverse frequency per class, applies Box-Cox normalization to tame the distribution tail, clips negatives, and normalizes to ratios for use as `class_weight` in sklearn or `weight` in PyTorch CrossEntropyLoss. Used anywhere labeled data has heavy class imbalance ├óΓé¼ΓÇ¥ layout element classification, NER, retrieval judgment labeling.
 25. `stratified-quota-sampling` owns fixed-budget coverage schedulers: Box-Cox tiering, quota allocation, and no-replacement sampling from an imbalanced pool. Pair it with `class-balancing` when quota selection alone still leaves residual label skew inside the loss, and with `optuna-nested-cv` when sample fraction, quota ratios, or tier weighting are part of the tuning contract.
-26. `pdf-extraction` is the end-to-end PDF╬ô├Ñ├åenriched-Markdown pipeline workflow: docling╬ô├Ñ├åbase64 strip╬ô├Ñ├åVLM image description╬ô├Ñ├åreinsert╬ô├Ñ├åmethods extraction (5 phases via `run_pipeline.bat`). Includes a table enhancement sub-pipeline: docling JSON bboxes╬ô├Ñ├åpymupdf crop╬ô├Ñ├åtabula+camelot extraction╬ô├Ñ├åVLM fusion╬ô├Ñ├åpatched Markdown. The layout classifier uses `class-balancing` for training. Standalone workflow skill; not a child of `agentic-harness`.
+26. `pdf-extraction` is the end-to-end PDF├óΓÇáΓÇÖenriched-Markdown pipeline workflow: docling├óΓÇáΓÇÖbase64 strip├óΓÇáΓÇÖVLM image description├óΓÇáΓÇÖreinsert├óΓÇáΓÇÖmethods extraction (5 phases via `run_pipeline.bat`). Includes a table enhancement sub-pipeline: docling JSON bboxes├óΓÇáΓÇÖpymupdf crop├óΓÇáΓÇÖtabula+camelot extraction├óΓÇáΓÇÖVLM fusion├óΓÇáΓÇÖpatched Markdown. The layout classifier uses `class-balancing` for training. Standalone workflow skill; not a child of `agentic-harness`.
 27. `openspec-workflow` is the spec-driven product/change lifecycle skill. Its companion action skills (`openspec-propose`, `openspec-explore`, `openspec-apply-change`, `openspec-archive-change`) are command-shaped entry points into the same OpenSpec operating model.
 28. `fabro-create-workflow` is the Fabro graph/run-config authoring companion. It can support `openspec-workflow` when a repo needs a new Fabro pipeline, but it is also usable as a standalone workflow-design skill.
 29. `agentic-harness` now has an explicit evaluation mix: `checklist` for structured audit artifacts, DSPy-derived metric/reward compile-refine patterns when scoring is explicit, and TextGrad-derived textual-loss loops when the critic must explain how to improve text/code/prompts. Optimizer scores inform repair; artifact-backed verification still decides completion.
 30. `codebase-knowledge-graph` is the current-repository relationship-mapping protocol. It builds the typed module/file/class/function graph and the foundational-vs-incidental distinction that should exist before `code`, `debugging`, or `validation` edits proceed.
-31. `code-extraction` extracts source files + configs from any project into a unified markdown artifact (docling-style: parse ╬ô├Ñ├å normalize ╬ô├Ñ├å markdown + JSON metadata). Supports multi-language detection (Python, Go, Rust, Swift, Java, JS/TS via markers or 8+ source files). Output feeds `codebase-knowledge-graph`, `documentation`, and LLM context assembly.
+31. `code-extraction` extracts source files + configs from any project into a unified markdown artifact (docling-style: parse ├óΓÇáΓÇÖ normalize ├óΓÇáΓÇÖ markdown + JSON metadata). Supports multi-language detection (Python, Go, Rust, Swift, Java, JS/TS via markers or 8+ source files). Output feeds `codebase-knowledge-graph`, `documentation`, and LLM context assembly.
 32. `diagnostic-scanner` invokes language-appropriate tools (mypy/pylint, go vet, cargo check, swiftc, eslint, etc.) and normalizes errors/warnings by severity and category. Produces fix prompts ready for LLM remediation. Output feeds `validation` and `code` for structured violation handling.
 33. `model-size-reduction` owns post-training checkpoint reduction: dtype casting, layer dropping, LoRA extraction, and DARE/TIES/DELLA sparsification directly against Hugging Face `state_dict`s. `continual-learning` still owns DARE as a lifelong-learning merge pattern; use `model-size-reduction` when the goal is footprint, portability, or architecture-agnostic checkpoint surgery.
 34. `generalization-theory` is the training-dynamics diagnostic lens for signal-vs-noise partitioning, grokking delay, and noisy-preference memorization. It helps choose intervention surfaces across data, architecture, and optimizer design, but it does not own the tuning/search loop (`optuna-nested-cv`) or long-horizon forgetting control (`continual-learning`).
-35. `test-planner` generates coverage-aware test plans with status flags (Γëí╞Æ╞Æ├│ GREEN=DONE, Γëí╞Æ╞Æ├¡ YELLOW=PARTIAL, Γëí╞Æ├╢Γöñ RED=MISSING). Proposes concrete scenarios by test level (smoke/unit/integration/e2e/regression) and detects regression subjects via git diff. Output feeds `tdd-agent` for test-driven implementation and `validation` for coverage verification.
+35. `test-planner` generates coverage-aware test plans with status flags (├░┼╕┼╕┬ó GREEN=DONE, ├░┼╕┼╕┬í YELLOW=PARTIAL, ├░┼╕ΓÇ¥┬┤ RED=MISSING). Proposes concrete scenarios by test level (smoke/unit/integration/e2e/regression) and detects regression subjects via git diff. Output feeds `tdd-agent` for test-driven implementation and `validation` for coverage verification.
 36. `doc-synthesizer` parses project structure via AST (Python focus; all languages via markers), builds dependency graphs, and generates Mermaid diagrams for module dependencies and data flow. Output feeds `documentation`, `codebase-knowledge-graph`, and architecture review. URI fetch/crawl extensible for Phase 2.
 37. `build-observability` is the run-centric observability layer for agentic execution. `agentic-harness` owns control flow and retries; `build-observability` projects runtime exhaust into normalized `runs/events/commands` records and operator-facing dashboard views.
-38. `react-fastapi-sqlite` is the full-stack application scaffold skill: React frontend (with TanStack Query for server-state caching), FastAPI backend (with SQLModel ORM layer), and SQLite file-based database. Use when building SPAs with Python REST backends, configuring client-side data fetching and invalidation patterns, or structuring domain-driven CRUD operations. Output: production-ready project layout with separation of concerns (api/ ╬ô├Ñ├å hooks/ ╬ô├Ñ├å pages/components/ hierarchy). Integrates with `code` for implementation standards and `validation` for integration testing.
-39. `git-workflow` is the branch strategy and LLM safety protocol for this repository. Enforces test╬ô├Ñ├ådev╬ô├Ñ├åmain push gates, requires LLM verification against last known working commit before each push, and pairs `code` verification (git diff checks) with `headless-browser-verification` screenshots for web frontend changes. Prevents accidental pushes to main by requiring explicit user approval at each stage.
+38. `react-fastapi-sqlite` is the full-stack application scaffold skill: React frontend (with TanStack Query for server-state caching), FastAPI backend (with SQLModel ORM layer), and SQLite file-based database. Use when building SPAs with Python REST backends, configuring client-side data fetching and invalidation patterns, or structuring domain-driven CRUD operations. Output: production-ready project layout with separation of concerns (api/ ├óΓÇáΓÇÖ hooks/ ├óΓÇáΓÇÖ pages/components/ hierarchy). Integrates with `code` for implementation standards and `validation` for integration testing.
+39. `git-workflow` is the branch strategy and LLM safety protocol for this repository. Enforces test├óΓÇáΓÇÖdev├óΓÇáΓÇÖmain push gates, requires LLM verification against last known working commit before each push, and pairs `code` verification (git diff checks) with `headless-browser-verification` screenshots for web frontend changes. Prevents accidental pushes to main by requiring explicit user approval at each stage.

 40. `cognitive-taxonomy` is the **reference skill for all memory decisions**. It synthesizes four peer-reviewed papers into a unified classification system: implicit/explicit/agentic paradigms, forms/functions/dynamics taxonomy, biological-artificial crosswalk, and neuro-symbolic System 1 vs System 2 dual-process reasoning. Use it to classify memory patterns, route queries correctly, diagnose underperformance (why is vector-only failing?), and design new memory architectures. It's a pure reference skill (no code changes) that sits above all memory subsystems (`agentic_kg_memory`, `procedural-memory`, `continuity-log`, `context-compaction`).

-41. `memory-architecture` is the **canonical design reference for agent memory systems**. Implements the Meta Context Graph layered stack with 4 concrete templates: (1) factual knowledge base (Implicit╬ô├Ñ├åExplicit╬ô├Ñ├åWorking), (2) personal assistant with memory (adds Episodic), (3) autonomous agent (adds Procedural), (4) research/knowledge synthesis pipeline. Each template includes full 5-layer architecture, entity anchor flow, procedure discovery flow, query routing lifecycle, and anti-patterns. Use when designing a new agent with memory, evaluating existing systems for gaps, onboarding developers. Depends on `cognitive-taxonomy` for classification; feeds into `procedural-memory`, `agentic_kg_memory`, `context-compaction` for implementation.
+41. `memory-architecture` is the **canonical design reference for agent memory systems**. Implements the Meta Context Graph layered stack with 4 concrete templates: (1) factual knowledge base (Implicit├óΓÇáΓÇÖExplicit├óΓÇáΓÇÖWorking), (2) personal assistant with memory (adds Episodic), (3) autonomous agent (adds Procedural), (4) research/knowledge synthesis pipeline. Each template includes full 5-layer architecture, entity anchor flow, procedure discovery flow, query routing lifecycle, and anti-patterns. Use when designing a new agent with memory, evaluating existing systems for gaps, onboarding developers. Depends on `cognitive-taxonomy` for classification; feeds into `procedural-memory`, `agentic_kg_memory`, `context-compaction` for implementation.

 42. `validation-artifacts` enforces the principle **"seeing is believing"** by making validation proof mandatory, not optional. Before any skill claims "validation passed", this skill demands reproducible artifacts: training loss curves + eval metrics on holdout sets, predictions + confusion matrices, test execution logs with exit codes, before/after screenshots + visual diffs, API request/response samples + latency profiles, script execution examples with outputs. Used by `validation`, `checklist`, `tdd-agent`, `debugging`, `git-workflow` to prevent "trust me" claims. Integrates with `headless-browser-verification` (UI artifacts) and `security-review` (security validation artifacts).

-43. `skill-sync` is the **LLM-assisted merge protocol for diverged skill copies** across master and local/remote mirrors. Distinct from `skill-wiki` (governance: intake/staging/lifecycle) ╬ô├ç├╢ `skill-sync` is operational: when both master and a mirror have independently changed since the last commit, it classifies the case (no-op / fast-forward / conflict), applies deterministic fast-forwards automatically, and routes true conflicts to an LLM merge that incorporates both sets of changes without dropping content from either side. Mechanically executed by `sync_skills.ps1`. MERGE-CONFLICT markers flag unresolved sections for human review before commit.
+43. `skill-sync` is the **LLM-assisted merge protocol for diverged skill copies** across master and local/remote mirrors. Distinct from `skill-wiki` (governance: intake/staging/lifecycle) ├óΓé¼ΓÇ¥ `skill-sync` is operational: when both master and a mirror have independently changed since the last commit, it classifies the case (no-op / fast-forward / conflict), applies deterministic fast-forwards automatically, and routes true conflicts to an LLM merge that incorporates both sets of changes without dropping content from either side. Mechanically executed by `sync_skills.ps1`. MERGE-CONFLICT markers flag unresolved sections for human review before commit.

-44. `consolidation` is the **triplet-based document consolidation pipeline** for living knowledge bases and skill libraries. Extracts subject-predicate-object triplets from each document, computes a pairwise Jaccard similarity matrix (or NLI-based soft Jaccard for semantic matching), runs **greedy nearest-neighbor chain decomposition** (single-linkage chaining) to group related documents, and emits a sorted report with prescriptions: MERGE (╬ô├½├æ0.8), migrate (0.5╬ô├ç├┤0.8), xref (0.3╬ô├ç├┤0.5). Groups are sorted by chain length descending ╬ô├ç├╢ largest clusters first. Sits above `gist_correlation_matrix` (matrix builder) and feeds prescriptions into `skill-wiki` (governance) and `skill-sync` (mechanical merge). Use when the library has grown by ╬ô├½├æ5 new entries, semantic search returns contradictory results, or a scheduled consolidation run is due.
+44. `consolidation` is the **triplet-based document consolidation pipeline** for living knowledge bases and skill libraries. Extracts subject-predicate-object triplets from each document, computes a pairwise Jaccard similarity matrix (or NLI-based soft Jaccard for semantic matching), runs **greedy nearest-neighbor chain decomposition** (single-linkage chaining) to group related documents, and emits a sorted report with prescriptions: MERGE (├óΓÇ░┬Ñ0.8), migrate (0.5├óΓé¼ΓÇ£0.8), xref (0.3├óΓé¼ΓÇ£0.5). Groups are sorted by chain length descending ├óΓé¼ΓÇ¥ largest clusters first. Sits above `gist_correlation_matrix` (matrix builder) and feeds prescriptions into `skill-wiki` (governance) and `skill-sync` (mechanical merge). Use when the library has grown by ├óΓÇ░┬Ñ5 new entries, semantic search returns contradictory results, or a scheduled consolidation run is due.

-45. `nearest-neighbor-chain` is the **greedy path-cover chain decomposition sub-skill** shared by `consolidation` and any other consumer that needs to partition a similarity matrix into semantic groups. It walks pairs sorted by descending score, extends only chain endpoints (no branching), and emits variable-length chains sorted by length descending. Singletons are docs with no above-Γòº├ñ neighbours. The "chaining effect" of single-linkage is intentional: each chain is a semantic thread; a chain break is a topic boundary. `gist_correlation_matrix` produces the matrix; `nearest-neighbor-chain` decomposes it; `consolidation` adds triplet extraction and MERGE/migrate/xref prescriptions on top.
+45. `nearest-neighbor-chain` is the **greedy path-cover chain decomposition sub-skill** shared by `consolidation` and any other consumer that needs to partition a similarity matrix into semantic groups. It walks pairs sorted by descending score, extends only chain endpoints (no branching), and emits variable-length chains sorted by length descending. Singletons are docs with no above-├ÅΓÇ₧ neighbours. The "chaining effect" of single-linkage is intentional: each chain is a semantic thread; a chain break is a topic boundary. `gist_correlation_matrix` produces the matrix; `nearest-neighbor-chain` decomposes it; `consolidation` adds triplet extraction and MERGE/migrate/xref prescriptions on top.

-46. `prompt-optimization` is the **automatic prompt self-improvement skill**. A child of `evaluator-optimizer` that applies optimization algorithms ╬ô├ç├╢ not manual rewriting. Labeled trainset + multi-step ╬ô├Ñ├å DSPy MIPROv2 (Bayesian joint instruction+demo search). No trainset + differentiable loss ╬ô├Ñ├å TextGrad (text-space gradient descent). Demos only ╬ô├Ñ├å APE. Single instruction ╬ô├Ñ├å OPRO. `agentic-harness` invokes this when a module's loss metric is stable but prompt quality is the bottleneck. Absorbs `integrate/dspy.md` and `integrate/textgrad.md`.
+46. `prompt-optimization` is the **automatic prompt self-improvement skill**. A child of `evaluator-optimizer` that applies optimization algorithms ├óΓé¼ΓÇ¥ not manual rewriting. Labeled trainset + multi-step ├óΓÇáΓÇÖ DSPy MIPROv2 (Bayesian joint instruction+demo search). No trainset + differentiable loss ├óΓÇáΓÇÖ TextGrad (text-space gradient descent). Demos only ├óΓÇáΓÇÖ APE. Single instruction ├óΓÇáΓÇÖ OPRO. `agentic-harness` invokes this when a module's loss metric is stable but prompt quality is the bottleneck. Absorbs `integrate/dspy.md` and `integrate/textgrad.md`.

-47. `uncertainty-quantification` is the **LLM output confidence protocol**. A child of `validation` for measuring when a model knows vs. doesn't know. Three-tier protocol: Tier 1 = fast (logprobs/verbal, <0.1s), Tier 2 = standard (N=3╬ô├ç├┤5 consistency samples), Tier 3 = thorough (N╬ô├½├æ10 + conformal prediction). Semantic entropy (arXiv:2302.09664) outperforms token-level entropy. Always use Tier 3 minimum for irreversible actions. Libraries: `selfcheckgpt`, `lm-polygraph`. Feeds `checklist` for audit trails and `uncertainty-quantification` threshold gates in `agent-governance`.
+47. `uncertainty-quantification` is the **LLM output confidence protocol**. A child of `validation` for measuring when a model knows vs. doesn't know. Three-tier protocol: Tier 1 = fast (logprobs/verbal, <0.1s), Tier 2 = standard (N=3├óΓé¼ΓÇ£5 consistency samples), Tier 3 = thorough (N├óΓÇ░┬Ñ10 + conformal prediction). Semantic entropy (arXiv:2302.09664) outperforms token-level entropy. Always use Tier 3 minimum for irreversible actions. Libraries: `selfcheckgpt`, `lm-polygraph`. Feeds `checklist` for audit trails and `uncertainty-quantification` threshold gates in `agent-governance`.

-48. `causal-inference` is the **LLM╬ô├Ñ├åDoWhy╬ô├Ñ├åLLM causal reasoning chain**. A child of `reasoning`. LLMs hallucinate on formal do-calculus (near-random; arXiv:2306.05836) ╬ô├ç├╢ all estimation routes through DoWhy, not the LLM. Three-phase protocol: LLM proposes DAG ╬ô├Ñ├å causal-learn validates (PC/FCI/GES) ╬ô├Ñ├å DoWhy identifies+estimates. LLM only interprets results. Counterfactual queries use `dowhy.counterfactual_outcomes`. Libraries: `dowhy`, `causal-learn`, `econml`, `pywhy-llm` (experimental).
+48. `causal-inference` is the **LLM├óΓÇáΓÇÖDoWhy├óΓÇáΓÇÖLLM causal reasoning chain**. A child of `reasoning`. LLMs hallucinate on formal do-calculus (near-random; arXiv:2306.05836) ├óΓé¼ΓÇ¥ all estimation routes through DoWhy, not the LLM. Three-phase protocol: LLM proposes DAG ├óΓÇáΓÇÖ causal-learn validates (PC/FCI/GES) ├óΓÇáΓÇÖ DoWhy identifies+estimates. LLM only interprets results. Counterfactual queries use `dowhy.counterfactual_outcomes`. Libraries: `dowhy`, `causal-learn`, `econml`, `pywhy-llm` (experimental).

-49. `synthetic-data` is the **LLM-generated training data pipeline**. A child of `stratified-quota-sampling`. Eight paradigms ordered by fidelity: Self-Instruct ╬ô├Ñ├å Evol-Instruct ╬ô├Ñ├å GLAN ╬ô├Ñ├å Magpie ╬ô├Ñ├å Self-Play ╬ô├Ñ├å Persona-driven ╬ô├Ñ├å Task-specific ╬ô├Ñ├å Preference. Six mandatory quality gates in order: dedup ╬ô├Ñ├å schema ╬ô├Ñ├å LLM judge ╬ô├Ñ├å IFD ╬ô├Ñ├å coverage ╬ô├Ñ├å safety. Model collapse risk (arXiv:2305.17493): requires a strong fixed teacher (GPT-4/Llama-3-70B), never train-on-own-outputs without mixing real data. Clean three-stage handoff: `synthetic-data` ╬ô├Ñ├å `stratified-quota-sampling` ╬ô├Ñ├å `class-balancing`. Library: `argilla-io/distilabel`.
+49. `synthetic-data` is the **LLM-generated training data pipeline**. A child of `stratified-quota-sampling`. Eight paradigms ordered by fidelity: Self-Instruct ├óΓÇáΓÇÖ Evol-Instruct ├óΓÇáΓÇÖ GLAN ├óΓÇáΓÇÖ Magpie ├óΓÇáΓÇÖ Self-Play ├óΓÇáΓÇÖ Persona-driven ├óΓÇáΓÇÖ Task-specific ├óΓÇáΓÇÖ Preference. Six mandatory quality gates in order: dedup ├óΓÇáΓÇÖ schema ├óΓÇáΓÇÖ LLM judge ├óΓÇáΓÇÖ IFD ├óΓÇáΓÇÖ coverage ├óΓÇáΓÇÖ safety. Model collapse risk (arXiv:2305.17493): requires a strong fixed teacher (GPT-4/Llama-3-70B), never train-on-own-outputs without mixing real data. Clean three-stage handoff: `synthetic-data` ├óΓÇáΓÇÖ `stratified-quota-sampling` ├óΓÇáΓÇÖ `class-balancing`. Library: `argilla-io/distilabel`.

-50. `continual-learning` is the **non-forgetting agent training protocol**. Sits in `learning/` alongside `deep-q-rl`. Prevents catastrophic forgetting when a model must learn a new task without erasing prior skills. Six approaches by compute budget: EWC (regularization, cheapest) ╬ô├Ñ├å LwF (distillation) ╬ô├Ñ├å GEM/A-GEM (episodic memory constraint) ╬ô├Ñ├å PackNet (parameter isolation) ╬ô├Ñ├å O-LoRA/InfLoRA (LoRA orthogonalization) ╬ô├Ñ├å MemRL (frozen backbone + episodic Q-value memory, ICML 2026). `procedural-memory` EMA (Γò¼Γûô=0.9) is intentionally aligned with single-sample EWC. Absorbs `integrate/MemRL` (arXiv:2601.03192). Libraries: Avalanche, Mammoth, HuggingFace PEFT.
+50. `continual-learning` is the **non-forgetting agent training protocol**. Sits in `learning/` alongside `deep-q-rl`. Prevents catastrophic forgetting when a model must learn a new task without erasing prior skills. Six approaches by compute budget: EWC (regularization, cheapest) ├óΓÇáΓÇÖ LwF (distillation) ├óΓÇáΓÇÖ GEM/A-GEM (episodic memory constraint) ├óΓÇáΓÇÖ PackNet (parameter isolation) ├óΓÇáΓÇÖ O-LoRA/InfLoRA (LoRA orthogonalization) ├óΓÇáΓÇÖ MemRL (frozen backbone + episodic Q-value memory, ICML 2026). `procedural-memory` EMA (├Ä┬▓=0.9) is intentionally aligned with single-sample EWC. Absorbs `integrate/MemRL` (arXiv:2601.03192). Libraries: Avalanche, Mammoth, HuggingFace PEFT.

-51. `program-synthesis` is the **formal verification + proof-assisted coding skill**. A child of `tdd-agent` ╬ô├ç├╢ `tdd-agent` escalates here when the property is unbounded, security-critical, or requires exhaustive correctness guarantees. AutoVerus (arXiv:2409.13082): 91.3% on 150 Verus tasks using GPT-4o + Rust ghost code, ~$37 total. EvalPlus (arXiv:2305.01210): pass@k drops 19╬ô├ç├┤28% with exhaustive testing vs. HumanEval ╬ô├ç├╢ all `tdd-agent` benchmarks should use EvalPlus. Three-phase loop: generate ╬ô├Ñ├å verify (formal checker) ╬ô├Ñ├å repair (RLEF feedback). Integration: `tdd-agent` handles empirical tests; `program-synthesis` handles formal properties.
+51. `program-synthesis` is the **formal verification + proof-assisted coding skill**. A child of `tdd-agent` ├óΓé¼ΓÇ¥ `tdd-agent` escalates here when the property is unbounded, security-critical, or requires exhaustive correctness guarantees. AutoVerus (arXiv:2409.13082): 91.3% on 150 Verus tasks using GPT-4o + Rust ghost code, ~$37 total. EvalPlus (arXiv:2305.01210): pass@k drops 19├óΓé¼ΓÇ£28% with exhaustive testing vs. HumanEval ├óΓé¼ΓÇ¥ all `tdd-agent` benchmarks should use EvalPlus. Three-phase loop: generate ├óΓÇáΓÇÖ verify (formal checker) ├óΓÇáΓÇÖ repair (RLEF feedback). Integration: `tdd-agent` handles empirical tests; `program-synthesis` handles formal properties.

-52. `active-inference` is the **Bayesian POMDP agent skill** based on the Free Energy Principle. Sits in `learning/` as a complement to `deep-q-rl`, not a replacement. Use when: partial observability (can't see full state), no clean scalar reward (prefer EFE preferences), principled tool selection (epistemic value drives info-gathering before committing to action). EFE decomposes into epistemic value (info gain) + pragmatic value (reach preferred obs) ╬ô├ç├╢ no reward design needed. Russian Doll MCTS ╬ô├½├¬ Sophisticated Inference: both use tree search; EFE replaces Q-value as node score. Library: `inferactively-pymdp`. Use `deep-q-rl` when full observability + `evaluate(state)` exists.
+52. `active-inference` is the **Bayesian POMDP agent skill** based on the Free Energy Principle. Sits in `learning/` as a complement to `deep-q-rl`, not a replacement. Use when: partial observability (can't see full state), no clean scalar reward (prefer EFE preferences), principled tool selection (epistemic value drives info-gathering before committing to action). EFE decomposes into epistemic value (info gain) + pragmatic value (reach preferred obs) ├óΓé¼ΓÇ¥ no reward design needed. Russian Doll MCTS ├óΓÇ░╦å Sophisticated Inference: both use tree search; EFE replaces Q-value as node score. Library: `inferactively-pymdp`. Use `deep-q-rl` when full observability + `evaluate(state)` exists.

-53. `median-bifurcation` is the **universal median-cut discriminative signal skill**. Any useful distinction a model or system must learn is a binary median cut. Three-step protocol: choose partition axis ╬ô├Ñ├å produce both sides explicitly (hard negatives baked in, not mined post-hoc) ╬ô├Ñ├å drop unwanted partition at inference. Applied recursively, n bifurcations yield 2^n epistemic cells at zero additional labeling cost. This is data-level contrastive learning: the loss sees ordinary cross-entropy; discriminative pressure comes from the data layout. Inspired by ANOVA factorial designs and k-means via median divisions. `mad-dynamic-batching` is a concrete instantiation for token-length distributions.
+53. `median-bifurcation` is the **universal median-cut discriminative signal skill**. Any useful distinction a model or system must learn is a binary median cut. Three-step protocol: choose partition axis ├óΓÇáΓÇÖ produce both sides explicitly (hard negatives baked in, not mined post-hoc) ├óΓÇáΓÇÖ drop unwanted partition at inference. Applied recursively, n bifurcations yield 2^n epistemic cells at zero additional labeling cost. This is data-level contrastive learning: the loss sees ordinary cross-entropy; discriminative pressure comes from the data layout. Inspired by ANOVA factorial designs and k-means via median divisions. `mad-dynamic-batching` is a concrete instantiation for token-length distributions.

-## MCG Foundation ╬ô├ç├╢ The Conceptual Backbone
+## MCG Foundation ├óΓé¼ΓÇ¥ The Conceptual Backbone

 The skill library is an implementation of the **Meta Context Graph (MCG)** architecture
 (Tekiner, 2025; Hu et al. arXiv:2512.13564) applied to automated software development.
 MCG is the glue that ties gstack (fat operational patterns) to llm-wiki (compiled living
 knowledge): both are instantiated here as the skills themselves (procedural memory) and
@@ -202,29 +203,29 @@ the Pattern Store vetting pipeline (tribal knowledge lifecycle).

 The full MCG system comprises two complementary graphs:

 | MCG Component | Software Dev Equivalent | Skill |
 |---|---|---|
-| Domain KG ╬ô├ç├╢ entities & relationships | Codebase / domain model | `agentic_kg_memory` + `kg_ontology` |
+| Domain KG ├óΓé¼ΓÇ¥ entities & relationships | Codebase / domain model | `agentic_kg_memory` + `kg_ontology` |
 | DKG entity identity layer | Symbol/module canonicalization | `kg_ontology` |
-| Context Graph ╬ô├ç├╢ decision traces (episodic) | learnings.jsonl, per-task rationale | `agentic-harness` |
-| CG patterns (semantic) | Pattern Store pending ╬ô├Ñ├å tenure | `skill-wiki` |
-| CG tribal knowledge (semantic) | Pattern Store promoted entries | `skill-wiki` ╬ô├Ñ├å skill files |
-| CG procedural schemas | **The SKILL.md files themselves** ╬ô├ç├╢ model-agnostic, slot-in primitives | This whole library |
+| Context Graph ├óΓé¼ΓÇ¥ decision traces (episodic) | learnings.jsonl, per-task rationale | `agentic-harness` |
+| CG patterns (semantic) | Pattern Store pending ├óΓÇáΓÇÖ tenure | `skill-wiki` |
+| CG tribal knowledge (semantic) | Pattern Store promoted entries | `skill-wiki` ├óΓÇáΓÇÖ skill files |
+| CG procedural schemas | **The SKILL.md files themselves** ├óΓé¼ΓÇ¥ model-agnostic, slot-in primitives | This whole library |
 | L4 Runtime state | Session / active context | `continuity-log`, `memory-bank` |
 | L3 Organisation conventions | Team / project norms | `memory-bank` project brief |
 | L2 Industry / domain | Domain KG per project | `agentic_kg_memory` |
 | L1 Universal best practices | Base skill library | This repo |

 **The skills are procedural memory** (CoALA taxonomy, arXiv:2309.02427). They cannot be
-summarized into a prompt and RAG-retrieved with equal effect ╬ô├ç├╢ they must be invoked. This
+summarized into a prompt and RAG-retrieved with equal effect ├óΓé¼ΓÇ¥ they must be invoked. This
 is the distinction between a great chef's accumulated technique and a recipe book. The
-Pattern Store vetting pipeline (3 applications ╬ô├Ñ├å promote) implements the tribal knowledge
-lifecycle from MCG: `tk_candidates` ╬ô├Ñ├å reviewed ╬ô├Ñ├å `tribal_knowledge` (active rule) ╬ô├Ñ├å
+Pattern Store vetting pipeline (3 applications ├óΓÇáΓÇÖ promote) implements the tribal knowledge
+lifecycle from MCG: `tk_candidates` ├óΓÇáΓÇÖ reviewed ├óΓÇáΓÇÖ `tribal_knowledge` (active rule) ├óΓÇáΓÇÖ
 compiled into a skill.

-For the full architecture, see `agentic_kg_memory/SKILL.md Γö¼┬║ MCG Foundation`.
+For the full architecture, see `agentic_kg_memory/SKILL.md ├é┬º MCG Foundation`.

 ## Repository Layout

 - `<skill>\\SKILL.md` -> canonical skill contract
 - `copilot-instructions.md` -> repo-wide Copilot guidance
@@ -257,14 +258,14 @@ For the full architecture, see `agentic_kg_memory/SKILL.md Γö¼┬║ MCG Foundation`

 Use this README as the live-skill audit source of truth for the concepts that were still unresolved in `integrate/compiled.md`. They are now fully dispositioned through promotion into the live graph or explicit absorption into existing skills.

 | `integrate/compiled.md` concept | Live disposition |
 |---|---|
-| `build-observability` | **live skill** ╬ô├Ñ├å `build-observability` |
-| `codebase-knowledge-graph` | **live skill** ╬ô├Ñ├å `codebase-knowledge-graph` |
-| `fat-skills` | **closed by absorption** ╬ô├Ñ├å `skill-wiki` + `agentic-harness` + repo routing guidance + memory / governance split |
-| `dev-pipeline` | **closed by absorption** ╬ô├Ñ├å `react-agent` + `openspec-workflow` + execution skills + `agentic-harness` + supporting release / safety lanes |
+| `build-observability` | **live skill** ├óΓÇáΓÇÖ `build-observability` |
+| `codebase-knowledge-graph` | **live skill** ├óΓÇáΓÇÖ `codebase-knowledge-graph` |
+| `fat-skills` | **closed by absorption** ├óΓÇáΓÇÖ `skill-wiki` + `agentic-harness` + repo routing guidance + memory / governance split |
+| `dev-pipeline` | **closed by absorption** ├óΓÇáΓÇÖ `react-agent` + `openspec-workflow` + execution skills + `agentic-harness` + supporting release / safety lanes |

 ## Design Principles

 - Skills should be composable rather than monolithic.
 - Policy, implementation, and tracking should be separated when they have different responsibilities.
@@ -276,17 +277,17 @@ Use this README as the live-skill audit source of truth for the concepts that we
 ## Living Skill Library

 Skills compound over time. Each skill accumulates evidence (EVIDENCE.md) and changelog history (HISTORY.md) alongside its behavioral contract (SKILL.md). The governance lifecycle is:

 ```
-integrate/          ╬ô├Ñ├ë raw intake (awesome-copilot, gstack, llm-wiki, etc.)
-integrate/staged/   ╬ô├Ñ├ë validated concepts awaiting promotion
-<skill>/SKILL.md    ╬ô├Ñ├ë active behavioral contract (status: active)
-<superseded>        ╬ô├Ñ├ë retired skills (status: superseded, superseded_by: <name>)
+integrate/          ├óΓÇá┬É raw intake (awesome-copilot, gstack, llm-wiki, etc.)
+integrate/staged/   ├óΓÇá┬É validated concepts awaiting promotion
+<skill>/SKILL.md    ├óΓÇá┬É active behavioral contract (status: active)
+<superseded>        ├óΓÇá┬É retired skills (status: superseded, superseded_by: <name>)
 ```

-Promotion gate: one Tier-1/2 evidence item + one local validation, OR two independent Tier-1╬ô├ç├┤3 items from distinct source types. See `skill-wiki/SKILL.md` for the full governance contract.
+Promotion gate: one Tier-1/2 evidence item + one local validation, OR two independent Tier-1├óΓé¼ΓÇ£3 items from distinct source types. See `skill-wiki/SKILL.md` for the full governance contract.

 SKILL.md frontmatter fields:
 ```yaml
 status: active          # raw | staged | active | superseded
 last_validated: YYYY-MM-DD
@@ -328,11 +329,11 @@ This library is optimized for automated software development. Skill-to-pipeline
 | Context window management and compaction | `context-compaction` |
 | MCP tool registration and routing | `mcp-tool-registry` |
 | Offline batch eval, regression detection | `checklist` (eval-pipeline section) |
 | Hyperparameter search / training | `optuna-nested-cv`, `mlflow` |
 | Imbalanced classifier class weights | `class-balancing` |
-| PDF╬ô├Ñ├åenriched-Markdown pipeline | `pdf-extraction` |
+| PDF├óΓÇáΓÇÖenriched-Markdown pipeline | `pdf-extraction` |
 | Semantic knowledge retrieval | `agentic_kg_memory`, `gist-retriever` |
 | Cross-session episodic recall | `agentic_kg_memory` (episodic section) |
 | RL from code execution feedback | `deep-q-rl` (code-rl section) |
 | SPO / DPO / offline preference optimization | `deep-q-rl` (SPO section) |
 | Reward function design, binary vs graded rewards | `deep-q-rl` (SPO section) |
@@ -346,31 +347,31 @@ This library is optimized for automated software development. Skill-to-pipeline
 - **2026-05-09**: Promoted `crystallization` into a standalone live skill. `skill-wiki` now owns routing and staged skill-library deltas, `crystallization` owns the actual work-chain distillation protocol, and `agentic_kg_memory` owns digest ingestion and graph updates.
 - **2026-05-02**: Promoted `build-observability` and `codebase-knowledge-graph` from unresolved `integrate/compiled.md` concepts into live skills. `build-observability` now owns the normalized `runs/events/commands` observability contract and projection/dashboard pattern; `codebase-knowledge-graph` now owns current-repo whole-system mapping, foundational-vs-incidental classification, and ripple analysis before edits.
 - **2026-05-09**: Imported `model-size-reduction` and `generalization-theory` from the local research/wiki intake. `model-size-reduction` now owns architecture-agnostic Hugging Face checkpoint slimming and delta sparsification; `generalization-theory` now owns the eNTK signal-vs-noise diagnostic lens for memorization, grokking, and noisy-preference fine-tuning.
 - **2026-05-02**: Explicitly closed the `fat-skills` and `dev-pipeline` umbrella concepts by absorption rather than promotion. `fat-skills` is now documented as split across `skill-wiki`, `agentic-harness`, repo-level routing guidance, and the existing memory / governance surfaces; `dev-pipeline` is documented as split across `react-agent`, `openspec-workflow`, the execution skills, and `agentic-harness`.
 - **2026-05-02**: Grounded the `agentic-harness` evaluation lane in `DSPy` and `TextGrad`. Added `integrate/dspy.md` and `integrate/textgrad.md`, extended `integrate/compiled.md` with `optimizer-driven-evaluation`, and updated the live `agentic-harness` skill to distinguish structured audit (`checklist`) from metric/reward compile-refine loops (DSPy) and textual-loss refinement loops (TextGrad).
-- **2026-05-02**: Added `class-balancing` (log inverse freq ╬ô├Ñ├å Box-Cox ╬ô├Ñ├å ratio weights for imbalanced classifiers) and `pdf-extraction` (full docling pipeline + table enhancement via tabula+camelot+VLM fusion). `hyper-parm_tuning` now frames Weighted Stage Allocation as the canonical cross-skill pattern; `agentic-hyperparm` is the agent-specific instantiation. `arxiv-bridge` was updated with CLI flags and a sequential-only warning.
+- **2026-05-02**: Added `class-balancing` (log inverse freq ├óΓÇáΓÇÖ Box-Cox ├óΓÇáΓÇÖ ratio weights for imbalanced classifiers) and `pdf-extraction` (full docling pipeline + table enhancement via tabula+camelot+VLM fusion). `hyper-parm_tuning` now frames Weighted Stage Allocation as the canonical cross-skill pattern; `agentic-hyperparm` is the agent-specific instantiation. `arxiv-bridge` was updated with CLI flags and a sequential-only warning.
 - Imported the portable OpenSpec/Fabro skill family as live agent skills: `openspec-workflow`, `openspec-propose`, `openspec-explore`, `openspec-apply-change`, `openspec-archive-change`, and `fabro-create-workflow`. Current rollout is agent-only first; any dark-factory pipeline promotion remains a separate second pass.
-- **Wave 3 Pareto additions** (Tier 3, scores 6╬ô├ç├┤9): `autoresearch` (new skill); `context-engineering` section ╬ô├Ñ├å `code`; `eval-pipeline` section ╬ô├Ñ├å `checklist`; `agent-as-ci-gate` full protocol ╬ô├Ñ├å `agent-governance`; `code-rl` section ╬ô├Ñ├å `deep-q-rl`. All 15 Pareto candidates now implemented.
+- **Wave 3 Pareto additions** (Tier 3, scores 6├óΓé¼ΓÇ£9): `autoresearch` (new skill); `context-engineering` section ├óΓÇáΓÇÖ `code`; `eval-pipeline` section ├óΓÇáΓÇÖ `checklist`; `agent-as-ci-gate` full protocol ├óΓÇáΓÇÖ `agent-governance`; `code-rl` section ├óΓÇáΓÇÖ `deep-q-rl`. All 15 Pareto candidates now implemented.
 - **Super System Prompt extraction finished**: added `documentation` (timestamped-vs-cumulative doc strategy) and `response-style` (voice preservation, anti-cliche prose, user-facing coherence).
-- **Wave 2 Pareto additions** (Tier 2, scores 12╬ô├ç├┤16): `context-compaction`, `security-review`, `mcp-tool-registry` (new skills); `self-repair` section ╬ô├Ñ├å `debugging`; `hierarchical-task-planning` section ╬ô├Ñ├å `agentic-harness`; `episodic-memory` section ╬ô├Ñ├å `agentic_kg_memory`.
-- **Wave 1 Pareto additions** (Tier 1, all score ╬ô├½├æ 20): `evaluator-optimizer`, `multi-agent-coordination`, `tdd-agent`, `agent-governance`. Fills the largest gaps: iterative generation loop, team topology, test-first lifecycle, and safety rails.
+- **Wave 2 Pareto additions** (Tier 2, scores 12├óΓé¼ΓÇ£16): `context-compaction`, `security-review`, `mcp-tool-registry` (new skills); `self-repair` section ├óΓÇáΓÇÖ `debugging`; `hierarchical-task-planning` section ├óΓÇáΓÇÖ `agentic-harness`; `episodic-memory` section ├óΓÇáΓÇÖ `agentic_kg_memory`.
+- **Wave 1 Pareto additions** (Tier 1, all score ├óΓÇ░┬Ñ 20): `evaluator-optimizer`, `multi-agent-coordination`, `tdd-agent`, `agent-governance`. Fills the largest gaps: iterative generation loop, team topology, test-first lifecycle, and safety rails.
 - **MCG grounding pass**: Grounded the full skill library in the Meta Context Graph (MCG) architecture (Tekiner 2025, Hu et al. arXiv:2512.13564, CoALA arXiv:2309.02427, ACE arXiv:2510.04618). Added MCG Foundation section to README, MCG Architecture section to `agentic_kg_memory/SKILL.md`, and MCG terminology alignment to `skill-wiki` Pattern Store.
 - **Restored `kg_ontology` to `status: active`**: The prior merge into `agentic_kg_memory` was architecturally wrong. `kg_ontology` owns the DKG entity-identity layer (synset/hypernym BM25 canonicalization); `agentic_kg_memory` owns the CG retrieval side. Two distinct MCG concerns.
 - Added `deep-research` as a child of `agentic-harness`: LangGraph research graph with Selenium fallback fetch pipeline.
 - Reframed `agentic-harness` as the multi-framework stationmaster.
 - Added `continuity-log` to preserve compact-safe reasoning products between long turns and compactions.
 - Absorbed `integrate\\llm-wiki` into existing live skills instead of promoting it as a standalone branch: compiled memory behavior now lives in `agentic_kg_memory`, staged retrieval behavior in `gist-retriever`, and the project-vs-corpus boundary in `memory-bank`.
 - Second-pass absorption of `integrate\\llm-wiki`: added consolidation tiers (working/episodic/semantic/procedural), temporal decay, supersession, automation hooks, graph traversal for discovery, and an initial crystallization contract to `agentic_kg_memory`. That protocol has since been promoted into the standalone `crystallization` skill.
 - Added `deep-q-rl` under new `learning/` section: DQN + Russian Doll MCTS pattern generalized from chess-deep-q; applies to any scored discrete-action environment.
-- Merged `hyper-parm_tuning` ╬ô├Ñ├å `optuna-nested-cv`: Methodology Primer section (preconditions checklist, layerwise decomposition, structured search protocol, sampler policy for LLM judges, search space type guide). `hyper-parm_tuning` is now `status: superseded`.
+- Merged `hyper-parm_tuning` ├óΓÇáΓÇÖ `optuna-nested-cv`: Methodology Primer section (preconditions checklist, layerwise decomposition, structured search protocol, sampler policy for LLM judges, search space type guide). `hyper-parm_tuning` is now `status: superseded`.
 - Fattened `agentic-harness` with gstack-derived patterns: Learnings Compounding (learnings.jsonl schema, 4 persistence layers), Automated Dev Pipeline (Autoship state machine), Review Army (7 specialists + adaptive ceremony), Context Compaction During Long Runs.
 - Fattened `deep-research` with research epistemology: Perspective Diversity (STORM), Source Quality Hierarchy (5-tier), Per-Role Model Strategy, Citation Chain Integrity, Research Anti-Patterns.
-- Added Pattern Store vetting mechanism to `skill-wiki/SKILL.md`: vector store as pre-skill staging, 3-application tenure threshold, confidence decay formula (`e^(-0.1 Γö£├╣ months)`), prune gate, promotion pipeline ╬ô├Ñ├å `integrate/staged/`.
+- Added Pattern Store vetting mechanism to `skill-wiki/SKILL.md`: vector store as pre-skill staging, 3-application tenure threshold, confidence decay formula (`e^(-0.1 ├âΓÇö months)`), prune gate, promotion pipeline ├óΓÇáΓÇÖ `integrate/staged/`.
 - All live and retained-historical `SKILL.md` files now carry `status:` governance frontmatter. `hyper-parm_tuning` remains the preserved superseded predecessor.
 - Added `design-patterns`, `agentic-design-patterns`, and `substrate-selection` as distinct skills so code pattern choice, LangGraph workflow shape, and runtime selection no longer collapse into `agentic-harness`.
 - Absorbed `integrate/gstack` ETHOS: "Boil the Lake" (completeness is cheap with AI) into `code/SKILL.md`; "Search Before Building" (3-layer knowledge taxonomy) into `code/SKILL.md`.
 - Absorbed `integrate/gstack/investigate` Iron Law (no fix without root cause) and 5-phase debugging protocol into `debugging/SKILL.md`.
 - Added Skill Routing section to `copilot-instructions.md` mapping request types to skills (pattern from gstack CLAUDE.md).
 - Added `## Applicability Envelope` to `agentic-harness/SKILL.md` and `debugging/SKILL.md` as template for all live skills.
 - Living Skill Library infrastructure: `integrate/README.md`, `integrate/staged/README.md`, `agentic-harness/EVIDENCE.md`, `agentic-harness/HISTORY.md`.
-- Added "Living Skill Library" lifecycle documentation and "Automated Software Development Pipeline" mapping to `README.md`.
\ No newline at end of file
+- Added "Living Skill Library" lifecycle documentation and "Automated Software Development Pipeline" mapping to `README.md`.

  === END MERGE CONTEXT =============================================

  [skill-sync] Agent: produce the merged file and paste below.
  [skill-sync] Paste merged content, then enter a line with only: ###END
 :
PS C:\Users\user\Documents\dev\skills> .\sync_skills.ps1
At C:\Users\user\Documents\dev\skills\sync_skills.ps1:222 char:23
+         Write-Host "  Conflict diff written to: $conflictFile" -Foreg ...
+                       ~~~~~~~~
Unexpected token 'Conflict' in expression or statement.
At C:\Users\user\Documents\dev\skills\sync_skills.ps1:476 char:28
+                     } else {
+                            ~
Missing closing '}' in statement block or type definition.
At C:\Users\user\Documents\dev\skills\sync_skills.ps1:467 char:53
+                 } elseif ($syncCase -eq 'conflict') {
+                                                     ~
Missing closing '}' in statement block or type definition.
At C:\Users\user\Documents\dev\skills\sync_skills.ps1:460 char:32
+             if ($resp -eq 'y') {
+                                ~
Missing closing '}' in statement block or type definition.
At C:\Users\user\Documents\dev\skills\sync_skills.ps1:441 char:40
+         foreach ($item in $needsMerge) {
+                                        ~
Missing closing '}' in statement block or type definition.
At C:\Users\user\Documents\dev\skills\sync_skills.ps1:408 char:34
+     if ($needsMerge.Count -gt 0) {
+                                  ~
Missing closing '}' in statement block or type definition.
At C:\Users\user\Documents\dev\skills\sync_skills.ps1:366 char:120
+ ... -gt 0 -or $staleFolders.Count -gt 0) -and -not $skipReconciliation) {
+                                                                         ~
Missing closing '}' in statement block or type definition.
At C:\Users\user\Documents\dev\skills\sync_skills.ps1:157 char:9
+     try {
+         ~
Missing closing '}' in statement block or type definition.
At C:\Users\user\Documents\dev\skills\sync_skills.ps1:477 char:118
+ ...  : $($item.Rel) (manual merge required â€” see .conflict file)" -Fore ...
+                                                                  ~
The Try statement is missing its Catch or Finally block.
At C:\Users\user\Documents\dev\skills\sync_skills.ps1:153 char:82
+ ... ke-LlmMerge($relPath, $baseContent, $masterContent, $mirrorContent) {
+                                                                         ~
Missing closing '}' in statement block or type definition.
Not all parse errors were reported.  Correct the reported errors and try again.
    + CategoryInfo          : ParserError: (:) [], ParseException
    + FullyQualifiedErrorId : UnexpectedToken

PS C:\Users\user\Documents\dev\skills> .\sync_skills.ps1

------------------------------------------------------------
  Reading last commit timestamp
------------------------------------------------------------
  Last commit : 05/25/2026 15:19:44
  Master      : C:\Users\user\Documents\dev\skills
  Master clean: no

------------------------------------------------------------
  Checking for skill folders missing from master
------------------------------------------------------------
  None.

------------------------------------------------------------
  Checking tracked .md files newer than last commit
------------------------------------------------------------
  [OK] C:\Users\user\.copilot\skills -- no locally-modified files
  [OK] C:\Users\user\.config\opencode\skills -- no locally-modified files

------------------------------------------------------------
  Syncing master -> local mirrors
------------------------------------------------------------
  -> C:\Users\user\.copilot\skills
     OK (exit 1)
  -> C:\Users\user\.config\opencode\skills
     OK (exit 1)

------------------------------------------------------------
  Deploying opencode config files
------------------------------------------------------------
  Deployed: opencode.json -> C:\Users\user\.config\opencode\opencode.json
  Deployed: oh-my-opencode-slim.json -> C:\Users\user\.config\opencode\oh-my-opencode-slim.json
  Deployed: orchestrator.md -> C:\Users\user\.config\opencode\oh-my-opencode-slim\orchestrator.md
  Deployed: orchestrator.agent.md -> C:\Users\user\.config\opencode\oh-my-opencode-slim\orchestrator.deepseek.md
  Deployed: orchestrator.gemma.md -> C:\Users\user\.config\opencode\oh-my-opencode-slim\orchestrator.gemma.md
  NOTE: orchestrator prompt variants are deployed from source templates.
        DeepSeek: agents\orchestrator.agent.md -> orchestrator.deepseek.md
        Gemma   : agents\orchestrator.gemma.md -> orchestrator.gemma.md

------------------------------------------------------------
  Remote: root@192.168.3.17:/root/.copilot/skills
------------------------------------------------------------
  Option A -- WinSCP CLI (if winscp.com is on PATH):
    winscp.com /command `
      "open sftp://root@192.168.3.17" `
      "synchronize remote -filemask=""|.git/;.gitignore;.copilot/;.config/;.DS_Store;.*/;pytest_cache/;todo/;react_agent/;__pycache__/;copilot/;$Recycle.Bin/;$AV_ASW/;$AV_ASW$VAULT/;*[0-9a-f][0-9a-f][0-9a-f][0-9a-f]*""  ""C:\Users\user\Documents\dev\skills"" /root/.copilot/skills" `
      "exit"

  Option B -- rsync (via WSL or Git Bash):
    rsync -avz --delete --exclude='.*' "C:/Users/user/Documents/dev/skills" root@192.168.3.17:/root/.copilot/skills

  Option C -- Manual WinSCP:
    Host    : 192.168.3.17
    User    : root
    Remote  : /root/.copilot/skills
    Local   : C:\Users\user\Documents\dev\skills
  Mode    : Mirror (remote = local, delete extras)

Launch WinSCP now? [y/n]: y
  SSH username (default: root):
  SSH password: ********
  Launching WinSCP (override remote)...
Searching for host...
Connecting to host...
Authenticating...
Using username "root".
Authenticating with pre-entered password.
Authenticated.
Starting the session...
Session started.
Active session: [1] root@192.168.3.17
Comparing...
Local 'C:\Users\user\Documents\dev\skills\headless-browser-verification' => Remote '/root/.copilot/skills/headless-browsLocal 'C:\Users\user\Documents\dev\skills\semantic-search-enrichment' => Remote '/root/.copilot/skills/semantic-search-eLocal 'C:\Users\user\Documents\dev\skills\test-planner' => Remote '/root/.copilot/skills/test-planner'                  Local 'C:\Users\user\Documents\dev\skills\nearest-neighbor-chain' => Remote '/root/.copilot/skills/nearest-neighbor-chaiLocal 'C:\Users\user\Documents\dev\skills\smoke_tests' => Remote '/root/.copilot/skills/smoke_tests'                    Local 'C:\Users\user\Documents\dev\skills\plugins\model-router\agents' => Remote '/root/.copilot/skills/plugins/model-roLocal 'C:\Users\user\Documents\dev\skills\plugins\oh-my-opencode-slim' => Remote '/root/.copilot/skills/plugins/oh-my-opLocal 'C:\Users\user\Documents\dev\skills\causal-inference' => Remote '/root/.copilot/skills/causal-inference'          Local 'C:\Users\user\Documents\dev\skills\kg_ontology\enhancements' => Remote '/root/.copilot/skills/kg_ontology/enhanceLocal 'C:\Users\user\Documents\dev\skills\stratified-quota-sampling' => Remote '/root/.copilot/skills/stratified-quota-sLocal 'C:\Users\user\Documents\dev\skills\checklist' => Remote '/root/.copilot/skills/checklist'                        Local 'C:\Users\user\Documents\dev\skills\agentic_kg_memory\enhancements' => Remote '/root/.copilot/skills/agentic_kg_meLocal 'C:\Users\user\Documents\dev\skills\agentic-harness' => Remote '/root/.copilot/skills/agentic-harness'            Local 'C:\Users\user\Documents\dev\skills\memory-bank\projects\skills' => Remote '/root/.copilot/skills/memory-bank/projLocal 'C:\Users\user\Documents\dev\skills\mlflow' => Remote '/root/.copilot/skills/mlflow'                              Local 'C:\Users\user\Documents\dev\skills\representation-pipeline' => Remote '/root/.copilot/skills/representation-pipelLocal 'C:\Users\user\Documents\dev\skills\request-intent-resolution' => Remote '/root/.copilot/skills/request-intent-resLocal 'C:\Users\user\Documents\dev\skills\timeout-guard' => Remote '/root/.copilot/skills/timeout-guard'                Local 'C:\Users\user\Documents\dev\skills\gist_correlation_matrix' => Remote '/root/.copilot/skills/gist_correlation_matLocal 'C:\Users\user\Documents\dev\skills\siamese_from_correlation_matrix' => Remote '/root/.copilot/skills/siamese_fromLocal 'C:\Users\user\Documents\dev\skills\spiral-radial-clustering-display' => Remote '/root/.copilot/skills/spiral-radiLocal 'C:\Users\user\Documents\dev\skills\skill-wiki' => Remote '/root/.copilot/skills/skill-wiki'                      Local 'C:\Users\user\Documents\dev\skills\skill-wiki\enhancements' => Remote '/root/.copilot/skills/skill-wiki/enhancemeLocal 'C:\Users\user\Documents\dev\skills\evaluator-optimizer' => Remote '/root/.copilot/skills/evaluator-optimizer'    Local 'C:\Users\user\Documents\dev\skills\multi-agent-coordination' => Remote '/root/.copilot/skills/multi-agent-coordinLocal 'C:\Users\user\Documents\dev\skills\tdd-agent' => Remote '/root/.copilot/skills/tdd-agent'                        Local 'C:\Users\user\Documents\dev\skills\context-compaction\enhancements' => Remote '/root/.copilot/skills/context-compLocal 'C:\Users\user\Documents\dev\skills\security-review' => Remote '/root/.copilot/skills/security-review'            Local 'C:\Users\user\Documents\dev\skills\agentic-design-patterns' => Remote '/root/.copilot/skills/agentic-design-patteLocal 'C:\Users\user\Documents\dev\skills\documentation' => Remote '/root/.copilot/skills/documentation'                Local 'C:\Users\user\Documents\dev\skills\openspec-workflow\references' => Remote '/root/.copilot/skills/openspec-workflLocal 'C:\Users\user\Documents\dev\skills\openspec-propose' => Remote '/root/.copilot/skills/openspec-propose'          Local 'C:\Users\user\Documents\dev\skills\openspec-archive-change' => Remote '/root/.copilot/skills/openspec-archive-chaLocal 'C:\Users\user\Documents\dev\skills\fabro-create-workflow' => Remote '/root/.copilot/skills/fabro-create-workflow'Local 'C:\Users\user\Documents\dev\skills\fabro-create-workflow\references' => Remote '/root/.copilot/skills/fabro-creatLocal 'C:\Users\user\Documents\dev\skills\integrate' => Remote '/root/.copilot/skills/integrate'                        Local 'C:\Users\user\Documents\dev\skills\integrate\staged\semantic-pyramid-memory' => Remote '/root/.copilot/skills/intLocal 'C:\Users\user\Documents\dev\skills\integrate\staged\symbolic-memory-compaction' => Remote '/root/.copilot/skills/Local 'C:\Users\user\Documents\dev\skills\integrate\meta-harness' => Remote '/root/.copilot/skills/integrate/meta-harnesLocal 'C:\Users\user\Documents\dev\skills\arxiv-bridge' => Remote '/root/.copilot/skills/arxiv-bridge'                  Local 'C:\Users\user\Documents\dev\skills\codebase-knowledge-graph' => Remote '/root/.copilot/skills/codebase-knowledge-Local 'C:\Users\user\Documents\dev\skills\build-observability' => Remote '/root/.copilot/skills/build-observability'    Local 'C:\Users\user\Documents\dev\skills\disabled\cua-desktop-agent' => Remote '/root/.copilot/skills/disabled/cua-deskLocal 'C:\Users\user\Documents\dev\skills\code-extraction' => Remote '/root/.copilot/skills/code-extraction'            Local 'C:\Users\user\Documents\dev\skills\uncertainty-quantification' => Remote '/root/.copilot/skills/uncertainty-quantLocal 'C:\Users\user\Documents\dev\skills\mergekit' => Remote '/root/.copilot/skills/mergekit'                          Local 'C:\Users\user\Documents\dev\skills\linear-programming-hyperparm-tuning' => Remote '/root/.copilot/skills/linear-pLocal 'C:\Users\user\Documents\dev\skills\agentic-hyperparm-macd' => Remote '/root/.copilot/skills/agentic-hyperparm-macLocal 'C:\Users\user\Documents\dev\skills\universal-filter' => Remote '/root/.copilot/skills/universal-filter'          Local 'C:\Users\user\Documents\dev\skills\ollama-structured' => Remote '/root/.copilot/skills/ollama-structured'
Synchronizing...
Local 'C:\Users\user\Documents\dev\skills' => Remote '/root/.copilot/skills'
C:\...\skills\AGENTS.md   |          31 KB |    0.0 KB/s | binary | 100%
C:\...\bm25-autoencoder   |            0 B |    0.0 KB/s | binary |   0%
C:\...\SKILL.md           |          21 KB |  199.3 KB/s | binary | 100%
C:\...\skills\error.md    |         243 KB | 1698.1 KB/s | binary | 100%
C:\...\skills\README.md   |          53 KB | 1566.1 KB/s | binary | 100%
C:\...\signal-modulation  |            0 B | 1458.3 KB/s | binary |   0%
C:\...\SKILL.md           |          21 KB | 1279.4 KB/s | binary | 100%
C:\...\sync_skills.ps1    |          32 KB | 1255.7 KB/s | binary | 100%
Local 'C:\Users\user\Documents\dev\skills\bm25-corpus-sampling' => Remote '/root/.copilot/skills/bm25-corpus-sampling'
C:\...\_collinearity.py   |           6 KB | 1053.4 KB/s | binary | 100%
C:\...\_dryrun.py         |           1 KB |  838.6 KB/s | binary | 100%
C:brown_retrieval_eval.py |          39 KB |  814.8 KB/s | binary | 100%
C:\...\retrieval_eval.db  |       43324 KB | 18790.2 KB/s | binary | 100%
C:\...\SKILL.md           |          30 KB | 18556.0 KB/s | binary | 100%
Local 'C:\Users\user\Documents\dev\skills\plugins\oh-my-opencode-slim' => Remote '/root/.copilot/skills/plugins/oh-my-opencode-slim'
oh-my-opencode-slim.json  |          23 KB | 18325.0 KB/s | binary | 100%
C:\...\opencode.json      |           6 KB | 16892.8 KB/s | binary | 100%

------------------------------------------------------------
  Done
------------------------------------------------------------
PS C:\Users\user\Documents\dev\skills>