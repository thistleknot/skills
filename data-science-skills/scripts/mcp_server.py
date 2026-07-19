"""FastMCP server: graph-augmented hybrid retrieval over data_science_skills.

Cascade (see ../references/retrieval.md):
  cosine seed (langchain PGVector)  ─┐
                                      ├─ RRF ─► graph expansion ─► MMR ─► ColBERT ─► whole-skill
  graph-density (neo4j) ─────────────┘         (neo4j)                              return

GRAPH_MODE controls the graph's role (the open question the eval settles):
  - "parallel": graph-density is the 2nd RRF leg beside cosine (operator's
    original "entity density as the parallel signal" design), no expansion.
  - "cascade":  cosine seeds, then expand outward through the graph.
  - "both":     RRF(cosine, density) AND expansion (default).

Storage is langchain PGVector (cmetadata JSONB); the entity graph lives in the
dedicated dss-neo4j (Chunk/Entity/Skill nodes). No BM25 sparse leg — the
entity/graph signal IS the parallel-to-semantic signal ("entities as BM25
surrogates").

Retrieval unit = whole skill: the ranked chunks vote for their skill; the top
skills are returned with ALL their chunks (a skill is one piece of knowledge).

Plain callables hold the logic; @mcp.tool() wrappers are thin (a decorated
function becomes a non-callable FunctionTool, so tests/other code call the
plain versions).
"""

import json
import math

import numpy as np
import psycopg
import requests
import torch
from fastmcp import FastMCP
from langchain_ollama import OllamaEmbeddings
from langchain_postgres import PGVector
from neo4j import GraphDatabase
from transformers import AutoModel, AutoTokenizer

OLLAMA_URL = "http://localhost:11434"
EMBED_MODEL = "nomic-embed-text"
PG_CONN = "postgresql+psycopg://langchain:langchain@localhost:5432/langchain"
PG_RAW = dict(host="localhost", port=5432, dbname="langchain",
              user="langchain", password="langchain")
COLLECTION = "data_science_skills"
NEO4J_URI = "bolt://localhost:7688"
COLBERT_MODEL = "colbert-ir/colbertv2.0"

# RETRIEVAL_MODE — set by deterministic bridging eval (eval_bm25_lane.py /
# eval_topic_route.py, n=33 fixed-gold bridging queries, deltas vs dense):
#   config                 R@20    nDCG@20   MRR      verdict
#   dense (E)              0.475   0.237     0.203    baseline
#   hybrid (dense⊕ts-BM25) +0.202 +0.151   +0.166    <- WINS all cutoffs, LOW variance
#   route  (ToC top-2)     +0.101 +0.084   +0.077    2nd; high variance, gold-inflated
#   fusion (entity-BM25)   +0.045 +0.012   +0.017    marginal (sub-5%)
#   graph  (ontology hop)  -0.015 -0.030   -0.046    net-negative
# HYBRID is the winner by 2x: true BM25 over the native tsvector column (full
# snowball-stemmed CONTENT, real tf, b=0 since HybridChunker keeps chunks ~equal
# length) RRF-fused with dense. The old entity/synset "enrich_tokens" BM25 was a
# lossy surrogate — decisively beaten by plain content BM25. Entity/SPO extraction
# now serves GRAPH CONSTRUCTION only (neo4j), not lexical retrieval.
#   "hybrid" : dense ⊕ tsvector-BM25 RRF (DEFAULT — the measured winner)
#   "dense"  : cosine only (floor)
#   "route"  : dense ⊕ top-2 topic-routed RRF (2nd; high variance)
#   "fusion" : dense ⊕ entity-BM25 RRF (legacy enrich-token lane; marginal)
#   "cascade": full diagnostic cascade (graph expand + MMR + ColBERT) — net-negative
RETRIEVAL_MODE = "hybrid"
ROUTE_TOPICS = 2             # top-t topics per query (top-2 beat top-3 on MRR/nDCG)
GRAPH_MODE = "both"          # parallel | cascade | both  (cascade mode only)
COSINE_K = 100
GRAPH_RRF_WEIGHT = 0.5
RRF_K = 60
RRF_K_OUT = 50
EXPANSION_HOPS = 1
EXPANSION_DISCOUNT = 0.5
EXPANDED_K = 80
MMR_LAMBDA = 0.7
MMR_K = 30
TOP_SKILLS = 5               # whole-skill units returned

mcp = FastMCP("data-science-skills")

_ct = _cm = None
_embeddings = None
_driver = None


def _get_colbert():
    global _ct, _cm
    if _cm is None:
        _ct = AutoTokenizer.from_pretrained(COLBERT_MODEL)
        _cm = AutoModel.from_pretrained(COLBERT_MODEL)
        if torch.cuda.is_available():
            _cm = _cm.to("cuda:0")
        _cm.eval()
    return _ct, _cm


def _get_store():
    global _embeddings
    if _embeddings is None:
        _embeddings = OllamaEmbeddings(model=EMBED_MODEL, base_url=OLLAMA_URL)
    return PGVector(embeddings=_embeddings, collection_name=COLLECTION,
                    connection=PG_CONN, use_jsonb=True)


def _get_driver():
    global _driver
    if _driver is None:
        _driver = GraphDatabase.driver(NEO4J_URI, auth=None)
    return _driver


# =============================================================================
# Stage 1a — cosine seed (langchain PGVector)
# =============================================================================

def cosine_seed(store, query: str, k: int) -> list:
    """Returns [(chunk_id, content, skill_slug, cos_sim), ...] best-first."""
    hits = store.similarity_search_with_score(query, k=k)
    rows = []
    for doc, dist in hits:
        m = doc.metadata
        rows.append((m["chunk_id"], doc.page_content, m["skill_slug"], 1.0 - float(dist)))
    return rows


# =============================================================================
# ToC / topic routing — the measured winner (see RETRIEVAL_MODE note).
# "ToC-seeded query expansion" for the closed 11-folder vocab = classify the
# query into its top-ROUTE_TOPICS topics via cosine against precomputed topic
# centroids (O(1), no LLM), then surface within-topic candidates dense missed.
# =============================================================================

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
_topic_labels = _topic_vecs = None


def _get_topic_centroids(store):
    """Embed the 11 topic descriptions once (cached). Guarantee: unit-normed."""
    global _topic_labels, _topic_vecs
    if _topic_vecs is None:
        labels = list(TOPIC_DESC.keys())
        v = np.array(store.embeddings.embed_documents([TOPIC_DESC[t] for t in labels]), dtype=float)
        v /= (np.linalg.norm(v, axis=1, keepdims=True) + 1e-9)
        _topic_labels, _topic_vecs = labels, v
    return _topic_labels, _topic_vecs


def route_topics(store, query: str, t: int) -> list:
    """Query -> its top-t taxonomy folders (cosine vs topic centroids)."""
    labels, cvecs = _get_topic_centroids(store)
    q = np.array(store.embeddings.embed_query(query), dtype=float)
    q /= (np.linalg.norm(q) + 1e-9)
    return [labels[i] for i in np.argsort(-(cvecs @ q))[:t]]


def topic_branch(store, query: str, topics: list, k: int) -> list:
    """Dense retrieval RESTRICTED to routed topics (metadata filter). Recalls
    within-topic tail items outside the global cosine top-k."""
    hits = store.similarity_search_with_score(query, k=k, filter={"topic": {"$in": topics}})
    return [(d.metadata["chunk_id"], d.page_content, d.metadata["skill_slug"], 1.0 - float(dist))
            for d, dist in hits]


# =============================================================================
# BM25 lane — true BM25 over the native tsvector column (content_tsv, snowball-
# stemmed, GIN-indexed). The measured winner (+0.202 R@20 fused with dense).
# tf from tsvector position counts; b=0 (HybridChunker => chunks ~equidistant).
# =============================================================================

BM25_K1 = 1.5
BM25_B = 0.0    # length-norm weight; TRUE-dl CV=0.65 (length varies) — eval whether b>0 helps
BM25_AVGDL = 72.1  # exact avg content_len (= sum of tf = true dl) over the collection


def build_bm25_idf(conn) -> int:
    """(Re)materialize the bm25_idf(word, idf) table from content_tsv — run once
    at ingest. IDF = ln((N-ndoc+0.5)/(ndoc+0.5)+1) via ts_stat. Returns lexeme
    count. Require: content_tsv column + GIN index exist (ensure_bm25_ddl)."""
    with conn.cursor() as cur:
        cur.execute("DROP TABLE IF EXISTS bm25_idf")
        cur.execute("""
            CREATE TABLE bm25_idf AS
            WITH n AS (SELECT count(*)::float c FROM langchain_pg_embedding e
                       JOIN langchain_pg_collection col ON col.uuid=e.collection_id
                       WHERE col.name=%s)
            SELECT s.word, ln((n.c - s.ndoc + 0.5)/(s.ndoc + 0.5) + 1) AS idf
            FROM n, ts_stat('SELECT content_tsv FROM langchain_pg_embedding e
                             JOIN langchain_pg_collection col ON col.uuid=e.collection_id
                             WHERE col.name = ''data_science_skills''') s
        """, (COLLECTION,))
        cur.execute("ALTER TABLE bm25_idf ADD PRIMARY KEY (word)")
        cur.execute("SELECT count(*) FROM bm25_idf")
        n = cur.fetchone()[0]
    conn.commit()
    return n


def ts_bm25_seed(conn, query: str, k: int, b: float = None, avgdl: float = None) -> list:
    """True BM25 (k1=1.5) over content_tsv, computed IN-DB in one query: tf from
    lexeme position counts, IDF joined from the materialized bm25_idf. Length norm
    via b (default BM25_B): denom = tf + k1*((1-b) + b*dl/avgdl), dl=length(tsv).
    b=0 drops the length term entirely. Returns [(cid, content, slug, score), ...]."""
    b = BM25_B if b is None else b
    avgdl = BM25_AVGDL if avgdl is None else avgdl
    with conn.cursor() as cur:
        cur.execute("""
            WITH ql AS (SELECT unnest(tsvector_to_array(to_tsvector('english', %(q0)s))) AS lex),
                 orq AS (SELECT string_agg(lex, ' | ') q FROM ql WHERE lex ~ '^[a-z0-9]+$')
            SELECT e.cmetadata->>'chunk_id', e.document, e.cmetadata->>'skill_slug',
                   sum(i.idf * (tf.cnt*(%(k1)s+1.0))
                       / (tf.cnt + %(k1)s*((1.0-%(b)s) + %(b)s*e.content_len/%(avg)s))) AS score
            FROM langchain_pg_embedding e
            JOIN langchain_pg_collection col ON col.uuid=e.collection_id
            JOIN LATERAL (SELECT u.lexeme lx, array_length(u.positions,1) cnt
                          FROM unnest(e.content_tsv) u
                          WHERE u.lexeme IN (SELECT lex FROM ql)) tf ON true
            JOIN bm25_idf i ON i.word = tf.lx
            WHERE col.name=%(col)s AND (SELECT q FROM orq) <> ''
              AND e.content_tsv @@ to_tsquery('english', (SELECT q FROM orq))
            GROUP BY e.cmetadata->>'chunk_id', e.document, e.cmetadata->>'skill_slug'
            ORDER BY score DESC LIMIT %(k)s
        """, {"q0": query, "k1": BM25_K1, "b": b, "avg": avgdl, "col": COLLECTION, "k": k,
              # psycopg named+positional can't mix; pass query via named too:
              })
        return [(cid, doc, slug, float(sc)) for cid, doc, slug, sc in cur.fetchall()]


# =============================================================================
# Graph signals from neo4j (density + expansion)
# =============================================================================

def graph_density(driver, chunk_ids: list) -> dict:
    """Per-chunk structural score: summed CO_OCCURS weight over the chunk's
    entities, normalized by entity count. Pure neo4j (Chunk nodes present)."""
    if not chunk_ids:
        return {}
    q = """
        UNWIND $ids AS cid
        MATCH (c:Chunk {id: cid})-[:HAS_ENTITY]->(e:Entity)
        OPTIONAL MATCH (e)-[r:CO_OCCURS]-()
        WITH cid, count(DISTINCT e) AS n, coalesce(sum(r.weight), 0) AS w
        RETURN cid AS id, CASE WHEN n > 0 THEN toFloat(w) / n ELSE 0.0 END AS density
    """
    with driver.session() as s:
        return {r["id"]: r["density"] for r in s.run(q, ids=chunk_ids)}


EXPAND_SEED_CAP = 20    # only expand from the strongest seeds
EXPAND_ENTITY_DEGCAP = 60  # skip hub entities (shared by >= this many chunks) — they explode the walk
EXPAND_LIMIT = 200      # cap total expanded chunks


def graph_expand(driver, seed_chunk_ids: list, hops: int) -> set:
    """Neighbor chunk ids that SHARE a (non-hub) entity with a seed chunk, plus
    one CO_OCCURS step. Bounded: caps seeds, drops hub entities (a common term
    linked to thousands of chunks would otherwise blow the walk up — the old
    unbounded `CO_OCCURS*0..h` made this ~20s/query on a 627k-edge graph), and
    LIMITs the result. Pure neo4j; returns chunk ids only."""
    if not seed_chunk_ids:
        return set()
    seeds = seed_chunk_ids[:EXPAND_SEED_CAP]
    q = f"""
        UNWIND $ids AS cid
        MATCH (:Chunk {{id: cid}})-[:HAS_ENTITY]->(e:Entity)
        WITH DISTINCT e WHERE count{{ (e)<-[:HAS_ENTITY]-(:Chunk) }} < $degcap
        MATCH (e)-[:CO_OCCURS*0..{hops}]-(ne:Entity)<-[:HAS_ENTITY]-(c2:Chunk)
        WHERE count{{ (ne)<-[:HAS_ENTITY]-(:Chunk) }} < $degcap AND NOT c2.id IN $ids
        RETURN DISTINCT c2.id AS id
        LIMIT $lim
    """
    with driver.session() as s:
        return {r["id"] for r in s.run(q, ids=seeds, degcap=EXPAND_ENTITY_DEGCAP, lim=EXPAND_LIMIT)}


# =============================================================================
# RRF, MMR, ColBERT
# =============================================================================

def rrf_fuse(cosine_rows: list, densities: dict, k_out: int) -> list:
    """Parallel step. RRF of the cosine ranking with the graph-density ranking
    over the cosine candidate pool. Returns [(chunk_id, content, skill_slug,
    fused), ...]."""
    cos_rank = {r[0]: i for i, r in enumerate(cosine_rows)}
    dens_rank = {cid: i for i, cid in enumerate(
        sorted(densities, key=densities.get, reverse=True))}
    worst = len(cosine_rows)
    scored = []
    for r in cosine_rows:
        cid = r[0]
        score = (GRAPH_RRF_WEIGHT / (RRF_K + dens_rank.get(cid, worst))
                 + (1 - GRAPH_RRF_WEIGHT) / (RRF_K + cos_rank.get(cid, worst)))
        scored.append((*r, score))
    scored.sort(key=lambda x: x[-1], reverse=True)
    return scored[:k_out]


def mmr_rerank(pool: list, cosine_sims: dict, densities: dict, k: int) -> list:
    """Diversity rerank over a [cosine, density, fused] score matrix (arxiv
    mmr_from_scores pattern)."""
    if not pool:
        return pool
    matrix = np.array([[cosine_sims.get(r[0], 0.0), densities.get(r[0], 0.0), r[-1]] for r in pool])
    relevance = matrix.sum(axis=1)

    def cos(a, b):
        na, nb = np.linalg.norm(a), np.linalg.norm(b)
        return float(np.dot(a, b) / (na * nb)) if na > 0 and nb > 0 else 0.0

    remaining = list(range(len(pool)))
    selected = [max(remaining, key=lambda i: relevance[i])]
    remaining.remove(selected[0])
    while remaining and len(selected) < k:
        nxt = max(remaining, key=lambda i:
                  MMR_LAMBDA * relevance[i]
                  - (1 - MMR_LAMBDA) * max((cos(matrix[i], matrix[j]) for j in selected), default=0.0))
        selected.append(nxt)
        remaining.remove(nxt)
    return [pool[i] for i in selected]


def colbert_rerank(query: str, pool: list, k: int) -> list:
    """MaxSim late interaction (colbert-ir/colbertv2.0 via raw transformers).
    Appends colbert_score, returns top-k."""
    if not pool:
        return pool
    tok, model = _get_colbert()
    dev = "cuda:0" if torch.cuda.is_available() else "cpu"
    mq = " ".join(f"#{t}" for t in query.split())
    qt = tok(mq, max_length=64, padding="max_length", truncation=True, return_tensors="pt").to(dev)
    with torch.no_grad():
        qe = torch.nn.functional.normalize(model(**qt).last_hidden_state, p=2, dim=2)
    scores = []
    for r in pool:
        dt = tok(r[1], max_length=512, padding="max_length", truncation=True, return_tensors="pt").to(dev)
        with torch.no_grad():
            de = torch.nn.functional.normalize(model(**dt).last_hidden_state, p=2, dim=2)
            scores.append(torch.sum(torch.max(torch.matmul(qe[0], de[0].T), dim=1).values).item())
    scores = np.array(scores)
    if scores.size and scores.max() > scores.min():
        scores = (scores - scores.min()) / (scores.max() - scores.min())
    ranked = sorted(zip(pool, scores), key=lambda x: x[1], reverse=True)
    return [(*r, float(sc)) for r, sc in ranked[:k]]


# =============================================================================
# Postgres content fetch (langchain_pg_embedding) + whole-skill load
# =============================================================================

def fetch_chunks(conn, chunk_ids: list) -> dict:
    """chunk_id -> (content, skill_slug) from langchain_pg_embedding."""
    if not chunk_ids:
        return {}
    with conn.cursor() as cur:
        cur.execute("""
            SELECT e.cmetadata->>'chunk_id', e.document, e.cmetadata->>'skill_slug'
            FROM langchain_pg_embedding e JOIN langchain_pg_collection col
              ON col.uuid = e.collection_id
            WHERE col.name = %s AND e.cmetadata->>'chunk_id' = ANY(%s)
        """, (COLLECTION, chunk_ids))
        return {r[0]: (r[1], r[2]) for r in cur.fetchall()}


def load_whole_skills(conn, driver, skill_slugs: list) -> list:
    """Load every chunk of each skill (ordered by chunk_index) + its ToC/tags.
    A skill is one piece of knowledge — return it whole."""
    out = []
    with conn.cursor() as cur:
        for slug in skill_slugs:
            cur.execute("""
                SELECT e.document, e.cmetadata
                FROM langchain_pg_embedding e JOIN langchain_pg_collection col
                  ON col.uuid = e.collection_id
                WHERE col.name = %s AND e.cmetadata->>'skill_slug' = %s
                ORDER BY (e.cmetadata->>'chunk_index')::int
            """, (COLLECTION, slug))
            rows = cur.fetchall()
            if not rows:
                continue
            meta0 = rows[0][1]
            out.append({
                "skill_slug": slug,
                "skill_name": meta0.get("skill_name"),
                "topic": meta0.get("topic"),
                "description": meta0.get("skill_description"),
                "source_books": meta0.get("source_books", []),
                "tags": _skill_tags(driver, slug),
                "content": "\n\n".join(r[0] for r in rows),
            })
    return out


def _skill_tags(driver, slug: str) -> list:
    with driver.session() as s:
        rec = s.run("MATCH (sk:Skill {slug:$slug}) RETURN sk.tags AS tags", slug=slug).single()
        return (rec["tags"] if rec and rec["tags"] else [])


# =============================================================================
# Cascade
# =============================================================================

def run_retrieval(query: str, k: int = TOP_SKILLS) -> str:
    """Return top-k whole skills as JSON, ranked per RETRIEVAL_MODE.

    Require: collection populated (dense); neo4j graph built (cascade only).
    Guarantee: dense mode needs only pgvector — the measured production path for
    topical-cluster retrieval. Raises rather than degrading if a store is
    unreachable. See references/retrieval.md + the RETRIEVAL_MODE eval table."""
    store = _get_store()
    conn = psycopg.connect(**PG_RAW)
    try:
        cosine_rows = cosine_seed(store, query, COSINE_K)
        if not cosine_rows:
            return json.dumps([])

        if RETRIEVAL_MODE == "hybrid":
            # dense ⊕ true-BM25(content tsvector), RRF — the measured winner.
            import experiments as _ex   # lazy: circular at top level
            final = _ex._rrf(cosine_rows, ts_bm25_seed(conn, query, COSINE_K))
        elif RETRIEVAL_MODE == "route":
            # dense ⊕ (dense restricted to the query's top-t routed topics), RRF.
            import experiments as _ex   # lazy: _ex imports this module (circular at top level)
            topics = route_topics(store, query, ROUTE_TOPICS)
            branch = topic_branch(store, query, topics, COSINE_K)
            final = _ex._rrf(cosine_rows, branch)
        elif RETRIEVAL_MODE == "dense":
            final = cosine_rows
        elif RETRIEVAL_MODE == "fusion":
            # dense ⊕ entity-BM25 RRF (exact-skill lookup objective). Lazy import:
            # bm25_experiment imports this module, so top-level would be circular.
            import experiments as _ex
            import bm25_experiment as _bm
            _bm.build_idf(conn)
            lex = _bm.lexical_seed_bm25(conn, query, COSINE_K)
            final = _ex._rrf(cosine_rows, lex)
        elif RETRIEVAL_MODE == "cascade":
            final = _run_cascade(query, cosine_rows, conn)
        else:
            raise ValueError(f"unknown RETRIEVAL_MODE {RETRIEVAL_MODE!r}")

        # whole-skill: rank skills by their best chunk, take top-k, return whole
        skill_order = []
        for r in final:
            if r[2] not in skill_order:
                skill_order.append(r[2])
        skills = load_whole_skills(conn, _get_driver(), skill_order[:k])
        return json.dumps(skills, indent=2)
    finally:
        conn.close()


def _run_cascade(query, cosine_rows, conn):
    """Diagnostic-only full cascade (graph expand + MMR + ColBERT). Measured
    net-negative for both objectives — kept for ablation, not the default path."""
    driver = _get_driver()
    cos_sims = {r[0]: r[3] for r in cosine_rows}
    densities = graph_density(driver, [r[0] for r in cosine_rows])
    if GRAPH_MODE in ("parallel", "both"):
        pool = rrf_fuse(cosine_rows, densities, RRF_K_OUT)
    else:
        pool = [(*r, r[3]) for r in cosine_rows][:RRF_K_OUT]
    if GRAPH_MODE in ("cascade", "both"):
        pool_ids = {r[0] for r in pool}
        neighbors = graph_expand(driver, [r[0] for r in pool], EXPANSION_HOPS) - pool_ids
        if neighbors:
            fetched = fetch_chunks(conn, list(neighbors))
            best = max((r[-1] for r in pool), default=0.0)
            for cid, (content, slug) in fetched.items():
                pool.append((cid, content, slug, best * EXPANSION_DISCOUNT))
            pool.sort(key=lambda x: x[-1], reverse=True)
            pool = pool[:EXPANDED_K]
    exp_dens = graph_density(driver, [r[0] for r in pool])
    mmr_pool = mmr_rerank(pool, cos_sims, exp_dens, k=min(len(pool), MMR_K))
    return colbert_rerank(query, mmr_pool, k=len(mmr_pool))


def run_browse_toc() -> str:
    """Every skill with topic + entity tags (the ToC), from neo4j Skill nodes."""
    driver = _get_driver()
    with driver.session() as s:
        rows = s.run("MATCH (sk:Skill) RETURN sk.slug AS slug, sk.topic AS topic, "
                     "sk.tags AS tags ORDER BY sk.topic, sk.slug").data()
    return json.dumps(rows, indent=2)


@mcp.tool()
def retrieve(query: str, k: int = TOP_SKILLS) -> str:
    """Graph-augmented hybrid retrieval over the data-science skills corpus.
    Returns the top-k whole skills (each with all chunks, ToC + entity tags)."""
    return run_retrieval(query, k)


@mcp.tool()
def browse_toc() -> str:
    """List every skill in the corpus with its topic and entity tags."""
    return run_browse_toc()


if __name__ == "__main__":
    mcp.run()
