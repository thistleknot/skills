The paper's core contribution is the decomposition and high-level architectural design of three distinct knowledge agent paradigms—RAG, LLM Wiki, and Fat Skills—focusing on their operational primitives and knowledge workflows. The methods are architectural, not algorithmic in the sense of precise computational steps, but can be pseudocoded as high-level process flows for each paradigm as described in the diagrams and tables.

Decomposition: The three main architectures described are:
1. RAG (Retrieval-Augmented Generation) Pipeline
2. LLM Wiki (Distillation/Compilation Workflow)
3. Fat Skills (Skill Routing and Autonomous Action)

Each is a distinct top-level method. There are also subcomponents such as the routing in Fat Skills and the distillation in LLM Wiki. The diagrams and descriptions provide the process flows but not low-level algorithmic details.

---

### RAG (Retrieval-Augmented Generation) Pipeline

**Inputs:**
- documents : list of unstructured documents (arbitrary formats; e.g., PDF, text, etc.)
- query : string

**Outputs:**
- answer : string

```
# Step 1: Embed documents
for doc in documents:
    chunks = chunk_document(doc)  # [inferred]: chunking strategy not specified
    for chunk in chunks:
        embedding = embed(chunk)
        add_to_vector_store(chunk, embedding)

# Step 2: On query, retrieve and generate
query_embedding = embed(query)
retrieved_chunks = vector_store_top_k(query_embedding, k)  # retrieve top-k chunks
answer = LLM_generate(query, retrieved_chunks)
return answer
```

**Inferred / Ambiguous:** 
- `chunk_document` implementation is not specified. 
- Embedding model choice, chunk size, and retrieval k are not given.
- LLM_generate is not defined in detail.
- No explicit details on vector store implementation.
- Basic RAG process flow only; no advanced augmentations described.

---

### LLM Wiki (Distillation/Compilation Workflow)

**Inputs:**
- sources : list of raw documents (e.g., PDFs, transcripts, notes)
- existing_wiki : set of wiki pages (can be empty)
- schema : rules for wiki page structure and fields

**Outputs:**
- updated_wiki : set of refined, cross-linked wiki pages

```
for source in sources:
    extracted_knowledge = distill(source)  # Uses LLM to convert raw doc to knowledge [inferred]: distillation details not specified
    for topic in extracted_knowledge.topics:
        page = find_or_create_wiki_page(topic, existing_wiki)
        page = update_page_with_extracted_knowledge(page, extracted_knowledge[topic])
        enforce_schema(page, schema)
        cross_link(page, updated_wiki)
    updated_wiki = save_or_update_pages(existing_wiki, extracted_knowledge)
return updated_wiki
```

**Inferred / Ambiguous:**
- `distill` process is not detailed (how LLM is used, prompts, etc.).
- Rules for cross-linking, schema enforcement, and update logic are not specified.
- How conflict resolution or page merging is handled is not detailed.
- No detail on how the wiki "compounds" knowledge over time.
- Cross-linking and enforcement of schema are described at a high level only.

---

### Fat Skills (Skill Routing and Autonomous Action)

**Inputs:**
- user_request : string
- routing_table : mapping from patterns to skills
- skill_set : set of skill modules (each can be invoked)
- cron_jobs : list of scheduled skill invocations

**Outputs:**
- result : action output or answer (varies by skill)

```
# On user request:
matched_skill = pattern_match(user_request, routing_table)
if matched_skill is not None:
    result = invoke_skill(matched_skill, user_request)
    return result

# Autonomous operation (cron jobs):
for cron in cron_jobs:
    if cron.schedule_due():
        result = invoke_skill(cron.skill, cron.parameters)
        log_result(cron, result)
```

**Inferred / Ambiguous:**
- `pattern_match` is described as deterministic; method not specified.
- Skill invocation, logging, and error handling are not detailed.
- No detail on how skills are authored or composed.
- How "skills run themselves" (autonomy) is mentioned but not specified in implementation.

---

No further algorithmic detail is present in the paper. All flows above are supported directly by the diagrams and text. No low-level code or data structures are specified.