"""Test the operator's ToC-routing thesis: does a topic-routed metadata branch
(fused parallel with dense, RRF) beat plain dense on bridging queries — where the
entity/synset graph earned nothing?

This tests a DIFFERENT signal than eval_bridging_det.py's graph leg: the curated
11-folder taxonomy (low cardinality, human-structured), not the 5,342-token noisy
entity vocab. "ToC-seeded query expansion" for an 11-way vocab = classify the
query into its top-t topics via cosine against precomputed topic centroids (O(1),
no LLM rephrase), then surface within-topic candidates dense ranked low.

  branch_dense  = global cosine (existing)
  branch_topic  = cosine RESTRICTED to the query's top-t routed topics (recalls
                  within-topic tail items outside the global top-CAND_K)
  fused         = RRF(branch_dense, branch_topic)

Configs: E (dense) | EX_bm25_rrf (entity-BM25, the champion so far) |
         ET_route_rrf (dense ⊕ topic-routed). Same fixed bridging gold, n=33.

Run:  python eval_topic_route.py --k 20 --topics 2
"""

import argparse
import sys
from pathlib import Path

import numpy as np
import psycopg

sys.path.insert(0, str(Path(__file__).parent))
import mcp_server as srv          # noqa: E402
import eval_ablation as ab        # noqa: E402
import experiments as ex          # noqa: E402
import bm25_experiment as bm      # noqa: E402
import eval_topical as tp         # noqa: E402
import eval_bridging_det as bd    # noqa: E402  (GOLD, _verify_gold)

# 11-folder taxonomy with a descriptive centroid string each. "misc" is a
# catch-all with no coherent semantics — deliberately vague so routing rarely
# picks it; this exposes whether the taxonomy's quality caps the branch.
TOPIC_DESC = {
    "classification": "classification predicting discrete class labels categories",
    "clustering-dimred": "clustering grouping and dimensionality reduction",
    "data-prep": "data preparation cleaning preprocessing feature engineering",
    "misc": "general miscellaneous assorted concepts",
    "model-eval": "model evaluation validation performance metrics scoring",
    "neural-nets": "neural networks deep learning layers activations",
    "optimization": "optimization gradient descent loss minimization training",
    "probability-stats": "probability statistics distributions inference hypothesis",
    "regression": "regression predicting continuous numeric outcomes",
    "reinforcement-learning": "reinforcement learning agents rewards policies",
    "trees-ensembles": "decision trees boosting bagging ensemble methods",
}


def _topic_centroids(store):
    emb = store.embeddings
    labels = list(TOPIC_DESC.keys())
    vecs = np.array(emb.embed_documents([TOPIC_DESC[t] for t in labels]), dtype=float)
    vecs /= (np.linalg.norm(vecs, axis=1, keepdims=True) + 1e-9)
    return labels, vecs


def route(store, labels, cvecs, query, t):
    q = np.array(store.embeddings.embed_query(query), dtype=float)
    q /= (np.linalg.norm(q) + 1e-9)
    sims = cvecs @ q
    top = np.argsort(-sims)[:t]
    return [labels[i] for i in top]


def branch_topic(store, query, topics, k):
    """Dense retrieval RESTRICTED to routed topics (metadata filter)."""
    hits = store.similarity_search_with_score(query, k=k, filter={"topic": {"$in": topics}})
    return [(d.metadata["chunk_id"], d.page_content, d.metadata["skill_slug"], 1.0 - float(dist))
            for d, dist in hits]


def cfg_skills(cfg, query, store, conn, labels, cvecs, t, k):
    emb = srv.cosine_seed(store, query, ex.CAND_K)
    if not emb:
        return []
    if cfg == "E":
        rows = emb
    elif cfg == "EX_bm25_rrf":
        rows = ex._rrf(emb, bm.lexical_seed_bm25(conn, query, ex.CAND_K))
    elif cfg == "ET_route_rrf":
        topics = route(store, labels, cvecs, query, t)
        rows = ex._rrf(emb, branch_topic(store, query, topics, ex.CAND_K))
    elif cfg == "ET_route_append":
        # DENSE-DOMINANT: dense order preserved; topic branch only APPENDS skills
        # dense didn't already surface (recall-only, can't displace a correct hit).
        topics = route(store, labels, cvecs, query, t)
        branch = branch_topic(store, query, topics, ex.CAND_K)
        order = []
        for r in emb:
            if r[2] not in order:
                order.append(r[2])
        for r in branch:
            if r[2] not in order:
                order.append(r[2])
        return order[:k]
    else:
        raise ValueError(cfg)
    order = []
    for r in rows:
        if r[2] not in order:
            order.append(r[2])
    return order[:k]


CONFIGS = ("E", "ET_route_rrf", "ET_route_append")


def run(k, t):
    store = srv._get_store()
    conn = psycopg.connect(**tp.PG_RAW)
    bm.build_idf(conn)
    labels, cvecs = _topic_centroids(store)
    CUTS = [c for c in (5, 10, 20) if c <= k] or [k]
    try:
        gold = bd._verify_gold(conn)
        # diagnostic: how many gold answers even LIVE in a routable (non-misc) topic
        misc_gold = sum(1 for _, gs in gold for g in gs if g.startswith("misc/"))
        tot_gold = sum(len(gs) for _, gs in gold)
        print(f"\n=== TOPIC-ROUTE eval: {len(gold)} bridging queries, k={k}, top-{t} topics "
              f"({tot_gold} gold slugs, {misc_gold} in 'misc/' = unroutable) ===", flush=True)
        # routing accuracy: does the query route to a topic containing a gold answer?
        hit = 0
        for q, gs in gold:
            topics = route(store, labels, cvecs, q, t)
            gold_topics = {g.split("/")[0] for g in gs}
            if gold_topics & set(topics):
                hit += 1
        print(f"  routing hit-rate (a gold answer's topic in top-{t}): {hit}/{len(gold)} = {hit/len(gold):.2f}", flush=True)
        hdr = "  " + f"{'config':>13}" + "".join(f"{'R@'+str(c):>8}" for c in CUTS) + \
              "".join(f"{'nDCG@'+str(c):>9}" for c in CUTS) + f"{'MRR':>8}"
        print(hdr, flush=True)
        m = len(gold); results = {}
        for c in CONFIGS:
            recs = {cut: 0.0 for cut in CUTS}; nds = {cut: 0.0 for cut in CUTS}; mrr = 0.0
            for q, gs in gold:
                ranked = cfg_skills(c, q, store, conn, labels, cvecs, t, k)
                rel = set(gs)
                for cut in CUTS:
                    r, _, nd = tp.score(ranked, rel, cut)
                    recs[cut] += r; nds[cut] += nd
                mrr += next((1.0/(i+1) for i, s in enumerate(ranked) if s in rel), 0.0)
            results[c] = (recs, nds, mrr)
            print("  " + f"{c:>13}" + "".join(f"{recs[cut]/m:>8.3f}" for cut in CUTS) +
                  "".join(f"{nds[cut]/m:>9.3f}" for cut in CUTS) + f"{mrr/m:>8.3f}", flush=True)
        big = CUTS[-1]; be, bn, bmr = results["E"]
        br, bnn, bm_ = be[big]/m, bn[big]/m, bmr/m
        print(f"\n  deltas vs dense (E) — R@{big} / nDCG@{big} / MRR (5% = shippable):", flush=True)
        for c in CONFIGS:
            if c == "E":
                continue
            r, n, mr = results[c]
            dr, dn, dm = r[big]/m - br, n[big]/m - bnn, mr/m - bm_
            flag = "  <-- LIFT" if max(dr, dn, dm) >= 0.05 else ("  (drop)" if max(dr, dn, dm) < 0 else "")
            print(f"    {c:>13}  {dr:+.3f} / {dn:+.3f} / {dm:+.3f}{flag}", flush=True)
    finally:
        conn.close()


if __name__ == "__main__":
    ap = argparse.ArgumentParser(description=__doc__)
    ap.add_argument("--k", type=int, default=20)
    ap.add_argument("--topics", type=int, default=2)
    args = ap.parse_args()
    run(args.k, args.topics)
