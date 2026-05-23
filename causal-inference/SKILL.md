---
name: causal-inference
description: >
  Hybrid causal reasoning protocol: LLM proposes the causal graph structure,
  symbolic libraries (DoWhy, causal-learn) execute identification and estimation,
  LLM interprets results in context. Use for counterfactual queries ("what would
  happen if X were different?"), treatment effect estimation, and root-cause
  analysis where correlation is insufficient. Distinct from reasoning (which
  is deductive/inductive, not causal) and deep-research (which gathers web
  evidence, not causal estimates).
status: active
last_validated: 2026-05-07
---

# Causal Inference

## When to Use

Use causal-inference when:

- The question requires a **counterfactual** answer: "What would Y have been if
  we had done X differently?"
- You need a **treatment effect estimate** (ATE, ATT, CATE) from observational data
- **Root cause analysis**: which variable causally explains an observed outcome?
- You have **confounders** that correlate with both treatment and outcome, making
  naive regression misleading
- You need to **propose a causal graph** from domain text and validate it against data

Do **not** use when:
- The answer requires web evidence gathering → use `deep-research`
- The question is purely logical/deductive → use `reasoning`
- You only need correlation (ML prediction, not intervention) → skip this skill
- The data has < 50 observations (causal discovery algorithms are unreliable)

**Critical rule:** LLMs can *suggest* causal graph structures from domain knowledge
but fail near-randomly at *formal* do-calculus from correlational data alone
(arXiv:2306.05836, ICLR 2024). Always route formal identification and estimation
through a symbolic library (DoWhy), not the LLM.

---

## Architecture

```
User causal query
        │
        ▼
┌─────────────────────────────┐
│  LLM: Propose Causal Graph  │  pywhy-llm: suggest edges, confounders,
│  (DAG structure suggestion) │  IVs, backdoor sets from domain text
└───────────────┬─────────────┘
                │ proposed DAG
                ▼
┌─────────────────────────────┐
│  Symbolic: Validate & Fit   │  causal-learn (PC/GES/LiNGAM) or
│  (causal discovery / test)  │  NOTEARS structure learning on data
└───────────────┬─────────────┘
                │ validated DAG
                ▼
┌─────────────────────────────┐
│  DoWhy: Identify + Estimate │  Pearl 4-step: model → identify →
│                             │  estimate → refute
└───────────────┬─────────────┘
                │ causal estimate + refutation results
                ▼
┌─────────────────────────────┐
│  LLM: Interpret & Narrate   │  Convert numerical result to natural
│                             │  language with uncertainty quantified
└─────────────────────────────┘
```

---

## Pearl's Ladder of Causation

| Rung | Query Type | Example | Required |
|---|---|---|---|
| 1 | **Association** | P(Y \| X=x) | Regression / ML |
| 2 | **Intervention** | P(Y \| do(X=x)) | Identification + estimation (DoWhy) |
| 3 | **Counterfactual** | P(Y_{x'} \| X=x, Y=y) | Abduction → Action → Prediction |

Most "causal" questions are Rung 2 or 3. Standard ML only answers Rung 1.

---

## Production Libraries

### DoWhy — Pearl SCM Pipeline
**Repo:** `py-why/dowhy` (⭐8,101, Apache 2.0, active May 2026)
**Library:** `pip install dowhy`

```python
import dowhy
from dowhy import CausalModel

# Step 1: Model — define DAG
model = CausalModel(
    data=df,
    treatment="X",
    outcome="Y",
    graph="""
        digraph {X -> Y; Z -> X; Z -> Y}
    """  # or graphml / networkx
)

# Step 2: Identify — apply backdoor/frontdoor criteria automatically
identified_estimand = model.identify_effect()

# Step 3: Estimate — ATE via regression / propensity / double ML
estimate = model.estimate_effect(
    identified_estimand,
    method_name="backdoor.linear_regression",
    target_units="ate"
)

# Step 4: Refute — falsification tests
refutation = model.refute_estimate(
    identified_estimand, estimate,
    method_name="random_common_cause"
)
```

Counterfactual estimation uses Pearl's 3-step (abduction-action-prediction):
`model.estimate_effect(..., method_name="backdoor.propensity_score_weighting")`

---

### pywhy-llm — LLM-Augmented DAG Construction
**Repo:** `py-why/pywhy-llm` (reference impl, experimental)
**Library:** `pip install pywhyllm`

```python
from pywhyllm.suggesters.model_suggester import ModelSuggester
from pywhyllm.suggesters.validation_suggester import ValidationSuggester

# LLM suggests causal edges from domain text
modeler = ModelSuggester("gpt-4")
dag = modeler.suggest_relationships(
    treatment, outcome, all_factors, domain_expertises
)

# LLM critiques graph, suggests latent confounders
validator = ValidationSuggester("gpt-4")
critiques = validator.critique_graph(all_factors, dag, domain_expertises)
latent = validator.suggest_latent_confounders(treatment, outcome)
```

---

### causal-learn — Structure Learning
**Repo:** `py-why/causal-learn` (JMLR 2024)
**Library:** `pip install causal-learn`

Algorithms for **discovering** the DAG from data when prior knowledge is unavailable:

| Algorithm | Assumption | Best For |
|---|---|---|
| **PC** | Gaussian / faithfulness | General-purpose constraint-based |
| **GES** | Linear Gaussian | Score-based, faster than PC |
| **LiNGAM** (DirectLiNGAM) | Non-Gaussian linear | Economic / sensor data |
| **FCI** | Allows hidden confounders | Observational data with latent vars |
| **Granger** | Time series | Temporal causal discovery |

```python
from causallearn.search.ConstraintBased.PC import pc
from causallearn.utils.cit import fisherz

cg = pc(data=X, alpha=0.05, indep_test=fisherz)
cg.draw_pydot_graph()
```

---

### EconML — Heterogeneous Treatment Effects
**Repo:** `py-why/EconML` (⭐4,623, MIT, Microsoft ALICE)
**Library:** `pip install econml`

Implements Double ML, Causal Forests, Orthogonal ML for CATE estimation.
Deep integration with DoWhy as the estimation back-end.

---

## LLM Capability Assessment

Based on published benchmarks (as of mid-2025):

| Task | LLM Performance | Notes |
|---|---|---|
| Pairwise causal discovery (named entities) | **97%** (GPT-4, arXiv:2305.00050) | Domain knowledge retrieval, not formal reasoning |
| Counterfactual reasoning (standard benchmarks) | **92%** (GPT-4, arXiv:2305.00050) | Surface-level, not structural |
| Formal causal inference from correlations | **Near-random** (arXiv:2306.05836) | Fails OOD; do not rely on LLM alone |
| Causal graph discovery (>50 nodes) | **Significantly lags algorithms** | CausalBench arXiv:2404.06349 |
| Collider (v-structure) identification | **Poor** | Chains → strong, colliders → fail |

**Hybrid architecture is the correct pattern** (Kıcıman et al. recommendation; Kambhampati LLM-Modulo framework):
LLM = domain expert proposing structure; symbolic library = executing formal math.

---

## Minimal Counterfactual Query Protocol

```python
def causal_counterfactual_query(
    question: str,          # "What would Y be if X had been x'?"
    data: pd.DataFrame,
    treatment: str,
    outcome: str,
    domain_context: str,    # text describing the domain for LLM DAG suggestion
    llm_fn: Callable,
) -> dict:
    """
    Require: data has >= 50 rows; treatment and outcome are column names.
    Guarantee: returns ATE estimate + refutation result + NL interpretation.
    Maintain: DAG is validated before estimation; never skip refutation.
    """
    # 1. LLM proposes DAG
    modeler = ModelSuggester("gpt-4")
    dag = modeler.suggest_relationships(treatment, outcome,
                                         list(data.columns), [domain_context])

    # 2. Validate with constraint-based discovery
    from causallearn.search.ConstraintBased.PC import pc
    cg = pc(data=data.values, alpha=0.05)
    # Merge: trust LLM for edge direction; trust PC for conditional independence

    # 3. DoWhy: identify + estimate + refute
    model = CausalModel(data=data, treatment=treatment, outcome=outcome, graph=dag)
    estimand = model.identify_effect()
    estimate = model.estimate_effect(estimand, method_name="backdoor.linear_regression")
    refute = model.refute_estimate(estimand, estimate,
                                    method_name="placebo_treatment_refuter")

    # 4. LLM interprets
    interpretation = llm_fn(
        f"The causal effect of {treatment} on {outcome} is estimated at "
        f"{estimate.value:.3f} (95% CI: {estimate.get_confidence_intervals()}). "
        f"Refutation p-value: {refute.new_effect:.3f}. "
        f"In plain language for the question '{question}':"
    )
    return {"estimate": estimate, "refutation": refute, "interpretation": interpretation}
```

---

## Anti-Patterns

| Anti-pattern | Fix |
|---|---|
| Asking LLM to compute ATE from correlational data alone | Always route estimation through DoWhy |
| Skipping the refutation step | Always run `refute_estimate` with at least one test |
| Using correlation analysis as a "causal" answer | Check which rung of the ladder the question requires |
| Treating LLM-suggested DAG as ground truth | Validate with causal-learn or domain expert review |
| Applying causal discovery on < 50 samples | Results are unreliable; state this explicitly |

---

## Integration with Skill Library

| Phase | Skill |
|---|---|
| Gathering domain evidence for DAG | `deep-research` |
| Reasoning about causal structure | `reasoning` (deductive framing) |
| Validating causal claims in outputs | `uncertainty-quantification` |
| Tracking causal experiment results | `mlflow` |
| Root-cause analysis in code bugs | `debugging` (not this skill — no observational data) |

---

## Evidence

- Kıcıman et al. arXiv:2305.00050 (TMLR): GPT-4 97% pairwise causal discovery, 92% counterfactual; recommends LLM+formal hybrid
- Jin et al. arXiv:2306.05836 (ICLR 2024 — Corr2Cause): LLMs near-random on pure formal causal inference
- CausalBench arXiv:2404.06349: LLMs vs. algorithms on causal discovery, 19 LLMs evaluated
- Kambhampati arXiv:2402.01817 (ICML 2024 — LLM-Modulo): LLMs need external symbolic verifiers for causal tasks
- DoWhy `py-why/dowhy` ⭐8,101 (active, Apache 2.0): `pip install dowhy`
- causal-learn JMLR 2024 (Vol. 25, No. 60): `pip install causal-learn`
- EconML `py-why/EconML` ⭐4,623 (MIT): `pip install econml`
- pywhy-llm `py-why/pywhy-llm` (experimental): `pip install pywhyllm`
<!-- consolidation:see-also:start -->
## See Also
[[checklist]]  [[gist_correlation_matrix]]  [[nearest-neighbor-chain]]
<!-- consolidation:see-also:end -->
