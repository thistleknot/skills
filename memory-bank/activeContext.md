# Active Context

## Current Focus
Setting up GitHub Copilot CLI with Cline-style memory bank via fastmcp.
Windows environment (py310 conda env).

## Recent Changes
- Installed memory bank scaffold via setup_copilot_memory.ps1
- MCP server registered at ~/.copilot/mcp-config.json
- COPILOT_CUSTOM_INSTRUCTIONS_DIRS pointing to ~/memory-bank/

## Next Steps
- Verify /mcp show lists memory-bank in Copilot CLI
- Populate memory bank per active project before first real session
- Resume quant pipeline work or RAG pipeline work as needed

## Active Decisions
- Memory bank write trigger: "update memory bank"
- Reads are static injection via AGENTS.md, not routed through MCP
- MCP server handles writes only

## Patterns and Preferences
- One degree less technical verbosity than default
- Plain speech, direct answers, no preamble
- Complete files always â€” never snippets
- Bold original phrasing when expanding ideas

## Learnings
- Copilot CLI reads AGENTS.md via COPILOT_CUSTOM_INSTRUCTIONS_DIRS
- MCP config lives at ~/.copilot/mcp-config.json
- fastmcp already installed in py310 env


### 2026-04-18 16:56
Completed the dungeon harness renderer pivot in C:\Users\user\notebooks\dungeon. The dungeon playthrough now renders as a single continuous ASCII map derived from room templates, graph anchors, and corridor projection helpers in dungeon.py. The old minimap plus active-room split was removed from dungeon_harness.py without changing the combat integration seam.


### 2026-04-18 16:59
Completed the actual dungeon display integration in C:\Users\user\notebooks\dungeon. The continuous ASCII dungeon map now renders on the live Game display path via Game.get_display_text(...) for dungeon-loaded games, not just in the harness. Integration stayed presentation-only and did not alter combat resolution or the Game.load_dungeon/open_door seam.


### 2026-04-18 17:39
Implemented a real player-facing dungeon game in C:\Users\user\notebooks\dungeon. Added play_dungeon.py with a manual terminal command loop on top of the existing skirmish+dungeon integration, preserved dungeon_harness.py as the deterministic regression runner, and fixed hero_party synchronization so defeated heroes do not reappear on room transitions.


### 2026-04-18 17:56
Reworked the dungeon playable entry point in C:\Users\user\notebooks\dungeon from typed commands into a key-driven tactical UI. `play_dungeon.py` now uses a visible cursor, WASD movement, Q/E hero cycling, J/K/L/; mode selection, contextual F/G confirms, and direct single-key input on Windows via msvcrt.


### 2026-04-18 18:31
Completed the dungeon visual-language overhaul in C:\Users\user\notebooks\dungeon. `play_dungeon.py` now renders a NetHack-inspired status/message HUD with recent events and intent previews, while `integration.py` applies semantic map styling, Unicode cursor support, and compact UI message formatting for the playable path. Target terminal is modern Windows with Unicode + ANSI enabled.


### 2026-04-18 19:01
Refined the dungeon controller in C:\Users\user\notebooks\dungeon around an OSR-style action taxonomy. `play_dungeon.py` now exposes six player-facing action modes — search, item, move, attack, skill, and spell — with a right-hand action pad (`U/I/O` over `J/K/L`) and `;` promoted to the door/open utility key.


### 2026-04-18 19:03
Started a new local-first, remote-ready civgame project in C:\Users\user\notebooks\civ. Added the initial FastAPI + SQLite + Streamlit scaffold, captured the user's explicit inspiration stack (Civ I, Civ II, Freeciv, Civ II mods including Master of Magic/Master of Orion/WW2, Civ III, and CTP2 mods including Ages of Man and Cradle of Civilization), and aligned the plan around a local-hosted authoritative server model that can grow into remote multiplayer later.


### 2026-04-18 19:07
Advanced civgame in C:\Users\user\notebooks\civ from scaffold to a real local-hosted prototype. The FastAPI server now supports unit movement, combat resolution, city founding, AI turn processing, and automatic handoff back to human turns. The Streamlit client can create players/sessions, move active units, found cities, end turns, and inspect the live map/session state. The influence stack is now explicitly anchored on Civ I, Civ II, Freeciv, Civ II mods (Master of Magic, Master of Orion, WW2), Civ III, and CTP2 plus Ages of Man and Cradle of Civilization.


### 2026-04-18 19:16
Refined the dungeon action surface again around a clearer action economy. The playable HUD now treats `open` as a first-class command in the action pad, `move` explicitly advertises half-speed vs rush, and `attack` exposes weapon-vs-kick as primary vs alternate execution on `F`/`G`.


### 2026-04-18 19:19
Expanded civgame in C:\Users\user\notebooks\civ into the first real empire-management layer. Cities now cache yields, grow from stored food, accumulate production, queue units/buildings, and feed science into per-player empire state. The FastAPI server exposes city production queue management, end-turn processing now performs economy resolution on round wrap, and the Streamlit client shows empire totals plus city management controls. This milestone intentionally prioritizes classic Civ-style empire backbone before tech tree, borders/resources, diplomacy, or scenario/mod expansion.


### 2026-04-18 19:29
Added item pickup to the dungeon controller in C:\Users\user\notebooks\dungeon. README now includes an action breakdown table, item mode picks up ground loot from the cursor, and downed enemies now drop collectible loot (including their weapons and remains) into per-room ground piles.


### 2026-04-18 19:41
Captured a key civgame design preference: the user wants tech pacing and overall campaign flow to be globally tunable in the style of classic Civ/CTP modding. Preference is for longer, more epic games where science advances more slowly over a broader calendar span, with explicit global levers controlling research pace, money/economy flow, time/calendar progression, and the feel of maintaining armies across long eras.


### 2026-04-18 19:42
Implemented the first action-expansion slice for the dungeon game in C:\Users\user\notebooks\dungeon. `search` now supports listening at nearby doors with hints from unrevealed room contents, and `move` now supports wait/defend when the cursor stays on the active hero. Defend is wired into combat as a real temporary defense bonus.


### 2026-04-18 19:46
Swapped the dungeon game's player party to a fixed HeroQuest-style quartet in C:\Users\user\notebooks\dungeon. The playable controller and regression harness now both seed `Warrior`, `Wizard`, `Elf`, and `Dwarf` through a dedicated skirmish party factory, preserving the existing squad-control model while replacing the older Archmage/Battle Lord sample heroes.


### 2026-04-18 19:47
Completed the civgame research-and-pacing milestone in C:\Users\user\notebooks\civ. Added a first-era tech tree (Pottery, Masonry, Bronze Working, Writing, Iron Working), active research selection, tech prerequisites, tech-gated unit/building unlocks, session-wide pacing controls, and calendar year progression. The Streamlit client now exposes both research choice and host-controlled campaign levers for slower or faster epic pacing.


### 2026-04-18 20:02
Paused the dungeon work mid-investigation on a player-reported combat stall. In the playable controller, a remaining enemy unit can appear as `Shadow Assassins HP 1/1 wounds=0 shaken=False` in `guard_post`, which leaves the room uncleared and blocks door progression. A screenshot was provided at `C:\Users\user\AppData\Local\Temp\copilot-image-ea2fa1.png`. The AI-vs-AI harness still reaches the boss room, so the bug appears specific to the player-controlled path or to how surviving multi-model enemies are presented/advanced there.


### 2026-04-18 20:20
Resolved the dungeon guard_post room-stall investigation in C:\Users\user\notebooks\dungeon. The reported `Shadow Assassins HP 1/1 wounds=0 shaken=False` state was a surviving last model from a 3-model squad, so play_dungeon.py now surfaces remaining model counts in inspect/enemy HUD text, and the playable controller now purges UNCONSCIOUS units after attacks, spells, and enemy-phase actions so spell knockouts no longer linger and block room-clear checks.


### 2026-04-18 20:40
Strengthened dungeon observability in C:\Users\user\notebooks\dungeon. `play_dungeon.py` now exposes `debug_snapshot()` with structured party/enemy/render state, the HUD shows effective per-hero movement budgets as `MV advance/rush/charge`, and tests now assert per-hero movement plus deterministic enemy-phase outcomes instead of relying on manual playthrough impressions. Also centralized movement-budget calculation in `skirmish.py` so controller/UI/test logic reuses the same effective move values as combat.


### 2026-04-18 20:41
Completed the civgame borders/resources milestone in C:\Users\user\notebooks\civ. Tiles now persist resource nodes and city ownership, cities claim radius-two territory, yields come from owned workable tiles, iron gates swordsman production alongside Iron Working, and the Streamlit client now shows both world/resource and territory views.


### 2026-04-18 20:50
Fixed GraphRAG LLM extraction resilience in C:\Users\user\notebooks\graphrag-rdf-lpg. graph_rag.py now retries transient proxy chat-completion failures, performs stronger local JSON string repair before escalating, and falls back to schema-valid empty extraction/review payloads with explicit warnings when JSON repair requests fail.


### 2026-04-18 20:59
Refined the civgame roadmap around a JSON-first modding contract. The preferred direction is a one-stop schema-validated mod pack with typed JSON files, with nations, technologies, governments, and wonders treated as first-class mod tables rather than markdown or hard-coded defaults. Scenario behavior should start as declarative JSON events before any deeper scripting layer.


### 2026-04-18 21:01
Completed repo-local Copilot/MCP bootstrap work in C:\Users\user\notebooks\storywriter using google agent memory. Added a root README.md for onboarding, created targeted Copilot instruction files under .github\instructions\ for runtime and tests, and updated .github\copilot-instructions.md to point at the new bootstrap surfaces. Scope stayed on repo-local discoverability and did not change the active storywriter_v3 / two_pass_story_engine runtime.


### 2026-04-18 21:04
Completed the repo-local dungeon playthrough workflow. Added `.copilot\skills\dungeon-playthrough\SKILL.md` plus `playthrough_capture.py` so gameplay changes can be validated through deterministic frame artifacts (`.png`, `.txt`, `trace.json`). Coupled fixes landed in `play_dungeon.py` (reject move-to-enemy tiles), `skirmish.py` (unique visible model positions), `dungeon.py` (share quest key across living heroes), and `dungeon_harness.py` (treat entering `boss_sanctum` as reaching the boss even if the party dies there).


### 2026-04-18 21:09
Completed the JSON-first mod foundation for the civ prototype. Base content now loads from schema-validated files under `src\\civgame\\content\\packs\\default\\`, with generated schemas under `src\\civgame\\content\\jsonschema\\`. `default_rules.py` is now a compatibility projection over the loaded content pack, which keeps the existing engine/API/UI stable while moving authoritative content out of code. The next recommended implementation slice is engine-level event hooks, followed by treasury/logistics.


### 2026-04-18 21:20
Fixed the dungeon movement/contact regression after the repo-local playthrough skill work. `play_dungeon.py` now rejects movement paths that pass through enemy model positions, and charge selection uses an open adjacent contact tile instead of stacking on the target. `integration.py` now clamps dungeon movement targets to open walkable tiles rather than occupied ones. `skirmish.py` AI charge selection now uses real reachable contact positions so enemy turns advance again instead of stalling on failed pseudo-charges.


### 2026-04-18 21:20
Adjusted Graph-RAG extraction failure handling in `graph_rag.py`: `llm_extract_graph()` no longer falls back to an empty extraction payload when JSON repair still fails. `run_extraction()` now catches malformed extraction JSON / repair failures at the per-quote level, logs a skip message, and leaves the quote unprocessed so it can be retried on the next run.


### 2026-04-18 21:33
Completed live validation and first commit setup for C:\Users\user\notebooks\storywriter using google agent memory. Ran py_compile and unittest on the active top-level pipeline, generated a live manuscript artifact at copilot_bootstrap_story.md via storywriter_v3.py using the Copilot proxy, initialized a new local git repository, and committed the repo-local Copilot bootstrap files plus the generated story artifact. Larger live runs exposed proxy timeout/circuit-breaker behavior, so a follow-up todo was added to harden that path.


### 2026-04-19 03:00
Refreshed C:\Users\user\notebooks\storywriter using google agent memory\.github\copilot-instructions.md after re-analyzing the repo. Kept the existing instruction file but corrected the command guidance to reflect the actual active v3 CLI versus the legacy run_demo.bat wrapper, preserved the architecture split between the integrated pipeline and retrieval-agent path, and retained the repo-specific persistence and prompt conventions.


### 2026-04-19 04:32
Analyzed the civctp2 repository at C:\Users\user\Documents\dev\civctp2 and created .github\copilot-instructions.md from repo sources rather than generic guidance. The new instructions capture the documented Windows/Linux/Docker build flows, the Sikuli smoke-test pattern from CI, the engine/data/script architecture split, and codebase-specific conventions like m_/s_/g_ naming, tab indentation, and generated parser files.


### 2026-04-19 07:14
Validated storywriter_v3 against the remote llama.cpp Qwen endpoint at http://192.168.3.17:8081/v1. Added local-model hardening in storywriter_v3.py: reasoning-tag stripping, more tolerant JSON parsing, optional streaming aggregation, and context-aware max_tokens halving on 'context size exceeded' errors. A live 1x1 run for seed 'A cartographer who discovers her maps predict the future' completed and wrote qwen_llama_story.md, but character/structure JSON still degraded and the final scene fell back after repeated connection errors. User-provided wrapper code clarified that the current server restart with '--chat-template chatml' is the wrong tradeoff for Qwen: ChatML ignores enable_thinking=false, so <think> blocks keep consuming context and output budget.


### 2026-04-19 07:30
Reran storywriter_v3 against the remote Qwen endpoint after the user restarted llama-server with the native Qwen jinja template and a larger 16384-token context window. Overrode LLM_SHARED_CONTEXT_BUDGET=16384 during execution. The rerun produced qwen_llama_story_native.md with a better premise/title ('The Ink of Tomorrow's Edge') and stable character names (Elara Vance, Silas Thorne), confirming the native template is materially better than ChatML for this model.


### 2026-04-19 07:45
Completed a Graph-RAG extraction resilience fix in C:\Users\user\notebooks\graphrag-rdf-lpg. `graph_rag.py` now normalizes and validates extractor payload schema before lexical review/triple conversion, so JSON-valid but schema-invalid responses are skipped per quote instead of crashing the run. Also downgraded lexical-review request failures to empty lexical expansions so transient proxy errors do not abort otherwise valid extraction work. A live proxy-backed extract run advanced the checkpoint from 1174 pending / 1334 cached to 1155 pending / 1353 cached before the session-ended validation stop.


### 2026-04-19 08:10
Paused storywriter/Qwen tuning while the user's master node reviews llama-server settings. Current status before pause: storywriter_v3.py now compacts the narrative prompt, applies scene input/output budgeting knobs, and the two-pass engine compresses continuity-bible sections to fit a 16k-per-slot style budget better. A full budgeted pipeline run improved premise/character/plot planning quality but scene generation still hit context-size 500s and fell back. As a workaround for immediate prose quality, a direct Qwen derivation pass from the improved 3-scene scaffold was written to qwen_derived_story.md.


### 2026-04-19 09:32
graphrag-rdf-lpg: structured tuner now log-aware. LAYER_SEARCH_SPACES specs are 4-tuples (kind, lo, hi, scale); scale ∈ {"linear","log"}. _to_search/_from_search/_step do the round-trip; sigma is computed in transformed space. All current factors flagged "linear" (bounded narrow-range, zero-floored). README updated. py_compile clean, log roundtrip verified.


### 2026-04-19 09:34
Implemented timeout-and-retry hardening in storywriter_v3.py for the remote Qwen llama.cpp endpoint. The LLM client now tracks successful call latencies by bucket (text/json/scene), computes an outlier threshold from median + MAD*2, uses that as a per-request timeout via client.with_options(timeout=...), and retries transport/server failures with fresh seeds on each attempt. Context-size errors still halve max_tokens between attempts. Smoke test against the live Qwen endpoint returned 'ready' successfully after the change.


### 2026-04-19 09:47
Adjusted the Qwen timeout heuristic in storywriter_v3.py based on the user's guidance. Cold-start requests now use a hard 300-second timeout ceiling. After at least 5 successful calls in a latency bucket, the client computes a moving timeout threshold from log-transformed elapsed times using median + MAD*2, then maps back to nominal seconds with exp(...) and clamps to the hard cap. Successful calls still populate bounded per-bucket deques, so the threshold remains a moving central-tendency estimate.


### 2026-04-19 10:54
graphrag-rdf-lpg: user clarified node ontology. Nodes should represent canonical lemma/synset + POS options, not raw semantic span text. POS choices are treated as mutually exclusive candidates for a node identity; original surface text remains evidence/label metadata from the semantic span and/or extracted LPG entity payload. Heuristic direction: remove stopwords, select lemma candidates, rank senses by POS prior plus corpus/head frequency and context, choose one canonical node, and avoid paraphrastic phrase nodes when confidence is low.


### 2026-04-19 11:00
graphrag-rdf-lpg: user refined node normalization heuristic. Canonical node selection should score candidate lemma/synset+POS options using a mix of BM25 score, POS tag conditioned on semantic triplet role (subject/predicate/object), high-frequency term priors, and stopword removal. Goal remains one deterministic node identity per surface span, with surface text preserved only as evidence/alias metadata.


### 2026-04-19 11:01
graphrag-rdf-lpg: graph-semantics clarification. POS and semantic triplet role are correlated but not identical. Negation handling should stay positive-only at graph edge level: if a proposition is negated in the sentence, do not emit the positive edge. Missing edge can only be read as negation under a local sentence/quote closed-world assumption, never as a global KG truth. Preserve negation in provenance/evidence if needed, not as a positive relation.


### 2026-04-19 11:08
Completed the next civctp2 HTML MVP slice in C:\Users\user\Documents\dev\civctp2. The web app now discovers real scenarios from Scenarios\*\scenXXXX, resolves base/default + english + scenario overlay layers, parses Const.txt / Advance.txt / civilisation.txt into typed summaries, and persists per-scenario sessions in SQLite. Also upgraded the UI-intent seam beyond button-only modals by adding a real text-prompt callback flow (rename showcase city) in the HTML client.


### 2026-04-19 11:12
Documented and launched the civctp2 HTML MVP in C:\Users\user\Documents\dev\civctp2. README.md now includes a dedicated 'Run the HTML MVP' section with the dependency install and uvicorn commands. Confirmed the app responds on http://127.0.0.1:8000/sessions/default after starting `python -m uvicorn web.app.main:app --host 127.0.0.1 --port 8000`.


### 2026-04-19 11:15
graphrag-rdf-lpg: user clarified retrieval/wiki memory direction. Saved retrieval/wiki artifacts should be organized by mutually exclusive downstream intent, not raw entity grouping. Existing wiki can be updated when new retrieval improves or prunes context, merged when multiple prior entries resolve to the same downstream intent, and forked into a new entry when the current answer reflects a different intent or lower-quality alternative. Entity overlap remains supporting evidence, not the primary organizing key.


### 2026-04-19 11:21
graphrag-rdf-lpg: user specified intent-memory ('a-mem') model. Persistent wiki state should follow: query -> LLM rephrase -> mutually exclusive intent classification -> indexed objective (updateable, recursively re-aligned against current and prior use cases) -> entity set (updateable/permeable if judge says score improves) -> score (positive-only monotonic updates). The free-form a-mem wiki text is a recursive summary of prior objectives met and current objective alignment; its purpose is to track the verbalized objective through successive use cases and move toward the underlying essence ('ousia').


### 2026-04-19 11:28
graphrag-rdf-lpg: user refined a-mem collapse rule. Objectives, like intents, should be treated as mutually exclusive sets. At query time, retrieved objectives/communities for an intent should be judge-checked for mutual exclusivity; if two are not mutually exclusive, they should merge. The highest-scoring surviving article absorbs the variance, updates its objective wording/entity set, and increases score only in the positive direction when fit improves.


### 2026-04-19 11:57
Patched storywriter_v3.py and two_pass_story_engine.py so two-pass scene generation uses stage-specific latency buckets (`scene_draft`, `scene_edit`, `scene_audit`, `scene_extract`) and preserves model-written prose when audit or extraction JSON fails. A live remote Qwen run (`qwen_timeout_story.md`, story ID `f91ebd3d`) completed end-to-end with a 1052-word scene and no deterministic fallback; only structured extraction failed, so downstream extracted elements/character updates were empty for that run.


### 2026-04-19 12:14
graphrag-rdf-lpg: full extraction completed on 2508/2508 quotes. Final checkpoint/export stats: 32353 triples, 16831 entities, 5095 predicates. kg.json and kg.yaml written. Ran full-snapshot cascade query for 'What is the meaning of life?' using the completed checkpoint; final answer remained 'Life has no meaning. Each of us has meaning and we bring it to life. It is a waste to be asking the question when you are the answer.' Query trace written to logs/query_runs/what_is_the_meaning_of_life.latest.{json,yaml}; graph written to graphs/what_is_the_meaning_of_life.html. SQL todo finish-extraction marked done; normalization and holdout remain pending.


### 2026-04-19 12:50
Implemented standalone community affinity mode selection for local clustering. `graph_rag.py` now exposes `community_affinity_mode` with `composite` (existing cosine + Jaccard + path behavior) and `jaccard` (standalone entity-overlap clustering) threaded through `CASCADE_DEFAULTS`, `retrieve_cascade(...)`, query/evaluate CLI, and tune frozen config. Validated with `py_compile` and a full-graph smoke run on `What is the meaning of life?` using Jaccard mode.


### 2026-04-19 14:16
Completed the two remaining session todos. Added explicit eval query banks (`tune`, `holdout`, `all`), persisted eval artifacts under `logs\\eval_runs\\`, and materialized a judge-driven normalization cleanup queue. Final artifact paths: `logs\\eval_runs\\all.latest.{json,yaml}` for cleanup diagnostics and `logs\\eval_runs\\holdout.latest.{json,yaml}` for holdout confirmation. Current holdout metrics on the finished graph: scalar `0.80625`, precision `0.7708333333333333`, recall `0.8416666666666668`.


### 2026-04-19 14:17
Fixed two storywriter_v3 live-run issues. First, the remote llama.cpp `curl.exe` path now sends/receives bytes and decodes stdout/stderr as UTF-8 explicitly, plus `_repair_common_mojibake()` repairs common cp1252-misdecoded UTF-8 sequences before prose sanitization or JSON parsing. Second, `generate_backward_plan()` now filters forward-requirement entries to real `(act, scene_num)` keys from the actual plot so hallucinated extra scenes no longer inflate internal planning for constrained runs like `--acts 1 --scenes 1`. Also corrected stale mojibake in `qwen_timeout_story.md`.


### 2026-04-19 14:34
Initialized a local Git repository for `graphrag-rdf-lpg` because the workspace was not previously under Git. Committed the retrieval/eval/README work and then normalized `.gitignore` to Git-compatible forward-slash rules so generated artifacts stay untracked. Current commit tip: `17647d7` on `master`.


### 2026-04-19 14:36
Removed an illegal synopsis-style manuscript preface from the storywriter output path. `storywriter_v3.py` no longer prepends `premise['world_description']` in italics ahead of Act 1, so final manuscripts now begin directly with the story. Cleaned the existing `qwen_timeout_story.md` artifact to remove the injected meta lead-in as well.


### 2026-04-19 16:15
Created a reusable Copilot skill at `C:\\Users\\user\\.copilot\\skills\\hyper-parm_tuning\\SKILL.md`. The skill captures the project's transferable hyperparameter optimization protocol: freeze architecture first, define one scalar objective, separate `tune` and `holdout`, tune layerwise, choose `linear` vs `log` vs `categorical` spaces intentionally, support structured fixed-budget search vs TPE, average noisy evaluations, persist trials, and validate once on holdout after selecting final params.


### 2026-04-19 16:16
Corrected the civctp2 HTML delivery path in C:\Users\user\Documents\dev\civctp2 after the user rejected ASCII-style output. The web client now serves the original checked-in CTP2 terrain tiles from `ctp2_data\default\graphics\tiles\gtset\TILExxxx.tga` through an on-demand Pillow-backed PNG route, and the map is now clickable with tile selection plus a simple scout movement loop instead of being a read-only viewer.


### 2026-04-19 16:47
Replaced the remote Qwen transport in storywriter_v3.py from curl.exe subprocess calls to direct httpx POSTs so Windows timeout/retry logic stays inside Python. Added tests covering direct Qwen-path success with Unicode punctuation and timeout retry with a fresh seed. Relaunched the full 3x2 run against the remote endpoint; new story_id=5136cea9 progressed through premise, characters, structure, backward planning, architecture, treatments, and committed Scene 1 successfully. Scene 1 finished at 951 words with coherence 0.85, and Scene 2 has started. The prior hard-timeout wedge caused by surviving curl children appears resolved.


### 2026-04-19 17:01
Updated `C:\\Users\\user\\.copilot\\skills\\hyper-parm_tuning\\SKILL.md` to include the explicit a-mem/wiki-memory tuning contract. The skill now encodes persistent memory as `intent -> objective -> entity_bag -> score -> wiki_summary -> history`, judge-driven update/merge/create decisions, monotonic score updates, and RAGAS-style `context_precision` / `context_recall` as the scalar tuning signal for the wiki layer.


### 2026-04-19 17:13
Split the prior mixed skill into two separate Copilot skills. `C:\\Users\\user\\.copilot\\skills\\hyper-parm_tuning\\SKILL.md` is now purely about experimental design and hyperparameter optimization. Added `C:\\Users\\user\\.copilot\\skills\\agentic_kg_memory\\SKILL.md` as the dedicated architecture/behavior skill for wiki-memory derived from retrieved knowledge-graph evidence, including intent, objective, throughlines, entity bags, fit score, counts, judge decisions, and merge/update/create rules.


### 2026-04-19 17:52
Completed the dedicated Graph-RAG tuning pass in `C:\\Users\\user\\notebooks\\graphrag-rdf-lpg`. Structured tuning artifacts now exist under `logs\\tuning_runs\\` for `broad`, `gist`, and `community`, plus a merged `best_params.latest.{json,yaml}` artifact. The reusable skill `C:\\Users\\user\\.copilot\\skills\\hyper-parm_tuning\\SKILL.md` was also corrected to explicitly name the three judge sampler takes: `conservative`, `balanced`, and `creative`.


### 2026-04-19 18:38
Closed the remaining dungeon playthrough gap in C:\Users\user\notebooks\dungeon. `playthrough_capture.py` now supports a true frame-by-frame agentic mode (`--agentic`) that captures a frame, decides the next key from the observed frame plus `render_text()` / `debug_snapshot()`, executes it, and records the full decision trace. `play_dungeon.py` now exposes `preview_state`, `current_player`, `room_is_clear`, and `quest_complete` in `debug_snapshot()` so the observation bundle matches the visible controller state.


### 2026-04-19 19:04
Switched storywriter_v3 JSON requests from weak json_object prompting toward explicit json_schema support driven by Pydantic models. llm_json() now accepts schema_model/schema_name and validates parsed payloads through model_validate(). Wired two-pass scene audit/extraction through schema models, plus coherence and generic element extraction. Validation passed with py_compile and unit tests. The fresh full Qwen story run (story_id=79f68ba5) also completed: manuscript saved to qwen_full_story_fresh.md, 5771 words total, final coherence 0.77.


### 2026-04-19 19:34
Implemented ontology-boundary cleanup in graph_rag.py. Extraction-time entity normalization now collapses concept spans to noun/proper-noun ontology heads, preserves named entities as full spans, and drops clausal debris instead of promoting it to graph node ids. Extraction no longer emits instance_of/has_label triples. Retriever load now canonicalizes legacy document entity aliases from kg.json and strips ontology-debug predicates from the searchable graph. Rendered graph and persisted query traces now filter low-signal predicates from visible artifacts. Re-ran the query 'what is the meaning of life'; refreshed artifacts now show canonical entities like happiness and meaning, while phrase spans like 'What Happiness Consists Of' remain only in lexical-expansion provenance.


### 2026-04-19 19:51
Hardened the live story pipeline to persist per-scene debug artifacts during real runs: each generated scene now saves continuity_bible, scene/audit/edit/extraction prompts, audit JSON, and structured scene output JSON in an artifacts directory beside the manuscript. Also strengthened the two-pass continuity surface with a dedicated Continuity Priorities section and stricter canonical-mechanics / named-cost / callback-discipline instructions. Launched a detached 3x2 rerun for the fog-city seed to qwen_full_story_continuity.md under story_id=e6229435 so the run survives shell teardown.


### 2026-04-19 20:10
Superseded detached run story_id=e6229435 after finding the first artifact patch still wrote too late in the scene lifecycle. Moved artifact persistence earlier into run_two_pass_scene_pipeline so continuity_bible and scene_prompt are saved as soon as they are constructed, then restarted the detached 3x2 fog-city rerun as story_id=1fbf7c44.


### 2026-04-19 20:13
Finished the ontology boundary pass in graphrag-rdf-lpg. Added predicate collapse alongside entity collapse so both entities and predicates now normalize to single canonical lemmas in user-facing artifacts. Legacy underscored predicate ids from kg.json are normalized on load by replacing underscores/hyphens before head selection. Created reusable skill file at C:\Users\user\.copilot\skills\kg_ontology\SKILL.md documenting the contract: surface forms are provenance, entities collapse to canonical head lemmas, predicates collapse to canonical predicate lemmas, and hypernym/debug scaffolding stays hidden by default.
