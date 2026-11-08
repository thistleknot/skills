# The integrated SDD flow — full trace

Canonical article for the chain sw-design actually runs today (2026-11-07, SpecsDB
REQ #73 / task #94 / W11). Receipts: `~/.harness/docs/playbooks/sdd-integration-{plan,receipts,worklog}-2026-11-07.md`.
Every feature names the framework it was pulled from.

**Source tags:** S sw-design original · D1 DDSE (ddse.md) · D2 Kiro-vs-AIUP notes ·
B1 SDD book (study library) · A1 Anioko guide · P1 pi-sdd-kit · G2 Thoughtworks
review · W1 wiki SDD.md (= spec-driven-development skill) · W2 Warp three-skills ·
W3 harness-resources stack (Tessl/xcapit/marcelsud/agentic-spec/specky) ·
W4 full-project patterns · L code-graph ladder.

## The shape

```
                        ┌─ spec exists? ──────────────────────────┐
 request → FEEDER GATE ─┤                                         │
                        └─ no (vibe-coded) → LADDER (walk back) ──┤→ Draft artifacts
                                                                  ↓
              Stage 1 → 2 → 3 → 4 → 5 → 6   (each gate advances .spec/state.json)
                                                                  ↑
        layers run across everything: decision · review · intake/conflict · citation law
```

## Entry — Feeder gate (`policy/triage.md`)

| Feature | Source |
|---|---|
| Five size lanes (mechanical / bug / small / data-touching / greenfield) | G2 size critique + A1 maturity levels; W3 xcapit fit/poor-fit corroboration |
| Maintenance strategy per artifact (spec-first / spec-anchored / spec-as-source) | G2 taxonomy, committed per artifact |
| INTAKE.md append-only entry at every gate pass | W4 intake-log pattern |
| Raw-idea lane | P1 sdd-idea, folded into classification |
| Rule file, not Article I amendment | amendment needs ≥2 failure cases (decision #39) |
| Graphify communities as size evidence | L, first ladder touchpoint |

## Branch — Brownfield recovery via the code-graph ladder (L)

When upstream stages are missing, the ladder runs BEFORE any artifact is written
(cheap→expensive):

| Rung | Tool | Evidence | Feeds |
|---|---|---|---|
| 0 | code2prompt-style index | constants + class/function headers + docstrings, one file, paired with the pyreverse diagram | orientation |
| 1 | graphify (CLI + MCP) | AST/call graph, communities = candidate modules, god nodes = candidate actors, query/path/impact | module map, actors; PR blast-radius later |
| 2 | pyreverse | Python UML class diagrams | Draft entity model |
| 3 | code2flow | entry-point call-flow DOT | Draft use-case step candidates |
| 4 | pycallgraph2 | runtime traces from real tests | live-vs-dead proof |
| 5 | gitnexus (deferred install) | commit-to-why history graph | historical confirmation |
| 6 | understand-anything (deferred) | LLM domain views, tours | stakeholder narrative |

Citation law: a recovered use case or entity is Draft until it cites one static line
(rungs 1–3) plus one dynamic-or-historical line (rungs 4–5). Source repos use this
ladder; shipped binaries go through reverse-engineer-anything under the same law.

## Stage 1 — Specification (speckit incumbent)

| Feature | Source |
|---|---|
| spec.md / plan.md / tasks.md | S |
| EARS acceptance criteria (validator = absorbed specky) | W1 + W3 |
| PRODUCT.md, separate file in specs/<issue>/ | W2 (+ Q3 decision #37) |
| `## Product Invariants` — agent-verifiable assertions | W2 |
| Decision ids minted at intent origin | D1 |

## Stage 2 — Requirements (sphinx-needs incumbent)

| Feature | Source |
|---|---|
| `req` needs with stable ids | S |
| Decision id per need | D1 required traceability |
| AI-Context block: Constraints / Patterns / Anti-patterns / Verification commands | D1 machine-parsable AI Context |

## Stage 3 — Design (needuml + PlantUML incumbent)

| Feature | Source |
|---|---|
| Class/sequence/component diagrams from needs | S |
| The two schema decisions (composite PK, containment-vs-reference) become typed records — CDR for interface contracts, ADR otherwise | D1 × S: S mandated recording, DDSE supplied the format |
| design.md seven sections (Overview / Architecture / Components and Interfaces / Data Models / Error Handling / Testing / Migration) | W1 template + G2's Kiro description; D2 scope rule |
| TECH.md (code-line refs, proposed changes, invariant→step validation mapping, parallelization) | W2 |
| `.spec/state.json` phase advance | P1 sdd-status concept onto the incumbent gate file (decision #38) |
| Brownfield recovery stays Draft | S rule, executed via the L ladder |

## Stage 4 — Use cases + entity model (AIUP incumbent)

| Feature | Source |
|---|---|
| use_cases.puml, UC-*.md, validator 0-errors | S + incumbents; UC-XXX ids match W4 numbered-stable-id pattern |
| Entity model nested in design.md Data Models; standalone only above 10 entities | D2 boundary; threshold is config, not law |
| Review gate before Ecore | P1 sdd-review |

## Stage 5 — Ecore

| Feature | Source |
|---|---|
| Type/bounds/enum mapping table | S, untouched |
| Every mapping choice cites its governing decision id via EAnnotation (lives in the .ecore; the code-side carrier is the stage-6 GENERATED header - see codegen gap) | D1 annotations riding S's EAnnotation escape hatch |

## Stage 6 — Classes (pyecoregen incumbent)

| Feature | Source |
|---|---|
| Generation, structure-only | S + G2 MDD caution (why it stops at structure) |
| `GENERATED FROM <name>.ecore - DO NOT EDIT - decisions: <ids>` header | W3 Tessl marker + D1 backlinks |
| Use case → operation checklist; invariant → verification-step trace | S rule + W2 |
| Post-generation review | P1 + W2 |
| Codegen gap (V2-W0 spike CONFIRMED: pyecoregen 0.5.1 DROPS EAnnotations, rc=0 files generated zero decision trace; therefore) decision backlinks into code ride the GENERATED header pass — decision backlinks into code ride the GENERATED header pass; invariant enforcement is never generated, it lands in a hand-written mixin | L + G2 MDD caution, empirically confirmed |

## Cross-cutting layers

| Layer | Features → sources |
|---|---|
| Decision | ADR/CDR/EDR/IDR/MDD prefixes + AI-Context + Status/Owner (D1, convention-first per decision #36, v2 lifecycle per #41). Enforcement lives at the PROJECT's `decision_gate.py` (V2-W2), NOT the harness self-check — V1's runner-in-verify.ps1 was a category error. Harness `check_decision_convention.py` stays a static FORMAT checker (allowlist + lifecycle + label-only-CDR), never executes commands (V2-W1 security). |
| Review/verification | `validate-changes-match-specs` skill (W2); computer-use lane via incumbent headless-browser-verification/agent-browser; graphify PR blast-radius + pycallgraph runtime evidence (L) — a change touching a community no decision cites is a finding |
| Intake/conflict | INTAKE.md + rule-conflict protocol (OPEN / RESOLVED-BY-SPEC-CHANGE / RESOLVED-BY-RULE-CHANGE / WITHDRAWN); contradiction in active acceptance criteria holds implement (W4) |
| Citation law (unifying) | One rule everywhere: no artifact without upstream evidence — decision ids on needs (D1), GENERATED-header decision backlinks on code (D1+W3, carrier fixed to header after V2-W0), static+dynamic citations on recovered artifacts (L), and a project gate that FAILS on violation (DDSD §1) |

## Deferred with reason

gitnexus / understand-anything installs + graphviz (footprint decision);
pyecoregen header-annotation script; CI enforcement wiring (until the commit-time
check lands); SpecsDB type-column migration (only if the convention falsifies).

## Coverage

Every source lands in at least one shipped feature: S D1 D2 B1 A1 P1 G2 W1 W2 W3 W4 L —
and no shipped feature is source-less.
