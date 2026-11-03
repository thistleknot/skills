---
name: reduce_overlaps
description: Use when chunking long text (markdown notes, docs, transcripts) for training corpora, RAG, or context generation — derives chunk size from the document's OWN section statistics instead of a fixed token count, then removes the overlap it introduced so the concatenation reconstructs the source with no duplicated spans.
---

# reduce_overlaps — semantic chunking sized by the corpus, de-duplicated by construction

## When to use

Chunking long text where a **fixed token window** would cut mid-thought: skill notes, wiki pages,
documentation, transcripts. Use it when the text has **structural boundaries already in it**
(markdown headers, paragraph breaks) that a token counter is blind to.

**Do not reach for this first.** Measure whether chunking is needed at all — if the documents fit the
context window, chunking adds a failure surface and buys nothing. See *The gate* below.

## The gate — measure before chunking, against the window YOU ACTUALLY TRAIN AT

```
p50 / p95 / max document tokens, vs the training window
fraction of documents exceeding it
```

**If <5% exceed, do not chunk** — handle the outliers by exclusion or truncation and stop.

**Read the window out of the training config and cite the file:line.** Do not use the model's
architectural context length, and do not assume. Small models on constrained GPUs are trained far
below their context limit, and the gate inverts across that gap:

```
1,523 markdown skill notes, p50 1,098 tok / p95 1,785 / max 3,130   (real tokenizer)

  vs 2,048 (the model's architectural context)   0.1% exceed  ->  "do not chunk"    WRONG WINDOW
  vs   512 (entigraph_ab.py:64 BLOCK)          100.0% exceed  ->  CHUNK REQUIRED    the real config
```

Same corpus, opposite verdicts. The 2,048 figure appeared in no training script in that repo — it was
the architectural limit, quoted from memory. **A gate measured against a plausible-looking number
that nothing actually uses returns a confident wrong answer.**

**Count tokens with the real tokenizer, not a words x constant estimate.** The same measurement run
with a 1.35 tok/word rule of thumb gave p50 838 against a true 1,098 — the actual ratio was 1.77.
That is a 24% undercount, enough to move a fill rate or a budget decision, and it costs one
`AutoTokenizer.from_pretrained` to avoid.

Chunking has a second, independent use even when documents fit: **generating grounded context
passages** (a `context` field for QA data). That job sizes for the consumer's context field, which is
usually far smaller than the training window. Size for the consumer, not for the model.

## The method

Derive every parameter from the document's own distribution. **No magic constants.**

```
1. SPLIT into sections on markdown headers  (^#{1,6}\s)
2. COUNT paragraphs per section = blank-line-separated blocks; EXCLUDE zero-paragraph sections
   (bare headers carry no content and would drag the median down)
3. Box-Cox transform the paragraph counts: bc_data, λ = boxcox(counts)
   m   = median(bc_data)                         <- robust centre in normalized space
   d   = MAD(bc_data)                            <- robust spread in normalized space
   hi  = m + 2*d                                 <- upper threshold in Box-Cox space
   Invert hi to natural scale for the split gate; invert m for the merge/stride target.
4. MERGE consecutive sections with < m paragraphs, accumulating until they reach m
5. SPLIT sections with > hi paragraphs into windows of m paragraphs, stepping by (m - d)
   -> an overlap of d paragraphs between consecutive windows
6. DE-OVERLAP the resulting sequence (below), so the overlap that preserved continuity at the
   boundary does not become duplicated training text
```

Median and MAD rather than mean and sd because section sizes are **right-skewed** — one 41k-word
appendix moves a mean and does not move a median. Apply **Box-Cox** (`scipy.stats.boxcox`) to the
paragraph counts before computing median and MAD; Box-Cox finds the optimal normalizing power λ
automatically (λ=0 is log, λ=0.5 is sqrt, etc.) rather than hardcoding a log assumption. Compute
`m` and `d` in Box-Cox space, then invert to get the natural-scale thresholds. Overlap of exactly `d`
(one robust unit of spread in the transformed space) keeps a thought that straddles a boundary intact
in at least one chunk.

## De-overlapping

Trim the longest **suffix of chunk i that is a prefix of chunk i+1**:

```python
def find_overlap(s1, s2):
    """Longest suffix of s1 that matches a prefix of s2."""
    for i in range(min(len(s1), len(s2)), 0, -1):
        if s1[-i:] == s2[:i]:
            return s1[-i:]
    return ""


def de_overlap_strings(strings):
    """Remove overlapping suffixes from consecutive strings."""
    result = []
    for i in range(len(strings) - 1):
        s1, s2 = strings[i], strings[i + 1]
        overlap = find_overlap(s1, s2)
        if overlap:
            s1 = s1[:-len(overlap)]
        result.append(s1)
    result.append(strings[-1])          # last chunk is kept whole
    return result
```

**Exact string matching, not fuzzy.** `difflib.SequenceMatcher` is the natural reach here and is the
wrong tool: overlap introduced by a known stride is character-identical, so exact matching is both
correct and O(n) per pair against SequenceMatcher's O(n²) — and fuzzy matching would silently trim
text that merely *resembles* the neighbour.

**Invariant that makes this checkable:** `"".join(de_overlap_strings(chunks))` reconstructs the source
exactly when the chunks tile it. Assert that; a chunker that loses or duplicates text fails loudly.

### Never run de-overlap on input that is already disjoint

Exact matching does not make the trim safe — it makes it *precise*, which is not the same thing. Two
adjacent-but-disjoint chunks can share a real suffix/prefix **by coincidence**, and structured text is
full of short repeated tokens that collide: a code fence closing one chunk and opening the next, a
`---` rule, a repeated table delimiter or bullet marker.

Measured: over 15,871 atoms built at stride = `m` (disjoint by construction), de-overlap removed
**310 characters.** Small, and every one of them data loss — there was no duplication to remove.

**So gate it on provenance, not on the match.** Run de-overlap only where a known stride actually
introduced overlap. Where chunks are disjoint by construction, verify with **conservation** instead:

```
paragraphs_in_atoms == paragraphs_in_source          # exactly once each, no loss, no duplication
```

Prefer conservation to reconstruction-equality whenever the chunker discards structural markup
(header text consumed by the split regex, for instance) — reconstruction then fails for a reason that
has nothing to do with correctness, and an assert that cries wolf gets deleted.

```
string  = 'abcdefghijklmnopqrstuvwxyz'                 26
chunks  = [s[0:13], s[8:15], s[14:]]                   13 + 7 + 12 = 32 chars, 6 overlapping
reduced = ['abcdefgh', 'ijklmn', 'opqrstuvwxyz']       8 + 6 + 12 = 26  -> exact reconstruction
```

## Two overlaps, two objects — the catch-22 and its resolution

The obvious objection: *why overlap chunks, de-overlap them, then reassemble overlapping training
records?* It reads as undoing your own work. It isn't, because **the two overlaps act on different
objects**:

| step | object | overlap means | knob |
|---|---|---|---|
| chunk (+ de-overlap only if a stride introduced overlap) | **atoms** — canonical units that tile the source | a span stored twice | correctness: assert conservation |
| pack into records | **records** — what the trainer consumes | a span *seen* twice | **exposure count** (a dose you want) |

Dedup guarantees each span exists exactly once in the canonical set. Stride then decides how many
times training sees it. Duplication in the corpus is a defect; repetition during training is a
hyperparameter.

**They annihilate only if you conflate them.** Windowing atoms at size `m` with stride `m - d` and
then de-overlapping trims exactly the shared span, collapsing every window back to one unit — the
overlap step and the dedup step cancel. Measured: at `m=2, d=1` the split branch degenerated to
"emit each paragraph alone," producing 38.8% single-paragraph chunks and a 10.5% spike under 5 words.

**Rules that keep them separate:**

1. **Build atoms with NO overlap** (stride = `m`), then **do not run de-overlap on them at all** —
   they are disjoint by construction, so every trim is loss (see above). Verify with conservation.
2. **Pack records to the TOKEN BUDGET**, greedily accumulating atoms until the window is full. Not to
   a paragraph count — paragraph count is how atoms were built, not how records are sized.
3. **Stride the record window in atoms**, and treat that stride as the exposure knob.

Packing to the budget also removes the need to equalise record lengths by sub-splitting. A ragged
section that would need special-casing under a paragraph-count scheme just gets absorbed by greedy
accumulation, which self-balances: measured 87% median fill, p25 393 / p95 508 against a 512 budget.

```
15,871 atoms (p50 95 tok)  ->  512-tok records, stride 1:
   10,954 records   p50 445 tok   87% fill   p50 4 atoms/record   2.94x exposure
   coverage 1,523/1,523 skills complete
```

Pick stride from an exposure measurement or the literature prior, never from chunking aesthetics.

**Assert coverage, not just counts.** A packer that advances its window can silently drop the tail of
a document; check that the union of packed indices equals every atom, per document.

**One atom may exceed the budget** (a single very long paragraph). Emit it alone and let the trainer
truncate — splitting mid-paragraph to satisfy the budget destroys the semantic boundary the whole
method exists to preserve. Report the count; 1 of 15,871 here.

## Downstream: length-quartile blocks and derived batch size

The records this produces carry a token count, and that column is what makes batching derivable
instead of guessed. Padding every batch to a global maximum wastes compute in proportion to the
length spread — measured p25 393 / p95 508 against a 512 budget, so a fixed batch sized for the top
pads the bottom quartile by ~23%.

```
1. PARTITION records into 4 blocks by token length, cuts from median/MAD
2. DERIVE batch size per block:  batch_b = vram_budget / max_tokens(block_b)
   -> short-record blocks get LARGER batches; batch size stops being a constant
3. INNER batch-epoch: resample each block WITHOUT replacement, so every record is seen once per outer
   epoch and none is over-exposed relative to its block-mates
4. ROTATE blocks between inner epochs, so the optimiser does not see all short records then all long
```

**The only thing that differs between blocks is `n_records`** — tokens per step stays roughly
constant, which keeps the gradient-noise scale from co-varying with document length.

**Do not tune this against the packing stride.** Rotation changes the ORDER records are seen; stride
changes HOW MANY TIMES. Treating them as one knob recreates the atoms/records conflation above at the
scheduler layer.

## Contract

- **Require** — text with detectable section structure; ≥1 section with ≥1 paragraph; a training
  window read from the config, not assumed.
- **Guarantee** — atoms in source order, disjoint, covering every source paragraph exactly once;
  records built only from atoms, each within the token budget unless a single atom exceeds it.
- **Maintain** — every parameter traces to a measured quantile of the input, never a constant.
- **Assert** — paragraph conservation (`atoms_in == source_in`); per-document coverage (the union of
  packed atom indices is every atom); zero-paragraph sections excluded before the median is taken;
  `de_overlap_strings` reconstructs the 26-char tiling example exactly.

## Report

Always emit the derived parameters and a **histogram**, overlaying atoms and packed records, so the
operator sees the shape rather than trusting a summary statistic:

```
gate       document tokens p50/p95/max, % exceeding the window, and the config file:line it came from
sections   N,  paragraphs/section median m, MAD d, upper m+2d
atoms      N, tokens p25/p50/p75/p95/max, paragraph conservation X/X
records    N, tokens p25/p50/p75/p95, % fill, atoms/record, EXPOSURE multiplier, coverage X/X docs
```

## Failure modes

- **Chunking a corpus that did not need it** — the most common. Run the gate first.
- **Gating against the architectural context length** instead of the configured training window —
  inverts the verdict outright. Cite the file:line.
- **Estimating tokens as words x a constant** — measured 1.35 vs a true 1.77, a 24% undercount.
- **Running de-overlap on disjoint input** — trims coincidental collisions; that is data loss.
- **Including zero-paragraph sections** in the median — bare headers pull `m` toward 1 and shatter the
  corpus into fragments.
- **Mean/sd instead of median/MAD** — one appendix sets the threshold for every other document.
- **Fuzzy overlap matching** — trims text that resembles the neighbour but was not duplicated.
- **Conflating corpus duplication with training repetition** — the first is a defect to remove, the
  second a dose to choose. Sizing them with one parameter makes them cancel.
- **Sizing chunks for the model's window when the consumer is a context field** — produces passages
  an order of magnitude larger than the thing they must match.
