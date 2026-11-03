# retrieve-skills SPEC

CURRENT disposition (2026-08-06, v3): single de facto skill named
`retrieve-skills` at `~/.claude/skills/retrieve-skills/`; the corpus lives at
`~/.claude/skills/.skills/` — a sibling dot-directory under the skills root.
Both locations rest on the same verified premise: discovery is one level deep
(`<root>/<name>/SKILL.md`), so `.skills/<name>/SKILL.md` (two levels) is never
discovered. Always-on exception: skills @-imported from CLAUDE.md/AGENTS.md
stay in natural location and OUT of the store — @-import works from any path,
but store membership would double-inject them. One fastmcp process serves the
gate two ways: MCP tools (`retrieve_skills`, `read_skill`) for model-invoked
mid-task retrieval, and HTTP `/route` for the deterministic per-prompt hook.
Stub battery + live modelless integration passed. Real model backends
(MiniLM, jina-colbert-v2) confirmed on the target machine via sweep.py
cross-validation.

SUPERSEDED (v2, 2026-08-06): corpus nested inside the skill folder at
`<skill-router>/skills/`, skill named skill-router. Replaced by user-specified
layout: store as sibling `.skills/` under the skills root, skill renamed
retrieve-skills. Same discovery premise; only paths and naming changed.

SUPERSEDED (v1, 2026-08-06): hook-only topology with the store at
~/skill-store and `deny: ["Skill"]`. Killed by two findings: (a) the router
works better as one deployable skill folder whose SKILL.md is the lone
discovered skill — which requires the Skill tool to stay ENABLED (deny would
kill the router's own invocability); (b) hook-only misses mid-task needs —
the MCP tool lets retrieval fire from task state, not just the raw prompt.
The hook remains as the deterministic auto-injection path; the deny rule is
dropped.

## Objective

A RAG gate sitting between the user prompt and non-mandatory system-prompt
injections (Claude Code skills). Replaces model-driven skill triggering:
dense top_k over skill descriptions -> jina-colbert-v2 rerank -> median-margin
gate -> inject accepted skills; else no skills. Two entry points, one gate:
UserPromptSubmit hook (deterministic, per prompt) and MCP tools (model-invoked,
mid-task). Mandatory ("always on") skills stay as `@path` imports in CLAUDE.md
and bypass the gate.

## Requirements (EARS)

- When a user prompt is submitted, the hook SHALL request routing from the
  local server and SHALL inject only accepted skills as additionalContext.
- If the server is unreachable, times out, or errors, the hook SHALL emit
  nothing and exit 0 (fail-open: no skills, prompt proceeds untouched).
- While a session is active, the router SHALL NOT inject the same skill twice
  (session dedup, sqlite-backed).
- Where INJECT_MODE=body, the injected block SHALL contain the complete SKILL.md
  body stripped of frontmatter. The router SHALL NOT truncate skill bodies;
  context budget is managed by the accept gate (max_accept), not by silently
  clipping documents.
- When reindexing, the indexer SHALL re-embed only skills whose description
  hash changed (load-if-exists checkpointing).

## Contracts

- **Require**: SKILL_STORE (default `~/.claude/skills/.skills/`) contains
  `<skill>/SKILL.md` files with YAML frontmatter carrying `name` and
  `description`; server started (start.sh) and healthy; MCP server registered
  (`claude mcp add --transport http`); hook registered in settings.json;
  retrieve-skills and @-imported always-on skills are the only directories
  directly under the skills root; store and @-imports disjoint; the Skill
  tool stays ENABLED (no deny rule — the router skill must be invocable).
- **Guarantee**: route() returns <= MAX_ACCEPT skills, each having passed
  recall (cosine top_k) and rerank (top RERANK_KEEP with margin above median).
  Empty index or empty prompt -> [].
- **Maintain**: one index row per skill name; embeddings stored normalized;
  per-prompt added latency bounded by hook timeout (default 2.5s) regardless
  of server state.
- **Assert**: hook emits valid `hookSpecificOutput` JSON or nothing; exit 0 on
  all paths; server /route validates request via pydantic.

## Acceptance

1. `test_gate.py` battery (all stubs, no model downloads): frontmatter parsing
   (5 varied fixtures), checkpoint re-embed counts (3 scenarios), top_k
   ordering (3 vector sets), gate accept/reject/cap (3 prompts), session
   dedup, hook fail-open subprocess check, hook contract integration against
   a stub HTTP server. All must pass.
2. Live modelless integration (SKILL_ROUTER_EMBED_MODEL=stub, RERANK=none):
   index fixtures -> start server -> /health -> hook end-to-end
   injection -> MCP client calls retrieve_skills + read_skill.

## Structure

- `SKILL.md` — the one discovered skill: tool advertisement + ops runbook.
- `../.skills/` — the corpus (sibling dot-dir under the skills root; undiscovered).
- `router_core.py` — pure logic: parsing, sqlite index, recall, gate. Scorers
  are injected callables (real models or stubs).
- `model_backends.py` — embedder (incl. stub backend) / reranker (pylate
  local | Jina API | none) singletons.
- `server.py` — fastmcp: tools retrieve_skills + read_skill; custom routes
  /health, /route, /reindex.
- `indexer.py` — CLI reindex (same checkpointing path as /reindex).
- `hook.py` — stdlib-only UserPromptSubmit client, fail-open.
- `settings.snippet.json`, `start.sh`, `test_gate.py`.
