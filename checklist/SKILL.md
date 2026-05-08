---
name: checklist
description: >
  Pydantic-schema LLM-as-judge validation pattern. Use when a pipeline node must
  produce structured, auditable findings — gaps, violations, proposals, or quality
  verdicts — from LLM output. Covers ItemType enum design, novelty-proof fields,
  decomposed action fields, non-fatal execution contract, review_required flag, and
  cross-run fingerprinting via the agentic_kg_memory throughline model. Subskill of
  agentic-harness. Not a todo tracker — no status lifecycle, no prioritization.
status: active
last_validated: 2026-04-28
---

# Checklist Skill

## When to Use

Use this skill when a harness node must:

- run an LLM-as-judge pass over a generated artifact and return structured findings
- propose new rules, policies, or guard rails from observed failures
- gate a pipeline stage on a structured quality verdict (pass/fail/warn per criterion)
- produce proposals that require human review before being applied

**Not** for tracking work in progress. That is the `todo` skill. A checklist item is
a finding about an artifact, not a task with a lifecycle.

---

## Core Pattern

The pattern has three layers:

```text
ItemType enum      categorize the finding space
ChecklistItem      one structured finding with novelty proof + decomposed action
ChecklistOutput    the full judge output (items list + optional summary)
```

Each layer has a contract. The contracts are what make the output auditable.

---

## 1. ItemType Enum

Define an enum whose values name **pattern categories**, not finding instances.

```python
class ItemType(str, Enum):
    """Pattern categories. Values are class labels, not instance descriptions."""
    unseeded_claim      = "unseeded_claim"
    unmotivated_exit    = "unmotivated_exit"
    premature_thesis    = "premature_thesis"
    # ... domain-specific values
    other               = "other"
```

Rules:
- Values must be generalizable across artifacts, not specific to one run
- Always include `other` as a fallback for genuine outliers
- Keep the enum small enough that the LLM can distinguish values reliably (< 15 values)

---

## 2. ChecklistItem

Every item must prove three things before it is actionable:

1. **What it found** — description + verbatim evidence
2. **Why it is novel** — closest existing coverage + the gap those rules miss
3. **What to do about it** — decomposed action fields, not freeform prose

```python
class ChecklistItem(BaseModel):
    item_type: ItemType
    affected_scope: str = Field(description="e.g. 'Act 2 Scene 1', 'module auth.py', 'stage 3'")
    description: str = Field(description="1-2 sentences describing the finding")
    evidence: str = Field(description="Short verbatim quote or path+line from the artifact")

    # Novelty proof — required. Prevents semantic duplicates.
    closest_existing: list[str] = Field(
        description="Keys/names from the existing rule/policy set closest to covering this finding"
    )
    coverage_gap: str = Field(
        description="One sentence: exactly what the closest existing coverage misses"
    )
    generalizable_rationale: str = Field(
        description="One sentence: why this is a recurring cross-artifact pattern, not a one-off patch"
    )

    # Decomposed action — structured so the proposal is machine-readable
    proposed_key: str = Field(description="snake_case identifier, must not duplicate any existing key")
    trigger_condition: str = Field(description="When to apply: the condition that activates the check")
    failure_condition: str = Field(description="What constitutes a violation — precise enough for an LLM to test")
    scope: str = Field(description="One of: item | cross_item | terminal_only", pattern="^(item|cross_item|terminal_only)$")
    prior_context_required: bool = Field(description="True if the check requires context from prior pipeline stages")
    confidence: float = Field(ge=0.0, le=1.0)

    def render_action(self) -> str:
        """Render structured fields into a target-format string.

        Preconditions: trigger_condition and failure_condition are non-empty.
        Guarantees: output is suitable for direct injection into the existing rule/policy set.
        """
        prefix = "PRIOR-DEPENDENT: " if self.prior_context_required else ""
        return f"{prefix}{self.trigger_condition}; {self.failure_condition}."
```

**The novelty-proof contract is mandatory.** If the LLM cannot explain what the
closest existing coverage misses, the finding is not novel and must not be included.
Include this instruction explicitly in the judge prompt:

> CRITICAL: If you cannot clearly explain why closest_existing do not cover the gap,
> do NOT include this item — a finding already covered by existing rules is not new.

---

## 3. ChecklistOutput

```python
class ChecklistOutput(BaseModel):
    items: list[ChecklistItem]
    summary: str = Field(default="", description="1-2 sentence summary of patterns found")
```

`summary` must have a default. LLMs frequently omit it even when schema-constrained.
A missing `summary` should not invalidate a `ChecklistOutput` with valid `items`.

---

## 4. Execution Contract

The checklist node is **non-fatal by design**. A failed judge pass must never break
the pipeline that called it.

```python
def run_checklist(
    artifact_text: str,
    existing_context: dict[str, str],   # current rules/policies/constraints
    llm_json_fn: Callable,
    output_path: Path,
) -> list[ChecklistItem]:
    try:
        prompt = _build_judge_prompt(artifact_text, existing_context)
        raw = llm_json_fn(
            system="You are a structural critic. Return valid JSON only.",
            user=prompt,
            temperature=0.2,
            max_tokens=4000,
            schema_model=ChecklistOutput,
        )
        output = raw if isinstance(raw, ChecklistOutput) else ChecklistOutput.model_validate(
            raw if isinstance(raw, dict) else {}
        )
        payload = {
            "review_required": True,
            "existing_context_count": len(existing_context),
            "summary": output.summary,
            "proposals": [
                {**item.model_dump(), "rendered_action": item.render_action()}
                for item in output.items
            ],
        }
        output_path.write_text(json.dumps(payload, indent=2), encoding="utf-8")
        return output.items

    except Exception as exc:
        log.warning(f"Checklist failed (non-fatal): {exc}")
        try:
            output_path.write_text(
                json.dumps({"review_required": False, "error": str(exc), "proposals": []}),
                encoding="utf-8",
            )
        except Exception:
            pass
        return []
```

Invariants:
- `output_path` always contains valid JSON after a call, even on error
- `review_required: false` in error output signals human that proposals are empty due to failure, not absence of findings
- `schema_model=ChecklistOutput` on the `llm_json_fn` call — do not use freeform JSON parsing

---

## 5. Judge Prompt Design

> **Model capability rule:** The LLM used to run the checklist judge must be more capable
> than any model whose output it is evaluating. See `evaluator-optimizer` § Judge Model
> Capability Rule. Never use the model-under-test as its own judge.

Structure the judge prompt so the LLM cannot skip novelty proof:

```text
EXISTING CONTEXT (full text — do not propose items that duplicate these):
{json.dumps(existing_context, indent=2)}

ITEM TYPES to look for:
  unseeded_claim: ...description...
  unmotivated_exit: ...description...
  ...

For each finding:
1. Select item_type
2. Name affected_scope
3. Write description (1-2 sentences)
4. Provide verbatim evidence quote
5. List closest_existing — the 1-3 keys from existing context closest to this
6. Write coverage_gap — exactly what those miss
7. Write generalizable_rationale — why this recurs across artifacts
8. Propose proposed_key (snake_case, must not duplicate any key above)
9. Write trigger_condition
10. Write failure_condition (precise enough for an LLM to test)
11. Set scope: item | cross_item | terminal_only
12. Set prior_context_required
13. Rate confidence 0.0–1.0

CRITICAL: If you cannot clearly explain why closest_existing do not cover the gap,
do NOT include it.

If no new findings exist, return an empty items list.

ARTIFACT:
---
{artifact_text}
---
```

---

## 6. Cross-Run Fingerprinting (agentic_kg_memory integration)

A finding reproposed in multiple runs is stronger evidence than a finding seen once.
Track proposals as throughlines using the `agentic_kg_memory` throughline model:

```python
# Fingerprint = frozenset of normalized action structure
def fingerprint(item: ChecklistItem) -> str:
    import hashlib, json
    key = frozenset([
        item.trigger_condition.strip().lower(),
        item.failure_condition.strip().lower(),
    ])
    return hashlib.sha256(json.dumps(sorted(key)).encode()).hexdigest()[:16]
```

Schema (SQLite):

```sql
CREATE TABLE IF NOT EXISTS checklist_throughlines (
    fingerprint     TEXT PRIMARY KEY,
    proposed_key    TEXT,
    trigger_cond    TEXT,
    failure_cond    TEXT,
    item_type       TEXT,
    q_score         REAL DEFAULT 0.5,
    visit_count     INT  DEFAULT 0,
    first_seen_run  TEXT,
    last_seen_run   TEXT,
    status          TEXT DEFAULT 'candidate',  -- candidate | ready | merged | deprecated
    history         JSON DEFAULT '[]'
);
```

Update rule (identical to `agentic_kg_memory` throughline Q-score):

```python
# On each run where the fingerprint appears
visit_count += 1
alpha = 1 / visit_count          # decaying rate: converges to mean entailment strength
r = confidence                   # use item confidence as the reward signal
q_new = q_old + alpha * (r - q_old)
```

Promotion rule:

```python
if q_score > 0.80 and visit_count >= 2:
    status = 'ready'             # surface as merge-ready into existing context
```

This prevents one-off artifact-specific findings from polluting the rule set,
while surfacing genuinely recurring structural patterns automatically.

---

## 7. What Checklist Is Not

| This skill | `todo` skill |
|---|---|
| Findings about an artifact | Tasks to be done |
| No status lifecycle | `pending → in_progress → done → blocked` |
| No prioritization | High / normal / low priority |
| Produced by LLM judge | Produced by agent planning |
| Requires human review before applying | Requires agent execution to complete |
| Cross-run fingerprinting for dedup | Session-scoped, no dedup needed |

Do not mix checklist items into the todo table. They have different shapes and
different ownership semantics.

---

## Reference Implementation

`gap_critic.py` in the storywriter pipeline is the canonical instance of this pattern:

- `GapType` = `ItemType`
- `GapReport` = `ChecklistItem`
- `GapCriticOutput` = `ChecklistOutput`
- `run_gap_critic()` = `run_checklist()`
- Called after each story run; proposals written to `{story_id}_rule_proposals.json`
- Proposed rules feed back into `DEFAULT_AUDIT_RULES` in `constants.py` after manual review

The throughline persistence layer (fingerprinting + Q-score) is not yet implemented
in `gap_critic.py` — it is the next planned enhancement (todo #25).

---

## 8. Eval Pipeline (Offline Batch Evaluation)

The checklist pattern (above) is **online** — it judges one artifact per run.
The eval pipeline is **offline** — it runs a batch of test cases through the system
under evaluation and returns aggregate metrics. Use when you need CI-gated quality gates
or regression detection across versions.

### Distinction from Related Skills

| This section | `evaluator-optimizer` | `autoresearch` |
|---|---|---|
| Offline batch eval of existing system | Online generate→critique→regenerate loop | Hill-climbing on a mutable artifact |
| Golden dataset required | No golden dataset needed | Scorer required, not a golden dataset |
| CI integration, pass/fail per run | Conversational, per-output | Git checkpoint per accepted change |
| Measures regression | Improves output quality | Improves artifact quality |

### Eval Pipeline Schema

```python
class EvalCase(BaseModel):
    case_id: str
    input: Any                  # prompt, code snippet, request — domain-specific
    expected: Any               # golden reference: correct output, target label, etc.
    tags: list[str] = []        # for slice analysis: e.g., ["edge_case", "regression"]

class EvalResult(BaseModel):
    case_id: str
    actual: Any
    score: float                # 0.0–1.0; 1.0 = perfect match or max judge score
    passed: bool                # True if score >= pass_threshold
    judge_reasoning: str = ""   # LLM judge rationale when score is not binary

class EvalReport(BaseModel):
    run_id: str
    model_version: str
    pass_rate: float            # passed / total
    mean_score: float
    results: list[EvalResult]
    slice_stats: dict[str, float]   # tag → pass rate for each tag
    regression_flags: list[str]     # case_ids that passed previously but failed now
```

### Scorer Types

```python
# 1. Exact match (deterministic outputs)
def exact_match(actual: str, expected: str) -> float:
    return 1.0 if actual.strip() == expected.strip() else 0.0

# 2. LLM judge (open-ended outputs)
def llm_judge(
    input: str, actual: str, expected: str, criteria: str, llm_fn: Callable
) -> tuple[float, str]:
    """
    Require: criteria is a precise rubric (not "is it good?").
    Guarantee: returns (score in [0,1], reasoning string).
    """
    prompt = f"""
Criteria: {criteria}

Input: {input}

Reference (expected): {expected}

Actual output: {actual}

Score the actual output against the criteria on a scale of 0.0 to 1.0.
Return JSON: {{"score": 0.0, "reasoning": "..."}}
"""
    return llm_fn(prompt)

# 3. Code execution (test pass rate)
def execution_score(code: str, test_suite: str) -> float:
    """Run generated code against test suite; return fraction of tests passing."""
    ...
```

### Regression Detection

The eval pipeline must detect when previously passing cases now fail.

```python
def detect_regressions(
    current: EvalReport,
    baseline_db: Path,
) -> list[str]:
    """
    Compare current results against the last baseline run stored in sqlite.
    Returns list of case_ids that regressed (passed in baseline, failed now).
    """
    with sqlite3.connect(baseline_db) as conn:
        baseline_passed = {
            row[0] for row in conn.execute(
                "SELECT case_id FROM eval_results WHERE run_id = (SELECT MAX(run_id) FROM eval_runs) AND passed = 1"
            )
        }
    now_failed = {r.case_id for r in current.results if not r.passed}
    return sorted(baseline_passed & now_failed)
```

### CI Integration

Define eval checks as source-controlled markdown, enforced as CI status checks.

```yaml
# .github/workflows/eval.yml
name: Eval Pipeline
on: [pull_request]
jobs:
  eval:
    runs-on: ubuntu-latest
    steps:
      - uses: actions/checkout@v4
      - run: pip install -r requirements.txt
      - run: python eval/run_eval.py --golden eval/cases.jsonl --threshold 0.85
      - name: Check pass rate
        run: |
          PASS_RATE=$(python -c "import json; r=json.load(open('eval_report.json')); print(r['pass_rate'])")
          python -c "assert float('$PASS_RATE') >= 0.85, f'Eval failed: pass_rate={$PASS_RATE} < 0.85'"
```

**CI gate rules:**
- `pass_rate >= threshold` required to merge (default threshold: 0.85)
- Any regression (case that passed before now fails) blocks merge regardless of pass_rate
- Eval report artifact uploaded for every run — required for baseline comparison

### Golden Dataset Governance

```
eval/
  cases.jsonl           # golden test cases (version-controlled)
  baselines/            # one JSON per eval run, named by commit SHA
  run_eval.py           # evaluation harness
  README.md             # how to add cases, how to update baseline
```

**Adding cases:**
- Add one case per observed failure mode — never add hypothetical cases
- Every case must have a tag (`regression`, `edge_case`, `happy_path`, etc.)
- After adding 3+ cases for the same pattern, consider a `checklist` judge rule instead

**Updating baseline:**
- Only update after a deliberate quality improvement (not after fixing a regression)
- Baseline update requires explicit commit message: `eval: update baseline (pass_rate: X → Y)`
<!-- consolidation:see-also:start -->
## See Also
[[agentic-harness]]  [[agent-governance]]  [[deep-research]]  [[validation-artifacts]]  [[react-agent]]
<!-- consolidation:see-also:end -->
