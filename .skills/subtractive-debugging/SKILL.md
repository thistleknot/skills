---
name: subtractive-debugging
description: >
  Systematic regression isolation by subtracting from a known-good state.
  Invoke when a feature used to work, many changes landed, and you need the
  first cascaded mismatch instead of another hypothesis chain. Triggers on:
  regression, last-known-good, bisect, first-bad-change, shrink-the-surface.
status: active
last_validated: 2026-05-15
supersedes: []
validation_method: session
---

# Subtractive Debugging

## Context

Use this skill when the problem is not **"what might be wrong?"** but
**"what changed between a known-good state and now?"**

This is for regressions where speculative debugging has already started to sprawl.
The contract is to anchor one stable control, define one exact property, subtract
from the current state until only the first cascaded mismatch remains, and only
then patch.

---

## Step 1 — Define the property and the control

Do not start with the broken artifact alone. Name:

1. the exact property you are testing
2. one known-good control that proves the mechanism itself still works
3. the current bad state
4. the last known good baseline

If you cannot name all four, you are not doing subtractive debugging yet.

```powershell
git --no-pager log --oneline -20 -- <affected-files>
git --no-pager diff --stat <known-good>..HEAD -- <affected-files>
```

Expected outcome: one regression statement in the form:

```text
Property: <what should still hold>
Control: <entity/path that still satisfies it>
Bad state: HEAD
Known-good baseline: <commit/tag>
```

---

## Step 2 — Shrink the surface to one closure layer

Do not debug through the whole pipeline.

Choose the narrowest layer that can still express the property:

- loader closure
- schema closure
- import/display closure
- runtime behavior closure
- artifact/render closure

Then build a checker for that layer only. The checker should answer
**"what differs from baseline at this exact surface?"** not
**"does the whole app still seem okay?"**

```powershell
# Example shell for a surface-specific checker
powershell -ExecutionPolicy Bypass -File .\surface-check.ps1 -BaselineCommit <known-good>
```

Expected outcome: a machine-readable report listing changed entities and invariant violations at one layer.

---

## Step 3 — Compare signatures, not files

Raw file diffs are too noisy once a wide import pass lands.

Model each relevant entity as a compact signature of the fields that matter to the
property. Then compare current signatures to baseline signatures.

Typical signatures:

- icon bundle ids
- string ids
- dependency ids
- section/token ids
- schema-required fields

```text
Entity signature =
  icon_id + gameplay_id + historical_id + prereq_id + statistics_id + stattext_id
```

Expected outcome: a list of:

- entities added since baseline
- entities whose signatures changed
- entities missing required fields or sections

---

## Step 4 — Subtract by interval, then by entity

First shrink the history interval. Then shrink the changed entity set.

Use the control to confirm the mechanism is still intact while the candidate set
gets smaller. If the control changed too, your chosen surface is wrong or too broad.

```powershell
# Coarse interval
powershell -ExecutionPolicy Bypass -File .\surface-check.ps1 -BaselineCommit <older-good>

# Tighter interval
powershell -ExecutionPolicy Bypass -File .\surface-check.ps1 -BaselineCommit <later-good>
```

Expected outcome:

1. current vs old-good gives a broad changed set
2. current vs later-good collapses that set
3. one commit interval or one import pass becomes the introducing boundary

---

## Step 5 — Name the first cascaded mismatch

Do not stop at **"these files changed."** Extract the first property violation that
explains downstream symptoms.

Good outputs:

- shared bundle introduced where uniqueness was required
- entity now points at missing section ids
- display layer reuses the loader layer's fallback ids
- baseline-unique mapping became many-to-one

Bad outputs:

- "a lot changed"
- "probably this commit"
- "the import path looks suspicious"

Expected outcome: one claim in the form:

```text
The first cascaded mismatch is <X>.
It was introduced between <baseline> and <current interval>.
It affects <entities>.
The control <control-id> remained stable.
```

---

## Step 6 — Patch only the isolated mismatch

Once the first cascaded mismatch is named, patch that boundary and rerun the same
checker. The checker is the regression test for the debugging loop.

```powershell
powershell -ExecutionPolicy Bypass -File .\surface-check.ps1 -BaselineCommit <known-good>
```

Exit only when:

1. the checker passes or the suspect set shrinks exactly as expected
2. the control remains unchanged
3. the original symptom is now explained by a bounded delta rather than a theory cloud

---

## Example

Concrete session instantiation:

- Property: Great Library import bundles remain unique where distinct pages are required
- Control: `IMPROVE_ARCOLOGIES`
- Bad state: `HEAD`
- Known-good baseline: `8fc48ba`, then tightened to `642ce10`
- Surface checker: repo-local `.modding-harness\gl-regression.ps1`

~~~powershell
powershell -ExecutionPolicy Bypass -File ".modding-harness\gl-regression.ps1" -BaselineCommit 8fc48ba
powershell -ExecutionPolicy Bypass -File ".modding-harness\gl-regression.ps1" -BaselineCommit 642ce10
~~~

This isolated one real regression surface:

```text
Shared Great Library bundle introduced or expanded:
IMPROVE_SHRINE, IMPROVE_SHRINE_EGYPT, IMPROVE_SHRINE_ZOROASTER
```

with `IMPROVE_ARCOLOGIES` unchanged across both baselines.

---

## Dead Ends — Do Not Use

### Debugging the whole pipeline between each guess

```powershell
# BROKEN — too much blast radius, no isolating signal
run-the-game.exe
click-around
guess
edit
run-the-game.exe
```

This creates narrative, not evidence. You need a narrower surface and a repeatable checker.

### Treating raw file churn as the regression

```powershell
# BROKEN — wide import commits make this too noisy
git --no-pager diff <good>..HEAD
```

A big diff is not a cause. Convert the diff into entity signatures and invariant violations first.

### Omitting the known-good control

```text
Broken entity: <target only>
```

Without a stable control, you cannot tell whether the mechanism failed globally or only a subset regressed.

### Patching before the interval collapses

```text
Maybe this field is wrong. Try changing it.
```

If the same class of error keeps reappearing, stop patching. Collapse the interval and the suspect set again.

---

## Applicability Envelope

**Works well when:**
- A feature clearly used to work at some earlier commit, tag, or artifact state
- The failure can be expressed as a narrow property at one layer
- A stable control entity or path exists
- Recent changes are broad enough that direct file diff reading is too noisy
- You can build a deterministic checker for the property

**Fails or degrades when:**
- No known-good baseline exists anywhere reachable
- The symptom is intermittent and not tied to a stable property
- The chosen checker still spans multiple layers and cannot isolate responsibility
- The system has no durable artifacts or history to compare

**Environment assumptions:**
- Git history or equivalent versioned checkpoints exist
- The agent can inspect both current and baseline artifacts
- The property can be expressed as entity signatures or invariant checks
- A known-good control can be identified on the same surface
<!-- consolidation:see-also:start -->
## See Also
[[stratified-quota-sampling]]  [[synthetic-data]]  [[tdd-agent]]
<!-- consolidation:see-also:end -->
