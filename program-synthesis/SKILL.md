---
name: program-synthesis
description: >
  LLM-guided formal verification and specification-first code synthesis. Three
  production targets: Verus (Rust ghost specs via AutoVerus), Dafny (SMT-backed
  pre/postconditions), and Lean 4 (theorem proving via LeanDojo/ReProver). Covers
  the AutoVerus 3-phase generate-refine-debug agent loop, EvalPlus test-coverage
  gap diagnosis, and the RLEF training protocol. Use when correctness must be
  proved for all inputs, not just tested on sampled ones. Escalation point for
  tdd-agent on safety-critical, unbounded, or concurrent correctness properties.
status: active
last_validated: 2026-05-07
---

# Program Synthesis

## When to Use

Use program-synthesis — not tdd-agent — when:

- Correctness must hold **for all inputs** (unbounded quantification), not just sampled tests
- The property involves **security invariants**: no overflow, no out-of-bounds, no injection
- **Concurrent/parallel code** requires data-race freedom or deadlock freedom
- A cryptographic primitive, memory allocator, or OS-level component requires proof-bounded correctness
- **EvalPlus-style test augmentation still fails**: 3+ hypothesis failures in `debugging` suggest a structural issue
  that tests cannot characterize
- The target is Rust, Dafny, or Lean (tooling mature) and spec can be expressed as pre/postconditions

Do **not** use when:
- UI, integration, or performance behavior is the target → use `tdd-agent`
- The target language has no mature formal verification tooling
- Property is too complex for current SMT solvers (check solver timeout first)
- Rapid exploration/prototype phase → use `tdd-agent`, escalate here only on stabilization

---

## The Correctness Gap

`tdd-agent` stops when tests pass. **EvalPlus** (arXiv:`2305.01210`, NeurIPS 2023) showed
that augmenting HumanEval with 80× more test cases causes pass@k to drop **19–28%** —
tests frequently don't cover the actual correctness condition.

```
debugging:          symptom → root cause → patch         (reactive, test-anchored)
tdd-agent:          spec → tests → implementation        (proactive, test-bounded)
program-synthesis:  spec/type → verified impl            (proactive, proof-bounded)
```

Some correctness properties **cannot be expressed as finite tests**:
- "Correct for all arrays of length n" (unbounded)
- "No integer overflow occurs" (requires symbolic reasoning)
- "This concurrent code has no data races" (requires temporal reasoning)

---

## Escalation Protocol from tdd-agent

```
tdd-agent (default path)
    │
    └─ escalate_to_program_synthesis when:
         ├─ safety-critical path: crypto, parser, allocator, OS primitive
         ├─ correctness is universally quantified ("for all inputs")
         ├─ 3+ debugging hypothesis failures suggest structural issue
         ├─ spec naturally expressed as pre/postcondition or refinement type
         └─ target language is Rust, Dafny, or Lean 4
```

---

## Three Formal Verification Targets

### 1. Verus + AutoVerus (Rust) — RECOMMENDED STARTING POINT
**AutoVerus arXiv:** `2409.13082` (OOPSLA 2025)
**Key advantage:** Verus uses Rust syntax for ghost code — no new language for the LLM.

**AutoVerus 3-phase agent loop:**

```
Phase 1: Generation
  LLM generates 5 candidate proofs (LoopInvAgent)
  AST filter: remove unsafe modifications (Lynette tool)
  Rank by {V=verified functions, E=errors}
  Merge best loop invariants via Houdini algorithm

Phase 2: Refinement (4 specialist agents in sequence)
  ConstantPropagation → ArrayLength → Quantifier → ConditionalLoopInvariant

Phase 3: Debugging (10 error-specific repair agents, priority-ordered)
  TypeError ≻ BoundErrors ≻ InvariantErrors ≻ ...
  Houdini minimization removes unnecessary annotations
```

**Results on Verus-Bench (150 tasks):**
| Source | Tasks | AutoVerus | Baseline (30s) |
|---|---|---|---|
| Diffy | 38 | **100%** | 5/38 |
| CloverBench | 11 | **100%** | 8/11 |
| MBPP | 78 | 87% | 43/78 |
| Total | 150 | **91.3%** | ~44% |

Cost: ~$37 for all 150 tasks (GPT-4o). Works across GPT-4o, GPT-4-turbo, DeepSeek-R1.

**SAFE extension** (Chen et al., ICLR 2025): fine-tune open-source LLMs on synthetic
Verus proof data via self-evolution (RLEF feedback). Lifts open models from 14% → 52.5%.

```rust
// Example: Verus ghost spec for a sort function
fn sort(v: &mut Vec<i32>)
    ensures
        v.len() == old(v).len(),
        forall |i: int, j: int| 0 <= i <= j < v.len() ==> v[i] <= v[j],
{}
```

---

### 2. Dafny + LLM

**DafnyBench arXiv:** `2406.08467` (2024)
750+ programs, ~53K lines. Best model (GPT-4 + prompting): **68% success rate**.
Error feedback retries improve results. Open: `github.com/sun-wendy/DafnyBench`.

**Laurel** (Mugnier et al., UCSD): unblocks ~45–60% of stalled Dafny proofs by
automatically generating intermediate assertions for the SMT solver (Z3).

**LLM-to-Dafny pattern:**
```python
# Generate pre/postconditions from natural language intent
# Feed to Dafny verifier; collect error messages
# Retry with error context (up to N iterations)
# Exit when verified or when retry budget exhausted
```

**Key finding** (Lahiri, MSFT): LLMs are better at generating *implementations from
specs* than generating *specs from natural-language intent*. Always provide or
validate the Dafny spec before generating the implementation.

---

### 3. Lean 4 + LeanDojo
**arXiv:** `2306.15626` (NeurIPS 2023, oral)
**Code/data:** `leandojo.org` (MIT license)

ReProver (retrieval-augmented theorem prover): 26.5% pass on miniF2F benchmark.
Trained on 98,734 theorems/proofs from Lean's mathlib. Strong for mathematical
reasoning properties.

**When to choose Lean over Verus/Dafny:** Mathematical proofs of algorithm correctness;
type-theoretic specifications; when the target has a mathlib formalization.

---

## RLEF — Closing the Training Loop
**arXiv:** `2410.02089` (Meta/FAIR, 2024)

RLEF trains code LLMs to **leverage execution feedback across multiple steps** (not
just independent sampling):
- Model interprets error messages and produces targeted repairs across turns
- New SOTA on CodeContests with 8B and 70B models
- Reduces required samples by **10× vs. independent sampling**

**Relationship to existing skills:** RLEF trains the *base capability* that the
`debugging` self-repair protocol relies on at inference time. The `debugging` skill
describes the inference protocol; RLEF describes how to train a model that executes
it better.

---

## Invoke Formal vs. Empirical Decision Table

| Signal | Use formal verification | Use tests only |
|---|---|---|
| Unbounded quantification | ✅ Required | ❌ Insufficient |
| Security invariant (no overflow, injection) | ✅ Required | ❌ Insufficient |
| Concurrent code correctness | ✅ Required | ❌ Insufficient |
| Performance / latency | ❌ Tests + benchmarks | ✅ |
| UI / integration behavior | ❌ Too complex for SMT | ✅ |
| Rapid prototype | ❌ Heavyweight | ✅ |
| Core algorithm kernel | ✅ Formally verify kernel | ✅ TDD the wiring |

---

## Interface Contract

```yaml
inputs:
  target_code: str               # function or module to verify
  specification: str             # pre/postconditions, invariants, or intent
  target_language: rust | dafny | lean
  verifier: verus | dafny | lean4
  method: autoVerus | dafny_retry | lean_reprover
  max_iterations: int            # retry budget (default: 10)
  model: str                     # LLM to use (default: gpt-4o)

outputs:
  verified: bool
  proof_artifact: str            # generated ghost spec / proof obligations
  verification_time_s: float
  error_trace: list[str]?        # if not verified: error messages per attempt
  iterations_used: int

preconditions:
  - verifier binary is available in PATH (verus, dafny, or lean4)
  - specification is provided or derivable from function signature + docstring
  - target_code compiles without errors before verification

postconditions:
  - if verified=True: proof_artifact passes verifier with zero errors
  - if verified=False: error_trace contains final SMT error or counterexample
  - never returns verified=True without a passing verifier run

invariants:
  - Houdini minimization runs after verification (remove unnecessary annotations)
  - specialist error-repair agents are dispatched by error type priority
```

---

## Practical Workflow

```python
def synthesize_with_verification(
    code: str,
    intent: str,
    language: str = "rust",
    max_iter: int = 10,
    llm_fn: Callable,
    verifier_fn: Callable,  # subprocess call to verus/dafny/lean
) -> dict:
    """
    Require: code compiles; intent is a natural-language correctness claim.
    Guarantee: returns verified proof artifact or error trace after max_iter.
    Maintain: each iteration uses previous error trace as context.
    """
    spec = llm_fn(f"Write Verus pre/postconditions for:\n{code}\nIntent: {intent}")
    for i in range(max_iter):
        annotated = llm_fn(f"Annotate this code with the spec:\n{spec}\n\n{code}")
        result = verifier_fn(annotated)
        if result.verified:
            return {"verified": True, "proof": annotated, "iterations": i + 1}
        # Error-type-specific repair agent
        repair_prompt = route_error_repair_agent(result.errors)
        code = llm_fn(repair_prompt + f"\n\nCurrent code:\n{annotated}")
    return {"verified": False, "error_trace": result.errors, "iterations": max_iter}
```

---

## Integration with Skill Library

| Context | Skill |
|---|---|
| Default feature/bugfix work | `tdd-agent` (escalate here only on formal properties) |
| Symptom-driven root cause | `debugging` |
| Generate synthetic Verus proof training data | `synthetic-data` (SAFE pattern) |
| Fine-tune model on proof data | `continual-learning` (RLEF) |
| Evaluate correctness coverage | `uncertainty-quantification` (EvalPlus gap diagnosis) |
| Spec + proof as architecture contract | `architecture` (Require/Guarantee/Maintain) |

---

## Evidence

- Liu et al. arXiv:2305.01210 (NeurIPS 2023): EvalPlus — pass@k drops 19–28% with exhaustive testing
- Yang et al. arXiv:2306.15626 (NeurIPS 2023 oral): LeanDojo/ReProver, 26.5% miniF2F
- Yao et al. arXiv:2311.03739: LLM-assisted Rust/Verus proof synthesis, significant effort reduction
- Yang et al. arXiv:2409.13082 (OOPSLA 2025): AutoVerus 91.3% on 150-task bench, $37 total
- Loughridge et al. arXiv:2406.08467: DafnyBench 68% success with GPT-4 + retry
- Jimenez et al. arXiv:2310.06770 (ICLR 2024): SWE-bench — tests pass ≠ correctness
- Gehring et al. arXiv:2410.02089: RLEF, 10× fewer samples on competitive programming
- Chen et al. ICLR 2025 (SAFE): open-source LLM 14% → 52.5% on Verus via self-evolution
- `evalplus/evalplus`: `pip install evalplus` — HumanEval+, MBPP+
<!-- consolidation:see-also:start -->
## See Also
<!-- consolidation:see-also:end -->
