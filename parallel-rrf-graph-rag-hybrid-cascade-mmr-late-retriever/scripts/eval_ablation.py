"""Cumulative ablation of the chosen retrieval hierarchy — component lift.

NOT an A-vs-B tournament. The operator's architecture is fixed:
  cascade: parallel{ embeddings, graph_expansion, rrf } -> mmr -> late_interaction
This measures how much each stage ADDS, by running the pipeline with stages
turned on cumulatively and reporting the marginal lift in recall/precision/
MRR/nDCG at the skill level.

Ground truth is DERIVED deterministically from the corpus — no LLM query-gen:
  - held_out_passage : a chunk's text is the query; target = its skill; that
    exact chunk is excluded from scoring (must find the skill's OTHER chunks).
    This is the discriminator.
  - description      : skill_description is the query; target = the skill (floor).
Both are sampled for a bounded run.

Variants (cumulative):
  E        embeddings only
  E+G      embeddings (+) graph_expansion, RRF-fused over chunks
  E+G+M    + MMR
  E+G+M+L  + ColBERT late interaction  (== the operator's full design)

Run:  python eval_ablation.py --n 150      # sample size per ground-truth type
"""

import argparse
import json
import math
import random
import sys
from pathlib import Path

import psycopg

import numpy as np
from pgvector.psycopg import register_vector

sys.path.insert(0, str(Path(__file__).parent))
import mcp_server as srv  # noqa: E402

PG_RAW = dict(host="localhost", port=5432, dbname="langchain",
              user="langchain", password="langchain")
COLLECTION = "data_science_skills"
KS = (1, 3, 5, 10)
CAND_K = 144        # embeddings candidate pool; graph expansion doubles it
MMR_LAMBDA = 0.7
COSINE_K = 100
RRF_K_OUT = 50
EXPANSION_HOPS = 1
MMR_K = 30
FINAL_K = 10          # rank depth we score skills to


# =============================================================================
# Deterministic ground truth from the corpus
# =============================================================================

def golden_pairs(n: int) -> dict:
    """Return {'held_out_passage': [(chunk_id, query_text, target_slug), ...],
              'description': [(None, desc, target_slug), ...]} sampled to n each."""
    rng = random.Random(42)
    with psycopg.connect(**PG_RAW) as c, c.cursor() as cur:
        cur.execute("""
            SELECT e.cmetadata->>'chunk_id', e.document, e.cmetadata->>'skill_slug',
                   e.cmetadata->>'skill_description'
            FROM langchain_pg_embedding e JOIN langchain_pg_collection col
              ON col.uuid = e.collection_id WHERE col.name = %s
        """, (COLLECTION,))
        rows = cur.fetchall()
    # one held-out passage per skill (a middle chunk), then sample n
    by_skill = {}
    desc_by_skill = {}
    for cid, doc, slug, desc in rows:
        by_skill.setdefault(slug, []).append((cid, doc))
        if desc and slug not in desc_by_skill:
            desc_by_skill[slug] = desc
    passages = []
    for slug, chunks in by_skill.items():
        if len(chunks) < 2:      # need other chunks to retrieve after excluding the query one
            continue
        cid, doc = chunks[len(chunks) // 2]
        passages.append((cid, doc[:1500], slug))
    rng.shuffle(passages)
    descs = [(None, d, s) for s, d in desc_by_skill.items()]
    rng.shuffle(descs)
    return {"held_out_passage": passages[:n], "description": descs[:n]}


# =============================================================================
# The cumulative pipeline (operator's hierarchy), staged by `variant`
# =============================================================================

def _expand_ranked(driver, conn, seed_ids: list, exclude: str) -> list:
    """Graph expansion for RECALL (option 1): chunks 1 hop out from the seeds'
    (non-hub) entities, ranked by how many seed-connected entities they share.
    Doubles the pool. NOT a query-relevance score — expansion only broadens what
    the downstream reranker (ColBERT) gets to see; there's no query-graph, so we
    don't pretend the graph ranks by relevance."""
    if not seed_ids:
        return []
    seeds = seed_ids[:srv.EXPAND_SEED_CAP]
    q = """
        UNWIND $ids AS cid
        MATCH (:Chunk {id: cid})-[:HAS_ENTITY]->(e:Entity)
        WITH DISTINCT e WHERE count{ (e)<-[:HAS_ENTITY]-(:Chunk) } < $degcap
        MATCH (e)-[:CO_OCCURS*0..1]-(ne:Entity)<-[:HAS_ENTITY]-(c2:Chunk)
        WHERE count{ (ne)<-[:HAS_ENTITY]-(:Chunk) } < $degcap AND NOT c2.id IN $ids
        RETURN c2.id AS id, count(DISTINCT ne) AS shared
        ORDER BY shared DESC LIMIT $lim
    """
    with driver.session() as s:
        ranked = [r["id"] for r in s.run(q, ids=seeds, degcap=srv.EXPAND_ENTITY_DEGCAP, lim=CAND_K)]
    ranked = [c for c in ranked if c != exclude]
    meta = srv.fetch_chunks(conn, ranked)
    return [(cid, meta[cid][0], meta[cid][1], 0.0) for cid in ranked if cid in meta]


def _fetch_embeddings(conn, chunk_ids: list) -> dict:
    """chunk_id -> embedding np.array, from langchain_pg_embedding (for real MMR)."""
    if not chunk_ids:
        return {}
    register_vector(conn)
    with conn.cursor() as cur:
        cur.execute("""SELECT e.cmetadata->>'chunk_id', e.embedding
                       FROM langchain_pg_embedding e JOIN langchain_pg_collection col
                       ON col.uuid=e.collection_id
                       WHERE col.name=%s AND e.cmetadata->>'chunk_id' = ANY(%s)""",
                    (COLLECTION, chunk_ids))
        return {r[0]: np.asarray(r[1], dtype=float) for r in cur.fetchall()}


def _mmr(query_vec, pool, embs, k):
    """Proper MMR over real chunk embeddings (fixes the earlier cosine=0 matrix).
    relevance = cosine(query, chunk); diversity = max cosine to already-picked."""
    def cs(a, b):
        na, nb = np.linalg.norm(a), np.linalg.norm(b)
        return float(a @ b / (na * nb)) if na and nb else 0.0
    cand = [r for r in pool if r[0] in embs]
    if not cand:
        return pool[:k]
    rel = {r[0]: cs(query_vec, embs[r[0]]) for r in cand}
    sel, rest = [], list(cand)
    first = max(rest, key=lambda r: rel[r[0]])
    sel.append(first); rest.remove(first)
    while rest and len(sel) < k:
        nxt = max(rest, key=lambda r: MMR_LAMBDA * rel[r[0]]
                  - (1 - MMR_LAMBDA) * max((cs(embs[r[0]], embs[s[0]]) for s in sel), default=0.0))
        sel.append(nxt); rest.remove(nxt)
    return sel


def retrieve_skills(query: str, variant: str, exclude_chunk: str = None) -> list:
    """Operator's design (option 1): embeddings → graph-expand to 2× (RECALL) →
    MMR → ColBERT rerank → whole-skill vote. Graph broadens the pool; ColBERT
    (late interaction) is what scores the graph-surfaced chunks against the query.
    No RRF, no graph-density scoring."""
    store, driver = srv._get_store(), srv._get_driver()
    conn = psycopg.connect(**PG_RAW)
    try:
        emb_rows = srv.cosine_seed(store, query, CAND_K)
        if exclude_chunk:
            emb_rows = [r for r in emb_rows if r[0] != exclude_chunk]
        if not emb_rows:
            return []

        pool = list(emb_rows)                      # E: cosine only
        if variant != "E":                          # +G: double the pool via graph (recall)
            exp = _expand_ranked(driver, conn, [r[0] for r in emb_rows], exclude_chunk)
            have = {r[0] for r in pool}
            pool += [r for r in exp if r[0] not in have]

        if variant in ("E+G+M", "E+G+M+L"):         # +M: real embedding-based MMR
            qv = np.asarray(store.embeddings.embed_query(query), dtype=float)
            embs = _fetch_embeddings(conn, [r[0] for r in pool])
            pool = _mmr(qv, pool, embs, k=min(len(pool), CAND_K))
        if variant == "E+G+M+L":                    # +L: ColBERT late interaction
            pool = srv.colbert_rerank(query, pool, k=len(pool))

        order = []                                   # chunks vote for their skill
        for r in pool:
            if r[2] not in order:
                order.append(r[2])
        return order[:FINAL_K]
    finally:
        conn.close()


# =============================================================================
# Metrics + ablation
# =============================================================================

def metrics_for(ranked: list, target: str) -> dict:
    r = next((i for i, s in enumerate(ranked, 1) if s == target), None)
    out = {}
    for k in KS:
        hit = r is not None and r <= k
        out[f"recall@{k}"] = 1.0 if hit else 0.0
        out[f"precision@{k}"] = (1.0 / k) if hit else 0.0
    out["mrr"] = 1.0 / r if r else 0.0
    out["ndcg@10"] = 1.0 / math.log2(r + 1) if r else 0.0
    return out


def run_ablation(n: int) -> None:
    gt = golden_pairs(n)
    variants = ["E", "E+G", "E+G+M", "E+G+M+L"]
    for gt_name, pairs in gt.items():
        print(f"\n=== {gt_name}: {len(pairs)} queries ===", flush=True)
        print(f"  {'variant':>9} {'recall@1':>9} {'recall@5':>9} {'mrr':>7} {'ndcg@10':>8}  (d_ndcg)")
        prev = None
        results = {}
        for v in variants:
            agg = {f"recall@{k}": 0.0 for k in KS}
            agg.update({f"precision@{k}": 0.0 for k in KS}); agg["mrr"] = 0.0; agg["ndcg@10"] = 0.0
            for cid, q, target in pairs:
                m = metrics_for(retrieve_skills(q, v, exclude_chunk=cid), target)
                for kk in agg:
                    agg[kk] += m[kk]
            for kk in agg:
                agg[kk] = round(agg[kk] / max(len(pairs), 1), 3)
            results[v] = agg
            delta = "" if prev is None else f"{agg['ndcg@10'] - prev:+.3f}"
            print(f"  {v:>9} {agg['recall@1']:>9} {agg['recall@5']:>9} {agg['mrr']:>7} {agg['ndcg@10']:>8}  {delta}", flush=True)
            prev = agg["ndcg@10"]
        (Path(__file__).parent / f"ablation_{gt_name}.json").write_text(
            json.dumps(results, indent=2), encoding="utf-8")


if __name__ == "__main__":
    ap = argparse.ArgumentParser(description=__doc__)
    ap.add_argument("--n", type=int, default=150, help="queries per ground-truth type")
    args = ap.parse_args()
    run_ablation(args.n)
