"""Aggregated retriever + parallel local/global eval.

Aggregated retriever contract (operator spec):
  - lanes run as PARALLEL async calls (dense || bm25 || community)
  - BARRIER: await all lanes before fusion (asyncio.gather)
  - STALL GUARD: each lane wrapped in asyncio.wait_for(timeout); a stalled/failed
    lane returns [] and is logged, never blocks the aggregate (partial-tolerant)
  - each lane holds its OWN psycopg connection (no shared-conn contention)

Lanes operate at SKILL level (ranked skill lists) so chunk-lanes and the
community-lane fuse uniformly via RRF.

Two payoffs tested CONCURRENTLY (asyncio.gather), each with its own retriever
(own connections, so no cross-eval contention):
  LOCAL  — bridging gold: does the community lane lift topical-cluster recall
           over the 2-lane hybrid?
  GLOBAL — thematic gold: does community expansion surface the whole topical
           cluster ("all regularization methods") vs plain hybrid?

Run:  python eval_aggregated.py --k 20 --lane-timeout 8
"""

import argparse
import asyncio
import json
import sys
from pathlib import Path

import psycopg

sys.path.insert(0, str(Path(__file__).parent))
import mcp_server as srv          # noqa: E402
import experiments as ex          # noqa: E402
import eval_topical as tp         # noqa: E402
import eval_bridging_det as bd    # noqa: E402
import bm25_experiment as bm      # noqa: E402

# Subgraph-DWPC community report (build_graph_report.py): cosine-graph Louvain
# communities + per-skill within-community DWPC-ranked neighbors + density/conductance.
GR = json.loads((Path(__file__).parent / "graph_report.json").read_text(encoding="utf-8"))
GR_COMM = GR["skill_comm"]               # slug -> community_id
GR_NBR = GR["dwpc_neighbors"]            # slug -> [[neighbor, dwpc_score], ...]
GR_METRICS = GR["comm_metrics"]          # cid(str) -> {size,density,conductance,lcc_ratio}
# gate: only expand into coherent communities (high density OR low conductance).
GATE_CONDUCTANCE = 0.6                   # skip expansion above this (poorly separated)

# thematic gold: topic -> query + the topical cluster of skills (verified at runtime)
THEMATIC = [
    ("what are the ways to regularize or shrink a regression model",
     ["regression/ridge-regression", "regression/lasso-regression", "regression/ridge-lasso-regression",
      "regression/lasso-penalty", "misc/regularization", "misc/regularization-path",
      "misc/shrinkage", "misc/shrinkage-penalty", "misc/soft-thresholding"]),
    ("techniques for cross-validating a model",
     ["model-eval/k-fold-cross-validation", "model-eval/leave-one-out-cross-validation",
      "model-eval/nested-cross-validation", "model-eval/cross-validation-score",
      "model-eval/grid-search-cross-validation"]),
    ("ensemble methods that combine many learners",
     ["trees-ensembles/bagging", "trees-ensembles/boosting", "trees-ensembles/random-forest",
      "trees-ensembles/adaboost", "trees-ensembles/gradient-boosting", "trees-ensembles/stacking-ensemble",
      "trees-ensembles/xgboost", "trees-ensembles/ensemble-learning"]),
    ("approaches to reducing dimensionality",
     ["clustering-dimred/principal-component-analysis", "clustering-dimred/dimension-reduction",
      "clustering-dimred/kernel-pca", "clustering-dimred/sparse-pca", "clustering-dimred/truncated-svd",
      "clustering-dimred/singular-value-decomposition-svd"]),
    ("algorithms for clustering data",
     ["clustering-dimred/k-means-clustering", "clustering-dimred/hierarchical-clustering",
      "clustering-dimred/dbscan", "misc/spectral-clustering", "misc/agglomerative-clustering"]),
    ("metrics for evaluating a classifier",
     ["model-eval/roc-curve", "model-eval/area-under-roc-curve", "model-eval/confusion-matrix"]),
    ("methods for handling missing or messy data",
     ["data-prep/missing-data", "data-prep/imputation", "data-prep/outlier",
      "data-prep/one-hot-encoding", "data-prep/normalization", "data-prep/standardization"]),
    ("gradient-based optimization of model parameters",
     ["optimization/gradient-descent", "optimization/stochastic-gradient-descent",
      "optimization/learning-rate", "optimization/loss-function"]),
]


# --- skill-level lanes (each returns a ranked list of skill slugs) -----------

def _rows_to_skills(rows):
    order = []
    for r in rows:
        if r[2] not in order:
            order.append(r[2])
    return order


def lane_dense(store, query, k):
    return _rows_to_skills(srv.cosine_seed(store, query, ex.CAND_K))[:k]


def lane_bm25(conn, query, k):
    return _rows_to_skills(srv.ts_bm25_seed(conn, query, ex.CAND_K))[:k]


def lane_community(store, query, k):
    """Subgraph-DWPC community expansion: top dense skill -> its within-community
    DWPC-ranked neighbors (hub-corrected on the community subgraph). Gated by
    community density/conductance — skip expansion for poorly-separated (mushy)
    communities and fall back to the dense top."""
    top = _rows_to_skills(srv.cosine_seed(store, query, 10))
    if not top:
        return []
    seed = top[0]
    cid = str(GR_COMM.get(seed, ""))
    m = GR_METRICS.get(cid)
    if not m or m.get("conductance", 1.0) > GATE_CONDUCTANCE:
        return top[:k]                       # gate: mushy community -> dense fallback
    nbrs = [n for n, _ in GR_NBR.get(seed, [])]
    return ([seed] + nbrs)[:k]


# --- async aggregated retriever: parallel lanes, barrier, stall guard --------

async def _guarded(fn, timeout, label):
    try:
        return await asyncio.wait_for(asyncio.to_thread(fn), timeout)
    except asyncio.TimeoutError:
        print(f"    STALLED lane {label} (>{timeout}s) — skipped", flush=True)
        return []
    except Exception as e:  # noqa: BLE001
        print(f"    FAILED lane {label}: {e}", flush=True)
        return []


async def aggregate(store, conn, query, k, lanes, timeout):
    """Run the requested lanes in parallel, barrier-await, RRF the skill lists."""
    jobs, labels = [], []
    if "dense" in lanes:
        jobs.append(_guarded(lambda: lane_dense(store, query, ex.CAND_K), timeout, "dense")); labels.append("dense")
    if "bm25" in lanes:
        jobs.append(_guarded(lambda: lane_bm25(conn, query, ex.CAND_K), timeout, "bm25")); labels.append("bm25")
    if "comm" in lanes:
        jobs.append(_guarded(lambda: lane_community(store, query, ex.CAND_K), timeout, "comm")); labels.append("comm")
    results = await asyncio.gather(*jobs)          # BARRIER
    # RRF over ranked skill lists
    ranks = [{s: i for i, s in enumerate(L)} for L in results]
    allsk = {s for L in results for s in L}
    scored = sorted(allsk, key=lambda s: -sum(1.0/(60+r.get(s, 10**6)) for r in ranks))
    return scored[:k]


def score(ranked, gold, k):
    rel = set(gold)
    hits = [1 if s in rel else 0 for s in ranked[:k]]
    import math
    rec = sum(hits)/len(rel) if rel else 0.0
    dcg = sum(h/math.log2(i+2) for i, h in enumerate(hits))
    idcg = sum(1/math.log2(i+2) for i in range(min(len(rel), k)))
    mrr = next((1.0/(i+1) for i, s in enumerate(ranked) if s in rel), 0.0)
    return rec, (dcg/idcg if idcg else 0.0), mrr


async def eval_suite(name, goldset, lane_configs, k, timeout):
    """Own connections (no cross-suite contention)."""
    store = srv._get_store()
    conn = psycopg.connect(**tp.PG_RAW); bm.build_idf(conn)
    out = {}
    try:
        for cfgname, lanes in lane_configs.items():
            R = N = M = 0.0
            for q, gold in goldset:
                ranked = await aggregate(store, conn, q, k, lanes, timeout)
                r, n, mr = score(ranked, gold, k)
                R += r; N += n; M += mr
            m = len(goldset)
            out[cfgname] = (R/m, N/m, M/m)
        return name, out, len(goldset)
    finally:
        conn.close()


async def main(k, timeout):
    # verify thematic gold slugs exist
    conn = psycopg.connect(**tp.PG_RAW)
    with conn.cursor() as cur:
        cur.execute("""SELECT DISTINCT e.cmetadata->>'skill_slug' FROM langchain_pg_embedding e
                       JOIN langchain_pg_collection col ON col.uuid=e.collection_id
                       WHERE col.name=%s""", (tp.COLLECTION,))
        present = {r[0] for r in cur.fetchall()}
    conn.close()
    thematic = [(q, [g for g in gs if g in present]) for q, gs in THEMATIC]
    local = bd.GOLD

    lane_cfgs = {"hybrid(E+B)": ["dense", "bm25"], "agg(E+B+Comm)": ["dense", "bm25", "comm"]}
    # BOTH suites in parallel
    (ln, lo, ln_n), (gn, go, gn_n) = await asyncio.gather(
        eval_suite("LOCAL", local, lane_cfgs, k, timeout),
        eval_suite("GLOBAL", thematic, lane_cfgs, k, timeout),
    )
    for nm, res, cnt in [(ln, lo, ln_n), (gn, go, gn_n)]:
        print(f"\n=== {nm}: {cnt} queries, k={k} ===", flush=True)
        print(f"  {'config':>16} {'R@'+str(k):>8} {'nDCG@'+str(k):>9} {'MRR':>8}", flush=True)
        for cfg, (r, n, mr) in res.items():
            print(f"  {cfg:>16} {r:>8.3f} {n:>9.3f} {mr:>8.3f}", flush=True)


if __name__ == "__main__":
    ap = argparse.ArgumentParser(description=__doc__)
    ap.add_argument("--k", type=int, default=20)
    ap.add_argument("--lane-timeout", type=float, default=8.0)
    args = ap.parse_args()
    asyncio.run(main(args.k, args.lane_timeout))
