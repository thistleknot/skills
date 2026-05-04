---
name: validation
status: active
last_validated: 2026-04-28
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

## Reversibility
Transformations must be reversible. Validate both forward and backward data perspective.

## Development Workflow
Document (features) → Unit Test (core functionality) → Integrate → Commit
