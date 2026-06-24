---
name: concept-segmentation
description: >
  Segment a chunked document into concept -> chunk_id ranges using a SQLite-backed
  read-and-extend loop, then optionally prune each concept's evidence to verbatim
  spans. Use when identifying where concepts begin and end across heuristic
  (Docling) section boundaries, handling overlapping concepts, and resuming after
  failure. Storage is SQLite3 + JSON1 holding the LangChain Document format — id /
  metadata range filtering only, no embeddings. The relevance filter (ColBERT span
  extraction) is flag-gated and OFF by default. Cross-reference:
  `extractive-context-pruning` for the optional span primitive;
  `book-concept-distillation` for the tier context.
status: active
last_validated: 2026-06-15
validation_method: design synthesis session
---

# Concept Segmentation

## Question

Given a chunked document where concepts overlap and section boundaries are a
heuristic (not gospel), how do you find each concept's chunk-id extent — cheaply,
resumably, without trusting the section headers — and feed verbatim evidence to
distillation?

---

## Why This Exists

Three facts about the data force this design:

1. A chunk may attest multiple concepts at once. Overlap is normal, so the output
   is a one-to-many map (chunk_id -> concepts), which a single-boundary binary
   search cannot represent. Segmentation, not boundary search.
2. Docling section boundaries are a heuristic. A concept can cross a section seam.
   So the section is a *prior* on where to read, never a hard wall.
3. Sections *generally* contain whole concepts. So the loop should confirm the
   common (section-contained) case cheaply and only pay to extend on the
   exception.

The earlier instinct — binary doubling/halving or golden-section (phi) search —
was the wrong frame. Doubling/halving oscillate (n x 2 x 1/2 = n). Phi and 1/phi
also oscillate (phi x 1/phi = 1). Golden-section search assumes a unimodal single
boundary, which overlapping concepts are not. The resolved design uses an
asymmetric resize pair and a measured structural unit instead.

---

## The Scale Unit: M (prior action)

Computed once at ingest, carried as document metadata. TRIZ prior-action: measure
the document's natural structural cadence up front so the loop never rediscovers
scale by trial at runtime.

- **M = median chunk-span between section boundaries.** Derived from the median
  count of double-newline (paragraph) breaks between Docling sections — a
  non-parametric statistic that drowns out per-section formatting noise and
  recovers the document's typical inter-section spacing. (This same median-spacing
  signal works as a standalone natural-chunk-boundary heuristic; here it sets the
  loop's unit.)
- **MAD = median absolute deviation of those spans.** Sets robust tolerances:
  merge runt sections whose span < M - k*MAD so they don't distort M, and set the
  breaker bound as M-multiples (or M + 3*MAD if section spans are skewed).

Median sets the unit; MAD sets the tolerances. Both computed once, upfront, from
the raw document — not per concept at runtime.

---

## Storage and Read Unit

**SQLite3 + JSON1, no Chroma, no embeddings.** The loop's only access pattern is
"chunks in this chunk_index range for this document" — a `WHERE chunk_index
BETWEEN ? AND ?` over a covering index. The full LangChain Document
(`page_content`, `metadata`, `type`) from the Docling ingest is stored verbatim
in a JSON column; `chunk_index` and `header_path` are promoted to indexed columns.
Semantic retrieval (Chroma, embeddings) is a FUTURE stage that reads the same rows
and embeds then — nothing in this loop needs it.

**The read unit is a MAD-aggregated section, merged at ingest — not in the loop.**
Runt sections (span < M - k*MAD) are folded into their predecessor by
`structural_cadence` during ingest, so the smallest unit the loop ever reads
already clears the floor. The loop does not aggregate sections; it reads whatever
the merged sections are. The common case is "read one natural-sized section,
concepts close, done."

---

## Images: concept-pull, not image-push (how humans read)

A human does not bind a figure to text at the moment they see it. They glance at
the figure, hold it unresolved, keep reading, and it snaps into place when the
text builds the concept it illustrates. The association is made FROM THE CONCEPT
SIDE, at comprehension time — pulled by the concept once it exists, not pushed
from the image's location. The segmentation pipeline mirrors this exactly, and it
is why the earlier image-placement machinery (label matching, +/-3M windows,
relevant_sections precompute) was the wrong direction — it tried to resolve at
ingest what is correctly deferred to distillation.

Three lanes, each doing what the human does at that stage, each on the right model:

- **Ingest = the glance.** qwen3-vl tags each image (concept-blind: "what is
  this"). Stored as an UNRESOLVED candidate: `header_path` (Docling's
  decide-and-done placement — a coordinate, NOT a semantic guarantee),
  `vlm_tags`, `caption`, `b64`. No concept association yet.
- **Segmentation = the reading.** qwen3.5 (text decoder). Text-only, image-free.
  The loop never sees a figure.
- **Distill = the snap.** When a concept closes, it reaches back for figures that
  correlate. Wide cheap recall (candidate net), then qwen3-vl transcribes each
  candidate GROUNDED in the concept (concept-aware: "what does this show *about
  this concept*"). The transcription — TEXT — joins the evidence. The image
  itself never reaches the distiller.

**Model routing — each model does only what it is best at:**

- **qwen3-vl** is the only model that touches an image, and its output is always
  TEXT. Vision-language transcription, ingest tags + distill grounded
  transcription. Weak-at-text is fine — it is describing a picture.
- **qwen3.5** is the text decoder. Segmentation verdicts and distillation. Never
  touches a pixel. Full text fidelity is preserved because the strong text model
  never degrades to a weaker multimodal one for reasoning.

**Skills are text-only, always.** No base64, no image refs, no figure embeds in
the distilled SKILL.md. The image's *information* survives as the qwen3-vl
transcription (prose evidence the distiller folds in as words); the image itself
does not. The b64 stays in the SQLite store for the future retrieval stage.

"Correlates" is precise: the gate judges whether the figure *supports* the
concept (functional), not whether it is *near* or *similar* to it (topical). The
transcription is grounded — it receives image + concept + section text — so it
reads as evidence ("the chart showing X beat Y on metric Z, supporting the
claim...") not an ungrounded caption ("a bar chart"). An ungrounded caption is
useless to distillation; a grounded transcription is source material.

```
# At concept close (DISTILL lane). Relevance and transcription are ONE qwen3-vl
# call — judging relevance already requires reading the image, so emit the
# grounded text in the same pass.
def pull_image_transcriptions(db, doc_name, concept, concept_chunk_ids,
                              concept_evidence_text, M, vlm):
    """
    Concept reaches back for figures that support it, qwen3-vl transcribes the
    relevant ones to grounded TEXT. Pull-from-concept; output is text only.

    Recall net (wide, cheap): candidate images within ~3*M of the concept range.
        Generous — a missed candidate is lost silently, a wrong one costs one VLM
        call and is dropped. The 3*M bound is a RECALL filter, not a placement
        decision.
    Transcription gate (qwen3-vl, grounded): per candidate, one pass returns
        {supports, transcription}. supports=False -> dropped. supports=True ->
        grounded supporting text joins the evidence.
    """
    lo = min(concept_chunk_ids) - 3 * M
    hi = max(concept_chunk_ids) + 3 * M
    candidates = get_images_in_range(db, doc_name, lo, hi)

    transcriptions = []
    for img in candidates:
        result = vlm.transcribe(                       # ImageTranscription
            image_b64=img.b64,
            concept=concept,
            section_text=concept_evidence_text,        # grounding context
        )
        if result.supports and result.transcription:
            transcriptions.append(result.transcription)  # TEXT, not the image
    return transcriptions   # [] -> concept distills text-only, fine
```

The recall net errs wide; the qwen3-vl gate is the precision step AND the
transcriber in one call. Runs in the distill lane, never in the hot segmentation
loop.

### Two VLM calls, by purpose — not two quality levels of one

The ingest tag call and the distill transcription call answer DIFFERENT
questions. Keeping both is correct architecture, not tolerated redundancy.

- **Ingest tag call** — "what is in this image." Concept-blind, image-only,
  cheap. Its job is a RECALL signal for the candidate net, not evidence. It needs
  no text grounding because deciding "this figure might matter to a training
  concept" only needs "flowchart, training loop, gradient". This is the index
  breadcrumb.
- **Distill transcription call** — "what does this image show ABOUT this
  concept." Concept-aware, grounded, the evidence that lands in the skill. The
  call that matters.

The grounded call CANNOT move to ingest. Grounding needs a concept, and at ingest
no concept exists yet (concept-pull happens later, at distill). So ingest can only
ever do image-only transcription; text-grounding waits for distill, where the
concept supplies the grounding. The earlier "+/-1 page" / "+/-3 median sections,
transcribe upfront" instinct was trying to do grounded-upfront-cheap, which is
impossible — you cannot ground without a concept, and committing to an arbitrary
±window IS the page-pairing problem the concept-pull architecture exists to avoid.

Gating: the grounded transcription is already filtered by two signals you have —
the 3*M positional net (a free SQL range query) AND the ingest tags. A figure gets
the expensive grounded call only if it is positionally near a closed concept and
its tags plausibly relate. That is the recall-cheap / precision-expensive
structure; no third filter is needed.

**ColBERT does not gate images.** ColBERT MaxSim is over text token embeddings —
text on both sides. Multimodal late-interaction (ColPali, ColQwen) embeds image
patches for visual page retrieval; it does not judge "supports this concept" and
emits no text. Wrong tool, new model, new lane, no payoff. The 3*M net + tags are
the gate.

### Ingest richness: tags vs image-only holistic (measure, do not reason)

Ingest emits EITHER bare tags OR an image-only holistic description (richer index
text, better recall). Holistic costs more per figure at ingest and is wasted on
figures that never become evidence. The trade is decided by one corpus fact: what
fraction of figures ever attach to a concept. Many load-bearing figures -> holistic
pays off; few -> tags, transcribe on demand.

MVP: ship tags + on-demand grounded transcription. Measure the attach rate the MVP
produces. Switch ingest to holistic only if the number is high. Decide by the
measurement, not by reasoning now — the lane is swappable without touching the
loop.

---

## The Loop: read, extend, snap, trim

The window grows in **M-units** (coarse, leaps by natural sections) with a
**ratio trim** on top (fine, +50% reach / -50% on overshoot). The two ratios are
deliberately NOT inverses: x1.5 then x0.5 = x0.75, so the window walks toward the
boundary instead of bouncing back to start. Retreat to a confirmed id is the fast
path; ratio trim is the fallback when the LLM won't commit a coordinate.

```
# Precomputed at ingest, in the documents table:
#   M   = median chunk-span between sections
#   MAD = median absolute deviation of those spans

def segment_document(doc_name, db, relevance_filter=False):
    """
    Walk the document, emitting closed concepts with their chunk_id extents and
    prepared evidence. Overlap is native: a chunk_id may appear under multiple
    concepts.

    Require: SQLite store populated by segmentation_store.ingest (chunks +
             documents rows); extract_spans available iff relevance_filter=True.
    Guarantee: every closed concept has a chunk_id range and a close_flag
               (closed_confirmed | closed_forced). No concept silently dropped.
    """
    cad = get_cadence(db, doc_name)           # {M, MAD, total_chunks, ...}
    M, last_chunk = cad["M"], cad["total_chunks"] - 1

    base, reach = resume_or_init(db, doc_name, M)   # checkpoint-aware
    open_concepts = {}                              # concept -> start_id
    closed_out = []

    while base < last_chunk:
        window_end = min(base + ceil(reach), last_chunk)
        window = get_chunk_range(db, doc_name, base, window_end)  # SQLite range read

        # qwen3.5 segments the window. "still open" is the DEFAULT;
        # only an explicit closed_at chunk_id closes a concept.
        verdict = llm.segment(
            chunks=window,
            open_concepts=open_concepts,
            instruction=(
                "List every concept present. For each, give the chunk_id range(s) "
                "that attest it — ranges MAY overlap. Emit closed_at=<chunk_id> "
                "only if the concept clearly ends within this window; otherwise "
                "leave it open. Do not guess an end."
            ),
        )

        register_new_concepts(verdict, open_concepts)
        closed = [c for c in verdict if c.closed_at is not None]

        if closed:
            base = max(c.closed_at for c in closed)      # snap to confirmed id
            reach = max(M, reach * 0.5)                  # overshot -> tighten
            for c in closed:
                evidence = prepare_evidence(db, doc_name, c.name, c.chunk_ids,
                                            relevance_filter)
                closed_out.append(emit(c, evidence, flag="closed_confirmed"))
                open_concepts.pop(c.name, None)
        else:
            reach = reach * 1.5                          # still open -> reach further

        # Circuit breaker: open concept spanning > 3 natural sections
        for name, start_id in list(open_concepts.items()):
            if (window_end - start_id) > 3 * M:          # or M + 3*MAD robustly
                ids = chunk_ids_for(name, start_id, window_end)
                evidence = prepare_evidence(db, doc_name, name, ids, relevance_filter)
                closed_out.append(emit_forced(name, start_id, window_end,
                                              evidence, flag="closed_forced"))
                open_concepts.pop(name)

        checkpoint(db, doc_name, base, open_concepts, reach)   # resumable

    # Book end: force-close anything still open (it ends at the document end)
    for name, start_id in open_concepts.items():
        ids = chunk_ids_for(name, start_id, last_chunk)
        evidence = prepare_evidence(db, doc_name, name, ids, relevance_filter)
        closed_out.append(emit_forced(name, start_id, last_chunk, evidence,
                                      flag="closed_forced"))

    return closed_out


# ── The flag-gated seam: full text (tested) vs pruned spans (nervous feature) ──

def prepare_evidence(db, doc_name, concept, chunk_ids, relevance_filter):
    """
    Turn a concept's chunk_ids into the evidence that goes to distillation.

    relevance_filter=False (MVP DEFAULT, fully tested path):
        return the full joined text of the concept's chunks. No ColBERT, nothing
        untested in the path.
    relevance_filter=True (flag-gated, validate before trusting):
        run extract_spans(concept, joined) and return only verbatim spans —
        the 5-10x token-budget win, quarantined behind the flag.

    The loop is identical either way; only this function's return changes.
    """
    rows = get_chunk_range(db, doc_name, min(chunk_ids), max(chunk_ids))
    rows = [r for r in rows if r["metadata"]["chunk_index"] in set(chunk_ids)]
    joined = "\n".join(r["page_content"] for r in rows)   # source order

    if not relevance_filter:
        return {"mode": "full_text", "text": joined}

    spans = extract_spans(query=concept, text=joined)     # ColBERT MaxSim
    return {"mode": "spans", "spans": spans}
```

---

## Why Each Piece Is There

- **M-unit growth, not chunk-ratio growth.** A long concept crossing several
  sections escalates as M, 1.5M, 2.25M... — it leaps by natural sections, so
  "cross several sections" takes a few probes, not dozens. The ratio is fine
  trim around a unit that is already the right order of magnitude. Prior action
  (measuring M at ingest) did the scale-finding once instead of per concept.

- **x1.5 grow / x0.5 trim, deliberately non-inverse.** Avoids the oscillation
  that doubling/halving and phi/(1/phi) both suffer. The walk is biased toward
  contraction (shrinks faster than it grows), which is correct given sections
  generally contain the concept — tighten aggressively, reach cautiously.

- **Retreat is a confirmed id, never a ratio.** When the LLM emits closed_at,
  snap base to it and skip the trim. The ratio trim is the fallback for when the
  model will only say "still in here" without a coordinate.

- **Breaker in the same unit as growth.** "3 x M" is literally three natural
  sections. Growth and kill-switch speak one language (M), removing the unit
  mismatch that earlier designs had (chunk-ratio growth vs section-median
  breaker).

- **Forced close is FLAGGED, never silent.** closed_forced=true tells the
  downstream dedupe tier this boundary was guessed, not confirmed. If the concept
  reappears in a later window it merges there — the breaker stops runaway compute
  without corrupting output. Silent force-close is the false-close failure that
  permanently fragments a real long concept.

- **"Still open" is the default.** Only an explicit chunk_id closes a concept.
  An uncertain model widens (costs a probe) rather than false-closes (fragments
  a skill). Over-widen is cheap; false-close is expensive.

---

## MVP Cut

Build only `segment_document` + `prepare_evidence`, reading from the SQLite store
(`segmentation_store.py`). Stop at closed concepts with evidence checkpointed.
Do NOT build distillation, cross-book matching, or thresholds — those are
undecided and pull the agent toward placeholder skills.

**With `relevance_filter=False` (the default), the loop has ZERO untested
components:** SQLite range reads, qwen3.5 segmentation, and full-text-to-evidence
are all known-good. The one new-and-unvalidated piece — ColBERT span extraction —
is quarantined behind the flag. Ship the loop now; turn on relevance filtering
once it is validated on real chunks, without touching loop logic.

- Storage: SQLite3 + JSON1, LangChain Document format, no embeddings.
- One scale constant: M (plus MAD for tolerances).
- One growth ratio pair: x1.5 / x0.5.
- One breaker: 3 x M, flagged.
- Two clamps: book end, and reach floor at M.
- Relevance filter: OFF by default (full text), flag-gated ON (spans).
- Checkpoint (doc_name, base, open_concepts, reach) to SQLite after each window.
- Validate on ONE window first (break after one), confirm overlap and provenance,
  then scale 1 -> 10 -> full document.

---

## Lessons

- Overlap forces a one-to-many map; binary boundary search cannot express it.
  Segment, do not search.

- Heuristic section boundaries forbid treating the section as a hard wall. The
  section is a read-window prior and a convergence aid, never a commitment.
  Concept identity completes above section scope.

- Using phi does NOT obligate using 1/phi. A growth ratio is one number. The
  reciprocal only earns its place in golden-section *search* (bracket reuse via
  phi^2 = phi+1), which this loop is not running. When the LLM emits a confirmed
  id, bracketing is obsolete.

- Choose a non-inverse resize pair on purpose. x2/÷2 and phi/(1/phi) return to
  start. x1.5/x0.5 = x0.75 walks. The asymmetry IS the feature.

- Measure scale once at ingest (M, MAD), non-parametrically. Runtime rediscovery
  of scale per concept is wasted compute and the source of slow escalation.

- Express the breaker in the growth unit. One currency (M) for reach and
  kill-switch removes unit-mismatch bugs.

- Overlap is free at extraction: same chunk, different concept-query, different
  spans. Concepts-first then N independent ColBERT passes is the correct order
  and parallelizes. (Only when relevance_filter is ON; OFF passes full text.)

- Quarantine the untested feature behind a flag, default OFF. The loop ships with
  zero unvalidated components; relevance filtering (the one feature never run)
  turns on later without touching loop logic. The MVP that works does not depend
  on the feature you are nervous about.

- SQLite + JSON1 beats Chroma when the access pattern is pure id/metadata range.
  No embedding cost, faster range reads, one fewer dependency. Embeddings are a
  future retrieval stage reading the same rows, not a loop requirement.

- Images resolve by concept-pull, not image-push. A figure is held unresolved at
  ingest (the glance) and snapped to a concept at distill when the concept reaches
  back for it (comprehension). Trying to bind image->concept at ingest is the
  wrong direction and was the source of all the placement-search sprawl (labels,
  +/-3M windows, relevant_sections). Defer to distill, pull from the concept.

- Image attachment is correlation transcribed to text, not similarity and not
  pixels. qwen3-vl judges whether a figure *supports* the concept (functional)
  and, in the same call, transcribes it to grounded supporting TEXT. The distiller
  (qwen3.5) reads that text, never the image. Skills stay text-only; the b64
  stays in the store.

- Route by what each model is best at. qwen3-vl is the ONLY model that touches a
  pixel and it always emits text. qwen3.5 (text decoder) does segmentation and
  distillation and never sees an image, so strong-text fidelity is never traded
  away to a weaker multimodal model.

- Two VLM calls answer different questions, not two quality tiers of one. Ingest
  tag = "what is this" (recall signal, image-only, cheap). Distill transcription =
  "what does this show about this concept" (evidence, grounded). The grounded call
  cannot move to ingest because grounding needs a concept and ingest has none —
  concept-pull is later, by definition.

- Grounded-upfront-cheap is impossible. Any attempt to ground a transcription at
  ingest must commit to an arbitrary ±window (pages or median sections) — which IS
  the page-pairing problem concept-pull exists to defer. Ingest does image-only;
  grounding waits for the concept at distill.

- Recall-wide candidate net, precision-sharp qwen3-vl gate. The 3*M image bound
  is a recall filter (err wide, cheap drops), never a placement decision. The
  gate's transcription IS the precision step — relevance and transcription are
  one VLM pass.

- Docling header_path is a storage coordinate, not semantic gospel. It was a
  decide-and-done ingest default. The distill lane does not inherit it as a
  relevance claim; it re-judges relevance with the VLM.

---

## Entities

- **SQLite3 + JSON1** — the store. LangChain Document per row, chunk_index and
  header_path promoted to indexed columns, full doc in a JSON column. Range
  filtering only, no embeddings. See `segmentation_store.py`.
- **M / MAD** — median chunk-span between sections + its MAD, computed at ingest
  by `structural_cadence.py` from double-newline cadence, stored in the documents
  table. Runt sections merged up at ingest.
- **extract_spans** — the ColBERT MaxSim primitive from
  `extractive-context-pruning`. Used only when relevance_filter is ON. Signature:
  `extract_spans(query, text) -> [(start, end, text)]`.
- **qwen3.5** — segmentation / closing-verdict model via Ollama.
- **Docling HybridChunker** — produces the chunks + header_path; M computation may
  be folded into this ingest stage since section headers alone are unreliable for
  short sections.

---

## Open Questions

- The k in the runt-section merge bound (M - k*MAD) — start k=1, tune on a real
  document.
- Breaker multiplier: fixed 3*M vs robust M + 3*MAD when section spans are skewed.
- Does any single Docling section exceed the segmentation model's clean context?
  If not, the within-section oversize branch is dead code — confirm max
  single-section token sum on the test corpus.
- llm.segment reliability on emitting overlapping ranges with stable ids —
  validate on one multi-concept section before scaling.

---

## Dead Ends

### Binary doubling/halving and phi/(1/phi) for window resize
Both are inverse pairs -> oscillation, cannot settle on arbitrary counts. Use a
non-inverse pair (x1.5 / x0.5).

### Golden-section search to locate the boundary
Assumes unimodal single boundary; overlapping concepts are neither. Only valid if
the LLM gives open/closed with no coordinate — which it does not here, since it
emits closed_at ids.

### Newline / double-newline count as the breaker
Raw counts measure formatting, not conceptual extent. Use chunk-span against the
median structural unit M. (The MEDIAN of double-newline spacing across sections is
fine as the ingest-time scale statistic; per-window raw counts are not.)

### Silent forced close
Permanently fragments a genuine long concept. Always flag closed_forced so the
dedupe tier can re-merge.

### Section header as a hard concept boundary
Docling headers are heuristic and unreliable for short sections. Prior instinct to
trust them alone is the thing this loop routes around.

### Chroma / embeddings for the segmentation loop
The loop's access pattern is pure id/metadata range filtering. Standing up a
vector store and deriving embeddings for it is cost and a dependency with no
payoff here. SQLite3 + JSON1 does the range reads faster. Embeddings belong to a
later retrieval stage that reads the same rows.

### Image-push placement (resolve image->concept at ingest)
Label matching, +/-3M centered windows, 7-section spans, relevant_sections
precompute — all variants of pushing the image to its concept at ingest. Wrong
direction. Images float by layout, references bind by meaning, and the relevance
standard differs between the ingest lane (any defensible placement) and the
distill lane (must actually support the concept). Resolve by concept-pull at
distill instead.

### Tightening the image candidate net for precision
The 3*M net is recall-oriented; a missed image is lost silently. Precision is the
VLM gate's job. Tightening the net to exclude wrong images also excludes floated
figures you want. Err wide, reject in the gate.

### Caption/embedding similarity for image relevance
Topical proximity, not functional support. Same failure as cosine for text spans.
Use the VLM correlation judgment.

### ColBERT (or multimodal late-interaction) to gate images
ColBERT MaxSim is text-on-both-sides. ColPali/ColQwen retrieve page images by
visual similarity and emit no text relevance judgment. Neither answers "does this
figure support this concept." The gate is the 3*M positional net + ingest tags,
then the qwen3-vl grounded transcription. No new model.

### Grounded image transcription at ingest
Grounding needs a concept; ingest has none (concept-pull is at distill). Doing it
at ingest forces an arbitrary ±window commitment — the page-pairing problem the
architecture defers on purpose. Ingest = image-only (tags or holistic);
grounding = distill.

---

## Applicability Envelope

**Works well when:**
- concepts overlap within sections (one-to-many chunk->concept)
- section boundaries are heuristic and a concept may cross a seam
- sections generally contain whole concepts (the cheap common case)
- the store supports exact id/metadata range filtering (Chroma, pgvector)

**Fails or degrades when:**
- a single section exceeds the model's clean context (needs an intra-section
  split branch — dead code unless confirmed present)
- llm.segment cannot emit stable overlapping ranges (validate first)
- the document has no detectable structural cadence (M undefined) — fall back to
  fixed-chunk windows

**Environment assumptions:**
- SQLite store populated by `segmentation_store.ingest` from the Docling JSONL
  (chunks + documents rows; M, MAD present)
- extract_spans available from `extractive-context-pruning` IF relevance_filter ON
- the same SQLite connection carries the loop checkpoint for resume
