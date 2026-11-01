# Workflow contract

## CURRENT

Accepted 2026-10-31: Spec Kit specifications inform Sphinx-Needs requirements;
transport is implementation-agnostic; downstream authoring stays in RST;
generation must cover structure and executable behavior; provenance spans Git
history and the current code revision.

This document specifies the workflow, not an implemented compiler.
The target application is a Python desktop 4X game; a small turn is the first
factory experiment, not the complete game specification.

## Definitions

- **Specification**: upstream intent, rules, scenarios, and design decisions authored through Spec Kit.
- **Requirement**: an atomic, identified, testable obligation transported into Sphinx-Needs.
- **Formal input**: typed definitions, relationships, guards, effects, and scenarios whose supported semantics are explicit.
- **Generation snapshot**: immutable validated inputs plus compiler, template, configuration, and dependency identities.
- **Contract**: a caller precondition, postcondition, invariant, or execution-point check with defined evaluation semantics.
- **Design view**: intended structure or behavior rendered from the formal inputs.
- **Implementation view**: source-extracted or scenario-observed relationships at a recorded code revision.

## Staged pipeline

| Stage | Mechanism and output | Obligation |
|---|---|---|
| SPECIFY | Spec Kit produces specifications, clarification, plans, and task artifacts | R1 |
| TRANSPORT | Discover configured source artifacts; map obligations and source locations into RST needs | R2 |
| VALIDATE | Check formal completeness, references, contracts, and supported semantics; freeze generation snapshot | R3, R4 |
| DESIGN | Render UML classes, state/activity flows, and component architecture from identified definitions | R5 |
| MODEL | Transform structural definitions and diagram-source semantics into Ecore; retain behavior inputs separately | R6 |
| GENERATE | Run pyecoregen for model classes and a declared generator for behavior and contract checks | R6, R7 |
| VERIFY | Execute acceptance scenarios and independent expectations against generated output | R8 |
| OBSERVE | Extract implementation structure and scenario traces; reconcile intended and implemented views | R9 |
| REPORT | Publish current traceability, freshness, decisions, and historical rollups | R10, R11 |

## Requirements

- **R1**: When starting a feature, the workflow MUST discover the installed Spec Kit lifecycle and configured artifact locations before transporting specifications.
- **R2**: When transporting specifications, the workflow MUST preserve each obligation's source identity, location, content hash, and semantic disposition in the transport record.
- **R3**: If an input has ambiguous effects, missing types, unresolved references, contradictory contracts, duplicate identities, or unsupported constructs, generation MUST stop with source-local diagnostics.
- **R4**: When starting deterministic generation, the workflow MUST bind the run to a validated generation snapshot.
- **R5**: When rendering design diagrams, the workflow MUST derive their identified nodes and relationships from the same formal definitions used for generation.
- **R6**: When generating executable behavior, the workflow MUST identify the behavior translator and its supported semantics separately from the Ecore-to-class generator.
- **R7**: When regenerating output, the workflow MUST preserve traceability from each generated symbol and enforced contract to its governing requirement revision.
- **R8**: When claiming executable implementation, the workflow MUST supply passing independent acceptance evidence for the exact requirement and code revisions.
- **R9**: When presenting implementation relationships, the workflow MUST record extraction provenance, source scope, and the applicable runtime scenario.
- **R10**: If a report's inputs differ from the current source snapshot, the workflow MUST mark that report stale.
- **R11**: When reporting feature history, the workflow MUST distinguish specification lifecycle events from implementation-evidence events.
- **R12**: If an upstream gate fails, the workflow MUST resolve or disposition that gate before running a dependent experiment.

## Authoring and transport boundary

Use the installed `speckit` lifecycle for constitution, specification,
clarification, planning, tasks, and analysis; discover version-specific command
names rather than copying bootstrap commands blindly into an existing project.
Use `spec` for atomic requirements, EARS guards, Given/When/Then scenarios, and
Require/Guarantee/Maintain/Assert contracts.

Discover actual feature directories through project configuration or Spec Kit's
discovery mechanism; do not assume `.specs`, `.spec/`, or `.specify/` contains the
feature specifications, or couple the local `.spec/` lifecycle to Spec Kit.

Transport may be a converter, import process, manual review, or LLM-assisted
authoring; the skill does not select it in advance.
Record the method/version, source hashes and locations, output hashes, mapping
of source obligations to needs, and unresolved or excluded items with reasons.
Do not claim transport determinism unless repeated transport has been tested.
Ordinary prose remains useful for intent but cannot silently acquire executable
semantics during compilation.

Keep downstream authored requirements, model definitions, diagram definitions,
and behavior rules in RST; JSON exports, PlantUML source, Ecore, and Python are
derived build artifacts, not competing authoring sources.
Preserve established need types and link names; add only the missing concepts
for specifications, requirements, features, model elements, decisions, and tests.
Export reproducible needs data and textual diagram definitions for automation.

## Generation seam

Before implementing a translator, specify its accepted grammar, type system,
reference resolution, contract semantics, error behavior, and mapping to output.
Start with typed state, explicit transitions, bounded guards, and effects needed
by the pilot; unsupported syntax fails rather than being guessed or executed as
arbitrary Python.

Structural UML expresses classes, attributes, references, multiplicity, and
ownership; behavioral UML expresses transitions, ordering, guards, and effects;
component views express responsibility and allowed dependencies.
Views are projections with shared IDs, not a sequence of images to reverse parse.
Diagram-only annotations cannot change executable semantics without a declared
translation rule and acceptance test.

The MODEL stage emits Ecore structural definitions and explicit behavior inputs;
the GENERATE stage invokes pyecoregen on Ecore and the tested behavior generator
on the behavior inputs, using the generator's supported extension mechanism.
Do not treat EOperation declarations, generated stubs, or stored constraint text
as implemented behavior or enforced contracts.
Do not edit generated files as a fix; change their governing inputs or generator.

## Preconditions and failure modes

- Discover existing specs, documentation, generators, graphs, decisions, and dependency locks before adding artifacts.
- Pin interpreter, tools, templates, configuration, and dependency versions for reproducibility experiments.
- Fail clearly on missing tool dependencies, invalid models, stale exports, generation failures, or acceptance failures.
- Preserve failed-run diagnostics and the last successful report with its original snapshot identity.
- Use source hashes for dirty worktrees and commit IDs for committed snapshots; never label dirty output as verified HEAD.
- Repair upstream specifications when code and intent disagree; feedback starts another explicit specification revision.

## CLOSED and OPEN

| Disposition | Decision or question | Basis or discriminating evidence |
|---|---|---|
| CLOSED | Spec Kit precedes Sphinx-Needs; transport mechanism stays open | Explicit user selection, 2026-10-31 |
| CLOSED | RST is the downstream authoring substrate | Explicit user selection of formal RST, 2026-10-31 |
| CLOSED | Structure-only generation is insufficient for the objective | User requires both contracts and working behavior, 2026-10-31 |
| CLOSED | Reuse existing diagram skill | Existing `sphinx` skill owns source-backed architecture and tracing |
| CLOSED | pyecoregen is not the requirements-to-Ecore translator | Its documented input is Ecore; see source below |
| OPEN | Formal inputs encode enough behavior for an executable turn | Three independently expected scenarios in the validation reference |
| OPEN | Selected transformations are reproducible | Two clean generations from identical pinned inputs |
| OPEN | History rollups survive revisions, retirement, restoration, and merges | Disposable history experiment in the validation reference |

## Sources

- [Spec Kit](https://github.com/github/spec-kit): upstream specification workflow and configuration.
- [Sphinx-Needs builders](https://sphinx-needs.readthedocs.io/en/latest/builders.html): needs exports.
- [needuml](https://sphinx-needs.readthedocs.io/en/latest/directives/needuml.html): requirement-aware PlantUML and textual export.
- [pyecoregen](https://github.com/pyecore/pyecoregen): Ecore-to-Python classes and extension options.
- [PyEcore executable models](https://pyecore.readthedocs.io/en/latest/user/advanced.html): explicit behavior implementations.

These references establish tool boundaries, not evidence that the proposed
end-to-end factory has been implemented or tested.
