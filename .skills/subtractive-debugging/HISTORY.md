# Subtractive Debugging — History

Changelog and promotion record for `subtractive-debugging/SKILL.md`.

---

## 2026-05-15 — Promoted from session pattern to live skill
**Changed:** Created the live `subtractive-debugging` skill for regression isolation by anchoring a known-good control, defining a narrow property, comparing entity signatures across baselines, collapsing the suspect interval, and naming the first cascaded mismatch before patching.
**Reason:** A repeated debugging failure mode appeared in the Call To Power 2 MoM Great Library work: broad diffs and speculative hypotheses obscured the actual regression boundary. The subtractive checker pattern produced a bounded, reusable protocol instead.
**Evidence:** Tier 2 grounding from `git bisect` documentation; Tier 5 grounding from Delta Debugging; Tier 4 grounding from the 2026-05-15 Great Library regression isolation session.
**Supersedes:** Ad hoc "check recent changes" guidance inside `debugging` for this regression-isolation niche.
