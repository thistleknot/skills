# Case Memory Reference

When to read this file: when the agent encounters a task similar to one it has
previously attempted, or when accumulating enough `memory.jsonl` entries that
pattern extraction becomes valuable.

---

## Memory-Informed Proposal Format

When memory retrieval informs a recommendation, present it in this structure:

**Value Proposition** — one sentence: what outcome this achieves for the user.

**Why / What / How / Where**
- *Why*: rationale — why this approach over alternatives, grounded in retrieved case evidence
- *What*: the specific change, action, or decision being proposed
- *How*: concrete steps to execute (reference the source case by `case_id` where applicable)
- *Where*: scope — which files, systems, or contexts this applies to

**Confidence** — `utility_score` of the source case(s) plus a one-line basis:
> `0.82 — cited in 4/5 retrievals; succeeded on 3 similar refactor tasks`

**ROI** — expected return vs. effort:
> `Medium effort (~2h). High return: eliminates recurring circular-dep failures that each cost ~1h to diagnose.`

Apply this format whenever a retrieved case meaningfully shapes a recommendation.
Skip it for trivial suggestions where the basis is self-evident.

---

## File-Backed State Semantics

The `.react_agent/` directory is not just a convenience — it is the agent's
**externalized working memory**. Every piece of state that matters beyond the
current step must be written here. Three properties are required:

- **Externalized** — State is written to files, not held only in the LLM's
  context window. If the context is cleared, the task can resume by reading
  `.react_agent/`. Do not treat in-context reasoning as a substitute for
  writing state to disk.

- **Path-addressable** — Later steps, downstream agents, and the Verifier role
  must be able to reopen any artifact by its exact path. Never reference "the
  output from step 3" — reference `.react_agent/stage_3/result.json`. This
  is what makes handoffs safe.

- **Compaction-stable** — State must survive context truncation, agent restart,
  and delegation to a child agent. If the agent stops mid-task, reading
  `progress.md`, `plan.md`, and `task.md` must be sufficient to resume.
  Design every write with this in mind: write the state you would need to
  reconstruct your current position from scratch.

### Canonical Workspace Layout

```
.react_agent/
├── task.md              # Execution contract (completion_conditions, permission_scope)
├── recon.md             # Reconnaissance findings
├── plan.md              # Subtask plan with output_paths and completion_conditions
├── changes.jsonl        # Append-only action log (path-addressable)
├── memory.jsonl         # Curated outcome/lesson log (distilled from daily files)
├── memory/              # Raw daily session logs (YYYY-MM-DD.md) — unfiltered capture
├── progress.md          # Current status dashboard (overwritten on each update)
├── evidence.md          # Evidence artifact written before task completion
├── corrections.md       # Behavioral correction log — always read at Phase 0
├── autonomy.md          # Standing permission tiers (Free / Ask first / Never) — read at Phase 0
├── personas/            # Role files for spawned subagents (optional)
│   └── <role>.md        # Role + constraints + output format + accumulated lessons
├── stage_<N>/           # Per-subtask working directories (when subtasks produce files)
│   └── verdict.md       # Verifier verdict for that stage
└── cases/               # Archived case files from prior task runs
    └── case_001.json
```

Stage directories keep subtask artifacts isolated and path-addressable.
This supports the Verifier role (reopens `stage_N/` by path, not by memory)
and enables partial resume (a failed subtask's stage directory persists).

---

## Correction Log (corrections.md)

`corrections.md` records **behavioral mistakes** from prior task executions — distinct from `memory.jsonl` (task-execution outcomes) and `cases/` (episodic task patterns). Its purpose is session-start bias correction: the agent reads it before planning to avoid repeating the same behavioral errors.

**Always read at Phase 0.** If `.react_agent/corrections.md` exists, read it before writing `task.md`.

### When to write an entry

Append an entry when the agent:
- Edited the wrong file (path confusion)
- Misunderstood a requirement and built the wrong thing
- Skipped a validation step and introduced a regression
- Repeated a failed approach without changing strategy
- Declared a task complete prematurely

Write the entry immediately after the mistake is corrected, not at session end.

### Entry format

```markdown
### [Short description of mistake]
- **Mistake:** What was done wrong (specific, with file paths or step references)
- **Correction:** What the right approach is
- **Rule:** The general rule to carry forward
- **Self-check:** A question to ask before the risky action — e.g. *"Did the user explicitly authorize this command in this session?"* or *"Have I verified the target path exists?"* One sentence, answerable yes/no.
```

### Lifecycle

Entries are never deleted mid-session. After a successful task run where no entry was triggered, review the file and prune entries that are clearly no longer relevant (e.g., related to a deleted file structure). Keep the file under 50 lines to avoid context overhead. When the entry count reaches 10 or more, run a pattern scan: if the same root cause appears 3+ times under different surface descriptions, add a `## Patterns` section at the bottom of `corrections.md` with a one-line rule per pattern. Patterns carry more generalization weight than individual entries.

---

## Memory Tiers

Three tiers separate raw capture from curated knowledge:

| Tier | File | Purpose | When to write |
|---|---|---|---|
| **Raw** | `memory/YYYY-MM-DD.md` | Unfiltered session log — everything | Every session: events, decisions, dead-ends |
| **Curated** | `memory.jsonl` | Distilled lessons worth keeping | After each subtask: promote significant findings |
| **Episodic** | `cases/case_NNN.json` | Completed task episodes with full context | After task completes — archive the episode |

**Promotion rule:** At session end, review the daily file. Any verified pattern, non-obvious lesson, or reusable approach becomes a one-liner in `memory.jsonl`. Daily files older than 30 days may be pruned; `memory.jsonl` entries persist as distilled knowledge.

---

## Autonomy Tiers (autonomy.md)

`autonomy.md` defines standing permission tiers that persist across all tasks in a project — distinct from `task.md`'s per-task `permission_scope`. Read at Phase 0 before writing `task.md`.

Default tier structure:

```markdown
## Free (no approval needed)
- File reads and writes within project directory
- Running tests and linters
- Writing to `.react_agent/`

## Ask first (surface and wait)
- Creating files outside the project directory
- Installing packages or modifying environment configs
- Any action that reorganizes directory structure

## Never (hard stop regardless of context)
- Modifying infrastructure, cron jobs, or scheduled tasks
- Deleting files without explicit per-session instruction
- Exfiltrating data to external services
```

Add entries as incidents occur: when an action causes harm, move it to a stricter tier and note the incident date and what happened. Write tiers reactively from real incidents — don't fill them prophylactically.

---

## Persona Files (personas/)

A persona file defines a reusable role for a spawned subagent. Unlike inline instructions (one-shot, forgotten), persona files accumulate timestamped lessons from prior runs.

```markdown
# Persona: [Role Name]

## Role
[One paragraph: domain, purpose, position in workflow]

## Constraints
- [Hard limits — what this persona must never change]
- [Output format requirements]

## Output Format
[Exactly what to return — structure, sections]

## Lessons
- (YYYY-MM-DD) [Lesson from a prior run where this persona made a correctable mistake]
```

Pass the persona file to a spawned subagent instead of repeating an inline role definition. Append a timestamped lesson whenever the subagent produces wrong output. The next invocation loads that lesson and avoids the repeat. This is the persona-level equivalent of `corrections.md`.

---

## Fact-Grounded Query Pipeline

This is the primary reasoning mode when memory is used as **proof** rather than
analogy. Cases and knowledge articles are not retrieved for similarity — they are
interrogated for *entailment*. The output is a syllogism: a set of premises the
evidence entails, plus a thesis that runs through them.

```
User query
  │
  ▼
Step 1 — Objective extraction
  LLM extracts the user's intent as an explicit objective function:
  "Given this query, state the single outcome the user needs in one sentence."
  │
  ▼
Step 2 — Utility index search
  Use the objective to search the knowledge article index (utility_score + keyword
  overlap). Retrieve top-N candidate articles.
  │
  ▼
Step 3 — Premise decomposition (KNWLER / SPO triplets, Qwen3-2b via Ollama)
  Break each candidate article into atomic Subject-Predicate-Object triplets.
  Each triplet is a candidate premise.
  │
  ▼
Step 4 — Entailment ranking (MSMarco)
  Score each premise against the objective:
    entailment_score = MSMarco(objective, premise)
  No binary gate. Produce a ranked list of (premise, score) pairs.
  The scores are evidence for the next step, not verdicts.
  │
  ▼
Step 5 — Telos: throughline + premise selection (single LLM call, Qwen3-2b via Ollama)
  Pass to the model in one call:
    - original query
    - extracted objective
    - ranked premises (from Step 4, with entailment scores as context)

  Procedure (abductive — conclusion-first):
    1. Identify what is true across the premises (common ground)
    2. Filter out what is incongruent (does not cohere with the common ground)
    3. Identify the throughline — that's your thesis

  Prompt:
  "Given this objective and the following premises (ranked by entailment score):
   1. Identify what is true across these premises — the common ground.
   2. Filter out any premise that is incongruent with that common ground.
   3. From what remains, identify the throughline — the single thesis these
      premises point toward in service of the objective.
   Return the thesis and ONLY the premises that survive."

  Output:
    - thesis (the throughline / telos)
    - surviving_premises[] (the syllogism — the subset that entails the thesis)

  This is abductive: start from the best explanation (thesis), then retain only
  the premises that hold it up. The entailment scores from Step 4 inform the
  LLM's judgment but don't gate it — a low-scored premise that the LLM
  recognises as critical to the throughline survives; a high-scored premise
  that points elsewhere gets dropped.
  │
  ▼
Step 6 — Source retrieval
  For each surviving premise, retrieve the source paper/article from the
  post-processed markdown files. These are the grounding documents.
  │
  ▼
Step 7 — Graph extraction over retrieved papers (KNWLER + Qwen3-2b)
  Run KNWLER over the retrieved source documents to extract a semantic
  triplet graph (SPO) grounded in the surviving premises.
  Focus the graph on two axes:
    - Philosophy: reasoning chains, mathematical foundations, formal arguments
    - Application: methodology, mechanisms, implementation patterns
  Then derive the throughline across the graph — this is the detailed,
  source-grounded elaboration of the thesis from Step 5.

  Output:
    - graph: SPO triplets extracted from retrieved papers
    - philosophy: reasoning/math premises (the "why")
    - application: methods/mechanisms (the "how")
    - grounded_response: throughline across both axes, answering the objective

  The full chain is:
    user intent → objective → entailed premises (index) → thesis →
    retrieved papers → graph → grounded response

  This output forms the basis of a new knowledge article, or an update
  to an existing one (see "Episodic cases as schema update opportunities").
  │
  ▼
Step 8 — Sufficiency check
  Does the grounded response answer the user's question?
  If yes → compose final response using the Proposal Format above.
  If no  → iterate once: refine the objective, re-run from Step 2.
  Cap at 2 iterations. If still insufficient, surface the gap explicitly.
```

### Why thesis-first (telos)

The combinatorial problem — finding the best subset of premises — is
intractable if approached exhaustively. But abduction sidesteps it: by
identifying the throughline first, the LLM implicitly selects the coherent
subset in one pass. Premises that don't load-bear for the thesis drop
naturally. The MSMarco entailment scores (Step 4) act as soft priors that
inform but don't constrain the LLM's judgment — a low-scored premise that
the LLM recognises as critical survives; a high-scored tangent gets dropped.

### Episodic cases as schema update opportunities

Cases (episodic) are not the terminal memory artifact — they are *evidence* that
should update **knowledge articles** (semantic memory units). Each completed
case is an opportunity to ask:

> "Does this episode deepen, contradict, or add nuance to an existing knowledge
> article? If yes, update that article in-place. If no article covers this, and
> the episode introduces a genuinely new insight, create one."

Knowledge articles are the objects the pipeline above actually reasons over.
Cases are the raw material that keeps them current. This keeps the memory
schema flexible: you are not accumulating a rigid bag of episodes — you are
maintaining a living knowledge base where episodes are the update signal.

The `memory_type` field governs this:
- `episodic` → raw case, candidate for promotion
- `semantic` → knowledge article (distilled cross-case insight, domain constraint)
- `procedural` → reusable step sequence (workflow template)
- `archival` → compressed/clustered; no longer retrieved directly

---

## Case Format

Cases stored in `.react_agent/cases/` represent completed task episodes.
A case captures what was attempted, what worked, and what to do differently.

Each case is an enriched **note** (A-MEM / Zettelkasten): beyond raw event
data, it carries LLM-generated semantic fields (`keywords`, `tags`,
`context_description`) that enable nuanced retrieval and cross-case linking.
The `utility_score` field is updated over time by MemRL-style outcome
weighting — cases that produced successful retrievals gain score; cases
that were retrieved but unhelpful lose it.

```json
{
  "case_id": "case_001",
  "task_summary": "Migrate pytest fixtures from conftest.py to per-module fixtures",
  "task_type": "refactor",
  "domain": "python_testing",

  "keywords": ["pytest", "fixtures", "conftest", "circular dependency", "bottom-up"],
  "tags": ["python", "testing", "refactor", "dependency-graph"],
  "context_description": "Restructuring shared test fixtures across a module hierarchy. Key risk is circular fixture dependencies; mitigation is mapping the dependency graph before moving anything.",

  "linked_cases": ["case_007", "case_012"],

  "approach": "Bottom-up: started with leaf test modules, worked toward shared fixtures",
  "outcome": "success",
  "steps_taken": 12,
  "failures_encountered": [
    {
      "step": 4,
      "error": "ImportError — circular fixture dependency between auth and db modules",
      "resolution": "Extracted shared fixture to a new conftest.py at the common parent directory"
    }
  ],
  "lessons": [
    "Check fixture dependency graph before moving fixtures — circular deps are common",
    "Run tests after each individual fixture move, not after batch moves"
  ],
  "transferable_patterns": [
    "When restructuring shared resources, map the dependency graph first",
    "Bottom-up ordering reduces breakage vs top-down"
  ],

  "utility_score": 0.82,
  "retrieval_count": 5,
  "citation_count": 4,

  "timestamp": "2026-03-28T14:30:00Z",

  "critic_note": "Succeeded because bottom-up ordering avoided circular deps. Next time: map deps before ANY move.",
  "lifecycle_state": "active",
  "memory_type": "episodic"
}
```

### Note Construction (A-MEM)

When writing a new case, populate the semantic fields by prompting the LLM:

> "Given this completed task episode, generate: (1) 5–8 keywords capturing key
> concepts, (2) 3–5 categorical tags, (3) a 1–2 sentence `context_description`
> that summarises the core challenge and mitigation strategy in a way that would
> help a future agent recognise a similar situation."

Then scan existing cases for candidates to link (same `task_type`, overlapping
`keywords`, or shared `failures_encountered` error types). For each candidate,
ask the LLM: "Should these cases be linked — do they share a meaningful pattern
or cautionary relationship?" Link if yes. Also **evolve** existing linked cases:
if the new case deepens, contradicts, or refines a linked case's
`context_description`, update that field in-place.

Also set these fields on write:
- **`memory_type`**: `episodic` for task execution cases; `semantic` for distilled cross-case facts or patterns; `procedural` for reusable step sequences (workflow templates); `archival` when a case has been compressed into a cluster summary.
- **`lifecycle_state`**: always `"active"` on creation; governed by access recency (see Lifecycle Transitions below).
- **`critic_note`**: after task completion, write 1–2 sentences — *why* the chosen approach succeeded or failed, not just *that* it did. Injected into the planner prompt alongside the retrieved case.

---

## Case Retrieval — Four-Phase (MemoRAG + MemRL + MemR³ + HippoRAG)

Standard retrieve-then-answer retrieves semantically similar cases but
introduces noise from cases that turned out to be unhelpful. Use four phases:

### Phase 0 — Global Pre-Scan (MemoRAG) *(skip if query is explicit)*

When the task query is **vague or implicit** — the desired outcome is not
clearly stated, or the task involves open-ended exploration — run a lightweight
pre-scan before retrieval:

1. Generate 2–3 **answer clues**: short phrases or keywords that would appear
   in a helpful case if one exists. Prompt: *"Given this task, what terms or
   patterns would a useful past case likely mention?"*
2. Use the clues to **augment the retrieval query** for Phase 1 — prepend them
   to the task description.
3. Skip Phase 0 when the task has an explicit, well-formed query (clue
   generation adds latency without benefit).

### Phase 1 — Broad Semantic Retrieval

Compare the incoming task against all cases on:

1. **Task type** — same category (refactor, migration, build, fix)
2. **Domain** — same technology or domain area
3. **Keyword / tag overlap** — match incoming task description against `keywords` and `tags`
4. **Structural similarity** — similar dependency structure or scope

Retrieve up to 5 candidate cases.

### Phase 1b — Multi-Hop Graph Walk (HippoRAG) *(when candidates have linked_cases)*

If any of the top candidates have non-empty `linked_cases`, extend retrieval
via **Personalized PageRank (PPR)** over the link network:

1. Treat the top-2 Phase 1 hits as **seed nodes**.
2. Follow `linked_cases` edges outward (up to 2 hops).
3. Score reachable cases by PPR weight × `utility_score`.
4. Add any high-scoring reachable case not already in Phase 1 results to the
   candidate set (cap total candidates at 8).

This surfaces multi-hop relevant cases that share no direct embedding
similarity with the query but are connected through an intermediate pivot
case — analogous to hippocampal associative recall.

### Phase 2 — Utility Filtering (MemRL)

Re-rank candidates by `utility_score`. Prefer cases where:
- `outcome == "success"` — successful strategies get priority
- `utility_score` is high (past retrievals of this case led to citations)
- `retrieval_count > 0 AND citation_count / retrieval_count > 0.5`

Discard candidates with `utility_score < 0.3` unless no higher-scoring case
matches the task type. This filters cases that were retrieved often but
consistently failed to improve planning.

### Phase 3 — Evidence-Gap Check (MemR³)

After reading the top-ranked case(s), explicitly track two state variables:

- **E (evidence)** — what the retrieved cases have reliably established
  (known pitfalls, effective approach patterns, domain constraints)
- **G (gap)** — what information is still missing before planning can begin

If `G ≠ ∅`: issue a refined retrieval query targeting the specific gap, then
re-check E and G. Stop retrieving when G is empty or max 3 retrieval cycles
have elapsed.

Surface E and G to the PLAN phase — they become direct inputs to plan
assumptions and risk sections.

---

## Case Retention

Write a case to `.react_agent/cases/` when:
- A task completes (success or failure after exhausting approaches)
- The task involved 3+ non-trivial steps
- A novel failure mode was encountered and resolved

**Write only on task completion** (Memento): capture only the final state,
final plan, and binary outcome — not intermediate steps. Writing partial
trajectories inflates the case store with noise and degrades retrieval.
The completed case represents the *full episode*; `steps_taken` and
`failures_encountered` carry the trajectory summary.

### Semantic Density Gate (SimpleMem)

Before writing, apply a density gate: ask the LLM whether the episode adds
genuinely new information relative to existing cases (new failure modes, new
domain, new approach pattern). If the answer is "no meaningful new content",
do not write a new case — instead update `context_description` and `lessons`
of the most similar existing case in-place.

This keeps the case store compact and prevents fragmentation into many
near-duplicate entries.

### Critic Note (RAG-Modulo)

When writing, populate `critic_note` with a structured self-critique:

> *"The approach succeeded/failed because [specific mechanism]. Key factor:
> [what made the difference]. Next time: [what to do differently, or what
> to keep doing]."*

This is stored alongside the case and **injected into the planner prompt**
during retrieval: the next agent reading this case sees not just *what worked*
but *why* — accelerating diagnosis and avoiding silent repetition of failures.

### Utility Score Initialisation

New cases start at `utility_score: 0.5`. After each retrieval:
- If the case was cited (it changed planning decisions): apply EMA update
  `score = 0.3 * 1.0 + 0.7 * score`
- If the case was retrieved but not cited: apply EMA update
  `score = 0.3 * 0.0 + 0.7 * score`

This is the MemRL non-parametric RL loop: no fine-tuning, just utility
accumulation on the case store.

**Parametric upgrade (Memento)**: when the case bank exceeds 20 cases, the
EMA rule above approximates a soft Q-learning update. If a lightweight neural
Q-function is available, replace the EMA with a TD update:
`Q(s,c) ← Q(s,c) + η(r − Q(s,c))`, where `s` is the incoming task state,
`c` is the retrieved case, and `r ∈ {0,1}` is the binary outcome. The EMA
approximates this without a network; use whichever matches available
infrastructure.

### Lifecycle State Transitions (MemOS)

Govern `lifecycle_state` based on access recency:

| From | To | Trigger | Action |
|---|---|---|---|
| `active` | `dormant` | Not retrieved in last **20 tasks** | Keep in index; apply ×0.6 penalty to effective `utility_score` in Phase 2 |
| `dormant` | `archived` | Not retrieved in last **100 tasks** | Trigger `CompressExperience`; merge into cluster summary; set `memory_type: archival` |
| `archived` | `active` | Explicitly retrieved (Phase 1 or 1b) | Restore to active index; reset recency counter |

---

## Indexed Experience Memory (Memex(RL))

For **within-task** context management on long-horizon tasks, maintain an
`IndexedSummary` alongside the full episode archive.

### Structure

```
.react_agent/
  index_summary.md      ← compact working context (CurrentStatus + IndexMap)
  archive/
    step_005_output.txt ← full tool output archived under stable key
    step_009_diff.patch ← full diff archived under stable key
    ...
```

### `index_summary.md` format

```markdown
# CurrentStatus
[1–3 sentences: what has been accomplished, what is immediately next]

# IndexMap
| Key              | Description                                    |
|------------------|------------------------------------------------|
| step_005_output  | Full grep results for circular import scan     |
| step_009_diff    | Complete patch applied to auth/conftest.py     |
```

### Operations

**CompressExperience** (triggered when context grows large):
1. Archive the full tool output or diff under a stable key in `archive/`
2. Add a row to IndexMap with a precise description
3. Replace the full content in the working context with `[see step_NNN_output]`
4. Update `CurrentStatus` to reflect current state

**ReadExperience(key)** (before re-running an expensive tool):
1. Check IndexMap — if this information was already captured, dereference it
2. Read the archived artifact directly rather than re-executing the tool
3. This is exact retrieval, not a lossy re-summary

**Rule**: Never re-run a tool whose output is already in the archive. Check
IndexMap first. This prevents redundant computation and context inflation.

---

## Cross-Task Learning (A-MEM Evolution)

After accumulating 5+ cases, scan for patterns:

- **Recurring failure modes** — Same error type in 3+ cases → add to
  "known pitfalls" in `progress.md`; check proactively in VALIDATE.
- **Effective approaches** — Approach pattern succeeding across multiple task
  types → elevate to a default strategy in planning.
- **Domain-specific constraints** — Domain consistently requiring certain
  preconditions → add to reconnaissance checklist.

### Memory Evolution

When a new case shares significant overlap with an existing case, do not just
link them — evolve the existing case. Ask: "Does this new episode deepen,
refine, or contradict the existing `context_description` or `lessons`?" If
yes, update in-place. This mirrors A-MEM's insight that new experiences should
propagate backwards: the memory network continuously refines its understanding
rather than just accumulating raw entries.

When a pattern emerges across 3+ linked cases, promote it to a named
**transferable pattern** card at the top of `performance.md`. Named patterns
are directly injectable into PLAN steps without re-deriving them each time.

---

## Scale: Hierarchical Index (RAPTOR)

When the case store exceeds **50 cases**, flat Phase 1 embedding search
degrades — the top-5 hits become noisy and miss thematically related cases.
Build a **RAPTOR tree** to maintain retrieval quality at scale.

### Tree Construction *(offline; rebuild after every 20 new cases)*

- **L0** — raw cases (all entries in `.react_agent/cases/`)
- **L1** — cluster raw cases by embedding similarity (k=5–8 clusters);
  summarise each cluster into a **cluster summary case** (`memory_type: semantic`)
- **L2** — cluster the L1 summaries (k=3–4);
  summarise each into an **abstract summary** (`memory_type: archival`)

### Retrieval at Inference

In Phase 1, query **all tree levels** in parallel:
- L2 hits surface broad thematic relevance (right domain, right task class)
- L1 hits surface cluster-level patterns (shared failure modes, approach families)
- L0 hits surface specific case details

Merge all hits into the Phase 1 candidate set (cap at 8), then continue
through Phase 1b → Phase 2 → Phase 3 as normal.

When a raw case is promoted into a cluster summary, set its `lifecycle_state`
to `"archived"` — it is no longer retrieved directly but lives in the L1
and L2 aggregates.

### When to Skip

Skip RAPTOR if the case store has ≤ 50 cases — flat retrieval is sufficient
and faster for small stores.

---

# Self-Improvement Patterns

The following meta-capabilities emerge from accumulated experience and can be
adopted by the agent to improve its own ReAct loop execution.

## Performance Tracking

After 3+ completed tasks, maintain a running summary in
`.react_agent/performance.md`:

```markdown
# Performance History

## Efficiency
- Average steps per subtask: [N]
- First-attempt success rate: [N%]
- Average retries per failure: [N]

## Common Failure Modes
| Failure Type | Frequency | Typical Resolution |
|---|---|---|
| Import errors | 5 | Check dependency order before editing |
| Test regression | 3 | Run narrower test set after each change |

## Approach Effectiveness
| Approach Pattern | Times Used | Success Rate |
|---|---|---|
| Bottom-up refactor | 4 | 100% |
| Batch edit then test | 2 | 50% |

## Named Transferable Patterns
| Pattern | Source Cases | Applies To |
|---|---|---|
| Map dependency graph first | case_001, case_007 | Any restructuring task |

## Improvement Targets
- [Identified area where current approach is weakest]
```

## Meta-Improvement

When `performance.md` reveals a recurring weakness:

1. Identify the failure pattern
2. Trace it to a specific phase of the ReAct loop (usually VALIDATE or PLAN)
3. Propose a concrete modification to that phase for this project
4. Write the modification as an addendum to `plan.md`
5. Apply it going forward and track whether it improves outcomes

This is *metacognitive self-modification* — the agent improving its own
improvement process. The modification applies to the current project only.
It does not alter the SKILL.md itself (that requires the skill-creator skill
and user involvement).

## Plan Revision

Plans written in Phase 2 are hypotheses, not commitments. Revise the plan when:

- A subtask reveals that the original decomposition was wrong
- A dependency was missed during reconnaissance
- The estimated scope of a subtask was significantly off
- A better approach becomes apparent from experience during execution

When revising:
1. Update `plan.md` with the new plan
2. Mark the revision in `progress.md`
3. Note what triggered the revision in `memory.jsonl`
4. Do NOT silently change direction — make plan revisions explicit

---

## Source Papers

The retrieval and memory patterns in this file are grounded in:

- **MemRL** (arXiv 2601.03192) — Two-phase retrieval; RL utility scoring on
  episodic memory; non-parametric self-evolution via outcome feedback
- **Memex(RL)** (arXiv 2603.04257) — Indexed Experience Memory;
  CompressExperience / ReadExperience; avoid lossy re-summarisation
- **MemR³** (Du et al., MBZUAI) — Closed-loop retrieval; evidence-gap tracker;
  retrieve / reflect / answer routing with early stopping
- **A-MEM** (Xu et al., arXiv 2502.12110) — Zettelkasten note construction;
  link generation; memory evolution on new experience arrival
- **SimpleMem** (Liu et al.) — Semantic density gating; multi-view indexing;
  online semantic synthesis to prevent fragmentation
