---
name: neurosymbolic
description: >
  Use when a task needs both neural pattern intuition and symbolic
  exactness/interpretability -- abstract reasoning (ARC-style), program or
  library synthesis, sample-efficient learning where a black-box model would be
  opaque or data-hungry. Combines LLM-guided generation with symbolic
  compression, algebra, or verification so the result is both learned and
  auditable.
status: active
last_validated: 2026-07-27
---

# Neurosymbolic

Distilled from arXiv 2310.19791 (LILO), 2508.03682 (Self-Questioning LMs),
2511.08747 (Vector Symbolic Algebras for ARC-AGI), 2511.18423 (agentic memory
via deep research).

## When to Use

- The task rewards *interpretability and sample efficiency*, and a pure neural
  model would be opaque, data-hungry, or unable to justify its steps
  (abstract-reasoning corpora, program induction).
- You can factor the problem into a neural part (propose / intuit) and a symbolic
  part (compress, bind, verify, refactor).
- You want a reusable, documented library of abstractions to grow over time
  rather than a one-off model.

**Do NOT use when** a plain neural model already clears the bar cheaply, or when
no symbolic structure exists to exploit. Current neurosymbolic ARC solvers still
score low on the hard eval sets (10.8% ARC-AGI-1-Train, 3.0% Eval per 2511.08747)
-- do not reach for this expecting human-level abstract reasoning.

## Core Concepts

- **Synthesize -> compress -> document loop (LILO, 2310.19791).** Iterate:
  LLM-guided program synthesis proposes solutions; a *symbolic* compressor
  (Stitch-style lambda-abstraction mining) refactors shared structure into a
  library; an auto-documentation pass infers natural-language names and
  docstrings from usage so the abstractions are human-readable and reusable by
  the synthesizer next round. This beats either neural or symbolic alone on
  string editing, scene reasoning, graphics composition.

- **Vector Symbolic Algebras (VSA) (2511.08747).** Represent objects and
  relations as high-dimensional vectors with algebraic bind/bundle/unbind
  operations. Gives a cognitively plausible, interpretable substrate for
  object-centric program synthesis at a fraction of a large-LLM's compute cost
  -- bridging System-1 intuition and System-2 reasoning.

- **Self-questioning as data-free self-play (2508.03682).** The model generates
  its own problems and solutions, improving via RL/self-play with majority-vote
  or unit-test verification as the correctness proxy -- symbolic verification
  standing in for absent labels. Caveat: majority voting is an imperfect oracle;
  no guarantee outside the practiced benchmark.

## Protocol

```
neurosymbolic_solve(domain, tasks):
    lib <- {}                              # symbolic library of abstractions
    repeat:
        cand   <- neural_propose(tasks, lib)   # LLM guided by current library
        checked<- symbolic_verify(cand)        # unit tests / algebra / solver
        reused <- symbolic_compress(checked)   # mine shared lambda abstractions
        lib    <- lib + document(reused)       # NL names + docstrings from usage
    return lib, solutions(checked)
```

Failure modes to keep visible: symbolic compression can be compute-heavy over
large corpora; VSA solvers remain far from human ARC performance; self-questioning
can drift when the verifier is weak.

## Related

`kg_ontology` and `agentic_kg_memory` (SPO/FOL symbolic layer), `reasoning`
(hypothesis ranking), `active-inference` (System-1/System-2 framing).
