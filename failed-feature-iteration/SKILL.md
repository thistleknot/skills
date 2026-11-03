---
name: failed-feature-iteration
description: Track failed feature implementations in persistent todos to enable iterative refinement across varying approaches (e.g., map-reduce, embedding analogies) until successfully encapsulated.
status: active
last_validated: 2026-06-07
supersedes: []
validation_method: session
---

# Failed Feature Iteration

**Purpose:** Prevent knowledge loss when feature implementations fail. Transform failures into structured iteration opportunities with explicit alternative approaches.

## Trigger

Activate this skill when:
- A feature implementation fails validation (tests, artifacts, or acceptance criteria)
- A feature is archived or rolled back due to blockers
- A recurring blocker pattern emerges across multiple attempts
- An approach is proven infeasible after significant effort

**Do NOT** simply archive and forget. That discards valuable context about what doesn't work.

## Protocol

When a feature fails:

### 1. Create High-Priority Todo

Immediately create a todo with prefix `[FAILED-FEATURE]`:

```
[FAILED-FEATURE] Implement X using approach Y
Priority: high
Status: in_progress
```

### 2. Document Failed Approach

In the todo description, explicitly record:

```
## Failed Attempt
- **Approach**: "Attempt 1: Direct RAG retrieval with vector similarity"
- **What was tried**: Specific implementation details, configuration, parameters
- **Why it failed**: Concrete failure mode (validation error, performance issue, architectural blocker)
- **Evidence**: Link to specific files, artifacts, or memory bank entries containing the failed attempt
  - Example: `See: skills/my-feature/attempt1/`, `validation_artifacts/2026-05-03-failure/`
  - Example: `Memory bank: ~/memory-bank/projects/myproject/progress.md (entry 2026-05-03)`

## Alternative Dimensions to Vary
For the next attempt, explicitly define 2-3 orthogonal dimensions to change:

1. **Approach variation**: "Attempt 2: Map-reduce summarization with chunking"
2. **Algorithm variation**: "Attempt 3: Embedding analogy + graph traversal"
3. **Data variation**: "Attempt 4: Synthetic data augmentation with class balancing"
4. **Architecture variation**: "Attempt 5: Two-stage pipeline with validation gate"

Each dimension should be:
- Concrete (specific technique or method)
- Testable (can be implemented and validated)
- Orthogonal (different axis of variation from previous attempts)

## Success Criteria
Define what "working" means for the next attempt:
- Validation metrics to achieve
- Artifacts to produce
- Acceptance criteria

### 3. Link References

Ensure the todo includes:
- Direct links to failed attempt code/artifacts
- Relevant memory bank entries
- Related skills that might help (e.g., `validation-artifacts`, `debugging`)
- Any constraints or non-negotiables from stakeholders

## Lifecycle

- The `[FAILED-FEATURE]` todo remains `in_progress` or `pending` with **high priority** until the feature is successfully integrated and validated.
- Each iteration updates the todo with:
  - New attempt number and approach
  - What was different this time
  - Results (pass/fail, metrics)
  - Lessons learned
- Only when the feature passes validation with supporting artifacts does the todo move to `completed` state.
- Upon completion, add a "resolved by" link pointing to the successful implementation and its validation artifacts.
- Archive the full iteration history in the project's memory bank under `progress.md` with cross-references to the final successful artifact.

## Example Todo

```
[FAILED-FEATURE] Implement PDF table extraction with VLM
Priority: high
Status: in_progress

## Failed Attempt 1
- Approach: Direct VLM inference on full page images
- What was tried: Used docling + GPT-4o on 300 DPI scans
- Why it failed: Tables with complex spanning cells produce malformed CSV; accuracy 62%
- Evidence: skills/pdf-extraction/attempt1/, validation_artifacts/2026-05-03-table-failure/

## Alternative Dimensions
1. Attempt 2: Pre-process with tabula for structure, VLM for cell content only
2. Attempt 3: Hybrid: camelot for simple tables, VLM only for complex spans
3. Attempt 4: Train layout classifier with class-balancing to route to correct extractor

## Success Criteria
- Table extraction F1 > 90% on holdout set
- CSV output validates with pandas read_csv
- Visual diff shows <5% cell mismatch

Related: [[pdf-extraction]] [[validation-artifacts]] [[class-balancing]]
```

## Integration with Other Skills

- **`validation-artifacts`**: Every iteration must produce validation artifacts proving the attempt outcome
- **`debugging`**: Use root-cause protocol to understand why each attempt failed before designing the next
- **`agentic-harness`**: Route failed feature todos as high-priority tasks in the harness queue
- **`memory-bank`**: Record iteration history in `progress.md` to preserve institutional knowledge
- **`skill-wiki`**: If the failure reveals a new pattern or anti-pattern, consider crystallizing it as a tribal knowledge entry

## Anti-Patterns to Avoid

- ❌ **Archive and forget**: Simply closing the todo without recording lessons
- ❌ **Random variation**: Changing multiple variables at once; isolate one dimension per attempt
- ❌ **No evidence**: Attempting without producing validation artifacts; "I think it's better" is insufficient
- ❌ **Infinite loop**: More than 5-7 attempts without success → escalate to architecture review (may need different skill)
- ❌ **Low priority**: Letting failed-feature todos languish; they are high-priority by definition

---

<!-- consolidation:see-also:start -->
## See Also
[[validation-artifacts]]  [[debugging]]  [[agentic-harness]]  [[memory-bank]]  [[skill-wiki]]
<!-- consolidation:see-also:end -->
