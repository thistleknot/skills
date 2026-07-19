"""Bridging-query eval: the test that actually judges the graph thesis.

The topical eval (eval_topical.py) used single-concept queries that CONTAIN the
target skill's name — dense's home turf, no hop to make — scored by a saturated
judge that rewarded recall volume. That test can't bear on whether graph
structure surfaces material dense MISSES. This fixes the two confounds:

  1. BRIDGING QUERIES — hand-authored so the query text shares NO surface token
     with the target concept. The answer skill is reachable by concept, not by
     lexical/embedding proximity. This is the regime GraphRAG claims to win.
  2. STRICT JUDGE — "directly answers OR is a necessary prerequisite/mechanism",
     not "adjacent". Breaks the ~70%-relevant saturation so the metric can
     discriminate connective precision, not blob size.

Configs unchanged (E / EX_bm25_rrf / EX_graph_h2) so results compare to
eval_topical.py head-to-head. Judge cache is SEPARATE (bridging_judge.sqlite) —
the strict prompt yields different labels than the lenient topical one.

Run:  python eval_bridging.py --k 20
"""

import argparse
import re
import sqlite3
import sys
from pathlib import Path

import psycopg
import requests

sys.path.insert(0, str(Path(__file__).parent))
import mcp_server as srv          # noqa: E402
import eval_ablation as ab        # noqa: E402
import experiments as ex          # noqa: E402
import bm25_experiment as bm      # noqa: E402
import eval_topical as tp         # noqa: E402  (cfg_skills, score, _skill_desc)

JUDGE_MODEL = tp.JUDGE_MODEL
JUDGE_DB = Path(__file__).parent / "bridging_judge.sqlite"
COLLECTION = ab.COLLECTION
CONFIGS = tp.CONFIGS

# Bridging queries: (query text with NO token overlap with the answer concept,
# the concept it's really asking about — for the human reader only). The point
# is that a keyword/embedding match on the query fails; you must traverse from
# the described symptom/mechanism to the named technique.
QUERIES = [
    "my model scores perfectly on data it has seen but fails on new data",          # overfitting -> regularization/cv
    "how do I keep coefficients from blowing up when predictors move together",     # multicollinearity -> ridge/regularization
    "a method to shrink parameter estimates toward zero to reduce variance",        # regularization/ridge/lasso
    "the assumption that lets least-squares give the best unbiased estimates",      # gauss-markov / homoscedasticity
    "splitting data repeatedly to estimate how well a model generalizes",           # cross-validation
    "grouping points so items in a group are more alike than across groups",        # clustering / k-means
    "reducing many correlated measurements to a few uncorrelated directions",       # pca / dimensionality reduction
    "combining many weak rules into one strong prediction",                         # ensemble / boosting / random forest
    "measuring how far predictions sit from the truth on average",                  # loss / rmse / mae
    "deciding a cutoff that trades catching positives against false alarms",        # roc / threshold / precision-recall
    "walking downhill on an error surface to fit parameters",                       # gradient descent
    "the tendency of a flexible model to swing wildly with small data changes",     # bias-variance / variance
    "turning categories into numbers a model can use",                              # encoding / feature engineering
    "estimating parameters by maximizing how likely the data is",                   # mle
    "a graph structure of nodes and edges used to model relationships",             # graph / network
]


def judge(con_j, conn, query, slug):
    row = con_j.execute("SELECT related FROM j WHERE query=? AND slug=?", (query, slug)).fetchone()
    if row is not None:
        return bool(row[0])
    desc = tp._skill_desc(conn, slug)
    prompt = (f"/no_think\nQuestion: \"{query}\"\n"
              f"Candidate skill: \"{slug.split('/')[-1]}\" — {desc}\n"
              "Does this skill DIRECTLY answer the question, or name the specific "
              "technique/mechanism/prerequisite the question is describing? "
              "Answer yes ONLY for a direct answer or its core mechanism — NOT "
              "for merely same-field or loosely-related topics. Answer strictly yes or no.")
    payload = {"model": JUDGE_MODEL, "messages": [{"role": "user", "content": prompt}],
               "format": "json", "think": False, "stream": False, "options": {"temperature": 0}}
    rel = False
    try:
        r = requests.post(f"{srv.OLLAMA_URL}/api/chat", json=payload, timeout=60)
        raw = r.json().get("message", {}).get("content", "")
        raw = re.sub(r"<think>.*?</think>", "", raw, flags=re.DOTALL)
        raw = re.sub(r"```(?:json)?", "", raw).strip().lower()
        rel = ("yes" in raw) or ('"related": true' in raw) or ('true' in raw and 'false' not in raw)
    except Exception as e:  # noqa: BLE001
        print(f"    judge failed ({slug}): {e}")
    con_j.execute("INSERT OR REPLACE INTO j VALUES (?,?,?)", (query, slug, int(rel)))
    con_j.commit()
    return rel


def run(k):
    store, driver = srv._get_store(), srv._get_driver()
    conn = psycopg.connect(**tp.PG_RAW)
    bm.build_idf(conn)
    con_j = sqlite3.connect(JUDGE_DB)
    con_j.execute("CREATE TABLE IF NOT EXISTS j (query TEXT, slug TEXT, related INT, PRIMARY KEY(query,slug))")

    POOL_K = k
    CUTS = [c for c in (5, 10, 20) if c <= POOL_K] or [POOL_K]
    queries = QUERIES

    try:
        pools, ranked_by_cfg = {}, {c: {} for c in CONFIGS}
        for q in queries:
            pool = set()
            for c in CONFIGS:
                r = tp.cfg_skills(c, q, store, driver, conn, POOL_K)
                ranked_by_cfg[c][q] = r
                pool.update(r)
            pools[q] = pool
        relevant = {q: {s for s in pools[q] if judge(con_j, conn, q, s)} for q in queries}
        avg_rel = sum(len(relevant[q]) for q in queries) / len(queries)
        print(f"\n=== BRIDGING eval: {len(queries)} non-co-located queries, pool_k={POOL_K}, "
              f"STRICT judge — avg {avg_rel:.1f} relevant skills/query ===", flush=True)
        hdr = "  " + f"{'config':>13}" + "".join(f"{'R@'+str(c):>8}" for c in CUTS) + \
              "".join(f"{'nDCG@'+str(c):>9}" for c in CUTS)
        print(hdr, flush=True)
        m = len(queries)
        for c in CONFIGS:
            recs = {cut: 0.0 for cut in CUTS}; nds = {cut: 0.0 for cut in CUTS}
            for q in queries:
                for cut in CUTS:
                    rec, _, nd = tp.score(ranked_by_cfg[c][q], relevant[q], cut)
                    recs[cut] += rec; nds[cut] += nd
            row = "  " + f"{c:>13}" + "".join(f"{recs[cut]/m:>8.3f}" for cut in CUTS) + \
                  "".join(f"{nds[cut]/m:>9.3f}" for cut in CUTS)
            print(row, flush=True)
        # per-query zero-relevant flag (a query no config could answer = bad seed)
        empties = [q for q in queries if not relevant[q]]
        if empties:
            print(f"  NOTE {len(empties)} queries had 0 judged-relevant (excluded from signal):", flush=True)
            for q in empties:
                print(f"    - {q[:70]}", flush=True)
    finally:
        conn.close(); con_j.close()


if __name__ == "__main__":
    ap = argparse.ArgumentParser(description=__doc__)
    ap.add_argument("--k", type=int, default=20)
    args = ap.parse_args()
    run(args.k)
