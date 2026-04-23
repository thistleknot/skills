---
name: kg_ontology
description: Ontology protocol for choosing canonical graph identities from extracted spans, separating evidence from ontology, and keeping hypernym/debug structure out of the default user-facing graph and KG memory surfaces.
---
# KG Ontology Protocol

## Scope Boundary

This skill is for **graph identity** and **visibility rules**.

It owns:
- canonical entity identity
- canonical predicate identity
- span-to-node collapse rules
- ontology/debug layer separation
- provenance vs ontology boundaries

It does **not** own:
- triplet confidence updates
- page or wiki-memory construction
- NLI retrieval
- throughline ranking
- MemRL-style score evolution

Those belong to `agentic_kg_memory`.

## Core Thesis

The visible graph is not the raw extractor output, and the memory layer is not the ontology layer.

- **Surface spans** are evidence, not ontology ids
- **Ontology** chooses one canonical identity per span
- **Triplets** use those canonical ids as their atoms
- **Pages and throughlines** consume the triplets; they do not redefine node identity
- **Hypernyms and ontology scaffolding** stay separate and hidden by default

Default contract:

`surface text -> candidate lemma/synset+POS identities -> canonical winner -> triplets/pages/throughlines`

Not:

`surface text -> raw extractor phrase -> visible graph`

## When to Use
Use this skill when:
- designing extraction schemas for a knowledge graph
- normalizing noisy entity or predicate phrases
- deciding what the canonical node id should be for a span
- deciding what should be visible in the main graph vs metadata/debug views
- creating or reviewing ontology rules for Graph-RAG or KG-backed memory systems

## Relation to KG Memory

The split is:

- `kg_ontology` = **what node is this?**
- `agentic_kg_memory` = **what does this evidence mean together?**

`kg_ontology` resolves:
- canonical entity ids
- canonical predicate ids
- alias and provenance handling
- hidden ontology/debug structure

`agentic_kg_memory` resolves:
- triplet confidence
- page construction
- throughline synthesis
- reinforce / weaken / add updates
- retrieval and ranking

Do not let pages, objectives, or throughlines invent their own node identities.
They should consume the ontology winners.

## Canonicalization Pipeline

Follow this order:

1. Normalize the surface span
2. Remove obvious stopword or clausal debris
3. Generate candidate identities
4. Score candidates using role-aware signals
5. Choose one deterministic winner
6. Persist aliases and source text as provenance only

### Candidate generation

Generate candidates as **lemma/synset + POS** options where possible.

- If a reliable synset or ontology sense is available, keep it as a candidate
- If sense resolution is weak, fall back to lemma-first identity
- Keep the final visible graph to one canonical winner per span

This means the ontology can be richer than the visible node label. The visible
graph stays simple; the candidate set and rejected options live in provenance/debug.

### Candidate scoring

Score candidates with local and corpus-aware signals:

- POS prior conditioned on semantic role (`subject`, `predicate`, `object`)
- noun/proper-noun head salience for entities
- verb-head salience for predicates
- BM25 or lexical fit to the source context
- corpus/head frequency priors
- stopword removal and phrase cleanup
- named-entity preservation rules

The winner should be deterministic for the same evidence and scoring policy.

## Canonicalization Rules

### Entities

1. If the item is a named entity (`person`, `organization`, `location`, `work`, etc.), preserve the full normalized span as the canonical identity.
2. Otherwise generate noun/proper-noun head candidates.
3. Lemmatize those candidates and keep optional synset/POS variants if available.
4. Score candidates using role-aware and corpus-aware signals.
5. Choose one canonical winner.
6. Store original phrases, rejected candidates, and aliases as provenance only.

Examples:
- `What Happiness Consists Of` -> `happiness`
- `Meaning of Life` -> `meaning`
- `Marcus Tullius Cicero` -> `marcus_tullius_cicero`

### Predicates

1. Select predicate-head candidates.
2. Prefer `VERB`, then `AUX`, then nominalized relation heads if no verb exists.
3. Lemmatize the candidate head and keep optional synset/POS variants if available.
4. Score candidates with role-aware and corpus-aware signals.
5. Use the winning single canonical predicate identity in the visible graph.

Examples:
- `search for` -> `search`
- `looking for` -> `look`
- `consists of` -> `consist`
- `is devoted to` -> `devote`

### Role-conditioned selection

Do not score candidates in a role-blind way.

- `subject` and `object` slots should strongly prefer noun/proper-noun identities
- `predicate` slots should strongly prefer verb or relation-head identities
- if a span can support multiple POS readings, use the semantic role to break ties

POS and semantic role are correlated, not identical, but role should still inform
the winner selection.

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
- candidate sense lists
- rejected canonicalization candidates
- raw extracted phrase nodes

These belong in a debug or ontology view only.

## Provenance Policy
Keep source phrases, but keep them out of canonical identity.

Persist separately:
- `surface_forms`
- candidate_identities
- `candidate_scores`
- lexical review candidates
- quote evidence
- alias mappings

If triplets, pages, or throughlines refer to a node, they should refer to the
canonical winner. Provenance records how the winner was chosen.

The ontology node is the winner. The raw text is evidence for how that winner was chosen.

## Identity Rules for KG Memory Consumers

Triplets should store canonical subject/predicate/object ids plus provenance.

Pages and throughlines may aggregate:
- canonical entity ids
- canonical predicate ids
- triplet ids

They should not:
- promote raw surface text to a new node id
- keep alternate ontology candidates as peer visible nodes
- re-canonicalize spans independently from the ontology layer

## Fallback Policy

If explicit synset grounding is unavailable or too weak:

- keep the richer candidate set in provenance
- use the best lemma-level candidate as the canonical winner
- do not expose low-confidence ontology branching in the default graph

This keeps the graph deterministic now without blocking a later upgrade to
explicit synset ids plus a hidden hypernym layer.

## Anti-Patterns
Avoid:
- using raw snake_case or extractor phrases as ontology ids
- showing `instance_of` / `has_label` in the default graph
- mixing hypernym structure into the same view as answer evidence
- using multi-word predicate phrases as final visible relation ids
- letting pages or throughlines redefine ontology ids
- treating lemma collapse as enough when role or POS evidence points elsewhere
- treating provenance text as ontology identity

## Minimal Output Contract
When applying this skill, report:
- the canonical entity rule
- the canonical predicate rule
- the candidate generation and scoring rule
- how semantic role affects identity choice
- which layers are visible by default
- which layers are hidden/debug only
- how KG-memory consumers use canonical ids
- how provenance is preserved without becoming ontology identity
