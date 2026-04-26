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
- cluster budgets, MMR, and recall backstops

Do not let pages, objectives, or throughlines invent their own node identities.
They should consume the ontology winners.

`kg_ontology` should not decide:

- which clusters get retrieval budget
- how many candidates come from each cluster
- whether to mix in global backstop results

Those are retrieval-policy questions, not identity questions.

## Connection Type Map

Seven distinct connection mechanisms operate in the graph. Each has a different
scope and purpose.

| # | Connection | Mechanism | Scope | Visible? |
|---|---|---|---|---|
| 1 | S-P-O within sentence | Triplet edge | Intra-sentence | Yes |
| 2 | Same canonical ID across sentences | Shared node identity | Cross-sentence | Yes (implicit) |
| 3 | SpaCy named entities across sentences | Named entity preservation → same canonical id | Cross-sentence | Yes (implicit) |
| 4 | Source string → entailed triplets | Throughline `supporting_fks` | String-to-many | Yes |
| 5 | Vertical alignment across sentences | BM25 — hypernym tokens injected into `bm25_text` | Cross-sentence | Implicit via retrieval |
| 6 | Polarity / negation | Stopwords preserved in `bm25_text` (NOT, never, no) | Intra-triplet | Via BM25 term match |
| 7 | Hypernym scaffolding | `subClassOf` lattice | Ontology layer | **Hidden by default** |

### Vertical alignment rule

Hypernym edges are **not** exposed as explicit cross-sentence graph edges.
Vertical alignment is achieved by **injecting the subject's hypernym chain tokens
into the `bm25_text`** of its sentence/page at index time.

```text
S1: dog.n.01 eat food.n.01
bm25_text(S1) = "dog.n.01 eat food.n.01 carnivore.n.01 animal.n.01 organism.n.01 matter.n.03"
```

A query for `animal` then retrieves S1 (dog), S2 (wolf), S3 (canine) via shared
token `animal.n.01` — without any explicit cross-sentence edge in the main graph.
The hypernym lattice lives in its own hidden layer; BM25 is the bridge.

### Polarity rule

Do **not** remove stopwords from the triplet text fed into `bm25_text`.
Negation markers (`NOT`, `never`, `no`, `without`) are stopwords in standard NLP
pipelines but are load-bearing for polarity. Stripping them collapses
`dog NOT eat plant` and `dog eat plant` into the same BM25 representation.

Preserve the full triplet token sequence including negation markers.
Polarity distinguishability is a property of the BM25 index, not a separate edge type.

### Diagram

```mermaid
graph LR

    subgraph CORPUS
        s1["S1: A dog eats food."]
        s2["S2: Wolves hunt prey."]
        s3["S3: A canine needs water."]
        s4["S4: Animals breathe oxygen."]
        s5["S5: Dogs do NOT eat plants."]
    end

    subgraph SYNSETS
        surf_dog["dog"]       -.->|resolves| syn_dog["dog.n.01"]
        surf_canine["canine"] -.->|resolves| syn_dog
        surf_wolf["wolf"]     -.->|resolves| syn_wolf["wolf.n.01"]
        surf_animal["animal"] -.->|resolves| syn_animal["animal.n.01"]
        surf_food["food"]     -.->|resolves| syn_food["food.n.01"]
        surf_prey["prey"]     -.->|resolves| syn_prey["prey.n.01"]
        surf_water["water"]   -.->|resolves| syn_water["water.n.01"]
        surf_oxygen["oxygen"] -.->|resolves| syn_oxygen["oxygen.n.01"]
        surf_plant["plant"]   -.->|resolves| syn_plant["plant.n.02"]
    end

    subgraph TRIPLETS
        tr_dog["dog.n.01"]       -->|"eat · S1"| tr_food["food.n.01"]
        tr_wolf["wolf.n.01"]     -->|"hunt · S2"| tr_prey["prey.n.01"]
        tr_dog                   -->|"need · S3"| tr_water["water.n.01"]
        tr_animal["animal.n.01"] -->|"breathe · S4"| tr_oxygen["oxygen.n.01"]
        tr_dog                   -->|"NOT eat · S5"| tr_plant["plant.n.02"]
    end

    subgraph SPACY
        sp_dog["dog.n.01"]
        sp_wolf["wolf.n.01"]
        sp_animal["animal.n.01"]
        sp_dog    -->|"nsubj-eat-dobj · S1"| sp_food["food.n.01"]
        sp_wolf   -->|"nsubj-hunt-dobj · S2"| sp_prey["prey.n.01"]
        sp_dog    -->|"nsubj-need-dobj · S3"| sp_water["water.n.01"]
        sp_animal -->|"nsubj-breathe-dobj · S4"| sp_oxygen["oxygen.n.01"]
        sp_dog    -->|"nsubj-NOT-eat-dobj · S5"| sp_plant["plant.n.02"]
    end

    subgraph HYPERNYMS["HYPERNYMS — hidden by default; tokens injected into BM25"]
        h_dog["dog.n.01"]       -->|subClassOf| h_carn["carnivore.n.01"]
        h_wolf["wolf.n.01"]     -->|subClassOf| h_carn
        h_carn                  -->|subClassOf| h_animal["animal.n.01"]
        h_animal                -->|subClassOf| h_org["organism.n.01"]
        h_food["food.n.01"]     -->|subClassOf| h_matter["matter.n.03"]
        h_water["water.n.01"]   -->|subClassOf| h_matter
        h_oxygen["oxygen.n.01"] -->|subClassOf| h_element["element.n.02"]
        h_plant["plant.n.02"]   -->|subClassOf| h_org
    end

    subgraph BM25["BM25 INDEX — vertical alignment via hypernym tokens · stopwords preserved for polarity"]
        bm25_s1["S1: dog.n.01 eat food.n.01 + carnivore animal organism matter"]
        bm25_s2["S2: wolf.n.01 hunt prey.n.01 + carnivore animal organism"]
        bm25_s3["S3: dog.n.01 need water.n.01 + carnivore animal organism matter"]
        bm25_s4["S4: animal.n.01 breathe oxygen.n.01 + organism element"]
        bm25_s5["S5: dog.n.01 NOT eat plant.n.02 + carnivore animal organism"]
        q_animal(["query: animal"])
        q_animal -->|"shared token: animal.n.01"| bm25_s1
        q_animal -->|"shared token: animal.n.01"| bm25_s2
        q_animal -->|"shared token: animal.n.01"| bm25_s3
        q_animal -->|"direct hit"| bm25_s4
        q_animal -->|"shared token: animal.n.01"| bm25_s5
    end

    subgraph THROUGHLINES
        tl_s1["TL S1: Dogs consume resources"]
        tl_s2["TL S2: Wolves are predators"]
        tl_s3["TL S3: Canines have hydration needs"]
        tl_s4["TL S4: Animals require gases"]
        tl_s5["TL S5: Dogs avoid plant matter"]
        tl_s1 -->|supporting_fks| tr_dog
        tl_s1 -->|supporting_fks| tr_food
        tl_s2 -->|supporting_fks| tr_wolf
        tl_s2 -->|supporting_fks| tr_prey
        tl_s3 -->|supporting_fks| tr_dog
        tl_s3 -->|supporting_fks| tr_water
        tl_s4 -->|supporting_fks| tr_animal
        tl_s4 -->|supporting_fks| tr_oxygen
        tl_s5 -->|supporting_fks| tr_dog
        tl_s5 -->|supporting_fks| tr_plant
    end

    s1 -->|extracts| surf_dog
    s1 -->|extracts| surf_food
    s2 -->|extracts| surf_wolf
    s2 -->|extracts| surf_prey
    s3 -->|extracts| surf_canine
    s3 -->|extracts| surf_water
    s4 -->|extracts| surf_animal
    s4 -->|extracts| surf_oxygen
    s5 -->|extracts| surf_dog
    s5 -->|extracts| surf_plant

    s1 -->|local TL| tl_s1
    s2 -->|local TL| tl_s2
    s3 -->|local TL| tl_s3
    s4 -->|local TL| tl_s4
    s5 -->|local TL| tl_s5

    syn_dog    -.-> tr_dog
    syn_dog    -.-> sp_dog
    syn_dog    -.-> h_dog
    syn_wolf   -.-> tr_wolf
    syn_wolf   -.-> sp_wolf
    syn_wolf   -.-> h_wolf
    syn_animal -.-> tr_animal
    syn_animal -.-> sp_animal
    syn_animal -.-> h_animal
    syn_food   -.-> tr_food
    syn_food   -.-> h_food
    syn_water  -.-> tr_water
    syn_water  -.-> h_water
    syn_oxygen -.-> tr_oxygen
    syn_oxygen -.-> h_oxygen
    syn_plant  -.-> tr_plant
    syn_plant  -.-> h_plant

    h_dog    -.->|inject| bm25_s1
    h_wolf   -.->|inject| bm25_s2
    h_dog    -.->|inject| bm25_s3
    h_animal -.->|inject| bm25_s4
    h_dog    -.->|inject| bm25_s5
```

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

### Candidate retrieval surface

Do not make the LLM choose from the whole ontology blindly.

Instead, build a tightly scoped candidate set for each span:

1. look up the normalized token/span in a **first-synset dictionary** if available
2. retrieve embedding-near lexical neighbors for the span
3. take the top `21` related words as expansion hints
4. for each strong related word, retrieve the top `3` first-synset candidates
5. derive a compact hypernym candidate set from those synsets
6. present that narrowed set to the LLM for selection or abstention

This same narrowing rule applies to **hypernyms** as well as synsets.

### First-synset dictionary

If a first-synset dictionary is available, use it as the first narrowing layer.

The important contract is not that the LLM sees an unlimited WordNet dump. The
important contract is that it sees a **small, relevant candidate set**.

That candidate set may come from:

- direct first-synset dictionary hits
- embedding-neighbor expansion
- role-aware lexical filters
- named-entity preservation rules

### Embedding-assisted candidate expansion

If direct dictionary lookup is too sparse, use word embeddings to retrieve
semantic neighbors first.

Recommended narrowing pattern:

- retrieve the top `21` related words for the span
- collect the top `3` first-synset candidates for each strong neighbor
- score the resulting synset pool by role, POS, lexical fit, and frequency
- derive a Pareto-like shortlist for the LLM rather than a flat unbounded list

This keeps correction retrievals tightly scoped and reduces absurd jumps such as
`john -> toilet`.

### Hypernym narrowing

The same approach should be used for hypernyms.

Do not retrieve hypernyms globally from the entire ontology tree.

Instead:

1. narrow to candidate synsets first
2. derive hypernym candidates only from that narrowed synset set
3. score those hypernyms with local context and role constraints
4. let the LLM choose from the shortlist or reject all of them

Hypernyms are ontology scaffolding, not free-floating replacement labels.
They should remain tightly coupled to the candidate synset pool that produced them.

### WordNet topology notes

If WordNet is the backing ontology, remember the structure:

- noun hypernyms form a **DAG**, not a simple tree
- verbs behave more like a **forest** of smaller hierarchies
- adjectives and adverbs should not be treated like the noun hypernym lattice
- multiple inheritance exists, so one candidate may legitimately map upward in more than one way

That means the system should not assume one universal parent chain for every item.
Hypernym correction must stay local to the narrowed synset set.

### Corpus-availability rule

If the runtime cannot reach the corpus or the exact inventory is unavailable:

- do **not** guess exact global counts
- do **not** expand to the entire ontology blindly
- continue using the local narrowed candidate set from dictionary hits, embeddings, and role filters
- preserve uncertainty in provenance/debug metadata

The ontology workflow depends more on **good local narrowing** than on knowing the
exact global synset or hypernym totals.

### Candidate scoring

Score candidates with local and corpus-aware signals:

- POS prior conditioned on semantic role (`subject`, `predicate`, `object`)
- noun/proper-noun head salience for entities
- verb-head salience for predicates
- BM25 or lexical fit to the source context
- corpus/head frequency priors
- stopword removal and phrase cleanup
- named-entity preservation rules

If you have a narrowed candidate set from dictionary hits, embedding neighbors,
or derived hypernyms, score **within that set**. Do not reopen the search space
after narrowing unless confidence is explicitly too low.

The winner should be deterministic for the same evidence and scoring policy.

## Canonicalization Rules

### Entities

1. If the item is a named entity (`person`, `organization`, `location`, `work`, etc.), preserve the full normalized span as the canonical identity.
2. Otherwise generate noun/proper-noun head candidates.
3. Lemmatize those candidates and keep optional synset/POS variants if available.
4. Score candidates using role-aware and corpus-aware signals.
5. Choose one canonical winner.
6. Store original phrases, rejected candidates, and aliases as provenance only.

If the entity is a person or other preserved named entity, strongly penalize
candidate synsets or hypernyms that would collapse it into an unrelated common noun.

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

If dictionary lookup, embedding neighbors, and hypernym narrowing all remain weak:

- let the LLM abstain from synset/hypernym commitment
- keep the lemma-level identity
- preserve the candidate shortlist in provenance for later repair

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
- how synset and hypernym candidate sets are narrowed before LLM choice
- how semantic role affects identity choice
- which layers are visible by default
- which layers are hidden/debug only
- how KG-memory consumers use canonical ids
- how provenance is preserved without becoming ontology identity
