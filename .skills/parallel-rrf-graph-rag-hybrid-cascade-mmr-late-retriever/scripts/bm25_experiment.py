"""Does a TRUE BM25-weighted synset/hypernym leg beat the overlap-count leg?

The winning ensemble (EX_rrf) fuses dense with a lexical leg that currently just
COUNTS matching enrich_tokens. This tests whether proper BM25 weighting (IDF +
tf-saturation over the corpus's synset/hypernym tokens) lifts further.

Configs: E (dense) | EX_rrf (dense ⊕ overlap-count lexical) | EX_bm25_rrf
(dense ⊕ BM25-weighted lexical). Same deterministic ground truth + metrics.

Run:  python bm25_experiment.py --n 100
"""

import argparse
import json
import math
import sys
from collections import defaultdict
from pathlib import Path

import psycopg

sys.path.insert(0, str(Path(__file__).parent))
import mcp_server as srv          # noqa: E402
import eval_ablation as ab        # noqa: E402
import experiments as ex          # noqa: E402  (_rrf, _query_syn_tokens, _rank_to_skills, lexical_seed)

BM25_K1, BM25_B = 1.5, 0.75
_IDF = None
_AVGDL = None


def build_idf(conn):
    """Corpus IDF + avg doc length over enrich_tokens (the synset/hypernym 'terms')."""
    global _IDF, _AVGDL
    if _IDF is not None:
        return
    with conn.cursor() as cur:
        cur.execute("""
            SELECT t, count(*) FROM langchain_pg_embedding e
            JOIN langchain_pg_collection col ON col.uuid=e.collection_id,
            LATERAL jsonb_array_elements_text(e.cmetadata->'enrich_tokens') t
            WHERE col.name=%s GROUP BY t
        """, (ex.COLLECTION,))
        df = {r[0]: r[1] for r in cur.fetchall()}
        cur.execute("""
            SELECT count(*), avg(jsonb_array_length(e.cmetadata->'enrich_tokens'))
            FROM langchain_pg_embedding e JOIN langchain_pg_collection col
            ON col.uuid=e.collection_id WHERE col.name=%s
        """, (ex.COLLECTION,))
        n, avgdl = cur.fetchone()
    _AVGDL = float(avgdl or 1.0)
    _IDF = {t: math.log((n - v + 0.5) / (v + 0.5) + 1) for t, v in df.items()}


def lexical_seed_bm25(conn, query, k):
    """BM25 over enrich_tokens: rank chunks by IDF-weighted, length-normalized
    match of the query's synset/hypernym tokens."""
    qtoks = ex._query_syn_tokens(query)
    if not qtoks:
        return []
    with conn.cursor() as cur:
        cur.execute(f"""
            SELECT e.cmetadata->>'chunk_id', e.document, e.cmetadata->>'skill_slug',
                   e.cmetadata->'enrich_tokens'
            FROM langchain_pg_embedding e JOIN langchain_pg_collection col
              ON col.uuid=e.collection_id
            WHERE col.name=%s AND e.cmetadata->'enrich_tokens' ?| %s
        """, (ex.COLLECTION, qtoks))
        rows = cur.fetchall()
    qset = set(qtoks)
    scored = []
    for cid, doc, slug, toks in rows:
        toks = toks or []
        dl = len(toks) or 1
        tf = defaultdict(int)
        for t in toks:
            if t in qset:
                tf[t] += 1
        s = sum(_IDF.get(t, 0.0) * (c * (BM25_K1 + 1)) /
                (c + BM25_K1 * (1 - BM25_B + BM25_B * dl / _AVGDL)) for t, c in tf.items())
        if s > 0:
            scored.append((cid, doc, slug, s))
    scored.sort(key=lambda x: x[-1], reverse=True)
    return scored[:k]


def _syn(name):
    from nltk.corpus import wordnet as wn
    try:
        return wn.synset(name)
    except Exception:  # noqa: BLE001 - bad/nonexistent synset name
        return None


def _query_synsets(query):
    from nltk.corpus import wordnet as wn
    import re as _re
    out = []
    for w in _re.findall(r"[a-zA-Z]+", query.lower()):
        if w in ex._STOP or len(w) < 3:
            continue
        s = wn.synsets(w)
        if s:
            out.append(s[0])
    return out


def lexical_seed_onto(conn, query, k):
    """ONTOLOGY-GRAPH leg: rank chunks by WordNet wu-palmer similarity between
    query synsets and chunk synsets (uses the IS-A hierarchy — matches related
    concepts with NO token overlap). Candidate pool = chunks sharing any
    synset/hypernym token (bounds the O(q*c) similarity computation)."""
    qsyn = _query_synsets(query)
    qtoks = ex._query_syn_tokens(query)
    if not qsyn or not qtoks:
        return []
    with conn.cursor() as cur:
        cur.execute("""
            SELECT e.cmetadata->>'chunk_id', e.document, e.cmetadata->>'skill_slug',
                   e.cmetadata->'enrich_tokens'
            FROM langchain_pg_embedding e JOIN langchain_pg_collection col
              ON col.uuid=e.collection_id
            WHERE col.name=%s AND e.cmetadata->'enrich_tokens' ?| %s
        """, (ex.COLLECTION, qtoks))
        rows = cur.fetchall()
    scored = []
    for cid, doc, slug, toks in rows:
        csyn = [s for s in (_syn(t) for t in (toks or [])) if s is not None]
        if not csyn:
            continue
        # sum over query concepts of best ontology similarity to any chunk concept
        s = 0.0
        for qs in qsyn:
            best = max((qs.wup_similarity(cs) or 0.0 for cs in csyn), default=0.0)
            s += best
        if s > 0:
            scored.append((cid, doc, slug, s))
    scored.sort(key=lambda x: x[-1], reverse=True)
    return scored[:k]


def lexical_seed_graph(driver, conn, query, k, max_hop):
    """n-HOP ONTOLOGY leg: from the query's degree-0 synsets, traverse the
    composed HYPERNYM graph (undirected) up to `max_hop` hops to reach chunk
    concepts, ranked by shortest hop-distance (hops=0 is a direct/collapsed
    match, hops>=1 is n-degree-out). Harmonic decay 1/(hops+1). This is the
    'graph enables extended hops' signal — 1-hop edges composed into n-hop reach."""
    qsyn = [s.name() for s in _query_synsets(query)]
    if not qsyn:
        return []
    cy = f"""
        UNWIND $qsyn AS qid
        MATCH (q:Synset {{id: qid}})-[h:HYPERNYM*0..{max_hop}]-(cs:Synset)
        WITH cs, min(size(h)) AS hops
        MATCH (cs)<-[:HAS_CONCEPT]-(c:Chunk)
        RETURN c.id AS cid, min(hops) AS hops
    """
    with driver.session() as s:
        hopmap = {r["cid"]: r["hops"] for r in s.run(cy, qsyn=qsyn)}
    if not hopmap:
        return []
    ranked_ids = sorted(hopmap, key=lambda c: hopmap[c])[:k]   # nearest first
    meta = srv.fetch_chunks(conn, ranked_ids)
    return [(cid, meta[cid][0], meta[cid][1], 1.0 / (hopmap[cid] + 1))
            for cid in ranked_ids if cid in meta]


def run_cfg(cfg, query, exclude, store, driver, conn):
    emb = [r for r in srv.cosine_seed(store, query, ex.CAND_K) if r[0] != exclude]
    if not emb:
        return []
    if cfg == "E":
        return ex._rank_to_skills(emb)
    if cfg == "EX_bm25_rrf":
        lex = [r for r in lexical_seed_bm25(conn, query, ex.CAND_K) if r[0] != exclude]
        return ex._rank_to_skills(ex._rrf(emb, lex))
    if cfg == "EX_bm25_L":                            # champion -> ColBERT (FAIR colbert test)
        lex = [r for r in lexical_seed_bm25(conn, query, ex.CAND_K) if r[0] != exclude]
        fused = ex._rrf(emb, lex)
        return ex._rank_to_skills(srv.colbert_rerank(query, fused, k=len(fused)))
    if cfg.startswith("EX_graph_h"):                  # EX_graph_h1 / h2 / h3
        hops = int(cfg[-1])
        lex = [r for r in lexical_seed_graph(driver, conn, query, ex.CAND_K, hops) if r[0] != exclude]
        return ex._rank_to_skills(ex._rrf(emb, lex))
    raise ValueError(cfg)


def run(n):
    store, driver = srv._get_store(), srv._get_driver()
    conn = psycopg.connect(**ab.PG_RAW)
    build_idf(conn)
    try:
        for gt_name, pairs in ab.golden_pairs(n).items():
            print(f"\n=== {gt_name}: {len(pairs)} queries ===", flush=True)
            print(f"  {'config':>13} {'recall@1':>9} {'recall@5':>9} {'mrr':>7} {'ndcg@10':>8}  {'vs E':>7}")
            base = None
            for cfg in ("E", "EX_bm25_rrf", "EX_bm25_L", "EX_graph_h1", "EX_graph_h2"):
                agg = {f"recall@{k}": 0.0 for k in ab.KS}; agg["mrr"] = 0.0; agg["ndcg@10"] = 0.0
                for cid, q, target in pairs:
                    m = ab.metrics_for(run_cfg(cfg, q, cid, store, driver, conn), target)
                    for kk in agg:
                        agg[kk] += m[kk]
                for kk in agg:
                    agg[kk] = round(agg[kk] / max(len(pairs), 1), 3)
                if cfg == "E":
                    base = agg["ndcg@10"]
                vs = f"{agg['ndcg@10']-base:+.3f}"
                print(f"  {cfg:>13} {agg['recall@1']:>9} {agg['recall@5']:>9} {agg['mrr']:>7} {agg['ndcg@10']:>8}  {vs:>7}", flush=True)
    finally:
        conn.close()


if __name__ == "__main__":
    ap = argparse.ArgumentParser(description=__doc__)
    ap.add_argument("--n", type=int, default=100)
    args = ap.parse_args()
    run(args.n)
