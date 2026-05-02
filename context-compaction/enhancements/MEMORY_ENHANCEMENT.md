# Enhancement Patch: context-compaction — Consolidation Policy by Memory Type

## Source

AI Meets Brain (2512.23343) — distinguishes factual (static), experiential (evolving), and working (volatile) memory with different lifecycle behaviors.

## Problem

Current `context-compaction` uses a **uniform eviction policy** across all memory content.
Every item beyond the context window is treated as equally eligible for eviction. This is
suboptimal because:

- **Factual memory** (agent guidelines, user preferences, established rules) should rarely or never be evicted
- **Experiential memory** (past experiences, lessons learned) should have configurable decay based on recency and frequency of re-access
- **Working memory** (active task state, tool output) is genuinely volatile and should follow current eviction logic

## Proposed Changes

### 1. Memory Type Annotation on PreCompact Packets

Extend `CompactionPacket` to mark items by memory type:

```python
class CompactionItem(BaseModel):
    content: str
    memory_type: Literal['factual', 'experiential', 'working']
    priority: int                    # 1-5, 5 = must keep
    access_frequency: int            # how many times referenced in past N turns
    last_accessed: datetime          # for exponential decay calculation
```

**Memory type classification rules:**
- `factual` — guidelines, preferences, rules, user instructions, established facts
- `experiential` — past decisions, lessons learned, do_not_redo entries, approaches tried
- `working` — active task state, intermediate results, tool output, current reasoning steps

**How the agent classifies:** PreCompact hook inspects each item. Items matching the patterns
above are annotated. If uncertain, default to `working` (safe, evicted first).

### 2. Type-Aware Eviction Policy

Modify the PreCompact hook to respect memory type priorities:

```
PreCompact hook execution:
  1. Classify each item -> memory_type + priority + access_frequency
  2. Sort by eviction eligibility:
     - Working items: sort by last_accessed (oldest first, evict first)
     - Experiential items: sort by decay_score(access_frequency, last_accessed)
     - Factual items: KEEP unless priority < 2
  3. Allocate budget:
     - factual: 80% of output budget (they fit, they're important)
     - experiential: 15% of output budget (compress, summarize)
     - working: 5% of output budget (keep only next_steps, blockers)
  4. If over budget: evict working first, then experiential (decayed), never factual
```

### 3. Exponential Decay for Experiential Memory

Experiential items decay based on access patterns:

```python
def decay_score(access_frequency, days_since_last_access, half_life=7.0):
    decay = 0.5 ** (days_since_last_access / half_life)
    return decay * min(access_frequency, 10) / 10  # normalize to [0, 1]
```

**Default half-life:** 7 days. Tunable per project. Items with `decay_score < 0.2` become
eligible for eviction over factual and high-priority experiential items.

**Rationale:** From Ebbinghaus forgetting curve. Memory that is never re-accessed decays.
The agent should preferentially evict these, preserving memory that remains relevant.

### 4. Updated PreCompact Packet Contract

```python
class CompactionPacket(BaseModel):
    session_id: str
    task_summary: str
    decisions: list[CompactionItem]          # marked as 'factual' or 'experiential'
    open_questions: list[CompactionItem]    # 'experiential' (revisited)
    artifacts: list[ArtifactRef]            # 'factual' (file references)
    next_steps: list[CompactionItem]        # 'working' (ephemeral, needed immediately)
    do_not_redo: list[CompactionItem]       # 'experiential' (re-learned insights)
    compacted_at: datetime
    memory_types: dict[str, int]            # 'factual': chars, 'experiential': chars, 'working': chars
```

### 5. Updated PostCompact Rehydration

PostCompact should restore items in order of memory type stability:

```
Rehydration order:
  1. Factual items first (stable context foundation)
  2. Experiential items (decay-scored, highest-scoring first)
  3. Working items last (only what's immediately needed)
```

This mirrors biological memory consolidation: stable semantic memories are restored
first, followed by recent episodic memories.

### 6. Anti-Pattern Section Update

Add to "Failure Modes" in `context-compaction/SKILL.md`:

```markdown
## Failure Modes (Type-Aware Compaction)

| Symptom | Root cause | Fix |
|---|---|---|
| Guidelines lost after compaction | Labeled as 'working' instead of 'factual' | Ensure PreCompact correctly classifies user instructions as factual |
| Key decisions evicted too soon | Half-life too short, or decision not re-accessed | Increase half-life for items with high priority (>=4) |
| Factual items overwriting each other | Factual budget exceeded | Split factual into separate compact files; never merge from different sessions |
| Experiential memory accumulation | Decay function too conservative | Tune half-life downward if memory bloat observed |
```

Add update to the "Evidence" section:

```markdown
- Ebbinghaus forgetting curve — exponential decay model for memory over time
- AI Meets Brain (2512.23343) — factual/experiential/working memory lifecycle distinctions
```

## Implementation Order

1. Define `CompactionItem` model with `memory_type` field
2. Update PreCompact hook to classify and sort by type
3. Implement exponential decay function for experiential items
4. Update PostCompact rehydration ordering
5. Update SKILL.md failure modes and evidence
6. Test with a long-running session (>20 turns), verify factual items survive

## Evidence

- AI Meets Brain (2512.23343) — three-type memory lifecycle
- Ebbinghaus forgetting curve (1885) — exponential decay model
