---
name: bpe-bm25
status: active
last_validated: 2026-10-04
description: >
  DEFAULT FOR TERM SALIENCE (operator 2026-10-04): a term's salience is its share of the
  sparsevec INNER PRODUCT between a chunk and its sparsevec neighbours, over a BPE-tokenised
  vocabulary hosted in Postgres -- not a BM25 score; see "Term salience" below. Also: shrink
  the lexical vocabulary behind a pgvector sparsevec BM25 index so HNSW can
  build a connected graph at scale, and measure the cost on recall@50 against gold
  derived from the corpus itself -- no hand-picked constants, no LLM judge. Use when
  a sparse index has millions of distinct terms and HNSW has been forced to a low m /
  ef_construction, and you want to reduce the candidate terms (BPE over a
  BM25-selected vocabulary) with the vocabulary size chosen by measurement. Trigger
  on "sparsevec vocabulary too large", "HNSW m=4", "reduce candidate terms", "BPE
  for lexical search", "raw BM25 vs sparsevec vs BPE", or any plan to pick a vocab
  size by hand. Companion to `stat-partitioning` (median/MAD bands) and
  `reduce_overlaps` (chunk sizing).
---

# bpe-bm25 — shrink the vocabulary behind a sparsevec BM25 index

## Intent

The target is a `sparsevec` BM25 index searched with HNSW. At scale the vocabulary
explodes (millions of distinct terms over millions of records), rows share few
nonzeros, and HNSW has to run at a low `m` / `ef_construction` to build at all. The
bet: **fewer, more shared candidate terms give rows more overlap, and so a graph HNSW
can actually walk.** Reduce the terms, then prove the recall cost on the index you
will deploy.

## The comparison that decides it — one number per arm

```
arm                                   recall@50
raw BM25, exact scan                    R0
raw BM25 as sparsevec, HNSW             R1
reduced vocabulary as sparsevec, HNSW   R2
```

- `R1 - R0` = what HNSW costs on the raw vocabulary.
- `R2 - R1` = what the vocabulary reduction buys or costs at matched HNSW.
- Ship the reduction only if `R2 >= R1` or `R2 >= (1 - BAR) * R0`, `BAR = 0.05`.

Run it at the HNSW parameters you are **forced** to use in production. A reduction
that loses at a rich graph (m=16, ef_construction=64) can still win at a starved one
(m=4, ef_construction=16) -- that is the whole hypothesis, so measure it there.

Reference measurement (~170k chunks, ~1.5M raw terms, ef_search=50):

```
                      m=16 / efc=64     m=4 / efc=16
R0  raw, exact            0.199            0.199
R1  raw, HNSW             0.197            0.053
R2  reduced, HNSW         0.179            0.046
```

At a rich graph HNSW cost 1% and the reduction cost 10%. At a starved graph HNSW lost
74% and the reduction did NOT rescue it -- it lost a further 13%. On this reference
corpus, shrinking the vocabulary does not make a starved HNSW graph walkable; the
graph parameters are the binding constraint. Re-run on your own corpus before
concluding otherwise.

## Rules for the comparison

- **recall@50, not recall@10 or hit@k.** With ~N relevant chunks per document,
  recall@k is capped at k/N; pick k so the cap is not binding. hit@k answers a
  different question and can move OPPOSITE to recall (HNSW can miss the single best
  chunk while retrieving more of the document in the top 50). One pooled number per
  arm; keep per-query-type splits in the log.
- **HNSW returns at most `ef_search` rows.** A metric at k > ef is computed over a
  truncated list. For recall@50, `ef_search >= 50`. Assert
  `len(rows) == min(k, ef)` on every HNSW query.
- **Raw means unnormalised BM25 weights.** An L2-normalised row under
  `sparsevec_ip_ops` turns `<#>` into cosine-BM25 -- a different ranking.
- **Same indexed population in every arm.** Never evaluate a chunk-sampled index:
  sampling splits documents and fragments the gold.
- **Parity first.** A psql exact scan (`SET enable_indexscan = off`) must reproduce
  the in-memory ranking before any HNSW number is read. Misses on short queries are
  rank-k score ties; compare score-sets, not row-sets.
- **Short queries are their own case.** 2-3 term queries give HNSW almost nothing to
  walk and collapse under it regardless of vocabulary (reference: ~0.4 -> ~0.09).
  Route them to exact scan.

## Term salience — the default option for "how much does this term matter" (2026-10-04)

**Operator ruling:** salience is read off the sparsevec **inner product**, with a BPE tokenizer as the
input to the sparsevec and Postgres hosting all of it. Operator report: this works much better than the
BM25-framed, whole-word route. That comparison was NOT measured here (see "Not known").

**The definition.** A term is a set of vocabulary columns: one for a word that is a single piece, several
for a longer word or a phrase (a BPE vocabulary spells it with `##` continuation pieces). Its salience is

```
self share   = sum over its columns of v_c^2 / <v, v>            the term's part of ONE chunk's own inner product
pair share   = sum over its columns of a_c * b_c / <a, b>        the term's part of the inner product between two chunks
```

An inner product is a sum over dimensions, so **shares add exactly**: a whole word's share is the sum of its
pieces' shares, and the shares of every column of one inner product sum to 1. That additivity is what makes a
BPE vocabulary the right input for this job — every term can be spelled from pieces, however rare, and the
share of the spelled term needs no approximation. Salience across the graph is then how the term moves the
chunk's position among its sparsevec neighbours, which is `pair share` over the HNSW cosine neighbours.

**Where it lives in Postgres** (the label's tables, one build per label): the vocabulary `lex_vocab(label,
col, piece, idf)`, the L2-normalised idf x saturated-tf view in `lex_cos_<label>` under `sparsevec_cosine_ops`
(neighbours: `ORDER BY vec <=> q LIMIT k`), the build's communities in `lex_assign`. Nothing is read from a
file. The command:

```
python tools/term_salience.py <term> [<term> ...] [--k 15] [--top 5] [--dense]
```

It prints the term's columns, how many of the nearest sparsevec neighbours of its most salient chunks also hold
it and the median share of the inner product it carries there, its spread over the communities (entropy, G2),
and with `--dense` its effect on the MiniLM embedding (median |e(d) - e(d without term)| against about 0.09 for a
random word, and the cosine between two such deltas against about 0.00 for different terms).

**Reference reading, live arXiv build (56,051 chunks, a WORD vocabulary, not BPE):** `grpo` is in 769 chunks of
204 papers; across the 45 nearest neighbours of its three most salient chunks, 37 hold it and it carries a median
15.7% of the inner product; 21% of its chunks sit in one community (G2 612). Deleting it moves a chunk's MiniLM
embedding by 0.235 (random word: 0.09), and two such deltas for the term agree at cosine 0.735. A phrase such as
`kv cache` cannot be spelled from that word vocabulary (`kv` is two characters, below its tokenizer's floor):
the case a BPE vocabulary exists for.

**Rules.**

- Spell the term with the **same tokenizer and vocabulary as the index**; a term that cannot be spelled has no
  salience, and the command says so rather than guessing.
- A chunk **holds** a phrase when its sparsevec is nonzero on every one of the phrase's columns. That is a bag,
  not adjacency: say so when reporting a phrase.
- Report the pair share with the number of neighbours that hold the term beside it; a share over three neighbours
  is not a share over thirty.
- Keep **self share** (one chunk's own inner product) and **pair share** (two chunks') apart in every table.

**Not known.** (1) BPE against the word vocabulary for this job: the operator's observation, with no measurement
in this skill. The discriminating test is the same terms, spelled both ways on the same chunks, comparing which
spelling recovers more of the neighbours that actually share the term. (2) The retrieval result below is a
different job and still stands.

**Do not read the retrieval measurement as a verdict on this option.** The measurements in the rest of this skill
ask whether a reduced BPE vocabulary keeps recall@50 for QUERIES. On the reference corpus it cost about 10% at a
rich HNSW graph, and on the arXiv build in this repo a raw word vocabulary beat BPE by 8-17% rec@50 at 40% more
disk. Choose the vocabulary for retrieval by the three-arm comparison above; choose it for term salience by this
section.

## Mechanics in pgvector

- Chunk vector = BM25 weight per term; query vector = 1 per query term; `ORDER BY
  vec <#> q` (negative inner product) IS the BM25 ranking.
- `sparsevec_ip_ops`, not cosine. One table per vocabulary -- the dimension is part of
  the column type.
- Limits: `SPARSEVEC_MAX_DIM` 1e9; 16,000 nonzeros per value; 1,000 per value under an
  HNSW index. Keep each row's HEAVIEST 1,000 (measured: no recall cost).
- `SET`, never `SET LOCAL`, on an autocommit connection -- `SET LOCAL` is a no-op there.

## The procedure

```
0. GOLD      derive query/relevant pairs FROM THE CORPUS, deterministically
1. CHUNK     pack whole units to a target fitted on the corpus's own sections
2. WORDS     one word tokenizer for index AND queries
3. BM25      doc x term matrix, unnormalised; keep it, do not collapse to doc x doc
4. SCORE     per term: max over chunks * sqrt(df), then log2
5. ELIGIBLE  df >= 2; exclude length outliers (k=2) unless wordfreq word or capitalised name
6. SOFT BAND keep score >= MIN(mean - f*sd, median - f*1.4826*MAD), whole distribution
7. WHALES    drop terms in > 50% of chunks
8. BPE       train on the SURVIVING TERM STRINGS only; sweep a MERGE BUDGET
9. REBUILD   BM25 over pieces, chunks and queries alike
10. COMPARE  the three arms above, recall@50, at the production HNSW parameters
```

### 0. Gold first

Term-list coverage cannot tune any of this: a lower bound only trims the bottom of a
distribution, where query terms never live. Only retrieval recall responds.

Gold that costs nothing, needs no judge, and is byte-reproducible:

| corpus shape | query | relevant set |
|---|---|---|
| documents with a title | the title | that document's chunks |
| any document | a mid-document sentence of 8-24 words, fixed seed | that document's chunks |
| documents with section headings | the heading | that section's chunks |

Drop heading lines from the indexed text so no query is verbatim in a chunk. ~200
queries per gold set detects a 5% delta; sample size is the query count.

### 1. Chunk on the corpus's own statistics

Per `reduce_overlaps`: fit a target on characters-per-section where real sections
exist (Box-Cox, median), then **pack consecutive whole units up to the target and
never split one**. That respects boundaries without knowing whether a unit is a line
or a paragraph (text extracted from PDFs is often line-granular). Fit once per
source; pooling registers of very different length gives a fit that describes
neither. Assert conservation: a document's chunks concatenate back to its units, none
lost, none duplicated -- a duplicate inflates df.

Do not detect headings by font size: body size by character mass lands on footnotes,
and many documents have no styled headings at all.

### 2-3. One tokenizer, keep the term axis

Index and queries through the **same** tokenizer; any disagreement is a defect. Keep
the doc x term BM25 matrix intact and unnormalised.

### 4. Score terms so rank means something

```
score(t)     = max over chunks of BM25(t, c) * sqrt(df(t))
log_score(t) = log2(score(t))
```

`sqrt(df)` is a **rank weight, not a filter**. BM25 is maximal for a rare term in a
short chunk, so any collapse without a df term ranks hapaxes first. Measured
alternatives (bare max, mean over occurrences, banding on df) put zero domain terms
in the top 1,000; `max * sqrt(df)` was the only rule that ranked them.

log2 is inert at a quantile cut and load-bearing at selection (mean and sd are not
transform-equivariant): compute band statistics on the log2 values.

### 5. Eligibility

`df >= 2` removes most of the vocabulary -- a hapax cannot match a query unless the
query contains that exact token.

Then the **length-outlier rule** -- flag and exclude, never correct:

```
outlier   = length > median + 2*1.4826*MAD of LETTERS-ONLY term lengths
exclude   = outlier AND NOT a dictionary word        (dictionary = wordfreq, zipf > 0)
```

Overlong terms are mostly missing spaces (`retrievalaugmented`), hashes, base64 and
LaTeX macro names. A genuine compound is lexicalized -- it is IN the dictionary -- so
dictionary membership is the only exemption. Nothing is split or repaired; this stage
only decides what enters the vocabulary. No special case for part numbers.

Two choices are load-bearing, both measured on a 40k-chunk sample (292k distinct terms):

- **Fit the length distribution on letters-only terms, apply it to all terms.** Fitted
  on all terms, base64 and hash strings pushed the median to 11 and the cutoff to 42
  chars -- above every missing-space fusion. Letters-only: median 7, MAD 2, cutoff
  12.9 chars at k=2.
- **Use a frequency dictionary (wordfreq), not WordNet.** WordNet lacks technical
  derivations, so it excluded `parameterization` (df 127), `compositionality` (75),
  `heteroscedasticity` (22); wordfreq keeps all three and still excludes the fusions
  (`retrievalaugmented`, `instructionfollowing`).

**Choose k and the keep-test on a hand-labelled diagnostic list, not by feel.** Read
the terms the widest rule would drop and label them KEEP (real words and technical
vocabulary), NAME (people, models, datasets -- real tokens, in no dictionary), ERROR
(missing-space fusions, LaTeX macros, URL fragments, hashes, base64, typos). Then
score each rule. Reference result, 77 KEEP / 39 NAME / 61 ERROR:

```
k   cutoff   keep-test           words kept   names kept   errors removed
2   12.9     NLTK/WordNet             5%           0%           100%
2   12.9     wordfreq                70%          21%           100%    <- chosen
2   12.9     wordfreq or df>=5       94%          92%            66%
3   15.9     wordfreq                91%          92%            57%
4   18.9     wordfreq                99%         100%            30%
```

k=2 + wordfreq is the only rule that removes every error, and fused text is the
target. Its cost was names -- so names are taken out of the length decision entirely.
k=3 and k=4 are dominated: short fusions (`selfattention`, 13 chars) slip under the
higher cutoffs.

**Names are their own class, decided per domain.** They reference, they do not
describe, and the length rule only ever touches LONG names -- a biased, arbitrary
subset. Detect them deterministically from the raw (un-lowercased) text: a term is a
NAME when it is capitalised in >= 50% of its mid-sentence occurrences (seen >= 2x).
Measured on the diagnostic list: NAME 36/36 detected, KEEP 0/70, ERROR 2/16 (CamelCase
brand fusions). Final rule:

```
overlong AND wordfreq word         -> keep
overlong AND capitalised name      -> NAME (never dropped by length)
overlong AND neither               -> exclude
NAME terms enter the index         -> per-domain switch
```

Switch names on when the corpus is queried for who/what entities are; off when they
are noise. Short names never reach the cutoff, so the switch governs the long ones.

**No standalone case filter.** A "predominantly ALL-CAPS" rule dropped 981 short terms
from the same sample -- `llm, gpu, rlhf, rag, mmlu, sgd, cpu` -- the core acronyms of
the domain. Acronyms (3-5 chars) can never be length outliers, so the rule above
never touches them.

### 6. Soft band — a size dial

```
keep(t)  iff  log_score(t) >= MIN( mean - f*sd,  median - f*1.4826*MAD )
```

The MIN is the most permissive of two lower bounds, so a term is not dropped because
one estimator misfits.

- **It sets size, not ranking.** Across f = 0.0 -> 1.0 the vocabulary changed 4x and
  recall did not move. Set f by the vocabulary size you need; f = 0.0 keeps ~50%.
- **Apply it once, globally.** Per-decile bands trim the bottom of every band
  including the best one, and lose terms at matched size.
- Globally the robust branch always bound; keep the disjunction as insurance.

### 7. Whales

Drop terms in more than 50% of chunks, **after** scoring: removing term u cannot
change term t's BM25; only dropping tokens from documents (length normaliser) would.

### 8. BPE over survivors, sized by a merge budget

Train BPE on the **surviving term strings only**, never the raw text -- a corpus-wide
second tokenizer diverges from step 2 and makes merged pieces unreachable from
queries.

Size it by a **merge budget**, not a multiple of the term count: a budget above the
term count merges every term whole and finds no shared subword. Sweep merges at
`min_frequency = 2`:

```
merges     pieces   single-token terms   mean pieces/term
   300        337        0.3%                3.82
 1,000      1,037        1.4%                3.10
 3,000      3,037        4.4%                2.53
10,000      8,479       14.0%                2.04
```

The budget saturates once no more pairs recur at `min_frequency`.

### 9. Derive on a sample, apply to the whole

The vocabulary can be derived on a sample and applied to a corpus that does not fit
in memory. Reference: pieces derived on a 17% sample scored the same recall@50 on the
full corpus as pieces derived on all of it, while sharing only half their members --
coverage matters, not the particular pieces.

- **A source never contributes more than it has.** When allocating a sample across
  sources, take `min(size, quota)`; a quota above a source's size means sampling
  with replacement, which duplicates df.
- **Sample chunks for the vocabulary, documents for the eval.**

## Alternative: PCA / LSA

Truncated SVD of the BM25 matrix gives a **dense** vector of a few hundred dimensions:
every row has every dimension, so HNSW connectivity is not a problem -- but it is
pgvector `vector`, not `sparsevec`, and loses exact-term matching. It attacks
connectivity directly; BPE attacks it by raising term overlap. Measure both on the
same three-arm comparison.

## Rejected on measurement

| proposal | why it looked right | what the measurement said |
|---|---|---|
| shrinking the vocabulary to rescue a starved HNSW graph | more shared nonzeros -> better connectivity | at m=4/efc=16 recall@50 0.053 raw vs 0.046 reduced; the reduction made it worse |
| judging HNSW by hit@k | the natural metric | hit@1 fell 20% while recall@50 fell 1% |
| recall@50 at ef_search < 50 | the production setting | undefined: HNSW returns at most ef rows |
| collapse by bare max | keeps df out of the score | ranks hapaxes first; no domain terms in top 1,000 |
| collapse by mean over occurrences | kills "one hapax wins" | same failure |
| band on df | holds idf constant per band | worst of four rules; high-df terms ARE the domain terms |
| score deciles, band within each | per-band robustness | ~88% flat per band; loses terms vs one global band |
| BPE vocab = n_terms x {2,3,5} | "scale it up" | identical vocab at every factor, 100% single-token |
| font-size heading detection | headings are bigger | picks footnotes; many documents have no styled headings |
| splitting or repairing overlong terms | recovers concatenations | out of scope: this stage only flags; exclude outliers unless they are dictionary words |
| standalone ALL-CAPS filter | removes boilerplate | dropped 981 short acronyms (`llm, gpu, rag, sgd`); apply case only to length outliers |
| term coverage as the tuning metric | cheap, no gold | blind to the size dial; only retrieval recall moves |
| evaluating a chunk-sampled index | cheaper | fragments every document's gold |
