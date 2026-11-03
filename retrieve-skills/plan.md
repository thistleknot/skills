# retrieve-skills — plan

Status legend: [ ] todo · [~] in progress · [x] done

## Phase 0 — Fix the scoring defect (blocks everything else)

Nothing below is trustworthy until routing scores are correct.

**Evidence so far**
- NLI model is correct in isolation. Verified empirically against
  `cross-encoder/nli-deberta-v3-base`:
  - entail pair -> 0.9892
  - contradiction pair -> 0.0
  - neutral pair -> 0.0006
  Label order `[contradiction, entailment, neutral]` and `NLI_ENTAILMENT_IDX=1`
  are both correct. Ruled out.
- Ad-hoc sourdough -> 'spec' hypothesis scored **0.0022** (correct).
- Running server reported **0.98867** for the same query.
- Two unrelated prompts scored 0.98848 / 0.98867 — near-identical. Signature of
  a near-constant premise or a near-constant hypothesis.
- `router_core.route()` line 232 passes `nli_fn(prompt, hyp)` — correct on read.
- Stale-process theory **ruled out**: server started 09:57/10:10, code mtimes
  08:26–08:44. Server is newer than the code.

**Remaining hypotheses (in order)**
1. The real `spec` frontmatter `description` is broad/generic enough to entail
   almost any prompt. My repro used an *invented* description. Must re-test with
   the real one via `discover_skills()` (not `load_skills` — no such symbol).
2. Descriptions are near-duplicates across skills, collapsing the hypothesis
   space so every prompt scores alike.
3. Server env differs from my shell env (`SKILL_ROUTER_NLI`,
   `SKILL_ROUTER_RERANK`, threshold) — compare `/health` against shell env.

- [~] P0.1 Re-run NLI with **real** descriptions from `discover_skills()`
- [ ] P0.2 If descriptions are the cause: report the distribution of entailment
      across all skills for one fixed off-topic prompt. A healthy index should
      be near-zero almost everywhere.
- [ ] P0.3 Fix root cause; add a regression test to `test_gate.py` asserting an
      off-topic prompt accepts **zero** skills.

## Phase 1 — Make retrieve-skills self-documenting

The skill must state its own architecture and operational contract.

- [ ] P1.1 Rewrite `SKILL.md` to document: recall -> rerank -> NLI gate,
      injection modes (`pointer|body`), env vars, ports, fail-open guarantee.
- [ ] P1.2 Document explicitly that **granularity is whole-skill**: one
      `SKILL.md` = one vector = one frontmatter description. Nested skills are
      NOT handled today.
- [ ] P1.3 Document the service + reingest workflow from Phases 2/3.

## Phase 2 — Service autostart

Goal: the RAG service starts with Windows, no manual launch.

- [ ] P2.1 `service/router_service.ps1` — start/stop/status/restart wrapper with
      logging to `logs/`, single-instance guard via pid file.
- [ ] P2.2 `service/install_service.ps1` — registers autostart.
      Prefer **Scheduled Task at logon** over a true Windows service: no admin
      elevation, no NSSM dependency, runs in the user session where the models
      and venv already resolve.
- [ ] P2.3 Health gate: installer verifies `/health` returns 200 before
      declaring success.
- NOTE: registering a service / modifying autostart is a system-settings change.
  Scripts will be written and verified, but the **operator runs the install
  step**; the assistant will not silently register system autostart entries.

## Phase 3 — Reingest tooling

- [ ] P3.1 `reingest.ps1` / `reingest.py` — drop the index and rebuild from the
      skills store. Flags: `--store <dir>` (default `~/.claude/skills`),
      `--dry-run`, `--verify`.
- [ ] P3.2 Print a diff summary: added / removed / description-changed skills,
      using the existing `_desc_hash()` so unchanged skills are visible as such.
- [ ] P3.3 `--verify` asserts index count == discovered count, and fails loudly
      on any skill missing `name`/`description` frontmatter (currently these are
      silently dropped by `discover_skills`).

## Phase 4 — Daisy-chain retrieval for skill-to-skill references

Today: if skill A's body says "use the `spec` skill", nothing resolves it. It is
inert prose. No second retrieval pass exists.

Design (explicit over inferred):
- [ ] P4.1 Frontmatter edge declaration, e.g. `requires: [spec, gstack]`.
      Explicit and debuggable; no extra model inference in the hot path.
- [ ] P4.2 On accept of skill A, transitively resolve `requires` and inject
      those bodies too. Depth cap (default 2) and cycle detection — a cycle must
      fail open, never loop.
- [ ] P4.3 `max_accept` must account for chained skills so a single hit cannot
      blow the injection budget. Chained skills bypass the NLI gate (they were
      pulled by explicit declaration, not by similarity) but still respect
      session dedup.
- [ ] P4.4 Tests: A->B chain, A->B->C depth cap, A->B->A cycle, budget overflow.

## Phase 5 — Section-level anchoring (deferred, design only)

Motivation: a 900-line SKILL.md is one vector described by one sentence. That
dilution is a plausible contributor to the Phase 0 defect.

- [ ] P5.1 Split on `##` headings -> records keyed `skillname#section-slug`
      carrying `parent`, `title`, inherited frontmatter.
- [ ] P5.2 Open question for operator: do sections retrieve *instead of* their
      parent, or *in addition to* it? Determines whether `pointer` injection
      targets a file or a file+anchor. Hard to reverse — decide before building.

## Ordering rationale

Phase 0 first: anchoring and daisy-chaining both inherit any scoring fault and
would make it far harder to see. Phases 2/3 are independent of the defect and
can proceed in parallel if Phase 0 stalls.
