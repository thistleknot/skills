---
name: evaluator-optimizer
description: >
  Iterative LLM-generates → LLM-critiques → LLM-regenerates loop. Use when
  a single generation pass is insufficient and quality must compound across
  iterations. Covers stopping criteria, prompt threading, MBR selection,
  and the distinction from offline eval pipelines. Subskill of agentic-harness.
status: active
last_validated: 2026-04-28
---

# Evaluator-Optimizer

## When to Use

Use this pattern — not a single generation call — when:

- Output quality has a well-defined rubric that an LLM can apply (code correctness, factual accuracy, style, security)
- Multiple candidate solutions should be compared and the best selected (MBR)
- A generation's failure mode can be described as text and fed back as a refinement prompt
- You are looping over code that fails tests, plans that violate constraints, or text that misses criteria

Do **not** use when:
- A single pass is already at the quality ceiling (eval returns perfect scores immediately)
- The evaluation requires execution / runtime feedback → use `self-repair` instead
- You are judging a static artifact, not iterating on generation → use `checklist` instead

---

## Architecture

```
┌──────────────┐
│   generator  │  produces initial candidate(s)
└──────┬───────┘
       │ candidates
       ▼
┌──────────────┐
│   evaluator  │  LLM-as-judge; produces structured critique + score
└──────┬───────┘
       │ verdict
       ├─── score ≥ threshold  ──►  [accept]
       └─── score < threshold  ──►  optimizer
                                       │
                               ┌───────▼──────┐
                               │   optimizer  │  synthesizes critique → new prompt
                               └───────┬──────┘
                                       │ refined prompt
                                       └──► generator  (next iteration)
```

The **generator**, **evaluator**, and **optimizer** can be the same model with different
prompts, or different models routed by capability. Keeping them logically separate is the
contract; the physical routing is an implementation detail.

### MBR Variant (Best-of-N)

When latency permits parallel generation:

```
generator × N  (parallel)
      │
      ▼
evaluator scores all N candidates
      │
      ▼
MBR selector: argmax(score) or consensus vote
```

MBR+DPO (arXiv:2410.02902, ICLR 2025 spotlight): generate N candidates, score with a
reward model or LLM judge, select the best, then use the best/worst pair as a DPO
training signal. Yields consistent downstream quality improvements without extra inference
at deploy time.

---

## Prompt Threading

The critique from the evaluator **must** be carried into the optimizer's prompt. This is
the load-bearing mechanism. A critique that gets dropped or summarised too aggressively
causes the generator to repeat the same mistake.

```python
# Minimal threading contract
def optimization_round(generator, evaluator, optimizer, task: str, max_rounds: int = 5):
    """
    Require: task is a complete problem statement; generator/evaluator/optimizer are callable(str) -> str.
    Guarantee: returns the highest-scoring output seen across all rounds.
    Maintain: full critique chain is carried forward each round.
    """
    history: list[dict] = []
    best_output, best_score = "", 0.0

    prompt = task
    for round_num in range(max_rounds):
        output = generator(prompt)
        critique, score = evaluator(task, output)

        if score > best_score:
            best_output, best_score = output, score

        history.append({"round": round_num, "output": output, "critique": critique, "score": score})

        if score >= ACCEPTANCE_THRESHOLD:
            break

        # Thread the full critique history into the next prompt
        critique_context = "\n".join(
            f"[Round {h['round']}] Score: {h['score']:.2f}\nCritique: {h['critique']}"
            for h in history
        )
        prompt = f"{task}\n\n## Previous Attempts\n{critique_context}\n\nProduce a new solution that addresses all critiques."

    return best_output, history
```

---

## Evaluator Design Contract

The evaluator prompt must return a **structured verdict**, not prose:

```python
class EvalVerdict(BaseModel):
    score: float                    # [0.0, 1.0]
    passed: bool                    # score >= threshold
    criteria: list[CriterionResult] # per-criterion breakdown
    blocking_issues: list[str]      # must-fix items fed to optimizer
    suggestions: list[str]          # nice-to-fix items

class CriterionResult(BaseModel):
    name: str
    passed: bool
    explanation: str                # ≤ 2 sentences; becomes optimizer context
```

**Anti-patterns:**
- Evaluator returns prose only → optimizer cannot extract blocking issues reliably
- Evaluator and generator share the same system prompt → evaluator inherits the generator's
  perspective and cannot critique it objectively (role contamination)
- Evaluator score always passes on round 1 → rubric is too loose; tighten criteria or
  calibrate scoring against known-bad examples

---

## Stopping Criteria

Stop iterating when **any** of:

| Condition | Rationale |
|---|---|
| `score >= ACCEPTANCE_THRESHOLD` | Quality criterion met |
| `delta_score < MIN_IMPROVEMENT` for N consecutive rounds | Plateau — further iterations will not help |
| `max_rounds` reached | Budget cap |
| Evaluator returns identical `blocking_issues` twice in a row | Generator is stuck; changing the optimizer prompt or the model is needed |

Never loop without a budget cap. Unbounded optimizer loops are the primary cause of
runaway token spend in agentic pipelines.

---

## Calibration

Before deploying the pattern to production:

1. Run the evaluator on 10 known-good and 10 known-bad examples.
2. Verify that `score ≥ ACCEPTANCE_THRESHOLD` separates them with < 10% error.
3. If the evaluator fails calibration, rewrite the rubric; do not tune the threshold.

---

## Integration with agentic-harness

Evaluator-optimizer is a harness **node pair**, not a full pipeline. Wire it as:

```
task_node → generator_node ─┐
                              ├─► evaluator_node ─► optimizer_node ─► generator_node (loop)
                              └─► accept_node (on pass)
```

Use `agentic-harness` routing state to track `round_count`, `best_score`, and
`blocking_issues`. Store each round's critique in `learnings.jsonl` for Pattern Store
vetting (see `skill-wiki`).

---

## Failure Modes

| Symptom | Root cause | Fix |
|---|---|---|
| Optimizer produces same output each round | Critique not threaded | Verify full critique history appears in optimizer prompt |
| Score never improves past round 1 | Role contamination | Use separate system prompts for generator and evaluator |
| Plateau after 2 rounds | Rubric too vague | Add concrete pass/fail criteria with examples |
| Token spend explodes | No max_rounds cap | Always set `max_rounds`; log tokens per round |
| Best-of-N always picks first candidate | Evaluator scores all N equally high | Re-calibrate evaluator; introduce contrastive examples |

---

## Evidence

- Anthropic "Building Effective Agents" (2024): evaluator-optimizer is one of five canonical agentic workflow patterns
- Self-debugging arXiv:2304.05128: +12% on TransCoder/MBPP with execution feedback loop
- MBR+DPO arXiv:2410.02902 (ICLR 2025 spotlight): best-of-N selection + offline DPO fine-tuning
- Devin TDD mode: +9.1pp SWE-bench Verified via iterative test-feedback loop (overlaps `tdd-agent`)
