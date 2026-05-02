# Build Observability — History

Changelog and promotion record for `build-observability/SKILL.md`.

---

## 2026-05-02 — Promoted from integrate concept to live skill
**Changed:** Created the live `build-observability` skill with a normalized
`runs / events / commands` contract, dashboard surface, runtime collector
pattern, trace-enrichment guidance, storage policy, and integration boundaries
for `agentic-harness`, `feature-catalog`, and memory/context-graph systems.
**Reason:** `integrate/compiled.md` identified `build-observability` as an
unresolved concept, and `sundai-hacker-feature-topology.md` showed that the
strongest reusable artifact was the observability schema plus dashboard/collector
pattern rather than a literal port of the OpenClaw-specific runtime.
**Evidence:** Tier 3 grounding from `integrate/compiled.md` and
`integrate/sundai-hacker-feature-topology.md`; Tier 4 grounding from the local
`agentic-harness`, `feature-catalog`, and `agentic_kg_memory` skill contracts.
**Supersedes:** The compiled `build-observability` concept stub only.
