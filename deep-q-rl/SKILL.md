---
name: deep-q-rl
description: Deep Q-learning with Russian Doll MCTS for any scored discrete-action environment. Use when you have a state space you can encode as a tensor, a score/evaluation function, and a discrete action set. Covers value-head Q-network, experience replay, target network, progressive-narrowing MCTS, AHA learning (mistake correction), and training-progress annealing.
status: active
last_validated: 2026-04-28
---
# Deep-Q RL for Scored Frameworks

## Purpose
Apply this skill when:
- You have a discrete action space and a scalar score/evaluation function
- You want to combine neural value learning with heuristic search
- The search space is large enough to require selective expansion (not exhaustive)
- You want online mistake correction during self-play training

The pattern originated in `chess-deep-q` but is domain-agnostic. Any framework where
you can define a score per state can host this approach.

---

## Score Correlate Design

**This is the highest-leverage design decision in the whole skill.**

The Q-network does not directly observe the true objective (winning, task completion,
final reward). It sees only what `evaluate(state)` returns at each step. If your
correlate is wrong, Q-learning optimizes the wrong thing — perfectly.

### Why a correlate is necessary

Terminal rewards alone (`+1` win, `-1` loss, `0` draw) are too sparse: in a 60-move game,
99% of transitions carry a zero reward signal and the network gets almost no gradient.
`evaluate` provides **dense intermediate signal** — a step-level proxy that correlates
with the true objective and fires on every transition.

### Properties of a good correlate

| Property | Description |
|---|---|
| **Correlation with true objective** | States that score higher heuristically should win more often |
| **Density** | Returns a meaningful non-zero value on every non-terminal state |
| **Monotonic alignment** | Improvement in score should predict improvement in outcome |
| **Current-player POV** | Sign must reflect the acting player's advantage, not an absolute side |
| **Bounded or normalizable** | MCTS leaf evaluation uses `tanh(score / K)`; calibrate K to ~1σ of score range |

### How to find your correlate

1. **Decompose the true objective into features that are observable mid-episode.**
   Chess: material balance + mobility + king safety + pawn structure + space control.
   Each feature is individually meaningful and measurable without knowing the outcome.

2. **Weight features by their empirical correlation with outcomes.**
   Run self-play or use labeled data; compute Pearson/Spearman between each feature
   and episode outcome. Drop features with near-zero correlation.

3. **Calibrate scale.**
   Compute the std of your raw score across a sample of positions. Set `K = std`.
   `tanh(score / K)` will then map ±1σ to ±0.76, keeping most scores well-separated.

4. **Validate directionally.**
   Pick 10 "obviously better" and 10 "obviously worse" state pairs for your domain.
   Your correlate must rank them correctly in the right direction. If it doesn't,
   the Q-network will learn to seek the wrong states.

### AHA learning depends on correlate quality

AHA learning triggers when `eval_drop > aha_threshold`. If your correlate is noisy
or poorly aligned, AHA fires on false positives (corrects good moves) or misses real
mistakes. Budget the AHA threshold at roughly **0.5σ–1.5σ** of typical single-step
eval change, not an absolute constant.

### Chess reference decomposition

```text
score = material_balance           # piece values (pawn=1, knight/bishop=3, rook=5, queen=9)
      + 0.1 * mobility             # number of legal moves available
      + king_safety                # shelter pawns, castling rights, exposure penalty
      + pawn_structure             # doubled/isolated/passed pawn bonuses/penalties
      + space_control              # center square control
      + piece_coordination         # connected rooks, bishop pairs
```

Each term is independently meaningful. The sum correlates with win probability even
without knowing the game outcome. This is what makes dense reward shaping work here.

---

## When to Use vs. Plain DQN
Use Russian Doll MCTS + value head when:
- The action space is wide (>10 moves) but most actions are noise
- A domain heuristic exists that can prioritize action categories
- You can afford multiple short rollouts per decision

Use plain DQN (no MCTS) when:
- Action space is small and roughly uniform
- No domain heuristic available for action categorization
- Inference latency budget is tight

---

## Abstract Interface

Your domain must implement these five operations:

```python
class ScoredEnvironment(Protocol):
    def encode_state(self, state) -> torch.Tensor
    """Convert state to float tensor. Shape is network-specific (e.g., [C, H, W] for grids)."""

    def evaluate(self, state) -> float
    """Dense correlate of the true objective. Must be current-player-POV.
    Not the true reward — a per-step proxy that correlates with episode outcome.
    Design process: decompose objective into observable mid-episode features,
    weight by empirical correlation with outcomes, calibrate scale to ~1σ."""

    def legal_actions(self, state) -> list
    """All valid actions from this state."""

    def apply(self, state, action) -> state
    """Return new state after applying action. Must not mutate the original."""

    def is_terminal(self, state) -> bool
    """True when the episode is over (win/loss/draw/done)."""

    # Optional but recommended for Russian Doll MCTS:
    def categorize_actions(self, state, actions) -> dict[str, list]
    """Partition actions into priority categories. Keys are category names, values are action lists."""

    def category_weights(self) -> dict[str, float]
    """Weight per category for proportional sampling. Higher = more likely to be sampled."""
```

The network, MCTS, and AHA components are all parameterized by these operations.

---

## Components

### 1. Value-Head Q-Network

Output is a **single scalar** in `[-1, 1]` via `tanh`, not a vector of Q-values.
MCTS uses this as a leaf-node evaluator; the Bellman update treats it as a state value.

```
Architecture: encode_state → [ConvBlocks or Dense layers] → Linear(_, 1) → tanh

For grid states:   Conv2D → Conv2D → Flatten → Linear(256) → Linear(1) → tanh
For vector states: Linear(128) → ReLU → Linear(64) → Linear(1) → tanh
```

**Contracts:**
- Input: `(batch, *state_shape)` float tensor
- Output: `(batch, 1)` float in [-1, 1]
- Loss: MSE against Bellman targets; direct MSE on AHA correction targets

### 2. Experience Replay + Bellman Update

Standard DQN experience replay. Store `(state_tensor, action, reward, next_state_tensor, done)`.

```python
# Bellman target
next_v = target_network(next_states).squeeze().detach()
target  = rewards + (1 - dones) * gamma * next_v
loss    = mse_loss(q_network(states).squeeze(), target)
```

**Reference values:** `batch_size=64`, `replay_buffer_maxlen=10000`, `gamma=0.99`

Train on every step once the buffer exceeds `batch_size`.

### 3. Target Network

A frozen copy of the Q-network used only for computing Bellman targets.
Prevents moving-target instability.

```python
# Sync every N episodes (not every step)
if episode % target_update_freq == 0:
    target_network.load_state_dict(q_network.state_dict())
```

**Reference value:** sync every 5 episodes.

### 4. Russian Doll MCTS

Progressive narrowing search: each level sees fewer candidates than the level above.
Implemented with UCB selection, parallel simulations, and a neural value function.

#### Funnel shape
```
Level:    1     2     3    4    5    6    7
Samples: [21,   13,   8,   5,   3,   2,   1]
```
Adjust depth to match domain complexity. Shallow domains (fast transitions) can afford
deeper funnels. Expensive evaluation functions need shallower funnels.

#### Action expansion
At each node, use `categorize_actions` + `category_weights` to draw a weighted sample
of size `samples_per_level[depth]` rather than expanding all legal actions.
This is the primary mechanism preventing combinatorial blowup.

#### UCB with annealing
```python
alpha = 1 + training_progress       # ramps from 1 to 2
beta  = current_move / max_moves    # ramps from 0 to 1

effective_exploration = base_weight * (1 - 0.5 * alpha * beta)

ucb = Q[s][a] / (N[s][a] + eps) + effective_exploration * sqrt(log(total) / (N[s][a] + eps))
```
Exploration collapses as training matures and as the game approaches its end.

#### Leaf evaluation
1. Terminal positions: assign `{+1, -1, 0}` directly
2. Neural network: `q_network(encode_state(s))` clamped to `[-1, 1]`
3. Fallback (net unavailable): `tanh(heuristic(s) / normalization_constant)`

#### MCTS iteration count annealing
```python
iterations = int(base_iters + max_iters * training_progress)
# e.g., 50 + 150 * t → 50 (untrained) to 200 (fully trained)
```
Start cheap and think harder as the value network becomes reliable.

#### Parallel simulations
Each simulation gets an **independent copy** of the state; backpropagation uses running
average `Q += (v - Q) / N`. Use `threading.Lock` per node to prevent race conditions.

### 5. AHA Learning (Mistake Correction)

Detects significant evaluation drops after a chosen action and immediately corrects.

```
Per-episode budget:  aha_budget_per_game = 3
Trigger threshold:   eval_drop > abs(aha_threshold)   # e.g., aha_threshold = -1.5
Correction target:   -1.0   (immediate negative signal)
```

**Algorithm per move:**
1. Ask MCTS for its choice `move`
2. Apply `move` to a test copy; compute `eval_change` from current player's perspective
3. If `eval_change < aha_threshold` and budget > 0:
   a. Compute gradient on state with target Q = -1.0
   b. Scan all legal actions; find alternatives with `eval_change >= aha_threshold`
   c. Play the best alternative; decrement budget
4. Otherwise play `move`

**When to enable:** During self-play training only. Not during inference.
Disable when the domain heuristic is unreliable — AHA depends on heuristic lookahead.

### 6. Weighted Action Categorization

Partition `legal_actions(state)` into priority tiers. Sample proportionally.

Example tier structure (chess-derived; adapt category names to domain):

| Category | Examples | Default weight |
|---|---|---|
| `captures_high_value` | Capturing higher-value pieces | 5.0 |
| `checks` | Moves that check the opponent | 4.0 |
| `captures_equal_value` | Even trades | 3.0 |
| `threatened_escapes` | Moving pieces under attack | 2.5 |
| `developing` | Improving piece position | 2.0 |
| `captures_low_value` | Capturing lower-value pieces | 1.5 |
| `center_control` | Moves to central squares | 1.5 |
| `king_safety` | Castling, shelter | 1.5 |
| `other` | Everything else | 0.5 |

For non-game domains, map to equivalent concepts: high-value actions, safe transitions,
exploratory actions, maintenance actions.

Proportional sampling:
```python
total_weight = sum(weights[cat] * len(actions[cat]) for cat in actions)
prob[a] = weights[category(a)] / total_weight
sample without replacement up to samples_per_level[depth]
```

### 7. Training Progress Annealing

`training_progress = min(episode / total_episodes, 1.0)` ∈ [0, 1].

| Parameter | Start (t=0) | End (t=1) | Formula |
|---|---|---|---|
| MCTS iterations | `base_iters` | `base_iters + scale_iters` | `base + scale * t` |
| Exploration weight | `1.6` | `0.8` | `max(1.6 * (1 - 0.5*t), 0.8)` |
| Samples per level | wider | narrower | `max(floor, int(width * (1 - 0.3*t)))` |
| Epsilon | initial | `epsilon_min` | decayed per batch |

---

## Generalization Contract

To adapt to a new domain:

| Required | Description |
|---|---|
| `encode_state(s) → Tensor` | Must be deterministic and consistent |
| `evaluate(s) → float` | Heuristic score; sign convention must be from current player's POV |
| `legal_actions(s) → List` | All valid actions; must be enumerable |
| `apply(s, a) → s'` | New state; must not mutate `s` |
| `is_terminal(s) → bool` | End condition |

| Recommended | Description |
|---|---|
| `categorize_actions(s, moves) → Dict` | Action priority tiers for weighted sampling |
| `category_weights() → Dict` | Per-category sampling weight |

| Optional | Description |
|---|---|
| Terminal value function | Override `{+1,-1,0}` with domain-specific terminal values |
| AHA threshold | Tune `aha_threshold` based on heuristic score scale |
| Normalization constant | `tanh(score / K)` — set K to ~1σ of typical score range |

**Score convention:** `evaluate` must return a score from the **current player's perspective**.
If the domain score is absolute (always from one side), negate on opponent turns.
MCTS backpropagation flips sign at each ply: `value = -value`.

---

## Configuration Reference

```text
# Q-network
learning_rate        = 0.001
gamma                = 0.99         # discount
batch_size           = 64
replay_buffer_maxlen = 10000

# Target network
target_update_freq   = 5            # episodes between syncs

# Epsilon-greedy (epsilon is used only if bypassing MCTS for fast action selection)
epsilon_init         = 0.1
epsilon_min          = 0.1
epsilon_decay        = 0.995

# MCTS
base_iterations      = 50           # at training_progress=0
max_iterations       = 200          # at training_progress=1
exploration_weight   = 1.6 → 0.8   # annealed
samples_per_level    = [21,13,8,5,3,2,1]  # starting widths

# AHA Learning
aha_budget_per_game  = 3
aha_threshold        = -1.5         # eval drop (heuristic units) to trigger correction
aha_min_move         = 5            # skip AHA on opening moves (position unsettled)

# Normalization
heuristic_norm_k     = 10.0         # tanh(score / k) for heuristic fallback
```

---

## Anti-Patterns

- **Action-vector Q-network**: outputting one Q-value per action breaks with large action spaces
  and prevents MCTS value-head usage. Use single-value output.

- **Absolute score convention**: if `evaluate` returns a fixed-side score (e.g., always White's
  advantage), MCTS backpropagation will be wrong on opponent nodes. Always return from
  current-player POV.

- **AHA learning outside training**: running AHA during inference introduces gradient updates on
  every call. Gate on `is_training=True` and `budget_remaining > 0`.

- **Sharing MCTS state across calls**: `ParallelRussianDollMCTS` maintains a visit count tree
  for one root position. Construct a new instance per move; do not reuse across positions.

- **Skipping proportional sampling**: expanding all legal actions defeats the Russian Doll funnel.
  Every node expansion must go through the weighted sampler.

- **Constant funnel width**: if `samples_per_level` doesn't narrow, the Doll degenerates into
  flat random sampling. Ensure each level is strictly smaller than the previous.

- **Missing neural fallback**: if the Q-network errors during MCTS evaluation, the simulation
  must fall back to the heuristic. Unhandled exceptions silently zero out rollout values.

- **Terminal-only reward signal**: relying solely on `{+1,-1,0}` at episode end makes the
  gradient signal too sparse for stable learning. Always define a dense step-level correlate.

- **Uncalibrated correlate scale**: using a raw score with arbitrary magnitude means `tanh(score / K)`
  saturates (all values near ±1) and the leaf evaluator loses resolution. Set K ≈ 1σ of your
  score distribution across sampled positions.

- **Misaligned correlate**: a correlate that doesn't rank "better" states above "worse" ones
  will cause Q-learning to converge on the wrong policy confidently. Validate directionally
  on 10–20 known state pairs before training.

---

## Chess Reference Implementation

The canonical implementation is at `thistleknot/chess-deep-q`:

| File | Role |
|---|---|
| `neural_network.py` | `ChessQNetwork` (value head), `DQNAgent` (AHA + MCTS dispatch) |
| `mcts.py` | `ParallelRussianDollMCTS` (parallel UCB, node locks, visit-count selection) |
| `evaluation.py` | `fast_evaluate_position` (material + mobility + king safety + pawn structure) |
| `board_utils.py` | `board_to_tensor` (12-channel [piece type × color] 8×8 tensor) |
| `chess_ai.py` | `OptimizedChessAI` (training loop, self-play, progress annealing, plotting) |

State encoding: 12 channels (6 piece types × 2 colors), each an 8×8 binary plane.
Terminal values: checkmate = ±1.0 (loser's side), stalemate/repetition = 0.0.
AHA threshold: -1.5 heuristic units; budget resets to 3 at game start.

---

## Code-RL: RL from Code Execution Feedback

Extends the deep-q-rl framework to the code-generation domain, where the
"score" is test pass rate and the "action space" is code edits or generation choices.
Sources: SWE-RL (arXiv:2502.18449, 41% SWE-bench Verified), MBR+DPO (arXiv:2410.02902,
ICLR 2025 spotlight).

### When to Use Code-RL

Use code-rl when:
- You have a **test suite** that can score code correctness as a scalar (pass rate)
- You want to improve code quality beyond a single-shot LLM generation
- You can afford multiple rollouts per code task (best-of-N or iterative)

Distinct from `self-repair` in `debugging` (single fix-run-retry loop) — code-rl
uses a policy gradient signal over many attempts, not just local repair.

### Environment Mapping

Apply the `ScoredEnvironment` interface to code:

| Abstract interface | Code-RL instantiation |
|---|---|
| `encode_state(s)` | Tokenise the current code file; use mean-pool embedding as state vector |
| `evaluate(s)` | Run test suite; return fraction of tests passing (0.0–1.0) |
| `legal_actions(s)` | LLM-generated candidate patches / completions |
| `apply(s, a)` | Apply patch to code file → new code file |
| `is_terminal(s)` | `evaluate(s) == 1.0` (all tests pass) OR `max_attempts` reached |

### Reward Signal Design

```python
def code_reward(before_pass_rate: float, after_pass_rate: float, attempt: int) -> float:
    """
    Dense reward: improvement in pass rate, penalised for attempt count.
    Require: both pass rates in [0.0, 1.0]; attempt >= 1.
    Guarantee: positive reward only when pass rate improves.
    """
    delta = after_pass_rate - before_pass_rate
    attempt_penalty = 0.01 * attempt       # small penalty per attempt to prefer early fixes
    return max(0.0, delta - attempt_penalty)
```

**Rule-based rewards (SWE-RL pattern):**
- `+1.0` on first full pass (all tests pass)
- `+delta` on partial improvement (more tests pass than before)
- `-0.1` on no change (discourage no-op patches)
- `-0.5` on syntax error (code does not even parse)

Rule-based rewards avoid the reward-hacking failure modes of LLM-judge rewards
for code tasks — execution is the ground truth.

### Best-of-N Selection (MBR Pattern)

When running multiple rollouts, select the best rather than the first success.

```python
def select_best_of_n(
    candidates: list[str],
    test_runner: Callable[[str], float],
    n: int = 8,
) -> tuple[str, float]:
    """
    Minimum Bayes Risk selection: evaluate all N candidates; return highest pass rate.
    Require: len(candidates) == n; test_runner is deterministic.
    Guarantee: returned code achieves max(pass_rates) across candidates.
    """
    scored = [(c, test_runner(c)) for c in candidates]
    return max(scored, key=lambda x: x[1])
```

MBR+DPO (arXiv:2410.02902): generate N samples → score all → use best as positive,
worst as negative → fine-tune with DPO. This converts best-of-N selection into a
training signal for the policy model.

### SWE-RL Pattern

SWE-RL (arXiv:2502.18449) trains on real GitHub issues with execution feedback:

1. **Issue → repository context** — load repo at commit before fix; read issue description
2. **Generate patch** — LLM proposes a code change
3. **Execute tests** — run the repo's existing test suite against the patch
4. **GRPO update** — reward = test pass rate delta; update policy weights
5. **Repeat at scale** — 50k+ GitHub issues as training distribution

Key results: 41% SWE-bench Verified (up from ~12% base). The reward signal is
entirely rule-based (test execution), not LLM-judged.

### Integration with Deep-Q-RL Components

| Deep-Q-RL component | Code-RL adaptation |
|---|---|
| Value-head Q-network | Code embedding → pass-rate predictor (regressor not classifier) |
| Experience replay | (code_state, patch, reward, new_code_state, done) tuples |
| Russian Doll MCTS | Action = candidate patch; evaluate = run test suite (expensive — use shallow funnel) |
| AHA learning | Trigger on `delta < -0.1` (patch degraded pass rate); replay with negative target |
| Action categorisation | Patch categories: bug_fix, refactor, test_addition, import_fix, logic_change |

**Shallow funnel for expensive evaluation:**
Test execution is slow (seconds per run). Use a 2–3 level funnel with small samples
rather than the default 7-level funnel. Budget: max 10–20 test runs per decision.

```python
code_rl_samples_per_level = [5, 3, 1]   # vs default [21,13,8,5,3,2,1]
```

### Anti-Patterns Specific to Code-RL

| Anti-pattern | Fix |
|---|---|
| LLM judge as reward instead of test execution | Execution is ground truth; judge rewards introduce hacking |
| Running full test suite on every MCTS node | Pre-filter with fast linting / syntax check; only run full suite on finalists |
| Ignoring partial credit | Pass rate delta is a richer signal than binary pass/fail; use it |
| Not checkpointing best patch | Always git-stash or checkpoint the highest-scoring patch before continuing |
| Unbounded rollouts | Set `max_attempts` (e.g., 10); return best seen if not fully solved |

## SPO / Offline Preference Optimization

Covers Soft Policy Optimization (SPO), DPO, and reward-weighted SFT — offline loops where the model is fine-tuned against pre-computed or batch-computed reward signals rather than an online simulator.

### When to Use SPO vs. Online RL

| Signal available offline? | Prefer |
|---|---|
| Yes — gold data, quality scores, format checkers | SPO / DPO |
| No — requires live environment feedback | Online RL (Code-RL, Deep-Q-RL) |

SPO is the right default when you have a structured output format, a scoring function that can run without a simulator, and a pre-existing base adapter that already emits roughly correct structure.

### Reward Component Design Rules

**Binary features → binary rewards.** If the training data either has a feature or it doesn't (e.g. evidence tags `observed`/`inferred`), the corresponding reward component must be binary: full credit if present anywhere in the output, zero otherwise. Partial credit for absent features (e.g. 0.5 × weight for missing tags) creates a free-point leak — the model earns reward without producing the feature.

**Penalise failure modes explicitly.** A reward that checks only *presence* of format markers scores a repeated line eight times as highly as eight unique lines. Add a uniqueness gate before format checks: if `unique_lines / total_lines < threshold` return 0.0 immediately. Detect tautological triplets (subject appears verbatim in object field) and deduct proportionally.

**Pre-score training samples; don't evaluate gold against gold.** When `compute_step()` scores gold `output_texts` against gold `ground_truths`, every clean sample scores ~1.0 and all examples receive equal weight. Pre-score each sample before the training loop using signals independent of format compliance (unique-content ratio, predicate specificity, subject dominance ratio). Embed as `precomputed_reward` and use it in `compute_step()`. Flat reward distribution (all ~0.8, no variance) is the diagnostic.

### Generation Parameter Pitfalls

**`repetition_penalty` conflicts with structured output headers.** `repetition_penalty > 1.0` penalises every token that appeared anywhere in the full input+output context, including the prompt. If the prompt's instruction list contains the same tokens as the expected output headers (e.g. `Non-Entailed Premises:`, `Throughline:`), the penalty prevents the model from generating those headers, producing garbled near-variants instead.

Safe default for structured output tasks:
```python
model.generate(
    **inputs,
    max_new_tokens=384,
    do_sample=False,
    no_repeat_ngram_size=6,   # blocks exact-line loops without touching header tokens
    # repetition_penalty=1.3  # NEVER with structured headers that echo prompt words
)
```

`no_repeat_ngram_size=6` prevents exact-line repetition (the failure mode `repetition_penalty` was trying to fix) without blocking 3–4-token header sequences.

**Eval pipeline must use identical generation params to inference.** A generation parameter change documented in the README but not propagated to the eval script will produce `avg_quality=0.0` silently — every structured output has garbled headers, every format check fails. After changing any generation param, grep the repo for `repetition_penalty`, `no_repeat_ngram_size`, `temperature`, and `do_sample` and audit every occurrence.

Diagnostic: quality collapse to 0.0 across *all* training samples simultaneously is a systemic eval bug, not model regression.

### Epoch Requirements

One epoch of SPO rarely generalises. Holdout metrics drawn from the training distribution can show 0.95+ correctness while out-of-distribution inputs exhibit repetition spirals, garbled tag variants, and format leakage from the base model's prior.

Validation protocol per epoch:
1. Run inference on 3–5 diverse quotes not from the training set.
2. Watch reward *variance* across training batches, not just mean — variance collapse early means local optimum on template compliance, not generalisation.
3. Declare done only when OOD inputs produce clean structured output.

### SPO Anti-Patterns

| Anti-pattern | Fix |
|---|---|
| Partial credit for absent binary features | Binary reward: present = full credit, absent = 0 |
| Uniform reward across all training samples | Pre-score offline; embed `precomputed_reward`; verify reward variance > 0 |
| Eval gen params differ from inference | Single source of truth for gen params; grep + audit after every change |
| `repetition_penalty` with structured headers | Remove it; use `no_repeat_ngram_size=6` |
| Declaring done after 1 epoch | Validate on OOD inputs; watch variance; run ≥ 2–3 epochs |
<!-- consolidation:see-also:start -->
## See Also
[[agent-governance]]  [[skill-wiki]]  [[deep-research]]
<!-- consolidation:see-also:end -->
