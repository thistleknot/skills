"""Tag every skill .md in the corpus with salient + differentiating ts_vector
lexeme lists, one <skill>.tags.json per file.

Both lanes are corpus-relative (salient = BM25 within-string MMR;
differentiating = across-string MMR against the corpus salient-frequency), so
ALL skills are lexed and tagged in a single batch, then written back
index-aligned. Lexing routes through Postgres to_tsvector('english', ...) so
tags are the exact content_tsv roots the retriever matches.

Corpus location is NOT hardcoded: set MMR_DST_CORPUS to the folder containing
the *.md files (searched recursively). Falls back to this machine's known
corpus path for backward compatibility.

Run modes:
    python tag_corpus.py --gate      # battery only, no writes
    python tag_corpus.py --run       # gate, then full corpus write
"""

import sys
import json
import glob
import os

sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))
sys.stdout.reconfigure(encoding="utf-8")

from mmr_dst import lex_texts, tag_token_lists

CORPUS = os.environ.get(
    "MMR_DST_CORPUS",
    r"C:\Users\user\Documents\wiki\data science\stackskills\skills_master",
)

# Unambiguous Postgres 'english' stopwords for the leak check. Kept minimal:
# Postgres keeps many words a naive list would drop (e.g. "around"), so only
# assert on words that are definitely in its snowball_english stopword set.
_STOPWORDS = {"the", "is", "a", "an", "of", "to", "and", "on", "at", "in", "be"}


def tag_texts(texts):
    """Lex through Postgres then run the two independent BM25+MMR lanes."""
    token_lists = lex_texts(texts)
    return tag_token_lists(token_lists)


def gate():
    """3+ varied batteries: contract checks, not one memorized case.

    Key assertion (the decouple's proof): at least one differentiating-only
    lexeme (in diff, not in salient) appears across the corpus battery. Under
    the old cascade diff was a strict subset of salient, so this was
    impossible; under the current across-string lane it is expected whenever a
    document has any term that is NOT salient elsewhere.
    """
    # Paragraph-length texts: the candidate pool must exceed top_n so the two
    # lanes (within-string vs across-string MMR) can select different subsets.
    # One-sentence texts exhaust the pool and both lanes collapse to the same
    # set — a battery artifact, not a decouple failure.
    batteries = [
        [
            "Gradient boosting builds an additive ensemble of shallow "
            "decision trees fit sequentially on the residual errors of the "
            "running model. Each new tree corrects the gradient of the loss, "
            "and a learning rate shrinks its contribution to control "
            "overfitting and improve generalization on held out data.",
            "Random forests train many decorrelated decision trees on "
            "bootstrap samples and random feature subsets, then average their "
            "predictions to reduce variance. Bagging and feature subsampling "
            "make the ensemble robust while keeping each individual tree "
            "deep, high variance, and cheap to fit in parallel.",
            "K means clustering partitions observations into a fixed number "
            "of clusters by alternating assignment of points to the nearest "
            "centroid and recomputing each centroid as the mean of its "
            "assigned points. The objective minimizes within cluster squared "
            "distance and converges to a local optimum sensitive to "
            "initialization.",
            "Principal component analysis projects correlated features onto "
            "orthogonal axes ordered by explained variance, computed from the "
            "eigenvectors of the covariance matrix. Retaining the leading "
            "components reduces dimensionality while preserving most of the "
            "variance for downstream visualization and modeling.",
        ],
        [
            "Bayes theorem updates a prior distribution into a posterior by "
            "multiplying it with the likelihood of the observed evidence and "
            "normalizing. Bayesian inference propagates uncertainty through "
            "the posterior rather than reporting a single point estimate, "
            "trading computation for calibrated probabilistic predictions.",
            "Cross validation estimates out of sample generalization error by "
            "repeatedly holding out folds of the training data, fitting on the "
            "remainder, and averaging the validation scores. K fold and "
            "leave one out schemes trade bias against variance in the error "
            "estimate and guide hyperparameter selection without touching the "
            "test set.",
            "Ridge regression shrinks the coefficients of a linear model "
            "toward zero with an L2 penalty on their squared magnitude, "
            "trading a little bias for a large reduction in variance under "
            "multicollinearity. The penalty strength is a regularization "
            "hyperparameter tuned by cross validation.",
        ],
        [
            "Convolutional networks share a small kernel of weights across "
            "every spatial location of the input, exploiting translation "
            "equivariance to detect local patterns with far fewer parameters "
            "than a dense layer. Stacked convolutions and pooling build a "
            "hierarchy of increasingly abstract visual features.",
            "Recurrent networks carry a hidden state across time steps, "
            "updating it from the previous state and the current input to "
            "model sequential dependencies. Gated variants like the long "
            "short term memory cell mitigate vanishing gradients and let the "
            "network retain information over long sequences.",
        ],
    ]
    ok = True
    diff_only_seen = False
    for bi, texts in enumerate(batteries):
        out = tag_texts(texts)
        if len(out) != len(texts):
            print(f"  battery {bi}: LEN MISMATCH {len(out)} != {len(texts)}")
            ok = False
            continue
        for salient, diff in out:
            for t in salient + diff:
                # stemmed/canonical: lowercase and no stopwords
                if t != t.lower():
                    print(f"  battery {bi}: non-lowercase term {t!r}")
                    ok = False
                for tok in t.split():
                    if tok in _STOPWORDS:
                        print(f"  battery {bi}: stopword leaked {t!r}")
                        ok = False
            if set(diff) - set(salient):
                diff_only_seen = True
        if not any(s for s, _ in out):
            print(f"  battery {bi}: all salient lists empty")
            ok = False
        print(f"  battery {bi} ({len(texts)} texts): "
              f"{[ (s[:3], d[:3]) for s, d in out ]}")
    if not diff_only_seen:
        print("  DECOUPLE FAIL: no differentiating-only lexeme in any battery")
        ok = False
    else:
        print("  decouple OK: differentiating-only lexemes present")
    print("GATE PASS" if ok else "GATE FAIL")
    return ok


def run():
    if not gate():
        print("Aborting: gate failed.")
        sys.exit(1)

    paths = sorted(glob.glob(os.path.join(CORPUS, "**", "*.md"), recursive=True))
    print(f"\ncorpus files: {len(paths)}  (CORPUS={CORPUS})")

    texts = []
    for p in paths:
        with open(p, "r", encoding="utf-8") as fh:
            texts.append(fh.read())

    print("lexing + tagging (single corpus-relative batch)...")
    tagged = tag_texts(texts)
    assert len(tagged) == len(paths), "index alignment broke"

    written = 0
    empty = 0
    diff_only_files = 0
    for p, (salient, diff) in zip(paths, tagged):
        if not salient and not diff:
            empty += 1
        if set(diff) - set(salient):
            diff_only_files += 1
        out_path = os.path.splitext(p)[0] + ".tags.json"
        with open(out_path, "w", encoding="utf-8") as fh:
            json.dump(
                {"salient": salient, "differentiating": diff},
                fh, ensure_ascii=False, indent=2,
            )
        written += 1

    print(f"wrote {written} tags.json ({empty} empty; "
          f"{diff_only_files} have >=1 differentiating-only lexeme)")


if __name__ == "__main__":
    mode = sys.argv[1] if len(sys.argv) > 1 else "--gate"
    if mode == "--gate":
        gate()
    elif mode == "--run":
        run()
    else:
        print("usage: tag_corpus.py [--gate|--run]")
