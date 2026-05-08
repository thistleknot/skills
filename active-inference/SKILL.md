---
name: active-inference
description: >
  Bayesian agent decision-making via the Free Energy Principle. An Active
  Inference agent maintains a generative model (A/B/C/D matrices) over hidden
  world states, selects actions by minimizing Expected Free Energy (EFE), and
  updates its posterior belief via variational inference after each observation.
  The EFE decomposes into epistemic value (reduce uncertainty about states) and
  pragmatic value (reach preferred outcomes) — no scalar reward function required.
  Use when the environment is partially observable, reward design is hard, or
  principled uncertainty-driven exploration is needed. Complements deep-q-rl
  (which assumes full observability + known evaluator).
status: active
last_validated: 2026-05-07
---

# Active Inference

## When to Use

Use active-inference when:

- The environment is **partially observable** (the agent doesn't know the full state)
- **No clean scalar reward signal** exists until end-to-end task evaluation
- You want **principled exploration** that naturally stops when beliefs converge
  (no UCB tuning, no ε-annealing schedule)
- Tool selection must be driven by **information gain** ("which tool resolves
  the most uncertainty about the current state?")
- You need **multi-modal observations** or an **online-learnable transition model**

Use `deep-q-rl` instead when:
- Full state observability is available
- A reliable `evaluate(state)` function or reward correlate exists
- You need the Russian Doll MCTS planning depth without a generative model

---

## Core Concepts

### Free Energy Principle
**Friston 2010** (Nature Reviews Neuroscience 11:127–138)

A system minimizes **variational free energy** — a proxy for surprise — over its
sensory states. This reduces to:
```
F = KL[Q(s) ‖ P(s | o)] - log P(o)
   ≈ -accuracy + complexity
```
Where `Q(s)` is the agent's belief over hidden states, `P(s | o)` is the true posterior.

### Expected Free Energy (EFE)
**Friston et al. 2015** (Cognitive Neuroscience 6(4):187–214)

For future policy π, the EFE is:
```
G(π) = -E[log P(o | C)]           # pragmatic value (reach preferred outcomes)
     + E[KL[Q(s | o, π) ‖ Q(s | π)]]  # epistemic value (info gain)
```

- High **pragmatic value** = policy reaches preferred observations `C`
- High **epistemic value** = policy reduces uncertainty about hidden states
- Action selection: softmax over `-G(π)` (prefer low EFE policies)

**The key insight for agents:** EFE naturally trades off exploration (epistemic)
vs. exploitation (pragmatic) without a scalar reward. When beliefs are uncertain,
epistemic value dominates (probe). When beliefs are confident, pragmatic value
dominates (act).

### Generative Model (POMDP)
**pymdp arXiv:** `2201.03904` (JOSS 2022)

```
A matrix: P(observation | hidden_state)     — likelihood mapping
B matrix: P(state_t+1 | state_t, action)    — transition model
C matrix: P(preferred_observation)           — preferences (soft reward)
D matrix: P(initial_hidden_state)            — prior over initial states
```

All matrices are parameterized as Dirichlet distributions, enabling online
Bayesian learning from observations.

---

## pymdp Library

**Repo:** `infer-actively/pymdp` (MIT, ~1000★)
**Install:** `pip install inferactively-pymdp`

```python
from pymdp import utils, maths
from pymdp.agent import Agent

# 3 hidden states, 4 observations, 2 actions
A = utils.random_A_matrix(num_obs=4, num_states=3)  # likelihood
B = utils.random_B_matrix(num_states=3, num_actions=2)  # transitions
C = utils.obj_array_uniform([4])  # flat preferences initially
D = utils.uniform_categorical([3])  # uniform prior

agent = Agent(A=A, B=B, C=C, D=D)

# Per-timestep loop
for obs in environment:
    belief = agent.infer_states(obs)        # variational inference
    action = agent.infer_policies()         # EFE minimization
    agent.infer_parameters()               # update A/B via Dirichlet EM
    environment.step(action)
```

**JAX rewrite (pymdp v1.0, in progress):**
```python
# Current alpha — API may change
from pymdp.jax.agent import Agent as JaxAgent
from pymdp.jax import mcts  # MCTS planning via mctx
```

---

## Tool-Use Application (Software Engineering Agent)

AIF maps naturally onto debugging/diagnostic agent scenarios:

```
States:    {bug_in_fileA, bug_in_fileB, bug_in_fileC, no_bug}
Actions:   {grep_fileA, grep_fileB, run_tests, read_stack_trace, apply_fix}
Obs:       {found_match, no_match, tests_pass, tests_fail, error_in_trace}
Preferred: P(obs = tests_pass) = 0.95  # C matrix
```

**EFE drives tool selection:**
- `grep_fileA` when P(bug in fileA) is highest and uncertain → high epistemic value
- `run_tests` after narrowing to one hypothesis → high pragmatic value
- Agent stops probing when beliefs converge (EFE → 0 for diagnostic actions)

**Key advantage over deep-q-rl for this scenario:**
- No need to design a reward function
- Handles partial observability (stochastic grep results, flaky tests) natively
- EFE naturally prioritizes information-gathering before committing to a fix

```python
# Minimal AIF tool-selection agent sketch
A = build_likelihood_from_tool_output_data(tools, states)
B = uniform_transitions(states, tools)  # or learned from prior runs
C = encode_preference(preferred_obs="tests_pass", strength=4.0)
D = uniform_prior(states)

agent = Agent(A=A, B=B, C=C, D=D)
obs = run_tool(initial_action)
while not agent.beliefs_converged(threshold=0.9):
    belief = agent.infer_states(obs)
    action = agent.infer_policies()
    obs = run_tool(action)
```

---

## Comparison with deep-q-rl

| Dimension | `deep-q-rl` | `active-inference` |
|---|---|---|
| **Observability** | Full state assumed | Native POMDP (partial observability) |
| **Reward requirement** | Needs `evaluate(state)` correlate | Preferences `C` encode soft targets; no scalar reward |
| **Exploration strategy** | UCB + annealing (tuned heuristic) | Epistemic value = automatic info gain |
| **Transition model** | Not used | Explicit B matrix; online Dirichlet learning |
| **Online model learning** | Q-network improves over episodes | A/B matrices update from observations |
| **Multi-modal observations** | Not native | A matrix multi-modal |
| **Convergence signal** | Reward plateau | EFE → 0 (beliefs converged) |

**Russian Doll MCTS** (deep-q-rl) ≈ **Sophisticated Inference** (active-inference):
both use tree search over policies; EFE replaces Q-value as the node scoring function.

---

## Curiosity vs. EFE Exploration

EFE-based exploration is the principled Bayesian alternative to heuristic curiosity modules:

| Method | Paper | Mechanism | Production? |
|---|---|---|---|
| **EFE epistemic value** | Friston et al. 2015 | KL info gain, emerges from generative model | ✅ pymdp |
| **ICM** (Pathak et al.) | arXiv:`1705.05363` ICML 2017 | Forward model prediction error | ✅ stable-baselines3 |
| **RND** (Burda et al.) | arXiv:`1810.12894` ICLR 2019 | Random network distillation | ✅ stable-baselines3 |

ICM/RND are cheaper heuristics. EFE is theoretically grounded and requires no separate
curiosity network — it emerges from the same generative model used for planning.

---

## Planning Modes

| Mode | pymdp | When to use |
|---|---|---|
| **Flat policy** | `agent.infer_policies()` | Short horizon (1–3 steps) |
| **Sophisticated Inference** | `pymdp/planning/si.py` | Multi-step planning with nested beliefs |
| **MCTS** | `pymdp/jax/mcts.py` (via mctx) | Large action spaces; deep planning |

For SE agents with large tool sets: MCTS over EFE with `mctx` (JAX).

---

## Numerical Caveats

```python
MINVAL = 1e-16   # floor all probabilities to avoid log(0)

# Dirichlet posterior must be initialized with pseudocounts ≥ 1
A_init = np.ones((num_obs, num_states)) * 0.1  # Dirichlet α > 0 everywhere

# EFE is in nats; scale sensitivity relative to magnitude of G
# If |G_epistemic| ≫ |G_pragmatic|: agent will explore indefinitely
# Fix: scale C preferences by info_gain magnitude or normalize G components
```

---

## Interface Contract

```yaml
inputs:
  num_states: int | list[int]       # hidden state factor dimensions
  num_obs: int | list[int]          # observation modality dimensions
  num_actions: int
  A: ndarray                        # likelihood P(obs | state)
  B: ndarray                        # transitions P(s' | s, a)
  C: ndarray                        # preferences over observations
  D: ndarray                        # prior over initial states
  planning_mode: flat | si | mcts
  convergence_threshold: float      # stop when max(belief) > threshold

outputs:
  action: int
  belief: ndarray                   # posterior Q(s) after inference
  efe_per_action: ndarray           # G(π) for each action
  epistemic_value: float
  pragmatic_value: float
  converged: bool

preconditions:
  - A, B, C, D matrices are valid probability distributions
  - All matrix entries > MINVAL (no zero probabilities)
  - Dirichlet pseudocounts ≥ 1 when using online learning mode

postconditions:
  - action = argmin G(π)
  - belief sums to 1.0
  - converged=True when max(belief) > convergence_threshold

invariants:
  - EFE decomposes into separable epistemic and pragmatic terms
  - Online learning updates A/B Dirichlet counts, never resets them
```

---

## Integration with Skill Library

| Context | Skill |
|---|---|
| Known reward + full observability | `deep-q-rl` (use instead) |
| Diagnostic tool selection under uncertainty | This skill |
| Uncertainty about agent output quality | `uncertainty-quantification` |
| Agent operating under partial info + causal queries | `causal-inference` |
| Memory of prior episode beliefs | `agentic_kg_memory` (belief persistence) |
| Exploration in training data generation | `synthetic-data` (curiosity-guided sampling) |

---

## Evidence

- Friston 2010 (NRN 11:127): Free Energy Principle unified brain theory
- Friston et al. 2015 (CogNeuro 6(4)): EFE epistemic + pragmatic decomposition
- Heins et al. arXiv:2201.03904 (JOSS 2022): pymdp library paper
- Da Costa & Friston arXiv:2201.06387 (Physics Reports 2023): FEP made simple
- Sajid et al. arXiv:1909.10863 (Neural Computation 2021): AIF demystified
- Tschantz et al. arXiv:2002.12636 (ICLR 2020 workshop): RL through Active Inference
- Pathak et al. arXiv:1705.05363 (ICML 2017): ICM curiosity baseline
- Burda et al. arXiv:1810.12894 (ICLR 2019): RND curiosity baseline
- `infer-actively/pymdp`: `pip install inferactively-pymdp`
<!-- consolidation:see-also:start -->
## See Also
<!-- consolidation:see-also:end -->
