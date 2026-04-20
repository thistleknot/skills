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

## Iterative Scale
**Debugging progression:** 5 → 10 → 20 → 40 → 80

**Validation progression:** 1 → 10 → 20 → 100 → 200 → production

Unit test on 1 element first — catches n/a, outliers, schema issues (use `break`). Before expensive loops: 10–20 first, then 100–200.

## Reversibility
Transformations must be reversible. Validate both forward and backward data perspective.

## Development Workflow
Document (features) → Unit Test (core functionality) → Integrate → Commit
