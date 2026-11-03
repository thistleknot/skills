---
name: training-regime-principles
description: >
  Cross-regime training principles for CPT → SFT → RL pipelines on small models (≤1B).
  Covers: what each regime teaches vs what it cannot, dependency chain enforcement,
  learning rate ladder, forgetting cascade, observability contracts, anti-patterns
  with proven failure modes, and decision logic for choosing between GRPO/DPO/PPO.
  Use when designing a training pipeline, diagnosing why a stage produced no lift,
  deciding whether to use RL or more SFT, or debugging cross-stage regressions.
  Source: RL_V2 project empirics (macroF1=0.549 SFT, +0.091 MGPO lift) + VibeThinker
  + DeepSeek-R1 + Zhu et al. 2608.03573.
---

# Training Regime Principles (CPT / SFT / RL)

## What Each Regime Does (and Cannot Do)

| Regime | Teaches | Cannot Teach | Mechanism |
|--------|---------|-------------|-----------|
| CPT | Knowledge (facts, entities, vocabulary) | Behavior, formatting | Next-token prediction on domain text |
| SFT | Behavior (how to respond, format, abstain) | New facts (already in weights) | Masked loss on response tokens only |
| RL | Precision (which behaviors to prefer, calibration) | New behaviors never produced by the base | Reward signal sharpens existing distribution |

**Single sentence:** CPT deposits knowledge. SFT teaches manners. RL teaches taste.

## The Dependency Chain (Hard Constraints)

```
CPT (knowledge) → SFT (behavior) → RL (sharpening)
```

Each stage has a hard dependency:
- SFT without pre-trained knowledge → fabrication
- RL without SFT behavior → zero signal (model doesn't produce what you're optimizing)
- RL on wrong SFT base → optimizing a null distribution

**Gate check before RL:** the SFT base MUST already produce the target behavior.
- f1_abstain > 0 on eval set before launching RL (proven: zero abstention base → adapter trains but max|B| < 1e-4)
- If base never abstains, fix SFT first — RL cannot create what doesn't exist

## Learning Rate Ladder

Each downstream stage uses progressively colder LR:

| stage | full-param | LoRA | effective step (LoRA) |
|-------|-----------|------|----------------------|
| Pre-training (scratch) | 3e-4 | — | — |
| CPT | 1e-4 | 1e-4 | lr×α/r |
| SFT | 2e-5 | 1e-4 | lr×32/16 = 2e-4 |
| RL | 1e-6 to 3e-6 | 1e-5 to 5e-5 | 2e-5 to 1e-4 |

**Rule:** LoRA LR ≈ 10× full-param LR for the same stage (same effective update magnitude).

## The Forgetting Cascade

Every stage risks destroying what the previous stage taught:

| risk | mitigation |
|------|-----------|
| CPT destroys general capabilities | 2-5% general replay, monitor held-out perplexity |
| SFT destroys CPT knowledge | Low LR (2e-5), 1-3 epochs max, completion-only loss |
| RL destroys SFT behaviors | KL penalty (β=0.05-0.10), few hundred steps, monitor macroF1 |

**Universal monitor:** track upstream metrics throughout downstream training. If upstream metric drops >15%, back off.

## SFT: The Load-Bearing Details

### Completion-only loss (NON-NEGOTIABLE)
```
Tokens:    [SYS] ... [USER] question [ASST] answer [EOS]
Loss mask:   0   ...   0      0        1     1      1
```
Divide by `num_response_tokens`, NOT total sequence length.

### What determines SFT quality
1. **Data stratification** — multi-regime × multi-domain (16-cell) ensures all behaviors seen
2. **Quality > quantity** — 27K good > 1M noisy (Llama 2 Chat, LIMA)
3. **Short training** — 1-3 epochs; beyond 3 → memorization
4. **Loss masking** — instruction tokens are context, not targets

### Proven failure: regime-only stratification
SFT with regime-only sampling (no domain cross) → f1_abstain=0.000.
Fix: 16-cell stratification (regime × domain). Proven at macroF1=0.549.

## RL: The Core Insight

RL SHARPENS existing behavior. It does NOT create new behavior.

### Signal preconditions (BOTH required)
1. **Data must be class-balanced** — Box-Cox stratified sampling lifts abstention from 6% to ~30%
2. **Base must already abstain** — RL on a base with f1_abstain=0 produces zero gradient

### Zero-variance = zero signal
If all G rollouts in a group score identically → std=0 → advantage=0 → no gradient.
- `frac_reward_zero_std=1.0` sustained >5 steps → kill the run
- Cause: batch contains only one class (all answerable OR all unanswerable)
- Fix: cross-hatch sampling ensures behavioral diversity per batch

### The three diagnostics (every RL run)
1. **Mean KL** — should stay [0, 0.02]. Past 0.1 = danger.
2. **Clip fraction** — 0.1-0.3 sweet spot. Near 0 = too timid. >0.4 = over-fitting rollout.
3. **frac_reward_zero_std** — should be <0.5. At 1.0 = no learning.

### Observability (NON-NEGOTIABLE)
Every 10 steps, print 3 sample (prompt, gold, completion, reward) tuples.
If all completions are the same class → training is broken → KILL IMMEDIATELY.
Do not wait for final scoring to discover hours later.

## When to Use Which Method (2026)

```
Missing KNOWLEDGE?
  → CPT (if model ≥3B) or RAG (if model ≤1B — parametric capacity insufficient)

Missing BEHAVIOR?
  → SFT with completion-only loss, stratified data

Imprecise about WHEN to use behaviors?
  → RL with appropriate reward:

    Have VERIFIABLE correctness (code/math)?
      → GRPO/MGPO with verifier reward (strongest signal)
    
    Have PAIRED preferences (A better than B)?
      → DPO (simpler, cheaper) or PPO (at scale, >70B)
    
    Have only UNPAIRED good/bad labels?
      → KTO
    
    Want single-stage alignment?
      → ORPO (combined SFT+preference) or SimPO (no reference model)
```

## DPO vs GRPO Decision

| criterion | DPO wins | GRPO wins |
|-----------|----------|-----------|
| Data type | Paired preferences | Verifiable rewards (code exec, math match, judge) |
| Stability | Very stable (supervised loss) | Less stable (on-policy, requires diversity) |
| Compute | 2 models in memory | 1-2 models + generation cost |
| Signal type | "Which is better" (relative) | "How good is this" (absolute) |
| Iterative improvement | Fixed dataset, no on-policy | On-policy generation discovers new solutions |
| Our use case | — | ✓ (judge reward, abstention calibration) |

## Anti-Patterns (Proven Failures from This Project)

| pattern | consequence | root cause | fix |
|---------|-------------|-----------|-----|
| RL on non-abstaining base | max\|B\| < 1e-4, macroF1=0 | No within-group variance on abstention | SFT with abstention data first |
| Regime-only SFT sampling | f1_abstain=0.000 | Model never sees abstention in training context | 16-cell stratification |
| Prompt truncation in RL | 4-token EOS, trains on garbage | TRL left-truncates, destroys few-shot | Pre-filter: SELECT prompts that fit |
| Think-token pollution | Judge scores gibberish | Reasoning model bleeds `<think>` tags | suppress_tokens + strip |
| acc@439 applied to RL | Category error | Wrong metric for calibration stage | macroF1@112 only |
| f1_abstain reported alone | Hides all-abstain collapse | Model learned to always refuse | Full confusion matrix always |
| β too low (0.02) | Policy collapse | Unconstrained drift from reference | β=0.10 proven stable |
| HPO results carried across schema changes | Production collapse | LR tuned against different optimization landscape | Re-run HPO under new schema |
| Multi-hour run without smoke test | Wasted wall-clock on broken config | Bug invisible at scale but obvious at 1 step | 1-element smoke FIRST |

## The Proven Configurations (Do Not Re-Derive)

### SFT (validated macroF1=0.549, f1_abstain=0.872)
- lr=2e-5, 3 epochs, full-param, completion-only loss
- 16-cell stratification (regime × domain), 400 rows
- adamw_8bit optimizer, gradient_checkpointing=True

### MGPO (validated +0.091 lift over SFT)
- lr=1e-4, LoRA r=16 α=64, β=0.10, G=4
- max_completion=512, 2B isolated judge
- Cross-hatch regime-only sampling (valid for RL because SFT base already abstains)
- TruncationFreeSampling: pre-filter prompts to fit within 512 tokens

### Base (denominator)
- macroF1@112 = 0.063 (near-random on calibration task)

## Parallel-RL (Documented, Parked)

RL adapters are orthogonal across domains (Zhu et al.):
- GRPO advantage normalization is zero-sum → cancels shared gradient → only task-specific residual remains
- Single-domain adapters can be merged via DARE+TIES with 97.4% retention
- 5% adapted pass exceeds single-task performance (103.2%)

**Not deployed because:** mixed-domain MGPO with cross-hatch already proved lift (+0.025 macroF1, all quadrants improved). Deploy only if cross-hatch grid reveals domain-specific regressions.

## Quality > Quantity (Universal)

| evidence | n | result |
|----------|---|--------|
| Stanford Alpaca (2023) | 52K synthetic | Competitive chatbot for $600 |
| Llama 2 Chat (2023) | 27K human | State-of-art alignment at release |
| LIMA (2023) | 1K curated | Matches 52K noisy |
| Our SFT (2026) | 400 rows (16-cell) | macroF1=0.549 (exceeds July reference) |

The principle holds at every stage. A small, well-stratified, high-quality dataset beats a large noisy one.
