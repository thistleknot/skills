---
name: sw-design
description: Chains software design artifacts from decisions to generated classes. A feeder gate (policy/triage.md) classifies the change; typed decision records (MDD/ADR/CDR/EDR/IDR, each with an AI-Context block, Proposed-Accepted-Deprecated-Superseded lifecycle) precede speckit specs; specs feed Sphinx-Needs requirements, which inform UML models; AIUP use cases and the entity model augment those findings; the entity model maps to an Ecore model that pyecoregen turns into Python classes; brownfield recovery runs the code-graph ladder; a project decision_gate enforces allowlisted verification commands. Covers the aha loop (decisions from unknown unknowns expressed as requirement prompts that re-run downstream artifacts, recorded in lessons_learned.md and dispositions.md) and stacked-MR discipline (self-contained MRs, aggregate state tracking, schema-translation test wrappers, fixture spoofing, test adjustment in later stacked MRs). Use when the user asks to design software from specs or decisions, record or check CDR/ADR decisions, triage a change, derive requirements and models, produce an entity model or Ecore file, or generate classes from a model; split a suite of changes into self-contained stacked MRs; write schema-translation wrappers for unit tests; or mentions sw-design, the speckit to Sphinx chain, AIUP, pyecoregen, Ecore, DDSE, decision records, the feeder gate, the aha loop, lessons_learned.md, dispositions.md, or stacked MRs.
license: MIT
metadata:
  category: methodology
  complexity: advanced
---

# sw-design: specification to requirements to models to generated classes

Each stage narrows the one before it. Use the earlier stage's output when it
exists. Later stages augment it and never restart from scratch.

## Flow

Decision records (typed TDRs: MDD/ADR/CDR/EDR/IDR, each with an AI-Context block) → speckit spec → Sphinx-Needs requirements → needuml UML (from the requirement and component needs) → AIUP business use cases, system use cases and entity model (the UML classes inform the entity model) → Ecore (from the entity model) → pyecoregen classes (the system use cases are the checklist the generated classes must cover).

Full flow with per-feature source trace (feeder gate, brownfield code-graph ladder,
stages 1-6, cross-cutting layers, citation law): `references/integrated-flow.md`.

## Spec substrate seam (repo files vs SpecsDB ledger)

Two substrates, two functions — never duplicate a body across both:

| Substrate | Holds | Canonical for |
|---|---|---|
| Repo files (speckit `spec.md`/`PRODUCT.md`/`plan.md`/`tasks.md`, `design.md`, `TECH.md`, use cases, entity model, `.ecore`, generated package) | the chain's working artifacts, versioned with the code | stage artifacts and their cross-citations; `.spec/state.json` is the only phase file `spec_gate` reads |
| SpecsDB (`~/.mcp/specs/specs.db` via the specs MCP) | cross-session ledger: requirement/task/decision rows, traceability graph, canon/failures | typed decisions (MDD/ADR/CDR/EDR/IDR) and their lifecycle (Proposed/Accepted/Superseded) |

Rules: repo artifacts cite decision **ids**; decision bodies live in exactly one
place — SpecsDB when the ledger is available (its rows are canonical, and the
AI-Context convention is parsed by `verify.ps1`), in-repo `docs/decisions/`
otherwise. Stage gates check citations, never restate bodies. A requirement or
task the ledger tracks MUST be mirrored to SpecsDB when the harness registers
it; a repo-only artifact is authoritative for its own stage.

## Feeder gate

Classify the change through `policy/triage.md` before entering the chain:

- mechanical edit -> chain skipped (constitution exception, one-line justification)
- small bug with obvious fix -> ticket, fix, test
- feature under ~3 points -> speckit flow only (spec/plan/tasks)
- feature ~3 points or above, or any change touching the data model -> full 6-stage chain
- greenfield module -> full chain + typed decision records + spec-as-source marking

Every entry appends a line to the repo's INTAKE.md: `| date | source | classification | lanes |`.
Maintenance strategy per artifact: speckit spec = spec-first (retire after merge); AIUP
UC-*.md = spec-anchored (living, status line updated); pyecoregen output = spec-as-source
(GENERATED, DO NOT EDIT).

## Stage 0: Decision records (DDSE)

Before any spec, record the durable choices the change depends on. Decisions are
the system of record that specs and code derive from; a spec contradicting an
Accepted decision is a defect, not a refinement. (Constitution Article XVI.)

Each decision is a typed record, in-repo, cross-linked to the work and code it
governs:

- `MDD` — Mission: what the system is for. Changes rarely; operator-level.
- `ADR` — Architecture: structure, components, technology.
- `CDR` — Contract: an API/interface agreement. Carries a required **contract**
  section (source of truth for the interface) and requires a contract test
  (Article V). Mock/type generation is a later increment, not a gate.
- `EDR` — Entity/Data: schema, data model, persistence.
- `IDR` — Implementation: local, changeable per task.

Every decision carries a machine-parsable AI-Context block:

```
AI-Context:
  Constraints: <limits the implementer must not cross>
  Patterns: <incumbent patterns to reuse>
  Anti-patterns: <rejected approaches this decision forbids>
  Verification commands: <commands proving conformance>
```

Lifecycle: `Proposed → Accepted → Deprecated → Superseded-by:<id>`. Code and specs
cite only `Accepted` decisions; a citation to a Deprecated/Superseded one is a
finding. A `Deprecated`/`Superseded` decision names its replacement; the old record
is kept, never deleted (Decision Memory).

**Gate 0 to 1:** every decision the change depends on is recorded and `Accepted`;
each carries an AI-Context block; no `Proposed` decision is cited downstream.

## Stages

| # | Stage | Input | Output | Owner |
|---|---|---|---|---|
| 1 | Specification | user intent | `spec.md`, `PRODUCT.md` (user stories + `## Product Invariants` block of agent-verifiable EARS assertions), `plan.md`, `tasks.md`; decision ids assigned here | speckit |
| 2 | Requirements | `spec.md` | Sphinx-Needs requirement needs (`req`) in `docs/sphinx/requirements.rst`, each with a stable id, its decision id, and a machine-parsable AI-Context block (Constraints / Patterns / Anti-patterns / Verification commands) | sphinx-needs |
| 3 | UML | requirement and component needs | needuml diagrams (class, sequence, component) generated from the needs and rendered with PlantUML; the two deferred schema decisions recorded as typed decision records (CDR for interface contracts, ADR otherwise) with AI-Context; `design.md` (Overview, Architecture, Components and Interfaces, Data Models, Error Handling, Testing Strategy, Migration Strategy) and `TECH.md` (Context with code line refs, Proposed changes, Testing and validation mapping invariants to steps, Parallelization); gate advances `.spec/state.json` | sphinx-needs (needuml) |
| 4 | Business use cases, system use cases, entity model | requirements, needuml class diagrams, `design.md` | `docs/use_cases.puml`, `docs/use_cases/<module>/UC-*.md` (business and system use cases); entity model lives as the Data Models subsection of `design.md`, promoted to standalone `docs/entity_model.md` only above 10 entities (config, not law); review gate before stage 5 | aiup |
| 5 | Ecore model | entity model | `<name>.ecore` (XMI); every mapping choice (type, bounds, id, reference, constraint) cites its governing decision id via `EAnnotation` | this skill, mapping below |
| 6 | Classes | `.ecore`, system use cases, `PRODUCT.md` | Python package generated by pyecoregen; post-generation annotation pass adds header `# GENERATED FROM <name>.ecore - DO NOT EDIT - decisions: <ids>` (pyecoregen itself unmodified); each system use case maps to a generated operation or documented external step AND each invariant traces to a verification step; post-generation review | pyecoregen |

## Rules

- Every artifact cites the upstream ids it realises. An id that appears in no
  upstream artifact is a finding to report, not a silent addition.
- Generated code is spec-as-source: humans edit the entity model and regenerate; the
  generated package is never hand-edited.
- Upstream exists: consume it. AIUP adds what the requirements and UML did not
  capture, and marks it as its own finding.
- Upstream missing: say which stage is missing, then recover the gap from the
  code with aiup's reverse-engineering pass. Mark every recovered artifact Draft.
  Run the code-graph ladder first (`reverse-engineer/references/code-graph-tools.md`)
  so each recovered artifact carries static + dynamic-or-historical evidence.
- A change in an upstream stage re-runs every downstream stage. Walk back to the
  earliest affected stage first.
- Business use cases state the business goal and its actors. System use cases
  state the system's actions with its actors. Both come out of AIUP.
- AIUP inherits the needuml class diagrams as entity candidates. A UML class with
  no entity, or an entity with no UML class, is a finding to record.
- pyecoregen does not read use cases. System use cases are the checklist: each
  one maps to an operation on a generated class, or to a documented external step.

## Decision provenance (the aha loop)

Decisions are usually not declared up front. They surface when an unknown
unknown appears during work — a surprise, a contradiction, a case the model
did not cover. The decision is the response to that aha.

The proper form of a post-aha decision is a **prompt that updates upstream
requirements**, not a local patch. The decision is expressed as a requirement
change, and the change re-runs every downstream stage: use cases, system use
cases, and the code. A decision that only patches code leaves the requirement
lying — that is a defect by the Rules above.

Where aha-derived decisions live (when the project does not carry a full TDR
set):

- `lessons_learned.md` — the running record: what surfaced, what was decided,
  what requirement or rule it implies.
- `dispositions.md` — the writeup of a settled decision: context, options
  weighed, chosen, rationale, and the downstream artifacts it re-runs.

Both are upstream artifacts in the citation law: downstream artifacts cite
them, and a change in either re-runs the affected stages.

## MR discipline (stacked MRs and schema-translation wrappers)

After a suite of changes, break the work into self-contained MRs, each
reviewable and mergeable on its own, stacked when the next one depends on the
previous.

- Track the aggregate state: the current branch is the aggregate. If the
  individual MRs are not on the current branch, aggregate them through a proxy
  branch (aggregate branch) that carries the core changes of the latest
  feature set.
- Build each MR's unit tests against the schema state that MR expects. When a
  stacked MR's expected schema differs from the aggregate state, build a
  **wrapper** that translates between the earlier schema and the aggregate
  state. The wrapper is the test-side adapter; the test stays honest to the
  MR's own contract.
- If a wrapper is made redundant (the feature is not decoupled yet), do not
  delete it silently — use fixtures to spoof the real activity instead, so
  the test still exercises the path without depending on live state.
- Later stacked MRs remove or adjust prior stacked MRs' unit tests when the
  schema changes. That adjustment is part of the later MR's diff, not a
  follow-up.

## Stage gates

- 1 to 2: every spec requirement has a need id and a decision id; PRODUCT.md carries
  the invariants block; no open clarification markers remain.
- 2 to 3: every diagram element traces to a requirement id; every req need carries its
  AI-Context block.
- 3 to 4: business and system use cases use the actor and element names of the
  needuml diagrams; every UML class is an entity or is justified out; CDR/ADR records
  exist for the schema decisions; design.md and TECH.md complete; state.json phase advanced.
- 4 to 5: every entity appears in the Ecore model; every foreign key has a reference;
  the use-case validator reports 0 errors; entity-coverage review passed.
- 5 to 6: the `.ecore` file loads; pyecoregen generates without error; the generated
  package imports; every system use case maps to a generated operation or a documented
  external step; every entity's governing decisions are cited in EAnnotations.
- 6 after: generated headers present; every PRODUCT.md invariant traces to a
  verification step; post-generation review passed.

## Entity model to Ecore mapping

Check each type against the installed pyecore/pyecoregen version before relying on it.

| Entity model | Ecore |
|---|---|
| `Long` | `ELong` |
| `Integer` | `EInt` |
| `Decimal` | `EBigDecimal` |
| `String` | `EString` |
| `Boolean` | `EBoolean` |
| `Date`, `DateTime` | `EDate` |
| `Binary content:` description | `EByteArray` |
| `Values: a, b` | `EEnum` with those literals |
| `Primary Key` | `EAttribute` with `iD = True` |
| `Foreign Key (X.col)` | `EReference` to class X |
| Cardinality `\|\|--o{` | many-valued reference, lower bound 0 |
| Cardinality `\|\|--o\|` | single-valued reference, lower bound 0 |
| `Not Null` | lower bound 1 |
| `Optional` | lower bound 0 |
| `Min`, `Max`, `Unique`, `Format` | Ecore has no slot for these; record them as `EAnnotation` |

Decisions to record in the UML stage, not to guess here:
- Composite primary keys: several id attributes, or one containment key.
- Containment versus plain reference for owner-to-child foreign keys.

## Known limits

- Use cases describe behaviour. Ecore holds structure only, so use-case steps
  never become generated code. They can name operations; the operation bodies
  stay hand-written.
- pyecoregen generates classes from the `.ecore` file. It does not generate
  behaviour, validation logic or persistence.
- Reverse-engineered specifications are Draft until a human approves them.

## Commands (verified against installed versions, 2026-11-07 sample run)

- Validate use cases: `python <validate_use_case.py> --strict docs/use_cases/*/UC-*.md`
  (locate the script under the aiup use-case-spec skill; never resolve it from the project root).
- Build Sphinx pages: `python -m sphinx -b html docs/sphinx docs/_build`. Drop `-W` until
  sphinx-needs' deprecation warnings are gone — it fails the build on warnings that are not ours.
- needuml renders only with `sphinxcontrib-plantuml` installed (present since 2026-11-07);
  without it needuml parses and silently renders nothing. Fallback that always works:
  hand-write the .puml and render with `java -jar <plantuml.jar> file.puml`. Java and the
  jar are required either way.
- Load an Ecore model: `ResourceSet().get_resource(URI(path)).load()` — the documented
  `Resource.load()` form is broken in pyecore 0.15.2.
- Generate classes: `pyecoregen -e -o <outdir> <name>.ecore` (verified on 0.5.1; the
  documented command form fails). Re-check `pyecoregen --help` after any version bump.
- EAnnotations do NOT survive codegen: decision citations live in the `.ecore`; the carrier
  into generated code is the GENERATED header pass (script pending). Behavior — invariant
  enforcement — is never generated; it lands in a hand-written mixin.
