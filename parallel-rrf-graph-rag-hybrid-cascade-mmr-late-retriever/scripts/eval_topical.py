"""Corrected eval: TOPICAL-CLUSTER relevance, LLM-judged (TREC-style pooling).

The earlier eval used self-retrieval ground truth (query from skill X must
return X) — which PENALIZES a retriever for surfacing *related* skills, the
actual goal ("ask about regression -> also want cross-validation"). This fixes
it:

  1. Query seeds: a sample of skills; the query is a natural topic question
     built from the skill's name (no exact wording copy).
  2. POOL: run every config, union their top-k skills → the judge pool. Pooling
     keeps the judgment unbiased across configs (every config's hits get judged).
  3. JUDGE: a local LLM labels each (query, skill name+description) pair
     related y/n (thinking-suppressed, cached in sqlite — judge once, reuse).
  4. Relevant set per query = pooled skills judged related.
  5. Score each config: precision@k / recall@k / nDCG@k vs that relevant set.

This is where the graph can finally earn its place — related-cluster retrieval
is exactly what entity/ontology connections optimize for.

Run:  python eval_topical.py --n 25 --k 10
"""

import argparse
import json
import math
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

PG_RAW = ab.PG_RAW
COLLECTION = ab.COLLECTION
JUDGE_MODEL = "qwen3.5-oc:4b"
JUDGE_DB = Path(__file__).parent / "topical_judge.sqlite"
CONFIGS = ("E", "EX_bm25_rrf", "EX_graph_h2")


# --- config runner (reuses proven legs) ------------------------------------

def cfg_skills(cfg, query, store, driver, conn, k):
    emb = srv.cosine_seed(store, query, ex.CAND_K)
    if not emb:
        return []
    if cfg == "E":
        rows = emb
    elif cfg == "EX_bm25_rrf":
        lex = bm.lexical_seed_bm25(conn, query, ex.CAND_K)
        rows = ex._rrf(emb, lex)
    elif cfg == "EX_graph_h2":
        lex = bm.lexical_seed_graph(driver, conn, query, ex.CAND_K, 2)
        rows = ex._rrf(emb, lex)
    else:
        raise ValueError(cfg)
    # local rank-to-skills that respects k (ex._rank_to_skills hard-caps at FINAL_K=10)
    order = []
    for r in rows:
        if r[2] not in order:
            order.append(r[2])
    return order[:k]


# --- LLM relatedness judge (pooled, cached) --------------------------------

def _skill_desc(conn, slug):
    with conn.cursor() as cur:
        cur.execute("""SELECT e.cmetadata->>'skill_description'
                       FROM langchain_pg_embedding e JOIN langchain_pg_collection col
                       ON col.uuid=e.collection_id
                       WHERE col.name=%s AND e.cmetadata->>'skill_slug'=%s LIMIT 1""",
                    (COLLECTION, slug))
        r = cur.fetchone()
        return (r[0] if r else "") or ""


def judge(con_j, conn, query, slug):
    row = con_j.execute("SELECT related FROM j WHERE query=? AND slug=?", (query, slug)).fetchone()
    if row is not None:
        return bool(row[0])
    desc = _skill_desc(conn, slug)
    prompt = (f"/no_think\nA data-science practitioner asks: \"{query}\"\n"
              f"Candidate skill: \"{slug.split('/')[-1]}\" — {desc}\n"
              "Is this skill topically relevant/useful to answer or explore that "
              "question (same or adjacent concept)? Answer strictly yes or no.")
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


# --- metrics ----------------------------------------------------------------

def score(ranked, relevant, k):
    hits = [1 if s in relevant else 0 for s in ranked[:k]]
    rec = sum(hits) / len(relevant) if relevant else 0.0
    prec = sum(hits) / k
    dcg = sum(h / math.log2(i + 2) for i, h in enumerate(hits))
    idcg = sum(1 / math.log2(i + 2) for i in range(min(len(relevant), k)))
    ndcg = dcg / idcg if idcg else 0.0
    return rec, prec, ndcg


def run(n, k):
    store, driver = srv._get_store(), srv._get_driver()
    conn = psycopg.connect(**PG_RAW)
    bm.build_idf(conn)
    con_j = sqlite3.connect(JUDGE_DB)
    con_j.execute("CREATE TABLE IF NOT EXISTS j (query TEXT, slug TEXT, related INT, PRIMARY KEY(query,slug))")

    POOL_K = k                      # pool + rank depth (pass a large k, e.g. 30)
    CUTS = [c for c in (5, 10, 20, 30) if c <= POOL_K] or [POOL_K]

    import random
    rng = random.Random(7)
    skills = sorted({s for _, _, s in ab.golden_pairs(10**9)["description"]})
    seeds = rng.sample(skills, min(n, len(skills)))
    queries = [(s, f"how does {s.split('/')[-1].replace('-', ' ')} work and what is it used for") for s in seeds]

    try:
        # 1) pool top-POOL_K skills across configs, per query
        pools, ranked_by_cfg = {}, {c: {} for c in CONFIGS}
        for src, q in queries:
            pool = set()
            for c in CONFIGS:
                r = cfg_skills(c, q, store, driver, conn, POOL_K)
                ranked_by_cfg[c][q] = r
                pool.update(r)
            pools[q] = pool
        # 2) judge every pooled (query, skill) -> relevant sets
        relevant = {}
        for src, q in queries:
            relevant[q] = {s for s in pools[q] if judge(con_j, conn, q, s)}
        # 3) score each config at multiple cutoffs (recall reveals cluster capture)
        avg_rel = sum(len(relevant[q]) for _, q in queries) / len(queries)
        print(f"\n=== topical-cluster eval: {len(queries)} queries, pool_k={POOL_K} "
              f"(LLM-judged, pooled) — avg {avg_rel:.1f} relevant skills/query ===", flush=True)
        hdr = "  " + f"{'config':>13}" + "".join(f"{'R@'+str(c):>8}" for c in CUTS) + \
              "".join(f"{'nDCG@'+str(c):>9}" for c in CUTS)
        print(hdr, flush=True)
        m = len(queries)
        for c in CONFIGS:
            recs = {cut: 0.0 for cut in CUTS}; nds = {cut: 0.0 for cut in CUTS}
            for src, q in queries:
                for cut in CUTS:
                    rec, _, nd = score(ranked_by_cfg[c][q], relevant[q], cut)
                    recs[cut] += rec; nds[cut] += nd
            row = "  " + f"{c:>13}" + "".join(f"{recs[cut]/m:>8.3f}" for cut in CUTS) + \
                  "".join(f"{nds[cut]/m:>9.3f}" for cut in CUTS)
            print(row, flush=True)
    finally:
        conn.close(); con_j.close()


if __name__ == "__main__":
    ap = argparse.ArgumentParser(description=__doc__)
    ap.add_argument("--n", type=int, default=25)
    ap.add_argument("--k", type=int, default=10)
    args = ap.parse_args()
    run(args.n, args.k)
