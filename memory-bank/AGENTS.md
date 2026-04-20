# Memory Bank

This file is auto-injected into every Copilot CLI session.

Treat all sections below as authoritative project context.


---

﻿# Project Brief

## Purpose
This memory bank covers Jos Hua's personal technical work outside of Boeing:
quantitative finance pipeline, homelab AI infrastructure, and associated tooling.
Not Boeing work. Not subject to Boeing IP constraints.

## Core Requirements
- Quant pipeline must be reproducible and checkpoint-based (sqlite load-if-exists)
- All price data via stooq through pandas_datareader. Never yfinance.
- Fundamentals via FMP free tier or SEC EDGAR XBRL API
- Local AI inference preferred over cloud where latency allows
- Code must be complete â€” no snippets, no placeholders

## Out of Scope
- Boeing proprietary systems
- Yahoo Finance or yfinance in any form
- Cloud-first solutions where local inference is viable


---

﻿# Product Context

## Why This Exists
Personal quant pipeline running in a Roth IRA via IBKR. Separate from day job.
Goal is systematic, rules-based portfolio management with minimal manual intervention.
Homelab AI stack supports both the quant work and general LLM experimentation.

## How It Should Work
- Pipeline runs on 13-week rolling tranches
- XGBoost business cycle classifier on FRED indicators drives regime detection
- Markowitz optimization with MAD-based Sharpe, fed by median-mean GAM normalized expected returns
- Parkinson volatility for bracket orders
- IBKR execution layer is the terminal output
- Two-stage optimizer consistently favors GLDM/XES/COPX cluster
- Current thesis: dollar debasement + geopolitical risk (Operation Epic Fury, US-Iran)
- Portfolio ratio: ~1.3:1 GLDM:XES reflecting near-term XES catalyst asymmetry

## User Experience Goals
- Run pipeline, get orders, approve, done
- Minimal friction between signal and execution
- Audit trail via sqlite so any run is reproducible


---

﻿# Tech Context

## Technologies Used
- Python 3.10 (conda env py310) on Windows
- FastAPI, Pydantic, Streamlit, Gradio, FastMCP
- XGBoost, scikit-learn, scipy, cvxpy
- pandas, pandas_datareader (stooq), numpy
- sqlite3 for checkpointing
- pgvector, BM25, GIST embeddings, ColBERT, cross-encoder reranking
- IBKR API (ib_insync or native) for execution
- Proxmox (pve-m7330), Docker, Rocky Linux 9
- Ollama, llama.cpp, Open-WebUI, ComfyUI
- Quadro P5200 GPU in homelab

## Development Setup
- Windows primary workstation, py310 conda env
- Homelab on Proxmox at 192.168.3.x subnet
- Ollama inference at 192.168.3.17
- Open-WebUI at 192.168.3.18
- llama.cpp OpenAI-compatible endpoint on port 8080
- GitHub Copilot CLI for agentic coding sessions

## Technical Constraints
- Price data: stooq only via pandas_datareader. Yahoo Finance/yfinance banned.
- Fundamentals: FMP free tier or SEC EDGAR XBRL only
- IBKR execution in Roth IRA â€” real money, no runaway automation
- Windows paths use backslash; Python code must use pathlib or raw strings

## Dependencies
- fastmcp (installed in py310)
- pandas_datareader for stooq
- cvxpy for portfolio optimization
- ib_insync or IBKR native API
- Optuna TPE for hyperparameter search

## Tool Usage Patterns
- sqlite load-if-exists before any heavy computation
- Assertions at every pipeline stage boundary
- Complete files delivered, never partial
- RAGAS macro-mean as RAG eval scalar


---

﻿# System Patterns

## Architecture
Two independent stacks:

1. Quant pipeline (local Windows + IBKR)
   - FRED data -> XGBoost classifier -> regime signal
   - stooq prices -> Parkinson vol -> expected returns
   - GAM normalization (Yeo-Johnson + dual-path) -> Markowitz optimizer
   - sqlite checkpointing throughout
   - IBKR API for bracket order execution in Roth IRA

2. Homelab AI (Proxmox host pve-m7330)
   - Open-WebUI at 192.168.3.18 with pgvector backend
   - Ollama at 192.168.3.17
   - llama.cpp serving Qwen on port 8080 as OpenAI-compatible endpoint
   - SearXNG for web search
   - ComfyUI in Docker with Quadro P5200

## Key Technical Decisions
- sqlite over postgres for local pipeline checkpointing (simpler, portable)
- stooq via pandas_datareader as the canonical price source
- fastmcp for all MCP servers
- pgvector + BM25 hybrid retrieval for RAG
- RAGAS macro-F1 as single scalar RAG eval metric

## Design Patterns in Use
- Load-if-exists checkpoint pattern on all heavy computations
- Two-stage optimizer (regime filter -> portfolio optimizer)
- 13-week rolling tranches for position management
- Assertions at pipeline checkpoints; transformations reversible
- Try/except only on non-critical paths; critical paths fail fast

## Component Relationships
- FRED indicators feed the classifier
- Classifier output gates the optimizer
- Optimizer output feeds IBKR bracket order generation
- All intermediate state persisted to sqlite

## Critical Implementation Paths
- Regime classifier must run before optimizer
- GAM normalization must precede expected return input to optimizer
- Parkinson vol must be computed before bracket sizing


### 2026-04-18 21:09
Established a new content architecture pattern for the civ project: authoritative game content lives in schema-validated JSON pack files, while runtime compatibility layers project that content into legacy rule shapes for the simulation engine. This keeps downstream systems stable during migration and gives modders a one-stop folder layout similar to classic civ/CTP database-driven modding workflows.


---

﻿# Active Context

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


---

﻿# Progress

## What Works
- Quant pipeline: XGBoost classifier, Markowitz optimizer, GAM normalization,
  Parkinson vol, IBKR bracket order generation, 13-week rolling tranches
- Homelab: Open-WebUI, Ollama, llama.cpp, pgvector, SearXNG, ComfyUI
- RAG pipeline: hybrid BM25 + GIST retrieval, ColBERT, cross-encoder reranking,
  GraphRAG with GATv2, RAGAS eval
- SEC EDGAR fundamentals: Dow 30 JSONB pipeline in PostgreSQL (secdb, port 5433)
- Copilot CLI memory bank: scaffold installed, MCP server registered

## What Is Left to Build
- Verify Copilot CLI /mcp show sees memory-bank server
- Portfolio benchmarking against SPY, risk-free rate, inflation
- OpenClaw multi-agent monitoring layer over quant pipeline (planned, not started)

## Current Status
Active. Quant pipeline running. Homelab stable.
Memory bank just installed for Copilot CLI workflow.

## Known Issues
- Copilot CLI MCP write-back not yet verified end-to-end
- AGENTS.md is a static snapshot; stale if memory bank files edited without rerunning script

## Evolution of Decisions
- Moved from 2:1 to 1.3:1 GLDM:XES ratio on near-term XES asymmetry
- Replaced Google PSE with SearXNG in homelab
- F106 RRF ensemble ER ranking gap diagnosed and patched


### 2026-04-18 16:56
Finished the dungeon renderer pivot. Updated dungeon.py with world-space projection helpers, switched dungeon_harness.py to a unified map renderer, refreshed tests in tests\test_dungeon.py, and kept the unittest suite green. Residual scope remains limited to the harness/playthrough renderer; skirmish.py interactive display was not changed.


### 2026-04-18 16:59
Finished the renderer pivot fully. dungeon.py projects rooms/corridors into world space, dungeon_harness.py uses the continuous map, integration.py now routes dungeon-loaded Game display output through the unified renderer, and tests cover both harness and live display behavior. Added a deferred note that a manual-input dungeon UI loop still does not exist.


### 2026-04-18 17:39
Finished the dungeon manual-play milestone in C:\Users\user\notebooks\dungeon. The project now has a playable terminal entry point (`play_dungeon.py`), regression coverage still passes, and tests cover both room traversal and manual hero activation. Deferred follow-up: explicit spell-casting commands in the playable UI remain low-priority polish work.


### 2026-04-18 17:56
Completed the keybinding ergonomics pass for the dungeon game in C:\Users\user\notebooks\dungeon. The playable path is now tuned for one-key tactical play rather than text commands, tests cover cursor movement plus spell mode, and the README documents the final keyboard layout. Remaining low-priority polish is a richer explicit spell menu beyond the current contextual casting behavior.


### 2026-04-18 18:31
Finished the dungeon readability pass. The playable entry point now distinguishes friendlies, hostiles, cursor focus, mode state, and action intent with Unicode + ANSI cues; README was updated to document the visual system; and the dungeon unittest suite remained green after the render/controller changes. Deferred follow-up: deeper NetHack-style examine text and inventory/action menus are captured as a low-priority todo.


### 2026-04-18 19:01
Completed the OSR command-surface remap for the dungeon game. Tests now cover the new action categories, README reflects the final keys, and the playable UI distinguishes non-combat utility actions (`search`, `item`, `skill`) from turn-consuming combat actions (`move`, `attack`, `spell`).


### 2026-04-18 19:03
Completed the first civgame scaffold milestone in C:\Users\user\notebooks\civ. The project now has a packaged Python layout, a FastAPI server for players/sessions/actions, SQLite persistence for players and session state, a Streamlit client for local play, deterministic map/session creation, city founding and end-turn actions, README run instructions, and a passing initial pytest suite. Next active work moved to the core simulation layer (movement, combat, deeper rules, and richer session actions).


### 2026-04-18 19:07
Completed the initial civgame playable-start milestone in C:\Users\user\notebooks\civ. Beyond the original FastAPI/SQLite/Streamlit scaffold, the project now includes deterministic land movement, server-authoritative combat, settler city founding, starting settler+warrior units, simple AI turn automation, a move-unit API endpoint, richer Streamlit controls, updated README guidance, and expanded pytest coverage for movement/combat/AI/session flow. Remaining work is now expansion work: deeper economy, production, diplomacy, research, borders/resources, scenario/mod systems, and richer CTP2/Civ-era homage mechanics.


### 2026-04-18 19:16
Completed the action-economy refinement for the dungeon controller. `play_dungeon.py` now presents OSR-style verbs with sub-actions (`move`: half-speed/rush, `attack`: weapon/kick), `README.md` documents the primary/alternate `F`/`G` model, and the dungeon test suite stayed green with added kick coverage.


### 2026-04-18 19:19
Completed the Empire Core expansion milestone for civgame in C:\Users\user\notebooks\civ. Added city food/production/science yields, stored food and production, population growth thresholds, build queues, starter building templates (granary/workshop/library), per-session empire science totals, city production queue API endpoints, Streamlit city production controls, and tests covering economy processing alongside the earlier movement/combat/session flow. Remaining expansion work has been split into explicit next tracks: tech tree, borders/resources, governments/diplomacy, and scenario/mod hooks.


### 2026-04-18 19:29
Completed the dungeon pickup pass. The action model is now documented in README with per-mode `F`/`G` behavior, item mode has a real pickup action, downed enemies leave loot behind for collection, and the dungeon unittest suite grew to 13 passing tests with pickup coverage.


### 2026-04-18 19:42
Completed the search/combat-utility pass for the dungeon controller. README now documents listen plus wait/defend behavior, `skirmish.py` grants a real defense bonus while defending, and the dungeon unittest suite increased to 15 passing tests with direct coverage for listen and defend.


### 2026-04-18 19:46
Completed the HeroQuest roster pass for the dungeon game. Added a dedicated `create_heroquest_party()` factory in `skirmish.py`, updated the playable controller and autoplay harness to use the four classic heroes, refreshed name-sensitive gameplay tests, and kept the suite green at 16 passing tests.


### 2026-04-18 19:47
Finished the civgame research-and-pacing expansion milestone. The project now supports actual technology advances, research completion, unlock-gated production, host-adjustable global pacing controls, and year progression on round wrap. Tests remain green after extending both engine and API coverage for research, unlocks, and session pacing updates.


### 2026-04-18 20:02
Saved a checkpoint for an unresolved dungeon bug before session restart. Added SQL todo `fix-room-stall` to investigate a playable-path issue where a surviving enemy can remain at `1/1` in `guard_post` and prevent room completion, even though the autoplay harness still succeeds. No fix was applied yet; next session should start by reproducing the stall directly in `play_dungeon.py` and tracing enemy activation/clear-room logic.


### 2026-04-18 20:20
Completed the dungeon guard_post follow-up in C:\Users\user\notebooks\dungeon. Added regression coverage for spell-based enemy cleanup and multi-model inspect text, and the dungeon gameplay test suite now passes with 18 tests.


### 2026-04-18 20:40
Dungeon state-debugging pass completed in C:\Users\user\notebooks\dungeon. Added deterministic coverage for controller snapshots after an enemy phase, verified that enemy movement and hero death are reflected in structured state and rendered HUD output, and surfaced per-hero movement budgets in the roster. Current dungeon test status is 20 passing.


### 2026-04-18 20:41
Finished the civgame borders/resources expansion in C:\Users\user\notebooks\civ. Added deterministic resource generation, cached territory ownership in map tiles, city/empire resource summaries, radius-two workable yields, UI/docs updates, and pytest coverage for territory plus iron-gated production. The next civ track is governments/diplomacy/treasury on top of the now-claimed map.


### 2026-04-18 20:50
Completed a GraphRAG extraction stability pass in C:\Users\user\notebooks\graphrag-rdf-lpg. Verified graph_rag.py compiles, parser-only repair cases pass, simulated repair-request HTTP 500 falls back cleanly, and a live `extract --limit 412 --extract-backend llm --llm-backend proxy --model gpt-4o` run processed one uncached quote successfully after two transient proxy 500 retries.


### 2026-04-18 20:59
Captured a key civgame architecture decision: mod content should live in JSON files validated by JSON Schema, not markdown. The mod foundation phase now explicitly includes nations.json plus first-class technologies, governments, wonders, scenarios, and event definitions so the project can support CTP2/Civ-II-style scenario editing and total-conversion packs later.


### 2026-04-18 21:01
Finished the repo-local Copilot/MCP bootstrap pass for C:\Users\user\notebooks\storywriter using google agent memory. The workspace now has a root README.md, targeted .github\instructions\ files for runtime and tests, and refreshed repo-wide Copilot guidance. Existing validation remained green via py_compile on two_pass_story_engine.py, storywriter_v3.py, and test_two_pass_story_engine.py plus unittest on test_two_pass_story_engine.py.


### 2026-04-18 21:04
Repo-local dungeon playthrough skill task is complete. Validation artifacts now live under `.react_agent\artifacts\blocked-move\`, the full unittest suite passes (`24` tests), and the harness reports `reached_boss=True` with `final_room='boss_sanctum'`. Remaining optional follow-up: confirm whether this environment auto-discovers project skills from `.copilot\skills\...` or wants a different project-local root.


### 2026-04-18 21:09
Finished the `civ-ruleset-scenario-foundation` milestone. Added typed content models, a default JSON content pack, schema generation, package-data wiring, a content loader, and regression coverage in `tests\\test_content.py`. Generated schema artifacts and confirmed the full civ pytest suite passes after the content externalization.


### 2026-04-18 21:20
Resolved the 'walking over enemies' regression and the coupled enemy-phase stall. Added gameplay tests for path-through rejection, non-overlapping charge contact, and opening-room enemy movement. Full dungeon unittest suite now passes at 27 tests, and a fresh `guard_post` end-turn run shows Shadow Assassins charging from `(16, 9)` to `(4, 9)` instead of staying idle.


### 2026-04-18 21:20
Graph-RAG extraction now preserves retry semantics for malformed LLM extraction payloads. Quotes with unrecoverable extraction JSON are skipped instead of being checkpointed with empty document payloads, so the next extraction run can retry them cleanly.


### 2026-04-18 21:33
Finished the requested working-proof and commit milestone for C:\Users\user\notebooks\storywriter using google agent memory. Validation passed with py_compile for two_pass_story_engine.py, storywriter_v3.py, and test_two_pass_story_engine.py plus unittest for test_two_pass_story_engine.py. A live story artifact was generated at copilot_bootstrap_story.md using the active storywriter_v3 pipeline, and a root commit was created containing README.md, .github\copilot-instructions.md, .github\instructions\storywriter-runtime.instructions.md, .github\instructions\storywriter-tests.instructions.md, and copilot_bootstrap_story.md. Follow-up remains on proxy resilience and structure-target honoring during live runs.


### 2026-04-19 03:00
Completed a repo-guidance refresh for C:\Users\user\notebooks\storywriter using google agent memory. The Copilot instructions file now matches the current codebase more closely: direct storywriter_v3.py commands for the active pipeline, run_demo.bat documented as the legacy demo path, validation commands preserved, and architecture/convention notes kept aligned with the current active and legacy runtimes.


### 2026-04-19 04:32
Completed a repo-guidance pass for C:\Users\user\Documents\dev\civctp2. Added .github\copilot-instructions.md with repo-specific build/test commands, architecture notes, and conventions drawn from README.md, CONTRIBUTING.md, .travis.yml, .gitlab-ci.yml, civpaths.txt, and the ctp2_code / ctp2_data / Scenarios layout.


### 2026-04-19 07:14
Storywriter Qwen endpoint integration progressed from failing chat-completions parsing to a working remote run path. The repo now has storywriter_v3.py changes that let the pipeline talk to the remote llama.cpp endpoint more safely, and qwen_llama_story.md was generated end-to-end. Remaining blocker: the server is currently using '--chat-template chatml', which increases context pressure and leaves Qwen reasoning traces enabled; because of that, several JSON planning calls degraded to heuristics and the scene loop still fell back to deterministic prose.


### 2026-04-19 07:30
Native-template Qwen rerun improved output quality but did not fully solve live generation. The manuscript qwen_llama_story_native.md was saved successfully, yet the planner still ignored the requested 1x1 target and generated 5 scenes, and the scene loop still fell back to deterministic prose for all scenes after request timeouts. The major regression from ChatML is gone, but remaining blockers are planner-shape control and scene-generation timeout resilience on the remote llama.cpp path.


### 2026-04-19 07:45
Finished a Graph-RAG extraction stability pass in C:\Users\user\notebooks\graphrag-rdf-lpg. Validated `graph_rag.py` with `python -m py_compile`, a mocked missing-`entities` extraction payload that now skips cleanly, and a live `extract --extract-backend llm --llm-backend proxy --model gpt-4o` run that processed multiple quotes without the prior fatal `ValueError: LLM extractor JSON must contain an 'entities' list.` crash.


### 2026-04-19 08:10
Storywriter Qwen work is paused pending upstream llama-server tuning on the user's master node. Latest completed artifacts: qwen_budgeted_story.md (better planning, fallback scenes) and qwen_derived_story.md (direct polished derivation from the improved scaffold). Remaining unresolved blocker at pause time: two-pass scene generation still exceeds context during live scene calls even after prompt budgeting; next resume point is to re-test against the updated server settings rather than continue local prompt trimming blindly.


### 2026-04-19 09:34
Added client-side timing heuristics and seeded retries to the storywriter_v3 Qwen path. Validation remains green via py_compile, the two-pass unit tests, and a live --test-llm call against the remote endpoint. Current resume point: use the hardened client on the next full story run instead of switching to a direct one-shot prose generation path.


### 2026-04-19 09:47
Timeout policy for the remote Qwen client is now aligned with the latest user requirement: hard 300s cap until 5 successful samples exist, then moving log-space median/MAD outlier detection for adaptive per-request timeouts. Validation after the change passed via py_compile, and a sanity check on the helper returned a nominal threshold from sample timings as expected.


### 2026-04-19 11:08
Finished the repo-backed content-loading pass for the civctp2 HTML MVP in C:\Users\user\Documents\dev\civctp2. Validation passed with py_compile, unittest on web\tests, HTML route rendering for base + MagnificentSamurai, and posted prompt/callback flow checks through FastAPI TestClient. Remaining planned work is the deeper normalized content model, gameplay action engine, richer map/panel wiring, and the SLIC runtime track.


### 2026-04-19 11:12
Completed the civctp2 run-documentation/startup pass. The HTML MVP is now documented in the root README and was started successfully on localhost:8000 with a live HTTP 200 response from `/sessions/default`. No code-path regressions were introduced; this pass only added run docs and booted the existing FastAPI app.


### 2026-04-19 11:57
Validated the scene-engine hardening with py_compile and `python -m unittest test_two_pass_story_engine.py` after adding coverage for audit/extraction JSON failure paths. A patched 1x1 remote Qwen pipeline run now completes to manuscript output (`qwen_timeout_story.md`) with model-written prose preserved even when extraction JSON is malformed; remaining work is tightening extraction robustness and separately investigating planner/backward-plan expansion beyond requested small structures.


### 2026-04-19 12:14
Completed end-to-end extraction over the full 2508-quote corpus and executed the meaning-of-life query on the finished graph. Final extraction stats: 32353 triples (obs=11478, pat=20384, inf=491), 16831 entities, 5095 predicates. Top retrieved quote remained the Viktor Frankl line ('Life has no meaning... you are the answer.'). Pending follow-up work remains around node normalization (lemma/synset+POS, positive-only negation handling) and holdout confirmation / a-mem intent-objective persistence.


### 2026-04-19 12:50
Completed the user-requested standalone Jaccard community mode. The graph now supports explicit community affinity selection without changing default composite behavior. Deferred follow-up: if desired, add `community_affinity_mode` as a categorical search factor in the tuning space rather than only a fixed CLI/frozen parameter.


### 2026-04-19 14:16
Reactive normalization cleanup and holdout confirmation are now complete. The eval loop emits a lemma-first cleanup queue from low-precision judge diagnostics, and the latest queue surfaces `authored -> author` as the top fix. Remaining work is optional follow-up only: persist a dedicated tuned-config artifact and, separately, the intent/objective-scoped wiki memory design.


### 2026-04-19 14:17
Validated the encoding/shape fixes with py_compile, `python -m unittest test_two_pass_story_engine.py test_storywriter_v3.py`, and a live remote Qwen smoke call returning `Elara’s hand hovered over the bridge’s parapet.` without mojibake. Added `test_storywriter_v3.py` coverage for mojibake repair and backward-plan scene clamping. Current status: future remote runs should preserve apostrophes correctly and keep backward-plan forward requirements aligned to the actual scene structure.


### 2026-04-19 14:34
Final delivery state is now commit-backed. README includes explicit query/evaluate/holdout/cleanup instructions, and the local repository is clean after ignoring generated runtime artifacts (`graphs/`, `logs/`, `chroma_quotes_db*/`, `lib/`, etc.). Recent commits: `bd2ba00`, `6158566`, `17647d7`.


### 2026-04-19 14:36
Validated the manuscript-assembly cleanup with py_compile and by confirming `qwen_timeout_story.md` now starts at `## Act 1` rather than an italicized synopsis using meta language like 'The protagonist'. Remaining storywriter follow-up is still extraction robustness under malformed Qwen JSON.


### 2026-04-19 16:15
Added a reusable Copilot skill for hyperparameter tuning under `~/.copilot/skills/hyper-parm_tuning/SKILL.md`. The artifact is complete and reusable outside the Graph-RAG project; no codebase files were changed for this task.


### 2026-04-19 16:16
Advanced the civctp2 HTML MVP from a content viewer into the first lightly playable shell. Validation passed with py_compile, unittest (`6` tests), live HTML route checks, live PNG terrain-asset checks, and live select-tile + move-scout POST flow on localhost:8000. Remaining gameplay gap is still substantial, but the delivered client now uses original terrain art and supports real map interaction rather than ASCII-style surrogate tiles.


### 2026-04-19 16:47
Validated the Qwen transport fix with py_compile plus unittest for test_storywriter_v3.py and test_two_pass_story_engine.py. Live rerun now advances past the previous Scene 1 timeout wedge and has stored 1 scene for story_id=5136cea9. Remaining known issue: extraction JSON can still fail on malformed Qwen output, which currently degrades safely to prose-only structured output.


### 2026-04-19 17:01
Revised the reusable hyperparameter tuning skill so it now covers the intended wiki-memory layer rather than only generic search strategy. The artifact now documents intent-scoped retrieval, objective exclusivity, entity-bag support, judge-driven updates, merge gates, create gates, and tunable controls for memory policy.


### 2026-04-19 17:13
Created a dedicated `agentic_kg_memory` skill and removed wiki-memory behavior from `hyper-parm_tuning`. The skill split now matches the intended boundary: one skill defines the memory system, the other defines how to tune systems once their behavior is already specified.


### 2026-04-19 17:52
Graph-RAG dedicated tuning is now artifact-backed. Best persisted config: `pool_size=21`, `gist_lambda=0.9`, `gist_k=5`, `gist_path_weight=0.32783132985506214`, `community_threshold=0.3565640591613225`, `entity_overlap_bonus=0.1098136044828372`, `community_path_weight=0.09222577678541438`, `community_affinity_mode=composite`, `max_hops=4`. Tuned holdout completed from that exact config, but holdout regressed to `scalar=0.7375` (`precision=0.7`, `recall=0.775`) versus the earlier default-stack holdout `0.80625`, so the tuning pass is complete but not an improvement over the prior serving baseline.


### 2026-04-19 18:38
Finished the first agentic dungeon harness milestone. The new guard-post policy clears `guard_post` through live frame-by-frame decisions, writes decision-linked artifacts under `.react_agent\artifacts\agentic-guard-post\`, and the dungeon unittest suite now passes at 28 tests. Deferred follow-up: extend the policy beyond the opening-room combat loop into multi-room or full-quest autoplay.


### 2026-04-19 18:59
## Layer 3 tuning complete (commit 1829f5e)

Replaced LLM-based RAGAS eval with deterministic ID-based metrics:
- Rank-sensitive precision@K (1/rank if ref paper found in top_k results)
- Binary recall (1.0 if ref paper anywhere in top_k)
- fit_score = (precision + recall) / 2

Results:
  tune (20q):   prec=0.350  rec=0.400  fit=0.379
  holdout (43q): prec=0.420  rec=0.558  fit=0.489

Best params: ew=0.5, top_k=8 (entailment_weight flat — only top_k mattered)

Production updated:
  syllogism_retriever.py: blend={title:0.3237, abstract:0.5803, utility:0.096}, top_k default→8
  entailment_ranker.py: ENTAILMENT_WEIGHT=0.5 (confirmed unchanged)
  best_retriever_params.json: written

All 3 tuning layers complete. Pipeline ready for production queries.


### 2026-04-19 19:04
Completed two storywriter milestones: (1) fresh full rerun finished successfully to qwen_full_story_fresh.md with 6 scenes and final coherence 0.77; (2) schema hardening landed so llm_json can request json_schema from the endpoint using Pydantic models instead of relying on generic json_object. Remaining follow-up is to expand schema use across more planning calls and verify the new schema path against a live rerun to reduce prose-only extraction fallbacks.


### 2026-04-19 19:34
Completed ontology leak fix for user-facing query artifacts. Verified graph and query traces for 'what is the meaning of life' no longer contain visible instance_of/has_label scaffolding or raw phrase nodes like what_happiness_consists_of. Current limitation: canonical entity ids are lemma/head based, not full WordNet synset IDs with a separate hypernym layer yet.


### 2026-04-19 19:51
Implemented live continuity artifact persistence and continuity-prompt hardening for storywriter_v3/two_pass_story_engine. Unit tests and py_compile passed after the patch. A detached continuity-focused full rerun is active (story_id=e6229435), writing qwen_full_story_continuity.md plus qwen_full_story_continuity_artifacts for per-scene inspection once scenes commit.


### 2026-04-19 20:10
Revised the live artifact persistence seam: continuity_bible / scene_prompt now write during prompt construction instead of waiting for the full two-pass scene result. Restarted the detached continuity-focused full rerun with the timing fix applied (story_id=1fbf7c44).


### 2026-04-19 20:13
Ontology cleanup is complete for current artifact mode. Verified refreshed meaning-of-life graph and query traces no longer contain visible raw phrase entities (`what_happiness_consists_of`), multi-word predicate ids (`look_for`, `search_for`, `consists_of`), or debug scaffolding (`instance_of`, `has_label`). Expected remaining provenance: lexical expansion `source_text` still preserves original phrases such as `What Happiness Consists Of` for auditability. Deferred work remains todo #20: explicit synset ids plus separate hidden hypernym/subClassOf layer.
