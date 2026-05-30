---
name: llm-pipeline-layer-tdd
description: >
  Gate-based TDD for layered LLM/ETL pipelines. Test each layer in isolation
  with spoofed inputs. Do not proceed to layer N+1 until layer N passes its
  contract on multiple seeds. When a layer fails, fix that layer's contract
  (prompts/schema/post-processor) â€” never patch the final output and call it
  done. Running the full pipeline and checking the end result is not testing.
status: active
last_validated: 2026-05-28
---

# LLM Pipeline Layer TDD

## The Law (verbatim)

> "Unit test driven development means you get the process correct through
> proper contracts. You don't proceed to the next scene until you confirm the
> prior scene was generated properly with various seeds. Else you fix the
> inputs â€” and to do that you fix the contracts for the prior layer's outputs.
> You're trying to do ETL all at once, then checking at the end. That's clearly
> not how you test ETL. You do small unit tests."

**Do not proceed to layer N+1 until layer N passes its contract on multiple
diverse seeds.**

Running end-to-end and observing bad final output is not testing. It is
laundering errors across layers. You cannot tell which layer broke or why.

---

## The Problem This Solves

Running a full LLM pipeline end-to-end and inspecting the final output is **not
testing**. It is running the pipeline. When the output is bad you have no idea
which layer broke, because every layer's failure can look like every other
layer's failure by the time it reaches the end.

This is exactly the ETL problem. You would never write an ETL job and then
debug it by reading the final database table. You test each transform unit in
isolation. LLM pipelines are ETL pipelines where the transforms are prompts.

---

## What "Contract" Means

Each layer has three parts:

```
Input shape    what the layer receives â€” fields, types, required vs optional
Output shape   what the layer must return â€” fields, types, non-empty constraints
Quality gate   the binary pass/fail criteria that confirm the output is usable
               as input for the next layer
```

The contract is not the code. The contract is the **agreement between layers**.
When a layer fails its gate, the fix is in the contract: the system prompt, the
schema, the quality threshold, or the post-processor for that layer â€” not in
the downstream layer that first made the problem visible.

---

## The Protocol

### 1 â€” Write the contract before testing

If you cannot specify all three parts (input shape, output shape, quality gate)
for the layer you are about to test, the layer does not have a defined contract.
Fix the contract definition first. Do not test what you cannot specify.

### 2 â€” Fabricate synthetic inputs

Do **not** use real outputs from the prior layer as test inputs. Real outputs
carry that layer's failures and entangle root causes.

Fabricate the minimum valid input that satisfies the input contract. Make it
realistic â€” representative of what a live run would actually send.

### 3 â€” Run the layer in isolation

Call the layer function directly. Do not run the full pipeline. One function
call. Inspect what it returns before any downstream processing sees it.

### 4 â€” Apply the quality gate

Check every criterion in the output contract against the result. Record which
ones pass and which ones fail. A partial pass is a failure â€” the gate is binary.

### 5 â€” If it fails: fix the contract, not the output

Identify which criterion failed. Trace it to the contract component that owns it:

```
criterion failed at output  â†’  was the input valid?
                                  yes â†’ fix this layer's prompt or schema
                                  no  â†’ fix the prior layer's output contract first
```

Fix only the identified component. Then re-run **all seeds**, not just the one
that was failing. A fix that passes seed A but breaks seed B is not a fix.

### 6 â€” Gate before proceeding

Only move to the next layer when:
- every quality gate criterion passes
- every seed passes
- the layer's output is a valid input for the next layer

If any seed still fails: repeat from step 3.

---

## Seed Requirements

Minimum 3 seeds per layer. Each seed must exercise a different failure mode:

| Seed | What it covers |
|---|---|
| A â€” standard | Normal input, expected genre, expected POV |
| B â€” edge | Minimal treatment, no prior context, short content |
| C â€” stress | Multiple characters, long prior context, complex scene |

One seed that passes is anecdotal. Three diverse seeds that all pass is
evidence the layer's contract is stable.

---

## Fix Sequence When a Layer Fails

Apply in order. Do not jump ahead:

```
1. Input contract violation   â†’ the prior layer produced malformed output; fix that layer first
2. System prompt ambiguity    â†’ a rule is missing or underspecified; add it explicitly
3. Post-processor gap         â†’ a deterministic strip or repair step is missing or incomplete
4. Quality threshold mis-set  â†’ recalibrate against observed failures; do not simply lower the bar
```

Post-processors that compensate for upstream prompt ambiguity are technical
debt. They mask the root cause. Fix the prompt first.

---

## Anti-Patterns

| What happened | Why it is wrong |
|---|---|
| Ran the full pipeline and read the final output | Cannot locate which layer broke |
| Fixed a bad scene by adding a post-processor | The treatment that fed it may be the actual failure |
| Moved to scene 2 after scene 1 looked "mostly ok" | "Mostly ok" is not a gate. Define the criterion. |
| Used real prior-layer output as test input for a broken layer | Carries upstream failures; root cause stays entangled |
| Ran one seed and declared the layer working | One seed is not coverage |
| Fixed the failing seed without re-running the others | Regression on seed B is now hidden |

---

## Storywriter v4 Layer Gates (Reference)

### L1 â€” Arc layer (4b): `generate_premise`
- `title`, `genre`, `world_description`, `core_conflict`, `cost_mechanism` all non-empty
- `themes` is a non-empty list
- `cost_mechanism` is a specific sentence, not a generic placeholder

### L2 â€” Characters (4b): `generate_characters`
- Returns a non-empty list
- Every character has `name`, `role`, `pronouns`, `arc`, `summary`
- At least one character has `role == "protagonist"`
- All `pronouns` fields non-empty

### L3 â€” Plot structure (4b): `generate_plot_structure`
- `acts` is a non-empty list
- Every act's first scene has `scene_num == 1` (numbering restarts per act)
- Every scene has non-empty `beat`, `pov`, `location`

### L4 â€” Architecture (4b): `plan_story_architecture`
- All of `character_seeds`, `act_bridges`, `scene_commitments` are lists (may be empty)
- `scene_commitments` reference only valid act numbers

### L5 â€” Backward plan (4b): `generate_backward_plan`
- `climax_spec` has non-empty `protagonist_decision` and `required_presence`
- `forward_reqs` is a dict keyed by `(act, scene_num)` tuples

### L6 â€” Scene treatments (2b): `generate_scene_treatments`
- Keyed by every `(act, scene_num)` pair in the plot structure
- Every treatment has `characters_present` (non-empty list), `pov_want`, `pov_decision`, `thematic_position`
- `thematic_position` varies across scenes (not verbatim repeated)

### L7 â€” Prose (0.8b): `generate_scene` â†’ `SceneOutput`
- `prose` non-empty, no scaffold headers (`Act N`, `Scene N`, `###`)
- Word count â‰¥ `min_scene_words`
- No first-person narration outside quoted dialogue
- Repetition ratio < 0.5 (`_check_repetition_ratio`)
- No Qwen3 think-token artifacts (`<think>`, `No_think`)

### L8 â€” Coherence (2b): `check_coherence`
- Returns `(score: float, feedback: str)`
- Score in `[0, 1]`; well-formed prose â‰¥ 0.70
- Feedback non-empty
- `she/he` alternation for different named characters is not flagged as POV violation

---

## Relation to Other Skills

| Need | Skill |
|---|---|
| Full pipeline output is wrong; root cause unknown | `pipeline-input-review` |
| Layer throws an exception or wrong type | `debugging` |
| Quality criteria need formal specification | `validation` |
| Prose quality needs iterative LLM improvement | `evaluator-optimizer` |

<!-- consolidation:see-also:start -->
## See Also
[[tdd-agent]]  [[pipeline-input-review]]  [[evaluator-optimizer]]  [[validation]]
<!-- consolidation:see-also:end -->
