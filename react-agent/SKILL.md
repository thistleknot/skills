---
name: react_agent
description: >
  Use this skill whenever the user gives an instruction that requires multi-step
  autonomous task execution — refactoring, migrations, building features, pipeline
  construction, data processing, infrastructure setup, or any task where the agent
  must plan, act, observe results, and iterate. Trigger on phrases like "automate",
  "build", "migrate", "refactor", "set up", "implement", "fix all", "convert",
  "process", or any instruction implying a sequence of changes with validation.
  Also trigger when the user explicitly asks for agentic, autonomous, or ReAct-style
  execution. Do NOT trigger for single-shot questions, explanations, or trivial edits.
status: active
last_validated: 2026-04-28
---

# ReAct Agent Skill

Bootstraps a structured Reason-Act-Observe loop for autonomous multi-step task
execution. Incorporates episodic memory, action validation, self-correction, and
progress tracking to reliably complete complex automation tasks.

## LLM Configuration

This skill attempts to route via **copilot-proxy** at `http://127.0.0.1:8069/v1`.
See the `copilot-proxy` instructions file for full setup. Run `copilot-proxy` in
a terminal before invoking this skill.

| Task type | Model | When |
|---|---|---|
| Reasoning, planning, analysis | `gpt-4o` | Reframe, Recon, Plan phases; REASON and REFLECT steps |
| Code generation, file edits | `gpt-4.1` | ACT step; any code write, edit, patch, or refactor |

```python
# copilot-proxy client config
from openai import OpenAI
reasoning_client = OpenAI(api_key="dummy-key", base_url="http://127.0.0.1:8069/v1")
# Reasoning tasks: model="gpt-4o"
# Coding tasks:    model="gpt-4.1"
```

If copilot-proxy is unavailable, fall back to whatever model is active in the
current session — the skill logic is model-agnostic.

## Default Agent Settings

This skill inherits its behavioral hyperparameters from
`agentic-harness/default_agent_settings.json`. Load them at run init:

```python
import json
from pathlib import Path

HARNESS_DIR = Path(__file__).parents[1] / "agentic-harness"
DEFAULT_SETTINGS = json.loads((HARNESS_DIR / "default_agent_settings.json").read_text())

def get_agent_settings(**overrides) -> dict:
    return {**DEFAULT_SETTINGS, **overrides}

# Example: react-agent uses defaults as-is
settings = get_agent_settings()
# retrieval_depth=5, reranking="llm_judge", context_budget=512,
# planning_depth=1, verification_passes=0, temperature=0.0,
# top_p=0.9, frequency_penalty=0.7, abstention_policy="exclude_if_low"
```

Override only what diverges from the contract.
See `agentic-harness/SKILL.md § Default Agent Settings` for the full parameter reference.

### Choosing `retrieval_depth`

Before fixing `retrieval_depth`, apply this conditional model:

```
IF task = single-file change or bounded lookup            → retrieval_depth = 3
IF task = multi-file refactor or moderate investigation   → retrieval_depth = 5 (default)
IF task = architectural change / unknown codebase         → retrieval_depth = 8+
ELSE (scope ambiguous from the task statement)            → ask during the Ambiguity Check interview
```

Contingencies:
- If Phase 1 Reconnaissance uncovers unexpected scope, raise `retrieval_depth` before Phase 2 planning begins.
- If iterations exhaust and the acceptance criterion is unmet, surface what is blocked rather than declaring done.

## Core Thesis

An LLM agent given a complex task fails in predictable ways: illegal actions
(malformed tool calls, invalid file edits), lost context (forgetting what was
tried), repeated mistakes (no memory of failures), and premature termination
(declaring done without verification). This skill addresses all four by
imposing structure on the agent's reasoning loop without constraining its
problem-solving flexibility.

The architecture draws from five research patterns:
- **Harness wrapping** — validate actions before execution, reject illegal ones
- **Episodic case memory** — store (task, approach, outcome) for retrieval
- **Persistent progress tracking** — log what worked, what failed, what to try next
- **Progressive disclosure** — load context incrementally, not all at once
- **Planner-executor separation** — reason about *what* at plan level, handle *how* at execution level

## Relation to Agentic Harness

Keep `react-agent` and `agentic-harness` separate.

- `react-agent` is the **outer execution operating system**:
  - reframe
  - reconnaissance
  - plan
  - execute
  - verify
  - preserve memory across turns
- `agentic-harness` is the **specialist sub-skill** for:
  - self-repairing code-generation pipelines
  - dark software factories
  - legality gates
  - reconcile / critic loops
  - harness synthesis from environment failures

When the system being changed is itself an agentic pipeline, use this split:

```text
react-agent      -> manages task contract, plan, progress, evidence, and handoffs
agentic-harness  -> manages coherence loop, legality loop, critic loop, and harness repair
```

Do not merge them by default. Merge only if the generic execution loop and the
harness-specific repair loop become operationally inseparable.

## Studio Model for Long-Running Work

Two analogies are load-bearing for this skill.

### RPG character sheet

The `.react_agent/` workspace is the **character sheet between sessions**.

- `task.md` = quest and win condition
- `recon.md` = what the party knows
- `plan.md` = intended route
- `progress.md` = current HP, inventory, and open status effects
- `evidence.md` = proof of what actually happened

If a future session cannot reopen those files and resume cleanly, the sheet is incomplete.

### Studio continuity packet

Treat long tasks like a production pipeline:

- the task is the film
- subtasks are scenes
- `plan.md` is the shooting schedule
- `progress.md` is the production board
- sparse retrieved context is the actor packet
- `evidence.md` is the continuity report

Each subtask should receive only the context needed to play its role well.
Do not dump the whole script into every actor packet.

## Kanban and Branch Discipline

When a task spans multiple features, fixes, or workstreams, promote the plan into
a lightweight kanban model.

Recommended states:

- `backlog`
- `ready`
- `in_progress`
- `review`
- `blocked`
- `done`

Minimum story fields:

- story id
- objective
- acceptance condition
- current status
- owner / agent
- branch name
- evidence path

Branch policy:

- one story or tightly-coupled subtask per branch
- branch names should be stable and descriptive:
  - `story/<id>-<slug>`
  - `feature/<slug>`
  - `bugfix/<slug>`
  - `chore/<slug>`
- update story status when branch state changes
- do not mark a story `done` until its evidence path exists and its acceptance condition is satisfied

If no git repository exists and the user has authorized repository setup, initialize
the repo before multi-story execution so branch and kanban state stay coherent.

## When You Receive a Task

Before writing any code or making any change, execute this sequence:

### Phase 0: Reframe

**Before anything else** — if `.react_agent/corrections.md` exists, read it in full. It records behavioral mistakes from prior sessions (wrong file edited, requirement misunderstood, validation skipped). Apply its rules now; do not wait until you repeat an error. If `.react_agent/autonomy.md` exists, read it immediately after — it defines standing permission tiers (Free / Ask first / Never) that apply to every task in this project regardless of per-task scope.

**Ambiguity check** — before self-deriving requirements, assess whether the task is genuinely open-ended: multiple valid interpretations, unclear scope boundary, or phrasing like "something like" or "maybe". If so, interview the user with 3–5 targeted questions. Capture answers in `.react_agent/interview.md` and derive `task.md` from that — not from inference alone. Skip the interview only when the task can be restated unambiguously in a single sentence.

1. Restate the user's instruction as abstract requirements (what must be true when done)
2. Identify the scope boundary — what is in scope, what is explicitly out
3. List preconditions — what must exist/be true before you can start
4. State the acceptance criteria — how will you (and the user) know it's done
5. Identify risks — what could go wrong, what's irreversible

Write this to `.react_agent/task.md` as an **execution contract** — include all
of the following fields explicitly:

```markdown
## Execution Contract
- required_outputs: [list of artifacts or state changes that must exist when done]
- budget: [estimated steps or time envelope]
- permission_scope: [what files, directories, services you are allowed to modify]
- completion_conditions: [observable checks that must all pass before declaring done]
- designated_output_paths: [exact paths where deliverable artifacts must be written]
```

This file is your north star. Return to it when you drift. The `completion_conditions`
field is the source of truth for the Completion Protocol and Verifier role.

### Phase 0.5: Six Hats + Causal Tree

Before reconnaissance, run one pass of structured thinking over the task. This
surfaces blind spots and contingencies **before** the first action, not after a
failed attempt.

**Six Hats sweep** (one sentence each — skip hats that don't apply):

| Hat | Lens | Ask |
|---|---|---|
| ⬜ White | Facts & data | What do I know for certain? What am I missing? |
| 🔴 Red | Intuition & risk feel | What feels wrong or risky here? |
| ⬛ Black | Caution & failure modes | What could break this? What's the irreversible action? |
| 🟡 Yellow | Benefits & best case | What does success look like concretely? |
| 🟢 Green | Alternatives | Is there a simpler or different approach? |
| 🔵 Blue | Process & meta | Am I solving the right problem? What order should this happen in? |

**Temporal causal tree** — model the task as an if/then/else before acting:

```
START
 ├─ IF precondition A holds → path P1
 │    ├─ IF sub-condition B → action X
 │    └─ ELSE → action Y; check again
 ├─ IF precondition A missing → action Z (unblock A first)
 └─ ELSE (ambiguous) → ask before proceeding
```

Identify at minimum:
- The earliest point of irreversibility
- The branch whose failure cascades furthest
- Any step where the next action depends on information you don't yet have

Add a `contingencies:` field to the Execution Contract in `task.md`:
```markdown
- contingencies: [branch → fallback for each major if/then/else node]
```

### Phase 1: Reconnaissance

Survey before you act. Do not propose solutions yet.

1. Read the relevant parts of the codebase/environment (directory structure, key files, configs)
2. Identify the entities involved (files, modules, services, data flows)
3. Map dependencies — what depends on what, what order must changes happen in
4. Check for existing tests, CI configs, linting rules that constrain your changes
5. Note anything surprising or contradictory

Write findings to `.react_agent/recon.md`.

### Phase 2: Plan

Decompose the task into ordered subtasks. For each subtask:

```
## Subtask N: [short name]
- depends_on: [list of prior subtask IDs, or "none"]
- inputs: [what this subtask reads/needs]
- outputs: [what this subtask produces/changes]
- output_paths: [exact .react_agent/ or project paths where outputs are written]
- completion_condition: [single observable check that unambiguously means done]
- validation: [how to confirm this subtask succeeded — command or file check]
- rollback: [how to undo if this subtask fails]
- risk: [low/medium/high] — [why]
```

The `completion_condition` must be concrete and path-addressable — not "looks good" or
"tests pass" without specifying which tests. It is the input to the Verifier role.

Write plan to `.react_agent/plan.md`.

Order subtasks by dependency. Independent subtasks can be done in any order.
Dependent subtasks must be done in series. Predecessors first — get prior layers
working before moving to later ones.

**Parallel dispatch** — when two or more subtasks are independent (no shared file writes, no shared state), mark them `spawn: parallel` in the plan and execute them as separate subagents. Each parallel subagent runs its own context window and reports only a summary back to the main session. This keeps the main context lean and reduces wall-clock time. Do NOT parallelize subtasks that write to the same files or depend on each other's outputs.

**Persona dispatch** — when spawning any subagent (parallel or serial), prefer loading a **persona file** from `.react_agent/personas/` rather than passing inline role instructions. A persona file carries role definition, constraints, output format, and accumulated timestamped lessons from prior runs. Inline instructions are one-shot; personas improve from experience. See `MEMORY.md` for the persona file format.

### Recursive Decomposition

If a subtask is itself too complex (ambiguous scope, multiple unknowns, or
estimated 5+ steps), do not force it into a single node. Recurse:

1. Mark the subtask as a **sub-plan** in `plan.md`
2. Run Phases 0–2 (Reframe, Recon, Plan) scoped to just that subtask
3. Write the sub-plan as an indented block under the parent subtask
4. Execute the sub-plan as its own nested ReAct loop
5. Collapse it back to a single status entry in `progress.md` when done

Expand when complexity demands; collapse when the problem resolves. A subtask
that spawns a sub-plan counts as one node in the parent plan's dependency graph.

Present the plan to the user. Wait for confirmation before proceeding unless the
user has indicated they want fully autonomous execution.

## The ReAct Loop

For each subtask, execute the following loop:

```
┌─────────────────────────────────────────┐
│  REASON  │  Why this action? What do I  │
│          │  expect to happen?           │
├──────────┼──────────────────────────────┤
│  VALIDATE│  Is this action legal? Does  │
│          │  it match the plan? Will it  │
│          │  break anything?             │
├──────────┼──────────────────────────────┤
│  ACT     │  Execute the change.         │
├──────────┼──────────────────────────────┤
│  OBSERVE │  What actually happened?     │
│          │  Read output, check files,   │
│          │  run tests.                  │
├──────────┼──────────────────────────────┤
│  REFLECT │  Did it work? If not, why?   │
│          │  Update memory. Decide next. │
└─────────────────────────────────────────┘
```

### REASON

Before each action, run a **Society of Thought** pass — explicitly instantiate
three internal perspectives and let them briefly conflict before committing:

| Perspective | Question |
|---|---|
| **Proposer** | What should be done and why? What is the predicted outcome? |
| **Skeptic** | What could go wrong? What am I missing or assuming? |
| **Verifier** | How will I confirm the action actually worked as intended? |

The Skeptic's objections either get resolved (strengthening the plan) or escalate
to blocking the action (send to VALIDATE for a scope or reversibility check).
Do not skip this pass for non-trivial actions — the research basis for it is
robust: multi-perspective internal deliberation causally improves accuracy on hard
reasoning tasks (Kim et al., arXiv:2601.10825).

If you cannot satisfy all three perspectives, you do not understand the action
well enough to execute it. Research first.

### VALIDATE (Harness Check)

Before executing, verify:

1. **Legal action check** — Is this a valid operation? Does the file exist? Is
   the function signature correct? Does the import path resolve?
2. **Scope check** — Does this action stay within the planned subtask scope?
   Am I accidentally touching something outside scope?
3. **Reversibility check** — Can this be undone? If not, flag for user
   confirmation before proceeding.
4. **Dependency check** — Have all predecessor subtasks completed successfully?
5. **Consistency check** — Does this change conflict with changes already made
   in this session? (Check `.react_agent/changes.jsonl` for prior edits)

If any check fails, do NOT execute. Fix the issue or escalate to the user.

Read `HARNESS.md` (in this skill directory) for detailed validation rules.

### ACT

Execute the change. Prefer minimal, atomic changes:
- One function at a time
- One file at a time where possible
- Complete implementations only — no stubs, no "TODO: implement this"
- If the action is a file edit, provide the complete changed function (not a snippet)

Log every action to `.react_agent/changes.jsonl`:
```json
{"subtask": 1, "step": 3, "action": "edit", "file": "src/auth.py", "function": "validate_token", "description": "Added expiry check", "timestamp": "..."}
```

### OBSERVE

After each action, verify the result:

1. **Read the output** — If a command was run, read stdout and stderr completely
2. **Check the artifact** — If a file was edited, read the relevant section back
   to confirm the edit landed correctly
3. **Run the relevant test** — If tests exist for the changed code, run them now.
   Do not batch test runs — test after each change
4. **Compare expected vs actual** — Does the observation match what you predicted
   in the REASON step?

### REFLECT

After observing:

1. **Success** — Log to memory, mark subtask step complete, proceed to next step
2. **Failure** — Diagnose:
   - Is this the same error type as a previous attempt? Check `.react_agent/memory.jsonl`
   - If yes: you are going in circles. Stop. Reframe the problem. Try a different
     approach. Read TROUBLESHOOTING below.
   - If no: log the failure with diagnosis, attempt a fix, re-enter the loop
3. **Unexpected result** — Something worked but not as predicted. Investigate
   before proceeding — unexpected success can mask latent bugs.

Log reflections to `.react_agent/memory.jsonl`:
```json
{"subtask": 1, "step": 3, "outcome": "fail", "error_type": "ImportError", "diagnosis": "circular import between auth and users modules", "approach_tried": "direct import", "next_approach": "lazy import or extract shared types to separate module", "timestamp": "..."}
```

### Self-Evolution (Attempt Cap)

The ReAct loop runs on an explicit attempt counter per subtask.

- Default cap: **5 attempts** per subtask.
- On attempt 2+: the approach must **materially differ** from the previous attempt.
  Changing a variable name or adjusting a parameter is not material. Refactoring
  the approach, using a different tool, or decomposing the problem differently is.
- When the cap is reached: mark the subtask `INCOMPLETE`, write a summary of all
  approaches tried and their failure signals to `progress.md`, and surface to the
  user. **Do not pretend the subtask passed.** `INCOMPLETE` is an honest and
  actionable status; false completion corrupts the downstream plan.
- Failure signals to reflect on before each retry: the named failure mode from
  HARNESS.md's taxonomy, which recovery action it maps to, and whether the
  acceptance condition itself (not the implementation) needs revision.

## Memory System

The `.react_agent/` directory is your working memory. It persists across
conversation turns within a session. Structure:

```
.react_agent/
├── task.md          # Reframed requirements and acceptance criteria
├── recon.md         # Reconnaissance findings
├── plan.md          # Ordered subtask plan
├── changes.jsonl    # Append-only log of every action taken
├── memory.jsonl     # Curated outcome/lesson log (distilled from daily files)
├── memory/          # Raw daily session logs (YYYY-MM-DD.md) — unfiltered capture
├── progress.md      # Current status dashboard (overwritten each update)
├── autonomy.md      # Standing permission tiers — read at Phase 0
├── personas/        # Role files for spawned subagents (optional)
└── cases/           # Archived case files from prior task runs (if any)
    └── case_001.json
```

Read `MEMORY.md` (in this skill directory) for case memory format and retrieval patterns.

### Memory Read (Before Planning)

At the start of each subtask, scan `memory.jsonl` for:
- Previous failures on similar operations (same file, same function, same error type)
- Successful approaches that might transfer
- Patterns across failures (if 3+ failures share a root cause, address the root cause)

### Memory Write (After Each Step)

After each REFLECT step, append to `memory.jsonl`. Include:
- The subtask and step number
- What was attempted (action description)
- What happened (outcome: success/fail/unexpected)
- Why (diagnosis if failed, confirmation if succeeded)
- What to do next (informed by what was learned)

When a decision, blocker, or rejected path is important enough that a future
turn would otherwise need to reconstruct it from scratch, write a distilled
continuity packet as well. Use the `continuity-log` skill for that style of
compact-safe note. Do **not** try to dump raw chain-of-thought; persist the
decision, evidence, dead end, and exact resume point.

### Context Budget Management

The context window is the most constrained resource during long tasks. Manage it actively:

- **Delegate verbose operations to subagents** — test runs, log analysis, doc fetching, and any operation that produces large output belong in a subagent. The subagent reports only its summary back, not the raw output.
- **Prefer CLI tools over MCP servers** — CLI tools (git, grep, find, npm) are context-neutral; MCP server tool definitions load on every request. Use CLI where both options exist.
- **Write before forgetting** — if a key finding, decision, or error message appears in context that you will need later, write it to `.react_agent/` immediately. Do not rely on it surviving context truncation.
- **When context is filling** — proactively checkpoint current subtask state to `progress.md` before auto-compaction fires. Fields that must survive any compaction: current subtask number, `task.md` completion conditions, and the last known working state.
- **Use continuity packets for pivots** — when the load-bearing thing to preserve is a decision or rejected approach rather than a file diff, write a `continuity-log` style packet so the next turn does not repeat the same analysis.
- **Protect on compaction**: `task.md` execution contract, `progress.md` status table, current subtask's `plan.md` entry, and any unresolved blockers.

### Progress Tracking

After each subtask completes (or fails), update `.react_agent/progress.md`:

```markdown
# Progress

## Task: [reframed task description]
## Status: IN_PROGRESS | BLOCKED | COMPLETE

| # | Subtask | Status | Notes |
|---|---------|--------|-------|
| 1 | Extract shared types | ✅ done | Created types.py |
| 2 | Migrate auth module | ✅ done | 3 functions updated |
| 3 | Update test suite | 🔄 in progress | 2/5 test files done |
| 4 | CI config update | ⏳ pending | Blocked on #3 |

## Lessons Learned
- [Accumulated insights from memory.jsonl]

## Current Blockers
- [Any issues requiring user input]
```

## Troubleshooting Protocol

When stuck (same error 2+ times, or no progress for 3+ steps):

### Level 1: Reread

Go back to `recon.md` and `task.md`. Are you solving the right problem? Did you
miss a dependency or constraint during reconnaissance?

### Level 2: Isolate

Extract the failing piece into a minimal reproduction:
- Create a standalone test file that exercises just the failing behavior
- Strip away everything unrelated
- Confirm the failure reproduces in isolation
- Fix it in isolation first, then reintegrate

### Level 3: Pivot

If the same approach has failed twice:
- State explicitly what approach was tried and why it failed
- Propose an alternative approach that avoids the failure mode
- If multiple alternatives exist, pick the simplest one
- Do NOT retry the same approach with minor variations

### Level 4: Escalate

If you have exhausted your approaches:
- Write a clear summary of what was tried, what failed, and why
- State what information or decision you need from the user
- Do not apologize — just present the situation and your options

## Completion Protocol

Before declaring a task complete:

1. **Recheck acceptance criteria** — Open `task.md`, verify each `completion_condition`
   is satisfied. Do not rely on memory of what ran — re-run the checks now.
2. **Evidence gate** — Before claiming done, write a standalone evidence artifact at
   `.react_agent/evidence.md` covering:
   - Problem statement (link to `task.md`)
   - Root cause or key change (what was wrong and what was done)
   - Resolution (what was changed and where)
   - Validation (commands run and their exact outputs)
   - Residual uncertainty (what you cannot verify and why)
   Do not release a completion claim while any `completion_condition` in `task.md`
   is uncited in this file. The evidence artifact is what a verifier or another
   agent would reopen to independently confirm the task is done.
3. **Acceptance alignment check** — Ask: does passing the local checks (tests green,
   linter clean) actually satisfy the `completion_conditions` in `task.md`? If
   there is a gap (local checks pass but a stated condition is still unmeasured),
   add a test or check that covers it before proceeding.
4. **Run full validation** — Execute the complete test suite, linter, type checker
   (whatever validation tools exist in the project).
5. **Review all changes** — Scan `changes.jsonl` for unintended side effects.
   Did you touch files outside the planned scope? If so, verify those changes
   are correct and necessary.
6. **Quality check** — Read `QUALITY.md` (in this skill directory) and walk
   through the six-dimension check before marking anything done.
7. **Generate summary** — Write a concise summary of what was done, structured as:
   - What changed (files, functions, configs)
   - Why (link back to task requirements)
   - How to verify (commands to run, things to check)
   - What was NOT done (explicit out-of-scope items, if any)

## Skill Composition

This skill works with other skills. When a subtask falls into another skill's
domain, delegate:

- File format tasks (docx, xlsx, pdf, pptx) → use the relevant format skill
- Frontend/UI work → use the frontend-design skill
- Browser/QA testing → use the gstack skill
- Self-repairing codegen pipelines, dark software factories, and legality / critic loops -> use the `agentic-harness` skill as a specialist sub-skill
- Between-compaction decision capture and resume notes -> use the `continuity-log` skill

The ReAct loop wraps around delegated skill execution — the delegated skill
handles the *how*, this skill handles the *whether it worked*.

## Anti-Patterns (Do NOT Do These)

- **Shotgun debugging** — Making multiple unrelated changes hoping one fixes
  the problem. Change one thing at a time.
- **Optimistic skipping** — Skipping validation because "it should work."
  Verify every change.
- **Scope creep** — Fixing things that aren't broken, refactoring code that
  isn't in scope, "improving" things the user didn't ask for.
- **Silent failure** — Encountering an error and moving on without logging it.
  Every failure teaches something.
- **Premature completion** — Declaring done without running the acceptance
  criteria checks. "It compiles" is not "it works."
- **Context amnesia** — Ignoring what's in `memory.jsonl` and repeating a
  failed approach. Read your own notes.
- **Tunnel vision** — Spending 5+ steps on a single failing approach. After 3
  failures on the same issue, you must change strategy.

## Reference: State Machine

```
START
  │
  ├─► Phase 0: Reframe ──► task.md          [gpt-4o]
  │
  ├─► Phase 1: Recon ────► recon.md         [gpt-4o]
  │
  ├─► Phase 2: Plan ─────► plan.md          [gpt-4o]
  │         └─► [user confirms]
  │
  └─► Phase 3: Execute (per subtask)
        │
        ├─► REASON ──► state intent         [gpt-4o]
        ├─► VALIDATE ─► harness checks      [gpt-4o]
        ├─► ACT ──────► code/file edits     [gpt-4.1]
        ├─► OBSERVE ──► read results        [gpt-4o]
        └─► REFLECT ──► log memory          [gpt-4o]
              │
              ├─ success ──► next step
              ├─ failure ──► diagnose, retry (max 3), pivot
              └─ unexpected ► investigate

  ├─► Phase 4: Completion checks
  │     ├─► Recheck completion_conditions (re-run)
  │     ├─► Write evidence.md (evidence gate)
  │     ├─► Acceptance alignment check
  │     ├─► Run full validation
  │     ├─► QUALITY.md six-dimension check
  │     └─► Generate summary
  │
  └─► DONE
```
<!-- consolidation:see-also:start -->
## See Also
[[tdd-agent]]  [[continuity-log]]  [[skill-wiki]]
<!-- consolidation:see-also:end -->
