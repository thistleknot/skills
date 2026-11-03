## 2026-11-02 — Align wiki scope and retrieval defaults
**Changed:** Mapped wiki `global`/`repo` labels to memory-index `shared`/`project` scope; documented `session` context; made lexical retrieval the default and marked Chroma/dense multi-view storage as proposals only.
**Reason:** The graph skill mixed two scope vocabularies and described dense/Chroma paths as defaults even though the active memory-index MCP is scoped SQLite with dense retrieval disabled.
**Evidence:** `conversation_store.py` accepts project/session/shared records and rechecks scope; `memory_stats` reports `dense_enabled: false`; the separate Chroma CLI is not the graph's authorization store.
**Supersedes:** The earlier global/repo scope mapping without API labels and unconditional Chroma/dense retrieval defaults.

## 2026-11-02 — Bind graph setup to the incumbent memory store
**Changed:** Replaced the executable separate-SQLite/Chroma setup recipe with a boundary that forbids a second store until a code-level spec and migration plan extend the active memory-index MCP; clarified that legacy Chroma recall promotion is not graph admission; marked dense retrieval optional.
**Reason:** The skill's setup recipe conflicted with the shared-store architecture and current admission policy.
**Evidence:** `memory-index/mem_server.py` serves the scoped SQLite MCP and read-only recall; `memory-index/README.md` and `mem.py` describe a separate legacy Chroma CLI with three-hit promotion; `memory_stats` reports the active SQLite store and dense disabled.
**Supersedes:** The standalone `wiki_memory.sqlite3`/Chroma setup recipe, preserved in `history/2026-11-02-superseded-graph-setup.md`.

## 2026-11-02 — Hash the opened representation
**Changed:** Defined `source_sha256` over the exact redacted UTF-8 body returned by `open_memory`; added a stored character count known at ingestion, a 6000-character bound, and fail-closed completeness checks.
**Reason:** The source-opening API redacts and bounds output, so a consumer cannot verify a hash over unavailable original bytes.
**Evidence:** `memory-index/mem_server.py` calls `open_memory` with a 6000-character limit and renders the returned body; `conversation_store.py` redacts the opened content before return.
**Supersedes:** The earlier wording that described the hash as covering the original complete chunk bytes.

## 2026-11-02 — Chunk-bound evidence and scope snapshots
**Changed:** Defined graph spans over complete opened chunks no larger than the memory-index open bound; source hashes cover those exact bytes; scope snapshots are prefilters while memory-index remains the authority; graph paths enter ranking only after source reauthorization and hash/version checks.
**Reason:** The first scope edit named authorization but did not define bounded-source hashing or the fields needed to prefilter graph candidates without leaking out-of-scope paths.
**Evidence:** `memory-index/mem_server.py` bounds `open_memory` to 6000 characters and returns current memory/raw IDs, project URI, scope, and session; `conversation_store.py` repeats scope authorization on open.
**Supersedes:** The earlier graph-scope wording that did not name the bounded chunk or source scope snapshot fields.

## 2026-11-02 — Scope-safe graph source handoff
**Changed:** Bound each edge to a memory-index record and raw revision; added project/session/shared scope snapshots; require authorization filtering and `open_memory` revalidation before graph ranking or traversal; defined exact chunk hashing and offsets.
**Reason:** Source version and hash alone did not prevent a graph query from considering evidence outside the caller's workspace or session.
**Evidence:** `memory-index/conversation_store.py` stores project URI, scope, session, raw ID, and repeats authorization at open; the graph schema had no scope handoff.
**Supersedes:** The earlier source-only provenance contract, which omitted scope filtering.

## 2026-11-02 — Ontology preserves evidence identity
**Changed:** Made kg_ontology forward source revision/hash, exact offsets, polarity, and inference classification unchanged while canonicalizing node identity.
**Reason:** Entity normalization must not collapse distinct evidence versions or rewrite span coordinates.
**Evidence:** `kg_ontology/SKILL.md` defines identity/provenance ownership; `agentic_kg_memory/SKILL.md` defines the immutable source contract. No runtime ontology code was changed.
**Supersedes:** The weaker instruction to preserve only general triplet epistemics/confidence metadata.

## 2026-11-02 — Immutable source identity and score separation
**Changed:** Added immutable source revision/hash and exact offset semantics to the proposed edge schema; expanded evidence identity to retain polarity/inference variants; specified a verified, audit-preserving migration boundary; separated epistemic support from downstream task utility and prohibited throughline score updates without a verified memory binding.
**Reason:** The proposed key could collide across opposing evidence, offsets had no unit or source revision, and entailment labels were incorrectly mapped onto helpful/harmful utility outcomes.
**Evidence:** `memory-index/conversation_store.py` stores immutable source references and accepts only idempotent `helpful`/`harmful` feedback; `agentic_kg_memory/SKILL.md` previously mixed entailment and task utility in q_score rules. No runtime graph schema or throughline feedback binding was found or changed.
**Supersedes:** The prior illustrative edge key and the rule mapping support/entailment to positive utility and contradiction to negative utility.

## 2026-11-02 — Source-backed graph paths and admission
**Changed:** Replaced co-occurrence edge creation with candidate-only entity discovery; required canonical, source-spanned graph relations; separated graph-assisted retrieval from graph-assisted reading; kept graph traversal behind matched controls; removed recall-driven promotion, scoring, reinforcement, and pruning; aligned memory admission with R14.
**Reason:** The skill's Pass 0, retrieval routing, and promotion instructions contradicted its source-validation section and the current memory-index R4/R14/R21 contracts.
**Evidence:** SpecsDB requirements #69–#72; decision #35; `docs/references/context-graph.md` (visible retrieval noise, raw passages unavailable); `docs/playbooks/memory-and-harness-integration.md` R4, R14, R21.
**Supersedes:** Entity co-occurrence as an asserted relation; three-recall promotion; query-time reinforcement and read-count pruning; unconditional graph retrieval. The newer canonicalization and GLiNER candidate-span guidance remains in force.
