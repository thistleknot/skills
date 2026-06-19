---
name: extractive-context-pruning
description: >
  Select verbatim spans from retrieved chunks using query-conditioned extractive
  methods before LLM generation. Use in any RAG or agentic memory recall path
  where context rot, token budget, or faithfulness matter. Default mechanism is
  ColBERT MaxSim on the document-token axis — out-of-the-box token spans, no
  fine-tuning. Spectrum spans token (ColBERT) and sentence (Provence, NLI,
  decoder) granularity. Cross-reference: `multigran-sparse-retrieval` for
  upstream retrieval; `customer-intent-resolution` for downstream routing.
status: active
last_validated: 2026-06-15
validation_method: literature review + design synthesis session
---

# Extractive Context Pruning

## Question This Skill Answers

What is the best mechanism for selecting verbatim, query-relevant sentence spans
from retrieved chunks before passing context to an LLM — balancing faithfulness,
speed, and minimal training overhead?

---

## Why This Exists

Context rot: LLM output quality degrades continuously as input token count grows,
well before the context window fills. Chroma 2025 tested 18 frontier models and
found all degrade, with severity increasing on complex tasks and when
needle–question semantic similarity is low — the exact regime RAG operates in.

The fix is not a larger context window. It is a tighter context: strip
retrieved chunks to only the sentences that answer the query before the LLM
sees them.

Abstractive compression (LLMLingua, abstractive RECOMP) is one path but
introduces a hallucination surface inside the compression step itself, and runs
at LLM latency. Extractive selection is verbatim and fast — no hallucination
path in the prune step.

---

## Mechanism Spectrum

### 1. ColBERT MaxSim, token axis — the OOB token-span extractor (DEFAULT)

This is the model people assume must exist for "given query + context, return all
relevant spans." It exists. It is ColBERT, used out-of-the-box with no
fine-tuning.

The insight: ColBERT's MaxSim already computes per-token query-document
relevance. The standard relevance score sums the per-query-token maxima into one
scalar. Keep the other axis instead — the per-DOCUMENT-token maximum — and you
have the relevance of each context token to the query, for free, from the same
forward pass.

```
1. encode query  -> E_q  (token embeddings, kept, not pooled)
2. encode chunk  -> E_d  (token embeddings, kept, not pooled)
3. for each document token d_j:
       rel[j] = max over query tokens i of  cos(E_q[i], E_d[j])
4. threshold rel[]            (calibrate; start ~0.5 cosine)
5. merge adjacent kept tokens -> span tuples
6. emit verbatim spans in SOURCE ORDER
```

Why no fine-tuning: ColBERT preserves per-token embeddings rather than pooling,
and generalizes out-of-domain by design — the property a BIO head has to be
trained to acquire. The token-relevance signal is architectural, not learned per
task.

OOB checkpoints (via PyLate or the colbert lib):
- `answerdotai/answerai-colbert-small-v1` (~33M, fast — default)
- `jinaai/jina-colbert-v2` (multilingual, longer context)
- `colbert-ir/colbertv2.0` (canonical)

Latency: ~10ms GPU. Verbatim. Native multi-span tuples.

Property to respect (guidance, not a caveat): MaxSim is bounded by query token
count — at most N_query document tokens clear the max per query, and very long
queries inject noise. Keep queries focused. For multi-concept queries, run one
pass per concept and union the spans.

This is the answer to "why isn't there an OOB IR model for this." There is — it
was summed one axis too early.

### 2. Encoder sentence labeler — Provence (sentence granularity + reranking)

Architecture: DeBERTa-v3-large cross-encodes [query, all sentences] in a single
forward pass. Per-sentence binary label: keep / discard. Threshold is adaptive —
no fixed compression ratio required.

Key property: sentences are encoded jointly, so coreference between sentences
is captured. A two-sentence answer ("We trained a model. It is called Provence.")
is selected correctly; independent encoding would miss the link.

Unified with reranking: if a reranker is already in the pipeline, Provence
folds in at nearly zero added cost.

Latency: ~5–20ms GPU. Requires a trained model (available on HuggingFace:
`naver-labs-europe/provence-reranker-debertav3-v1`).

### 3. Decoder attention probe — Sentinel (zero training, sentence level)

Architecture: 0.5B proxy decoder LLM processes a QA-style prompt over the chunk.
Final-token attention is extracted. A lightweight linear classifier trained on
attention features scores sentence relevance.

Key property: no dedicated compression model to train. The proxy LLM is
model-agnostic — works with any downstream generator.

Sentinel shuffles sentence order during training to remove positional bias,
forcing semantic relevance rather than position heuristics.

Latency: ~50–100ms (small decoder). Needs the classifier training step but not
a full fine-tune.

### 4. Entailment / NLI (1-degree functional relevance)

Architecture: NLI model (DeBERTa-NLI, MNLI-trained) classifies each sentence
as entailing, neutral, or contradicting a hypothesis derived from the query.
Per-sentence, independent encoding.

Key property: entailment is asymmetric and logical — it captures causal and
functional relationships, not just topical proximity. If the query is "preparing
for surgery", the hypothesis "sterilization is required" is entailed even though
"sterilization" and "surgical procedure" may sit in different embedding clusters.
This is the right mechanism when relevant sentences are one functional hop from
the query rather than topically identical to it.

Latency: ~5ms GPU. Models widely available (cross-encoder/nli-deberta-v3-large).

Limitation: independent sentence encoding misses cross-sentence coreference.
Use when the relevance relationship is logical/causal; use cross-encoder when
coreference within the chunk matters more.

### 5. Decoder + integer indices (zero infra, multi-hop reasoning)

Architecture: split chunk into sentences, number them 0..N-1, pass the list to
a small decoder model. Constrained-decode to JSON schema
`{"relevant": [int, ...]}`. Reconstruct verbatim by index lookup.

Key property: integer indices are trivially reliable under constrained decoding.
Character/token offsets require precise counting and are fragile — do not use.
Span text output with downstream string match is the only alternative.

Validation required: assert all returned indices are in [0, N-1]. Regen on
failure, budget 1–2 retries, then fall back to full chunk or encoder labeler.
Log failure rate by model/chunk-length to detect model ceiling before prod.

Latency: ~50–200ms depending on model size. Zero training, zero new infra if a
small decoder is already in the stack.

---

## Decision Matrix

| Criterion | ColBERT MaxSim | Provence labeler | Entailment | Attention probe | Decoder + indices |
|---|---|---|---|---|---|
| Granularity | Token spans | Sentence | Sentence | Sentence | Sentence |
| Latency | ~10ms | ~10ms | ~5ms | ~75ms | ~100ms |
| Training needed | None (OOB) | Pretrained | Pretrained | Classifier training | None |
| New infra | ColBERT ckpt | Reranker | NLI model | Proxy LLM + classifier | Any decoder |
| Coreference | Late interaction | Yes (joint) | No | Yes | Yes |
| 1-degree relevance | Partial | Partial | Yes (logical) | Partial | Yes (reasoning) |
| Multi-span tuples | Native | Via sentences | Via sentences | Via sentences | Via indices |
| Output reliability | Exact | Exact | Exact | Exact | Requires validation |

**Default to ColBERT MaxSim (token axis)** when: you want verbatim token spans
out-of-the-box with no fine-tuning, the query is focused, and you do not already
have a reranker you'd rather reuse. This is the primary recommendation.

**Select Provence** when: you want sentence granularity AND a reranker folded
into one near-zero-cost stage. Sentence boundaries are coarser but coreference
across sentences is captured by joint encoding.

**Select entailment** when: relevant sentences are one functional or causal hop
from the query — not topically identical but logically implied. Medical, legal,
procedural domains.

**Select attention probe** when: zero training budget, you want sentence scores
from a small decoder already in the stack.

**Select decoder + indices** when: relevance requires multi-hop reasoning the
query doesn't state explicitly, or a decoder is already mid-call (agentic memory
recall inside an existing LLM turn).

---

## Integration Point

Pruning belongs **on the recall/read path only**.

```
hybrid RRF
  → top-K chunks
  → sentence splitter
  → query-conditioned selector          ← this skill
  → re-emit kept sentences in SOURCE ORDER
  → generator
```

**Source order is mandatory.** After selection, always re-sort kept sentences
by their original position in the chunk. Relevance-rank order produces
incoherent context — the logical flow of the source breaks.

**Never prune at write time.** At memory write time the future query is unknown.
Lossy pruning at write time is irreversible and violates the reversibility
contract. Correct pattern: write full trace, prune only at recall when the
query is present.

---

## Pseudocode

This is the canonical function other skills call. Signature is fixed: takes a
query and a chunk, returns a list of verbatim span tuples in source order.

```
function extract_spans(query, chunk, threshold=0.5):
    # Encode — two independent forward passes, no joint encoding
    E_q = colbert.encode_query(query)       # shape: [n_query_tokens, dim]
    E_d = colbert.encode_document(chunk)    # shape: [n_doc_tokens, dim]

    # MaxSim: flip the axis ColBERT normally sums over
    # sim_matrix[i, j] = cosine(E_q[i], E_d[j])
    sim_matrix = cosine_similarity(E_q, E_d)    # [n_query_tokens, n_doc_tokens]
    doc_scores = sim_matrix.max(axis=0)          # [n_doc_tokens] — the axis flip

    # Threshold and merge adjacent relevant tokens into spans
    mask = doc_scores >= threshold               # [n_doc_tokens] bool
    spans = merge_adjacent_tokens(mask, chunk)
    # merge_adjacent_tokens: walk mask, collect contiguous True runs,
    # map token offsets back to character offsets in original chunk

    # Return verbatim text in source order (already in order by construction)
    return [(char_start, char_end, chunk[char_start:char_end]) for each span]

# Threshold calibration: run on a held-out chunk with known relevant passage,
# sweep 0.3–0.7, pick the value that best captures the known relevant text.
# Start at 0.5; most corpora settle between 0.45–0.6.

# Multi-concept query: run one pass per concept, union the span sets,
# merge overlapping spans, emit in source order.
```

**Caller contract:**
- Require: query is a focused noun phrase or short sentence (not a multi-topic paragraph)
- Require: chunk is a string with recoverable token→character offset mapping
- Guarantee: returned spans are verbatim substrings of chunk, in source order
- Guarantee: no span crosses a chunk boundary (call per chunk, not per document)
- Maintain: threshold is stable across a session; re-calibrate only per corpus

---

## Lessons

- The OOB token-span extractor is ColBERT with the MaxSim axis flipped. MaxSim
  computes per-token query-document relevance, then sums over query tokens into
  one scalar for ranking. Keep the per-document-token max instead and you have
  token relevance for free, no fine-tuning. This is the default mechanism.

- A standard cross-encoder discards the token signal: only the [CLS] embedding
  feeds the relevance head, so the per-token attention the model computed is
  pooled away. Extracting it means head-selection over attention matrices or a
  backward pass for saliency — both work, but ColBERT exposes the same signal by
  design, which is why it wins.

- BIO token-classification head is the only mechanism here needing labeled span
  data (MultiSpanQA, BioASQ) and per-domain fine-tuning. Given ColBERT delivers
  token spans OOB, BIO is a footnote: reach for it only with domain span labels
  AND a need for sub-token precision ColBERT's threshold can't give. Do not
  default to it.

- Topical proximity ≠ task relevance. Embedding cosine captures how similar two
  topics are; it cannot model whether a sentence serves a task. When relevant
  sentences are one functional or causal hop from the query — present in the
  chunk but not topically identical — cosine under-scores them and over-scores
  topically similar but functionally irrelevant sentences. This is the core
  justification for asymmetric query-document interaction (cross-encoder,
  entailment, decoder).

- Entailment is the right mechanism when the relevance relationship is
  logical or causal, not when it is topical. The NLI framing ("does the query
  entail needing this sentence?") captures 1-degree functional hops that cosine
  and even cross-encoders can miss. The cost is loss of coreference — acceptable
  when sentences are self-contained.

- Extractive beats abstractive for faithfulness (verbatim) and speed (10x+).
  Reserve abstractive methods for summarization tasks, not context selection.

- The right output abstraction is integer sentence indices, not character
  offsets or span text. Indices require no counting, no string match, and are
  reliable under constrained decoding.

- Sentence is the right atom for most RAG content. Sub-sentence BIO token
  labeling is only warranted when individual sentences fuse relevant and
  irrelevant clauses — common in dense technical text. Benchmark retention
  ratio on actual corpus before committing; if kept sentences still carry
  substantial noise the atom is wrong.

- Sentence splitter quality is load-bearing. Spacy/NLTK break on code,
  citations, and technical prose. Validate on actual chunk content before
  committing to a splitter. A bad split caps the ceiling regardless of
  selector quality.

- Positional bias is real. Models favor sentences at fixed positions
  (typically early). Sentinel addresses this via shuffle during training.
  For decoder + indices, validate with sentences in shuffled order as a
  sanity check.

- Pruning is the distill step, not the retrieval step. It does not replace
  reranking or RRF — it runs after them on already-ranked chunks.

---

## Entities

- **ColBERT / ColBERTv2** — late-interaction retriever; MaxSim over per-token
  embeddings. Default token-span extractor via the document-token axis.
  Checkpoints: `answerdotai/answerai-colbert-small-v1`, `jinaai/jina-colbert-v2`,
  `colbert-ir/colbertv2.0`. Tooling: PyLate, RAGatouille.
- **NLI / Entailment models** — cross-encoder/nli-deberta-v3-large,
  facebook/bart-large-mnli. Use for 1-degree functional relevance tasks.
- **Provence** — NAVER Labs Europe, ICLR 2025. DeBERTa-v3 encoder labeler.
  HuggingFace: `naver-labs-europe/provence-reranker-debertav3-v1`.
- **Sentinel** — May 2025. Attention-probe sentence labeler, 0.5B proxy decoder.
- **RECOMP** — earlier extractive + abstractive pruners; fixed compression ratio
  is the key limitation superseded by Provence.
- **LLMLingua / LongLLMLingua** — token-level prompt compression, abstractive,
  higher hallucination surface than extractive approaches.
- **Context rot** — Chroma 2025 research. Systematic LLM degradation as input
  length grows. Primary motivation for this skill.
- **XProvence** — multilingual extension of Provence (Jan 2026).

---

## Open Questions

- At what chunk-length or corpus density does sentence-level pruning
  under-compress enough to warrant BIO token labeling?
- What sentence splitter handles code blocks, citations, and bulleted
  technical prose robustly? Candidate: custom regex over spacy.
- Optimal threshold for Provence on domain-specific corpora vs. the
  default MS Marco / NQ trained threshold.
- Concrete token reduction ratio on Jos's Graph-RAG corpus — benchmark
  not yet run.
- Whether the decoder + indices approach degrades on non-English or
  heavily domain-specific sentence lists.

---

## Dead Ends

### Embedding cosine as the selector

Cosine similarity measures symmetric topical proximity in embedding space — it
answers "how similar are these topics", not "does this sentence serve this task".
Relevance is asymmetric and functional; cosine is neither.

The failure mode: a query about "preparing for surgery" will score sentences
about incision techniques and suturing highly (same medical domain cluster)
while potentially under-scoring a sentence about sterilization — which is one
functional hop away and may sit in a different embedding cluster, but is exactly
what the task requires. Domain bleed compounds this: everything in a tightly
clustered corpus scores similarly high regardless of actual relevance.

Use embedding cosine as a **baseline benchmark only** — to measure how much the
chosen mechanism improves over a naive floor. Never as the production selector
when functional or causal 1-degree relevance is in scope.

### Pruning at write time
Query is unknown. Lossy. Irreversible. Violates reversibility contract.
Write full trace; prune only at recall.

### Character or token offset output from decoder
Requires the model to count precisely. Fragile. Use integer sentence indices
or span text + string match instead.

### Fixed compression ratio
Assumes a known proportion of the chunk is relevant. Real contexts vary from
zero-relevant to fully-relevant. Adaptive threshold (Provence-style) is
the correct shape.

### Relevance-rank order output
Sorting kept sentences by their relevance score produces incoherent context.
Always re-sort by original source position before passing to generator.

---

## Applicability Envelope

**Works well when:**
- retrieved chunks contain topic-drift sentences mixed with relevant ones
- token budget pressure is real (agentic systems, long sessions, cost targets)
- faithfulness of context is load-bearing (no hallucination in prune step)
- a query is available at prune time (recall path, not write path)

**Fails or degrades when:**
- chunks are already tightly scoped (retrieval is already precise enough)
- sentences within a chunk are so interdependent that dropping any breaks
  coherence — consider full-chunk retrieval instead
- sentence splitter produces malformed units on the target corpus
- relevant sentences are functionally implied by the query but not topically
  similar — encoder labeler and cosine both degrade here; use entailment or
  decoder instead

**Environment assumptions:**
- a query exists at prune time
- source chunks are retained in the store (prune is non-destructive)
- a sentence splitter is available (spacy, NLTK, or custom)
- a small encoder or decoder model is accessible for the selector