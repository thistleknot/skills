> SUPERSEDED 2026-10-26: merged into `SKILL.md` (R14 and related edits). Kept as source text; do not route to it.

 **Skill:** `agentic_memory_lifecycle`
Description:
Manages the end-to-end lifecycle of agentic long-term memory: extraction, structuring, validation, consolidation, forgetting, and retrieval. Use when an agent must persist cross-session knowledge, evolve its harness memory component, or prevent context bloat and retrieval decay.

When to Use
Cross-session trajectory distillation
Harness memory component optimization
Preventing context window bloat or retrieval noise
Establishing durable semantic/episodic/procedural memory stores
Do not use when:

Managing ephemeral in-context folding or KV-cache state
Fine-tuning base model weights (parametric memory)
Logging raw activity without a retrieval or validation objective
Scope Boundary
Owns the memory pipeline between execution and persistence.

Owns: Fact extraction, structural routing (graph/vector/hierarchical), update validation gates, consolidation/forgetting logic, and active retrieval injection.
Does not own: Base model training, transient context window management, or external tool execution.
Protocol
Extract — Parse raw trajectories into atomic facts, episodic events, semantic concepts, and procedural steps. Resolve coreferences and anchor temporally. (AtomMem, MIRIX)
Structure — Route into specialized stores. Map entities and relations into associative/knowledge graphs; embed summaries for vector search. Maintain type separation to avoid flat-store retrieval collapse. (MIRIX, HippoRAG)
Validate — Gate proposed memory/skill updates. Run control-vs-treatment execution or require recurrence across tasks before admission. Reject spurious shortcuts or hallucinated facts. (HDSO, Metis)
Consolidate & Forget — Merge redundancies, update strength/recency weights (Ebbinghaus decay), and retire stale entries when contribution fades. Cap active memory size to prevent library drift. (MemoryBank, Library Drift, RMM)
Retrieve — Trigger active retrieval on task intent. Combine graph traversal (for relational/step logic) with vector search (for semantic match). Inject precise, non-noisy context into the execution harness. (AtomMem, MIRIX, Harness 2)
Output Artifacts
Structured Memory Index — Graph/vector store with typed nodes (episodic, semantic, procedural) and temporal/relational edges.
Validation Log — Admission/rejection record with control-vs-treatment evidence or recurrence counts.
Consolidation Report — Merged facts, retired entries, and decay-adjusted weights.
Retrieval Injection — Task-aligned memory context formatted for prompt injection.
Routing Rules
ARTIFACT / ACTION
DESTINATION
Raw trajectory → atomic facts
Extraction module
Facts → relational/semantic mapping
Graph/Vector store
Proposed memory update
Validation gate (control-vs-treatment)
Stale/low-utility entries
Retirement log (library drift prevention)
Task execution requiring history
Active retrieval + prompt injection


Dead Ends (Do Not Use)
Flat storage without routing: Dumping all memories into a single vector store causes isolated matching and retrieval noise.
Unconstrained LLM rewrites: Letting the model freely edit memory leads to hallucination accumulation and bloat.
Validating after deployment: Admitting updates without control checks encodes spurious shortcuts that degrade future harness performance.
Infinite accumulation: Skipping forgetting/retirement guarantees retrieval decay (library drift) regardless of model capability.
SOTA Mapping
PROTOCOL STEP
GROUNDED METHODS
Extract
AtomMem (atomic facts), MIRIX (6-type separation)
Structure
HippoRAG (knowledge graphs), MIRIX (hierarchical routing)
Validate
HDSO (control-vs-treatment), Metis (recurrence gates)
Consolidate/Forget
MemoryBank (Ebbinghaus decay), Library Drift (retirement caps), RMM (reflective RL)
Retrieve
AtomMem (associative graph recall), Harness 2 (active intent retrieval)


This skill operationalizes the literature into a reusable, gated pipeline that treats memory as an editable, validated harness component rather than a passive log.