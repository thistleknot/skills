The paper's core contribution is the knowledgeThe paper's core contribution is a conceptual liquidization and crystallization framework, which defines two algorithmic processes: (1) liquidizing knowledge by decomposing artifacts into atomic elements and forming rich connections among them, and (2) crystallizing knowledge by structuring elements into new artifacts under emerging contexts, with both processes involving human interaction and context as a guiding 'solvent' or 'catalyst'.

Decomposition:
- Sub-algorithm 1: Knowledge Liquidization (decompose artifact, create connections)
- Sub-algorithm 2: Knowledge Crystallization (identify structure among elements, assemble artifact)
- Context is used as input/guide for both.
- The actual computational steps are described at a high conceptual level, not in detail.

---

### Knowledge Liquidization

**Inputs:**
- artifact : document or structured knowledge artifact (e.g., text, document)
- context : context object/descriptor (e.g., user query, domain knowledge)

**Outputs:**
- elements : list of atomic elements (e.g., paragraphs, sections, concepts)
- connections : list of possible connections between elements

```
function Liquidize(artifact, context):
    elements = DecomposeArtifact(artifact, context)
    connections = []
    for e1 in elements:
        for e2 in elements:
            if e1 != e2 and IsPotentiallyConnected(e1, e2, context):
                connections.append((e1, e2))
    return elements, connections
```

**Inferred / Ambiguous:** 
- DecomposeArtifact: The paper states "decomposing a knowledge representation into atomic units" but does not specify how atomic units are determined; assumed as paragraphs/sections or similar [inferred].
- IsPotentiallyConnected: The paper states "adding links among atomic units..."; criteria for linking is not given [inferred].
- The function returns both the elements and their possible connections, which matches the description but details are unspecified.
- The actual mechanics for decomposition and connection detection are not described.

---

### Knowledge Crystallization

**Inputs:**
- elements : list of atomic elements (output from Liquidize)
- connections : list of possible connections between elements
- emerging_context : descriptor of the new context (e.g., user query, task)

**Outputs:**
- artifact : newly structured artifact (e.g., report, document, summary)

```
function Crystallize(elements, connections, emerging_context):
    relevant_elements = SelectRelevantElements(elements, emerging_context)
    structure = IdentifyStructure(relevant_elements, connections, emerging_context)
    artifact = AssembleArtifact(structure)
    return artifact
```

**Inferred / Ambiguous:** 
- SelectRelevantElements: The paper states "identifies new relationships among some of the units capturing an emerging context" but does not specify the selection method [inferred].
- IdentifyStructure: "discovers a new cohesive structure among coherent units," but the algorithm for structuring is not given [inferred].
- AssembleArtifact: How the structured elements are assembled into an artifact is not described [inferred].
- Actual computational criteria for relevance and structure formation are unspecified.

---

### System Usage Cycle

**Inputs:**
- user_input : user artifact or query (e.g., document, request for information)
- context : context object/descriptor

**Outputs:**
- system_output : artifact or knowledge structure for user

```
function KnowledgeCycle(user_input, context):
    if IsContribution(user_input):
        elements, connections = Liquidize(user_input, context)
        StoreInRepository(elements, connections)
        return AcknowledgeContribution()
    else: # user is requesting knowledge
        all_elements, all_connections = RetrieveFromRepository(context)
        artifact = Crystallize(all_elements, all_connections, context)
        return artifact
```

**Inferred / Ambiguous:** 
- IsContribution: Determining whether the user input is a knowledge contribution or a request is not explicitly defined [inferred].
- StoreInRepository, RetrieveFromRepository: Repository operations are referenced in the scenario but not specified [inferred].
- The flow is inferred from the KNC user story in Section 3.2.
- The process for matching context when retrieving elements/connections is not described.

---

No specific algorithmic details are given for the ART-SHTA or livingOM systems beyond interaction and representational paradigms, so only the above general framework methods are extractable from the text.