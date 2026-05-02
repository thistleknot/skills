# Enhancement Patch: skill-wiki — Procedural DAG Extraction from Continuity Logs

## Source

NS-Mem (2603.15280) SK-Gen pipeline: automatic procedure extraction from experience traces.

## Problem

`skill-wiki` currently requires **manual skill promotion**: a human identifies that a
procedure is valuable and explicitly authors/promotes it. This misses a large category of
procedures that emerge organically from repeated task execution across sessions — they
appear in continuity logs, react-agent runs, and project progress reports, but nobody
manually promotes them to formal skills.

## Proposed Change

Add a **skill discovery and extraction layer** to `skill-wiki` that:

1. Monitors continuity logs and task artifacts for recurring procedural patterns
2. Applies SK-Gen-lite pattern mining (simplified from the full NS-Mem pipeline)
3. Proposes new skills or enhancements to existing skills automatically
4. Routes proposed skills through the existing staged to active promotion flow

### New Conceptual Layer: Skill Discovery Pipeline

```
continuity-log entries + react-agent task artifacts
        |
        v
 +-----------------+
 |  Pattern        |
 |  Detection      |
 |  (SK-Gen-lite)  |
 +--------+--------+
          | recurring patterns
          v
 +--------+--------+
 |  LLM Verify     |
 |  (skill quality)|
 +--------+--------+
          | quality score > threshold?
          v
 +--------+--------+
 |  Skill Draft    |
 |  Generation     |
 +--------+--------+
          | review or auto-promote
          v
 +--------+--------+
 | staged -> active|
 | (existing)      |
 +-----------------+
```

### SK-Gen-Lite for Skill Discovery

The full NS-Mem pipeline uses PrefixSpan on session action sequences. For skill
discovery, adapt this to work on continuity log entries and task artifacts with
simpler pattern matching:

**Pattern extraction heuristics:**
1. **Sequence co-occurrence:** Two or more task steps that appear together in > N continuity log entries
2. **Tool usage clustering:** Same set of tools (bash, read, edit, write) used in similar order across multiple sessions
3. **Decision pattern repetition:** Same architecture/tool/library choice repeated across different projects
4. **Failure pattern repetition:** Same class of errors or blockers appearing across sessions (indicates skill gap, propose new skill)

**Quality score thresholds (matching SK-Gen from NS-Mem):**
- `score < 0.6`: Ignore, too noisy
- `0.6 <= score < 0.8`: Propose as enhancement to existing skill
- `0.8 <= score < 1.0`: Propose as new skill (automated draft)
- `score >= 1.0`: Propose with "promote automatically" flag (no review needed)

### Updated Skill Anatomy

Add to "Skill Anatomy" section in `skill-wiki/SKILL.md`. New entry in the skill lifecycle:

```
  Discovery    — scan continuity logs -> detect patterns -> score quality
  Authoring     — human writes SKILL.md from scratch (existing)
  Promotion     — staged to active (existing)
  Enhancement   — detect skill gaps -> propose updates (NEW: from pattern discovery)
```

### Integration with Existing Lifecycle Stages

| Current Stage | Enhanced With |
|---|---|
| **Authoring** | Manual only (unchanged) |
| **Discovery** | NEW: Pattern detection from continuity logs to auto-drafts |
| **Promotion** | Manual review to staged (unchanged); score >= 1.0 to auto-promote |
| **Enhancement** | NEW: Skill gaps from failure patterns to propose SKILL.md edits |
| **Supersession** | Manual or auto (when new pattern supersede score > 0.9) |

### Discovery Trigger and Rate

**Triggers:**
- On completion of a long task (> 30 turns or > 3 hours)
- Daily batch scan (if skill-wiki runs as a daemon)
- After a new skill is promoted (re-scan to check for overlaps)

**Rate limit:** Max 3 skill proposals per scan to prevent proposal spam. Queue extras for next scan.

### New Data Contract

Add to `skill-wiki/SKILL.md` — discovered skill proposal format:

```python
class SkillProposal(BaseModel):
    source_type: Literal['continuity_log', 'task_artifact', 'failure_pattern']
    source_path: str
    discovered_at: datetime
    pattern_description: str
    skill_candidate: str                # auto-generated SKILL.md content
    quality_score: float
    should_enhance_existing: bool       # True -> merge into existing skill
    enhance_target_skill: str | None    # skill name to enhance
    requires_review: bool               # False only if score >= 1.0
    evidence_entries: list[str]         # continuity log IDs that support this proposal
```

### Updated "When to Use" Section

Add to the top of `skill-wiki/SKILL.md`:

```markdown
Use `skill-wiki` when:
  ...existing items...
  - Detecting procedural patterns from continuity logs for skill discovery (SK-Gen-lite)
  - Proposing skill enhancements based on recurring task patterns
```

### Updated Anti-Patterns

Add to "Anti-Patterns" section:

```markdown
- Auto-proposing skills based on patterns with score < 0.6 (too noisy, wastes review effort)
- Letting discovery overwhelm manual authoring (SK-Gen-lite is assistive, not replacement)
- Proposing overlapping skills (check existing skills before promoting new ones)
- Not linking discoveries to source continuity logs (always preserve traceability)
```

### Updated Evidence

Add to "Evidence" section:

```markdown
- NS-Mem (2603.15280) — SK-Gen pipeline for procedure extraction (adapted)
- PrefixSpan (Pei et al., 2001) — sequential pattern mining (adapted for shorter sequences)
```

## Implementation Order

1. Define SkillProposal model
2. Implement pattern detection heuristics (sequence co-occurrence, tool clustering, decision repetition)
3. Implement quality scoring (LLM-based assessment)
4. Wire into existing staged to active promotion flow
5. Add discovery trigger (task completion hook, scheduled scan)
6. Update SKILL.md sections (anatomy, when-to-use, anti-patterns, evidence)
7. Test: run for 5+ tasks, verify proposals are actionable and not noisy

## Evidence

- NS-Mem (2603.15280) — SK-Gen pipeline, quality scoring, DAG construction
- PrefixSpan (Pei et al., 2001) — sequential pattern mining
