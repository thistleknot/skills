"""Extract salient and differentiating tags as ts_vector-canonical lexemes.

Single entry point: pass a list of strings, get back one tuple per string:
(salient_terms, differentiating_terms). Text is lexed through Postgres
to_tsvector('english', ...) BEFORE any term selection runs, so every returned
term is an exact `content_tsv` lexeme root (Snowball English stem + stopword
removal) -- the same roots the retriever's tsvector-BM25 lane matches against.

Collapsed from three files (ts_lexer.py, bm25_salient_terms.py, mmr-dst.py)
into one -- same three responsibilities (lex / score+MMR / entry point), no
behavior change, kept in this order as clearly delimited sections instead of
separate importable modules.

BM25 with no query = treat each term in the doc as its own 1-term query.
That's it.

    relevance(t, D) = idf(t) * tf_norm(t, D)        # one scalar per term, no query
       idf     = log((N - df + 0.5)/(df + 0.5) + 1)  # corpus rarity
       tf_norm = freq*(k1+1) / (freq + k1*(1 - b + b*|D|/avgdl))  # saturated, length-normed

Normal BM25 sums this over the query terms. Query-free, you just don't sum --
you keep the per-term score as each term's weight. Same as TF-IDF term
weighting, but with tf saturation (k1) and length norm (b).

That per-term scalar is the relevance MMR consumes:

    MMR:  pick term maximizing  lam*relevance(t) - (1 - lam)*max_sim(t, already_picked)

MMR never needed a query -- it needs (relevance, similarity). In retrieval MMR,
relevance = query-similarity. Here, relevance = BM25 self-weight. Same operator,
query swapped out for "how much this term defines this doc." _build_candidates
computes exactly that scalar -> _mmr_select diversifies over it: that IS the
salient lane. (The differentiating lane reuses the tf_norm half of the same
scalar as relevance -- see below.)

Two lanes = two MMR diversity axes (this is the settled design):
    salient(D)        = MMR WITHIN the string. Relevance = BM25 score of the
                        term in D; redundancy = Jaccard vs terms already chosen
                        for D. A diverse summary of what D is about. NOT
                        contrastive: 'regress' can be salient in every
                        regression doc.
    differentiating(D)= MMR ACROSS strings. Relevance = tf_norm ONLY (in-doc
                        frequency, idf-free); redundancy = the fraction of OTHER
                        docs for which the term is salient. Terms strong in D
                        and absent elsewhere -- what sets D apart.

Why the across-string MMR is a single-pass re-rank, not greedy iteration:
    In standard MMR the redundancy penalty depends on what has already been
    chosen. Here the differentiating penalty (corpus salient-frequency) is
    FIXED per term -- it does not change as we pick more terms for D. Greedy
    MMR with a selection-independent penalty is mathematically identical to
    sorting once by lam * relevance - (1 - lam) * penalty. So salient sets are
    computed first (pass 1), the corpus salient-frequency derived from them,
    then each doc's candidates re-ranked by that closed form (pass 2). No loss
    vs greedy.

Length normalization (avg_dl):
    BM25's length factor uses document length in LEXEMES (Solr/Lucene field
    length = token count), NOT the number of n-gram candidates. n-grams are
    candidates; len(token_list) is the field length.

Pipeline (Behavioral):
    1. Lex every input text through Postgres to_tsvector (lex_texts): ordered
       lexeme stream, stopwords dropped, repeats kept.
    2. tag_token_lists runs the two lanes above over one shared per-text BM25
       candidate pool, in two passes: salient sets first, then differentiating
       using the corpus salient-frequency derived from them. Neither lane is
       drawn from the other's OUTPUT (no cascade); they share the candidate
       POOL and differ only in the diversity axis.

Require (preconditions):
    - texts is a list of strings.
    - The langchain_postgres container is up (lex_texts needs to_tsvector).

Guarantee (postconditions):
    - len(result) == len(texts), index-aligned with the input;
    - result[i] == (salient, differentiating), both lists of lexeme terms in
      selection order;
    - input texts are not modified.

Failure modes:
    - a text yielding no candidates produces ([], []);
    - lexing is English-only (Postgres 'english' config);
    - Postgres unreachable raises (fail fast -- DB alignment is the point).

Lessons learned (do not re-litigate -- these cost real cycles):
    - HAPAX NOISE. An idf-rarity differentiating lane rewards df=1 fragments
      ('wherea lasso', 'n especi') that carry no routing signal, because a
      corpus hapax has maximal idf. The fix is NOT min_df hacking: make the
      differentiating lane's RELEVANCE be tf_norm (idf-free) so a term seen
      once has near-zero relevance, and put ALL the rarity pressure in the
      across-string redundancy penalty. Hapax then self-eliminates.
    - IDF INVERSION. Central concepts appear in many docs -> high df -> low idf
      -> an idf-ranked lane BURIES them. 'regress'/'ridg' must surface via
      in-doc frequency (tf_norm), with rarity applied as a cross-doc penalty,
      not as an idf multiplier on relevance.
    - BM25 SCORE INCLUDES IDF. Do not use the BM25 score as the differentiating
      lane's relevance -- idf in the score re-boosts hapax. tf_norm only.
    - ACROSS-STRING MMR IS A CLOSED-FORM RE-RANK. The cross-doc penalty is
      selection-independent, so greedy MMR collapses to one sort by
      lam*rel - (1-lam)*penalty. No greedy loop needed for that lane.
    - SCOPE-LOCK ON BM25. The only sanctioned BM25 changes are (1) stemming via
      Postgres to_tsvector('english') and (2) avg_dl = document length in
      lexemes (Solr length norm). No invented formulas.
    - n_max=1 by default. At unigrams the differentiating across-string Jaccard
      degenerates to "salient here, not salient there", which is exactly the
      contrast we want; bigrams reintroduce fragment noise.
"""

import os
from collections import Counter
from math import log

import psycopg

# ---------------------------------------------------------------------------
# Section 1: lexing (formerly ts_lexer.py)
#
# Lex text through Postgres `to_tsvector('english', ...)` so tags share the
# exact lexeme roots stored in the retriever's `content_tsv` column. NLTK's
# SnowballStemmer does not drop stopwords the way Postgres does, so tokenizing
# through the live Postgres analyzer is what keeps tags DB-aligned.
# ---------------------------------------------------------------------------

DSN = os.environ.get(
    "MMR_DST_PG_DSN", "postgresql://langchain:langchain@localhost:5432/langchain"
)


def lex_texts(texts, dsn=DSN, connect_timeout=10):
    """Return the ordered Postgres lexeme stream for each input text.

    Preconditions:
        texts is a list of strings; Postgres reachable at dsn.

    Guarantees:
        len(result) == len(texts), index-aligned; each result[i] is a list of
        lexemes (with repeats) in position order; stopwords removed by the
        'english' config; identical stemming to content_tsv.

    Failure modes:
        Raises on connection error (fail fast). A text with no lexemes -> [].
    """
    results = []
    with psycopg.connect(dsn, connect_timeout=connect_timeout) as conn:
        with conn.cursor() as cur:
            for text in texts:
                if not text or not text.strip():
                    results.append([])
                    continue
                cur.execute(
                    "SELECT lexeme, positions "
                    "FROM unnest(to_tsvector('english', %s))",
                    (text,),
                )
                positioned = []
                for lexeme, positions in cur.fetchall():
                    for pos in (positions or []):
                        positioned.append((pos, lexeme))
                positioned.sort()
                results.append([lexeme for _, lexeme in positioned])
    return results


# ---------------------------------------------------------------------------
# Section 2: BM25 scoring + two-lane MMR (formerly bm25_salient_terms.py)
# ---------------------------------------------------------------------------

def _ngrams(tokens, n_max):
    """Return all 1..n_max contiguous token grams as space-joined strings."""
    grams = []
    for n in range(1, n_max + 1):
        for i in range(len(tokens) - n + 1):
            grams.append(" ".join(tokens[i:i + n]))
    return grams


def _similarity(left, right):
    """Jaccard token overlap between two space-joined (stemmed) terms."""
    left_tokens = set(left.split())
    right_tokens = set(right.split())
    if not left_tokens or not right_tokens:
        return 0.0
    return len(left_tokens & right_tokens) / len(left_tokens | right_tokens)


def _idf(term_df, text_count):
    """BM25 (Lucene-style, +1-corrected) inverse document frequency."""
    return log((text_count - term_df + 0.5) / (term_df + 0.5) + 1.0)


def _mmr_select(ranked, top_n, lam):
    """MMR-select up to top_n terms from a relevance-ranked candidate list.

    This is the WITHIN-string selector used by the salient lane: the redundancy
    of a candidate is its max Jaccard overlap with terms ALREADY chosen for the
    same document.

    Preconditions:
        ranked is a list of (term, relevance) pairs; 0.0 <= lam <= 1.0.

    Guarantees:
        Returns a list of terms (<= top_n) chosen by
        lam * relevance - (1 - lam) * max Jaccard-redundancy vs already chosen.
        Deterministic given a stable input order.
    """
    selected = []
    remaining = list(ranked)
    while remaining and len(selected) < top_n:
        best = None
        best_mmr = float("-inf")
        for term, relevance in remaining:
            redundancy = max(
                (_similarity(term, chosen) for chosen in selected),
                default=0.0,
            )
            mmr = lam * relevance - (1.0 - lam) * redundancy
            if mmr > best_mmr:
                best_mmr = mmr
                best = (term, relevance)
        selected.append(best[0])
        remaining.remove(best)
    return selected


def _build_candidates(token_lists, min_df, n_max, k1, b):
    """Score every candidate gram per text by BM25; also expose tf_norm.

    Preconditions:
        token_lists is a list of lexeme lists.

    Guarantees:
        Returns (per_text_scores, document_frequency, text_count):
          per_text_scores[i] = list of (term, bm25_score, tf_norm) for text i,
            where bm25_score = idf * tf_norm and tf_norm is the length-normalized
            term-frequency factor alone (idf-free);
          document_frequency = Counter of gram -> #texts containing it;
          BM25 length norm uses len(token_lists[i]) (lexeme field length).
    """
    doc_grams = [_ngrams(tokens, n_max) for tokens in token_lists]
    text_count = len(token_lists)
    if text_count == 0:
        return [], Counter(), 0

    # avg_dl = mean document length in LEXEMES (Solr field length), not grams.
    total_len = sum(len(tokens) for tokens in token_lists)
    avg_len = total_len / text_count if text_count else 0.0

    document_frequency = Counter()
    for grams in doc_grams:
        for term in set(grams):
            document_frequency[term] += 1

    per_text_scores = []
    for tokens, grams in zip(token_lists, doc_grams):
        term_frequency = Counter(grams)
        doc_len = len(tokens)  # lexeme field length, the avg_dl unit
        scores = []
        for term, freq in term_frequency.items():
            if document_frequency[term] < min_df:
                continue
            if avg_len > 0:
                tf_norm = freq * (k1 + 1) / (
                    freq + k1 * (1 - b + b * doc_len / avg_len)
                )
            else:
                tf_norm = 0.0
            idf = _idf(document_frequency[term], text_count)
            scores.append((term, idf * tf_norm, tf_norm))
        per_text_scores.append(scores)

    return per_text_scores, document_frequency, text_count


def tag_token_lists(token_lists, salient_top_n=8, diff_top_n=8, lam=0.7,
                    min_df=1, n_max=1, k1=1.5, b=0.75, pool=50):
    """Salient (within-string MMR) + differentiating (across-string MMR) lanes.

    Preconditions:
        token_lists is a list of Postgres-lexed lexeme lists.
        0.0 <= lam <= 1.0.

    Guarantees:
        Returns one (salient, differentiating) tuple per text, index-aligned.
        salient(D)        = MMR WITHIN D: BM25-score relevance, redundancy =
                            Jaccard vs terms already chosen for D.
        differentiating(D)= MMR ACROSS strings: tf_norm relevance, redundancy =
                            fraction of OTHER docs for which the term is salient.
                            Computed as a closed-form re-rank (see module doc).
        Two passes: salient sets first, then differentiating using the corpus
        salient-frequency derived from them.

    Failure modes:
        A text with no candidates -> ([], []). Empty corpus -> [].
    """
    if not 0.0 <= lam <= 1.0:
        raise ValueError("lam must be between 0.0 and 1.0")

    per_text_scores, document_frequency, text_count = _build_candidates(
        token_lists, min_df, n_max, k1, b
    )
    if text_count == 0:
        return []

    # PASS 1 -- salient (within-string MMR) for every document.
    salient_sets = []
    for scores in per_text_scores:
        if not scores:
            salient_sets.append([])
            continue
        by_score = sorted(scores, key=lambda row: -row[1])[:pool]
        salient = _mmr_select(
            [(term, bm25) for term, bm25, _ in by_score], salient_top_n, lam
        )
        salient_sets.append(salient)

    # Corpus salient-frequency: #docs for which each term is salient. This is
    # the ACROSS-string signal the differentiating lane penalizes against.
    salient_df = Counter()
    for salient in salient_sets:
        for term in set(salient):
            salient_df[term] += 1

    others = text_count - 1  # docs other than the current one

    # PASS 2 -- differentiating (across-string MMR) for every document.
    results = []
    for scores, salient in zip(per_text_scores, salient_sets):
        if not scores:
            results.append(([], []))
            continue

        max_tf = max(tf_norm for _, _, tf_norm in scores) or 1.0
        own = set(salient)
        ranked = []
        for term, _bm25, tf_norm in scores:
            relevance = tf_norm / max_tf  # in-doc salience, idf-free, [0, 1]
            elsewhere = salient_df.get(term, 0) - (1 if term in own else 0)
            redundancy = (elsewhere / others) if others > 0 else 0.0  # [0, 1]
            ranked.append((term, lam * relevance - (1.0 - lam) * redundancy))
        ranked.sort(key=lambda pair: -pair[1])
        differentiating = [term for term, _ in ranked[:diff_top_n]]

        results.append((salient, differentiating))

    return results


# ---------------------------------------------------------------------------
# Section 3: public entry point (formerly mmr-dst.py)
# ---------------------------------------------------------------------------

def tag_texts(texts, salient_top_n=8, diff_top_n=8, lam=0.7, min_df=1,
              n_max=1, k1=1.5, b=0.75, pool=50):
    """Return (salient, differentiating) lexeme term lists per text.

    Preconditions:
        texts is a list of strings; Postgres reachable for lexing.

    Guarantees:
        Returns a list of (salient_terms, differentiating_terms) tuples,
        one per input string, index-aligned with texts. All terms are exact
        Postgres to_tsvector('english') lexemes. salient = within-string MMR;
        differentiating = across-string MMR (see module doc).

    Failure modes:
        Empty candidate pools yield ([], []) for that text. Postgres
        unreachable raises.
    """
    token_lists = lex_texts(texts)
    return tag_token_lists(
        token_lists,
        salient_top_n=salient_top_n,
        diff_top_n=diff_top_n,
        lam=lam,
        min_df=min_df,
        n_max=n_max,
        k1=k1,
        b=b,
        pool=pool,
    )


if __name__ == "__main__":
    sample = [
        "Gradient boosting builds trees sequentially on residuals.",
        "Random forests average many decorrelated decision trees.",
        "K means clustering partitions points around centroids.",
    ]

    for salient, differentiating in tag_texts(sample):
        print(salient, differentiating)
