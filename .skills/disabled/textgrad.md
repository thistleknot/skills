# TextGrad Evaluation Topology

**Source:** `zou-group/textgrad` @ `75e912e210864b61999781778cdf756d4468120f`  
**Clone:** `/home/user/harness/integrate/textgrad`  
**Purpose:** A framework for treating evaluator feedback as a natural-language loss signal and then updating text, code, prompts, or other unstructured variables via textual gradients. For `agentic-harness`, the portable value is the evaluation loop: define the loss in language, separate forward and backward engines, store optimization trajectories, and treat noisy objectives with explicit hygiene.

---

## Topology Overview

```text
FORWARD LAYER ──────────────────────────────────────────────────────────────────
  candidate generator
       │
       ├── black-box LLM or prompt under test
       └── produces mutable text / code / prompt artifact

LOSS LAYER ─────────────────────────────────────────────────────────────────────
  natural-language evaluation instruction
       │
       ├── TextLoss or custom evaluator
       ├── describes what is wrong
       └── returns critique as optimization signal

BACKWARD LAYER ─────────────────────────────────────────────────────────────────
  backward engine
       │
       ├── interprets feedback as textual gradients
       ├── can be a different model from the forward engine
       └── drives update of mutable variables

OPTIMIZER LAYER ────────────────────────────────────────────────────────────────
  TGD
       │
       ├── backward()
       ├── step()
       └── repeated text-level improvement loop

OBSERVABILITY LAYER ────────────────────────────────────────────────────────────
  predictions + loss_history + trajectories
       │
       ├── optimization path is retained
       ├── noisy objectives acknowledged explicitly
       └── final prediction may use majority vote
```

---

## Feature Inventory

### NATURAL-LANGUAGE LOSS FUNCTIONS

**`TextLoss`**  
The evaluation objective is written in natural language rather than as a scalar-only hand-coded function. Feedback is concise, critical, and directly about what to change.

**Migration value:** highest-priority. This is the cleanest pattern for harness stages where deterministic metrics are weak but critique can still be precise.

### TEXTUAL-GRADIENT UPDATE LOOP

**`TGD` optimizer`**  
TextGrad mirrors the PyTorch shape: define variables, compute loss, run `backward()`, then `step()`.

**`requires_grad` for unstructured artifacts`**  
Prompts, answers, code snippets, and other text artifacts become explicitly mutable evaluation targets.

**Migration value:** very high. This maps cleanly onto prompt, code, and solution refinement inside a harness.

### SEPARATE FORWARD AND BACKWARD ENGINES

**`BlackboxLLM` for generation`**  
One model can produce the candidate artifact.

**`set_backward_engine(...)` for critique`**  
A separate evaluator model can generate the gradient-like feedback signal.

**Migration value:** high. This supports cleaner generator/critic separation in `agentic-harness`.

### TRAJECTORY + LOSS HISTORY AS FIRST-CLASS ARTIFACTS

**`predictions` trajectory`**  
Released evaluation artifacts include intermediate candidate trajectories, not just the final answer.

**`loss_history`**  
Optimization history is preserved explicitly.

**Migration value:** high. Harness evaluation should preserve the path of improvement, not just the end verdict.

### NOISY-OBJECTIVE HYGIENE

**`multi-seed averaging`**  
TextGrad’s code-optimization evaluation notes that small code changes can produce unstable scores, so results are run across multiple seeds and averaged.

**`majority-vote final prediction`**  
For solution optimization, the released results note that objectives can encourage exploration, so final predictions may use majority voting.

**Migration value:** very high. This is directly relevant to harness eval design whenever scores are noisy or exploratory objectives distort a single-run answer.

### SAFETY + TRANSPARENCY IN CODE EVALUATION

**`sandbox warning for generated code`**  
The evaluation docs explicitly warn that running untrusted model-generated code requires a robust sandbox.

**`limitations documented alongside results`**  
The repo foregrounds instability, network/rate-limit issues, and evaluator caveats rather than hiding them.

**Migration value:** very high. `agentic-harness` should treat optimizer-style code evaluation as dangerous and noisy by default.

---

## Harness Adaptation Notes

### WHAT TEXTGRAD CONTRIBUTES TO `agentic-harness`

Use TextGrad-style patterns when:

1. the evaluator needs to explain what to improve in natural language
2. the optimized object is text/code/prompt-like rather than a clean numeric parameter vector
3. you want a generator/critic split with explicit trajectory retention

### WHAT NOT TO COPY BLINDLY

- Do not confuse textual feedback with final acceptance.
- Do not trust one optimization run on a noisy objective.
- Do not run code-eval loops outside a safety envelope.

---

## Bottom Line

**Bottom line:** TextGrad contributes the **textual-loss evaluation loop** for `agentic-harness`: critique as loss, backward-model feedback, explicit mutable text variables, trajectory retention, and noisy-objective hygiene. It is the right complement to metric-first evaluation, not a replacement for it.
