#!/usr/bin/env python3
"""Second consolidation axis: niche collision via differentiating-term overlap.

Thesis
------
`consolidation` scores ONE axis (triplet-overlap fusion, tau=0.3) and prescribes
by magnitude alone. Magnitude cannot separate *"these are the same skill"* from
*"these are adjacent topics"* -- which is exactly the merge-vs-cross-reference
decision. This module supplies the missing axis.

    axis A  (existing)  overlap          -- are these related at all?
    axis B  (this file) niche collision  -- do these claim the same ground?

                | high collision            | low collision
    high overlap| MERGE   (same niche)      | XREF   (adjacent topics)
    low  overlap| RENAME  (naming/desc bug) | SEPARATE

Measured caveat (2026-07-26), do not re-litigate
------------------------------------------------
- The SALIENT lane is useless as a pairwise axis: it is within-doc MMR, so each
  doc's top terms are idiosyncratic by construction. Measured 0.000 Jaccard on
  every pair of a 12-doc sample. Axis A must stay the existing fusion score.
- The DIFFERENTIATING lane does separate families (within 0.040 vs cross 0.007
  on that same sample) but weakly, with false positives by rank 4. That sample
  was too small for the across-corpus lane to calibrate -- its redundancy term
  is estimated from how often a word is salient in OTHER docs. Hence this
  module runs the full corpus and sweeps K rather than trusting one setting.

Require   - Postgres reachable for mmr_dst.lex_texts (langchain_postgres:5432),
            or pass --fallback to use the pure-python snowball lane.
Guarantee - writes per-skill term lists to the checkpoint and returns a pairwise
            collision matrix aligned to the returned name order.
Maintain  - tagging is checkpointed by (skill, content_hash); re-runs on an
            unchanged corpus do no Postgres work at all.
Assert    - a corpus of fewer than MIN_CORPUS docs raises rather than returning
            a matrix, because the differentiating lane is not estimable there.
"""

from __future__ import annotations

import argparse
import hashlib
import json
import re
import sqlite3
import sys
import time
from pathlib import Path

MIN_CORPUS = 40          # below this the across-corpus redundancy term is noise
DOC_CHARS = 8000         # per-doc truncation; keeps BM25 and runtime bounded
CHECKPOINT = Path(__file__).with_name(".term_axis.db")

# Structural vocabulary every SKILL.md shares. Left in, it inflates every pair
# uniformly and flattens the distribution -- the same reason consolidation's
# existing pipeline strips boilerplate before vectorising.
BOILERPLATE = re.compile(
    r"^\s*#{1,6}\s*(when to use|trigger conditions?|failure modes?|purpose|scope"
    r"|requires?|usage|files?|contract|related|overview|why|how to apply)\b.*$",
    re.I | re.M,
)


def load_corpus(root: Path) -> tuple[list[str], list[str]]:
    """Return (names, texts) for every skill with a SKILL.md, sorted by name."""
    names, texts = [], []
    for path in sorted(root.glob("*/SKILL.md")):
        raw = path.read_text(encoding="utf-8", errors="replace")
        body = re.sub(r"^---.*?^---", " ", raw, count=1, flags=re.S | re.M)  # frontmatter
        body = re.sub(r"```.*?```", " ", body, flags=re.S)                    # code blocks
        body = BOILERPLATE.sub(" ", body)
        names.append(path.parent.name)
        texts.append(body[:DOC_CHARS])
    return names, texts


def _hash(text: str) -> str:
    return hashlib.sha256(text.encode("utf-8")).hexdigest()[:16]


def _open_checkpoint() -> sqlite3.Connection:
    conn = sqlite3.connect(CHECKPOINT)
    conn.execute(
        "CREATE TABLE IF NOT EXISTS tags ("
        " skill TEXT NOT NULL, content_hash TEXT NOT NULL,"
        " salient TEXT NOT NULL, differentiating TEXT NOT NULL,"
        " computed_at TEXT NOT NULL, PRIMARY KEY (skill, content_hash))"
    )
    return conn


def tag_corpus(names: list[str], texts: list[str], fallback: bool = False) -> list[list[str]]:
    """Differentiating terms per doc, checkpointed by (skill, content_hash).

    The whole corpus must be tagged in ONE call: the differentiating lane scores
    a term by how often it is salient elsewhere, so tagging docs individually
    would silently produce a different (and meaningless) result.
    """
    if len(names) < MIN_CORPUS:
        raise ValueError(
            f"corpus of {len(names)} < MIN_CORPUS={MIN_CORPUS}; the differentiating "
            "lane is not estimable on a sample this small (measured: false "
            "positives by rank 4 on 12 docs)"
        )

    conn = _open_checkpoint()
    hashes = [_hash(t) for t in texts]
    cached = {
        row[0]: json.loads(row[1])
        for row in conn.execute(
            "SELECT skill, differentiating FROM tags WHERE content_hash IN "
            f"({','.join('?' * len(hashes))})", hashes
        )
    }
    if len(cached) == len(names):
        print(f"  checkpoint hit: all {len(names)} skills already tagged")
        return [cached[n] for n in names]

    print(f"  checkpoint miss ({len(cached)}/{len(names)} cached) -- tagging full corpus")
    t0 = time.time()
    if fallback:
        sys.path.insert(0, str(Path(__file__).resolve().parents[1] / "bm25-snowball-keywords"))
        from script import salient_terms                       # noqa
        pairs = [(s, s) for s in salient_terms(texts)]         # no separate lane
    else:
        sys.path.insert(0, str(Path(__file__).resolve().parents[1] / "mmr-dst"))
        from mmr_dst import tag_texts                          # noqa
        pairs = list(tag_texts(texts))
    print(f"  tagged {len(names)} skills in {time.time()-t0:.1f}s")

    now = time.strftime("%Y-%m-%dT%H:%M:%S")
    out = []
    for name, h, (sal, diff) in zip(names, hashes, pairs):
        conn.execute(
            "INSERT OR REPLACE INTO tags VALUES (?,?,?,?,?)",
            (name, h, json.dumps(list(sal)), json.dumps(list(diff)), now),
        )
        out.append(list(diff))
    conn.commit()
    conn.close()
    return out


def collision_matrix(term_lists: list[list[str]], k: int) -> list[list[float]]:
    """Pairwise Jaccard over each doc's top-k differentiating terms."""
    sets = [set(t[:k]) for t in term_lists]
    n = len(sets)
    M = [[0.0] * n for _ in range(n)]
    for i in range(n):
        for j in range(i + 1, n):
            union = sets[i] | sets[j]
            v = len(sets[i] & sets[j]) / len(union) if union else 0.0
            M[i][j] = M[j][i] = v
    return M


def main() -> int:
    ap = argparse.ArgumentParser(description="differentiating-term collision axis")
    ap.add_argument("--root", type=Path, default=Path(__file__).resolve().parent.parent)
    ap.add_argument("--k", type=int, default=40)
    ap.add_argument("--fallback", action="store_true", help="snowball lane, no Postgres")
    ap.add_argument("--top", type=int, default=25, help="print N highest-collision pairs")
    args = ap.parse_args()

    names, texts = load_corpus(args.root)
    print(f"corpus: {len(names)} skills")
    diff = tag_corpus(names, texts, fallback=args.fallback)
    M = collision_matrix(diff, args.k)

    pairs = sorted(
        ((M[i][j], names[i], names[j]) for i in range(len(names)) for j in range(i + 1, len(names))),
        reverse=True,
    )
    print(f"\ntop {args.top} niche collisions (k={args.k}):")
    for score, a, b in pairs[: args.top]:
        print(f"  {score:.3f}  {a}  <->  {b}")
    return 0


if __name__ == "__main__":
    sys.exit(main())
