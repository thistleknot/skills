# Agentic Harness — History

Changelog and supersession record for `agentic-harness/SKILL.md`.
Current version of the contract is always in SKILL.md; this file records what changed and why.

---

## 2026-05-02 — DSPy + TextGrad grounded the evaluation lane
**Changed:** Added explicit evaluation-stack guidance to `SKILL.md`: `checklist`
for structured audit artifacts, DSPy-style metric/reward compile-refine loops
for scoreable modules, and TextGrad-style natural-language loss loops for text,
code, and prompt refinement. Updated the repo mirror and the condensed `.llm.md`
summary to keep the same evaluation story across invocation surfaces.
**Reason:** `integrate/compiled.md` is now being used as a high-level requirements
surface for skill evolution. The prior contract said "critic loop" but did not
separate metric-first optimization from textual-feedback optimization, which made
the evaluation lane underspecified.
**Evidence:** Tier 3 grounding from `stanfordnlp/dspy` optimizer/refine docs and
`zou-group/textgrad` README + evaluation docs; plus session crystallization that
`agentic-harness` needs a clearer evaluation taxonomy than a single generic judge.
**Supersedes:** Vague "evaluator-optimizer" phrasing as the only evaluation pattern.

---

## 2026-04-28 — Applicability envelope added; evidence + history sidecars created
**Changed:** Added `## Applicability Envelope` section to SKILL.md. Created EVIDENCE.md
and HISTORY.md sidecars following the `skill-wiki` living-skill pattern.
**Reason:** Comprehensive skills inventory + awesome-copilot aggregation session (2026-04-28)
surfaced that skills need explicit "when this works / when it fails" documentation.
Skills are conditional protocols, not universal facts — without the envelope,
agents cannot self-correct when invoking a skill in an out-of-envelope context.
**Evidence:** Tier 4 (session crystallization); `skill-wiki/SKILL.md` Applicability Envelope convention.
**Supersedes:** Nothing — additive change.

---

## Prior — Multi-framework stationmaster reframe
**Changed:** Renamed from "dark factory skill" to "programmatic train station" framing.
Added explicit multi-framework coverage: OpenClaw, Claude Code, OpenCode, GitHub Copilot CLI.
Reframed `agentic-harness` as the shared contract that frameworks plug into.
**Reason:** Real-world usage showed multiple frameworks need the same routing/gating contracts.
The single-framework wrapper model was too narrow.
**Evidence:** Tier 4 (session crystallization — harness used across OpenClaw and Copilot CLI).
**Supersedes:** Single-framework wrapper model.

---

## Prior — Checklist promoted to sub-skill
**Changed:** `checklist` promoted from inline pattern to standalone sub-skill (`checklist/SKILL.md`).
LLM-as-judge structured output pattern extracted to a reusable behavioral contract.
**Reason:** `gap_critic.py` in the storywriter project demonstrated the pattern was independently
reusable outside the harness context.
**Evidence:** Tier 4 (session crystallization — checklist used independently of agentic-harness
in 3+ projects).

---

## Prior — deep-research added as child
**Changed:** Added `deep-research` as a child skill under `agentic-harness`.
LangGraph-based web research with Selenium fallback now seeds the harness TaskSpec.
**Reason:** Research pipeline is a standard pre-phase for any dark-task harness run.
**Evidence:** Tier 4 (session crystallization — research phase consistently needed before harness execution).

---

## Prior — continuity-log added as child
**Changed:** Added `continuity-log` as compact-safe distilled session state for harness runs.
**Reason:** Long harness runs were losing context between turns at compaction events, forcing
full re-derivation of decisions already made.
**Evidence:** Tier 4 (session crystallization — multi-turn harness runs losing state at compaction).
