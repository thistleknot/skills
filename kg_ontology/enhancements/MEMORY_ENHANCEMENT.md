# Enhancement Patch: kg_ontology — Temporal Entity Resolution

## Source

AI Meets Brain (2512.23343) Section 4.1.3 — biological systems distinguish entity identity from entity state across time. The hippocampus (episodic) and prefrontal cortex (procedural) each track entity states, while the neocortex maintains stable entity identity.

## Problem

`kg_ontology` resolves surface form variations of entity names ("SOW", "Statement of
Work", "sow") to a single canonical node. However, it assumes entities are **static**:
the same canonical node applies regardless of when the entity is referenced.

This breaks down when entities change state over time:
- A file `config.yaml` existed at version 1.2 but was upgraded to version 2.0
- A tool `pydantic` was at v1.x but is now at v2.x
- A decision "use SQLite not PostgreSQL" was made in January but reversed in March
- A user `Jack` had a broken bowl at timestamp T1 but bought a new one at T2

Currently, all states collapse into a single node, losing the temporal dimension.
Queries like "what was the state of X at time T?" cannot be answered.

## Proposed Changes

### 1. Entity State Versioning

Each DKG canonical node gains a **temporal dimension**:

```sql
ALTER TABLE canonical_nodes ADD COLUMN current_version TEXT DEFAULT '0';

CREATE TABLE entity_states (
    state_id TEXT PRIMARY KEY,
    canonical_node_id TEXT REFERENCES canonical_nodes(page_id),
    version TEXT NOT NULL,             -- semver-like: '1', '1.2', 'v2'
    valid_from DATETIME NOT NULL,
    valid_to DATETIME,                 -- NULL = current (not yet superseded)
    state_attributes TEXT NOT NULL,    -- JSON: entity properties at this version
    confidence_score REAL NOT NULL,
    extracted_from TEXT REFERENCES canonical_nodes(page_id)  -- provenance
);
```

**Key distinction:**
- `canonical_nodes` = entity identity (what thing is), changes rarely
- `entity_states` = entity state/timeline (what thing was at time T), changes frequently

### 2. Temporal Query Resolution

When resolving entity mentions in text, the ontology layer considers **temporal context**:

```
Text: "Jack bought a new bowl because the old one was broken"
         |                              |
         |                              |-> current state (bowl #2, intact)
         |-> past state (bowl #1, broken at T1)

Without temporal resolution: both phrases resolve to "bowl", loss of distinction
With temporal resolution: two distinct states of entity "bowl" in different time windows
```

**Implementation heuristic:**
1. Extract temporal markers from text: "old", "previous", "new", "now", dates, "at T1"
2. If temporal markers present, resolve to specific `entity_states` version
3. If no temporal markers, resolve to `valid_to IS NULL` (current state)

**For continuity-log entries and episodic records:**
Each entry carries a timestamp. When the episodic record references an entity,
the temporal resolution uses that timestamp to select the correct entity state.

### 3. State Transition DAG (New Sub-Layer)

Add a lightweight state transition graph to capture how entities evolve:

```
entity "config.yaml"
  state "v1.2" (valid_from: 2026-01-01, valid_to: 2026-01-15)
    |-> state "v2.0" (valid_from: 2026-01-15, valid_to: NULL)
       |-> state "v2.1" (valid_from: 2026-02-01, valid_to: NULL)

entity "tech_stack" (a user preference/decision)
  state "SQLite + Chroma" (valid_from: 2025-06-01, valid_to: 2026-01-01)
    |-> state "SQLite + Chroma + pgvector" (valid_from: 2026-01-01, valid_to: NULL)
```

This transition graph is a **separate concern** from the procedural DAGs in
`procedural-memory`. Procedural DAGs model *action dependencies*; state transition
DAGs model *entity evolution*. Both are DAGs but serve different purposes.

### 4. Integration with Existing KG Layers

```
 +-----------------------------------------------------------+
 |  kg_ontology (SKILL.md)                                   |
 |                                                           |
 |  DKG Entity Identity Layer:                               |
 |    - resolves surface forms to canonical node             |
 |  DKG State Resolution Layer:  (NEW)                       |
 |    - resolves canonical node + timestamp to entity state  |
 |                                                           |
 |  agentic_kg_memory (CG side):                             |
 |    - patterns, throughlines, episodic retrieval           |
 |    - references entity_states via canonical_node_id       |
 |                                                           |
 |  procedural-memory (logic layer):                         |
 |    - procedural DAGs reference entity_ids, not states     |
 |    - when a procedure depends on an entity, it depends on |
 |      the entity's state at the time the procedure was     |
 |      extracted                                            |
 +-----------------------------------------------------------+
```

**Key rule:** Proximity queries resolve to the entity's **state at the time of
the event**, not the entity's **current state**. This is the biological
hippocampus-analog: episodic memory retrieves "what was true then" not "what is
true now."

### 5. Synset-Augmentation Update

The existing `synset_augmentation.py` handles synonym/hypernym resolution for
entity identity. The temporal layer is orthogonal: it works on top of the
already-resolved canonical node.

**Implementation:** No changes to synset_augmentation.py. Add a new `temporal_resolution.py`
module that:
1. Takes a resolved canonical node ID + timestamp from context
2. Queries entity_states for the matching version
3. Returns the state_attributes snapshot at that time

**Fallback:** If no temporal context is available (timestamp unknown), return the
latest state (valid_to IS NULL). If multiple states exist without clear ordering,
return all states with timestamps so the consumer can disambiguate.

### 6. Anti-Pattern Section Update

Add to "Anti-Patterns" in `kg_ontology/SKILL.md`:

```markdown
### Temporal Anti-Patterns

| Anti-Pattern | Symptom | Fix |
|---|---|---|
| Temporal collapse | "old config" and "new config" resolve to same node | Add entity state version tracking |
| State without provenance | entity_states exists but no extracted_from link | Require provenance on every state insertion |
| Over-factoring temporal states | Every minor diff creates a new state | Require semantic difference threshold |
| Current-state confusion | Past events resolve to current state | Enforce temporal context propagation |
```

Add to Evidence:

```markdown
- AI Meets Brain (2512.23343) Section 4.1.3 — hippocampal vs prefrontal entity state tracking
- MemGPT (arXiv:2310.08560) — sliding window memory state management
```

## Implementation Order

1. Add `entity_states` and `state_transitions` SQL schema
2. Add `current_version` column to `canonical_nodes`
3. Implement `temporal_resolution.py` module
4. Update KG insertion pipeline to capture temporal context
5. Update synset selection to preserve temporal context
6. Add temporal anti-patterns to SKILL.md
7. Test with config file version changes, user preference changes, decision reversals

## Evidence

- AI Meets Brain (2512.23343) Section 4.1.3 — biological entity state vs identity distinction
- MemGPT (arXiv:2310.08560) — temporal state management
