"""Full 3-lane sandwich ablation — the architecture we actually agreed:

  [dense || bm25 || graph-on-expanded]  -> RRF -> MMR -> ColBERT -> whole-skill

Measures each stage's MARGINAL lift on the deterministic bridging gold (n=33),
so we see whether the graph lane / MMR / entailment each earn their place — not
just the end number. Graph lane is seeded from the ENTITIES OF THE TOP DENSE HITS
(pseudo-relevance feedback = good seeds; raw-query seeding is what failed before),
expanded 1 hop over CO_OCCURS.

Configs (incremental):
  E        dense only
  EB       RRF(dense, bm25)                    <- current shipped hybrid
  EBG      RRF(dense, bm25, graph)             <- the 3-lane sandwich
  EBG_M    EBG -> MMR
  EBG_MC   EBG -> MMR -> ColBERT (entailment)

Run:  python eval_sandwich.py --k 20 --wgraph 1.0
"""

import argparse
import sys
from pathlib import Path

import numpy as np
import psycopg

sys.path.insert(0, str(Path(__file__).parent))
import mcp_server as srv          # noqa: E402
import experiments as ex          # noqa: E402
import eval_topical as tp         # noqa: E402
import eval_bridging_det as bd    # noqa: E402
import bm25_experiment as bm      # noqa: E402

CAND_K = ex.CAND_K
POOL = 50          # pre-MMR/ColBERT pool cap (keeps ColBERT tractable)
SEED_M = 10        # top-M dense hits whose entities seed the graph expansion


def graph_expanded_seed(driver, conn, dense_ids, k):
    """PRF graph lane: entities of the top-SEED_M dense chunks -> CO_OCCURS 1-hop
    -> chunks sharing that entity neighborhood, ranked by connection count. Good
    seeds (relevant entities), unlike raw-query synset seeding."""
    seeds = dense_ids[:SEED_M]
    if not seeds:
        return []
    cy = """
        MATCH (c0:Chunk)-[:HAS_ENTITY]->(e:Entity) WHERE c0.id IN $seeds
        WITH collect(DISTINCT e.id) AS se
        UNWIND se AS eid
        MATCH (e:Entity {id:eid})-[:CO_OCCURS]-(e2:Entity)
        WITH DISTINCT e2 WHERE size([(e2)<-[:HAS_ENTITY]-() | 1]) < 200   // degree cap: skip hubs
        MATCH (e2)<-[:HAS_ENTITY]-(c:Chunk) WHERE NOT c.id IN $seeds
        RETURN c.id AS cid, count(*) AS score
        ORDER BY score DESC LIMIT $k
    """
    with driver.session() as s:
        rows = [(r["cid"], r["score"]) for r in s.run(cy, seeds=seeds, k=k)]
    if not rows:
        return []
    meta = srv.fetch_chunks(conn, [c for c, _ in rows])
    return [(cid, meta[cid][0], meta[cid][1], float(sc)) for cid, sc in rows if cid in meta]


def rrf_multi(lists, weights, k_out=CAND_K, rrf_k=60):
    ranks = [{row[0]: i for i, row in enumerate(L)} for L in lists]
    by = {}
    for L in lists:
        for row in L:
            by.setdefault(row[0], row)
    scored = []
    for cid, row in by.items():
        s = sum(w / (rrf_k + ranks[i].get(cid, len(lists[i]))) for i, w in enumerate(weights))
        scored.append((row[0], row[1], row[2], s))
    scored.sort(key=lambda x: x[-1], reverse=True)
    return scored[:k_out]


def to_skills(rows, k):
    order = []
    for r in rows:
        if r[2] not in order:
            order.append(r[2])
    return order[:k]


def run(k, wgraph):
    store = srv._get_store(); driver = srv._get_driver()
    conn = psycopg.connect(**tp.PG_RAW); bm.build_idf(conn)
    gold = bd._verify_gold(conn); m = len(gold)
    configs = ("E", "EB", "EBG", "EBG_M", "EBG_MC")
    agg = {c: [0.0, 0.0, 0.0] for c in configs}   # R@k, nDCG@k, MRR
    try:
        for q, gs in gold:
            rel = set(gs)
            dense = srv.cosine_seed(store, q, CAND_K)
            bm25 = srv.ts_bm25_seed(conn, q, CAND_K)
            graph = graph_expanded_seed(driver, conn, [r[0] for r in dense], CAND_K)
            cos_sims = {r[0]: r[3] for r in dense}
            ranked = {
                "E":   dense,
                "EB":  rrf_multi([dense, bm25], [1, 1]),
                "EBG": rrf_multi([dense, bm25, graph], [1, 1, wgraph]),
            }
            ebg_pool = ranked["EBG"][:POOL]
            mmr = srv.mmr_rerank(ebg_pool, cos_sims, {}, k=min(len(ebg_pool), POOL))
            ranked["EBG_M"] = mmr
            ranked["EBG_MC"] = srv.colbert_rerank(q, mmr, k=len(mmr))
            for c in configs:
                sk = to_skills(ranked[c], k)
                rec, _, nd = tp.score(sk, rel, k)
                agg[c][0] += rec; agg[c][1] += nd
                agg[c][2] += next((1.0/(i+1) for i, s in enumerate(sk) if s in rel), 0.0)
        print(f"\n=== SANDWICH ablation: {m} bridging queries, k={k}, w_graph={wgraph} "
              f"(seed_m={SEED_M}, pool={POOL}) ===", flush=True)
        print(f"  {'config':>8} {'R@'+str(k):>8} {'nDCG@'+str(k):>9} {'MRR':>8}   {'stage':>24}", flush=True)
        labels = {"E": "dense", "EB": "+bm25 (shipped hybrid)", "EBG": "+graph (3-lane)",
                  "EBG_M": "+MMR", "EBG_MC": "+ColBERT entailment"}
        base = agg["E"][0]/m
        for c in configs:
            r, n, mr = agg[c][0]/m, agg[c][1]/m, agg[c][2]/m
            print(f"  {c:>8} {r:>8.3f} {n:>9.3f} {mr:>8.3f}   {labels[c]:>24}", flush=True)
        print(f"\n  marginal R@{k} vs previous stage:", flush=True)
        prev = None
        for c in configs:
            r = agg[c][0]/m
            if prev is not None:
                print(f"    {c:>8}  {r-prev:+.3f}", flush=True)
            prev = r
    finally:
        conn.close()


if __name__ == "__main__":
    ap = argparse.ArgumentParser(description=__doc__)
    ap.add_argument("--k", type=int, default=20)
    ap.add_argument("--wgraph", type=float, default=1.0)
    args = ap.parse_args()
    run(args.k, args.wgraph)
