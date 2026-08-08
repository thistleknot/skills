---
name: autoresearch
description: >
  Autonomous iterative hill-climbing research loop. Use when the goal is
  quantitative improvement on a defined metric: define objective + scorer,
  loop (propose change → measure delta → keep/discard), checkpoint after
  each gain. Inspired by Karpathy's autoresearch pattern. Distinct from
  deep-research (web evidence) and react-agent (task execution).
status: active
last_validated: 2026-04-28
supersedes: []
validation_method: session
---

# Autoresearch

## When to Use

Use autoresearch when:

- You have a **measurable objective** — a scalar score, pass rate, loss, accuracy
- You can **propose incremental changes** programmatically (hyperparams, prompt variants, code patches, architecture choices)
- You want **autonomous exploration** without human steering at each iteration
- The search space is too large for exhaustive evaluation but structured enough for hill-climbing

Do NOT use autoresearch for:
- Web evidence gathering (use `deep-research`)
- One-shot task execution (use `react-agent`)
- Random search without a metric (define the metric first)

---

## Core Loop

```
define(objective, scorer, initial_state)
    │
    ▼
┌─────────────┐
│  PROPOSE    │  generate a candidate change Δ from current_state
└─────────────┘
       │ candidate
       ▼
┌─────────────┐
│  MEASURE    │  score(apply(current_state, Δ)) → new_score
└─────────────┘
       │ delta = new_score - best_score
       ▼
┌─────────────┐
│  KEEP/DISCARD│  if delta > 0: accept; else: discard
└─────────────┘
       │ if accepted
       ▼
┌─────────────┐
│  CHECKPOINT │  git commit OR sqlite row; log delta, iteration, change description
└─────────────┘
       │
       └──────────► loop until budget exhausted or convergence
```

### Convergence Criteria

| Criterion | When to use |
|---|---|
| `patience` steps without improvement | Typical — halt when stuck |
| Score ≥ `target_score` | When a threshold is known |
| Budget exhausted (time / iterations / cost) | Always as a backstop |
| Improvement rate < `theta` per last N steps | Diminishing returns detection |

---

## State Schema

```python
class ChangeRecord(BaseModel):
    iteration: int
    description: str            # what changed and why (LLM-generated summary)
    delta: float                # new_score - prev_score
    accepted: bool
    score_before: float
    score_after: float
    artifact_hash: str          # SHA-256 of the changed artifact

class ResearchState(BaseModel):
    iteration: int
    best_score: float
    current_state: Any          # domain-specific: prompt string, config dict, code file
    change_log: list[ChangeRecord]
    budget_used: BudgetSnapshot
    checkpoint_path: str        # path to last committed checkpoint
```

---

## Proposer Patterns

### LLM Proposer
For prompt variants, code improvements, architecture choices:

```python
def propose_llm(
    current_artifact: str,
    objective: str,
    change_log: list[ChangeRecord],
    llm_fn: Callable,
) -> tuple[str, str]:
    """
    Require: current_artifact is valid; change_log includes the last 5 accepted changes.
    Guarantee: returns (new_artifact, description) — LLM-generated change with rationale.
    """
    recent = change_log[-5:] if len(change_log) >= 5 else change_log
    prompt = f"""
Objective: {objective}

Recent changes (most recent first):
{json.dumps([r.dict() for r in reversed(recent)], indent=2)}

Current artifact:
---
{current_artifact}
---

Propose ONE improvement. Return JSON: {{"change": "...", "description": "..."}}
where "change" is the full modified artifact and "description" explains the rationale.
"""
    return llm_fn(prompt)
```

### Grid/Random Proposer
For discrete hyperparameter spaces:

```python
def propose_grid(param_space: dict[str, list], rng: Random) -> dict:
    """Sample one parameter configuration uniformly from the Cartesian product."""
    return {k: rng.choice(v) for k, v in param_space.items()}
```

---

## Checkpoint Protocol

Use **git checkpoints** when the artifact is source code:

```python
def checkpoint_git(state: ResearchState, repo_path: Path) -> str:
    """
    Commit accepted state to git. Returns commit SHA.
    Require: git repo exists at repo_path; state.best_score improved.
    Guarantee: commit message includes iteration, score, and change description.
    """
    import subprocess
    subprocess.run(["git", "add", "-A"], cwd=repo_path, check=True)
    msg = (
        f"autoresearch iter={state.iteration} "
        f"score={state.best_score:.4f} "
        f"delta={state.change_log[-1].delta:+.4f}\n\n"
        f"{state.change_log[-1].description}"
    )
    result = subprocess.run(
        ["git", "commit", "-m", msg],
        cwd=repo_path, check=True, capture_output=True, text=True
    )
    return result.stdout.split()[-1]
```

Use **sqlite checkpoints** when the artifact is config / training state:

```python
def checkpoint_sqlite(state: ResearchState, db_path: Path) -> None:
    with sqlite3.connect(db_path) as conn:
        conn.execute("""
            INSERT OR REPLACE INTO autoresearch_runs
            (iteration, best_score, artifact_hash, description, accepted_at)
            VALUES (?, ?, ?, ?, datetime('now'))
        """, (state.iteration, state.best_score,
              state.change_log[-1].artifact_hash,
              state.change_log[-1].description))
```

---

## Rollback on Degradation

Always retain the best accepted state. If a run is interrupted, resume from the last checkpoint.

```python
def rollback_to_best(state: ResearchState, repo_path: Path) -> None:
    """Reset working tree to last known-good commit."""
    best_commit = _find_best_commit(repo_path)  # scan log for highest score in message
    subprocess.run(["git", "checkout", best_commit, "--", "."], cwd=repo_path, check=True)
```

**Rollback triggers:**
- Score degraded by more than `rollback_threshold` (e.g., 10% relative)
- `n_consecutive_failures` exceeded (e.g., 5 steps with no improvement)
- Scorer raises an exception (broken artifact — revert immediately)

---

## Budget Caps

Always impose explicit budget caps. Autoresearch loops can run indefinitely otherwise.

```python
class ResearchBudget(BaseModel):
    max_iterations: int = 50
    max_wall_clock_seconds: int = 3600
    max_llm_calls: int = 200
    patience: int = 10          # consecutive steps without improvement before halt

def budget_exhausted(state: ResearchState, budget: ResearchBudget) -> bool:
    """Check patience by scanning change_log backwards for consecutive rejections."""
    streak = 0
    for r in reversed(state.change_log):
        if not r.accepted:
            streak += 1
        else:
            break
    return (
        state.iteration >= budget.max_iterations
        or streak >= budget.patience
    )
```

---

## Scorer Design

The scorer is the highest-leverage component. Autoresearch optimises whatever the scorer measures.

| Scorer type | When to use | Example |
|---|---|---|
| Unit test pass rate | Code correctness | `pytest --tb=no -q` → parse `X passed` |
| LLM judge score | Prompt / content quality | `checklist` or `evaluator-optimizer` score |
| Loss / accuracy | ML model training | eval set loss after N epochs |
| Latency / cost | Performance optimisation | median p50 of 100 requests |
| Custom heuristic | Domain-specific | feature correlation, BLEU, ROUGE |

**Scorer contracts:**
- Must return a **scalar** in a bounded range (normalise if needed)
- Must be **deterministic or averaged** over multiple runs (avoid noise-chasing)
- Must be **cheap enough** to call at every iteration
- Higher = better (negate loss / latency if needed)

---

## Integration with Skill Library

| Phase | Skill |
|---|---|
| Propose code changes | `evaluator-optimizer` (generate→critique→regenerate) |
| Fix broken proposals | `debugging` (self-repair section) |
| Score via test execution | `tdd-agent` (Red→Green pass rate) |
| Score via LLM judge | `checklist` |
| Checkpoint state | `continuity-log` (distilled decisions) |

---

## Karpathy Autoresearch Principles

From Karpathy's autoresearch pattern (nanollm-wiki, 2024):

1. **Define the goal clearly** in one sentence before the first iteration
2. **Write the scorer first** — if you can't score it, you can't optimise it
3. **Commit every accepted change** — never lose a working state
4. **Log the rationale** with each commit — the change log is the research notebook
5. **Stop when the curve flattens** — diminishing returns are a signal, not a failure
6. **Review the change log periodically** — patterns reveal the search landscape

The key insight: the proposer learns from the change log. Each iteration's rationale is context for the next proposal. This is what makes LLM-driven improvement self-directed rather than random.

---

## Anti-Patterns

| Anti-pattern | Fix |
|---|---|
| No scorer — "I'll know improvement when I see it" | Define a numeric scorer before the first iteration |
| Scorer measures the wrong thing | Validate scorer on 5 known good/bad states first |
| No patience / budget cap | Always set both; add wall-clock cap as backstop |
| Discarding the change log | The log IS the research; always persist it |
| Running proposer with no log context | Pass last 5 accepted changes — proposer needs to know what worked |

---

## Retrieval Policy Self-Evolution (EvolveMem Target)

Autoresearch applies to retrieval configuration, not just code or prompts. EvolveMem (SimpleMem v3.0) is structurally identical to this loop — targeted at retrieval policy:

```
Evaluate retrieval quality (RAGAS or equivalent scorer)
    → Diagnose: which retrieval dimensions are underperforming?
    → Propose: config changes (depth, view weights, fusion constants, intent-aware settings)
    → Guard: verify no regression on prior benchmark set
    → Repeat
```

**Merge target:** run against the existing RAGAS fitness function rather than as a separate system. The scorer is already defined; the proposer targets retrieval hyperparameters instead of code artifacts.

Wire it into the standard `autoresearch` loop:

```python
scorer  = lambda cfg: ragas_eval(run_retrieval(cfg), ground_truth)
propose = lambda state: llm_propose_retrieval_config(state.current_state, state.change_log[-5:])
# loop: propose → measure → keep/discard → checkpoint
```

Key insight: EvolveMem discovers retrieval dimensions not in the original design — it is autoresearch applied reflexively to the memory/retrieval system itself. No new framework required.

### Concrete scorer design — separate scorers for code vs retrieval

Code and retrieval quality are incommensurable. Use two independent scorers; don't compose them into one number.

```python
# Code quality scorer
code_scorer = lambda cfg: (
    cfg["pass_rate"] * (1.0 - cfg["test_failure_rate"])
)

# Retrieval quality scorer (RAGAS composite)
retrieval_scorer = lambda cfg: ragas_eval(
    run_retrieval(cfg), ground_truth,
    metrics=["faithfulness", "answer_relevancy", "context_precision"]
)
```

Run EvolveMem as autoresearch on `retrieval_scorer` only. The code scorer stays on the code improvement loop. Mixing them creates a multi-objective problem that collapses signal.

**Proposer target space for retrieval evolution:**

```python
RETRIEVAL_CONFIG_SPACE = {
    "chunk_size":          [256, 512, 1024],
    "top_k":               [5, 10, 20],
    "bm25_weight":         (0.0, 1.0),      # complement = dense weight
    "reranker_threshold":  (0.0, 1.0),
    "recall_expand":       [True, False],   # memo.recall() upstream toggle
    "intent_depth":        ["shallow", "deep"],
}
```

---

## Evidence

- Karpathy autoresearch pattern (llm-wiki / nanollm-wiki, 2024)
- awesome-copilot: `autoresearch` skill
- ACE arXiv:2510.04618 — generation→reflection→curation loop, +10.6%
- SWE-RL arXiv:2502.18449 — execution-feedback RL, 41% SWE-bench Verified
- Self-debugging arXiv:2304.05128 — execution feedback loop, +12%
<!-- consolidation:see-also:start -->
## See Also
[[react-agent]]  [[stratified-quota-sampling]]  [[synthetic-data]]
<!-- consolidation:see-also:end -->
