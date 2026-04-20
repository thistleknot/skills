# Progress

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
