---
name: sparsevec-lexsem-graph
description: >
  Build and validate a lexical (capped subword sparsevec BM25: BPE or WordPiece with ##
  marker) + semantic (dense) retrieval stack on pgvector/HNSW with UMAP-Leiden communities.
  Use when sizing a subword vocab, storing BM25 as a sparsevec, tuning HNSW recall, or
  deriving cross-view communities and synonym candidates. Cross-reference: `pg-fts-pipeline`
  (lexical serving), `rag-kg-pipeline` (graph consumer), `validation` (battery design),
  `crystallization` (this file's provenance).
status: active
last_validated: 2026-10-03
validation_method: session (english_quotes, 1954 docs, 200-query batteries) + literature
---

# sparsevec-lexsem-graph

## Digest

**Question.** Can one index type (HNSW) serve BM25 lexical search AND feed UMAP/Leiden
community detection over lexical and semantic views, with a subword tokenizer sized by rule
instead of by guess, and no all-pairs correlation pass?

**Path to displaying clusters (executive summary).**
1. Embed every chunk with the dense model; mean-center and L2-normalize (R9).
2. Build one neighbor graph with HNSW (cosine, k=15). Everything below reads this graph.
3. Communities = consensus Leiden: 16 seeds, co-association on the graph's edges, keep pairs
   agreeing in at least half the runs, cluster once more. Single runs are not stable enough
   to ship (R11 is read on the consensus labels).
4. Resolution from a sweep: seed-stability goes flat over a wide range; pick the point in that
   range that gives the cluster size you want to show. n is an output, never an input (R20).
5. 2D layout = UMAP from the same neighbor graph. Labels never enter this step; it only
   decides where dots sit (R10).
6. Medoid per community chosen in embedding space (member closest to all others); its text
   is the label at that dot. Further quotes per community follow the exemplar rule (17d, R26):
   1 to 3 quotes by Box-Cox of size, drawn inside the centroid band at equal steps of band position, MMR inside each window.
7. Colour by community, hues assigned so 2D-neighbouring communities differ; the medoid text,
   not the hue, is the identifier.
8. New rows get a community by nearest-neighbour vote over the index, or by a UMAP+k-means
   model fit on a sample (k from step 4); Leiden is not re-run (14b, R21).
The picture is for browsing and labelling. Cluster ids do not improve ranking on their own
view and are not a query-time filter (R22); result pages group the retrieved set post hoc (17c).
Reference run: `umap_medoids.py <dense>` -> `umap_medoids.png`, `umap_medoids.csv`.

**Findings (durable).**
- BM25 is exactly an inner product when the doc sparsevec holds saturated tf and the
  query holds idf*qtf. No approximation is needed; dropping saturation loses roughly half
  the exact top-k before any index is involved. avgdl from a ~10% sample is as good as full.
- HNSW over a BM25 sparsevec in ip space needs more graph than dense embeddings: very small
  M/ef recovers under half the exact top-k; M=16 with ef in the high-tens to low-hundreds
  reaches 95-99%. Representation loss and index loss multiply.
- Cosine on mean-centered dense vectors is Pearson correlation; a thresholded kNN graph IS
  the sparse significant-correlation matrix. No model, no all-pairs.
- Significance pruning of kNN edges is inert: HNSW top-k neighbors already sit an order of
  magnitude above a random-pair null (median + 3*MAD removes well under 1% of edges), so
  communities and their seed-stability are unchanged. A percentile threshold that does
  bite (p99.9) removes ~90% of edges and shreds the graph into singletons; the stability
  number rises only because isolated nodes are trivially stable. Community instability on
  short text is not caused by weak edges and cannot be pruned away. Use the null as a
  floor for edges ADDED beyond top-k, never as a filter on the ones the index returned.
- Subword vocab sizes above the corpus's merge capacity are identical (training saturates);
  sizing must come from surviving-term count, not a round number.
- Vocab = n_terms * sigma, n_terms = words surviving df>2, outlier removal, and the decile
  band: recall knee sits at sigma=1 (below it ranking drops significantly, above it nothing
  improves), at a fraction of the saturated vocab. Typo robustness falls monotonically with
  vocab; sigma=1 is the operating point on both axes.
- The continuation marker ("##" on word-internal pieces, WordPiece convention) raises typo
  robustness significantly at the same vocab and leaves ranking unchanged: a word-initial
  piece and the same letters mid-word stop colliding. Always on.
- BPE vs WordPiece, trained on the same surviving words at the same cap with the same
  marker, four trainings each, paired: WordPiece ranks slightly better (single-digit
  percent relative on P@13 and R@13, nDCG flat); BPE is slightly more typo-tolerant (a
  couple of points of hit@13). Both effects are small, real (CIs exclude 0, retraining
  spread is an order of magnitude smaller), and opposite. Pick by query source: clean
  system-generated queries -> WordPiece; human-typed queries -> BPE. Record the choice.
- A pretrained BERT WordPiece (30k, bert-base-uncased) as the lexical tokenizer ties
  whole-word BM25 on ranking and is worst-in-class on typos: most common words are single
  tokens in its vocab, so it behaves like a whole-word tokenizer. Its shared token space
  with the dense model buys BM25 nothing.
- n is not a parameter. Under Leiden's RB objective n grows with resolution without end, so
  there is no plateau in n; the plateau is in seed-ARI, which goes flat at a ceiling across a
  wide resolution range (on the dense view: flat from n~40 to n~190). Pick resolution inside
  that range by serving size. Pair-precision lift climbs with n only because finer partitions
  are purer; compare it at equal n. The lexical view has no usable ceiling on short text:
  "no n" is a valid result and means edges-only for that view.
- Single-seed Leiden on the dense view tops out just under the stability gate. Consensus
  clustering (8-16 seeds -> co-association restricted to kNN edges -> keep pairs agreeing in
  at least half the seeds -> one Leiden run) lifts stability clearly past the gate with
  agreement unchanged and only a handful of isolates. Communities therefore come from
  consensus Leiden on the dense view; raw single-seed labels are never shipped.
- The real dense view behaves nothing like the lexical stand-in: dense retrieval roughly
  doubles lexical on P@13 and nDCG with the tag truth, the two views' partitions are near-
  independent (ARI well under 0.1), and ~80% of dense kNN edges have no lexical edge; the
  top of those contrast edges are clean paraphrases (same idea, different words). That is
  the synonym-candidate channel working as intended.
- Out-of-sample assignment works, and the map is the instrument for it: UMAP-10d fit on half
  the data + KMeans at the plateau k, applied to the other half, matches a kNN vote of
  Leiden labels on agreement with the full consensus partition and on draw-to-draw
  stability, with slightly higher tag agreement; KMeans on raw dense is less stable at the
  same k. What does not work is choosing k by a BSS ratio or Calinski-Harabasz: both pick
  the smallest k offered in either space. k comes from the stability plateau.
- A community id does not improve ranking on the view it came from: filtering to the
  query's cluster and capping per cluster are significantly worse, boosting is flat at best.
  Across views it does carry signal: a lexical ranking boosted by the dense top-5 majority
  cluster nearly doubles its precision (significant), landing a little under full
  lexical+dense rank fusion. Read: the cluster id is a one-integer compression of the dense
  ranking, worth using where the dense ranking itself cannot be served, and nowhere else.
- A Leiden community is a connected region, not a ball: median cosine to the medoid is low
  (~0.3) and the far end can be unrelated to it (reached by a chain of local neighbours).
  Two cheap markers separate core from periphery: members with a lexical∩semantic kNN edge
  inside the community (about three quarters) carry roughly twice the tag agreement of the
  rest; a one-sided centroid cut (cos >= median-MAD, same retention) is slightly sharper. The
  two markers are partly independent: both together mark a core with higher agreement than
  either alone, neither marks a periphery near random. Read by eye, cores are single clear
  topics (darkness/stars, the craft of writing, mortality); the edge-only members are not
  stragglers but small coherent side topics (fire, kissing, drinking) riding inside a larger
  community, i.e. the fine resolution level showing through the coarse one. mean-1sd and median-MAD
  agree on ~90% of members; in normal space the mean/sd cut is the principled one and
  median-MAD is the fallback for residual skew. Cosine to centroid is
  near-symmetric on this corpus (skew ~0), so a log transform changes nothing; check skew
  first and transform only when it is there. The
  medoid is the label of the core; the periphery is what nearest-neighbour reassignment and
  post-hoc result grouping are for.
- Stored communities and result-list groups are different partitions (ARI ~0.4 at equal k),
  and inside a result set the post-hoc groups agree with tags better than the stored labels
  do. So the two serve different jobs: stored ids for the catalog (browse without a query,
  facets, routing, cross-view boost, ids stable over time, out-of-sample via 14b); post-hoc
  grouping for the result page (group, pick medoids, diversify, "more of this group" as a
  query-by-example from the group medoid). Neither replaces the other.
- At equal n against the consensus-Leiden reference, no other partitioner beats graph
  communities on tag agreement, cross-seed stability and out-of-sample behaviour taken
  together: k-means ties or slightly leads on tag agreement but its partitions do not
  reproduce across seeds (agreement about half of consensus Leiden's); median/PCA split trees,
  MMR-style medoid cells and max-entropy annealing are lower on tag agreement and mostly less
  stable. No test a method can run on its own clusters finds a topic-scale stopping point: the
  variance-share permutation null and the annealing critical temperature accept every split,
  projection bimodality refuses the first, and facility-location coverage beats its shuffled
  null out to hundreds of centers. The corpus is a continuum; n comes from cross-seed
  stability (R20). Weakest point: the tag truth is broad and favours compact blobs, so a
  method that ties on tags and loses on stability is a stability call, not a quality proof.
- Score shape before mean/sd: embedding dimensions and cosine-to-centroid are already
  symmetric (no transform), kNN edge cosines are mildly right-skewed (fitted lambda negative),
  lexical edge cosines sit near log, BM25 scores need a lambda between identity and log (log
  overcorrects). Fisher z worsens skew on tail-selected edges (near-duplicates dominate).
  Per-dimension robust scaling or Yeo-Johnson of the embedding is neutral on retrieval and on
  community quality. In normal space mean/sd is the principled cut; median-MAD is the
  fallback for residual skew.
- MMR and max-entropy belong to representative selection, not partitioning: the medoid-per-
  community table reads like an MMR list because one-per-group is diversification. Use
  facility-location/MMR to pick exemplars (display, result-page diversification), where
  diversity is the goal.
- Equal-weight RRF of a strong and a weak arm lands below the strong arm alone. Fusion weight
  must follow measured per-arm quality, or the weak arm runs as filter/boost only. (OPEN:
  measured once, not yet swept.)
- kNN edge cosines fall into three tiers with distinct operations: cos~1 (exact copies)
  -> COLLAPSE to one canonical row with alias ids; significant-but-distinct (every other
  kNN edge; the null cut removes <1%) -> EDGE, consumed by Leiden and the contrast views;
  below null -> nothing. A grey band (variant/excerpt/overlapping chunk, roughly 0.8-0.95)
  is kept as edges flagged variant_of and deduped at serve time, never merged. Stored
  vectors are never BLENDED with neighbors: smoothing sharpens communities, blurs
  retrieval, and is irreversible; neighbor blending belongs on the query side (Rocchio).
- Capped-vocab subwords are MORE typo-robust than whole-word tokens; saturated subwords
  (common words kept whole) are less. The mechanism is piece length, not subwords per se.
- Capped subword training is not bit-deterministic across runs (tie-breaking): vocab
  overlap ~98-99%, recall spread small but nonzero. Train once, save the tokenizer file,
  reuse it; differences smaller than that spread are training noise.
- Tokenizer-side decile cut (word-level BM25 -> log -> deciles -> keep above bin
  median-MAD / mean-SD -> survivors train the tokenizer) is a wash on a flat-vocabulary
  corpus and reported strong on a domain corpus: it needs a wide term-weight spread and
  boilerplate-like terms to act on. Index-side, the same cut reduces to a data-derived
  stopword list.
- Lexical Leiden communities on short text are seed noise at every resolution; lexical
  EDGES (kNN, contrast pairs) are stable. Community labels come from the semantic side.
- PCA/LSA (TruncatedSVD) over the lexical sparsevec: for RETRIEVAL it is destructive (rare-
  term directions, where BM25's signal lives, are the low-variance ones PCA discards first;
  a large fraction of the exact top-k is lost even at hundreds of dims). For COMMUNITIES it
  raises seed-stability monotonically as dims fall while external agreement (label pair-
  precision) falls at the same rate: at very low dims the clusters are reproducible and
  nearly random. Stability and external agreement must be read together; stability alone
  passes a meaningless partition. On short text the two curves cross around 128-256 dims
  and still miss the stability gate. Worth retrying only on corpora with real topic
  structure, with both columns reported.
- UMAP accepts an HNSW-built kNN (precomputed_knn); edge overlap with its internal search
  is ~0.99. One index type, two spaces: ip for queries, cosine for doc-doc.
- UMAP adds nothing to community detection. Leiden on the raw HNSW kNN graph (cosine-
  weighted, symmetrized by union) gives the same community count and the same seed-
  stability as Leiden on UMAP's fuzzy-reweighted graph_, on both views. Label differences
  between the two graphs equal the seed-to-seed differences (noise). UMAP is for the 2D
  picture and for placing new points on an existing layout; t-SNE is for pictures only.
- Small query batteries (~20) flip sign against 200-query results; broad-tag truth caps
  recall. Use >=200 queries and a strict (specific-tag) truth.

**Entities.** pgvector `sparsevec` + `sparsevec_ip_ops`; hnswlib; umap-learn (`graph_`,
`precomputed_knn`, model operators `*`, `+`, `-`); leidenalg (RBConfiguration, multiplex,
negative-link layer); HF `tokenizers` (`models.BPE`, `models.WordPiece`, `BpeTrainer`,
`WordPieceTrainer`, `continuing_subword_prefix`); `ts_stat()`; ftfy.

**Lessons.** See Guards and CLOSED below.

**Open.** MMR/facility-location exemplars inside a community vs closest-to-medoid as the display (untested); Weighted RRF (or dense-primary with lexical as boost/filter) vs equal-weight RRF, measured on the 200-query battery; whether the data-derived stopword cut helps the ensemble; sigma knee, HNSW ef and the tokenizer-side decile cut on a domain corpus.

---

## BM25 as a sparsevec (derivation)

Standard BM25 for query q against document d:

```
BM25(q, d) = sum over terms t in q of
             idf(t) * qtf(t) * tf(t,d) * (k1 + 1)
             / ( tf(t,d) + k1 * (1 - b + b * len(d) / avgdl) )

idf(t)  = ln( 1 + (N - df(t) + 0.5) / (df(t) + 0.5) )      # Lucene/Robertson form, never negative
N       = number of documents         df(t) = documents containing t
len(d)  = tokens in d                 avgdl = mean len over the corpus
k1 = 1.2   b = 0.75                   (defaults; tune per corpus if at all)
```

Every factor is either per-(term, document) or per-term. Split them by side:

```
doc side   (stored once per document, in the sparsevec):
    sat(t, d) = tf(t,d) * (k1 + 1) / ( tf(t,d) + k1 * (1 - b + b * len(d) / avgdl) )

query side (computed at query time from a small idf table):
    qw(t)     = idf(t) * qtf(t)

then       BM25(q, d) = sum_t qw(t) * sat(t, d)  =  <qvec, dvec>      # plain inner product
```

Checks and consequences:

- `<qvec, dvec>` reproduces brute-force BM25 to floating-point precision (assert it once).
- The doc vector holds no idf, so when the corpus grows only the idf table changes; documents
  are not re-indexed. avgdl from a ~10% seeded sample matches the full-corpus value.
- Global stats need one pass: `df(t)` from `ts_stat()` or a column sum of (tf > 0); `avgdl`
  from a length column. Terms unseen in a sample get the maximum idf.
- pgvector: `sparsevec` column for `dvec`, `sparsevec_ip_ops` HNSW index, query with `<#>`
  (negative inner product) against `qvec`.
- Doc-to-doc similarity (for the kNN graph) uses a symmetric view instead:
  `lexvec(d) = normalize( sat(:, d) * idf )`, cosine. BM25 itself is asymmetric and is not a
  doc-doc distance (R7).
- Dropping saturation (`tf / (len/avgdl)` or raw tf) is not an approximation of the above; it
  loses roughly half of the exact top-k before any index is involved.

---

## STAGED PIPELINE

| # | Stage | Step | Mechanism | Tag | Guards |
|---|---|---|---|---|---|
| 1 | INGEST | load | rows with text (+ optional labels for truth) | [mandatory] | |
| 2 | CLEAN | repair | ftfy.fix_text (mojibake, curly quotes) before any tokenizing | [mandatory] | R1 |
| 3 | CLEAN | length_filter | keep log2(char len) in median +/- 2*MAD | [opt] flag | |
| 4 | TOKEN | word_filter | pre-tokens with df>2; drop non-dictionary length outliers (log2 len > med+2*MAD) | [mandatory] | R2 |
| 5 | TOKEN | decile_band | word-level BM25 max weight -> log -> deciles -> keep above bin median-MAD (or mean-SD) | [opt] flag | R3 |
| 6 | TOKEN | n_terms | survivors of 4 ∩ 5 | [mandatory] | |
| 7 | TOKEN | subword | HF BPE (default) or WordPiece on survivors, vocab = n_terms*sigma, sigma default 1, continuing_subword_prefix="##" | [mandatory] | R4,R5,R14,R15 |
| 7b | TOKEN | alphabet_complete | after training, add every corpus char in both bare and "##" form (trainer only guarantees bare); BPE: round-trip vocab.json/merges.txt via from_file; WordPiece: rebuild from vocab dict | [mandatory] | R5,R15 |
| 7c | TOKEN | persist | save tokenizer file; all downstream arms load it, never retrain | [mandatory] | R16 |
| 8 | SCORE | doc_sparsevec | sat = tf(k1+1)/(tf+k1(1-b+b*len/avgdl)); store per doc | [mandatory] | R6 |
| 9 | SCORE | idf_table | df from one pass (ts_stat or equivalent); idf on the QUERY side only | [mandatory] | R6 |
| 10 | SCORE | doc_doc_view | sat*idf, L2-normed (symmetric lexical view) | [mandatory] | R7 |
| 11 | INDEX | hnsw_ip | HNSW ip space over 8, serves queries | [mandatory] | R8 |
| 12 | INDEX | hnsw_cos | HNSW cosine over 10 (lexical) and over centered dense (semantic) | [mandatory] | R7,R9 |
| 13 | GRAPH | knn_graph | symmetrize the HNSW cosine kNN (union), weight = cosine; this is the community graph | [mandatory] | R10 |
| 13a | GRAPH | umap | UMAP(precomputed_knn from 12) for a 2D map or transform of new points; NOT for clustering | [opt] flag | R10 |
| 13c | GRAPH | lsa_coarse | TruncatedSVD(k) over the lexical view -> cosine kNN -> Leiden, as a COARSE partition; k chosen where seed-ARI and external agreement rise together; never applied to the retrieval index | [opt] flag | R11,R18 |
| 13d | GRAPH | edge_tiers | per view: top-1 cosine quantiles; cos>=dup_thr (~0.99) collapse to canonical + aliases; grey band (~0.8-0.95) edge flagged variant_of; all other kNN edges plain edges | [mandatory] | R19 |
| 13e | SCORE | score_shape | per score family before any sigma/MAD cut: report skew; WHERE |skew|>0.5 fit Box-Cox lambda on the target corpus (Yeo-Johnson for signed values) and cut in the transformed space; mean/sd there, median-MAD only for residual skew | [mandatory] | R24 |
| 13b | GRAPH | edge_null | 100k random-pair cosines -> median, MAD, p99.9; report kNN-edge cosine distribution against it; prune ONLY edges added beyond top-k | [opt] flag | R17 |
| 14 | COMM | leiden_consensus | per view: sweep resolution log-spaced ~0.1-20, 4 seeds; find the STABILITY plateau (seed-ARI flat at its ceiling; n keeps growing with resolution, that is normal); inside it pick resolution by serving size (N / target cluster size); then CONSENSUS: 8-16 seeds -> co-association on kNN edges, keep >=0.5 -> Leiden once; gate R11 on consensus labels; two levels (coarse+fine) as columns | [mandatory] | R11,R18,R20 |
| 14b | COMM | oos_assign | new/held-out rows get a community without re-running Leiden: either kNN vote of consensus labels over the HNSW index (no second model), or UMAP-10d fit on a sample + KMeans at k from the stability plateau, transform+predict for the rest; both match out-of-sample on agreement and stability | [mandatory] | R21 |
| 14c | COMM | core_tier | per member, two markers: (a) centroid band: score = cos to community centroid; check skew, log-transform the distance only if skewed; band = mean-1sd in the power-transformed normal space (one-sided, ~84% kept), median-MAD only where residual |skew| stays above ~0.5; (b) >=1 lex∩sem kNN edge to a same-community member. Tier = core (a AND b, ~65%), member-near (a only: close to centroid, no lexical agreement), satellite (b only: a lexically+semantically coherent sub-clump off the centroid, e.g. a side topic the resolution did not split; these are what the FINE level is for), periphery (neither, ~7%, reassignment candidates). Medoid describes the core, never the boundary | [mandatory] | R23 |
| 15 | COMM | combine | sem*lex (precision), sem+lex (recall), sem-lex (synonym candidates), lex-sem (homonyms/ID collisions); optional multiplex Leiden | [opt] flag | |
| 16 | EVAL | battery | >=200 queries, strict truth; paired bootstrap CIs vs a fixed base; typo battery for tokenizer arms | [mandatory] | R12,R13 |
| 17 | SERVE | thesaurus | sem-lex pairs reviewed -> Postgres thesaurus dictionary; cluster ids as filter columns | [opt] flag | |
| 17b | SERVE | cluster_at_query | community id is NOT a same-view relevance signal (filter/boost/cap all neutral or worse). WHERE the serve path has only the lexical index and one dense query embedding, boost lexical results by membership in the dense top-5 majority cluster (w ~0.3 of the query's top BM25 score): recovers most of the lexical->fusion gain with one int column. WHERE the dense ranking is available, fuse rankings instead | [opt] flag | R22 |
| 17c | SERVE | result_grouping | 'more of this group' at query time: hybrid top-N -> cluster the N post hoc (agglomerative, average link, cosine; small fixed k or one tuned threshold) -> medoid per group shown -> expansion = ANN query from the chosen group's medoid (query by example), optionally AND stored cluster id for strict containment. MMR is the 1-per-group case | [opt] flag | R22 |
| 17d | SERVE | exemplar_display | quotes shown per community: n = round(1 + 2*minmax(BoxCox(size))) (1 smallest, 3 largest; size counted once, a sum-to-one ratio step is a no-op under min-max); pool = centroid band AND lex∩sem edge, fallback band only, never beyond; position each pool member on the band's own axis, z = (t - t_medoid)/(edge - t_medoid) with t the (Box-Cox) distance to the centroid and edge the one-sided mean+1sd cut (median+1.4826 MAD only where skew remains); medoid first, then targets at z = k/n for k=1..n-1 (n=2 midpoint, n=3 one third and two thirds, never the edge); per target an equal-width window |z - k/n| <= 1/(2n) and one MMR(lambda=0.5) pick inside it (relevance = closeness to the target, redundancy as below), empty window -> nearest-z member. Display rule specified by the operator, NOT measured against n-closest-to-medoid. MMR redundancy term (tested in-community, n=5): put each view's cosine on a global percentile scale first, then combine as a product (or mean) of the two; this gave the lowest pairwise redundancy in both views, beat alternating views per pick and dense-only, and lexical-only came close; max-combination (redundant if either view agrees) was worse, not better. Tag coverage and representativeness were not separable across arms. Bridge records: roughly a quarter of records carry a fifth or more of their neighbour weight in one other community, so a record MAY be an exemplar candidate for each community holding at least that share (untested) | [opt] flag | R26 |
| 17e | SERVE | entity_highlight | WHERE records carry NER entities, name a community by its entity profile: per community draw uniformly without replacement until M entity-bearing records are seen (or the community is exhausted); list top n_show (same Box-Cox 1 to 3 as 17d) entities per class by sample count then log-odds z vs the corpus (informative corpus prior). Query path: dense/hybrid top-N -> the communities with most hits (enrichment = hit share / size share reported) -> draw -> entities per class; stored community id identifies the cluster, no per-cluster query needed (a medoid-as-query is only a stand-in for 'a query that lands here'). Show two views per selected community, side by side: the query view (its top hits by score) and the community view (unbiased: from the SAME uniform draw, floor MIN_SAMPLE, take the sample medoid, then the 17d z-step MMR picks, then entities; only the lex∩sem edge marker reads the stored graph). Output as figure and as TOON text for an LLM (tabular arrays: hits, hit_entities, clusters, community_view, community_entities). Draw-until beats a fixed uniform-share quota by roughly 2 to 3x on recovery of the full-community top entities when most records carry none (a fixed quota is spent on empty records); recovery plateaus where most entities occur once (top-10 ties). Raw entity counts alone are dominated by corpus-wide frequent entities | [opt] flag | R27, R29 |

---

## Guards (EARS)

- R1 IF text is double-encoded THEN the run SHALL repair it before tokenizing (junk subword tokens otherwise).
- R2 The word filter SHALL use the same normalizer and pre-tokenizer as subword training.
- R3 WHERE the decile band is enabled, the run SHALL print decile edges of log(max BM25 weight per term); IF 90% of terms fall in one narrow band THEN the band cut has nothing to act on and SHALL be reported as inert.
- R4 The run SHALL report target and realized vocab; realized < target means saturation.
- R5 IF a tokenizer encoding of any corpus text yields [UNK] THEN the run SHALL fail (alphabet completion missing).
- R6 IDF SHALL live on the query side only, so corpus growth updates a small table, never the doc vectors.
- R7 Doc-doc neighbors SHALL come from the symmetric view (sat*idf, L2-normed, cosine), never from the ip BM25 index (asymmetric).
- R8 HNSW ef_search SHALL be >= k and SHALL be set by measured recall against exact brute-force BM25 on the target corpus, starting at M=16.
- R9 WHEN a dense view is used for correlation, it SHALL be mean-centered (sample mean) and re-normalized first.
- R10 Communities SHALL be computed on the weighted kNN graph (raw HNSW neighbors, symmetrized), never on a 2D projection; UMAP reweighting is optional and SHALL NOT be required by the clustering path.
- R11 IF seed-stability ARI of a view's CONSENSUS communities is below 0.8 THEN that view's labels SHALL NOT be used for routing or filtering; its edges may still be used. Single-seed Leiden stability is diagnostic only (its ceiling sits below the gate on dense short text).
- R12 A tokenizer or pruning decision SHALL rest on >=200 queries with paired CIs; a 20-query battery is a smoke test.
- R13 WHERE ground truth comes from broad labels, recall SHALL be computed on a strict subset (label df capped) or replaced by nDCG.
- R14 WHERE WordPiece is chosen over BPE, it SHALL be trained on the same surviving words, at the same cap, with the same marker; the choice SHALL be made from the query source (system-generated -> WordPiece, human-typed -> BPE) and recorded, not re-measured per experiment.
- R15 Subword training SHALL set continuing_subword_prefix="##"; a prefix-free run is a comparison arm only.
- R16 A capped tokenizer SHALL be trained once and loaded from file thereafter; IF two arms differ by less than the retraining spread THEN the difference SHALL be reported as noise.
- R18 Seed-stability ARI SHALL be reported alongside an external agreement measure (label pair-precision lift over random, or a labeled sample); IF stability rises while agreement falls THEN the partition is smoothing away signal and SHALL NOT be promoted.
- R20 n SHALL NOT be set directly; it SHALL fall out of a resolution chosen inside the stability plateau by serving size. IF no plateau reaches the gate after consensus THEN that view SHALL ship no cluster ids (edges only). Pair-precision lift rises with n by construction and SHALL be compared only at equal n.
- R21 WHERE a parametric clusterer (KMeans/GMM) is fit on a sample for out-of-sample assignment, k SHALL come from the Leiden stability plateau (or the shipped n); BSS/TSS and Calinski-Harabasz SHALL NOT select k (they collapse to the smallest k on kNN-structured data).
- R22 A community id SHALL NOT be used to filter or boost a ranking computed on the same view it was derived from; it MAY carry the other view's signal into a ranking that lacks it, at a weight set by the paired 200-query battery.
- R23 A community SHALL ship with a per-member tier (core / member / periphery) from the two markers in 14c; display, expansion and 'more of this' SHALL rank by cosine to the medoid and default to the core tier. Centroid cuts SHALL be one-sided (distance is bounded at 0); the band SHALL be mean-1sd in the normal space reached by a skew check and a fitted Box-Cox of the distance where skewed (median-MAD only where residual |skew| stays above 0.5), never a +/- band.
- R24 Before any mean/sd or MAD threshold on a score family (distance to centroid, edge cosine, BM25 score, term weight) the run SHALL report skew; WHERE |skew| > 0.5 it SHALL fit a Box-Cox lambda on the target corpus (Yeo-Johnson where values can be negative) and cut in the transformed space; lambda SHALL NOT be copied across corpora or score families. Fisher z SHALL NOT be used on tail-selected kNN edge cosines.
- R25 No test a cluster applies to its own top direction (variance-share permutation null, annealing critical temperature, projection bimodality, coverage gain vs shuffled null) SHALL set n or stop a split on short-text embeddings; n SHALL come from the cross-seed stability plateau (R20). Diverse-representative selection (MMR / facility location) SHALL pick exemplars, not form clusters.
- R26 Exemplar count n per community SHALL be a function of cluster size only (Box-Cox, min-max to [1,3]); picks SHALL sit at equal steps of band position z (k/n, k=1..n-1) in the band's own normal space, and MMR SHALL choose within each equal-width window and SHALL NOT also scale n. The pool SHALL stay inside the centroid band (R23); IF the band holds fewer than n members THEN show fewer, never reach outside it. Equal-count rank strata were the earlier rule and are superseded (CLOSED).
- R27 Entity sampling SHALL draw uniformly without replacement inside a community until M entity-bearing records are seen or the community is exhausted (the draw count is an output), SHALL NOT weight draws by retrieval hits, and SHALL show enrichment z beside raw counts; counts are reported as x of the draws, never as community rates. A TOON document handed to an LLM SHALL quote strings only where the spec requires (empty, padded, true/false/null, number-like, or containing : , " \ [ ] { } control characters, or leading - or #) and write numbers bare. Show it per query: top results with community id and stored entities, the selected communities, sampled entities per class.
- R29 A selected community SHALL be shown from two views kept apart: the query's (hits ranked by score) and the community's own (exemplars and entities computed from one uniform sample of that community, medoid first, z-step MMR picks per R26). The hits SHALL NOT feed the exemplar choice. A Layer-1 gate SHALL check that sample-derived medoid ranks near the top of full-community centrality and that picks land near their target z on the full-community axis before the view ships.
- R28 MMR redundancy over two views SHALL be computed on percentile-scaled cosines (raw lexical and dense cosines differ in range and skew) and combined as product or mean; alternating views per pick and single-view dense redundancy SHALL NOT be the default. No arm SHALL be judged only on the view it optimises.
- R19 Stored doc vectors SHALL NOT be averaged or blended with neighbors; collapse SHALL retain alias ids so it is reversible; dup_thr and the grey band SHALL be set per view from the measured top-1 cosine distribution, not reused across views.
- R17 WHERE an empirical-null threshold is enabled, it SHALL apply only to edges added beyond the index's top-k; IF it would remove more than a few percent of top-k edges THEN the threshold is mis-set (percentile on a heavy-tailed null), not the graph.

---

## CLOSED (do not re-litigate without new data)
- Feeding query hits into the community's exemplar pool: mixes score-biased and unbiased views and hides what the community is; kept as two views (R29).
- Equal-count strata of cosine-to-medoid as the exemplar spread rule (superseded 2026-10-03): rank-based, so spacing follows density and ignores the band's sigma; replaced by equal steps of band position z (17d, R26).
- Log transform + mean removal (space constant, rows summing to 0, i.e. centered log-ratio) on the sparse lexical doc vectors: roughly halves neighbour tag precision versus the raw idf-weighted vectors (zeros become a large constant mass and dominate). Dense vectors already get the corpus-mean constant removed; no further transform is needed there (R24).
- MMR redundancy by max over views (OR) beating product (AND): predicted, measured the reverse; percentile max compresses the penalty toward 1.
- Fixed quota = a community's share of a uniform sample for entity discovery: spent mostly on records with no entity; replaced by draw-until-M (17e). Raw entity count as the ranking: replaced by count plus enrichment z.
- Blending size, n_records and MMR into one n, or using deciles on top of Box-Cox size ratios: closed 2026-10-01 on logic (size would be counted twice, and the two normalisations answer different questions: how many vs which). Open only as a measurement: display rule vs n-closest-to-medoid on tag precision.

- Approximating BM25 with tf/len and no saturation: loses ~half the exact top-k. Rejected.
- HNSW at M=4/ef=16 over BM25 sparsevec: recovers under half of exact. Rejected.
- Round-number subword vocab (8k/10k/16k) on small corpora: identical after saturation. Use the sigma rule.
- Prefix-free subword pieces (no "##"): superseded; the marker raises typo robustness significantly at zero ranking cost.
- Pretrained BERT WordPiece as the lexical tokenizer: ties whole-word BM25, worst on typos, most of its vocab dead on a small corpus. Not adopted for the lexical side.
- BPE vs corpus-trained WordPiece at the same cap and marker: small, real, opposite effects (WordPiece +ranking, BPE +typo tolerance). Single trainings cannot separate them; four paired trainings can. Decide by query source, not by re-measuring.
- Significance pruning of top-k edges before Leiden: MAD thresholds remove <1% of edges (no change); percentile thresholds fragment the graph (hundreds of singletons, fake stability). Rejected as a stability fix.
- UMAP fuzzy reweighting as a clustering pre-step: same communities, same stability as the raw kNN graph. Dropped from the mandatory path.
- PCA/LSA before the retrieval index: loses a large share of exact BM25 top-k at any practical k. Rejected for serving; coarse-partition use only, under R18.
- Blending (neighbor-averaging) stored chunk vectors to strengthen communities: blurs retrieval, irreversible. Rejected; query-side expansion only.
- Community id as a same-view retrieval signal (filter to the query's cluster, boost members, cap per cluster): filter and cap significantly worse, boost flat to worse. The cluster is a quantization of the space already being ranked. Rejected; navigation and routing only.
- BSS/TSS or Calinski-Harabasz to choose k on dense text: picks the minimum k offered, in raw and in UMAP space alike. Not a selector here.
- graph2vec for communities: whole-graph embedding, wrong level; node-level needs node2vec/DeepWalk, which on a cosine-kNN graph is the dense+UMAP representation already in hand.
- Equal-weight RRF when per-arm nDCG differs ~2x: below the stronger arm alone. Weight by measured quality or demote the weak arm.
- Raw single-seed Leiden labels on the dense view: ceiling below the gate; consensus over seeds is the shipped form.
- Plateau-in-n as the resolution selector: n never plateaus under RB Leiden. Superseded by the stability plateau + serving size.
- Recursive median/PCA split trees as a clusterer (fixed depth, permutation-null stop on top-direction variance share, mean cut in Yeo-Johnson space): the equal-count control cuts through the densest part of a unimodal projection (tag agreement about half of k-means); the permutation stop never stops (tree runs to the size floor, equal leaves); out-of-sample it is the least stable and least tag-aligned assigner tested. Rejected.
- Max-entropy deterministic annealing as a clusterer: the top-eigenvalue split rule fires for every cluster inside the same narrow temperature range (K doubles at every cooling step), leaving a few giant cells beside tiny ones; lowest tag agreement at equal n. Rejected.
- MMR / facility-location / k-center medoid cells as clusters: below k-means on tag agreement at equal n and low agreement with the graph partition; k-center chases outliers (worst), facility location is the best of the family. Rejected for clustering; kept as the exemplar picker.
- Coverage-gain null stop for K (facility-location gain vs column-shuffled copy): observed beats null out to hundreds of centers; no stop at topic scale.
- Per-dimension robust scaling / Yeo-Johnson of the embedding: neutral on retrieval (paired CI includes 0) and inside the draw-to-draw spread on communities. Optional flag, default off.
- Clustering the 2D t-SNE/UMAP output: discards edge weights; t-SNE cannot place new points. Graph-level only.
- Index-side decile pruning at entry level: hurts. At term level: equals a stopword cut; use a plain data-derived stopword list instead.
- Dictionary/length outlier rule on top of df>2: added nothing on tested corpus; keep as a flag, default on, cheap.
- Negative dense doc-doc edges: little meaning after centering. Signed edges only on the term-term (lexical) side for synonym mining.
- Raw term co-occurrence as synonym signal: finds associations, not synonyms. Use negative first-order + positive second-order (PPMI) within semantic clusters.

---

## Cheapest discriminating tests (each <15 min)

1. Decile edges of log(max BM25 weight per term). Wide, even spacing -> band cut has structure to use.
2. Seed-stability ARI per view (2-4 seeds, several resolutions). Gate for using labels.
3. HNSW ef sweep, exact BM25 as ground truth, on the target corpus. Sets ef.
4. Sigma sweep {0.5, 1, 1.5} with bookends {0.25, 2}; paired CIs vs sigma=1; typo battery (6-word window, every word edited once).
5. Retrain the capped tokenizer 3-4 times; vocab Jaccard and recall spread = the noise floor for tokenizer comparisons.
6. Top-20 neighbor overlap with and without dense mean-centering. Low overlap -> center before clustering.
7. ARI(sem, lex) read against the seed-noise floor; top-30 sem-lex edges by eye.
8. Leiden on raw kNN graph vs UMAP graph_: if community count and seed-ARI match, skip UMAP for clustering.
9. LSA dims sweep {16..512}: seed-ARI and label pair-precision lift side by side. Promote a k only if both rise; a stable-but-random partition is the failure this catches.
10. Edge-tier histogram per view: top-1 cosine p50/p90/p99/max and edge counts above 0.8/0.9/0.95, with the top pairs printed. Sets dup_thr; a near-empty top band means collapse is a no-op on that corpus.
11. Resolution sweep per view (`resolution_sweep.py <dense>`): n, seed-ARI, pair-precision lift, cross-view ARI at ~10 log-spaced resolutions, extended upward until seed-ARI goes flat. Then consensus at 8 and 16 seeds on one resolution inside the flat region; the gate is read there.
12. 2D UMAP picture with medoid quotes (`umap_medoids.py <dense>`): medoid chosen in embedding space, every community coloured (hues far apart for 2D neighbours), medoid = numbered star in the community colour, quotes in a side legend, no text on the map. Solid islands vs a diffuse middle is the visual form of the consensus ARI.
13. Out-of-sample assignment (`oos_cluster.py`): 50/50 split, two draws; arms = KMeans raw, UMAP-10d+KMeans, kNN vote of sample Leiden; score held-out pp-lift, ARI vs full-data consensus, draw-to-draw ARI. Compare at EQUAL k.
14. Cluster-at-query battery (`cluster_retrieval.py`): base ranking vs filter / boost at 3 weights / per-cluster cap, paired CIs; then the cross-view form (lexical base, dense cluster). Same-view arms are expected to be flat or negative; only the cross-view boost can pay.
15. Post-hoc vs stored grouping (`result_grouping.txt` recipe): cluster each query's top-N post hoc at k = stored clusters present; ARI between the two and within-result tag pair-precision for each. Decides which partition the result page uses.
16. Core/periphery check (`core_periphery.txt` recipe): per member cos to medoid and centroid; tag pair-precision lift for members with vs without a lex∩sem edge inside the community, and above vs below the one-sided centroid cut. Both should separate; if neither does, the community is a chain with no core and should not be displayed as one.
17. Partitioner alternatives at equal n (`median_clusters.py`, `maxent_clusters.py`): k-means, median/PCA trees, MMR-medoid cells, annealing vs the consensus-Leiden reference. Read tag lift, seed/draw stability and out-of-sample agreement together; lift alone favours more clusters and compact blobs.
10. kNN-edge cosine distribution vs the random-pair null (median, MAD, p99.9). Edges an order of magnitude above the null -> the index already did the significance test; do not prune.

---

## Preconditions / failure modes

- Needs a labeled or self-derived query battery of >=200; without it, only the typo battery and exact-BM25 recall are measurable.
- Subword saturation on tiny corpora makes vocab sweeps non-discriminating; report realized vocab.
- Alphabet completion is required for any capped tokenizer: characters seen only mid-word (digits, non-Latin script) otherwise encode to [UNK].
- Dense model unavailable -> lexical-only path is still valid; community labels then have no source (lexical fails R11 on short text).