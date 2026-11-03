---
name: sphinx-dfp-sdd
description: >-
  Guide Spec Kit specifications through transported Sphinx-Needs RST requirements,
  UML and functional/architecture models, Ecore, pyecoregen, and explicit behavior
  generation with revision-bound verification and Git history rollups. Use for
  specification-driven code factories, requirement-to-code provenance, feature
  retirement/restoration, and deterministic regeneration experiments. Compose the
  existing spec, speckit, and sphinx skills; do not use for ordinary standalone
  Sphinx documentation or claim prose-to-working-code generation without evidence.
---

# Sphinx DFP SDD

## CURRENT contract

Start with **Spec Kit specifications informing Sphinx requirements**.
Treat **deterministic automated code generation** as a falsifiable hypothesis.
The default application is a Python desktop 4X game; do not mistake that target
for an already specified game or expand a compiler pilot into full gameplay.

This skill defines the workflow and its gates; it ships no compiler or tested
end-to-end factory. Never report a capability as operational because this skill
describes it.

## Owners and references

| Work | Owner or reference |
|---|---|
| Spec Kit lifecycle, bootstrap, artifact discovery | Existing [speckit](../speckit/SKILL.md) |
| EARS, scenarios, structural and behavioral contracts | Existing [spec](../spec/SKILL.md) |
| Source-backed Sphinx diagrams, tracing tools, and ELK-informed Graphviz layout | Existing [sphinx](../sphinx/SKILL.md) |
| Transport, formal model, generation contracts | [Workflow contract](references/workflow.md) |
| Identities, evidence, decisions, historical aggregates | [Provenance contract](references/provenance.md) |
| Hypotheses, bounded experiments, acceptance gates | [Validation procedure](references/validation.md) |

Read the relevant reference before working at its boundary; verify sibling
skills exist and use their installed commands rather than copying their bodies.
If an owner is missing, report the specific missing dependency instead of
silently inventing an equivalent workflow.

## Execution

1. Inspect project instructions, memory where defined, existing specs, needs,
   generators, decisions, and graphs; extend incumbents before adding artifacts.
2. State the spec layer and the dependency chain; identify the earliest OPEN
   assumption and its pass/fail consequences before doing dependent work.
3. Use Spec Kit upstream; discover its configured specification outputs and
   resolve clarification markers through its lifecycle before transport.
4. Transport into Sphinx-Needs RST without prescribing the transport technology;
   preserve source mappings and disposition every unmapped obligation.
5. Validate formal completeness and freeze the generation snapshot; keep the
   determinism claim scoped to the transformations actually tested.
6. Derive design views and Ecore from shared identified definitions; generate
   behavior and contract checks through an explicit tested translation seam.
7. Run acceptance evidence tied to exact revisions, then extract implementation
   views and reconcile structural/behavioral differences with the design.
8. Publish current and historical rollups with freshness, exact evidence, and
   unresolved gaps; update specifications before regenerating a correction.

Only a passed upstream gate permits dependent execution; a failed gate may be
dispositioned as failure without being treated as passed.
Keep downstream authored content in RST; derived JSON, diagram source, Ecore,
Python, and reports must identify their generating snapshot.

## Delivery rules

- Preserve requirement and feature identity through revisions, renames, retirement, and restoration.
- Never infer implementation from a commit message, generated stub, diagram edge, or self-reported completion flag.
- Keep intended diagrams distinct from extracted structure and scenario-specific observed calls.
- For layered architecture and functional diagrams, follow the [Sphinx skill's ELK-informed layout rules](../sphinx/SKILL.md#apply-elk-informed-layered-layout-conventions); the selected rendering engine remains explicit and diagram layout does not alter model semantics.
- Use Graphify as an evidence-qualified index; inferred edges cannot certify implementation or determine generation semantics.
- Bound each experiment below 15 minutes, keep matched controls, and disposition after no more than three tests.
- Update the current disposition in place; move superseded durable material to dated support with a pointer when it exists.
- Record interpretation decisions with basis and date in the project's existing interpretations log.
- Finish with requirements coverage, actual validation results, OPEN assumptions, and a sprawl review.

## Completion boundary

For skill delivery, validate frontmatter, local references, routing, contract
coverage, and realistic scenario walkthroughs; label walkthroughs as reviews.
For factory delivery, require successfully run transformation, behavior,
regeneration, diagram, and history gates from the validation procedure.
Do not substitute skill validation for factory validation.
