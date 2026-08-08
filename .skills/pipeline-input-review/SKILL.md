---
name: pipeline-input-review
description: >
  Protocol for partitioning a pipeline problem to its minimal failing unit,
  verifying inputs at that exact stage, and giving an agentic harness a
  hyper-focused problem statement before attempting any fix. Use when a
  harness produces wrong, blurry, or misaligned output and you are tempted to
  patch the output rather than find the upstream cause. Canonical trigger:
  pipeline output looks wrong, preceded by a symptom that could have been
  caught one stage earlier (colour blurring, crop offset, mis-parsed grid).
status: active
last_validated: 2026-05-22
supersedes: []
validation_method: session
---

# Pipeline Input Review

## Core Thesis

**A harness that patches its own outputs without reviewing upstream inputs is
not debugging — it is laundering errors.**

When agentic work produces bad output, the instinct is to re-prompt, tweak
parameters, or post-process the result. The right move is to identify the
boundary just before the failure, materialise the actual inputs at that
boundary, and only then decide what to fix. Everything else is guessing.

This is *not* the same as general debugging (which traces from error lines
forward). It is specifically about **pipeline partitioning before harness
dispatch**: splitting the problem so the harness receives only the smallest
coherent unit that can express the failure.

---

## The Problem It Solves

Multi-stage pipelines fail in ways that look like output problems but are
really input problems one stage upstream.

**Canonical example — Civ2 sprite extraction:**

| Stage | What was visible | What was actually broken |
|---|---|---|
| Grid detection | Output cells looked "blurry" | Green-line grid was being mis-parsed |
| Cell extraction | Icons appeared mis-cropped | Wrong column/row boundaries from stage above |
| Cleanup | Crop was eating real content | Crop ran before alpha cleanup inflated the bbox |

At each stage, patching the output (rescale, re-crop, post-process) obscured
the upstream cause. Once the grid parsing was fixed, all downstream stages
corrected themselves.

**Pattern:** blurry or offset output → misaligned crop → wrong grid → the
error was introduced at stage 1, but only visible at stage 3.

---

## Protocol

### Step 0 — Name the symptom precisely

Before touching any code, write a one-sentence symptom statement:

```
The output of <stage N> produces <exact wrong thing> when the input is <known-good input>.
```

If you cannot fill in all three blanks, you do not have a concrete symptom yet.
Do not dispatch to a harness until you can.

### Step 1 — List the pipeline stages

Write them out in order. Each stage has an input and an output. Do not skip
stages because "they obviously work" — that assumption is exactly where the
bug lives 80% of the time.

```
Stage 1: [input] → [transform] → [output]
Stage 2: [stage 1 output] → [transform] → [output]
...
Stage N: symptom visible here
```

### Step 2 — Walk backwards from the symptom

Starting at stage N, ask for each stage going backwards:

> *"If this stage's INPUT were correct, would its output be correct?"*

If yes: the bug is upstream of this stage.
If no or unsure: materialise the actual input and inspect it.

**Stop at the first stage where you cannot answer "yes" with evidence.**
That is the stage to fix.

### Step 3 — Materialise inputs at the boundary

Before dispatching to a harness, produce a concrete artefact showing exactly
what enters the failing stage:

- Write the raw input to a file
- Render it visually if it is image/spatial data
- Print the parsed structure before transformation

The harness must see the actual input, not a description of what the input
*should* be. If you describe the input without materialising it, you are still
guessing.

### Step 4 — Write a hyper-focused problem statement

Give the harness exactly one stage to fix. Include:

1. The stage name
2. The exact wrong behaviour (with the materialised input as evidence)
3. The expected correct behaviour
4. The constraint: *do not touch other stages*

```
Fix stage: [stage name]
Input:     [file path or inline sample]
Current:   [what it produces now]
Expected:  [what it should produce]
Constraint: change only [stage name]; other stages are not in scope.
```

If the problem statement requires more than one stage to express, go back to
Step 2 — you have not found the root stage yet.

### Step 5 — Verify the fix does not break adjacent stages

After fixing the identified stage, re-run the full pipeline with the
previously-failing input. Confirm:

- [ ] The fixed stage now produces the expected output
- [ ] Downstream stages produce correct output (not just "different")
- [ ] The fix does not require any downstream stage to compensate

If downstream stages now need adjustment, that is scope expansion — handle
each as a separate partitioned problem, not in the same pass.

---

## Harness Dispatch Rules

When assigning this work to an agentic harness:

1. **One stage per task.** Do not combine "fix the grid parser and fix the
   crop logic" into one harness call. The harness will conflate them.

2. **Provide evidence, not descriptions.** Attach the materialised input file.
   A harness working from a description will hallucinate the input.

3. **State the constraint explicitly.** "Do not touch X" is load-bearing.
   Without it, a harness will refactor adjacent code and introduce new failure
   modes.

4. **Review the output of the fixed stage before running the full pipeline.**
   One verified stage is worth more than one full pipeline run that hides the
   error.

---

## When to Use This Skill vs Others

| Situation | Use |
|---|---|
| Output is wrong; pipeline has multiple stages | **This skill** — partition first |
| Error has a stack trace or exception | `debugging` — trace from error line |
| Regression after a known-good commit | `subtractive-debugging` — walk commits |
| Harness is producing incoherent cross-stage output | `agentic-harness` — coherence gate |
| Wrong output for one record, correct for others | `schema-induction` — find the differentia |

The key differentiator: this skill activates when there is **no error message**
but the output is visibly wrong. The absence of an exception is what makes it
tempting to patch outputs instead of finding the upstream cause.

---

## Lessons That Generated This Skill

1. **Civ2 sprite extraction (2026-05):** Unit icon B5 was being cut off.
   Root cause traced through three stages: crop happening before alpha cleanup
   → artifact pixels inflating the bounding box → content being excluded.
   Fix required changing stage order, not adjusting the crop parameters.
   Lesson: the symptom (cut-off content) pointed at crop; the root cause was
   in cleanup ordering one stage earlier.

2. **Civ2 grid parsing (2026-05):** Misaligned sprite extractions preceded by
   blurry colour rendering. Root cause: green-line grid coordinates were being
   mis-parsed. Every downstream stage (cell extraction, cleanup, crop) was
   operating on wrong cell boundaries. No amount of post-processing fixes the
   output of a mis-parsed grid.

3. **CTP2 UI TGAs (2026-05):** `Targa Load Error` dialogs appeared one at a
   time, one per game session. The first attempted fix scanned 854 UI TGAs
   referenced in LDL layout files and created loose grey placeholders for all
   missing names. That stopped the dialogs but broke the menu: loose TGAs
   overrode packed UI art and produced a black/grey interface. The corrected
   lesson is narrower: enumerate repeated missing-asset errors, but verify
   whether loose files override a packed-asset layer before creating them.
   Only create known-safe emergency assets; do not blanket-stub visual UI.

---

## Anti-Patterns

| Anti-pattern | Why it fails |
|---|---|
| "Let me just re-run with different parameters" | Does not change what enters the failing stage |
| Patching the output and calling it fixed | Next stage or next session surfaces the same root cause in a different form |
| Dispatching to a harness with a vague problem statement | Harness fixes the wrong stage, sometimes making things worse |
| Inspecting stage N output without inspecting stage N input | Confirms the symptom; does not locate the cause |
| Fixing multiple stages in one pass | Makes it impossible to know which fix resolved the problem |

<!-- consolidation:see-also:start -->
<!-- consolidation:see-also:end -->
