"""BM25 lane over the native tsvector column (snowball-stemmed, in-DB, no extra
extension — pg_bestmatch is NOT available here). True BM25 math with tf taken
from the tsvector's position counts; length normalization DROPPED (b=0) because
the Docling HybridChunker keeps chunks ~equidistant, so dl/avgdl ~ 1.

  score(chunk) = Σ_t  IDF(t) · tf(t)·(k1+1) / (tf(t) + k1)      [b = 0]
  tf(t)  = array_length((unnest(content_tsv)).positions, 1)      per chunk
  IDF(t) = log((N - ndoc + 0.5)/(ndoc + 0.5) + 1)                ndoc via ts_stat

Configs: E (dense) | Xenrich (dense ⊕ old enrich-token BM25) |
         Xts (dense ⊕ tsvector BM25). Same n=33 bridging gold.

Run:  python eval_bm25_lane.py
"""

import argparse
import math
import re
import sys
from collections import defaultdict
from pathlib import Path

import psycopg

sys.path.insert(0, str(Path(__file__).parent))
import mcp_server as srv          # noqa: E402
import eval_ablation as ab        # noqa: E402
import experiments as ex          # noqa: E402
import bm25_experiment as bm      # noqa: E402
import eval_topical as tp         # noqa: E402
import eval_bridging_det as bd    # noqa: E402

BM25_K1 = 1.5
_LEX_OK = re.compile(r"[a-z0-9]+")


def build_ts_idf(conn):
    """IDF over the collection's tsvector lexemes (ndoc from ts_stat)."""
    with conn.cursor() as cur:
        cur.execute("""SELECT count(*) FROM langchain_pg_embedding e
                       JOIN langchain_pg_collection col ON col.uuid=e.collection_id
                       WHERE col.name=%s""", (ab.COLLECTION,))
        n = cur.fetchone()[0]
        cur.execute("""SELECT word, ndoc FROM ts_stat(
            'SELECT content_tsv FROM langchain_pg_embedding e
             JOIN langchain_pg_collection col ON col.uuid=e.collection_id
             WHERE col.name = ''data_science_skills''')""")
        idf = {w: math.log((n - nd + 0.5) / (nd + 0.5) + 1) for w, nd in cur.fetchall()}
    return idf, n


def ts_bm25_seed(conn, idf, query, k):
    """True BM25 (b=0) over the tsvector column; tf from position counts."""
    with conn.cursor() as cur:
        cur.execute("SELECT tsvector_to_array(to_tsvector('english', %s))", (query,))
        lex = [l for l in (cur.fetchone()[0] or []) if _LEX_OK.fullmatch(l)]
    if not lex:
        return []
    tsq = " | ".join(lex)
    with conn.cursor() as cur:
        cur.execute("""
            SELECT e.cmetadata->>'chunk_id', e.cmetadata->>'skill_slug',
                   u.lexeme, array_length(u.positions, 1) AS tf
            FROM langchain_pg_embedding e
            JOIN langchain_pg_collection col ON col.uuid=e.collection_id,
            LATERAL unnest(e.content_tsv) u
            WHERE col.name=%s AND e.content_tsv @@ to_tsquery('english', %s)
              AND u.lexeme = ANY(%s)
        """, (ab.COLLECTION, tsq, lex))
        rows = cur.fetchall()
    agg = {}
    for cid, slug, lexeme, tf in rows:
        tf = tf or 1
        contrib = idf.get(lexeme, 0.0) * (tf * (BM25_K1 + 1)) / (tf + BM25_K1)
        if cid not in agg:
            agg[cid] = [slug, 0.0]
        agg[cid][1] += contrib
    scored = [(cid, "", v[0], v[1]) for cid, v in agg.items()]
    scored.sort(key=lambda x: x[-1], reverse=True)
    return scored[:k]


def cfg(name, query, store, conn, idf, k):
    emb = srv.cosine_seed(store, query, ex.CAND_K)
    if not emb:
        return []
    if name == "E":
        rows = emb
    elif name == "Xenrich":
        rows = ex._rrf(emb, bm.lexical_seed_bm25(conn, query, ex.CAND_K))
    elif name == "Xts":
        rows = ex._rrf(emb, srv.ts_bm25_seed(conn, query, ex.CAND_K))
    else:
        raise ValueError(name)
    order = []
    for r in rows:
        if r[2] not in order:
            order.append(r[2])
    return order[:k]


CONFIGS = ("E", "Xenrich", "Xts")


def run(k):
    store = srv._get_store()
    conn = psycopg.connect(**tp.PG_RAW)
    bm.build_idf(conn)
    idf, n = build_ts_idf(conn)
    print(f"ts BM25: {len(idf)} lexemes over {n} chunks (b=0, equidistant-chunk assumption)", flush=True)
    CUTS = [c for c in (5, 10, 20) if c <= k] or [k]
    try:
        gold = bd._verify_gold(conn)
        print(f"\n=== BM25-LANE eval (tsvector): {len(gold)} bridging queries, k={k} ===", flush=True)
        hdr = "  " + f"{'config':>10}" + "".join(f"{'R@'+str(c):>8}" for c in CUTS) + \
              "".join(f"{'nDCG@'+str(c):>9}" for c in CUTS) + f"{'MRR':>8}"
        print(hdr, flush=True)
        m = len(gold); res = {}
        for c in CONFIGS:
            recs = {cut: 0.0 for cut in CUTS}; nds = {cut: 0.0 for cut in CUTS}; mrr = 0.0
            for q, gs in gold:
                ranked = cfg(c, q, store, conn, idf, k)
                rel = set(gs)
                for cut in CUTS:
                    r, _, nd = tp.score(ranked, rel, cut)
                    recs[cut] += r; nds[cut] += nd
                mrr += next((1.0/(i+1) for i, s in enumerate(ranked) if s in rel), 0.0)
            res[c] = (recs, nds, mrr)
            print("  " + f"{c:>10}" + "".join(f"{recs[cut]/m:>8.3f}" for cut in CUTS) +
                  "".join(f"{nds[cut]/m:>9.3f}" for cut in CUTS) + f"{mrr/m:>8.3f}", flush=True)
        big = CUTS[-1]; be, bn, bmr = res["E"]
        br, bnn, bm_ = be[big]/m, bn[big]/m, bmr/m
        print(f"\n  deltas vs dense (E) — R@{big} / nDCG@{big} / MRR:", flush=True)
        for c in CONFIGS:
            if c == "E":
                continue
            r, nn, mr = res[c]
            print(f"    {c:>10}  {r[big]/m-br:+.3f} / {nn[big]/m-bnn:+.3f} / {mr/m-bm_:+.3f}", flush=True)
    finally:
        conn.close()


if __name__ == "__main__":
    ap = argparse.ArgumentParser(description=__doc__)
    ap.add_argument("--k", type=int, default=20)
    args = ap.parse_args()
    run(args.k)
