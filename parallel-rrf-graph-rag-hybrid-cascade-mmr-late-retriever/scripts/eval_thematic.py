"""Thematic retrieval eval — the GraphRAG-target regime, done properly.

4 themes, 5 varied natural-language questions each (n=20), each mapped to a
curated corpus-verified topical cluster (the theme gold). Measures THEMATIC
recall + precision @k: does the retriever surface the whole related cluster?

Compares, via the async aggregated retriever (parallel lanes + barrier + stall
guard from eval_aggregated):
  hybrid (dense+bm25)  vs  agg (dense+bm25+community)  vs  comm_only
so we see whether Leiden communities lift thematic recall over 2-lane hybrid.

Run:  python eval_thematic.py --k 20
"""

import argparse
import asyncio
import sys
from pathlib import Path

import psycopg

sys.path.insert(0, str(Path(__file__).parent))
import eval_topical as tp          # noqa: E402
import bm25_experiment as bm       # noqa: E402
import mcp_server as srv           # noqa: E402
import eval_aggregated as agg      # noqa: E402  (aggregate, lanes)

THEME_GOLD = {
    "regularization": ["misc/regularization", "misc/regularization-path", "misc/shrinkage",
        "misc/shrinkage-penalty", "misc/soft-thresholding", "misc/penalty-term", "misc/penalty-parameter",
        "regression/ridge-regression", "regression/lasso-regression", "regression/ridge-lasso-regression",
        "regression/lasso-penalty"],
    "cross_validation": ["model-eval/k-fold-cross-validation", "model-eval/leave-one-out-cross-validation",
        "model-eval/nested-cross-validation", "model-eval/cross-validation-score",
        "model-eval/grid-search-cross-validation", "model-eval/hold-out-set", "misc/model-selection",
        "misc/grid-search"],
    "ensembles": ["trees-ensembles/bagging", "trees-ensembles/boosting", "trees-ensembles/random-forest",
        "trees-ensembles/adaboost", "trees-ensembles/gradient-boosting", "trees-ensembles/stacking-ensemble",
        "trees-ensembles/xgboost", "trees-ensembles/ensemble-learning", "trees-ensembles/ensemble-method",
        "trees-ensembles/averaging-ensemble"],
    "dim_reduction": ["clustering-dimred/principal-component-analysis", "clustering-dimred/dimension-reduction",
        "clustering-dimred/kernel-pca", "clustering-dimred/sparse-pca", "clustering-dimred/truncated-svd",
        "clustering-dimred/singular-value-decomposition-svd", "clustering-dimred/randomized-svd",
        "clustering-dimred/principal-component"],
}

# Questions are framed as a READER OF THE SOURCE BOOKS (ISL, Applied Regression
# Modeling, Statistics for ML, ML Algorithms, Data Mining for Business Analytics)
# would ask — symptom/goal phrasing, deliberately SCRUBBED of the technique-name
# vocabulary that appears in slugs/descriptions (no "ridge/lasso/regularization/
# cross-validation/PCA/bagging/boosting/ensemble" etc.). That vocabulary is
# retrieval-side only (the query expander); putting it in the question = leakage.
QUESTIONS = {
    "regularization": [
        "my model nails the training data but flops on new data — how do I rein it in",
        "how do I stop a linear model from leaning too hard on any single predictor",
        "ways to keep the fitted weights small so the model travels better",
        "give up a little accuracy on the data I have for better results on data I don't",
        "automatically sideline the unhelpful predictors while fitting a linear model"],
    "cross_validation": [
        "how do I get a trustworthy estimate of performance on data the model hasn't seen",
        "my single train/test split feels lucky — how do I make evaluation more reliable",
        "how do I pick the best setting for a tuning knob without fooling myself",
        "squeezing a reliable performance estimate out of a limited amount of data",
        "how do I decide which of several candidate models is genuinely better"],
    "ensembles": [
        "can I get a better prediction by pooling several mediocre models",
        "how do I make a crowd of simple rule-based predictors work together",
        "taming the wild swings of a flexible model by pooling many copies of it",
        "building models one after another so each one fixes the previous one's mistakes",
        "letting several different classifiers each weigh in on the final answer"],
    "dim_reduction": [
        "I have hundreds of overlapping measurements — how do I boil them down to a few",
        "squashing many correlated variables into a smaller set of independent ones",
        "how do I lay out very high-feature data on two or three axes to look at it",
        "finding the few underlying directions that explain most of the variation",
        "shrinking a huge feature matrix to something manageable without losing much"],
}

CONFIGS = {"hybrid": ["dense", "bm25"], "agg": ["dense", "bm25", "comm"], "comm_only": ["comm"]}


def rp(ranked, gold, k):
    rel = set(gold)
    hits = sum(1 for s in ranked[:k] if s in rel)
    return hits/len(rel) if rel else 0.0, hits/k


async def run(k):
    store = srv._get_store()
    conn = psycopg.connect(**tp.PG_RAW); bm.build_idf(conn)
    ks = sorted({10, k})
    try:
        # accum[cfg][cut] = [recall_sum, prec_sum]; per-theme too
        acc = {c: {ct: [0.0, 0.0] for ct in ks} for c in CONFIGS}
        per_theme = {t: {c: {ct: [0.0, 0.0] for ct in ks} for c in CONFIGS} for t in THEME_GOLD}
        n = 0
        for theme, qs in QUESTIONS.items():
            gold = THEME_GOLD[theme]
            for q in qs:
                n += 1
                for cfg, lanes in CONFIGS.items():
                    ranked = await agg.aggregate(store, conn, q, max(ks), lanes, timeout=8.0)
                    for ct in ks:
                        r, p = rp(ranked, gold, ct)
                        acc[cfg][ct][0] += r; acc[cfg][ct][1] += p
                        per_theme[theme][cfg][ct][0] += r; per_theme[theme][cfg][ct][1] += p
        print(f"\n=== THEMATIC eval: {n} questions across {len(THEME_GOLD)} themes ===", flush=True)
        for ct in ks:
            print(f"\n  --- @{ct} ---   {'config':>10} {'recall':>8} {'precision':>10}", flush=True)
            for c in CONFIGS:
                R, P = acc[c][ct][0]/n, acc[c][ct][1]/n
                print(f"                {c:>10} {R:>8.3f} {P:>10.3f}", flush=True)
        # per-theme recall@k (does community help specific themes?)
        print(f"\n  per-theme recall@{k}:   {'theme':>16} {'hybrid':>8} {'agg':>8} {'comm_only':>10}", flush=True)
        for t in THEME_GOLD:
            nt = len(QUESTIONS[t])
            h = per_theme[t]['hybrid'][k][0]/nt
            a = per_theme[t]['agg'][k][0]/nt
            co = per_theme[t]['comm_only'][k][0]/nt
            print(f"                        {t:>16} {h:>8.3f} {a:>8.3f} {co:>10.3f}", flush=True)
    finally:
        conn.close()


if __name__ == "__main__":
    ap = argparse.ArgumentParser(description=__doc__)
    ap.add_argument("--k", type=int, default=20)
    args = ap.parse_args()
    asyncio.run(run(args.k))
