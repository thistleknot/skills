# Skill Inventory

20 planned skills extracted from 21 source documents. Descriptions state trigger conditions and what problem each solves. No implementations defined here.

---

## Epistemics & Reasoning

### 01 � `reasoning-protocol`

Activate when a claim needs to be built rather than retrieved � evaluating a hypothesis, validating premises before acting, or reasoning under uncertainty where the wrong frame corrupts downstream work.

**Key features**
- FOL formalization: entities/predicates as P(S,[O]), observed vs inferred tagging
- Premise validation before building on them; "confidently wrong" prevention
- Six Thinking Hats multi-perspective sweep + SME hat
- Anti-sycophancy guard � mirror test, challenge before accepting
- System I / System II two-pass integration via Executive Function
- OODA loop mapped to scientific method stages
- Deductive ? inductive ? abductive reasoning chain made explicit
- Syllogism as output format: observed/inferred premises ? abductive throughlines
- Negative inference / Diaresis for scope narrowing
- Confidence calibration: "insufficient information" is a valid response
- Latent knowledge activation � 2�3 domain hops before answering
- Reframe-before-responding � state actual need, distinguish from stated goal
- TRIZ heuristics for hypothesis construction

**Sources:** `ssp.md`, `sspv2.md`

---

## Code Engineering

### 02 � `code-engineering`

Activate on any coding task involving structure, design decisions, naming, or interface contracts. The territory above syntax but below architecture.

**Key features**
- Data-centric code organization: inputs ? classes ? functions ? main
- Gang of Four pattern selection-by-pressure (Creational / Structural / Behavioral)
- Require / Guarantee / Maintain / Assert contracts at interfaces
- Pragmatic Programmer: DRY, orthogonality, tracer bullets, plain text first
- Naming discipline � no temporal/subjective adjectives (optimized, enhanced, v2)
- Docstrings: purpose + preconditions + failure modes, not boilerplate
- Try/except discipline: fail fast on critical paths, acceptable elsewhere
- Whole-function update protocol: scope limitation, never snippets
- Abstract class design from FOL entity/predicate analysis
- Three-pass refactoring: deduplicate ? merge functions ? move main last
- sqlite load-if-exists checkpointing for heavy computations
- Stack defaults: fastapi, pydantic, sqlite, gradio/streamlit, fastmcp

**Sources:** `ssp.md`, `sspv2.md`

---

### 03 � `debugging-protocol`

Activate when a defect needs diagnosis rather than a patch. Structures isolation so the fix space is known before any code changes.

**Key features**
- Diaresis method: divide into working vs broken, logic vs data vs environment
- Salience-based scope tiers: high / medium / low / ignore relative to error line
- Iterative scale: 5?10?20?40?80 records before full pipeline
- Error schema checklist: rogue n/a, duplicate keys, missing fields, wrong joins, off-by-one, type mismatches, duplicate function definitions
- Pivot rule: stop patching if the same class of error repeats, revisit approach
- Autonomous iteration: run/observe/fix/rerun without asking on syntax/schema/logic failures
- Assert-at-checkpoint validation: actual vs expected at each pipeline stage
- 4-phase structure (from gstack `investigate`): gather evidence ? isolate variable ? hypothesize ranked causes ? implement with confirmed root cause
- Iron Law: no code change without confirmed root cause

**Sources:** `ssp.md`, `sspv2.md`, `gstack.md`

---

### 04 � `codebase-knowledge-graph`

Activate when an agent or developer needs to reason about a codebase as a whole interconnected system rather than flat files. Addresses the failure mode where LLMs produce duplicate functionality, inconsistent patterns, and context-blind changes.

**Key features**
- Hierarchical knowledge graph model: modules/files/classes/functions as typed nodes with semantic edges
- Junior-vs-senior framing: what/how (implementation) vs why/what-if (system-level)
- Distinguishing foundational from incidental code before any change
- Whole-system ripple effect analysis prior to edits
- LLM failure modes: context loss in large repos, duplicate functionality, inconsistent pattern application

**Sources:** `The_day_I_taught_AI.md`

---

### 05 � `documentation-strategy`

Activate when deciding how to record significant changes, track project evolution, or structure reference material.

**Key features**
- Timestamped vs cumulative changelog decision criteria (timestamped for 4+ critical changes or 50+ files; cumulative for routine incremental work)
- Documentation lifecycle: session file ? commit ? folder if sprawling ? quarterly consolidation
- First-principles docstring structure: thesis + necessary conditions as P(S,[O]) + workflow state machine + design decisions + invariants + error handling + usage patterns + extension points
- Archiving discipline: clean old artifacts, unify filenames, no date/number sprawl

**Sources:** `ssp.md`

---

## Memory & Knowledge

### 06 � `memory-architecture`

Reference skill for designing memory layers before building. Prevents the vector-only trap and episodic dump anti-patterns by providing a taxonomy and four concrete design templates.

**Key features**
- Five-layer stack: implicit / semantic / episodic / procedural / working
- Three-paradigm cognitive taxonomy: implicit / explicit / agentic
- Forms / functions / dynamics framework
- Biological-to-AI crosswalk: hippocampus, prefrontal cortex ? agent structures
- Neuro-symbolic dual-process axis: System 1 (neural/fuzzy) vs System 2 (symbolic/exact)
- Four design templates: RAG-lite, Personal Assistant, Autonomous Agent, Research Pipeline
- Anti-patterns catalog: vector-only, episodic dump, no entity anchors, no decay policy, manual-only procedures
- Query classification ? memory routing decision tree

**Sources:** `agentic-memory.md`, `Meta_Knowledge_Graphs.md`, `A-MEM paper`, `MemRL paper`

---

### 07 � `memory-lifecycle`

Activate when a memory system needs to stay healthy over time rather than accumulate indefinitely.

**Key features**
- Confidence scoring: source count + recency + contradiction weight + time decay
- Supersession: new info links to and marks old as stale, not overwrites
- Ebbinghaus-style forgetting: exponential decay, reinforcement resets the curve
- Consolidation tiers: working ? episodic ? semantic ? procedural
- Type-aware compaction: factual / experiential / working annotation on PreCompact packets
- Eviction ordering: factual kept, experiential via decay, working evicted first
- Budget allocation: 80% factual / 15% experiential / 5% working
- Rehydration ordering by stability layer (factual first, working last)

**Sources:** `llm-wiki.md`, `agentic-memory.md`, `Meta_Knowledge_Graphs.md`

---

### 08 � `procedural-memory`

Activate when an agent needs to discover, store, and reuse multi-step procedures across sessions � not just facts. Implements the SK-Gen pipeline with hybrid retrieval.

**Key features**
- Raw episodic traces ? PrefixSpan sequential pattern mining
- LLM quality verification (0.0�1.0 rubric) for candidate procedures
- Procedural DAG construction with START/GOAL anchors and edge attributes
- Dual-index vectors: goal-level (title-like) + step-level (body-like) embeddings
- EMA updates on index vectors to prevent catastrophic forgetting
- Transition count statistics for probabilistic step ordering
- Cross-session knowledge fusion: merge single-path DAGs into multi-path DAGs
- Hybrid retrieval: System 1 neural (BM25+NLI+vector) + System 2 symbolic (DAG traversal) via RRF
- Query classifier: factual / constraint / procedural / open-ended routing
- Skill discovery from continuity logs: quality thresholds 0.6/0.8/1.0, rate limit 3 proposals/scan

**Sources:** `agentic-memory.md`, `A-MEM paper`

---

### 09 � `llm-wiki`

Activate when building a knowledge base that should get richer with every source rather than re-deriving answers each query. The wiki sits between raw sources and answers as a maintained, compounding artifact.

**Key features**
- Three-layer architecture: raw sources (immutable) ? wiki pages (LLM-owned) ? schema document (operating contract)
- Ingest: one source touches 10�15 pages via cross-reference updates
- Query: search pages ? synthesize with citations ? optionally file answer back as new page
- Lint: contradictions, stale claims, orphan pages, broken cross-references
- `index.md` (content catalog) + `log.md` (append-only chronology)
- Entity extraction with typed relationships: uses / depends-on / contradicts / caused / supersedes
- Graph traversal queries starting from entity nodes
- Hybrid search: BM25 + vector + graph traversal + RRF fusion
- Event-driven automation hooks: on source / session-start / session-end / query / memory-write / schedule
- Quality scoring + self-healing + contradiction resolution with human override
- Crystallization: completed work chains ? structured digest filed as wiki page
- Governance: audit trail, sensitive data filtering, reversible bulk ops, mesh sync, shared/private scoping
- Output variety: markdown, comparison tables, timelines, dependency graphs, slide decks, JSON/CSV

**Sources:** `llm-wiki.md`, `llm-wiki-pattern-topology.md`, `RAG_LLM_Wiki_or_GBrain.md`

---

### 10 � `context-graph`

Activate when a system needs to remember not just what it knows but how and why decisions were made � meta-knowledge rather than object-knowledge. The second project should be faster than the first; the tenth nearly automatic.

**Key features**
- Decision trace schema: type + choice + rationale + confidence + outcome + schema_version + timestamp
- Pattern nodes (success_rate + applicable_domains) and tribal knowledge nodes
- Typed relationships: MADE_DECISION / BASED_ON / INFORMED_BY / PRECEDED_BY
- Four metadata source types: user-provided / system-inferred / integrated ontologies / agent-generated
- Four-layer context hierarchy: universal ? industry ? company ? project/runtime
- Three memory functions: episodic (decision traces) / semantic (patterns + tribal knowledge) / procedural (proven schemas + resolution DAGs)
- Multi-agent kitchen brigade: Document / Schema / Extraction / Resolution / Validation / Feedback agents
- Accuracy compounding: corrections ? patterns ? applied to future runs
- Repeatability: proven-schema retrieval via graph queries
- Governance: human-in-loop, immutable audit, RBAC, schema evolution + stale-pattern detection
- Scale: index on type/timestamp/project_id, cold-storage archival for older decisions

**Sources:** `Meta_Knowledge_Graphs.md`, `agentic-memory.md`

---

## Agent Infrastructure

### 11 � `harness-control-plane`

Activate when designing or migrating agentic runtime infrastructure. Reference for the control-plane patterns proven in OpenClaw � the most portable value is the execution contract, not the product surface.

**Key features**
- Gateway daemon: long-lived host-local authority over sessions, tools, channels, events
- Typed WebSocket API + App SDK for external clients
- Multi-agent routing: per-agent workspace + agentDir + session store + auth profiles
- Session model: lifecycle, tools (list/history/send/spawn/yield/status), routing by source type
- Serialized agent loop + lane-aware queue + write locks for concurrency safety
- ACP harness bridging: normalize claude/codex/copilot/cursor/gemini/opencode/pi under one surface
- Skill loader: multiple roots, deterministic precedence, allowlists, load-time gating by env/bin/OS
- Plugin SDK with harness registration seam (`registerAgentHarness`)
- Bundle adapters: Codex/Claude/Cursor content packs ? native skills/hooks/MCP/LSP defaults
- Sandbox: modes (off/non-main/all) � scopes (agent/session/shared) � backends (docker/ssh/openshell)
- Model failover + auth rotation: 2-stage, selection-source-aware policy, durable failure state
- Background task ledger: first-class tracked records, push delivery, runtime-aware reconciliation
- Automation: cron (persistent jobs, delivery control, model/tool overrides), webhooks, hooks

**Sources:** `open-claw.md`

---

### 12 � `harness-evolution`

Activate when improving an agent harness iteratively against a benchmark rather than tuning prompts. The model is fixed; only the harness workspace is editable.

**Key features**
- AHE outer loop: ROLLOUT ? CLEAN ? ATTRIBUTE ? ROLLBACK ? AGENT_DEBUGGER ? EVOLVE ? COMMIT
- ROLLOUT: k traces per task for pass@1 stability
- CLEAN: strip base64 + deduplicate tool output
- ATTRIBUTE: compare prior manifest predictions vs observed deltas (iteration 2+)
- ROLLBACK: revert rejected edits at file granularity
- AGENT_DEBUGGER: per-task failure/success reports + benchmark overview
- EVOLVE: propose edits with predicted fix set + regression risk per edit
- COMMIT: versioned git commit with change manifest per iteration
- Component observability: harness workspace editable, benchmark substrate read-only
- Experience observability: layered trajectory distillation
- Decision observability: self-declared predictions verified next round
- BOOTSTRAP_SKILLS: one-shot explore agent seeds initial skill set

**Sources:** `Agentic_Harness_Engineering.md`, `AutoHarness paper`

---

### 13 � `experiment-loop`

Activate when setting up a reward-driven autonomous experimentation loop. Distinct from `harness-evolution` � that improves the scaffold around a fixed model; this mutates a candidate implementation against a fixed evaluator.

**Key features**
- `program.md` as org-code: researcher policy externalized as a markdown task contract, transplantable into any agent runtime (Copilot, OpenCode, Aider, Pi, etc.)
- Narrow mutation boundary: one editable file/surface, benchmark substrate explicitly read-only
- Fixed-budget experiment loop: TIME_BUDGET, single scalar reward, timeout/crash semantics
- Keep/discard state machine: advance on improvement, revert on failure or tie � no state drift
- Lightweight experiment ledger: commit + score + memory + status + description (TSV ? sqlite/MLflow upgrade path)
- Reproducible benchmark substrate: pinned dataset, fixed tokenizer, cached artifacts built once
- Bring-your-own-agent: substrate contract driven by external coding agent, not a built-in runtime
- Stronger factory upgrades: parallel worker lanes, structured run artifacts, separate proposer/runner/critic roles

**Sources:** `autoresearch.md`

---

### 14 � `fat-skills`

Activate when designing knowledge that needs to trigger autonomous actions rather than just respond to queries.

**Key features**
- Thin harness: routing only, ~200 lines, RESOLVER.md as dispatcher
- Resolver: skill descriptions function as the routing table � fewer, fatter skills over many narrow ones
- Fat skill anatomy: triggers / tools / writes_to / mutating flag / multi-tier protocol / inline citation hierarchy / philosophy line
- Always-on layer: signal-detector fires in parallel with every message, captures ideas + entity mentions
- Cron: 5-min staggered slots, quiet hours (11PM�8AM), idempotency, files to `reports/` for audit
- Deterministic split: LLM synthesis (latent work) vs SQL/API/calculations (deterministic) � mixing causes hallucination
- Postgres + pgvector backend for latent + deterministic data separation

**Sources:** `RAG_LLM_Wiki_or_GBrain.md`, `gstack.md`

---

### 15 � `build-observability`

Activate when instrumenting an agentic system to make build progress visible and auditable.

**Key features**
- Normalized runs/events/commands schema: stage, status, owner, command lifecycle states
- Dashboard surface: current stage, timeline, command activity, changed files, artifact list, sub-agent hierarchy, deploy outcome
- Runtime collector pattern: reads agent session files ? projects into observability schema
- Observability trace enrichment ? decision trace capture feeding back into `context-graph`
- Postgres when `DATABASE_URL` set, sqlite fallback

**Sources:** `sundai-hacker-feature-topology.md`, `Meta_Knowledge_Graphs.md`

---

### 16 � `session-continuity`

Activate at the start of any session-bounded agent workflow. Prevents session amnesia from degrading work quality across resets.

**Key features**
- Six-file memory bank: projectbrief ? productContext ? activeContext ? systemPatterns ? techContext ? progress
- Read-all-before-acting discipline: non-optional, every session
- Timestamped append-only updates: never overwrite history
- Todo lifecycle: `list_todos` at session start; add/complete/update/remove during task; update activeContext + progress after significant completions
- Trigger conditions for updating each file vs skipping
- gstack complement: `context-save`/`context-restore` (git state + decisions + remaining work), `learn` (cross-session knowledge review/search/prune)

**Sources:** `sspv2.md`, `gstack.md`

---

## Workflow & Process

### 17 � `spec-driven-dev`

Activate for any significant change that warrants specification before implementation. Directly portable � no Sundai environment required.

**Key features**
- `openspec-explore`: clarify/think/inspect stance, explicitly forbids implementation
- `openspec-propose`: one-shot bootstrapper, walks artifact dependencies, generates proposal.md + design.md + tasks.md
- `openspec-workflow`: umbrella model � spec authoring ? review loop ? Fabro setup ? validate ? implement ? verify ? ship
- `openspec-apply-change`: execute tasks in sequence from active change, update checkboxes
- `openspec-archive-change`: completion check + optional delta-spec sync + dated archive
- `fabro-create-workflow`: natural language ? DOT graphs + TOML run configs, model assignment via stylesheet, preflight validation
- `review-loop` protocol: when to review, how to process objections, how to log rounds

**Sources:** `sundai-hacker-feature-topology.md`

---

### 18 � `dev-pipeline`

Activate for full development lifecycle work. Reference for the gstack skill family organized by phase.

**Key features (by phase)**
- Ideation: `office-hours` � YC forcing questions, startup and builder modes, demand validation
- Planning: `plan-ceo/eng/design/devex-review` (each with 3�4 modes), `autoplan` (orchestrates all four, surfaces only taste decisions)
- Execution safety: `careful` / `freeze` / `unfreeze` / `guard` (session-scoped behavior modifiers)
- Browser automation: `browse` (headless, ~100ms), `open-gstack-browser` (headed + anti-bot), `setup-browser-cookies`, `pair-agent` (share session with remote agent)
- Data extraction: `scrape` (read-only JSON), `skillify` (codify scrape ? permanent ~200ms browser-skill)
- Benchmarking: `benchmark` (Core Web Vitals + bundle sizes), `benchmark-models` (cross-model latency/tokens/cost/quality)
- Review gates: `review` (specialist sub-agents per domain), `codex` (adversarial Codex CLI), `cso` (secrets + OWASP + STRIDE), `qa` / `qa-only`, `design-review`, `devex-review`
- Ship pipeline: `ship` ? `land-and-deploy` ? `canary` ? `document-release`; `setup-deploy` (platform detection)
- Design track: `design-consultation` (full design system ? DESIGN.md), `design-shotgun` (multi-variant), `design-html` (approved mockup ? Pretext HTML/CSS)
- Session persistence: `learn`, `context-save` / `context-restore`, `retro`, `plan-tune`, `setup-gbrain`

**Sources:** `gstack.md`

---

### 19 � `optimizer-driven-evaluation`

Activate when a harness needs iterative evaluation that goes beyond a one-shot judge call. This concept is intended to strengthen the evaluation lane inside `agentic-harness`, not to replace final artifact-backed verification.

**Key features**
- DSPy optimizer contract: program + metric + small trainset -> compiled candidate program
- Optimizer families for LM programs: few-shot bootstrapping, instruction search, reflective prompt evolution, finetune, ensembling, prompt<->weight meta-optimization
- Reward-threshold refinement loops: `BestOfN` / `Refine`, multiple rollout IDs, `fail_count` error budget, feedback reused as hints
- Trace-aware optimization: keep only high-scoring traces, use code/data/trajectory context to propose better instructions
- TextGrad natural-language losses: evaluator instructions become loss functions, critique becomes optimization signal
- Textual-gradient updates over mutable text/code/prompt variables; separate forward and backward engines
- Noisy-objective hygiene: multi-seed averaging, trajectory + loss-history retention, majority-vote finalization when the objective encourages exploration
- Safety + transparency: sandbox code-eval workloads and expose limitations/variance alongside results

**Sources:** `dspy.md`, `textgrad.md`

---

## Output & Voice

### 20 � `voice-and-output`

Activate when writing, editing, or expanding text that must preserve a particular voice or meet specific format constraints.

**Key features**
- Bold-user-phrasing: bold original text, unbolded text is addition � creates visible audit trail of contributions
- Semantic redundancy avoidance: unbolded additions must be semantically distinct from bolded, not high-cosine restatements
- Transition quality: implicit logical connections over formulaic "because/therefore" connectors, match user cadence
- AI writing clich�s banned: "Here's the thing", staccato drama fragments, "X isn't about Y it's about Z", hashtag lists, em-dash theatrics, "uncomfortable truth", landing-page Problem/Solution format, false-humility closers
- Prose over bullets unless structure is load-bearing
- Coherence-frontloading in agentic contexts: goal/todo/intent at top of response
- Three valid response types: ask / declare insufficient info / give prevailing answer � no filler

**Sources:** `ssp.md`, `sspv2.md`
