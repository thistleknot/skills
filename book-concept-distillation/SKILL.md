---
name: book-concept-distillation
description: >
  Distill core concepts from technical books (data science, programming) into
  reusable SKILL.md artifacts, using a local multimodal pipeline. Concepts are
  tagged at chunk level, consolidated up an aggregation hierarchy, and
  cross-referenced across books via a normalized concept index. Use when
  converting a corpus of extracted books into a tagged, cross-linked skill
  library. Cross-reference: `extractive-context-pruning` for the consolidation
  step when a tier's aggregate overflows context; `crystallize` for the digest
  protocol; `fable-mode` for the staged build.
status: active
last_validated: 2026-06-15
validation_method: design synthesis session
---

# Book Concept Distillation

## Question

How do you turn a corpus of extracted technical books into a cross-referenced
library of concept-tagged SKILL.md files, running locally on a single 16GB GPU,
with a pass structure that adds no redundant work?

---

## Why This Exists

The goal is not a concept graph for its own sake. It is auto-generated skills:
each durable concept becomes a SKILL.md, and concept tags are the index that
links skills to each other and back to their source chapters and books.

Two forces shape the design:

1. **Aggregation discipline** — a pass earns its place only if it consolidates
   an aggregate that did not exist until the prior tier finished. Anything that
   re-reads the same granularity is a step, not a pass.
2. **Context rot** — consolidating too large an aggregate in one model call
   degrades output mid-list. This is what forces a combiner tier for large
   books and connects directly to `extractive-context-pruning`.

---

## Aggregation Tiers

The pipeline has one generating sweep and a hierarchy of capstones. Each tier
consolidates the tier below.

### Tier 0 — Chunk sweep (the only forward pass)

Iterate OWUI chunks in document order. The VLM reads each chunk (text, plus
images where present) and emits concept tags. Read and tag are the same call.
Fold each tag into a running index: `concept -> [attestations]`, where each
attestation carries chunk / chapter / book provenance.

Image chunks route to the vision model; text-only chunks skip it. This is the
generating tier — every later tier consumes its index, never re-reads chunks.

### Tier 1 — Chapter combiner (CONDITIONAL)

A local reduce over one chapter's chunk-tags: deduplicate and consolidate into
a chapter-scoped concept list. This is a map-reduce combiner, not a fundamental
concept boundary. Its only job is cardinality reduction — turn N raw chunk-tags
into a smaller chapter concept set so the book tier reconciles less at once.

**Enable only when a book's full tag set would overflow clean consolidation
context.** Small papers: skip it, consolidate at book tier directly. Large
references: it earns its keep. The toggle is keyed to measured tag cardinality
per book, not assumed.

### Tier 2 — Book capstone (UNCONDITIONAL)

Consolidate concepts across all chapters of a book. A concept attesting in
chapters 2 and 7 resolves to one concept here — its identity completes at book
scope, not chapter scope. Skill distillation happens at this tier: each
above-threshold concept becomes a SKILL.md draft, because concept identity is
stable within a book.

Intra-book cross-references are free — they are already in the index.

### Tier 3 — Cross-book capstone (UNCONDITIONAL, per book added)

Normalize concepts across books. This is entity resolution: the same concept
under different names across authors ("backprop" / "backpropagation" /
"reverse-mode autodiff") must canonicalize to one node. Fires once per book
added, reconciling that book's concepts against the existing skill library —
merge, enrich, or fork. The cross-book aggregate only exists after >= 2 books.

---

## Physical Realization

The logical structure is one sweep plus boundary-fired capstones. The physical
model placement is governed by 16GB VRAM on the Quadro P5200.

### Model stack (Ollama, qwen3.5 family)

qwen3.5 is Alibaba's Feb 2026 multimodal family — sizes 0.8b/2b/4b/9b/27b/35b,
256K context, unified vision + text. The family being multimodal means one
size can do both reading and tagging if quality allows.

- **Tier 0 sweep:** `qwen3.5:2b` vision (~2.7GB, fine for small schematics, not
  dense figure reasoning) + a small text tagger (`qwen3.5:9b` ~6.6GB). Both
  resident at ~9.3GB — no per-chunk model swap.
- **Tier 2/3 capstones:** swap to a larger model (`qwen3.5:27b` ~17GB or
  `qwen3.6:35b`) at the boundary for distillation quality. The swap aligns with
  the aggregate boundary — never per chunk.

### Ollama gotchas (silent failures)

- `OLLAMA_MAX_LOADED_MODELS=2` and a long `keep_alive` — otherwise Ollama
  unloads a model between calls and thrashes VRAM during the sweep.
- Set `num_ctx` explicitly. The default truncates chunks without warning
  despite the 256K ceiling.
- Use `format` with a JSON schema for tag emission — reliable structured output
  (integer indices or label lists), not free-text parsing.
- **GGUF vision trap:** imported GGUF fine-tunes may lack a working mmproj
  vision file in Ollama; vision silently fails. Keep the vision path on the
  stock packaged `qwen3.5:2b` or route it through llama.cpp. Use custom
  fine-tunes for text-only tagging / distillation legs.

---

## Tagging and Distillation Shape

- **Tier 0 tag output:** free-form concept labels, cheap and noisy by design.
  A 2b-class tagger is acceptable here *only because* the book capstone uses a
  stronger model to consolidate and clean.
- **Above-threshold gate:** only concepts above a frequency threshold get
  distilled into skills. Decide whether the threshold is global or
  per-book-normalized — 3 hits in a 40-page paper != 3 hits in an 800-page
  reference. Per-book normalization is the safer default.
- **Concept matching at tier 3:** similarity-shortlist (pgvector over concept
  name + definition embeddings) plus an LLM adjudication call on near-matches.
  Embedding threshold alone over-merges. False merges are the expensive error —
  bias toward keeping concepts separate and forking on doubt.

---

## Pseudocode

The synthesis between this skill and `extractive-context-pruning`: concept
identification produces a query; extract_spans pulls the verbatim evidence;
the capstone distills evidence into a skill. Three operations, one data flow.

```
# ── TIER 0: chunk sweep (one forward pass per chunk) ──────────────────────

concept_index = {}   # concept_label -> [chunk, ...]

for chunk in book.chunks_in_order():
    if chunk.has_image:
        image_desc = vision_model.describe(chunk.image)   # qwen3.5:2b
        text = chunk.text + "\n" + image_desc
    else:
        text = chunk.text

    # Cheap noisy tagging — free-form labels, one call per chunk
    labels = tagger.tag(query=None, chunk=text)
    # tagger: qwen3.5:9b fine-tune, JSON schema {"concepts": ["str",...]}

    for label in labels:
        concept_index[label].append(chunk)


# ── TIER 1: chapter combiner (CONDITIONAL — enable if len(concept_index) > 200) ──

if len(concept_index) > CHAPTER_COMBINER_THRESHOLD:
    concept_index = consolidate_within_chapter(concept_index)
    # collapses near-duplicate labels within chapter scope only


# ── TIER 2: book capstone ─────────────────────────────────────────────────

swap_model(qwen3.5:27b)   # swap at boundary, never per chunk

for concept, attestation_chunks in concept_index.items():

    # Gate: skip low-frequency concepts
    freq_ratio = len(attestation_chunks) / book.total_chunks
    if len(attestation_chunks) < 2 or freq_ratio < 0.005:
        continue

    # ── THE SYNTHESIS ──
    # Use the concept label as the query into extract_spans.
    # This is the call into `extractive-context-pruning`.
    relevant_spans = []
    for chunk in attestation_chunks:
        spans = extract_spans(query=concept, chunk=chunk.text)
        # returns [(char_start, char_end, verbatim_text), ...]
        relevant_spans.extend(spans)

    # Distill verbatim spans → SKILL.md
    # Only the extracted spans reach the distillation model — not full chunks.
    # This is the token budget win: 5-10x fewer tokens into the capstone call.
    skill_draft = distill(
        concept=concept,
        evidence=relevant_spans,       # verbatim, source-ordered
        provenance=attestation_chunks  # chapter/book metadata for cross-refs
    )
    write_skill(skill_draft)           # → skills repo as SKILL.md


# ── TIER 3: cross-book capstone (fires per book added) ────────────────────

for concept, skill in new_book.skills.items():
    embedding = embed(concept.name + " " + concept.one_line_definition)
    candidates = pgvector.query(embedding, threshold=0.85)

    if not candidates:
        write_new_skill(skill)
        continue

    # LLM adjudicates near-matches — fork on doubt
    decision = adjudicate(concept, candidates)
    if decision == "merge":
        enrich_existing_skill(candidates[0], relevant_spans)
    else:
        fork_skill(skill)   # keep separate, add cross-reference tag
```

**The key join:** `extract_spans(query=concept, chunk=chunk.text)` is where
the two skills meet. The concept label from the tagging pass becomes the
query; the attestation chunk becomes the document; ColBERT MaxSim returns
only the verbatim sentences that support that concept. The distillation model
sees dense relevant evidence, not full chunks with topic drift.

**Why this ordering matters:** running extract_spans before distillation
reduces the token budget into the capstone call by 5-10x, which is the
difference between a 27b model staying within a clean context window and
degrading mid-distillation on a large book's attestation set.

---

## Lessons

- A pass is legitimate only as a capstone over a new aggregate. Chunk ->
  chapter -> book -> corpus are candidate tiers, but chapter is a combiner
  (optimization), not a semantic boundary. Book and cross-book are the only
  unconditional capstones.

- Demote chapter from a pass to a tag when book-level consolidation fits in one
  clean context. The chapter combiner is dead weight unless cardinality forces
  it. Measure before enabling.

- Concept identity completes at book scope. Distilling skills at chapter
  boundaries fragments cross-chapter concepts and reintroduces a merge pass.
  Distill at book; enrich at cross-book.

- Read and tag are one operation. There is no separate "extraction" sweep —
  tagging happens as the VLM reads.

- Model swaps belong at aggregate boundaries, never per chunk. Per-chunk
  swapping on 16GB is the dominant latency cost and is avoidable.

- Cheap-and-noisy tagging is correct at tier 0 because a stronger model cleans
  it at the capstone. Do not over-invest the tagger.

- The unified multimodal family means you may collapse vision + text to one
  model — but only if a single size satisfies both schematic-reading and
  tagging. Verify before assuming you need two.

---

## Entities

- **OWUI** — Open-WebUI, source of extracted book chunks. Needs a
  document-iteration endpoint distinct from its retrieval/query API.
- **Hermes Agent** — NousResearch autonomous agent; orchestrates the sweep
  (sequential sub-agent) and capstones (boundary-triggered sub-agents); holds
  the concept index in persistent memory; writes SKILL.md to the skills repo.
- **qwen3.5** — Alibaba Feb 2026 multimodal Ollama family, 0.8b–122b, 256K ctx.
- **qwen3.6:35b** — May 2026 follow-on, agentic-coding focused; capstone option.
- **pgvector / SQLite Graph-RAG** — existing substrate for the concept index
  and cross-book entity resolution.
- **extractive-context-pruning** — paired skill; invoked inside a capstone when
  a concept's attestation set is too large to consolidate in one call.

---

## Open Questions

- Frequency threshold: global or per-book-normalized? (Leaning per-book.)
- Concept matching at tier 3: embedding-only vs shortlist + LLM adjudication,
  and what false-merge rate is tolerable.
- Chapter-combiner trigger: at what measured per-book tag cardinality does
  book-level consolidation start degrading? Benchmark on one real book.
- Does OWUI expose ordered full-document chunk iteration, or only retrieval?
- Are the qwen3.5 fine-tunes text-only, or vision-capable checkpoints?
- Token-reduction and concept-recall numbers on the actual corpus — not yet
  measured.

---

## Dead Ends

### Chapter as a fixed pass
Running a chapter consolidation pass unconditionally re-does work the book pass
would do anyway. It is a combiner, justified only by cardinality. Toggle it.

### Skill distillation at chapter boundary
Fragments cross-chapter concepts into partial skills that need a later merge —
the exact pass the design eliminates. Distill at book scope.

### Per-chunk model swapping
Interleaving vision and text models per chunk on 16GB thrashes VRAM. Keep the
small pair resident; swap only at capstone boundaries.

### Embedding-only cross-book merge
Similarity threshold alone over-merges distinct concepts. Use a shortlist plus
LLM adjudication; fork on doubt.

### Trusting imported GGUF vision in Ollama
Vision silently fails without the mmproj file. Verify the vision path on stock
packaged models or llama.cpp before building on it.

---

## Applicability Envelope

**Works well when:**
- the corpus is many technical books with recurring, nameable concepts
- output is a tagged, cross-linked skill library (not a one-off summary)
- running locally on constrained VRAM where model residency matters
- concepts recur across chapters and books, making consolidation valuable

**Fails or degrades when:**
- books are tightly scoped single-topic works (little to consolidate)
- images carry dense, reasoning-heavy figures beyond a 2b VLM's reach
- the concept definition is too vague to tag consistently
- OWUI cannot iterate chunks in document order

**Environment assumptions:**
- OWUI holds extracted, chunked books with ordered access
- Ollama runs the qwen3.5 family with two-model residency configured
- a Graph-RAG substrate (pgvector / SQLite) backs the concept index
- Hermes orchestrates the sweep and capstones