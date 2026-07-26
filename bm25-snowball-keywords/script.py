"""BM25 salient terms per section, plus a query-expansion primer vocabulary.

Purpose:
    (1) For every string in a corpus, rank its terms (unigrams + bigram
    collocations) by their BM25 self-retrieval contribution — the terms
    that best anchor that string against the rest of the corpus.
    (2) Collapse those per-section tags into one deduped vocabulary
    ("primer") suitable for priming a query-expansion model: the model
    picks terms off this list, and by construction each term BM25-retrieves
    the section(s) it was extracted from.

Require (preconditions):
    - strings: non-empty list of non-empty texts; must be the full
      comparison set (df/avgdl are computed from it).
Guarantee (postconditions):
    - salient_terms: one ranked list per input string, same order; every
      returned term's Snowball stem occurs in its source string (the
      displayed surface form is the stem's most frequent corpus-wide
      spelling, which may differ from the section's local variant).
    - expansion_primer: deduped term -> sorted section-id list, covering
      exactly the union of per-section top-N tags.
Failure modes:
    - all-stopword strings yield empty tag lists;
    - N == 1 corpora make idf degenerate (no contrast);
    - bigrams never crossing a stopword boundary is a heuristic — noun
      phrases with interior stopwords ("bag of words") are not captured.
"""

import math
import re
from collections import Counter, defaultdict

import snowballstemmer

_STEM = snowballstemmer.stemmer("english")

STOPWORDS = frozenset("""
a an and are as at be but by for from has have if in into is it its no not
of on or such that the their then there these they this to was were will
with which would can could should may might than each other more most some
using used use also when while over under between against
""".split())


def _words(text):
    """Raw lowercase token stream, order preserved (needed for bigrams)."""
    return re.findall(r"[a-z0-9][a-z0-9\-]+", text.lower())


def _keep(t):
    return t not in STOPWORDS and len(t) >= 3


def tokenize(text):
    """Terms for one doc: (stem, surface) pairs, unigrams + bigrams.

    Scoring space is Snowball stems (rank/ranks/ranking merge); the
    surface form rides along so output stays human/model-legible.
    Stopword and length filters apply to surface forms. A bigram is
    emitted only when both tokens are content words adjacent in the raw
    stream — cheap collocation candidates without a POS tagger.
    """
    raw = _words(text)
    stems = _STEM.stemWords(raw)
    pairs = [(s, w) for s, w in zip(stems, raw) if _keep(w)]
    pairs += [(f"{sa} {sb}", f"{wa} {wb}")
              for (sa, wa), (sb, wb) in zip(zip(stems, raw),
                                            zip(stems[1:], raw[1:]))
              if _keep(wa) and _keep(wb)]
    return pairs


def salient_terms(strings, top_n=10, k1=1.5, b=0.75, min_df=1):
    """Per string, terms ranked by BM25(term, string) against the corpus.

    score(t, d) = idf(t) * tf*(k1+1) / (tf + k1*(1 - b + b*|d|/avgdl))
    idf(t)      = log((N - df + 0.5)/(df + 0.5) + 1)

    idf carries the contrast against all other strings — no pairwise loop.
    Scoring runs over Snowball stems; each returned term is the stem's
    most frequent corpus-wide surface form. Raise min_df to 2+ to
    suppress typo/OCR junk on noisy corpora.

    Returns: list (parallel to strings) of [(surface_term, score), ...]
    descending.
    """
    docs = [tokenize(s) for s in strings]
    N = len(docs)
    avgdl = sum(len(d) for d in docs) / max(N, 1)
    df = Counter(t for d in docs for t in {stem for stem, _ in d})

    surface = defaultdict(Counter)  # stem -> surface form counts
    for d in docs:
        for stem, word in d:
            surface[stem][word] += 1
    display = {stem: c.most_common(1)[0][0] for stem, c in surface.items()}

    results = []
    for d in docs:
        dl = len(d)
        tf = Counter(stem for stem, _ in d)
        scored = []
        for t, f in tf.items():
            if df[t] < min_df:
                continue
            idf = math.log((N - df[t] + 0.5) / (df[t] + 0.5) + 1)
            sat = f * (k1 + 1) / (f + k1 * (1 - b + b * dl / avgdl))
            scored.append((display[t], idf * sat))
        scored.sort(key=lambda x: -x[1])
        results.append(scored[:top_n])
    return results


def expansion_primer(strings, top_n=10, labels=None, **kw):
    """Deduped vocabulary for priming a query-expansion model.

    labels: optional per-string names (e.g. markdown section titles);
    defaults to s0..sN. Returns: dict term -> sorted list of labels it
    anchors. Render with format_primer(); the label doubles as a routing
    hint (expansion output -> section).
    """
    labels = labels or [f"s{i}" for i in range(len(strings))]
    vocab = {}
    for i, ranked in enumerate(salient_terms(strings, top_n=top_n, **kw)):
        for t, _ in ranked:
            vocab.setdefault(t, set()).add(labels[i])
    return {t: sorted(ids) for t, ids in sorted(vocab.items())}


def format_primer(primer):
    """One line per term: 'term -> label1, label2'. Paste-ready block."""
    return "\n".join(f"{t} -> {', '.join(ids)}" for t, ids in primer.items())


_HEADER = re.compile(r"^(#{1,6})\s+(.*)$", re.MULTILINE)


def markdown_sections(md_text):
    """Split markdown into (title, text) sections.

    A section is a header line plus everything until the next header of
    any level. The header text is kept inside `text` too — header terms
    are strong anchors and should be scorable. Text before the first
    header becomes a ('_preamble', ...) section if non-blank.
    Failure mode: headers inside fenced code blocks are treated as real
    headers (no fence tracking).
    """
    sections = []
    matches = list(_HEADER.finditer(md_text))
    if not matches:
        return [("_document", md_text)] if md_text.strip() else []
    if md_text[: matches[0].start()].strip():
        sections.append(("_preamble", md_text[: matches[0].start()]))
    for m, nxt in zip(matches, matches[1:] + [None]):
        end = nxt.start() if nxt else len(md_text)
        sections.append((m.group(2).strip(), md_text[m.start():end]))
    return sections


def tag_markdown(md_texts, top_n=10, **kw):
    """Full pipeline: markdown docs -> per-section tags + primer.

    md_texts: list of markdown document strings. Sections across all
    docs form one corpus (df/avgdl are global). Returns
    (sections, tags, primer) where sections is [(title, text)], tags is
    parallel ranked term lists, primer is the deduped vocabulary.
    """
    sections = [s for md in md_texts for s in markdown_sections(md)]
    bodies = [text for _, text in sections]
    titles = [title for title, _ in sections]
    tags = salient_terms(bodies, top_n=top_n, **kw)
    primer = expansion_primer(bodies, top_n=top_n, labels=titles, **kw)
    return sections, tags, primer


if __name__ == "__main__":
    import sys

    if len(sys.argv) > 1:  # usage: python bm25_salient_terms.py *.md
        docs = [open(p, encoding="utf-8").read() for p in sys.argv[1:]]
    else:
        docs = [(
            "# Gradient Descent\n"
            "Gradient descent updates model weights by stepping along the "
            "negative gradient of the loss function. The learning rate "
            "controls the step size of each weight update. A small "
            "learning rate converges slowly.\n"
            "## Stochastic Variant\n"
            "Stochastic gradient descent estimates the gradient from a "
            "minibatch, trading gradient accuracy for faster updates and "
            "a regularizing noise in the weight trajectory.\n"
            "# BM25 Ranking\n"
            "BM25 ranks documents against a query using term frequency "
            "saturation and inverse document frequency computed over the "
            "corpus, normalized by document length.\n"
            "# Vector Search\n"
            "A vector database stores embeddings and answers nearest "
            "neighbor queries using approximate indexes such as HNSW.\n"
        )]

    sections, tags, primer = tag_markdown(docs, top_n=8)
    for (title, _), ranked in zip(sections, tags):
        print(f"[{title}] " + ", ".join(f"{t}:{s:.2f}" for t, s in ranked))
    print("\n--- primer ---")
    print(format_primer(primer))