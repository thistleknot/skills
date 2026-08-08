---
name: validation
status: active
last_validated: 2026-07-19
description: Validation and testing protocol. Use when confirming a working implementation, writing tests, or verifying pipeline outputs.
---
# Validation

## Contract
Doesn't count until it runs successfully. Did you actually look at the layer outputs — not just the final state?

Get predecessors working before moving to later stages. When all changes settle: run the full pipeline, archive each artifact, output each layer's inputs and outputs for visual inspection.

## Assert Strategy
- Assert at data checkpoints within the pipeline — not just end-to-end
- Asserts expressed using variables of the feature being validated
- Check presumed vs actual conditions — does data align with expected intent?
- Assert between iterative (loop) processes and after function calls
- Place assert calls in main, not in class functions

## Validation Class Pattern
- Separate validation class with one function per feature
- Processing classes return data; validation class evaluates it
- Validation called from main — not embedded in processing classes

## Paired Feature Validation

When validating extensible features (see `git-workflow/SKILL.md § Paired/Dimensional Feature Testing` and `tdd-agent/SKILL.md § Paired Feature Testing in Red-Green-Refactor`), validate both base and variant in the same test run:

### Single-Instance Validation (Insufficient)
```python
def validate_units():
    base_unit = Unit(name="Rifleman", tech_required=None)
    assert base_unit in available_units()  # ✅ Works
    
    # Problem: Only tests one path
    # Doesn't prove the system is extensible
```

### Paired-Instance Validation (Complete)
```python
def validate_units():
    """Validate base units work AND tech-gated units respect gates."""
    base_unit = Unit(name="Rifleman", tech_required=None)
    tech_gated_unit = Unit(name="LaserSoldier", tech_required="laser_tech")
    
    # Base case: always available
    available = available_units(techs=[])
    assert base_unit in available, "Base units should always appear"
    
    # Variant case: gated by tech
    assert tech_gated_unit not in available, "Tech-gated unit should be hidden"
    
    # After tech unlock: variant appears
    available_with_tech = available_units(techs=["laser_tech"])
    assert tech_gated_unit in available_with_tech, "Tech-gated unit should appear after unlock"
    
    # Coexistence: both work together
    assert len(available_with_tech) > 1, "Both base and variant should coexist"
    print(f"✅ Paired validation passed: {len(available_with_tech)} units available with tech")
```

### Validation Checklist for Paired Features

- [ ] Base feature validated alone (works without variants)
- [ ] Variant feature validated alone (works with new conditions)
- [ ] Both tested in same session (no conflicts)
- [ ] Variant only appears when conditions met (gating logic correct)
- [ ] Artifacts capture both states (screenshots, logs, output samples)
- [ ] Edge cases checked: empty state, partial tech, all techs, tech removal

### Iterative Scale for Paired Testing

**Validation progression:** 1 → 10 → 20 → 100 → 200 → production

- **Stage 1 (n=1):** Single base + single variant. Do they work independently?
- **Stage 2 (n=10):** 10 base units, 3 variants with different tech. Do they interact?
- **Stage 3 (n=20):** Mix of variants, some overlapping tech requirements. Any conflicts?
- **Stage 4+ (n=100+):** Stress test with many variants, partial loads, dynamic changes

Do NOT skip to production without completing all stages. Each reveals different failure modes.

## Iterative Scale
**Debugging progression:** 5 → 10 → 20 → 40 → 80

**Validation progression:** 1 → 10 → 20 → 100 → 200 → production

Unit test on 1 element first — catches n/a, outliers, schema issues (use `break`). Before expensive loops: 10–20 first, then 100–200.

## Sample size for comparative / benchmark evals (A/B config, retrieval, model deltas)

When the test is "does config B beat config A" (retrieval configs, model variants,
prompt changes), the sample size that matters is **the number of independent test
items (queries/records), not the number of scored sub-comparisons**. Two axes get
conflated constantly — separate them explicitly:

- **Items (queries/records) = statistical power.** Drives the confidence interval
  on the delta. This is the axis to grow.
- **Scored pairs / judge calls / pooled candidates = cost.** Grows with items ×
  pool-depth. Inflating this (deeper pools, more candidates per query) raises
  *cost*, not power — a bigger pool does not tighten the delta CI.

### Default: n≈20 items, detect deltas ≥5%

**A lift worth shipping shows at n≈20 within a ~5% delta.** If an effect needs
n=100 to surface, it is too small to productionize — disposition it as "no
shippable lift" rather than chasing significance. Start at 20; only grow the
*item* count (not the pool) if a delta lands right at the 5% threshold and the
decision hinges on it.

### Prefer deterministic ground truth over an LLM judge when you can define relevance

If you authored the test items, you already know the right answers — encode a
**fixed gold set per item** (deterministic labels) instead of pooling candidates
and paying an LLM judge per pair. Deterministic labels: 0 judge cost, independent
ground truth (no judge saturation), runs in seconds → you can afford more items.
Reserve the LLM-judge/pooling design for when relevance genuinely can't be
pre-specified. Watch for **judge saturation** — if the judge marks a large
fraction of candidates "relevant", the metric rewards recall *volume*, not
correctness, and can no longer discriminate configs.

### The ground-truth definition IS the experiment

A technically-clean eval on the wrong relevance definition gives a confidently
*wrong* decision. Before trusting a comparative result, verify the test items
live in the regime the hypothesis is about (e.g. a graph/expansion leg only earns
its keep on queries whose answer is NOT co-located with the query in the base
signal's space — testing it on easy in-regime queries measures nothing).
Report deltas **per regime/cutoff**, not one global number — an effect can flip
sign between the head (top-k precision/MRR) and the tail (deep recall).

## Reversibility
Transformations must be reversible. Validate both forward and backward data perspective.

## Development Workflow
Document (features) → Unit Test (core functionality) → Integrate → Commit

## Testing Hierarchy

Apply this progression when validating any new dimension, feature, or pipeline process:

| Stage | What it tests | Pass condition |
|---|---|---|
| **Smoke** | Does the process run at all for this dimension/feature? | No crash, output produced |
| **Unit (n=1)** | One record through the full process | Correct output for that record |
| **Contract (sample)** | A representative sample across edge cases | Schema and contract assertions hold |
| **Cross-feature integration** | This feature interacting with other dimensions | No conflicts, shared state correct |
| **Subset integration** | A bounded subset of the full data (minimizes commitment time) | Stable end-to-end within the subset |
| **Full** | All data | Production-equivalent correctness |

Do not skip stages. Each stage reveals a different failure class. A smoke pass does not imply unit correctness; a unit pass does not imply cross-feature stability.

For schema translation workflows: "smoke" means the CLI/UI wrapper accepts the dimension as input; "unit" means one record translates and loads in the target system correctly; "contract" means the mapping table holds across a sample of records.

### Endless-data warning

If a process (training, embedding, BM25 indexing, etc.) would take **more than 2 hours** to run on the full dataset, stop and surface this before starting:

> "Full run is estimated at N hours. Goal is convergence / parity — not exhaustive processing. Recommended alternatives:"
> - **Reduced epochs** — stop when validation loss plateaus (early stopping), not at a fixed epoch count
> - **Reduced record count** — a representative subset (e.g. stratified sample) converges to the global mean faster than the full corpus; use as a proxy for correctness
> - **Both** — short run, fewer records, validate parity against a held-out reference metric

**When parity is the goal (not exhaustive coverage):** the model or index needs to converge on a global mean with minimum error loss — it does not need to see every record. A well-sampled subset is sufficient and avoids over-indexing on outliers in a long tail.

Flag this at planning time, not after a multi-hour run has already started.
<!-- consolidation:see-also:start -->
## See Also
[[codebase-knowledge-graph]]  [[validation-artifacts]]  [[git-workflow]]
<!-- consolidation:see-also:end -->
