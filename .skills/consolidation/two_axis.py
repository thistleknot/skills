#!/usr/bin/env python3
"""Two-axis merge review: relatedness x niche collision -> MERGE/XREF/RENAME/SEPARATE.

Thesis
------
A single similarity score cannot separate *"these are the same skill"* from
*"these are adjacent topics"*, which is precisely the merge-vs-cross-reference
decision `consolidation` has to make. Two axes can:

    axis A  relatedness     dense cosine (nomic-embed-text)  -- related at all?
    axis B  niche collision differentiating-term Jaccard     -- same ground?

                | high collision            | low collision
    high related| MERGE   (same niche)      | XREF   (adjacent topics)
    low  related| RENAME  (naming/desc bug) | SEPARATE

RENAME is not a curiosity: it is the `class-balancing` failure mode, where a
folder promises one thing and the body delivers another. Measured 2026-07-26 --
that skill contains zero classifier-weighting material despite its name.

Calibration (measured, do not re-litigate)
------------------------------------------
- Axis B uses `diff_top_n=16`, swept over {8,16,24,32,48,64} against a 20-pair
  hand gold set: AUC 0.925, positives mean 0.167 vs negatives mean 0.016. At the
  default 8 the lists are hard-capped and any downstream top-K slice is inert.
- The SALIENT lane is useless as a pairwise axis (0.000 on every pair) -- it is
  within-doc MMR, so each doc's terms are idiosyncratic by construction.
- B_HI=0.15 (~p99) is deliberately above the p95 (0.103); the measured negatives
  ceiling is 0.032, which equals the corpus median. It is a floor on "shares
  vocabulary distinctive to BOTH", not a similarity threshold.

Require   - Postgres (mmr_dst) and ollama with nomic-embed-text.
Guarantee - a quadrant label + both scores for every pair above either floor.
Maintain  - embeddings checkpointed by (skill, content_hash); unchanged corpus
            does no ollama work.
Assert    - refuses to run on a corpus below term_axis.MIN_CORPUS.
"""

from __future__ import annotations

import argparse
import json
import math
import sqlite3
import sys
import time
import urllib.request
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parent))
sys.path.insert(0, str(Path(__file__).resolve().parents[1] / "mmr-dst"))

from term_axis import CHECKPOINT, DOC_CHARS, _hash, collision_matrix, load_corpus  # noqa

DIFF_TOP_N = 16      # swept; see module docstring

# Axis A is thresholded by PERCENTILE, not by a fixed cosine. Dense cosines over a
# genre-homogeneous corpus sit uniformly high -- measured 2026-07-26 across 8,778
# pairs: min 0.439, MEDIAN 0.709, max 0.921. A fixed 0.72 floor therefore sat one
# hundredth above the median and admitted 1,012 "MERGE" pairs, 11.5% of the corpus.
# consolidation/SKILL.md already says this ("a fixed 0.3 would produce a
# near-complete graph"); this is that guidance applied.
A_PCT = 97.0         # -> 0.814 on the current corpus
# Axis B is a Jaccard over distinctive terms and is NOT genre-inflated: median
# 0.032, which independently equals the ceiling of a 10-pair hand-labelled
# negative set. 0.15 (~p99) buys precision over recall deliberately -- a missed
# merge lands in XREF, which is harmless, while a false merge destroys content.
B_HI = 0.15
EMBED_MODEL = "nomic-embed-text:latest"
OLLAMA = "http://localhost:11434"


CHUNK_CHARS = 3000   # see _embed_one


def _embed_one(text: str) -> list[float]:
    """Mean-pooled embedding of a document, chunked to fit the model's context.

    nomic-embed-text has a 2048-token context and returns HTTP 500 -- not a
    truncated vector -- when the prompt exceeds it. The limit is in TOKENS, so
    character length is a poor proxy: measured 2026-07-26, an 8100-char string of
    common repeated words embedded fine while 20 of 133 real skill files at
    7000-8000 chars failed, because code blocks and rare technical terms tokenize
    far denser than prose.

    3000 chars is a conservative budget for worst-case dense text. Chunks are
    mean-pooled so the vector still represents the whole document rather than
    only its opening.
    """


    chunks = [text[i:i + CHUNK_CHARS] for i in range(0, max(len(text), 1), CHUNK_CHARS)] or [" "]
    vecs = []
    for chunk in chunks:
        if not chunk.strip():
            continue
        req = urllib.request.Request(
            f"{OLLAMA}/api/embeddings",
            data=json.dumps({"model": EMBED_MODEL, "prompt": chunk}).encode(),
            headers={"Content-Type": "application/json"},
        )
        with urllib.request.urlopen(req, timeout=180) as resp:
            vecs.append(json.loads(resp.read())["embedding"])
    if not vecs:
        raise ValueError("no embeddable content")
    dim = len(vecs[0])
    return [sum(v[d] for v in vecs) / len(vecs) for d in range(dim)]


def embed_corpus(names: list[str], texts: list[str]) -> list[list[float]]:
    """Dense vectors per skill, checkpointed by (skill, content_hash)."""

    conn = sqlite3.connect(CHECKPOINT)
    conn.execute(
        "CREATE TABLE IF NOT EXISTS embeddings ("
        " skill TEXT NOT NULL, content_hash TEXT NOT NULL, vec TEXT NOT NULL,"
        " model TEXT NOT NULL, computed_at TEXT NOT NULL,"
        " PRIMARY KEY (skill, content_hash))"
    )
    out, misses = [], 0
    for name, text in zip(names, texts):
        h = _hash(text)
        row = conn.execute(
            "SELECT vec FROM embeddings WHERE skill=? AND content_hash=?", (name, h)
        ).fetchone()
        if row:
            out.append(json.loads(row[0]))
            continue
        misses += 1
        vec = _embed_one(text)
        conn.execute(
            "INSERT OR REPLACE INTO embeddings VALUES (?,?,?,?,?)",
            (name, h, json.dumps(vec), EMBED_MODEL, time.strftime("%Y-%m-%dT%H:%M:%S")),
        )
        out.append(vec)
    conn.commit()
    conn.close()
    print(f"  embeddings: {len(names)-misses} cached, {misses} computed")
    return out


def cosine_matrix(vecs: list[list[float]]) -> list[list[float]]:
    norms = [math.sqrt(sum(x * x for x in v)) or 1.0 for v in vecs]
    n = len(vecs)
    M = [[0.0] * n for _ in range(n)]
    for i in range(n):
        for j in range(i + 1, n):
            dot = sum(a * b for a, b in zip(vecs[i], vecs[j]))
            M[i][j] = M[j][i] = dot / (norms[i] * norms[j])
    return M


def percentile(values: list[float], pct: float) -> float:
    """Nearest-rank percentile of a sorted-in-place copy."""
    v = sorted(values)
    return v[min(len(v) - 1, int(len(v) * pct / 100.0))]


def quadrant(a: float, b: float, a_hi: float, b_hi: float) -> str:
    """Label a pair. Order matters: MERGE is the only both-high case."""
    if a >= a_hi and b >= b_hi:
        return "MERGE"
    if a >= a_hi:
        return "XREF"
    if b >= b_hi:
        return "RENAME"
    return "SEPARATE"


def main() -> int:
    ap = argparse.ArgumentParser(description="two-axis merge review")
    ap.add_argument("--root", type=Path, default=Path(__file__).resolve().parent.parent)
    ap.add_argument("--out", type=Path, default=Path(__file__).with_name("merge_report.md"))
    ap.add_argument("--a-pct", type=float, default=A_PCT,
                    help="percentile of the cosine distribution used as the relatedness floor")
    ap.add_argument("--b-hi", type=float, default=B_HI)
    args = ap.parse_args()

    names, texts = load_corpus(args.root)
    print(f"corpus: {len(names)} skills")

    from mmr_dst import tag_texts
    t0 = time.time()
    diff = [d for _, d in tag_texts(texts, diff_top_n=DIFF_TOP_N, salient_top_n=8)]
    print(f"  axis B (terms) in {time.time()-t0:.1f}s")
    B = collision_matrix(diff, DIFF_TOP_N)

    t0 = time.time()
    A = cosine_matrix(embed_corpus(names, texts))
    print(f"  axis A (embeddings) in {time.time()-t0:.1f}s")

    flat_a = [A[i][j] for i in range(len(names)) for j in range(i + 1, len(names))]
    a_hi = percentile(flat_a, args.a_pct)
    print(f"  axis A floor: p{args.a_pct} = {a_hi:.3f} (median {percentile(flat_a,50):.3f})")

    rows = []
    for i in range(len(names)):
        for j in range(i + 1, len(names)):
            a, b = A[i][j], B[i][j]
            q = quadrant(a, b, a_hi, args.b_hi)
            if q != "SEPARATE":
                rows.append((q, a, b, names[i], names[j]))

    order = {"MERGE": 0, "RENAME": 1, "XREF": 2}
    rows.sort(key=lambda r: (order[r[0]], -(r[1] + r[2])))

    counts = {q: sum(1 for r in rows if r[0] == q) for q in order}
    total_pairs = len(names) * (len(names) - 1) // 2
    print(f"\n{total_pairs} pairs -> " + ", ".join(f"{q}={counts[q]}" for q in order)
          + f", SEPARATE={total_pairs - len(rows)}")

    lines = [
        "# Two-axis merge review",
        "",
        f"- corpus: **{len(names)}** skills, {total_pairs} pairs",
        f"- axis A relatedness = nomic-embed cosine, floor **{a_hi:.3f}** (p{args.a_pct} of 8,778 pairs; median {percentile(flat_a,50):.3f})",
        f"- axis B niche collision = differentiating-term Jaccard "
        f"(diff_top_n={DIFF_TOP_N}), floor **{args.b_hi}**",
        f"- buckets: " + ", ".join(f"**{q}** {counts[q]}" for q in order)
        + f", SEPARATE {total_pairs - len(rows)}",
        "",
        "| bucket | A related | B collision | skill | skill |",
        "|---|---:|---:|---|---|",
    ]
    for q, a, b, x, y in rows:
        lines.append(f"| {q} | {a:.3f} | {b:.3f} | `{x}` | `{y}` |")
    args.out.write_text("\n".join(lines) + "\n", encoding="utf-8")
    print(f"report -> {args.out}")
    return 0


if __name__ == "__main__":
    sys.exit(main())
