---
name: prompt-optimization
description: >
  Systematic prompt quality improvement via DSPy (trace-guided compilation),
  TextGrad (text-space gradient descent), OPRO (meta-prompting), ProTeGi
  (error-case textual gradients), and APE (candidate generation). Use when a
  multi-step LLM pipeline degrades, a specific output quality must compound
  across iterations, or you have labeled training data and need prompts that
  maximize a metric. Distinct from evaluator-optimizer (single critique loop
  on one generation) and autoresearch (arbitrary metric hill-climbing over code
  or configs).
status: active
last_validated: 2026-05-07
absorbs: [integrate/dspy.md, integrate/textgrad.md]
---

# Prompt Optimization

## When to Use

Use prompt-optimization — not a single generation call or evaluator-optimizer — when:

- You have a **multi-step LLM pipeline** (RAG, agent loop, multi-hop QA) where
  modules share credit and individual prompts are hard to tune independently
- You have **labeled (input, expected_output) pairs** and a metric function,
  and want prompts that maximize the metric automatically
- The **task framing is wrong** and demos alone won't fix it (instruction rewrite needed)
- Output quality degrades after switching LLMs (DSPy BootstrapFewShot re-adapts)
- You want to **polish a single output** without a training set (TextGrad)
- You want zero-shot improvement from a history of scored attempts (OPRO)

Do **not** use when:
- A single-pass evaluator-optimizer loop (generate→critique→fix) is enough
- The prompt is already at the quality ceiling (run a baseline score first)
- You are judging a static artifact, not iterating on generation → use `checklist`
- Token budget is very tight and no training set exists → use `response-style` instead

---

## Strategy Selection

```
Agent observes prompt quality degrading
         │
         ├─► Have 20+ labeled (input, expected_output) pairs?
         │           │
         │     YES ──┼─► Multi-step pipeline (RAG, tool-use, reasoning chain)?
         │           │           │
         │           │     YES ──┴─► Use MIPROv2 (budget=light first)
         │           │               lib: dspy + dspy[optuna]
         │           │
         │           │     NO ───► Single instruction / classifier?
         │           │               ├─ Error-case diagnosis needed → ProTeGi
         │           │               └─ Instruction rewrite only → COPRO
         │
         └─► No labeled data?
                     │
               ──────┼──────────────────
               │                        │
         Have a natural-           Have 5-10 (input,output)
         language loss fn          demo examples only
         (e.g. "evaluate …")
               │                        │
               └─► TextGrad             └─► APE (generate candidates)
                   (per-output polish)       then OPRO (score+refine)
```

**Composition pattern (best results):**
`APE (seed instruction) → BootstrapFewShot (add demos) → MIPROv2 (joint) → TextGrad (per-output polish)`

---

## Core Approaches

### 1. DSPy — Declarative Self-Improving Python
**arXiv:** `2310.03714` (ICLR 2024); Assertions: `2312.13382`; MIPRO: `2406.11695`
**Library:** `pip install dspy dspy[optuna]`
**Repo:** `stanfordnlp/dspy` (active, May 2026)

DSPy replaces hand-written prompt strings with typed `Signature` objects and
`Module` subclasses. A **Teleprompter (optimizer)** compiles the program — running
it against a training set and automatically populating demonstrations and/or
instructions to maximize the metric.

**Three key optimizers:**

| Optimizer | Tunes | Strategy |
|---|---|---|
| BootstrapFewShot | Demos only | Execute teacher → keep passing traces |
| COPRO | Instructions only | LLM proposes candidates; beam search (breadth×depth) |
| **MIPROv2** *(SOTA)* | Instructions + demos jointly | Bayesian search (Optuna TPE) over candidates; `auto=light/medium/heavy` |

**Assertions** (`dspy.Assert` / `dspy.Suggest`) embed hard/soft constraints in the
forward pass. Failed assertions trigger self-refinement retry loops during compilation.

```python
import dspy
from dspy.teleprompt import MIPROv2

# Define your pipeline module
class RAGModule(dspy.Module):
    def __init__(self):
        self.retrieve = dspy.Retrieve(k=3)
        self.generate = dspy.ChainOfThought("context, question -> answer")

    def forward(self, question):
        context = self.retrieve(question).passages
        return self.generate(context=context, question=question)

# Compile with MIPROv2 (light budget = 6 candidate programs)
teleprompter = MIPROv2(metric=exact_match, auto="light")
optimized = teleprompter.compile(RAGModule(), trainset=trainset)
```

**Limitations:**
- Requires a fast, cheap metric evaluation (token cost = n_candidates × dev_size)
- Demo injection inflates context length for weak models
- Cold-start: BootstrapFewShot degrades when the teacher model is weak

---

### 2. TextGrad — Text-Space Gradient Descent
**arXiv:** `2406.07496` (Nature 2025: `10.1038/s41586-025-08661-4`)
**Library:** `pip install textgrad`
**Repo:** `zou-group/textgrad` (active, Jul 2025)

TextGrad implements a computational graph where edges are LLM calls. The
**backward pass** asks a critic LLM to produce a textual gradient — a
natural-language critique explaining *why* the loss is high and *how* the
variable should change. The optimizer (`TGD`) rewrites the variable using
that feedback (mirroring `x ← x − α∇L`).

```python
import textgrad as tg

model = tg.BlackboxLLM("gpt-4o")
question = tg.Variable(question_text, role_description="question")
answer = model(question)

loss_fn = tg.TextLoss("Evaluate the answer for accuracy and completeness.")
loss = loss_fn(answer)
loss.backward()   # critic writes natural-language gradient into answer.grad
optimizer = tg.TGD(parameters=[answer])
optimizer.step()  # rewrites answer.value using gradient feedback
```

**Best for:** Polishing single outputs (code review, answer refinement, molecule
design) when no training set exists. Two LLM calls per backward step per variable.

**Limitations:**
- Very high API cost: 2+ backward calls per variable per step
- Optimization is non-deterministic; no convergence guarantee
- Requires a powerful critic model (GPT-4o used in all benchmarks)

---

### 3. OPRO — Optimization by Prompting
**arXiv:** `2309.03409` (ICLR 2024)
**Repo:** `google-deepmind/opro` (reference impl, no package)

Frames optimization as in-context meta-prompting: the LLM receives a meta-prompt
containing the task description plus a history of scored solution attempts
(ascending by score). Generates new candidates from this context.

**Best for:** Single flat instruction optimization; zero-training-set improvement
when only a scoring function exists; non-text objectives (routing, TSP) alongside prompts.

**Limitations:** Context window grows with history; plateau tendency without
diversity mechanisms; no multi-module support.

---

### 4. ProTeGi / APO — Error-Case Textual Gradients
**arXiv:** `2305.03495` (EMNLP 2023)
**Repo:** `microsoft/LMOps/prompt_optimization/`

Samples error cases, asks LLM for `n_feedbacks` natural-language critiques of
why those cases failed, then rewrites the prompt in the opposite direction.
Beam search over candidates across gradient steps.

**Best for:** Binary/multi-class classification prompt optimization with labeled
training data; when interpretable "why did this fail?" diagnostics are needed.

**Limitations:** Gradient vanishes when accuracy > 90% (too few errors); single-prompt only.

---

### 5. APE — Automatic Prompt Engineer
**arXiv:** `2211.01910` (ICLR 2023)

Given a few (input, output) demos, a proposer LLM generates a pool of candidate
instruction strings. Each is scored on a held-out set. Best candidate selected.

**Best for:** Bootstrapping a task instruction from a handful of examples when
no metric/training-set exists. Use as first step before MIPRO or OPRO refinement.

---

## Interface Contract

```python
from dataclasses import dataclass
from typing import Callable, Literal, Any
from enum import Enum

class OptimizationStrategy(Enum):
    BOOTSTRAP_FEWSHOT   = "bootstrap_fewshot"
    INSTRUCTION_REWRITE = "instruction_rewrite"  # COPRO / MIPRO
    TEXTGRAD            = "textgrad"
    OPRO_META           = "opro_meta"

@dataclass
class PromptOptimizationInput:
    # REQUIRED
    program: Any                    # dspy.Module, textgrad graph, or callable
    metric: Callable                # metric(example, prediction) -> float | bool

    # CONDITIONALLY REQUIRED
    trainset: list[Any] | None = None   # Required for BootstrapFewShot, COPRO, MIPRO
    loss_fn: Callable | None = None     # Required for TextGrad

    # CONFIGURATION
    strategy: OptimizationStrategy | None = None  # None = auto-detect
    budget: Literal["light", "medium", "heavy"] = "light"
    seed: int = 42

@dataclass
class PromptOptimizationOutput:
    optimized_program: Any
    best_score: float
    score_history: list[float]
    optimized_instructions: dict[str, str]  # module_name -> instruction
    demos_injected: dict[str, int]
    total_lm_calls: int
    optimization_log: list[dict]
    warnings: list[str]
```

**Auto-detection logic:**
- `trainset` provided + `dspy.Module` → MIPROv2
- `trainset` provided + callable prompt → ProTeGi / COPRO
- No `trainset` + `loss_fn` provided → TextGrad
- No `trainset` + no `loss_fn` → APE

---

## Cost Envelope

| Method | LM calls per iteration | Total budget (light) |
|---|---|---|
| BootstrapFewShot | `O(trainset × traces)` | ~trainset_size |
| MIPROv2 light | `6 × val_size` candidates | ~6×50 = 300 calls |
| TextGrad | `2 × n_vars × n_steps` | ~2×1×5 = 10 calls |
| ProTeGi | `beam × n_feedbacks × rounds` | ~3×4×3 = 36 calls |

**Always estimate cost before running.** Surface estimated call count to user.

---

## Key Rules

1. **Run a baseline score first** — if already > 90% accurate, gradient vanishes. Stop.
2. **The metric is the highest-leverage component** — store it as a named, versioned artifact.
3. **Persist the optimization_log** — future runs warm-start from prior history (especially OPRO).
4. **Compose, don't replace** — optimal pipeline: APE → BootstrapFewShot → MIPROv2 → TextGrad.
5. **Budget token cost explicitly** — unbounded optimization loops are runaway token spend.

---

## Integration with Skill Library

| Phase | Skill |
|---|---|
| Single generate→critique→fix loop | `evaluator-optimizer` |
| Score via test execution | `tdd-agent` (pass rate as metric) |
| Score via LLM judge | `checklist` |
| Autonomous search over multiple dimensions | `autoresearch` |
| Multi-step pipeline routing | `agentic-harness` |
| Tracking experiment runs | `mlflow` |

---

## Evidence

- DSPy arXiv:2310.03714 (ICLR 2024): +20-50% on multi-step pipelines vs. human-written prompts
- MIPROv2 arXiv:2406.11695 (EMNLP 2024): joint instruction+demo search via Bayesian optimization
- TextGrad arXiv:2406.07496 (Nature 2025): 20-point improvement on solution optimization tasks
- OPRO arXiv:2309.03409 (ICLR 2024): up to +8% GSM8K, +50% BBH over human prompts
- ProTeGi arXiv:2305.03495 (EMNLP 2023): beam-search over error-case textual gradients
- APE arXiv:2211.01910 (ICLR 2023): better or equal to human instructions on 19/24 NLP tasks
- `stanfordnlp/dspy` (active): `pip install dspy dspy[optuna]`
- `zou-group/textgrad` (active): `pip install textgrad`
<!-- consolidation:see-also:start -->
## See Also
[[synthetic-data]]  [[hyper-parm_tuning]]  [[react-agent]]
<!-- consolidation:see-also:end -->
