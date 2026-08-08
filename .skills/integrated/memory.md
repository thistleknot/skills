Already have everything from the fetches. Here's the single unified prompt:

---

```
Crystallize the following completed work chain using the crystallization skill protocol.

## Work chain summary

Multi-session research thread converging on three repos and one architectural 
integration pattern:
- ActiveGraph (yoheinakajima/activegraph) — shared graph substrate for multi-agent 
  coordination
- SimpleMem (aiming-lab/SimpleMem) — agent session and cross-session memory
- MemoRAG (qhjqhj00/MemoRAG) — global memory-enhanced retrieval for long-context corpora
- TencentDB-Agent-Memory (Tencent/TencentDB-Agent-Memory) — reference architecture only,
  not an integration target (TypeScript/Node/OpenClaw, Python friction)

Goal: extract durable architectural lessons and produce a single integration 
directive for the existing OpenCode multi-agent harness + Chroma/pgvector/wiki 
memory stack.

---

## Question

What is the complete architecture for adding shared-state coordination, 
agent session memory, and corpus retrieval memory to an existing OpenCode 
multi-agent coding harness — and what are the durable lessons from each layer?

---

## Findings

### Layer 1 — Shared graph substrate (ActiveGraph)

Event-sourced reactive graph runtime. Every agent mutation is an append-only event. 
The graph is the world; the event log is the audit trail.

The graph replaces context-passing, not orchestration. Orchestrator still drives 
sequencing. Integration pattern:

  orchestrator writes job + assignee to graph → calls agent directly → 
  agent reads own assignment from graph → writes output to graph → 
  orchestrator reads result and assigns next

Handoff = object status transition. No agent needs to know any other agent exists.

Agent contract:
  Require(graph object exists, correct status) → Execute → 
  Guarantee(output written, status updated) → no direct agent-to-agent calls

Dispatcher routing table lives in orchestrator skill:
  task.status=open           → spawn coder
  task.status=review_ready   → spawn reviewer
  task.status=revision_needed → spawn coder
  task.status=failed         → spawn debugger
  task.status=approved       → check goal completion or decompose further

Relation behaviors handle dependency unblocking without a coordinator — logic 
on typed edges, not endpoints. Fork-and-diff branches at any historical event, 
diffs against parent; LLM replay cache means shared prefix doesn't re-execute. 
Use for coder→reviewer hypothesis testing without manual revert.

Stack: Python 3.11+, SQLite default, Postgres optional. v1.0 stable May 2026.

### Layer 2 — Agent session memory (SimpleMem)

Three-stage pipeline at write time + intent-aware retrieval at read time.

Stage 1 — Semantic Structured Compression (write time, not async):
- Entropy-aware filtering during LLM generation
- Raw dialogue → atomic units: coreferences resolved, timestamps anchored absolute
- 3-view indexing: dense vector 1024-d, BM25 sparse, symbolic metadata
- Example: "He'll meet Bob tomorrow at 2pm" →
  "Alice will meet Bob at Starbucks on 2025-11-16T14:00:00"

Stage 2 — Online Semantic Synthesis (write time, not background):
- Related fragments consolidated on-the-fly into higher-level abstractions
- Memory topology stays compact immediately, no cleanup debt

Stage 3 — Intent-Aware Retrieval Planning (read time):
- LLM generates retrieval plan from query intent, not fixed-depth search
- Parallel multi-view retrieval across semantic, lexical, symbolic indexes
- Depth adapts: single-hop → minimal; multi-hop temporal → expanded
- Result: 43.24% F1 with 30× fewer tokens than full-context (LoCoMo-10)

Cross-session module (SimpleMem-Cross):
- SQLite (sessions/events/observations) + LanceDB (vector + provenance)
- Lifecycle: start_session → record_message/tool_use/file_change → stop_session
- Observation extraction: decisions, discoveries, learnings per session
- Provenance: every memory entry links to source evidence
- Consolidation worker: decay, merge, prune
- 64% improvement over Claude-Mem on LoCoMo

EvolveMem (v3.0):
- Retrieval policy self-evolves via LLM closed loop:
  Evaluate → Diagnose → Propose config changes → Guard regression → Repeat
- Discovers retrieval dimensions not in original design (AutoResearch on itself)
- Architecturally identical to existing TextGrad RAG optimizer + greedy hill climbing
- Merge target: run against existing RAGAS fitness function rather than separately

Omni-SimpleMem: text, image, audio, video unified memory. Knowledge graph 
augmentation for cross-modal reasoning. SOTA LoCoMo F1=0.613 (+47%), 
Mem-Gallery F1=0.810 (+51%).

Storage: LanceDB (vector), SQLite (metadata), BM25. Python 3.10, PyPI, MCP server.
Near-term actionable — drops into existing Python stack with minimal friction.

### Layer 3 — Corpus retrieval memory (MemoRAG)

Not an agent memory system. A retrieval paradigm.

Dual-system architecture:
- Memory model (lightweight long-range LLM: memorag-qwen2-7b-inst, 400K-1M tokens)
  builds global understanding of the entire corpus database
- Generator (expensive LLM, swappable: GPT, Mistral, Llama) produces final answer

The key mechanism: given a query, the memory model generates clues — surrogate 
queries and draft answers — that guide the retriever to the right evidence. 
Standard retriever (BGE-M3 + FAISS) finds passages. Generator answers from those.

Three memory model operations:
  memo.recall(query)  → text clues for retrieval guidance
  memo.answer(query)  → direct answer from global memory
  memo.rewrite(query) → query decomposed into surrogate queries

This is HyDE but trained, not prompted. Outperforms HyDE, BGE-M3, RQ-RAG across 
LongBench, InfBench, UltraDomain benchmarks.

Caching: KV cache + FAISS index + chunked passages persisted to disk.
  200K tokens: 35s to encode, 1.5s to reload from cache.
  Fits on 16GB GPU under default settings (Quadro P5200 compatible).

Beacon ratio parameter extends context window:
  memorag-qwen2-7b-inst default: 400K tokens
  beacon_ratio=16: up to 1M tokens

Generator is pluggable — OpenAI-compatible API supported. Memory model and 
generator are independent; use local memory model + API generator or vice versa.

Stack: Python, HuggingFace, FAISS, Apache 2.0. Training scripts + dataset released.
pip install memorag.

Relevance to existing stack: not OpenCode session memory — this is the retrieval 
layer for the scientific literature pipeline. MemoRAG's global memory understands 
corpus shape (entity relationships across the whole corpus) rather than individual 
chunks. Directly replaces or augments the current BM25+dense+ColBERT+cross-encoder 
pipeline. The memory model does structurally what the throughline node and ingredient 
knowledge graph do explicitly — but learned, not constructed.

### Reference architecture concepts (TencentDB — no integration)

L0-L3 semantic pyramid (concept only):
  L0 Conversation → L1 Atom (atomic facts, every N turns) →
  L2 Scenario (scene blocks, Markdown) → L3 Persona (user profile)
  Upper layers = structure. Lower layers = evidence.
  Drill-down chain: Persona → Scenario → Atom → Conversation (deterministic).

Mermaid canvas for short-term working memory (concept only):
  Verbose tool logs offloaded to filesystem with node_id references.
  Agent operates on Mermaid graph (hundreds of tokens), drills down on demand.
  Cuts token usage 61.38% in benchmark vs baseline.
  Apply this pattern to dark factory session state: encode task state as 
  symbolic graph, not prose.

### How the three active layers integrate

Session graph (ActiveGraph) = ephemeral world state for this run.
Session memory (SimpleMem-Cross) = persistent memory across runs.
Corpus retrieval (MemoRAG) = global understanding of the literature/knowledge corpus.

SimpleMem-Cross lifecycle maps to OpenCode session boundary:
  orchestrator.start_session(goal) → previous context injected automatically
  each agent: record_tool_use, record_file_change
  orchestrator.stop_session() → extracts observations, writes to persistent memory
  next session: orchestrator reads prior context before decomposing goal

MemoRAG sits upstream of the RAG pipeline, not inside the agent session:
  query arrives → memory model generates clues → retriever finds passages →
  agent receives retrieved context → writes output to graph

---

## Entities involved

- ActiveGraph (yoheinakajima/activegraph, v1.0, Python 3.11+, MIT)
- SimpleMem (aiming-lab/SimpleMem, v0.2.0, Python 3.10, MIT, PyPI)
- SimpleMem-Cross, EvolveMem, Omni-SimpleMem (components of SimpleMem)
- MemoRAG (qhjqhj00/MemoRAG, v0.1.5, Python, Apache 2.0, WebConf 2025)
- memorag-qwen2-7b-inst, memorag-mistral-7b-inst (HuggingFace memory models)
- TencentDB-Agent-Memory (reference only, not integration target)
- OpenCode multi-agent harness (orchestrator, coder, reviewer, debugger, researcher)
- Tekiner context graph (governance/provenance layer, four metadata categories)
- arXiv 2605.18747 — Code as Agent Harness (Ning et al., May 2026)
- ActiveGraph primitives: Graph, Behavior, RelationBehavior, Patch, Frame, Fork
- Existing stack: Chroma, pgvector, wiki, SPO triplets, MemRL Q-score,
  TextGrad optimizer, GATv2, BM25+ColBERT+cross-encoder pipeline, dark factory harness

---

## Lessons

1. The graph replaces context-passing, not orchestration. Orchestrator stays as 
   sequencer. Status transitions are the inter-agent protocol.

2. Design the status state machine before writing any agent logic. The routing 
   table (status → agent) lives in the orchestrator skill only.

3. Fork-and-diff is the mechanism for hypothesis testing without manual revert. 
   Wire into the coder→reviewer loop.

4. Write-time synthesis beats background maintenance. Consolidate on write; 
   background worker only for decay/merge/prune of old memories.

5. Atomic memory units require three representations: dense vector, BM25 sparse, 
   symbolic metadata. RRF fusion across all three is the baseline. Fixed top-k 
   without intent-awareness degrades under query diversity.

6. Intent-aware retrieval planning: retrieval scope should be LLM-reasoned from 
   query intent, not a fixed k. Depth adapts to query complexity.

7. Lossless drill-down chain is required. Abstraction must trace deterministically 
   to source evidence. Maps to: SPO triplet → BIO-tagged span → raw conversation.

8. EvolveMem = TextGrad loop with a narrower target. Same structure. Merge into 
   existing RAGAS-scored fitness rather than running as a separate system.

9. Session lifecycle hooks are the integration surface. start_session / record_event 
   / stop_session is the right shape for OpenCode agent session management. This is 
   the Tekiner context graph write-back mechanism, implemented.

10. MemoRAG's memory model generates retrieval clues from global corpus understanding. 
    This is what the throughline node and ingredient knowledge graph do structurally — 
    but learned. Replace or augment the current colBERT+cross-encoder reranking layer 
    with MemoRAG's recall() output as the retrieval query.

11. Mermaid canvas as symbolic short-term working memory. Encode task state as a 
    symbolic graph; offload raw evidence; retrieve by node_id. Apply to dark factory 
    session state and OpenCode agent context.

12. Token budget is explicit architecture. Canvas constrained to a ratio of context 
    window. Retrieval depth adapts to query complexity. Treat token cost as a 
    first-class constraint in every memory layer.

13. Provenance tracking is first-class at every layer. ActiveGraph: every mutation 
    is an event. SimpleMem: every memory entry links to source. MemoRAG: KV cache 
    traces to original corpus chunks. Maps to SPO epistemic tagging and MemRL 
    Q-score updates.

---

## Open questions

- ActiveGraph status state machine: define object types and status transitions for 
  the 5-role OpenCode harness (orchestrator/coder/reviewer/debugger/researcher)
- Mermaid canvas node/edge schema for dark factory coding session state 
  (task, subtask, file, test, failure, patch) — bounded design task
- MemoRAG integration point: does recall() replace the ColBERT reranking query, 
  or sit upstream as a query expansion step before BM25+dense retrieval?
- MemoRAG on Quadro P5200 16GB: confirm beacon_ratio ceiling before OOM; 
  test memorag-qwen2-7b-inst at default settings first
- SimpleMem-Cross consolidation decay schedule for coding memory — what half-life 
  is appropriate for code decisions vs conversational preferences?
- EvolveMem + TextGrad merge: single RAGAS fitness function or separate retrieval 
  fitness with RAGAS as a component?
- Optimistic concurrency: patch rejection protocol when multiple agents write 
  concurrently to the same ActiveGraph object
- Whether Omni-SimpleMem's KG augmentation overlaps with existing GATv2 + BM25 
  Graph-RAG pipeline or addresses a distinct cross-modal retrieval problem

---

## Routing

- Digest page → agentic_kg_memory
- Entity triplets → agentic_kg_memory
- Lesson 8 (EvolveMem ↔ TextGrad merge) → skill-wiki: flag autoresearch skill 
  for update to cover retrieval policy evolution as first-class target
- Lesson 9 (session lifecycle hooks) → skill-wiki: staged draft for OpenCode 
  session memory skill, start/record/stop contract
- Open question: Mermaid schema → add_todo: design canvas node/edge schema 
  for dark factory coding session state
- Open question: ActiveGraph status state machine → add_todo: define object types 
  and transitions for 5-role OpenCode harness
- Open question: MemoRAG integration point → add_todo: benchmark recall() as 
  upstream query expansion against existing BM25+ColBERT pipeline on RAGAS
```