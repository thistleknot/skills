---
name: human-verification-checkpoints
description: >
  Surface real, human-verifiable artifacts at critical junctions instead of proceeding on
  self-assessed "it works." Use during any multi-step or pipeline work whenever an output drives
  downstream steps and would be expensive to unwind — prompts, rubrics, specs, schemas,
  reward/metric definitions, interfaces, data transforms. Emit the ACTUAL artifact (rendered
  prompt, sample outputs, real run logs) to a file the human can read; pause for sign-off at the
  highest-stakes gates, and for fast goal-iteration emit a reviewable verification log instead of
  going silent. Prevents convincingly-wrong outputs from compounding into full-pipeline
  re-litigation. Trigger when: defining/changing a prompt/rubric/reward/schema, declaring
  something "verified/proven/works", or about to build on an output that many later steps depend on.
---

# Human Verification Checkpoints

## Why this exists
The model can be **convincingly wrong** — produce a plausible output, assert it works, and build on
it. Unverified outputs then compound silently until the whole pipeline must be re-litigated. The
antidote: at critical junctions, **float up a concrete artifact the human can verify**, instead of a
confident summary of your own work. Treat the human as the in-the-loop sanity check / unit test.
Confident prose is NOT evidence.

## What counts as a "critical junction"
Any output that downstream work depends on AND is expensive to unwind:
- A prompt / rubric / spec that drives many downstream computations (e.g. an LLM-as-judge prompt).
- A schema, data transform, or interface that everything consumes.
- A reward / scoring function or metric definition.
- An architectural or design decision.
- Heuristic: *"if this is wrong, do we redo a lot?"* → yes → it's a junction.

## The protocol
1. **Show the artifact, not a description of it.** Write the *actual* rendered thing to a file — the
   real prompt with real data, the real sample outputs, the real config/diff, the real run log.
   Never substitute prose ("the prompt includes X") for the artifact itself.
2. **Make it a durable pipeline output.** Emit these artifacts to files (e.g. a `review/` or
   `artifacts/` dir), registered like any other pipeline output — so they exist whether or not you
   remember to surface them, and can be re-reviewed later. Generate them FROM the live code path so
   they cannot drift from what actually runs.
3. **Float it up explicitly.** Point the human to the file and state the decision that is theirs to
   make. Do not declare it sufficient on their behalf.
4. **Pick the gate type:**
   - **Blocking gate** (pause for sign-off): highest-stakes, most-expensive-to-unwind junctions.
     Stop and require approval before proceeding.
   - **Async verification log** (don't go silent): when iterating fast on goals, emit a reviewable
     log/artifact the human *can* inspect. If all is well, no correction needed — but the trail
     prevents silent compounding.
5. **Back every "it works" claim with execution.** If you say "verified / passes / proven / fixed,"
   it must be backed by a runnable check (a test, a rendered output, a real run) whose result you
   SHOW — not by your reading of the code.

## Anti-patterns (do NOT)
- Summarize/paraphrase an output instead of rendering it.
- Mark work "done/verified" from self-review rather than an executed check or human review.
- Proceed to build on an unverified artifact.
- Bury a critical artifact in chat scroll instead of writing a file.
- Use a confident tone as a substitute for evidence.

## How to apply (cheap, not heavy)
- One small artifact + one pointer line per junction is enough; this is not ceremony.
- Prefer a tiny dumper script wired into the pipeline (renders the live artifact to a file) over an
  ad-hoc chat paste — it stays in sync and is re-runnable.
- When unsure whether something is a junction, it probably is — emit the artifact.
