---
name: evaluator-optimizer
description: >
  Iterative LLM-generates â†’ LLM-critiques â†’ LLM-regenerates loop. Use when
  a single generation pass is insufficient and quality must compound across
  iterations. Covers stopping criteria, prompt threading, MBR selection,
  and the distinction from offline eval pipelines. Subskill of agentic-harness.
status: active
last_validated: 2026-04-28
---

# Evaluator-Optimizer

## When to Use

Use this pattern â€” not a single generation call â€” when:

- Output quality has a well-defined rubric that an LLM can apply (code correctness, factual accuracy, style, security)
- Multiple candidate solutions should be compared and the best selected (MBR)
- A generation's failure mode can be described as text and fed back as a refinement prompt
- You are looping over code that fails tests, plans that violate constraints, or text that misses criteria

Do **not** use when:
- A single pass is already at the quality ceiling (eval returns perfect scores immediately)
- The evaluation requires execution / runtime feedback â†’ use `self-repair` instead
- You are judging a static artifact, not iterating on generation â†’ use `checklist` instead

---

## Architecture

```
â”Œâ”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”
â”‚   generator  â”‚  produces initial candidate(s)
â””â”€â”€â”€â”€â”€â”€â”¬â”€â”€â”€â”€â”€â”€â”€â”˜
       â”‚ candidates
       â–¼
â”Œâ”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”
â”‚   evaluator  â”‚  LLM-as-judge; produces structured critique + score
â””â”€â”€â”€â”€â”€â”€â”¬â”€â”€â”€â”€â”€â”€â”€â”˜
       â”‚ verdict
       â”œâ”€â”€â”€ score â‰¥ threshold  â”€â”€â–º  [accept]
       â””â”€â”€â”€ score < threshold  â”€â”€â–º  optimizer
                                       â”‚
                               â”Œâ”€â”€â”€â”€â”€â”€â”€â–¼â”€â”€â”€â”€â”€â”€â”
                               â”‚   optimizer  â”‚  synthesizes critique â†’ new prompt
                               â””â”€â”€â”€â”€â”€â”€â”€â”¬â”€â”€â”€â”€â”€â”€â”˜
                                       â”‚ refined prompt
                                       â””â”€â”€â–º generator  (next iteration)
```

The **generator**, **evaluator**, and **optimizer** can be the same model with different
prompts, or different models routed by capability. Keeping them logically separate is the
contract; the physical routing is an implementation detail.

### MBR Variant (Best-of-N)

When latency permits parallel generation:

```
generator Ã— N  (parallel)
      â”‚
      â–¼
evaluator scores all N candidates
      â”‚
      â–¼
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
    explanation: str                # â‰¤ 2 sentences; becomes optimizer context
```

**Anti-patterns:**
- Evaluator returns prose only â†’ optimizer cannot extract blocking issues reliably
- Evaluator and generator share the same system prompt â†’ evaluator inherits the generator's
  perspective and cannot critique it objectively (role contamination)
- Evaluator score always passes on round 1 â†’ rubric is too loose; tighten criteria or
  calibrate scoring against known-bad examples

---

## Evaluator Output Constraints

### Score floor

`0.0` is reserved for **empty or unparseable output only**. A non-empty, coherent response
that has flaws must receive a score â‰¥ 0.15 regardless of severity.

```python
# Required guard after every evaluator call
if score == 0.0 and len(output.split()) > 30:
    score = 0.15  # Reserve 0.0 for empty/unparseable only
```

Without this guard, small-model evaluators snap to `0.0` for any severe issue (factual
contradiction, missing required element), causing the optimizer to discard otherwise-recoverable
candidates and inflating retry counts.

### Score band documentation

Every evaluator prompt must document the scoring rubric inline. Never leave score interpretation
to the model:

```
Score guide:
0.9 = excellent, minor stylistic gaps only
0.8 = one small factual inconsistency, no major problems
0.7 = one noticeable problem that affects immersion
0.5 = multiple problems, at least one is significant
< 0.5 = direct factual contradiction or structural failure
0.0 = empty output or output that cannot be parsed
```

### Known small-model evaluator biases

Models below approximately 4B parameters exhibit **systematic biases baked into their weights**
that cannot be overridden by prompt instructions alone. These biases manifest as:

| Model size | Bias class | Symptom |
|---|---|---|
| â‰¤ 3B | Narrative voice / POV | Always flags second person; sometimes third-person omniscient as "wrong POV" |
| â‰¤ 3B | Passive voice | Penalizes all passive constructions regardless of context |
| â‰¤ 3B | Sentence length | Scores short sentences low as "incomplete"; scores long sentences low as "complex" |
| â‰¤ 3B | Dialogue tagging | Flags any non-"said" dialogue tag as an error |

**The fix is exclusion, not instruction.** Telling a small-model evaluator "do not evaluate X"
does not suppress the bias â€” the model pattern-matches on the axis regardless of instructions
and leaks the penalty into the aggregate score.

Correct approach:
```
# BAD â€” small model will still penalize POV regardless
"Evaluate the following story on: plot logic, character consistency, narrative voice."

# GOOD â€” exclude the biased axis entirely
"Evaluate the following story on: plot logic (do events follow from each other?),
character consistency (do characters act per their established traits?).
Do NOT include narrative voice, POV, sentence structure, or style in your evaluation."
```

**Detection protocol before deploying an evaluator in a retry loop:**
1. Run the evaluator on 5 known-good prose samples that vary only on the biased axis
2. If scores vary by > 0.2 across samples that differ only on the excluded axis, the bias is active
3. Remove the biased axis entirely from the rubric; handle it via a separate deterministic guard

---

## Judge Model Capability Rule

**The judge must always be more capable than the model being evaluated.**

A model cannot validate its own sufficiency. If you are testing whether a smaller or
cheaper model handles a task well enough, the verdict must come from a model that is
demonstrably stronger â€” not a peer, and never the model under test.

```
valid:     GPT-4o judges Qwen-3.5-0.8b output            âœ“
valid:     Claude Sonnet judges Haiku output              âœ“
invalid:   Qwen-3.5-0.8b judges its own output           âœ—
invalid:   Haiku judges Haiku output                      âœ—
invalid:   equal-capability model used as judge           âœ— (marginal â€” avoid)
```

This applies everywhere a model output is being scored for sufficiency:

- Harness qualification: before routing a task to a cheap model, a stronger model
  confirms its output meets the quality bar on a representative sample
- Eval pipeline: the judge LLM in the `llm_judge` scorer must outrank the system under eval
- MBR selection: if using an LLM to pick best-of-N from a cheap generator, the selector
  must be the stronger model
- `checklist` audit passes: judge model tier â‰¥ generator model tier + 1 capability level

**Practical implication for model routing:**
Using `qwen3.5:0.8b` for a task in production means a stronger model (e.g., Sonnet,
GPT-4o, or qwen2.5-coder:7b+) previously confirmed that `qwen3.5:0.8b` produced
sufficient quality on that task class. That confirmation is the prerequisite, not the
current run. Store the qualifying verdict in the harness checkpoint so it doesn't need
to be re-run on every invocation.

---

## Stopping Criteria

Stop iterating when **any** of:

| Condition | Rationale |
|---|---|
| `score >= ACCEPTANCE_THRESHOLD` | Quality criterion met |
| `delta_score < MIN_IMPROVEMENT` for N consecutive rounds | Plateau â€” further iterations will not help |
| `max_rounds` reached | Budget cap |
| Evaluator returns identical `blocking_issues` twice in a row | Generator is stuck; changing the optimizer prompt or the model is needed |

Never loop without a budget cap. Unbounded optimizer loops are the primary cause of
runaway token spend in agentic pipelines.

---

## Calibration

Before deploying the pattern to production:

1. Run the evaluator on 10 known-good and 10 known-bad examples.
2. Verify that `score â‰¥ ACCEPTANCE_THRESHOLD` separates them with < 10% error.
3. If the evaluator fails calibration, rewrite the rubric; do not tune the threshold.

---

## Integration with agentic-harness

Evaluator-optimizer is a harness **node pair**, not a full pipeline. Wire it as:

```
task_node â†’ generator_node â”€â”
                              â”œâ”€â–º evaluator_node â”€â–º optimizer_node â”€â–º generator_node (loop)
                              â””â”€â–º accept_node (on pass)
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
| Score is always 0.0 for non-empty output | Small-model snap-to-zero | Apply score floor: `max(0.15, score)` for non-empty output |
| Score varies across POV/voice-only differences | Small-model POV bias | Remove voice/POV/style axes from evaluator prompt; use deterministic pronoun-ratio guard instead |
| Evaluator penalizes correct output that contradicts its training | Baked-in small-model bias | Exclude the biased axis entirely from the rubric; validate pre-deployment (see Evaluator Output Constraints) |

---

## Evidence

- Anthropic "Building Effective Agents" (2024): evaluator-optimizer is one of five canonical agentic workflow patterns
- Self-debugging arXiv:2304.05128: +12% on TransCoder/MBPP with execution feedback loop
- MBR+DPO arXiv:2410.02902 (ICLR 2025 spotlight): best-of-N selection + offline DPO fine-tuning
- Devin TDD mode: +9.1pp SWE-bench Verified via iterative test-feedback loop (overlaps `tdd-agent`)
<!-- consolidation:see-also:start -->
## See Also
[[agentic-design-patterns]]  [[agentic_kg_memory]]  [[mcp-tool-registry]]
<!-- consolidation:see-also:end -->
