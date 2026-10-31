---
name: unsupervised-entity-relations
description: >
  Derive entities, entity classes and relation classes from raw text with no parser, no NER and no pretrained
  model, using information-theoretic statistics: DIRT (Discovery of Inference Rules from Text; Lin & Pantel 2001)
  pattern similarity, NPMI (normalised pointwise mutual information), PPMI (positive pointwise mutual
  information), Dunning's G2 log-likelihood ratio, and Louvain over a co-mention graph. Records how a parser-free
  implementation departs from the paper (surface windows between anchored entities, G2 x NPMI gates, pair-set
  cosine), the acceptance test that failed, and a verified bibliography (Hasegawa 2004, Bouma 2009, C-value,
  TopMine, AutoPhrase). Use when you need entities or relation types from domain text without spaCy, when a
  tagger fails on part numbers, codes or jargon, or when choosing between PMI, NPMI, PPMI and a likelihood-ratio gate.
status: active
last_validated: 2026-10-04
validation_method: live run mixed-full-dual (2026-09-07); bibliography identifiers verified 2026-09-07
ported_from: 'F:\Documents\dev\graph\skills\unsupervised-entity-relations\SKILL.md'
---
# Unsupervised entity and relation extraction

*Terms: DIRT = Discovery of Inference Rules from Text; PMI = pointwise mutual information; NPMI = normalised PMI (Bouma 2009); PPMI = positive PMI (PMI clipped at zero); G² = Dunning's log-likelihood ratio.*

*Keywords for search: DIRT · Lin & Pantel · NPMI · Bouma · Dunning G² ·
Hasegawa · co-mention Louvain · parser-free relation discovery ·
distributional hypothesis.*

**Scope.** Starts from DIRT (the canonical method, below), then records what
a parser-free implementation looks like on domain data — entity classes from
co-mention NPMI + Louvain, relation classes from shared entity-pair
populations — with a verified bibliography at the end. Implementation lives
in `F:\Documents\dev\graph` (spec §6.20, §6.24).

---

## 📐 Core Methodology of DIRT
The core methodology of DIRT (Discovery of Inference Rules from Text) relies on an extension of Harris’s Distributional Hypothesis. While the original hypothesis states that words appearing in similar contexts have similar meanings, DIRT extends this to paths in a dependency graph: paths that connect similar pairs of words tend to have similar meanings.
The implementation pipeline is structured into three sequential phases: dependency path extraction, mutual information calculation, and path similarity scoring.
------------------------------
## Phase 1: Dependency Path Extraction
DIRT converts unstructured text sentences into structured paths using a dependency parser. A path represents the grammatical relationship between two noun concepts (anchored at Slot X and Slot Y).

   1. Sentence Parsing: The sentence is parsed into a directed graph where nodes are words and edges represent grammatical relations.
   2. Path Identification: The algorithm extracts the path between two nouns by traversing the tree. The words at the endpoints are stripped out and replaced by variables X and Y.
   3. Data Representation: The system stores these extractions as statistical blocks termed triples:
   $$\text{Triple} = (\text{path}, \text{slot}, \text{filler})$$ 
   * Example sentence: "The treatment cured the disease."
      * Extracted path: X ← subj ← cure → obj → Y
      * Resulting triples: (path, Slot X, treatment) and (path, Slot Y, disease).
   
------------------------------
## Phase 2: Quantifying Association via Mutual Information (MI)
To ensure the algorithm ignores trivial or overly generic word combinations, DIRT uses Pointwise Mutual Information (PMI). PMI measures how much more frequently a specific filler word appears in a path's slot compared to random chance.
For a given path p, a slot s (which can be X or Y), and a filler word f, the mutual information I(p, s, f) is calculated using the following probability ratio:
$$I(p, s, f) = \log \frac{P(p, s, f)}{P(s) \cdot P(p \vert{} s) \cdot P(f \vert{} s)}$$ 
By substituting frequency counts (c) from the corpus, the operational formula becomes:
$$I(p, s, f) = \log \frac{c(p, s, f) \times c(s, \ast, \ast)}{c(p, s, \ast) \times c(\ast, s, f)}$$ 
Where:

* c(p, s, f) is the frequency of filler f in slot s of path p.
* $c(p, s, \ast)$ is the total frequency of all fillers in slot s of path p.
* $c(\ast, s, f)$ is the total frequency of filler f across all paths containing slot s.
* $c(s, \ast, \ast)$ is the global count of all path-slot-filler combinations.

A positive I(p, s, f) value means the filler is highly characteristic of that specific path relation.
------------------------------
## Phase 3: Path Similarity Scoring
The final phase compares two distinct paths, p₁ and p₂, to see if they are semantically equivalent. DIRT uses a modified version of Lin’s Information-Theoretic Similarity Measure.
The similarity of a single slot s between two paths is calculated by intersecting the filler words they share ($T(p_1, s) \cap T(p_2, s)$):
$$\text{Sim}_s(p_1, p_2) = \frac{\sum_{f \in T(p_1, s) \cap T(p_2, s)} \left[ I(p_1, s, f) + I(p_2, s, f) \right]}{\sum_{f \in T(p_1, s)} I(p_1, s, f) + \sum_{f \in T(p_2, s)} I(p_2, s, f)}$$ 
## Total Path Similarity
Because a path contains two separate endpoints, the overall semantic similarity score between path p₁ and path p₂ is computed as the geometric mean of the similarities of their individual slots (X and Y):
$$\text{Sim}(p_1, p_2) = \sqrt{\text{Sim}_X(p_1, p_2) \times \text{Sim}_Y(p_1, p_2)}$$ 
If Sim(p₁, p₂) passes a predefined threshold, DIRT outputs the pair as a valid inference rule (p₁ ≈ p₂).



------------------------------
## Implementation notes — chunkgraph (F:\Documents\dev\graph, 2026-09-07)

What we actually shipped, and where it departs from the paper. Spec:
`.spec/specs/graph-explorer/design.md` 6.20 (E10-E14, relations v0) and
6.24 (E15-E19, classes). Live run: `mixed-full-dual`, 10,830 chunks.

### Deviation 1 — no dependency parser; sentence-window connectors

Phase 1 above needs a parser. We deliberately avoided pretrained models
(operator constraint: "avoid heavy deep learning libraries that are
pretrained... the more unsupervised the better"), so the *path* is replaced
by the **literal token span between two vocabulary-anchored entities inside
one sentence**, capped at 4 tokens.

    X ← subj ← cure → obj → Y        (DIRT: parsed path)
    X  "of the"  Y                    (ours: surface connector span)

Two-tier label per extraction: `connector` = the exact surface string,
`template` = its closed-class signature (`w` = one content word elided, so
`played a key role` → template `a w`). Genitives are unified by rule at
extraction time: `X's Y` and `Y of X` both normalize to one direction-fixed
`(src, dst, GEN)` row. Cost of the deviation: no argument roles, no
long-distance dependencies. Benefit: zero model weights, ~12 min over
918,707 sentences.

### Deviation 2 — association measured with Dunning G² × NPMI, not MI alone

Phase 2's PMI is unnormalized and rewards rare events. We gate each
candidate relation on **two independent floors**:

* **Dunning log-likelihood ratio (G²)** ≥ 10.83 (χ², p<0.001) — the same
  ruler the phrase stage uses. Answers "is this pairing more than chance?"
* **Sentence-level NPMI** — PMI normalized to [-1, 1] by `-log p(x,y)`, so a
  rare pair and a frequent pair are directly comparable. Raw PMI is not;
  this is the fix for PMI's rare-event bias, which the paper's threshold
  handles only implicitly.
* Support floor `n ≥ 3`.

**Where NPMI does the same job on edges.** The identical measure carries the
*entity co-mention graph* (E15): two entities sharing a chunk get an edge
weighted by NPMI over co-mention counts, floored at 3 shared chunks. So one
normalization serves both layers — NPMI for "do these two belong together"
(entity edges, relation plausibility), G² for "is this pattern significant"
(phrase merging, relation gating). Live: 2,653,691 co-mention pairs →
16,073 edges surviving the floors → Louvain (seed 7) → **4,708 entities
classed, 27s**.

### Deviation 3 — pair-set cosine instead of Lin's MI-weighted similarity

Phase 3's `Sim_s` weights each shared filler by its MI in both paths, then
takes the geometric mean over slots X and Y. We use the **unweighted set
cosine over the (src, dst) pairs each template joins**:

    sim(p1, p2) = |A ∩ B| / sqrt(|A| · |B|)      A, B = pair sets

This is the paper's structure with the MI weights set to 1, and it treats
the pair as one joint object rather than two independently-scored slots.
Justification: our "fillers" are already canonical-id entities (NPMI-
collapsed), and the dominant template `''` holds ~96,839 pairs — Jaccard is
swamped by it, cosine is not. Connected components (union-find, no seed)
over the thresholded similarity graph mint the classes. Live: **11,328
templates → 396 similarity edges → 68s**, merging e.g.

    class 'the' ← [the, the w, the w w, the w w w]
    class 'in'  ← [in, on]
    class 'a'   ← [a, an w, a w, a w and w, a w w]

### The acceptance test we set, and failed

Pre-registered check: re-split the hand-built GEN rule by connector and see
whether DIRT **rediscovers** it — do `'s`, `of`, `of the` co-class from
distribution alone? **No.** `all GEN/* co-classed: False`; each landed in
its own singleton among 864 distinct `GEN/<connector>` keys.

Diagnosed, not tuned away: `connector` stores the raw surface span
(`GEN/of which was the`), so one genitive fragments into hundreds of keys,
each below the shared-pair floor. The fix is **canonicalizing connectors
before similarity** (collapse the span to its closed-class skeleton, which
the `template` field already does — the gen-check should run over templates,
not raw connectors), not lowering the threshold. Recorded as an open E16
defect rather than a passing number.

### Measured on a small one-topic corpus (RL_V2, 2026-10-08)

Same derivation (`entity_derive` + `relations`) on 119 chunks of one textbook family; verdicts in RL_V2 `dispositions.md`.

* **Vector and co-mention neighbours differ.** Top-5 Jaccard 0.036 against a 0.008 chance baseline: `Gini` co-mentions
  `[impurity, splitting, node]`, its vector neighbours are `[Gini impurity, Expected Gini, entropy]`. Keep them as separate edge
  types; the vector signal is "same kind", the co-mention signal is "same topic".
* **The guards assume a mixed corpus.** The closed-class cut and residual-IDF floor scored "random forest" and "decision tree" 0
  (first token in 44% of chunks; residual IDF -0.05). Defaults found 4 of 16 skill names, relaxed guards 10 of 16. Print the guard
  features for known domain terms before calling a term absent.
* **No class passed the seed-ARI >= 0.8 gate** (best 0.73 on the subset, 0.785 on all 1,330 chunks), so class naming never ran.
  The gate stays at 0.8.
* **The genitive test is circular on templates.** Candidates already write one `GEN` key, so template mode "merges" genitives by
  construction; only the raw-connector side is informative (9 keys, 9 classes, the original failure).
* **Relation classes need scale:** 34 similarity edges over 2,275 templates; 0 on the 66-chunk family corpus.
* **Follow-up (same day): type terms from co-mention communities, not context vectors.** On the whole 29-skill family (66
  paragraph-packed chunks, code fences stripped, default guards) Leiden over the NPMI edges gave seed-ARI 0.796 to 0.894, accepted at
  res 4.0 with 53 classes; the vector route (`type_entities`) failed the gate on every corpus. But purity on a 4-group battery was
  2 of 4 at >= 0.7 (3 of 4 above a shuffled baseline), and the same method fell to 0.19 to 0.64 with relaxed guards.
* **Scale did not rescue the vector route (8 families, ~147k tokens, 12x the single family).** Best seed-ARI 0.729 (default
  guards) and 0.747 (relaxed) against 0.768 at 12k tokens; no partition accepted. Co-mention Leiden at that scale passes the gate
  (108 classes, connected-only 0.810) but is topic-level: 9 classes of 48 to 197 terms, and all four battery term groups
  (impurity measures, boosting, bagging, hyperparameters) land in one 167-term class, so purity 1.00 there is a blob, not a
  result. Check that groups land in DIFFERENT classes, not only that each group is pure.
* **DIRT does not rediscover genitives by distribution at that scale:** 47 raw `GEN/<connector>` keys gave 47 classes with 2
  similarity edges over 7,857 templates. The template-key comparison is circular (the candidate step writes one `GEN` key); the
  valid test drops the hand-written rule: `of` vs `of the` pair-set cosine 0.037 (shared pairs 4), `'s` (pairs reversed) vs
  `of the` 0.041, unrelated controls `in` vs `and` 0.021. Entity pairs rarely repeat in ~28k candidate events; the original run
  that this method came from used 918,707 sentences. Do not expect relation classes below roughly that order of magnitude.
* **Why the vector route fails the gate (null-controlled):** context-PPMI vectors beat a column-shuffled null by only 0.10 to 0.19
  seed-ARI at every resolution above 2 classes (0.305/0.437/0.505 vs 0.115/0.266/0.405); neighbour count k (5/15/40) and
  `min_occ` (3/5) change nothing; the only seed-stable fine partition is spelling-only (0.789), which is surface form, not type.
* **Two measurement traps in the class gate:** `type_entities` takes the finest passing resolution, and a ONE-class partition
  passes at ARI 1.0; and ARI over a graph with isolated nodes is inflated because they are singletons in every seed. Report
  connected-only ARI and require more than one class.

### What this says about the paper

DIRT's real content is Phase 3's insight — *two patterns mean the same thing
when they connect the same populations* — and that survives every deviation
above. Phases 1 and 2 are implementation choices of their era: a parser
because 2001 had no cheap alternative, MI because NPMI/G² weren't the
defaults yet. Swapping both and keeping Phase 3 still produced sensible
merges, which is the useful finding.

------------------------------
## References — what cites what

DIRT is one paper; the measures we substituted for its Phases 1-2 have their
own canon. Mapping each piece of our pipeline to its source:

| Our step | Paper |
|---|---|
| PMI (the ancestor) | Church & Hanks 1990, *Word Association Norms, Mutual Information, and Lexicography*, Computational Linguistics 16(1) |
| **NPMI** — pmi / -log p(x,y), the [-1,1] normalization we use for entity edges AND relation plausibility | **Bouma 2009, *Normalized (Pointwise) Mutual Information in Collocation Extraction*, GSCL** |
| Dunning G² gate (LLR >= 10.83) | Dunning 1993, *Accurate Methods for the Statistics of Surprise and Coincidence*, Computational Linguistics 19(1) |
| Louvain over the co-mention graph | Blondel, Guillaume, Lambiotte & Lefebvre 2008, *Fast unfolding of communities in large networks*, J. Stat. Mech. |
| Phrase merge pre-BM25 (gensim Phraser) | Mikolov et al. 2013, *Distributed Representations of Words and Phrases* (the phrase score); gensim implements the NPMI variant |
| Pattern similarity via shared argument pairs | Lin & Pantel 2001, *DIRT — Discovery of Inference Rules from Text*, KDD |

### The parser problem, and the paper that actually matches us

DIRT's Phase 1 assumes a dependency parser and **nouns** at both slots
(Lin's Minipar). That assumption fails on domain corpora: a part number, a
SKU, an alloy spec, an error code is not a noun any tagger will find, and we
refuse to call spaCy at all (no pretrained models in the deterministic path).

The paper that matches what we built is **Hasegawa, Sekine & Grishman 2004,
*Discovering Relations among Named Entities from Large Corpora*, ACL**: they
take the **bag of context words BETWEEN two entities** — a surface window,
no parse — and cluster those context vectors by cosine similarity to
discover relation types, fully unsupervised. Our sentence-window connector
plus pair-set cosine is that method with the roles swapped (we cluster
patterns by shared pairs rather than pairs by shared context; the duality is
the same distributional bet).

**For entity discovery without POS tags**, the relevant lineage is
statistical term extraction, not tagging:

* **Frantzi & Ananiadou 1998/2000 — C-value / NC-value.** Multiword term
  extraction by frequency + nestedness, built for medical corpora, no
  tagger required. The closest published answer to "how do I find part
  numbers as terms".
* **El-Kishky et al. 2014 — TopMine**; **Shang et al. 2018 — AutoPhrase.**
  Phrase mining from raw corpora by statistics; AutoPhrase adds distant
  supervision from a knowledge base, TopMine does not.
* Our own vocabulary stage (`salient_grams.select_vocab_unified`: df band +
  keyness + anomaly + spline + MMR) is in this family — corpus statistics
  selecting the term inventory, with no notion of part of speech anywhere.

**The claim this supports:** DIRT's durable content is the distributional
bet in Phase 3 — *patterns that connect the same populations mean the same
thing*. Phases 1-2 are era-specific implementation (a parser because 2001
had no cheap alternative; MI because NPMI/G² were not yet defaults).
Replacing the parser with surface windows (Hasegawa) and MI with NPMI/G²
(Bouma/Dunning) keeps the bet and drops the assumptions domain data breaks.

### Bibliography (identifiers verified 2026-09-07)

Every entry below was resolved against the live source, not recalled. One
guess was wrong on the first pass and is recorded so the error does not
repeat: `aclanthology.org/P04-1052` is Siddharthan & Copestake, *Generating
Referring Expressions in Open Domains* — the Hasegawa paper is **P04-1053**.

1. **Lin, D. & Pantel, P. (2001).** DIRT — Discovery of Inference Rules from
   Text. *KDD '01*.
   <http://www.cs.columbia.edu/~kapil/documents/candidacy_papers/lin01.pdf>
   — the pattern-similarity bet (Phase 3) our relation classes rest on.

2. **Hasegawa, T., Sekine, S. & Grishman, R. (2004).** Discovering Relations
   among Named Entities from Large Corpora. *ACL-04*, pp. 415–422, Barcelona.
   <https://aclanthology.org/P04-1053/>
   — **the parser-free match to what we built**: context words BETWEEN two
   entities, clustered by similarity, no dependency parse, no POS assumption.

3. **Bouma, G. (2009).** Normalized (Pointwise) Mutual Information in
   Collocation Extraction. In *From Form to Meaning: Processing Texts
   Automatically — Proceedings of the Biennial GSCL Conference 2009*,
   Tübingen, pp. 31–40.
   <https://www.semanticscholar.org/paper/15218d9c029cbb903ae7c729b2c644c24994c201>
   — **the NPMI citation**: pmi / -log p(x,y), interpretable on [-1,1] and
   far less frequency-sensitive than raw PMI. Carries our entity co-mention
   edges and relation plausibility. (No stable open PDF; GSCL proceedings.)

4. **Church, K. W. & Hanks, P. (1990).** Word Association Norms, Mutual
   Information, and Lexicography. *Computational Linguistics* 16(1), 22–29.
   <https://aclanthology.org/J90-1003/> — PMI's origin, and the source of the
   rare-event bias NPMI exists to fix.

5. **Dunning, T. (1993).** Accurate Methods for the Statistics of Surprise
   and Coincidence. *Computational Linguistics* 19(1).
   <https://aclanthology.org/J93-1003/> — the G² gate (LLR >= 10.83) on
   phrase merges and relation candidates.

6. **Blondel, V. D., Guillaume, J.-L., Lambiotte, R. & Lefebvre, E. (2008).**
   Fast unfolding of communities in large networks. *J. Stat. Mech.* (2008)
   P10008. <https://arxiv.org/abs/0803.0476> — Louvain, run over the NPMI
   co-mention graph to mint entity classes.

7. **Mikolov, T., Sutskever, I., Chen, K., Corrado, G. & Dean, J. (2013).**
   Distributed Representations of Words and Phrases and their
   Compositionality. <https://arxiv.org/abs/1310.4546> — the phrase score
   gensim's Phraser implements (NPMI variant) in our PHRASE stage.

8. **Frantzi, K. & Ananiadou, S. (1998/2000).** The C-value/NC-value method
   of automatic recognition for multi-word terms (*ECDL '98*); extended as
   *Automatic recognition of multi-word terms*, Int. J. on Digital Libraries
   3(2), 2000. — term inventory by frequency + nestedness, built for medical
   corpora, **no tagger**: the published answer to "find part numbers".

9. **El-Kishky, A., Song, Y., Wang, C., Voss, C. & Han, J. (2014).**
   Scalable Topical Phrase Mining from Text Corpora. *PVLDB* 8(3), 305–316.
   <https://arxiv.org/abs/1406.6312> — TopMine.

10. **Shang, J., Liu, J., Jiang, M., Ren, X., Voss, C. R. & Han, J. (2017).**
    Automated Phrase Mining from Massive Text Corpora.
    <https://arxiv.org/abs/1702.04457> — AutoPhrase (distant supervision on
    top of corpus statistics; the statistics half is the reusable part).