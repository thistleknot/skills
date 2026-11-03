## 2026-10-26 — Merge SKILL2 (agentic_memory_lifecycle) and its retrieval run
**Changed:** Added R14 (admission by recurrence or control-vs-treatment, flag `--admit`, off), a `global` gate stratum, two Dead Ends (reinforce-on-recall decay; model confidence as admission signal), two Open Questions, ExpeL under R12, five EVIDENCE rows.
**Rejected from SKILL2:** Ebbinghaus decay as a mechanism (built in conversation_store, never called, and the harness spec closes recall-as-utility); "flat storage without routing" as a dead end (contradicts R2: full context and BM25 match or beat structured stores); SOTA-map cells "MIRIX (hierarchical routing)" and "Harness 2 (active intent retrieval)" (in the retrieved text hierarchical retrieval is AtomMem's, active retrieval is MIRIX's, Harness 2 makes no retrieval claim).
**Reason:** SKILL2 shares this skill's scope; one skill, not two.
**Status:** still draft; no live run.

## 2026-10-24 — Integrate with the harness-evolution skills and the conflation test
**Changed:**
- Repointed the dangling "harness-evolution digest" reference to `recursive-harness-self-improvement` and `auto-research`.
- Added an open question on read scoping by project or session.
**Reason:** The cross-reference named no existing skill. The opencode conflation case (`~/.claude/.tmp/plan.md`) is a live test of a mechanism this evidence set does not cover.
**Evidence:** validator `PASS 201 skill(s) scanned`; router reindex `{"total":201,"embedded":1}`; `EVIDENCE.md` has no row on scoping. Receipts in `~/.claude/.tmp/critique.md` (RC-12, RC-20).
**Status:** still draft. The conflation battery plus its benefit probe would be this skill's first gate-protocol run on a real harness, the condition `status: active` waits on.

## 2026-10-24 — Create agent-long-term-memory as a staged draft
**Changed:** Added `agent-long-term-memory` (status: draft): memory map, staged pipeline with flags, rules R1–R13, bounded gate protocol, CLOSED dead ends.
**Reason:** Crystallization of retrieved graph evidence on agentic harness long-term memory, plus a web sweep for counter-evidence the retrieval commentary left out (simple baselines, benchmark validity, poisoning, embedding limits).
**Evidence:** Tier 1–3 sources in `EVIDENCE.md`; no live run. Promote to `active` only after one gate-protocol run on a real harness.
**Supersedes:** none. Nearest neighbor `agentic_kg_memory` owns storage; this skill owns substrate choice and the acceptance gate.
