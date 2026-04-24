---
name: agentic-harness
description: >
  Protocol for synthesizing, debugging, iterating on, and verifying automated LLM
  pipeline harnesses (dark software factories, code-generation wrappers, multi-stage
  agentic systems). Think of it as the programmatic train station for agentic coding
  systems like OpenClaw, Claude Code, OpenCode, and GitHub Copilot CLI: they define
  the default backbone, while the harness routes work, enforces legality, tracks
  branch/story state, and reconciles failures into general harness fixes. Use when a
  harness produces incoherent output, illegal or prohibited actions, gate failures,
  LLM truncation bugs, test-generation failures, or violation-count divergence. The
  core contract: set a coherence=False todo at task start and iterate until you can
  flip it to True.
---

# Agentic Harness Skill

## Programmatic Train Station Thesis

Think of `agentic-harness` as the **programmatic train station** for agentic coding systems.

- OpenClaw, Claude Code, OpenCode, GitHub Copilot CLI, or similar systems are the backbone templates
- tasks, stories, and prompts are the passengers
- branches and artifacts are the platforms
- legality gates, critics, and retry policies are the signals and switchyard logic
- the harness is the stationmaster that routes traffic, prevents collisions, and
  records what actually departed and arrived

The harness is not just a wrapper around one model. It is the control layer that:

- normalizes work requests into explicit stories or scenes
- routes them to the right coding agent or subagent
- enforces policy before side effects happen
- reconciles failures into reusable repair logic
- tracks which branch, artifact, and critic state belongs to which work item

If several coding agents can enter the same project, the harness should be the
shared station contract they all pass through.

### Backbone operating model

When building a new coding harness, start from the operational backbone used by
systems like **OpenClaw, OpenCode, GitHub Copilot CLI, and Claude Code**.

Minimum backbone behaviors:

- terminal-native tool execution, not chat-only ideation
- explicit search -> inspect -> edit -> run -> verify loop
- branch or worktree awareness
- artifact and evidence production at known paths
- checkpointed plan / todo / state tracking
- critic-gated completion rather than "looks good" completion

Extra planners, evaluators, memory layers, or multi-agent rooms can sit on top
of this backbone, but they should not replace it.

The intended stance is **dark for a specific task**: once a story or work item is
well-scoped, the harness should be able to run that task end-to-end with minimal
human interruption. The darkness is scoped to the assigned task, not treated as a
blanket license for unrestricted repo-wide autonomy.

## Core Contract — The Coherence Flag

**Before touching any harness code**, register a coherence sentinel in SQL:

```sql
INSERT INTO todos (id, title, description, status) VALUES
  ('coherence', 'Harness coherence', 
   'All known incoherence sources resolved; pipeline completes a representative run without divergence',
   'in_progress');
```

The flag stays `in_progress` (coherence=False) until every root cause in the
**Incoherence Checklist** is cleared and a live run confirms it.  
Flip it only when the pipeline actually passes:

```sql
UPDATE todos SET status = 'done' WHERE id = 'coherence';
-- coherence = True
```

> "Did you fulfill this request?" — answer only after the todo is `done`.

---

## Relation to React Agent

Keep `agentic-harness` and `react-agent` as **adjacent but separate** skills.

- `react-agent` is the general-purpose execution loop for planning, progress,
  evidence, and multi-step delivery.
- `agentic-harness` is the specialist loop for **self-repairing automated systems**:
  legality, coherence, critic routing, retry discipline, and harness synthesis.

Recommended composition:

```text
react-agent
    -> Phase 0-2: contract, recon, plan, kanban, branch discipline
    -> delegates harness-specific execution to agentic-harness
agentic-harness
    -> diagnoses coherence failures
    -> repairs proposer / validator / critic logic
    -> returns a stable harness candidate plus coherence verdict
```

Do not collapse them into one skill unless you find repeated evidence that the
outer delivery loop and the inner harness-repair loop cannot be maintained independently.

## No Band-Aid Repair Rule

This skill is explicitly **anti ad-hoc repair**.

- Do not patch only the current generated artifact if the defect comes from the
  proposer, validator, critic, retry policy, or state contract.
- Fix the mechanism that produced the defect class.
- A repair only counts when it suppresses the failure mode on:
  1. a minimal isolated reproduction
  2. a representative full harness run

If the only way to "fix" the system is to hand-edit each bad output, the harness
is still incoherent.

## Artifact-Backed Coherence Gate

Coherence is not true just because logs look better.

Before flipping the coherence flag, confirm that:

- the expected artifact exists at a known path
- the artifact was produced by the repaired pipeline, not by manual patching
- the artifact can be reopened and inspected after the run
- the artifact satisfies the task-specific completion condition

## Autonomy Should Be Inspectable from Code

Do not treat autonomy as a vibe or a marketing label. Treat it as a property of
the **orchestration code**.

When reviewing a harness, inspect:

- how much task decomposition happens without a human turn
- how much decision authority is delegated to workers
- what monitoring hooks exist
- where intervention points still exist
- whether approval nodes protect irreversible actions

Use a simple code-inspection lens:

```text
assess_autonomy(code):
    orchestration = extract_orchestration_logic(code)
    impact = score_task_and_decision_independence(orchestration)
    oversight = score_monitoring_and_intervention_points(orchestration)
    return weighted_autonomy_score(impact, oversight)
```

Operational rule:

- higher autonomy requires **more explicit oversight**, not less
- if impact rises while intervention points disappear, the harness is becoming reckless
- inspect the orchestration graph before trusting a "fully autonomous" claim

---

## AutoHarness Thesis — Learn the Harness, Not Just the Prompt

AutoHarness (arXiv:2603.03329) matters because it validates a stronger pattern than
"retry the prompt until it behaves":

- the agent should **write or refine code around itself**
- the environment should act as the **critic**
- legality should be checked by **verifiable code**, not only by model intuition

The paper's core result is that a smaller model with a synthesized harness can
outperform a larger unharnessed model. The transferable lesson is not "use games";
it is: **if the environment has hard rules, move those rules into code and refine
that code from live failures**.

## Orchestration Patterns to Carry Forward

These patterns are in scope for this skill and should be used explicitly when they fit.

### LangGraph pattern

Use a LangGraph-style architecture when you need:

- explicit typed shared state
- named nodes with stable contracts
- router / supervisor nodes
- bounded loops with counters in state
- checkpointed recovery between turns
- human-review or approval nodes

Default node set for a software harness:

- planner
- router
- implementer
- executor
- critic
- verifier
- recovery / retry
- human-review

State should carry:

- current objective
- current story or scene id
- current branch
- artifact paths
- retry counters
- critic findings
- coherence status

### Operating modes

Support two explicit operating modes:

- **semi-autonomous** - workers advance until a checkpoint, then pause for review
- **fully autonomous** - workers continue without a human checkpoint, but only
  inside a verified envelope with strong monitoring

For dark-factory use, prefer **fully autonomous for the current task** once the
story, artifact target, and guardrails are explicit.

Default checkpoint triggers:

- destructive file operations
- dependency installation or environment mutation
- branch merge or deployment
- low-confidence critic verdicts
- novelty or ambiguity that changes the project plan

Do not let a harness drift between these modes implicitly. The current mode
should be named in state and visible in logs.

### Anthropic agentic orchestration patterns

Treat the following as canonical patterns:

- **Prompt chaining** — linear stage-by-stage transformations
- **Routing** — classify work, then send to the right specialist
- **Parallelization** — fan out independent workers, then reduce
- **Orchestrator-workers** — one coordinator delegates subproblems
- **Evaluator-optimizer** — critic loop that scores and refines outputs

Mapping to harness work:

- prompt chaining -> multi-stage codegen pipeline
- routing -> choose planner / coder / test-writer / repair path
- parallelization -> run multiple candidate harnesses or rollouts
- orchestrator-workers -> PM / implement / verify split
- evaluator-optimizer -> reconcile / critic / fix loop

### AutoGen pattern

AutoGen-style multi-agent chat is appropriate when role conflict is useful, not decorative.

Useful roles:

- product manager
- planner
- coder
- code critic
- tool executor
- verifier
- repo steward

If using group chat / chat room capability:

- cap rounds explicitly
- define termination conditions up front
- keep the code critic independent from the coder
- require artifact output, not just conversation consensus
- have one manager agent decide when a discussion ends and work product is accepted

The point of a chat room is perspective separation, not theatrical dialogue.

### Canonical split

Treat a harness as three separable responsibilities:

```python
def propose_action(state) -> object:
    ...

def is_legal_action(state, action) -> bool:
    ...

def critique_transition(state, action, env_feedback) -> dict:
    ...
```

- `propose_action` picks a candidate move / patch / command
- `is_legal_action` enforces rule validity before commitment
- `critique_transition` consolidates environment failure into a repair signal

For software harnesses, "action" can mean:
- shell command
- file patch
- generated import / dependency choice
- next pipeline transition

---

## Harness Synthesis Loop

When the task is not just to debug a harness but to **build one automatically**,
use this loop:

1. Start from a minimal harness skeleton
2. Run it in the real environment
3. Stop the rollout immediately on illegal action, execution failure, or invalid state transition
4. Sample a small set of concrete failures
5. Consolidate them into a critic report
6. Refine the harness code, not just the prompt
7. Keep multiple harness candidates alive when exploring different control structures
8. Promote the candidate with the best legality rate / reward

### Search policy

AutoHarness uses tree search with Thompson sampling over code hypotheses. The
important operational point is:

- do not refine a single brittle harness forever
- keep several competing harness variants
- balance exploration (new logic) against exploitation (repairing the current best)

For day-to-day engineering, a simpler equivalent is acceptable:
- maintain 2-4 materially different harness candidates
- score them on legality first, then reward / usefulness
- kill candidates that repeat the same failure mode

### Archive-driven discovery

Keep an archive of prior harness candidates, not just the current best attempt.

Minimum archive contents:

- candidate id
- control structure summary
- benchmark or story set used
- legality / trust / completion metrics
- critic report
- artifact path
- failure class labels

Promotion rule:

- only promote a candidate into the archive if it beats the incumbent on the
  benchmark suite or introduces a materially different control structure worth keeping

The point is to let the station learn from previous harnesses instead of
re-deriving the same loops every session.

### Failure sampling

The paper's setup is a good default pattern:
- run multiple environments in parallel
- cap rollout length
- sample only a few failed steps for refinement
- train until legality reaches 1.0 or the budget is exhausted

The point is to feed the refiner **high-signal failures**, not every log line.

---

## Harness Progression Ladder

AutoHarness suggests three increasing levels of control:

### 1. Harness-as-action-verifier
- let the LLM propose an action
- reject it if `is_legal_action(...)` fails
- re-prompt with an explicit illegal-action warning

Use this first. It is the lowest-friction upgrade over a raw agent.

### 2. Harness-as-action-filter
- code enumerates or narrows legal candidates
- the LLM ranks or selects among them

Use this when the action space is structured and legality can be enumerated.

### 3. Harness-as-policy
- code directly chooses the next action
- no LLM call is required at execution time

Use this only after legality is stable and the task is repetitive enough that the
policy can be distilled into code.

Rule of thumb:
- verifier -> when the model is smart but sloppy
- filter -> when the legal set is derivable
- policy -> when the task is narrow, repeated, and testable

---

## Refinement Rules from Environment Feedback

Preserve the split between proposer bugs and validator bugs.

- If `is_legal_action(...)` says **legal** but the environment rejects the action:
  - refine **both** proposer and validator
- If `is_legal_action(...)` says **illegal** and the environment also rejects it:
  - refine the **proposer** first
- If actions are legal but reward is poor:
  - legality is solved; optimize policy quality separately

Do not mix these failure classes together. A harness that confuses legality with
strategy becomes harder to repair.

### Heuristic ordering

Optimize in this order:

1. illegal-action rate
2. execution reliability
3. task reward / output quality

A clever policy with illegal actions is not a policy. It is noise with moments of success.

---

## AutoHarness Core Methods — Pseudocode

Use these as the concrete reference pattern when implementing automatic harness
learning rather than manual one-off fixes.

### 1. Harness synthesis via tree search

```text
Initialize tree with root node containing empty/template code

WHILE timeout not reached:
    node = Thompson_sample(tree)

    rollout_results = run_parallel_envs(node.code, n=10, max_steps=1000)

    failed_steps = collect_failures(rollout_results, max=5)
    # illegal action, exception, wrong format, invalid transition

    new_code = Refiner(
        base_code=node.code,
        failed_steps=failed_steps,
        env_desc=environment.description,
        action_space=environment.action_space,
    )

    new_node = tree.add_child(parent=node, code=new_code)

    heuristic = eval_legal_action_rate(new_code, test_rollouts=1000)
    update_node_stats(new_node, heuristic)

    IF heuristic == 1.0:
        RETURN new_code
```

### 2. Thompson sampling node selection

```text
FOR each node in tree:
    alpha = node.wins + 1
    beta = node.trials - node.wins + 1
    node.sample = draw Beta(alpha, beta)

RETURN argmax(node.sample for node in tree)
```

Why this matters:
- early low-trial nodes remain explorable
- search does not collapse to one brittle path too early
- partial successes can still compete with the current best candidate

### 3. Harness-as-action-verifier inference loop

```text
FUNCTION agent_step(observation):
    action = propose_action(observation)

    IF is_legal_action(observation, action):
        RETURN action
    ELSE:
        action = LLM(
            observation,
            warning="previous action was illegal: " + action,
        )
        RETURN action
```

### 4. Refiner prompt logic

```text
FUNCTION Refiner(base_code, failed_steps, env_desc, action_space):
    FOR each failed_step in failed_steps:
        analyze state
        identify violated rule or contract
        reason about the fix

    reason about loop-avoidance and fallback behavior

    new_code = LLM(
        system="python programmer, environment expert",
        context=[env_desc, action_space, failed_steps, base_code, signatures],
        rules=[
            no broad try/except,
            satisfy all observed states,
            fix all current errors,
            prefer safe executable code,
            add tie-breaking / random fallback only where needed,
        ],
    )

    RETURN new_code
```

### 5. Harness-as-policy reward heuristic

```text
FUNCTION compute_heuristic(trajectory):
    IF illegal_action_taken:
        RETURN 0
    ELSE:
        r = environment_reward(trajectory)   # sparse reward in [0, 1]
        RETURN 0.5 + 0.5 * r
```

This keeps legality as a hard floor:
- illegal trajectories score `0`
- any legal zero-reward trajectory still beats an illegal one
- reward optimization only starts after validity is preserved

### 6. Refinement routing

```text
result = execute_step(state, code)

IF is_legal_action() returned True AND environment rejected action:
    refine BOTH propose_action() AND is_legal_action()

ELIF is_legal_action() returned False AND environment confirms action was illegal:
    refine ONLY propose_action()
```

### Working premises

- [observed] harness synthesis should search over a **tree of code hypotheses**, not only flat iterative prompting
- [observed] the refiner should receive **state + action + error**, not just an error string
- [observed] `propose_action` and `is_legal_action` should be separable and repairable independently
- [inferred] Beta priors keep underexplored nodes alive long enough to discover better harness structures
- [inferred] the `0.5 + 0.5r` heuristic preserves legality as a strict constraint before reward optimization

---

## Incoherence Checklist

Work through these in order; each is a potential root cause for a harness that
produces degraded or diverging output.

### 1. Sentinel objects fed back to the LLM
- Never return a sentinel dict (e.g. `{"kind": "ParseError", ...}`) from a
  parse function and pass it to a downstream LLM call.
- The LLM treats the sentinel as content and generates responses around it,
  creating new files / new import chains → violation count grows each round.
- **Fix**: return `[]` / `{}` / `None` on parse failure; log a warning instead.
  Salvage partially-truncated JSON by slicing at the last `}` before `]`.

### 2. Gate timeouts as false negatives
- Long-running shell commands in gates (e.g. `pip install -e .`) take 30-40 s
  to *fail* when the target file doesn't exist.  Combined with an OR chain they
  can exceed the gate timeout and return exit=-1.
- **Fix**: guard expensive operations behind file-existence checks:
  ```bash
  ([ -f pyproject.toml ] || [ -f setup.py ]) && pip install -e '.[dev]' -q \
    || pip install -r requirements.txt -q 2>/dev/null || true
  ```
- After fix, measure: gate that took 83 s → 1.2 s.

### 3. LLM output truncation mid-structure
- At `max_completion_tokens=4096`, the LLM truncates mid-JSON.
- **Fix pattern**:
  ```python
  def _salvage_json_array(raw: str) -> list:
      last_brace = raw.rfind("}")
      if last_brace == -1:
          return []
      candidate = raw[: last_brace + 1].rstrip() + "]"
      # find opening bracket
      start = candidate.find("[")
      if start == -1:
          return []
      try:
          return json.loads(candidate[start:])
      except json.JSONDecodeError:
          return []
  ```
- Always validate completeness: check for a sentinel like `# END OF FILE` or
  verify the JSON is syntactically closed before accepting the response.

### 4. Violation-count divergence (getting worse, not better)
- Symptom: violations grow round-over-round (7 → 12 → 11 → 26).
- Diagnosis: either sentinel objects (see #1) or the LLM is introducing new
  imports / files to fix existing violations, creating a cascade.
- **Distinguish import violations from LLM-reported violations**:
  - Import violations (from actual Python import attempts) are authoritative.
  - LLM-reported NameErrors / style issues are advisory; treat as soft.
- Hard-stop after `MAX_ROUNDS` and pass residual violations forward rather than
  cycling forever.  Residual LLM-only violations are usually false positives.

### 5. Test generation producing empty output
- Symptom: `generate_tests` discards all files; 0 test files written.
- Common cause: the generated source has broken imports (pygame, cv2, etc.)
  that cause `CollectionError` at pytest collection time.
- **Fix options**:
  - Have tests use inline stubs rather than importing real modules.
  - Inject `SDL_VIDEODRIVER=dummy DISPLAY=:99` before collection.
  - Generate a `conftest.py` that mocks heavy deps before any import.
- Continuation limit: if a test file generation hits 5 continuation turns and
  still has a `SyntaxError`, discard and move on; don't block the pipeline.

### 6. Full pipeline retry vs. targeted fix
- Pipeline retry on gate failure triggers full re-implementation (expensive).
- Before accepting a retry, confirm the gate failure is a *real* code defect,
  not a harness timing/tooling issue (see #2).
- Fix the harness first; only then let the pipeline retry the generated code.

---

## Observability Pattern for Long-Running Harness Runs

```bash
# Start
nohup python -m dark_factory "prompt" --output /tmp/gendir > /tmp/run.log 2>&1 &
echo "PID $!"

# Monitor
tail -f /tmp/run.log

# Key log signals to watch for:
# GOOD:  "reconcile_audit round N: M violation(s) (K from import check)"  — K decreasing
# GOOD:  "generate_tests: N files"                                         — N > 0
# GOOD:  "gate install_deps: exit=0"
# BAD:   "reconcile_audit round N: M violation(s) (0 from import check)"  — M growing
# BAD:   "ReadTimeout on attempt N" × 3+                                  — server overloaded
# BAD:   "Test for X truncated at turn 5" / SyntaxError                   — test discard
# BAD:   "gate install_deps: exit=-1"                                      — gate timeout bug
```

**ReadTimeout handling**: `MAX_RETRIES=4`, backoff `[2, 5, 10, 20]` seconds.
Silence in the log after a retry message = generation in-flight (not hung).
DEFAULT_TIMEOUT = 300 s per attempt.  A 216-second generation is slow but valid.

---

## Secure Execution Envelope

If the harness performs real software work, give it a controlled execution
envelope rather than raw host access.

Minimum envelope:

- isolated worktree, container, or sandboxed repo copy
- mounted codebase or bounded workspace path
- explicit security guardrails on commands, files, and network access
- static analysis tools available to the critic / verifier layer
- audit logs for actions, errors, security events, and outputs

Security loop:

```text
while run_active:
    monitor_for_unauthorized_access()
    monitor_for_data_leakage()
    verify_workspace_integrity()
    if security_issue_detected:
        isolate_run()
        emit_security_report()
        route_to_recovery()
```

Do not call a system "autonomous" if it is only autonomous because it was given
unsafe unrestricted access.

### Trust gate for generated code

The verifier should aggregate multiple analysis tools into a trust pass, not rely
on one model's confidence.

Minimum trust inputs:

- tests
- static analysis
- lint or type checks when available
- security scan or policy checks
- dependency / import reality checks

Use trust as a gate for acceptance, not as a substitute for artifact-backed verification.

### Hallucination control

Treat hallucinations in repository-level codegen as a tracked failure class.

Useful buckets:

- invented imports or APIs
- nonexistent files, modules, or symbols
- false assumptions about repo structure
- security or policy violations

Mitigation order:

1. improve retrieval and context grounding
2. improve verifier / critic detection
3. only then retry generation

---

## Dark Software Factory — Specific Internals

These apply to the `dark_factory` harness at `/home/user/harness`:

| Constant | File | Value | Notes |
|---|---|---|---|
| `_MAX_ROUNDS` | `reconcile.py:23` | 4 | Fix+audit cycles; round counter is 0-based internally, displayed 1-based |
| `_SNAPSHOT_CHARS` | `reconcile.py:24` | 32 000 | Source fed to audit/fix LLM; fills most of 48K context for large projects |
| `GATE_TIMEOUT` | `gates/runner.py:14` | 120 s | Gate shell command hard cap |
| `MAX_RETRIES` | `llm.py:308` | 4 | LLM HTTP retries before raising |
| `DEFAULT_TIMEOUT` | `llm.py:49` | 300 s | Per-attempt HTTP timeout |

**Pipeline flow**: PM → implement → reconcile (audit/fix loop) → generate_tests → install_deps gate → verify → [retry ×3]

**LLM tiers**:
- `heavy` → `local-qwen` (Qwen3.6-35B-A3B, 127.0.0.1:8081, ~15-20 tok/s, 4096 max out)
- `fast`/`standard` → `copilot-proxy` (192.168.3.122:8069, gpt-4o / gpt-4.1 / claude-sonnet-4)

**Reconcile route logic** (`reconcile.py:231`):
```python
if state["violations"] and state["round"] < state["max_rounds"]:
    return "fix"   # continue loop
return END         # pass residuals to verify
```
Note: `round` increments *after* fix, so 4 fix passes happen before the `< 4` guard closes.

**Test stub pattern**: tests use inline class stubs, not real `src.*` imports.
This avoids pygame `ImportError` at collection time but means test coverage
of the real implementation requires a separate integration pass.

---

## Dark Software Factory Delivery Model

Beyond the internal reconcile loop, keep the **project-management mentality** explicit.

### Kanban from the project plan

Translate the project plan into story cards with at least:

- story id
- objective
- acceptance condition
- current status
- branch
- artifact path
- latest critic note

Recommended statuses:

- backlog
- ready
- in_progress
- review
- blocked
- done

Update the story as development continues; do not let the kanban lag behind the branch state.

### Git discipline

If the user has authorized repository setup and the project is not yet under git:

1. initialize the repository
2. create the main branch
3. create one branch per story or tightly-coupled feature
4. keep commits causal and small
5. merge only after artifact-backed verification

Branch naming examples:

- `story/<id>-<slug>`
- `feature/<slug>`
- `bugfix/<slug>`
- `chore/<slug>`

### Agent platform routing

Treat each coding framework as both a worker line and a reference backbone the
station can inherit from:

- OpenClaw -> autonomous coding backbone with explicit control loop expectations
- Claude Code -> strong long-horizon coding / editing worker
- OpenCode -> alternate coding worker or experimentation lane
- GitHub Copilot CLI -> terminal-native execution / inspection lane

The harness should decide:

- which agent gets which story
- what context packet each agent receives
- what artifact path the agent must produce
- what critic or verifier checks the result afterward

Do not let every agent freestyle its own lifecycle. Shared station rules should
outlive any one framework.

If building a new harness from scratch, copy the backbone shape first:

1. inspect the repo and active state
2. plan and track work explicitly
3. use tools to search, edit, and execute
4. emit artifacts and evidence
5. let critics or verifiers decide completion

Only then add more exotic orchestration.

### Task taxonomy and capability routing

Keep a simple task taxonomy beyond "write code":

- requirements / scoping
- design / architecture
- implementation
- test generation
- debugging / repair
- maintenance / migration
- research / evaluation

Route work using:

- task type
- task complexity
- agent capability
- developer expertise
- required oversight level

Rule of thumb:

- give agents work they are structurally equipped to do
- keep high-risk, underspecified, or capability-mismatched work under tighter human control
- professionals do not just let the agent vibe; they control routing, checkpoints, and acceptance

### MLflow experiment ledger

Use `mlflow` as the station ledger when the harness compares multiple frameworks,
prompt packets, critics, or retry policies.

Recommended mapping:

- experiment -> project or harness family
- parent run -> story, benchmark suite, or repair campaign
- child run -> framework-specific attempt, critic pass, or verification pass

Minimum tags:

- `framework`
- `story_id`
- `branch`
- `artifact_path`
- `coherence_status`
- `critic_round`

Minimum metrics:

- `illegal_action_rate`
- `gate_pass_rate`
- `critic_violation_count`
- `artifact_generated`
- `time_to_first_artifact_sec`

Minimum artifacts:

- logs
- critic reports
- generated repo or output bundle
- evidence packet

This keeps Claude Code, OpenCode, GitHub Copilot CLI, and future worker lines
on one shared comparison surface.

### Studio analogies

Use the studio metaphor to control context:

- stories are scenes
- the kanban is the shooting board
- the continuity script is the artifact / evidence packet
- sparse retrieved context is the actor prompt
- the critic is script supervision

Only hand each worker the context needed for its scene.

### RPG memory analogy

Between sessions, the agent should reread the equivalent of a character sheet:

- current objective
- current branch
- open story cards
- artifact inventory
- unresolved status effects (blockers, retries, critic findings)

If the next session cannot reload that sheet and continue coherently, the harness memory is insufficient.

---

## Iteration Protocol

1. **Identify**: run the pipeline; capture log; label each failure by checklist item number.
2. **Prioritize**: fix structural incoherence (#1 sentinels, #2 gate races) before
   surface symptoms (#5 test generation), because structural bugs cause cascading failures.
3. **One fix per commit**: keep the causal chain legible; don't batch unrelated fixes.
4. **Verify the fix in isolation** before re-running the full pipeline:
   - For gate bugs: time the gate command directly in shell.
   - For parse bugs: feed a known-truncated fixture through the parse function.
   - For LLM-output bugs: replay the prompt with a checkpoint.
5. **Re-run pipeline on a representative prompt** (same complexity as the failing case).
6. **Check the coherence flag criteria** — only flip when *all* items are cleared.

---

## Checklist Before Flipping coherence → True

- [ ] Violation count converges (decreases) across reconcile rounds
- [ ] Gate `install_deps` exits 0 in < 5 s for projects without pyproject.toml
- [ ] `generate_tests` produces ≥ 1 test file per source module
- [ ] No ParseError sentinel fed to any downstream LLM call
- [ ] Pipeline completes without `retry` for a straightforward prompt
- [ ] All tests in the generated project pass (or known skips are documented)
- [ ] Expected artifact exists at a known path and can be reopened after the run
