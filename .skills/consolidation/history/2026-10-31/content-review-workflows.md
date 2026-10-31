# Content review: workflow and protocol candidates

Screen source: `merge_report-20261030.md`; reviewed 30 MERGE rows and 15 RENAME rows.
`MERGE` below means a supported consolidation opportunity, not an executed merge.
`XREF` includes a recommended explicit relationship where one is not already present.

## MERGE-screen rows 31–60

| Pair | Disposition | Evidence and preservation requirement |
|---|---|---|
| spec-driven-development / troubleshooting | XREF | The former owns the Requirements→Design→Tasks method (`spec-driven-development/SKILL.md:32-152`); the latter resolves divergence and blocks during that method (`troubleshooting/SKILL.md:27-204`). |
| speckit-checklist / speckit-tasks | XREF | Requirements-quality checklist (`speckit-checklist:14-354`) precedes dependency-ordered `tasks.md` generation (`speckit-tasks:141-214`). |
| ollama-harness-paradigm / pi-config | XREF | Cross-harness endpoint/template diagnosis (`ollama-harness-paradigm:13-68`) versus `.pi` files and provider registration (`pi-config:15-185`). |
| speckit-checklist / speckit-implement | XREF | Acceptance-quality review and task execution are distinct lifecycle steps (`speckit-checklist:14-354`; `speckit-implement:58-224`). |
| speckit-implement / speckit-taskstoissues | XREF | The latter is explicitly deprecated GitHub-issue export (`speckit-taskstoissues:14-88`); implement executes `tasks.md` (`speckit-implement:58-224`). |
| mergekit / model-size-reduction | XREF | Mergekit produces a merged checkpoint (`mergekit:17-37`); size reduction selects portability reductions, including unsupported architectures (`model-size-reduction:15-112`). |
| mlflow / optuna-nested-cv | XREF | MLflow owns run lineage and artifacts (`mlflow:13-34,169-224`); Optuna owns search and nested CV (`optuna-nested-cv:16-34,176-259`). |
| debugging / debugging-and-error-recovery | MIGRATE | Both own root-cause triage. Keep **debugging** as canonical because it is the broader protocol (`debugging:43-172`) and library hub. Migrate the latter's stop-line, reproduction/localization commands, error-class checklist, untrusted-output handling, and red flags (`debugging-and-error-recovery:21-154,172-281`); then retain a superseded redirect. |
| speckit-checklist / speckit-specify | XREF | `specify` authors feature requirements (`speckit-specify:238-344`); checklist validates requirement quality (`speckit-checklist:14-354`). |
| pi-config / pi-ollama-config | MERGE | Both configure Pi against local Ollama. Keep **pi-config** for its broader provider/defaults contract (`pi-config:15-185`); migrate installed-model discovery, compact validation, and failure-mode material from `pi-ollama-config:112-140`. |
| quality-assurance / troubleshooting | XREF | QA defines phase gates and testing strategy (`quality-assurance:34-173`); troubleshooting handles a failed or blocked execution (`troubleshooting:27-204`). |
| grpo-from-scratch / grpo-stability-improvements | MIGRATE | `grpo-stability-improvements` is a focused continuation of the base algorithm's Ch.7 material (`grpo-from-scratch:137-154`; `grpo-stability-improvements:21-138`). Keep **grpo-from-scratch**; preserve all joint diagnostic metrics, format reward, and DAPO/Dr.GRPO/DeepSeek modification details. |
| adapter-merging-strategies / mergekit | XREF | Adapter strategy chooses DARE→TIES for multi-reward LoRA (`adapter-merging-strategies:30-125`); mergekit provides general merge methods and CLI (`mergekit:55-320`). |
| speckit-analyze / speckit-taskstoissues | XREF | Analyze identifies artifact inconsistency (`speckit-analyze:58-210`); taskstoissues exports existing tasks and is deprecated (`speckit-taskstoissues:14-88`). |
| speckit-converge / speckit-taskstoissues | XREF | Converge assesses implementation versus intent and appends tasks (`speckit-converge:95-239`); taskstoissues exports them. |
| speckit-clarify / speckit-plan | XREF | Clarification resolves requirement ambiguity; planning creates research/design contracts (`speckit-clarify:243-289`; `speckit-plan:111-165`). |
| speckit-clarify / speckit-tasks | XREF | Clarify precedes a tasks artifact; their completion conditions differ (`speckit-clarify:243-289`; `speckit-tasks:141-214`). |
| auto-ingest / pdf-extraction | XREF | Auto-ingest is queue/MCP orchestration (`auto-ingest:36-132,413-428`); PDF extraction is the document-processing engine (`pdf-extraction:18-105`). |
| speckit-analyze / speckit-plan | XREF | Plan creates design; analyze detects cross-artifact inconsistency (`speckit-plan:111-165`; `speckit-analyze:68-206`). |
| megacave / ultracave | KEEP | They prescribe opposite response-density modes: classical complete prose versus terse fragments (`megacave:24-63`; `ultracave:24-61`). Similar format is intentional, not redundant. |
| speckit-plan / speckit-specify | XREF | Specify defines requirements and plan defines implementation design; separate command artifacts (`speckit-specify:283-344`; `speckit-plan:111-165`). |
| agentic-design-patterns / react-agent | XREF | Pattern selection and lane design (`agentic-design-patterns:14-142`) differs from operating a ReAct runtime (`react-agent:84-196`). |
| agentic-hyperparm-macd / signal-modulation | XREF | Both use MACD, but one tunes agent equilibrium (`agentic-hyperparm-macd:44-286`) and the other first demodulates a general non-stationary signal (`signal-modulation:50-224`). |
| continual-learning / model-size-reduction | XREF | Preventing forgetting and reducing checkpoint size are separate objectives; the former's DARE section is a method reference only (`continual-learning:59-190`; `model-size-reduction:15-112`). |
| speckit-clarify / speckit-taskstoissues | XREF | Requirements clarification and deprecated issue export are non-overlapping stages. |
| continual-learning / mergekit | XREF | Closed false-merge case: continual learning's DARE example (`continual-learning:153-176`) does not make it a mergekit replacement; mergekit owns model merging (`mergekit:17-37`). |
| speckit-implement / speckit-specify | XREF | Specify produces requirements; implement executes the resulting task plan. |
| speckit-clarify / speckit-converge | XREF | Clarify resolves before planning; converge reconciles delivered code with intent (`speckit-clarify:243-289`; `speckit-converge:138-239`). |
| agentic-design-patterns / agentic-harness | XREF | Architecture pattern chooser (`agentic-design-patterns:14-142`) versus runtime/harness execution contract (`agentic-harness:20-281`). |
| speckit-checklist / speckit-plan | XREF | Checklist evaluates requirement quality; planning performs research and design. |

## RENAME-screen rows 16–30

| Pair | Disposition | Evidence |
|---|---|---|
| local-llm-harness-wiring / ollama-structured | XREF | Harness endpoint/debug wiring (`local-llm-harness-wiring:13-59`) differs from structured output schemas/API paths (`ollama-structured:15-184`). |
| speckit-analyze / speckit-constitution | XREF | Analyze is artifact review; constitution sets project principles and scope guard (`speckit-analyze:68-206`; `speckit-constitution:22-150`). |
| speckit-checklist / speckit-constitution | XREF | Requirement quality checks versus governing project rules. |
| incremental-implementation / tdd-agent | XREF | Incremental slicing/rollback (`incremental-implementation:21-199`) differs from Red-Green-Refactor (`tdd-agent:31-173`). |
| incremental-implementation / task-breakdown | XREF | Delivery slice policy differs from task decomposition and dependency sequencing (`task-breakdown:28-135`). |
| speckit-constitution / speckit-specify | XREF | Constitution constrains a project; specify authors a feature artifact. |
| auto-research / react-agent | XREF | Research digest/harness-evolution evidence (`auto-research:16-147`) differs from ReAct operating procedure (`react-agent:84-196`). |
| openspec-workflow / troubleshooting | XREF | Change-management lifecycle and failure diagnosis are separate. |
| speckit-clarify / speckit-constitution | XREF | Feature ambiguity handling differs from stable constitutional policy. |
| meta-harness / recursive-harness-self-improvement | XREF | Meta-harness is execution/hand-off control (`meta-harness:30-175`); recursive harness self-improvement is a research digest plus gate (`recursive-harness-self-improvement:20-150`). |
| memory-bank / retro | XREF | Durable memory lifecycle (`memory-bank:27-161`) differs from retrospective review steps (`retro:10-38`). |
| spec-driven-development / spec-new | XREF | Broad three-phase practice (`spec-driven-development:32-152`) versus a command that opens a new gated spec lane (`spec-new:13-49`). |
| agent-identity / cognitive-taxonomy | XREF | Agent profile isolation (`agent-identity:29-117`) differs from memory-type taxonomy and routing (`cognitive-taxonomy:48-217`). |
| interview-me / to-questionnaire | XREF | Interactive intent interview (`interview-me:38-134`) differs from a rendered questionnaire template (`to-questionnaire:19-51`). |
| cua-desktop-agent / react-agent | XREF | Desktop vision/action stack (`cua-desktop-agent:14-110`) differs from a general ReAct operating loop. |

## Totals

- Reviewed: 45 pairs.
- MERGE: 1 (`pi-config` + `pi-ollama-config`).
- MIGRATE: 2 (`debugging-and-error-recovery` into `debugging`; `grpo-stability-improvements` into `grpo-from-scratch`).
- XREF: 41.
- KEEP: 1.
- RENAME: 0; the screen's RENAME quadrant did not establish a name/content mismatch in this slice.
