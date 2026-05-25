"""brown_retrieval_eval.py — RAGAS-style retrieval comparison on Brown corpus.

Compares four retrieval systems:
  dense_only    — nomic-embed-text cosine similarity (Ollama)
  bm25_full     — BM25 over full corpus (rank_bm25, BM25Okapi)
  hybrid_rrf    — Reciprocal Rank Fusion: dense + bm25_full
  proxy_louvain — dense top-50 → k-means on proxy TF-IDF (2000-para sample)
                  → pairwise BM25 within clusters → Louvain rerank

Judge metrics (qwen3.5:4b via Ollama, single structured call per system):
  relevance              — answer addresses the question
  entailment             — answer logically entailed by retrieved context
  faithfulness           — answer claims grounded in context
  correctness            — factual content matches context
  context_entity_precision — context entities relevant to the question
  context_entity_recall  — key answer entities surface in context
  factualness            — all stated facts supported by context
  fluency                — grammatical correctness and readability
  coherence              — internal logical structure of the answer
  informativeness        — specific, useful information density

  Plus two label-based metrics (no LLM needed):
  context_precision  — fraction of top-K from same Brown category
  context_recall     — |same-cat in top-K| / min(|same-cat total|, K)

Pipeline per query:
  1. qwen3.5:4b generates an open-ended factual question from the source paragraph
  2. each system retrieves top-K docs
  3. qwen3.5:4b generates an answer from retrieved context
  4. single structured call scores all 10 LLM metrics via Pydantic JSON schema

Thinking suppression: think=False (top-level Ollama field) + /no_think system prefix.

Ground truth: same Brown category = relevant for context_precision / context_recall.
Query set  : 30 paragraphs (CDF-diff stratified).
Embeddings : checkpointed to SQLite to avoid recomputation.

Require:
  pydantic, rank_bm25, networkx>=2.7, nltk(brown corpus), scikit-learn, scipy, numpy, requests
  Ollama running on localhost:11434 with nomic-embed-text and qwen3.5:4b pulled.
"""

import math
import pickle
import re
import sqlite3
import time
import numpy as np
import networkx as nx
import requests
from collections import defaultdict
from pathlib import Path
from typing import Optional

from pydantic import BaseModel, Field

import nltk
from nltk.corpus import brown
from scipy.stats import median_abs_deviation, norm
from sklearn.preprocessing import PowerTransformer
from sklearn.feature_extraction.text import TfidfVectorizer
from sklearn.cluster import KMeans
from rank_bm25 import BM25Okapi

CKPT = Path(__file__).parent / "retrieval_eval.db"
K = 10           # retrieval depth for all metrics
DENSE_POOL = 50  # dense candidates fed to proxy reranker
OLLAMA = "http://localhost:11434"
LLM_MODEL  = "qwen3.5:4b"
EMB_MODEL  = "nomic-embed-text"
N_QUERIES  = 30   # query budget (LLM calls ≈ N * (1 + 4*(1+1)) = N*9)



# ── checkpoint ────────────────────────────────────────────────────────────────

def _db():
    db = sqlite3.connect(CKPT)
    db.execute("CREATE TABLE IF NOT EXISTS cache (key TEXT PRIMARY KEY, value BLOB)")
    db.commit()
    return db


def _get(db, key):
    row = db.execute("SELECT value FROM cache WHERE key=?", (key,)).fetchone()
    return pickle.loads(row[0]) if row else None


def _set(db, key, value):
    db.execute("INSERT OR REPLACE INTO cache VALUES (?,?)", (key, pickle.dumps(value)))
    db.commit()


# ── Ollama helpers ────────────────────────────────────────────────────────────

def _strip_think(text: str) -> str:
    """Remove <think>...</think> blocks that Qwen3 emits in thinking mode."""
    return re.sub(r"<think>.*?</think>", "", text, flags=re.DOTALL).strip()


def llm(
    prompt: str,
    max_tokens: int = 300,
    fmt: Optional[dict] = None,
    system: str = "/no_think You are a precise evaluation assistant.",
) -> str:
    """
    Call qwen3.5:4b via Ollama /api/generate with thinking suppressed.

    Thinking is disabled two ways:
      1. think=False at the top-level JSON field (Ollama-specific for Qwen3)
      2. /no_think prefix in the system prompt (model-level instruction)

    Require: Ollama running on localhost:11434 with qwen3.5:4b pulled.
    Guarantee: returns response text; raises on connection failure.
    """
    body: dict = {
        "model": LLM_MODEL,
        "system": system,
        "prompt": prompt,
        "stream": False,
        "think": False,
        "options": {"temperature": 0, "num_predict": max_tokens, "seed": 42},
    }
    if fmt is not None:
        body["format"] = fmt
    resp = requests.post(f"{OLLAMA}/api/generate", json=body, timeout=120)
    resp.raise_for_status()
    return resp.json()["response"].strip()


def embed_batch(texts: list[str], db, cache_key: str) -> np.ndarray:
    """
    Embed a list of texts with nomic-embed-text via Ollama, L2-normalised.
    Results are checkpointed so re-runs skip the API calls.

    Require: texts non-empty, Ollama running with nomic-embed-text pulled.
    Guarantee: returns float32 array shape (len(texts), embedding_dim).
    """
    cached = _get(db, cache_key)
    if cached is not None:
        return cached

    print(f"  Embedding {len(texts):,} texts with {EMB_MODEL}...")
    vecs = []
    batch_size = 64
    for i in range(0, len(texts), batch_size):
        batch = texts[i : i + batch_size]
        resp = requests.post(
            f"{OLLAMA}/api/embed",
            json={"model": EMB_MODEL, "input": batch},
            timeout=300,
        )
        resp.raise_for_status()
        vecs.extend(resp.json()["embeddings"])
        if i % 512 == 0 and i > 0:
            print(f"    {i}/{len(texts)}")

    arr = np.array(vecs, dtype=np.float32)
    norms = np.linalg.norm(arr, axis=1, keepdims=True)
    arr = arr / np.where(norms > 1e-9, norms, 1.0)
    _set(db, cache_key, arr)
    print("  Embeddings cached.")
    return arr


# ── corpus ────────────────────────────────────────────────────────────────────

def build_corpus() -> list[dict]:
    """
    Return all Brown paragraphs with ≥10 alpha tokens as dicts:
    {id, text, tokens, category}
    """
    docs = []
    for cat in sorted(brown.categories()):
        for fid in brown.fileids(categories=cat):
            for para in brown.paras(fid):
                tokens = [w.lower() for s in para for w in s if w.isalpha()]
                if len(tokens) >= 10:
                    docs.append({
                        "id": len(docs),
                        "text": " ".join(tokens),
                        "tokens": tokens,
                        "category": cat,
                    })
    return docs


# ── CDF-diff stratified sampling ─────────────────────────────────────────────

def cdf_diff_sample(docs: list[dict], n_sample: int = 2000, seed: int = 42) -> list[int]:
    """
    Sample n_sample document indices using log-normal → MAD-scale →
    Yeo-Johnson → Gaussian CDF-difference weights.
    """
    by_cat = defaultdict(list)
    for i, d in enumerate(docs):
        by_cat[d["category"]].append(i)

    cats = sorted(by_cat.keys())
    counts = np.array([len(by_cat[c]) for c in cats], dtype=float)

    x = np.log1p(counts)
    med = np.median(x)
    mad = median_abs_deviation(x, scale=1.4826)
    x = (x - med) / (mad + 1e-9)

    pt = PowerTransformer(method="yeo-johnson", standardize=False)
    x = pt.fit_transform(x.reshape(-1, 1)).ravel()

    order = np.argsort(x)
    cdf_vals = norm.cdf(x[order])
    w_sorted = np.diff(cdf_vals, prepend=0.0)
    w_sorted /= w_sorted.sum()
    weights = np.empty_like(w_sorted)
    weights[order] = w_sorted

    rng = np.random.default_rng(seed)
    quotas = np.round(weights * n_sample).astype(int)
    quotas = np.maximum(quotas, 1)
    excess = int(quotas.sum()) - n_sample
    for idx in np.argsort(quotas)[::-1]:
        if excess <= 0:
            break
        trim = min(int(quotas[idx]) - 1, excess)
        quotas[idx] -= trim
        excess -= trim

    idxs = []
    for i, cat in enumerate(cats):
        pool = by_cat[cat]
        q = int(quotas[i])
        chosen = rng.choice(len(pool), size=min(q, len(pool)), replace=False)
        idxs.extend(pool[j] for j in chosen)
    return idxs


# ── RAGAS metrics ─────────────────────────────────────────────────────────────

def context_precision(retrieved_cats: list[str], query_cat: str) -> float:
    """Fraction of top-K retrieved docs from the same category (signal-to-noise)."""
    return sum(c == query_cat for c in retrieved_cats[:K]) / K


def context_recall(retrieved_cats: list[str], query_cat: str, total_relevant: int) -> float:
    """
    |same-cat in top-K| / min(total_relevant, K).
    Measures whether retrieval surfaced what was needed.
    """
    hits = sum(c == query_cat for c in retrieved_cats[:K])
    denom = min(total_relevant, K)
    return hits / denom if denom > 0 else 0.0


class JudgeScores(BaseModel):
    """Structured LLM judge output — all 10 metrics in a single response."""

    relevance: float = Field(..., ge=0.0, le=1.0,
        description="Answer directly addresses the question asked.")
    entailment: float = Field(..., ge=0.0, le=1.0,
        description="Answer is logically entailed by the retrieved context.")
    faithfulness: float = Field(..., ge=0.0, le=1.0,
        description="Every answer claim has explicit support in the context.")
    correctness: float = Field(..., ge=0.0, le=1.0,
        description="Factual content of the answer matches the context.")
    context_entity_precision: float = Field(..., ge=0.0, le=1.0,
        description="Named entities in the context are relevant to the question.")
    context_entity_recall: float = Field(..., ge=0.0, le=1.0,
        description="Key entities needed to answer the question appear in the context.")
    factualness: float = Field(..., ge=0.0, le=1.0,
        description="All stated facts are verifiable from the context.")
    fluency: float = Field(..., ge=0.0, le=1.0,
        description="Answer is grammatically correct and readable.")
    coherence: float = Field(..., ge=0.0, le=1.0,
        description="Answer is internally logical and well-structured.")
    informativeness: float = Field(..., ge=0.0, le=1.0,
        description="Answer is specific and provides useful information density.")


def score_all_metrics(
    question: str,
    answer: str,
    context_texts: list[str],
) -> JudgeScores:
    """
    Single structured LLM call returning all 10 judge metrics.

    Uses Ollama format= (JSON schema) so the model returns valid JSON
    matching JudgeScores.  qwen3.5:4b + think=False + /no_think prefix.

    Require: question, answer, and up to 5 context snippets (≤400 chars each).
    Guarantee: returns a JudgeScores instance; falls back to 0.5 on parse failure.
    """
    ctx = "\n\n".join(f"[{i+1}] {t[:400]}" for i, t in enumerate(context_texts[:5]))
    prompt = (
        f"Question: {question}\n\n"
        f"Retrieved Context:\n{ctx}\n\n"
        f"Answer: {answer[:400]}\n\n"
        "Score the Answer on these 10 dimensions, each a float from 0.0 to 1.0:\n"
        "  relevance              – answer addresses the question\n"
        "  entailment             – answer logically follows from context\n"
        "  faithfulness           – all answer claims grounded in context\n"
        "  correctness            – factual content matches context\n"
        "  context_entity_precision – context entities relevant to question\n"
        "  context_entity_recall  – key answer entities present in context\n"
        "  factualness            – all stated facts supported by context\n"
        "  fluency                – grammatical correctness and readability\n"
        "  coherence              – logical structure of the answer\n"
        "  informativeness        – specific, useful information density\n"
        "Return ONLY the JSON object, no commentary."
    )
    schema = JudgeScores.model_json_schema()
    raw = llm(prompt, max_tokens=256, fmt=schema)
    try:
        return JudgeScores.model_validate_json(raw)
    except Exception:
        # fallback: extract floats from any valid JSON fragment
        try:
            import json
            data = json.loads(raw)
            clamped = {k: min(1.0, max(0.0, float(v))) for k, v in data.items()
                       if k in JudgeScores.model_fields}
            defaults = {f: 0.5 for f in JudgeScores.model_fields if f not in clamped}
            return JudgeScores(**{**defaults, **clamped})
        except Exception:
            return JudgeScores(**{f: 0.5 for f in JudgeScores.model_fields})


def generate_question(para_text: str) -> str:
    """Use qwen3.5:4b to generate an open-ended factual question about the paragraph."""
    prompt = (
        f"Read this passage:\n{para_text[:500]}\n\n"
        "Write ONE open-ended factual question (who/what/when/where/why/how) "
        "whose specific answer is directly stated in the passage.\n"
        "Do NOT write a yes/no question.\n"
        "Output only the question, nothing else."
    )
    return llm(prompt, max_tokens=60)


def generate_answer(question: str, context_docs: list[dict]) -> str:
    """Use qwen3.5:4b to answer the question using only the retrieved context."""
    ctx = "\n\n".join(f"[{i+1}] {d['text'][:300]}" for i, d in enumerate(context_docs[:5]))
    prompt = (
        "Answer the question using ONLY the provided context. Be concise.\n\n"
        f"Context:\n{ctx}\n\n"
        f"Question: {question}\n\nAnswer:"
    )
    return llm(prompt, max_tokens=150)


# ── Reciprocal Rank Fusion ────────────────────────────────────────────────────

def rrf_fuse(rank_lists: list[list[int]], rrf_k: int = 60) -> list[int]:
    scores: dict[int, float] = defaultdict(float)
    for ranks in rank_lists:
        for rank, doc_id in enumerate(ranks):
            scores[doc_id] += 1.0 / (rrf_k + rank + 1)
    return sorted(scores.keys(), key=lambda d: -scores[d])


# ── proxy BM25 + Louvain reranker ─────────────────────────────────────────────

def proxy_louvain_rerank(
    dense_top50: list[int],
    docs: list[dict],
    proxy_tfidf: TfidfVectorizer,
    n_clusters: int = 5,
) -> list[int]:
    """
    Project dense candidates into proxy TF-IDF space, k-means cluster,
    pairwise BM25 within each cluster, Louvain community detection,
    rerank by intra-community cohesion score.

    Require:
      dense_top50 — corpus doc indices (at most 50)
      proxy_tfidf — fitted on 2000-para CDF-diff sample

    Guarantee:
      Returns top-K doc indices; falls back to dense order if no graph edges form.
    """
    if len(dense_top50) <= 1:
        return dense_top50[:K]

    cand_texts = [docs[i]["text"] for i in dense_top50]
    vecs = proxy_tfidf.transform(cand_texts)

    n_c = min(n_clusters, len(dense_top50))
    labels = KMeans(n_clusters=n_c, n_init=3, random_state=42).fit_predict(vecs)

    G = nx.Graph()
    G.add_nodes_from(dense_top50)

    for c_id in range(n_c):
        members = [dense_top50[j] for j, lbl in enumerate(labels) if lbl == c_id]
        if len(members) < 2:
            continue
        bm25 = BM25Okapi([docs[i]["tokens"] for i in members])
        for qi, qid in enumerate(members):
            scores = bm25.get_scores(docs[qid]["tokens"])
            for di, did in enumerate(members):
                if di == qi:
                    continue
                w = float(scores[di])
                if w > 0.5:
                    if G.has_edge(qid, did):
                        G[qid][did]["weight"] = max(G[qid][did]["weight"], w)
                    else:
                        G.add_edge(qid, did, weight=w)

    if G.number_of_edges() == 0:
        return dense_top50[:K]

    communities = nx.community.louvain_communities(G, weight="weight", seed=42)
    node_to_comm = {node: cid for cid, comm in enumerate(communities) for node in comm}

    cohesion: dict[int, float] = defaultdict(float)
    for u, v, data in G.edges(data=True):
        if node_to_comm.get(u) == node_to_comm.get(v):
            cohesion[u] += data["weight"]
            cohesion[v] += data["weight"]

    return sorted(
        dense_top50,
        key=lambda d: (-cohesion.get(d, 0.0), dense_top50.index(d)),
    )[:K]


# ── main ──────────────────────────────────────────────────────────────────────

def main():
    nltk.download("brown", quiet=True)
    db = _db()

    print("Building corpus...")
    docs = build_corpus()
    print(f"  {len(docs):,} paragraphs across {len(set(d['category'] for d in docs))} categories")

    # ── dense embeddings (nomic-embed-text, checkpointed) ────────────────────
    emb_key = f"emb_nomic_{len(docs)}"
    embeddings = embed_batch([d["text"] for d in docs], db, emb_key)
    print(f"  Embedding shape: {embeddings.shape}")

    # ── full-corpus BM25 ──────────────────────────────────────────────────────
    print("Building full-corpus BM25 index...")
    bm25_full = BM25Okapi([d["tokens"] for d in docs])

    # ── proxy TF-IDF on 2000-para CDF-diff sample ────────────────────────────
    print("Sampling 2000-para proxy corpus (CDF-diff)...")
    sample_idx = cdf_diff_sample(docs, n_sample=2000, seed=42)
    proxy_tfidf = TfidfVectorizer(max_features=8_000, sublinear_tf=True)
    proxy_tfidf.fit([docs[i]["text"] for i in sample_idx])
    print(f"  Proxy vocab: {len(proxy_tfidf.vocabulary_):,} terms")

    # ── query set ─────────────────────────────────────────────────────────────
    print(f"Sampling {N_QUERIES}-query evaluation set (CDF-diff, seed=99)...")
    query_idx = cdf_diff_sample(docs, n_sample=N_QUERIES, seed=99)
    cat_counts: dict[str, int] = defaultdict(int)
    for d in docs:
        cat_counts[d["category"]] += 1

    # ── evaluation loop ───────────────────────────────────────────────────────
    systems = ["dense_only", "bm25_full", "hybrid_rrf", "proxy_louvain"]
    llm_metrics = list(JudgeScores.model_fields.keys())  # 10 fields
    all_metrics = llm_metrics + ["context_precision", "context_recall"]
    results: dict[str, list[dict]] = {s: [] for s in systems}

    total_calls = N_QUERIES * (1 + len(systems) * 2)  # q_gen + (ans_gen + score_all) per system
    print(f"\nEvaluating {N_QUERIES} queries × {len(systems)} systems")
    print(f"Estimated LLM calls: ~{total_calls}  ({LLM_MODEL})\n")

    t0 = time.time()
    for qi, qidx in enumerate(query_idx):
        qdoc = docs[qidx]
        qcat = qdoc["category"]
        qtoks = qdoc["tokens"]
        qemb = embeddings[qidx]

        print(f"[{qi+1:02d}/{N_QUERIES}] cat={qcat}  generating question...")
        question = generate_question(qdoc["text"])

        # retrieve top-50 dense (exclude self)
        cos = embeddings @ qemb
        cos[qidx] = -1.0
        dense50 = list(np.argsort(cos)[::-1][:DENSE_POOL])
        dense10 = dense50[:K]

        # full BM25 top-K
        bm25_scores = bm25_full.get_scores(qtoks)
        bm25_scores[qidx] = -1.0
        bm25_10 = list(np.argsort(bm25_scores)[::-1][:K])

        # hybrid RRF
        rrf_10 = rrf_fuse([dense50, bm25_10])[:K]

        # proxy Louvain
        proxy_10 = proxy_louvain_rerank(dense50, docs, proxy_tfidf)

        for sys_name, top10 in zip(systems, [dense10, bm25_10, rrf_10, proxy_10]):
            retrieved_docs  = [docs[i] for i in top10]
            retrieved_cats  = [d["category"] for d in retrieved_docs]
            context_texts   = [d["text"] for d in retrieved_docs]
            total_rel       = cat_counts[qcat] - 1

            answer = generate_answer(question, retrieved_docs)
            scores = score_all_metrics(question, answer, context_texts)

            rec = scores.model_dump()
            rec["context_precision"] = context_precision(retrieved_cats, qcat)
            rec["context_recall"]    = context_recall(retrieved_cats, qcat, total_rel)
            results[sys_name].append(rec)

        elapsed = time.time() - t0
        print(f"  done  ({elapsed:.0f}s elapsed)")

    # ── results table ─────────────────────────────────────────────────────────
    col = 9
    hdr = f"{'System':<16}" + "".join(f"{m[:col-1]:>{col}}" for m in all_metrics) + f"{'composite':>{col}}"
    print("\n" + "=" * len(hdr))
    print(hdr)
    print("-" * len(hdr))

    # composite: equal weight across all 12 metrics
    composite_scores = {}
    for sys_name in systems:
        recs = results[sys_name]
        v = {m: float(np.mean([r[m] for r in recs])) for m in all_metrics}
        comp = float(np.mean(list(v.values())))
        composite_scores[sys_name] = comp
        row = f"{sys_name:<16}" + "".join(f"{v[m]:>{col}.3f}" for m in all_metrics) + f"{comp:>{col}.3f}"
        print(row)

    print("=" * len(hdr))
    best = max(composite_scores, key=composite_scores.__getitem__)
    print(f"\nBest composite: {best}  ({composite_scores[best]:.4f})")
    print()
    print(f"LLM judge : {LLM_MODEL}")
    print(f"Embeddings: {EMB_MODEL}")
    print(f"Queries   : {N_QUERIES}  |  K={K}  |  proxy_pool={DENSE_POOL}")


if __name__ == "__main__":
    main()
