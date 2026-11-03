"""Deterministic bridging eval — the trustworthy test of the graph thesis.

No LLM judge, no pooling. 20 hand-authored bridging queries whose text shares
(near-)no surface token with the answer, each mapped to a FIXED small set of
real answer-skill slugs = ground truth I define, not a lenient model. This is
the correct instrument:

  - Query lives OUTSIDE dense's home turf (describes a symptom/mechanism, not the
    technique's name) -> the regime where graph structure is supposed to win.
  - Independent gold set (1-4 slugs) -> metric measures hitting the RIGHT skill,
    not blob volume. Saturation is impossible.
  - n=20, deterministic -> runs in seconds; look for deltas > 5% (the operator's
    disposition: a real lift shows at this size, a sub-5% effect isn't shippable).

Configs E / EX_bm25_rrf / EX_graph_h2 (== eval_topical.py, head-to-head).
All gold slugs verified present in the collection before scoring.

Run:  python eval_bridging_det.py
"""

import argparse
import sys
from pathlib import Path

import psycopg

sys.path.insert(0, str(Path(__file__).parent))
import mcp_server as srv          # noqa: E402
import eval_ablation as ab        # noqa: E402
import experiments as ex          # noqa: E402
import bm25_experiment as bm      # noqa: E402
import eval_topical as tp         # noqa: E402  (cfg_skills, score)

CONFIGS = tp.CONFIGS

# (bridging query — no/minimal surface overlap with the answer, gold answer slugs)
GOLD = [
    ("my model scores perfectly on data it has seen but fails on fresh data",
     ["misc/overfitting", "misc/regularization", "model-eval/k-fold-cross-validation",
      "model-eval/bias-variance-tradeoff"]),
    ("how do I stop coefficients from exploding when predictors move together",
     ["misc/multicollinearity", "regression/ridge-regression"]),
    ("a way to pull parameter estimates toward zero to cut variance",
     ["misc/regularization", "regression/ridge-regression", "regression/lasso-regression"]),
    ("the property of constant error spread that least squares assumes",
     ["misc/homoscedasticity"]),
    ("carving up the data many times over to gauge how well it generalizes",
     ["model-eval/k-fold-cross-validation", "model-eval/cross-validation-score",
      "model-eval/leave-one-out-cross-validation"]),
    ("putting points into groups whose members resemble one another",
     ["misc/clustering", "clustering-dimred/k-means-clustering", "clustering-dimred/cluster-analysis"]),
    ("collapsing many correlated measurements into a few independent directions",
     ["clustering-dimred/principal-component-analysis", "clustering-dimred/dimension-reduction"]),
    ("blending many weak learners into one strong predictor",
     ["trees-ensembles/ensemble-learning", "trees-ensembles/boosting",
      "trees-ensembles/random-forest", "trees-ensembles/bagging"]),
    ("the typical magnitude of prediction error, penalizing big misses hardest",
     ["probability-stats/root-mean-squared-error", "optimization/loss-function"]),
    ("a curve trading catches against false alarms across every cutoff",
     ["model-eval/roc-curve", "model-eval/area-under-roc-curve"]),
    ("iteratively stepping downhill on the error surface to fit weights",
     ["optimization/gradient-descent", "optimization/stochastic-gradient-descent"]),
    ("the tension between a rigid model and one that overreacts to noise",
     ["model-eval/bias-variance-tradeoff"]),
    ("turning text categories into numeric columns a model can consume",
     ["data-prep/one-hot-encoding", "data-prep/encoding-function"]),
    ("choosing parameters that make the observed data most probable",
     ["probability-stats/maximum-likelihood-estimation", "probability-stats/likelihood-function"]),
    ("partitioning unlabeled points around a fixed count of centers",
     ["clustering-dimred/k-means-clustering", "clustering-dimred/tuning-k-means-configuration"]),
    ("a penalty that can drop some coefficients to exactly zero for selection",
     ["regression/lasso-regression", "regression/lasso-penalty"]),
    ("a penalty that smoothly damps coefficients without removing any",
     ["regression/ridge-regression"]),
    ("averaging many bootstrap-resampled learners with randomized splits",
     ["trees-ensembles/random-forest", "trees-ensembles/bagging"]),
    ("sequentially fitting new learners to the leftover errors of prior ones",
     ["trees-ensembles/boosting", "trees-ensembles/gradient-boosting"]),
    ("keeping only the top singular directions of a matrix to compress it",
     ["clustering-dimred/singular-value-decomposition-svd", "clustering-dimred/truncated-svd"]),
    ("predicting a yes/no outcome as a probability between zero and one",
     ["regression/logistic-regression", "misc/logistic-function"]),
    ("a branching flowchart of if-then splits that routes an input to an outcome",
     ["trees-ensembles/decision-tree", "trees-ensembles/classification-tree"]),
    ("the chance of seeing data this extreme when nothing real is happening",
     ["probability-stats/p-value"]),
    ("a formal procedure to decide whether an observed effect is genuine or luck",
     ["probability-stats/hypothesis-testing", "probability-stats/hypothesis-test-decision"]),
    ("a number from minus one to one saying how tightly two variables track together",
     ["probability-stats/correlation"]),
    ("rescaling each feature to a common scale so none dominates by magnitude",
     ["data-prep/standardization", "data-prep/normalization"]),
    ("making the model pay more for mistakes on the scarce category",
     ["misc/class-weight"]),
    ("the knob setting how large each optimizer update step is",
     ["optimization/learning-rate"]),
    ("a grid cross-tabulating predicted against true labels",
     ["model-eval/confusion-matrix"]),
    ("labeling a point by the majority vote of its closest examples",
     ["classification/k-nearest-neighbors-classifier"]),
    ("finding the widest-margin separating boundary between two classes",
     ["classification/support-vector-machine", "classification/support-vector-classifier"]),
    ("randomly switching off units during training to curb co-adaptation",
     ["neural-nets/dropout"]),
    ("filling in absent values so the dataset has no gaps",
     ["data-prep/imputation", "data-prep/missing-data"]),
]


def _verify_gold(conn):
    """Drop any gold slug not actually in the collection (fail-loud on typos)."""
    with conn.cursor() as cur:
        cur.execute("""SELECT DISTINCT e.cmetadata->>'skill_slug'
                       FROM langchain_pg_embedding e JOIN langchain_pg_collection col
                       ON col.uuid=e.collection_id WHERE col.name=%s""", (ab.COLLECTION,))
        present = {r[0] for r in cur.fetchall()}
    cleaned, dropped = [], []
    for q, gold in GOLD:
        good = [g for g in gold if g in present]
        dropped += [g for g in gold if g not in present]
        if good:
            cleaned.append((q, good))
    if dropped:
        print(f"WARNING dropped {len(dropped)} missing gold slugs: {sorted(set(dropped))}", flush=True)
    return cleaned


def run(k):
    store, driver = srv._get_store(), srv._get_driver()
    conn = psycopg.connect(**tp.PG_RAW)
    bm.build_idf(conn)
    CUTS = [c for c in (5, 10, 20) if c <= k] or [k]
    try:
        gold = _verify_gold(conn)
        print(f"\n=== DETERMINISTIC bridging eval: {len(gold)} non-co-located queries, "
              f"k={k}, fixed gold ({sum(len(g) for _, g in gold)/len(gold):.1f} slugs/query) ===", flush=True)
        hdr = "  " + f"{'config':>13}" + "".join(f"{'R@'+str(c):>8}" for c in CUTS) + \
              "".join(f"{'nDCG@'+str(c):>9}" for c in CUTS) + f"{'MRR':>8}"
        print(hdr, flush=True)
        m = len(gold)
        results = {}
        for c in CONFIGS:
            recs = {cut: 0.0 for cut in CUTS}; nds = {cut: 0.0 for cut in CUTS}; mrr = 0.0
            for q, gset in gold:
                ranked = tp.cfg_skills(c, q, store, driver, conn, k)
                rel = set(gset)
                for cut in CUTS:
                    rec, _, nd = tp.score(ranked, rel, cut)
                    recs[cut] += rec; nds[cut] += nd
                # MRR: reciprocal rank of first gold hit
                rr = next((1.0 / (i + 1) for i, s in enumerate(ranked) if s in rel), 0.0)
                mrr += rr
            results[c] = (recs, nds, mrr)
            row = "  " + f"{c:>13}" + "".join(f"{recs[cut]/m:>8.3f}" for cut in CUTS) + \
                  "".join(f"{nds[cut]/m:>9.3f}" for cut in CUTS) + f"{mrr/m:>8.3f}"
            print(row, flush=True)
        # deltas vs dense baseline E on the biggest cutoff + MRR
        big = CUTS[-1]
        be, bn, bm_ = results["E"]
        base_r, base_n, base_mrr = be[big]/m, bn[big]/m, bm_/m
        print(f"\n  deltas vs dense (E) — R@{big} / nDCG@{big} / MRR (5% = shippable):", flush=True)
        for c in CONFIGS:
            if c == "E":
                continue
            r, n, mr = results[c]
            dr, dn, dm = r[big]/m - base_r, n[big]/m - base_n, mr/m - base_mrr
            flag = "  <-- LIFT" if max(dr, dn, dm) >= 0.05 else ("  (drop)" if max(dr, dn, dm) < 0 else "")
            print(f"    {c:>13}  {dr:+.3f} / {dn:+.3f} / {dm:+.3f}{flag}", flush=True)
    finally:
        conn.close()


if __name__ == "__main__":
    ap = argparse.ArgumentParser(description=__doc__)
    ap.add_argument("--k", type=int, default=20)
    args = ap.parse_args()
    run(args.k)
