---
name: kg_ontology
description: Ontology protocol for collapsing extracted graph spans to canonical lemma identities, separating evidence from ontology, and keeping hypernym/debug structure out of the default user-facing graph.
---
# KG Ontology Protocol

## Core Thesis
The visible graph is not the raw extractor output.

- **Surface spans** are evidence, not ontology ids.
- **Entities** collapse to one canonical noun/proper-noun lemma.
- **Predicates** collapse to one canonical predicate lemma.
- **Named entities** keep their full normalized span.
- **Hypernyms and ontology scaffolding** are separate layers, hidden by default.

Default contract:

`surface text -> canonical entity/predicate lemma -> visible graph`

Not:

`surface text -> raw snake_case phrase -> visible graph`

## When to Use
Use this skill when:
- designing extraction schemas for a knowledge graph
- normalizing noisy entity or predicate phrases
- deciding what should be visible in the main graph vs metadata/debug views
- creating or reviewing ontology rules for Graph-RAG

## Canonicalization Rules

### Entities
1. If the item is a named entity (`person`, `organization`, `location`, `work`, etc.), preserve the full normalized span as the canonical id.
2. Otherwise choose the noun/proper-noun head.
3. Lemmatize that head.
4. Use the lemma as the canonical visible node id.
5. Store original phrases as `surface_forms` or provenance only.

Examples:
- `What Happiness Consists Of` -> `happiness`
- `Meaning of Life` -> `meaning`
- `Marcus Tullius Cicero` -> `marcus_tullius_cicero`

### Predicates
1. Select the predicate head token.
2. Prefer `VERB`, then `AUX`, then nominalized relation heads if no verb exists.
3. Lemmatize the head.
4. Use that single lemma as the canonical visible relation id.

Examples:
- `search for` -> `search`
- `looking for` -> `look`
- `consists of` -> `consist`
- `is devoted to` -> `devote`

## Layer Separation

### Visible default graph
Show only:
- canonical entity nodes
- canonical predicate nodes
- quote/document provenance nodes
- semantic evidence edges

### Hidden by default
Do not show in the main user-facing graph:
- `instance_of`
- `has_label`
- alias links
- hypernym / `subClassOf` scaffolding
- raw extracted phrase nodes

These belong in a debug or ontology view only.

## Provenance Policy
Keep source phrases, but keep them out of canonical identity.

Persist separately:
- `surface_forms`
- lexical review candidates
- throughlines
- quote evidence

The ontology node is the winner. The raw text is evidence for how that winner was chosen.

## Anti-Patterns
Avoid:
- using raw snake_case extractor phrases as ontology ids
- showing `instance_of` / `has_label` in the default graph
- mixing hypernym structure into the same view as answer evidence
- using multi-word predicate phrases as final visible relation ids
- treating provenance text as ontology identity

## Minimal Output Contract
When applying this skill, report:
- the canonical entity rule
- the canonical predicate rule
- which layers are visible by default
- which layers are hidden/debug only
- how provenance is preserved without becoming ontology identity
