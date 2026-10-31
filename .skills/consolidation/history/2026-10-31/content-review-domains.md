# Content review — domains slice

Scope: MERGE rows 61–89 and RENAME rows 31–43 from `merge_report-20261030.md`.
Method: compare invocation contract, output, and declared integration; the two-axis
screen supplies candidates only. Line references are to the reviewed `SKILL.md`.

| Screen pair | Disposition | Evidence and retained boundary |
|---|---|---|
| spec-new / spec-next | XREF | `spec-new` opens the record and writes the first artifact (description; Steps L20); `spec-next` advances an already active, approved phase (description; Steps L15). Sequential commands, not duplicate contracts. |
| speckit-converge / speckit-specify | XREF | `speckit-specify` creates or updates a feature specification (description; Outline L58); `speckit-converge` audits implementation against artifacts and appends remaining tasks (description; Execution Steps L95). |
| agentic-harness / meta-harness | XREF | `agentic-harness` owns one issue’s execution mechanics (Core Contract L159); `meta-harness` explicitly owns upstream objective/scope/session handoff above it (Purpose L16; Separation contract L56). |
| speckit-specify / speckit-taskstoissues | KEEP | Specification authoring (specify Outline L58) differs from issue export; taskstoissues is explicitly deprecated but preserves a still-distinct migration path (Deprecation Notice L14). |
| spec-driven-development / spec-next | XREF | Broad requirements/design/tasks methodology (Three-Phase Workflow L32) vs local `.spec` state-machine advancement (spec-next description). |
| context-compaction / continuity-log | XREF | Compaction controls eviction and rehydration (Tiered Memory Model L30; hooks L93); continuity-log persists decision packets (Entry Format L86; Read Protocol L117). |
| speckit-clarify / speckit-implement | XREF | Clarify resolves specification gaps (description; Outline L58); implement executes `tasks.md` (description; Outline L58). |
| data-science-skills / parallel-rrf-graph-rag-hybrid-cascade-mmr-late-retriever | XREF | The former declares itself consumer routing into the latter (description; flow L65); the latter owns ingestion/retrieval service mechanics (Source of truth L91; Retrieval L145). |
| spec-approve / spec-next | XREF | Approval is human-only gate state (spec-approve L13, L47); next is model-side phase advancement and refuses unapproved state (spec-next description). |
| git-workflow / incremental-implementation | KEEP | Git branch/push approval policy (Git Workflow L12–70) and thin vertical code-slice delivery (Increment Cycle L21) are independent controls. |
| memory-architecture / memory-bank | XREF | Architecture defines system-level memory roles; memory-bank is the operational persistence protocol. Existing structural relationship is explicit in the library; preserve it rather than merge. |
| adapter-merging-strategies / continual-learning | KEEP | Adapter skill composes 4+ independently trained LoRAs with DARE/TIES (When to Use L10; Pipeline L30); continual-learning prevents sequential-update forgetting across six methods (Approaches L59). DARE overlap is a method, not an invocation collision. |
| code-review-and-quality / incremental-implementation | KEEP | Pre-merge five-axis review (Overview L8; axes L22) is distinct from implementation sequencing (Increment Cycle L21). |
| evaluator-optimizer / prompt-optimization | XREF | Evaluator-optimizer is a per-output generate/critique/regenerate loop (description; Architecture L30); prompt-optimization compiles/tunes prompts across data and metrics (Strategies L73; Interface L199). |
| code-review-and-quality / codebase-knowledge-graph | XREF | Review quality gates (Five-Axis Review L22) consume code changes; graph protocol maps dependencies/ripple/reuse before edits (Protocol L54). |
| spec-next / spec-status | XREF | Mutating phase advancement vs read-only state report (spec-status description; Reading it L21). |
| context-engineering / writing-for-agents | XREF | Context-engineering chooses project/session material (Context Hierarchy L20); writing-for-agents defines the document/pointer authoring rules (Context pointers L11; pruning L77). |
| codebase-knowledge-graph / git-workflow | KEEP | Repository dependency reasoning (Graph Model L39; ripple L69) and source-control promotion policy (Branch Hierarchy L12; push gates L39) have no duplicate deliverable. |
| rag-eval / ragas | KEEP | RAG Eval provides a fixed single-pass 10-metric retrieval fitness score (description; Metrics L48); ragas maps metric applicability for an answer-vs-reference schema judge (Purpose L26; applicability L38). |
| active-inference / continual-learning | KEEP | Active Inference is POMDP belief/action selection (Core Concepts L38; pymdp L84); continual learning retains past capabilities during updates (Six Approaches L59). |
| agentic-orchestration / context-engineering | XREF | Orchestration assigns roles/work; context engineering selects and structures information. Shared agent language does not duplicate a procedure. |
| ewma-eta-watchdog / timeout-guard | XREF | Adaptive batch ETA/prediction-interval watchdog (three parts L38) differs from hard per-attempt local-LLM timeout and retry policy (Purpose L9; Policy L16). |
| program-synthesis / synthetic-data | KEEP | Program synthesis proves correctness using Verus/Dafny/Lean (Targets L71); synthetic-data produces fine-tuning data with generation and quality gates (Paradigms L38; Code synthesis L102). |
| agentic-harness / recursive-harness-self-improvement | XREF | Harness is the operational execution protocol (Core Contract L159); RSI evolves harness components from failure traces with held-out gates (description; findings L32). |
| speckit-checklist / speckit-taskstoissues | KEEP | Per-feature requirements checklist generation (description; Execution L88) is not GitHub issue conversion, even though both consume feature artifacts. |
| llm-pretraining-fundamentals / reasoning-distillation | KEEP | General causal-LM pretraining loop/data (Description L10; Training Loop L39) and teacher-trace student distillation/data filtering (Description L10; Dataset L38) are separate training objectives. |
| spec-next / troubleshooting | XREF | `spec-next` advances normal state; troubleshooting handles spec/reality divergence and dependency blocks (Issues L27, L78). |
| codebase-knowledge-graph / incremental-implementation | XREF | Mapping/reuse/ripple analysis occurs before edits (Protocol L54); incremental implementation governs how edits are delivered (Increment Cycle L21). |
| ollama-structured / pi-ollama-config | XREF | Schema-constrained response generation (Two API Paths L24) differs from Pi’s local-provider model registry configuration (Where It Lives L15; Configure L112). |
| hyper-parm_tuning / mergekit | KEEP | `hyper-parm_tuning` is already superseded by `optuna-nested-cv` (frontmatter L3–5). Its historical experimental-design contract does not rename or merge into checkpoint/model merging (mergekit Method Reference L131). |
| speckit-constitution / speckit-implement | XREF | Constitution establishes project principles (description; Scope Guard L22); implement executes task plans (description). |
| agent-identity / writing-for-agents | XREF | Identity isolates roles/tone/profiles (description; steps L29–106); writing-for-agents designs reliable instruction documents and pointers (L11–77). |
| speckit-constitution / speckit-taskstoissues | KEEP | Project-governance constitution and deprecated issue-export command differ in input, output, and lifecycle point. |
| spec-init / speckit-specify | KEEP | `spec-init` provisions the local `.spec` gate once (description; Steps L14); speckit-specify authors a feature spec inside a separate `.specify` framework (description). |
| evidence-first-exploration / incremental-implementation | XREF | Evidence-first designs falsifiable probes for opaque/surprising systems (Core discipline L20; probes L92); incremental implementation delivers known changes in slices (L21). |
| linear-programming-hyperparm-tuning / memory-architecture | KEEP | LP/MIP formulation of measurable discrete configuration tuning (description; Formulation L73) has no memory-system responsibility. |
| react-fastapi-sqlite / request-intent-resolution | KEEP | Full-stack application scaffold stages (Architecture L17; Database L113) differ from support-thread intent/retrieval pipeline (Architecture L18; Retrieval L423). |
| ai-prompting / spec-driven-development | XREF | Prompting teaches agent communication strategies (Core Strategies L26); SDD governs requirements/design/tasks artifacts (Three-Phase L32). |
| gstack / quality-assurance | XREF | Gstack is an executable browser QA tool (description; Setup L128); QA is phase-specific validation policy and gates (Phase validation L34; Gates L96). |
| caveman / session-recap | KEEP | Caveman persists a terse response voice (Persistence L15); session-recap recursively summarizes prior transcript data (Procedure L27). |
| concept-segmentation / universal-filter | KEEP | Concept segmentation is a SQLite read-and-extend document-boundary workflow (description; Loop L223); universal-filter sets a skew-aware numeric cutoff (description). |
| siamese_from_correlation_matrix / spec-driven-development | KEEP | Correlation-derived metric-learning signals/losses (Pattern L17; Signals L50) and requirements/design/tasks methodology (SDD L32) are unrelated. |

## Result

- Reviewed: 42 pairs.
- MERGE: 0; MIGRATE: 0; XREF: 22; KEEP: 20; RENAME: 0.
- No candidate in this slice has the same invocation contract and deliverable. The
  screen’s high scores mostly join sequential workflow stages, parent/subskill
  relationships, or shared generic agent vocabulary.
