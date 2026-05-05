---
name: skill-sync
description: >
  LLM-assisted merge protocol for diverged skill copies across local and remote
  mirrors. Use when syncing the skills master repo with mirrors that have both
  been independently edited since the last commit. Handles fast-forward and
  conflict cases; invokes LLM merge for true conflicts. Pairs with sync_skills.ps1.
status: active
last_validated: 2026-05-04
supersedes: []
validation_method: session
---

# Skill Sync — LLM-Assisted Mirror Merge Protocol

## Scope

This skill governs how diverged skill files are reconciled across mirrors of the
skills repo. It is the **cognitive protocol**; `sync_skills.ps1` is the mechanical
executor that calls back to the agent for the LLM merge step.

**Ownership boundary:**

| Concern | Owner |
|---|---|
| Skill lifecycle (intake, promotion, supersession) | `skill-wiki` |
| **Operational sync/merge across mirrors** | **`skill-sync` (this skill)** |
| Branch strategy and push gates | `git-workflow` |
| Multi-agent peer coordination | `multi-agent-coordination` |

---

## Trigger Conditions

Invoke this skill when:
- Running `sync_skills.ps1` and it reports files where both master and a mirror
  have diverged from the last commit
- Manually reconciling skill edits made on different machines or by different agents
- A remote mirror (e.g., `192.168.3.17:/root/.copilot/skills`) has been modified
  by another agent instance and you need to fold those changes back to master

---

## Case Classification

For any tracked file, compare three versions:

- `base` — last committed state: `git show HEAD:<rel-path>` from master repo
- `master` — current content at master working copy path
- `mirror` — current content at the mirror path being reconciled

| master == base | mirror == base | Case | Action |
|---|---|---|---|
| ✓ | ✓ | **No-op** | Skip; nothing to merge |
| ✓ | ✗ | **Fast-forward A→B** | Mirror has new content; copy mirror → master |
| ✗ | ✓ | **Fast-forward B→A** | Master is ahead; mirror will receive it on next sync push |
| ✗ | ✗ | **Conflict** | Both sides diverged; LLM merge required |

### Detecting which case applies

```powershell
$base          = git show "HEAD:$relPath" 2>$null
$masterContent = Get-Content $masterFile -Raw -ErrorAction SilentlyContinue
$mirrorContent = Get-Content $mirrorFile -Raw -ErrorAction SilentlyContinue

$masterChanged = ($masterContent -ne $base)
$mirrorChanged = ($mirrorContent -ne $base)

if     (-not $masterChanged -and -not $mirrorChanged) { "no-op" }
elseif (-not $masterChanged -and      $mirrorChanged) { "fast-forward: take mirror" }
elseif (     $masterChanged -and -not $mirrorChanged) { "fast-forward: master already ahead" }
else                                                   { "conflict: llm merge required" }
```

---

## LLM Merge Protocol

### When to invoke

Only for the **Conflict** case: both `master` and `mirror` differ from `base`.

### Input preparation

```
base   = git show HEAD:<rel-path>          (common ancestor)
diff_A = git diff --no-index base master   (what master changed)
diff_B = git diff --no-index base mirror   (what mirror changed)
```

### Prompt contract

**System framing:**
> You are a precise text merge operator. You will be given a base document and
> two independent sets of changes (diffs). Your job is to produce a single merged
> document that incorporates all changes from both diffs.

**User message template:**
```
## Base document

<base file content>

## Changes from Side A (master)

<unified diff, diff_A>

## Changes from Side B (mirror)

<unified diff, diff_B>

## Instructions

Produce the complete merged file that incorporates all changes from both diffs.
Rules:
1. If the two diffs touch different sections, interleave them cleanly.
2. If both diffs touch the same section:
   - Prefer the more complete or additive version.
   - Do not silently drop content from either side.
   - If they directly contradict (e.g., different values for the same field),
     keep the Side A version but append a <!-- MERGE-CONFLICT --> comment
     immediately after showing both alternatives.
3. Preserve YAML front matter. If both sides changed `last_validated`, take the
   more recent date.
4. Return only the complete merged file — no preamble, no explanation.
```

### Output handling

- Write the LLM output to a temp file, verify it is non-empty and UTF-8 valid
- Diff the merged result against base to confirm changes were applied
- If the result equals base (LLM stripped all content), **abort and flag as
  unresolved** — do not write to master
- If the result contains `<!-- MERGE-CONFLICT -->`, flag the file for human review
  before committing; do not auto-commit
- Otherwise, write merged content to master file

### Failure modes

| Symptom | Cause | Recovery |
|---|---|---|
| Merged output equals base | LLM ignored both diffs | Retry once with temperature=0; if still empty, fall back to manual |
| Output contains `<!-- MERGE-CONFLICT -->` | Genuine semantic conflict | Flag for human review; do not auto-commit |
| Output is malformed YAML front matter | LLM dropped or garbled frontmatter | Restore frontmatter from base; re-check body |
| LLM call fails or times out | API error | Fall back to interactive prompt: show diff_A + diff_B, ask user to choose |

---

## Integration with `sync_skills.ps1`

The script's Step 4 (Reconciliation) calls back to the agent for LLM merge:

```
Interactive mode: [y=copy mirror / m=llm-merge / n=skip / d=diff each]
Autopilot mode (-Yes):
  - fast-forward cases: copy automatically
  - conflict cases: invoke LLM merge, write result, flag MERGE-CONFLICT files
```

After merge, the script resumes with its existing commit-offer step (Step 4 end).

---

## Applicability Envelope

**Works well when:**
- Changes on each side are additive (new sections, extended content)
- The two diffs touch largely non-overlapping areas of the file
- Files are well-structured markdown with clear section headers

**Fails or degrades when:**
- Both sides made contradictory changes to the same field (e.g., conflicting
  protocol changes — requires human judgment)
- The base is very short (< 5 lines) and both diffs are large restructurings
- The file is binary or non-text (not applicable to skill `.md` files)

---

## Scope of Tracked Files

Same as `sync_skills.ps1`:
- `README.md`, `copilot-instructions.md`, `MEMORY_SKILLS_PLAN.md`, `AGENTS.md`
  at repo root
- All `*.md` files inside any skill subfolder (one level deep)

Remote mirror sync (to/from `192.168.3.17`) uses WinSCP or rsync; the LLM merge
step applies before the outbound push, not after.