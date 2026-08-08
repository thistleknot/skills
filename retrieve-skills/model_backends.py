"""Model scorer singletons for skill-router.

Purpose: wire real models to the injectable scorer slots in router_core.route:
- embed_fn: sentence-transformers bi-encoder (recall stage; default MiniLM-L6)
- rerank_fn: jina-colbert-v2 via pylate (local) or Jina Reranker API, or
  'none' (pass-through: preserves recall order)

Preconditions: models are downloaded on first use (network + disk); Jina API
backend requires JINA_API_KEY. Singletons are lazy so the server starts fast
and /health reports which stages are warm.

Failure modes: import/load errors raise at first use — server.py catches per
request and fails open (returns no skills). API backend errors raise
RuntimeError with the HTTP body for the log.
"""
from __future__ import annotations

import json
import os
import urllib.request
from functools import lru_cache

EMBED_MODEL = os.environ.get("SKILL_ROUTER_EMBED_MODEL", "sentence-transformers/all-MiniLM-L6-v2")
RERANK_BACKEND = os.environ.get("SKILL_ROUTER_RERANK", "none")  # api | local | none
# API backend wants the bare model name; pylate wants a full hub id / local path.
RERANK_MODEL = os.environ.get("SKILL_ROUTER_RERANK_MODEL", "jina-colbert-v2")
RERANK_LOCAL_MODEL = os.environ.get(
    "SKILL_ROUTER_RERANK_LOCAL_MODEL", "jinaai/jina-colbert-v2-64"
)


def _stub_embedder():
    """Deterministic hash-bucket bag-of-words embedder (256 dims).

    Purpose: run the full server modelless for integration tests and dev
    (SKILL_ROUTER_EMBED_MODEL=stub). NOT for production routing quality.
    """
    import hashlib

    import numpy as np

    def embed_fn(texts: list[str]):
        out = np.zeros((len(texts), 256), dtype=np.float32)
        for i, t in enumerate(texts):
            for w in t.lower().split():
                out[i, int(hashlib.md5(w.encode()).hexdigest(), 16) % 256] += 1.0
        return out

    return embed_fn


@lru_cache(maxsize=1)
def get_embedder():
    if EMBED_MODEL == "stub":
        return _stub_embedder()
    import torch
    from sentence_transformers import SentenceTransformer

    device = os.environ.get("SKILL_ROUTER_DEVICE", "cpu")
    model = SentenceTransformer(EMBED_MODEL, device=device)

    def embed_fn(texts: list[str]):
        return model.encode(texts, normalize_embeddings=True)

    return embed_fn


def _rerank_api(query: str, docs: list[str]) -> list[float]:
    """Jina Reranker API (model jina-colbert-v2). Require: JINA_API_KEY set.

    Guarantee: returns one score per input doc, in input order.
    """
    key = os.environ.get("JINA_API_KEY")
    if not key:
        raise RuntimeError("JINA_API_KEY not set; use SKILL_ROUTER_RERANK=local|none")
    body = json.dumps(
        {"model": RERANK_MODEL, "query": query, "documents": docs, "top_n": len(docs)}
    ).encode()
    req = urllib.request.Request(
        "https://api.jina.ai/v1/rerank",
        data=body,
        headers={"Content-Type": "application/json", "Authorization": f"Bearer {key}"},
    )
    with urllib.request.urlopen(req, timeout=10) as r:
        resp = json.load(r)
    scores = [0.0] * len(docs)
    for item in resp["results"]:
        scores[item["index"]] = float(item["relevance_score"])
    return scores


@lru_cache(maxsize=1)
def _get_local_colbert():
    from pylate import models, rank

    device = os.environ.get("SKILL_ROUTER_DEVICE", "cpu")
    model = models.ColBERT(model_name_or_path=RERANK_LOCAL_MODEL, trust_remote_code=True, device=device)

    def rerank_fn(query: str, docs: list[str]) -> list[float]:
        q_emb = model.encode([query], is_query=True)
        d_emb = model.encode([docs], is_query=False)
        ranked = rank.rerank(
            documents_ids=[list(range(len(docs)))],
            queries_embeddings=q_emb,
            documents_embeddings=d_emb,
        )[0]
        scores = [0.0] * len(docs)
        for item in ranked:
            scores[int(item["id"])] = float(item["score"])
        return scores

    return rerank_fn


def get_reranker():
    """Return rerank_fn per SKILL_ROUTER_RERANK: api | local | none."""
    if RERANK_BACKEND == "local":
        return _get_local_colbert()
    if RERANK_BACKEND == "none":
        return lambda query, docs: [float(len(docs) - i) for i in range(len(docs))]
    return _rerank_api
