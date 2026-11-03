"""Ensemble-lift gamut: does combining retrieval signals beat dense alone?

Signals available on this corpus:
  dense    - nomic cosine (pgvector)
  colbert  - ColBERT v2 late interaction (rerank)
  graph    - neo4j entity-expansion (recall broadener, no query-graph)
  lexical  - synset/hypernym overlap ("entities as BM25 surrogate"): query
             content words -> first WordNet synset+hypernym -> match chunks'
             cmetadata.enrich_tokens, ranked by overlap count.

Configs (the gamut) — each returns ranked skills; we report skill-level
recall@k / MRR / nDCG@10 vs the dense baseline E, on the held-out-passage set
(has headroom) and description set (near-saturated floor).

Run:  python experiments.py --n 80
"""

import argparse
import json
import re
import sys
from pathlib import Path

import numpy as np
import psycopg
from nltk.corpus import wordnet as wn
from nltk.corpus import stopwords

sys.path.insert(0, str(Path(__file__).parent))
import mcp_server as srv          # noqa: E402
import eval_ablation as ab        # noqa: E402  (golden_pairs, metrics_for, _expand_ranked, _fetch_embeddings, _mmr)

PG_RAW = ab.PG_RAW
COLLECTION = ab.COLLECTION
CAND_K = 144
FINAL_K = 10
_STOP = set(stopwords.words("english"))


def _rank_to_skills(rows):
    order = []
    for r in rows:
        if r[2] not in order:
            order.append(r[2])
    return order[:FINAL_K]


def _rrf(list_a, list_b, k_out=CAND_K, rrf_k=60):
    """RRF over two ranked chunk lists (rows: (cid,content,slug,score))."""
    ra = {r[0]: i for i, r in enumerate(list_a)}
    rb = {r[0]: i for i, r in enumerate(list_b)}
    by = {r[0]: r for r in list_a}; by.update({r[0]: r for r in list_b})
    wa, wb = len(list_a), len(list_b)
    scored = [(r[0], r[1], r[2], 1/(rrf_k+ra.get(cid, wa)) + 1/(rrf_k+rb.get(cid, wb)))
              for cid, r in by.items()]
    scored.sort(key=lambda x: x[-1], reverse=True)
    return scored[:k_out]


# --- lexical (synset/hypernym surrogate) leg -------------------------------

def _query_syn_tokens(query: str) -> list:
    toks = []
    for w in re.findall(r"[a-zA-Z]+", query.lower()):
        if w in _STOP or len(w) < 3:
            continue
        syns = wn.synsets(w)
        if syns:
            toks.append(syns[0].name())
            hyp = syns[0].hypernyms()
            if hyp:
                toks.append(hyp[0].name())
    return list(set(toks))


def lexical_seed(conn, query: str, k: int) -> list:
    toks = _query_syn_tokens(query)
    if not toks:
        return []
    with conn.cursor() as cur:
        cur.execute(f"""
            SELECT e.cmetadata->>'chunk_id', e.document, e.cmetadata->>'skill_slug',
              (SELECT count(*) FROM jsonb_array_elements_text(e.cmetadata->'enrich_tokens') t
               WHERE t = ANY(%s))::float AS ov
            FROM langchain_pg_embedding e JOIN langchain_pg_collection col
              ON col.uuid=e.collection_id
            WHERE col.name=%s AND e.cmetadata->'enrich_tokens' ?| %s
            ORDER BY ov DESC LIMIT %s
        """, (toks, COLLECTION, toks, k))
        return cur.fetchall()


# --- configs ----------------------------------------------------------------

def run_config(cfg: str, query: str, exclude: str, store, driver, conn) -> list:
    # store/driver/conn are created ONCE by run() and reused — opening a fresh
    # connection per query per config exhausted Postgres ('too many clients').
    emb = [r for r in srv.cosine_seed(store, query, CAND_K) if r[0] != exclude]
    if not emb:
        return []
    if cfg == "E":                                   # dense baseline
        return _rank_to_skills(emb)
    if cfg == "L":                                   # dense -> ColBERT
        return _rank_to_skills(srv.colbert_rerank(query, emb, k=len(emb)))
    if cfg == "EL_rrf":                              # RRF(dense, colbert)
        cb = srv.colbert_rerank(query, emb, k=len(emb))
        return _rank_to_skills(_rrf(emb, cb))
    if cfg == "GL":                                  # dense + graph-recall -> ColBERT
        exp = ab._expand_ranked(driver, conn, [r[0] for r in emb], exclude)
        have = {r[0] for r in emb}; pool = emb + [r for r in exp if r[0] not in have]
        return _rank_to_skills(srv.colbert_rerank(query, pool, k=len(pool)))
    if cfg == "X":                                   # lexical (synset) alone
        return _rank_to_skills([r for r in lexical_seed(conn, query, CAND_K) if r[0] != exclude])
    if cfg == "EX_rrf":                              # RRF(dense, lexical) — the winner
        lex = [r for r in lexical_seed(conn, query, CAND_K) if r[0] != exclude]
        return _rank_to_skills(_rrf(emb, lex))
    if cfg == "EXL":                                 # RRF(dense, lexical) -> ColBERT
        lex = [r for r in lexical_seed(conn, query, CAND_K) if r[0] != exclude]
        fused = _rrf(emb, lex)
        return _rank_to_skills(srv.colbert_rerank(query, fused, k=len(fused)))
    if cfg == "GEXL":                                # kitchen sink: dense+graph+lexical -> ColBERT
        exp = ab._expand_ranked(driver, conn, [r[0] for r in emb], exclude)
        lex = [r for r in lexical_seed(conn, query, CAND_K) if r[0] != exclude]
        have = {r[0] for r in emb}
        base = emb + [r for r in exp if r[0] not in have]
        fused = _rrf(base, lex)
        return _rank_to_skills(srv.colbert_rerank(query, fused, k=len(fused)))
    raise ValueError(cfg)


CONFIGS = ["E", "L", "EL_rrf", "GL", "X", "EX_rrf", "EXL", "GEXL"]


def run(n: int, configs=None) -> None:
    configs = configs or CONFIGS
    gt = ab.golden_pairs(n)
    store, driver = srv._get_store(), srv._get_driver()   # created ONCE, reused
    conn = psycopg.connect(**PG_RAW)
    try:
      for gt_name, pairs in gt.items():
        print(f"\n=== {gt_name}: {len(pairs)} queries ===", flush=True)
        print(f"  {'config':>8} {'recall@1':>9} {'recall@5':>9} {'mrr':>7} {'ndcg@10':>8}  {'vs E':>7}")
        base = None
        table = {}
        for cfg in configs:
            agg = {f"recall@{k}": 0.0 for k in ab.KS}; agg["mrr"] = 0.0; agg["ndcg@10"] = 0.0
            for cid, q, target in pairs:
                m = ab.metrics_for(run_config(cfg, q, cid, store, driver, conn), target)
                for kk in agg:
                    agg[kk] += m[kk]
            for kk in agg:
                agg[kk] = round(agg[kk] / max(len(pairs), 1), 3)
            table[cfg] = agg
            if cfg == "E":
                base = agg["ndcg@10"]
            vs = "" if base is None else f"{agg['ndcg@10']-base:+.3f}"
            print(f"  {cfg:>8} {agg['recall@1']:>9} {agg['recall@5']:>9} {agg['mrr']:>7} {agg['ndcg@10']:>8}  {vs:>7}", flush=True)
        winner = max(table, key=lambda c: table[c]["ndcg@10"])
        print(f"  best: {winner}  nDCG@10={table[winner]['ndcg@10']}  (E={base})", flush=True)
        (Path(__file__).parent / f"experiments_{gt_name}.json").write_text(
            json.dumps(table, indent=2), encoding="utf-8")
    finally:
        conn.close()


if __name__ == "__main__":
    ap = argparse.ArgumentParser(description=__doc__)
    ap.add_argument("--n", type=int, default=80)
    args = ap.parse_args()
    run(args.n)
