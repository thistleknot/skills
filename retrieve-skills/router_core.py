"""Core routing logic for skill-router.

Purpose: deterministic skill selection through recall, rerank, and a
median-margin accept gate. Scorers are injected for production or tests.
"""
from __future__ import annotations

import hashlib
import sqlite3
import time
from dataclasses import dataclass
from pathlib import Path
from typing import Callable

import numpy as np
import yaml


@dataclass
class Skill:
    name: str
    path: str
    description: str


@dataclass
class RouteConfig:
    top_k: int = 34
    rerank_keep: int = 21
    max_accept: int = 2
    rerank_margin: float = 1.5


def parse_frontmatter(text: str) -> dict | None:
    """Extract a YAML frontmatter mapping or return None."""
    text = text.lstrip("\ufeff").replace("\r\n", "\n")
    if not text.startswith("---"):
        return None
    parts = text.split("---", 2)
    if len(parts) < 3:
        return None
    try:
        data = yaml.safe_load(parts[1])
    except yaml.YAMLError:
        return None
    return data if isinstance(data, dict) else None


def skill_body(text: str) -> str:
    """Return SKILL.md content with the frontmatter block removed."""
    text = text.lstrip("\ufeff").replace("\r\n", "\n")
    if text.startswith("---"):
        parts = text.split("---", 2)
        if len(parts) >= 3:
            return parts[2].strip()
    return text.strip()


def discover_skills(store_dir: str | Path) -> list[Skill]:
    """Collect valid top-level <store>/<name>/SKILL.md entries."""
    out: list[Skill] = []
    root = Path(store_dir).resolve()
    for p in sorted(root.glob("*/SKILL.md")):
        try:
            fm = parse_frontmatter(p.read_text(encoding="utf-8", errors="replace"))
        except OSError:
            continue
        if not fm:
            continue
        name, desc = fm.get("name"), fm.get("description")
        if not name or not desc:
            continue
        out.append(Skill(str(name).strip(), str(p), " ".join(str(desc).split())))
    return out


def _desc_hash(skill: Skill) -> str:
    return hashlib.sha256(f"{skill.name}\x00{skill.description}".encode()).hexdigest()


def _normalize(mat: np.ndarray) -> np.ndarray:
    norms = np.linalg.norm(mat, axis=-1, keepdims=True)
    norms[norms == 0] = 1.0
    return mat / norms


class SkillIndex:
    """SQLite-backed embedding cache with content-hash checkpointing."""

    def __init__(self, db_path: str | Path):
        self.db_path = str(db_path)
        Path(self.db_path).parent.mkdir(parents=True, exist_ok=True)
        self._conn = sqlite3.connect(self.db_path, check_same_thread=False)
        self._conn.executescript(
            """
            CREATE TABLE IF NOT EXISTS skills (
                name TEXT PRIMARY KEY, path TEXT NOT NULL,
                description TEXT NOT NULL, hash TEXT NOT NULL,
                dim INTEGER NOT NULL, vec BLOB NOT NULL, ts REAL NOT NULL);
            CREATE TABLE IF NOT EXISTS sessions (
                session_id TEXT NOT NULL, skill_name TEXT NOT NULL, ts REAL NOT NULL,
                PRIMARY KEY (session_id, skill_name));
            """
        )
        self._conn.commit()

    def reindex(self, skills: list[Skill], embed_fn: Callable) -> dict:
        """Upsert skills, embedding only changed descriptions."""
        cur = self._conn.execute("SELECT name, hash FROM skills")
        existing = dict(cur.fetchall())
        todo = [s for s in skills if existing.get(s.name) != _desc_hash(s)]
        if todo:
            vecs = _normalize(np.asarray(embed_fn([s.description for s in todo]), dtype=np.float32))
            for s, v in zip(todo, vecs):
                self._conn.execute(
                    "INSERT OR REPLACE INTO skills VALUES (?,?,?,?,?,?,?)",
                    (s.name, s.path, s.description, _desc_hash(s), v.shape[0], v.tobytes(), time.time()),
                )
        live = {s.name for s in skills}
        for s in skills:
            self._conn.execute("UPDATE skills SET path=? WHERE name=?", (s.path, s.name))
        removed = [n for n in existing if n not in live]
        for n in removed:
            self._conn.execute("DELETE FROM skills WHERE name=?", (n,))
        self._conn.commit()
        return {"total": len(skills), "embedded": len(todo), "removed": len(removed)}

    def vectors(self) -> tuple[list[Skill], np.ndarray]:
        """Return indexed skills and their normalized embedding matrix."""
        rows = self._conn.execute(
            "SELECT name, path, description, dim, vec FROM skills ORDER BY name"
        ).fetchall()
        if not rows:
            return [], np.zeros((0, 0), dtype=np.float32)
        skills = [Skill(r[0], r[1], r[2]) for r in rows]
        mat = np.stack([np.frombuffer(r[4], dtype=np.float32) for r in rows])
        return skills, mat

    def injected(self, session_id: str) -> set[str]:
        rows = self._conn.execute(
            "SELECT skill_name FROM sessions WHERE session_id=?", (session_id,)
        ).fetchall()
        return {r[0] for r in rows}

    def mark_injected(self, session_id: str, name: str) -> None:
        self._conn.execute(
            "INSERT OR REPLACE INTO sessions VALUES (?,?,?)", (session_id, name, time.time())
        )
        self._conn.commit()


def top_k(query_vec: np.ndarray, mat: np.ndarray, k: int) -> list[tuple[int, float]]:
    """Return cosine top-k row indexes and scores in descending order."""
    if mat.size == 0:
        return []
    q = np.asarray(query_vec, dtype=np.float32)
    n = np.linalg.norm(q)
    if n == 0:
        return []
    sims = mat @ (q / n)
    order = np.argsort(-sims)[:k]
    return [(int(i), float(sims[i])) for i in order]


# ── Hybrid lexical+semantic recall ──────────────────────────────────────────

import re
from functools import lru_cache

try:
    from nltk.stem import WordNetLemmatizer
    _lemmatizer = WordNetLemmatizer()
except ImportError:
    _lemmatizer = None

try:
    from rank_bm25 import BM25Okapi
except ImportError:
    BM25Okapi = None


def _tokenize(text: str) -> list[str]:
    """Lowercase, split hyphens, strip punctuation, lemmatize, remove stops."""
    text = text.lower()
    text = text.replace("-", " ")  # split hyphenated terms (memory-bank → memory bank)
    text = re.sub(r"[^\w\s]", " ", text)
    tokens = text.split()
    if _lemmatizer:
        out = []
        for t in tokens:
            n_form = _lemmatizer.lemmatize(t, pos="n")
            v_form = _lemmatizer.lemmatize(t, pos="v")
            out.append(min(n_form, v_form, key=len))
        tokens = out
    return [t for t in tokens if t not in _STOPWORDS]


_STOPWORDS = frozenset({
    "a", "an", "the", "is", "are", "was", "were", "be", "been", "being",
    "have", "has", "had", "do", "does", "did", "will", "would", "could",
    "should", "may", "might", "shall", "can", "need", "must",
    "for", "of", "in", "on", "at", "to", "from", "by", "with", "and",
    "or", "but", "not", "no", "if", "then", "else", "when", "where",
    "how", "what", "which", "who", "whom", "this", "that", "these",
    "those", "it", "its", "you", "your", "we", "our", "they", "their",
    "i", "my", "me", "he", "she", "his", "her", "us", "them",
    "use", "using", "used",  # extremely common in skill descriptions
})


class BM25Index:
    """Lightweight BM25 index over lemmatized skill name+description."""

    def __init__(self, skills: list[Skill]):
        self._skills = skills
        # Index on name + description concatenated
        corpus = [_tokenize(f"{s.name} {s.description}") for s in skills]
        self._bm25 = BM25Okapi(corpus) if BM25Okapi and corpus else None

    def query(self, text: str, k: int) -> list[tuple[int, float]]:
        """Return top-k (index, score) by BM25."""
        if not self._bm25 or not self._skills:
            return []
        tokens = _tokenize(text)
        if not tokens:
            return []
        scores = self._bm25.get_scores(tokens)
        order = np.argsort(-scores)[:k]
        return [(int(i), float(scores[i])) for i in order if scores[i] > 0]


def hybrid_recall(
    query: str,
    query_vec: np.ndarray,
    mat: np.ndarray,
    bm25: BM25Index,
    skills: list[Skill],
    k: int,
    lexical_weight: float = 0.67,
) -> list[tuple[int, float]]:
    """Fuse BM25 (lexical_weight) + cosine (1-lexical_weight) via RRF.

    Includes a name-match boost: if query tokens overlap with a skill's name
    tokens, that skill gets a direct RRF bonus (technical terms are exact).
    """
    semantic_weight = 1.0 - lexical_weight
    rrf_k = 60  # standard RRF constant

    # Get both ranked lists
    sem_results = top_k(query_vec, mat, k * 2)
    lex_results = bm25.query(query, k * 2)

    # RRF fusion
    scores: dict[int, float] = {}
    for rank, (idx, _) in enumerate(sem_results):
        scores[idx] = scores.get(idx, 0) + semantic_weight / (rrf_k + rank + 1)
    for rank, (idx, _) in enumerate(lex_results):
        scores[idx] = scores.get(idx, 0) + lexical_weight / (rrf_k + rank + 1)

    # Name-match boost: if query tokens intersect skill name tokens, add rank-1 bonus
    query_tokens = set(_tokenize(query))
    for idx, skill in enumerate(skills):
        name_tokens = set(_tokenize(skill.name))
        overlap = query_tokens & name_tokens
        if overlap:
            # Proportional to overlap fraction of the name
            boost = lexical_weight / (rrf_k + 1) * (len(overlap) / len(name_tokens))
            scores[idx] = scores.get(idx, 0) + boost

    ranked = sorted(scores.items(), key=lambda x: -x[1])[:k]
    return [(idx, score) for idx, score in ranked]


def route(
    prompt: str,
    index: SkillIndex,
    embed_fn: Callable,
    rerank_fn: Callable,
    cfg: RouteConfig,
    session_id: str | None = None,
) -> list[dict]:
    """Apply hybrid recall (0.67 lexical + 0.33 semantic), rerank, margin gate."""
    if not prompt.strip():
        return []
    skills, mat = index.vectors()
    if not skills:
        return []
    q = np.asarray(embed_fn([prompt]), dtype=np.float32)[0]
    bm25 = BM25Index(skills)
    recall = hybrid_recall(prompt, q, mat, bm25, skills, cfg.top_k, lexical_weight=0.67)
    cands = [(skills[i], sim) for i, sim in recall]
    docs = [f"{s.name}: {s.description}" for s, _ in cands]
    rr = rerank_fn(prompt, docs)

    baseline = float(np.median(np.asarray(rr, dtype=np.float64)))
    ranked = sorted(zip(cands, rr), key=lambda t: -t[1])[: cfg.rerank_keep]

    seen = index.injected(session_id) if session_id else set()
    accepted: list[dict] = []
    for (s, sim), score in ranked:
        if s.name in seen:
            continue
        margin = float(score) - baseline
        if margin < cfg.rerank_margin:
            continue
        accepted.append(
            {"name": s.name, "path": s.path, "description": s.description,
             "recall_sim": sim, "rerank_score": float(score),
             "rerank_margin": margin, "rerank_baseline": baseline}
        )
        if len(accepted) >= cfg.max_accept:
            break
    if session_id:
        for a in accepted:
            index.mark_injected(session_id, a["name"])
    return accepted
