# Glossary — defined terms, and the intent behind them

<!-- NO GOVERNING SPEC. Basis: operator instruction 2026-09-12 — "create a glossary in
     ~\.skills that is referenced by ~\.claude and ~\.harness", after an AI session
     invented the expansion "Synthetic Pair Optimization" for an undefined overloaded
     "SPO" and wrote it into validation-artifacts/SKILL.md as fact. Carrying the
     operator's objective intent forward is an explicit requirement of that instruction,
     not an embellishment. Promote to a REQ before anything depends on this file. -->

## The rule

**An acronym in this table is written out on first use in every file that uses it.**

An acronym that is neither in this table nor expanded in its own file is a **defect**.
The move is to add the row — never to guess. An unresolvable acronym is a question to the
operator, not a gap to fill. A fabricated expansion is worse than an unexpanded one:
unexpanded stays visibly unknown, fabricated becomes load-bearing and propagates.

**Carry the intent, not just the letters.** Every row records what the operator was
*trying to do* when they used the term. The SPO incident happened because a reader knew
the letters were ambiguous and still could not tell which job the term was doing. The
intent column is what makes the disambiguation decidable at the next call site.

## Overloaded — must be disambiguated at every use

| Term | Authoritative meanings | Objective intent — what it is doing when used | Rejected / do not use |
|---|---|---|---|
| **SPO** | **(A)** subject-predicate-object — KG triplets, incl. the `spo_score` record-quality field. **(B)** soft policy optimization — offline preference optimization, `deep-q-rl`. | **A:** scoring and gating extracted premise triplets so only well-formed, entailed records enter a training set. Owner: `agentic_kg_memory`, `request-intent-resolution`, `integrate/two skills.md`. **B:** fine-tuning a model against pre-computed reward without a live simulator. Owner: `deep-q-rl`. | ❌ **"Synthetic Pair Optimization"** — not a term in any literature. Invented by an AI session from the phrase "synthetic paired data" in surrounding body text, then defended with a fabricated acronym note. **Reject on sight.** |
| **k / K** | **(A)** `score_arms --k`: samples per EVAL question. **(B)** GRPO group size (rollouts per record), written K. **(C)** count correct out of K, in the Beta posterior `a=1+k, b=1+(K-k)`. | **A:** how many times each of the 16 eval questions is answered; k=1 means one lucky draw counts, k=8 means the `always` band needs all eight -- receipts at different k are NOT comparable (RL_V2 2026-09-18: a 9/16 at k=1 beside a 2/16 at k=8). **B:** how many completions GRPO scores per prompt; K=4 in RL_V2. **C:** the numerator of the available-gradient statistic. | Never write bare "k" in a receipt or a plot axis; say eval-k, group-K, or correct-count. |
| **2B** | A 2-billion-parameter judge model (`qwen3-2b`, `qwen3.5-oc:2b`) used as a scoring/eligibility gate. | Cheap isolated judge that scores candidate records so a bigger model never has to. "2B filter" / "2B scoring gate" / "2B eligibility" all mean *this model's score cleared the class threshold*. | Not a list-item label. `comfyui-api-render:31` "Layer 2b" and `llm-pipeline-layer-tdd:183` "(2b)" are enumeration, unrelated. |
| **CV** | **(A)** cross-validation. **(B)** coefficient of variation. **(C)** curriculum vitae. | **A:** nested tuning — outer holdout, inner Optuna (`optuna-nested-cv`). **B:** dispersion of document length in BM25 length-norm tuning (`parallel-rrf-…`). **C:** résumé writing (`business-writing`). | — |
| **GIST** | **(A)** Graph-Integrated Search & Traversal, a retrieval architecture. **(B)** the `avsolatorio/GIST-Embedding-v0` sentence-transformer checkpoint. | **A:** the traversal design (`gist_correlation_matrix`). **B:** the specific embedding model pinned in `request-intent-resolution`. `optuna-nested-cv:465` tunes a bare "GIST weight" — say which. | — |
| **L1 / L2** | **(A)** memory retrieval tier. **(B)** vector norm. **(C)** MCG knowledge-scope tier. | **A:** L2 = markdown/memory-bank, L1 = triplet store — "try L2 first" (`agentic_kg_memory:21`). **B:** L2-normalize before clustering (`:1639`). **C:** L2 = Industry/Domain scope (`:1418`) — an *inverted* numbering. Three schemes, two of them in one file. | Never write bare "L2" in `agentic_kg_memory`; it is ambiguous within a single document. |
| **TF** | **(A)** TensorFlow. **(B)** term frequency. | **A:** framework version capture (`validation-artifacts:71`). **B:** always hyphenated as TF-IDF (`bm25-autoencoder`). | — |

## Single-sense but never expanded anywhere — expand on first use

A guesser will invent an expansion for these exactly as it did for SPO.

| Term | Meaning | Objective intent |
|---|---|---|
| **TPE** | Tree-structured Parzen Estimator | The Optuna sampler. 19 uses across 12 files; "Parzen" appears zero times in the store. |
| **JEV** | *(expansion not defined by the model card or the operator)* A decoder model with a classification head, trained on many classification tasks, used as a general classifier: ask it a question, read a score. | Cheap local scorer that produces decision features for an LLM harness before dispatch (`tiers.toml` `[scorer.jev]`). Current checkpoint: `qwen3.5-0.8b-nvsh-tool-jev-scorer-v2`, fine-tuned for nvsh operation scoring; routing use is unvalidated. |
| **CPT** | Continued pre-training | Further pretraining on domain corpus before SFT. See orphan below. |
| **SMP** | *(orphan)* | `class-balancing:35` writes "raw continued pretraining (SMP)" — the same concept as CPT under a one-off abbreviation matching no expansion. Treat as a defect; use CPT. |
| **SGD** | Stochastic gradient descent | Optimizer choice recorded in training artifacts. |
| **MSE** | Mean squared error | Loss metric named in holdout eval. |
| **ROC / AUC** | Receiver operating characteristic / area under curve | Classification quality in validation artifacts. |
| **RNG** | Random number generator | Seed capture for reproducibility. |
| **SLA** | Service level agreement | Latency budget in benchmark artifacts. |
| **P50 / P95 / P99** | Latency percentiles | Benchmark distribution, not a version number. |

## Provenance of the SPO ruling

The operator settled this directly (2026-09-12):

> "I meant soft policy optimization and expected the ai to understand what I meant,
> despite me also using that term for subject predicate object … No — it was either
> subject, predicate, object or soft policy optimization."

Two senses. There is no third.
