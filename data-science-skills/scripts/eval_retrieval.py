"""IR eval harness for the data-science-skills retriever.

Answers "what's the best hierarchical fit given our options" empirically:
generates a golden query set, then measures skill-level recall@k / precision@k
/ MRR / nDCG@k across retriever CONFIGURATIONS (GRAPH_MODE, fusion weight,
expansion hops, k) so the graph-leg-role question is settled by data.

Ground truth is SKILL-LEVEL (see the operator's contract: a skill is one piece
of knowledge; a query "hits" if retrieval returns the right skill). Queries are
LLM-paraphrased to AVOID the skill's own wording, then overlap- and
retention-filtered so the eval doesn't just reward surface lexical match.

Golden set is cached in sqlite (load-if-exists) so query generation — the
expensive LLM step — runs once.

Run:
    python eval_retrieval.py --gen 5        # generate 5 queries/skill (once)
    python eval_retrieval.py --sweep        # measure all GRAPH_MODE configs
    python eval_retrieval.py --config both  # measure one config
"""

import argparse
import json
import math
import re
import sqlite3
import sys
from pathlib import Path

import psycopg
import requests

sys.path.insert(0, str(Path(__file__).parent))
import mcp_server as srv  # noqa: E402

OLLAMA_URL = "http://localhost:11434"
GEN_MODEL = "qwen3.5-oc:4b"
GOLDEN_DB = Path(__file__).parent / "eval_golden.sqlite"
PG_RAW = dict(host="localhost", port=5432, dbname="langchain",
              user="langchain", password="langchain")
COLLECTION = "data_science_skills"
EVAL_K = 10                      # measure ranks up to here
OVERLAP_MAX = 0.6               # drop queries too lexically similar to the description


# =============================================================================
# Golden query generation (LLM-paraphrase, overlap + retention filtered)
# =============================================================================

def _skills_with_desc() -> list:
    with psycopg.connect(**PG_RAW) as c, c.cursor() as cur:
        cur.execute("""
            SELECT DISTINCT e.cmetadata->>'skill_slug', e.cmetadata->>'skill_name',
                   e.cmetadata->>'skill_description'
            FROM langchain_pg_embedding e JOIN langchain_pg_collection col
              ON col.uuid = e.collection_id WHERE col.name = %s
        """, (COLLECTION,))
        return [(r[0], r[1], r[2]) for r in cur.fetchall() if r[0]]


def _lexical_overlap(a: str, b: str) -> float:
    """Jaccard over content-word sets — proxy for 'query just echoes the source'."""
    wa = set(re.findall(r"[a-z]{3,}", a.lower()))
    wb = set(re.findall(r"[a-z]{3,}", b.lower()))
    return len(wa & wb) / max(len(wa | wb), 1)


def _gen_for_skill(name: str, desc: str, n: int) -> list:
    prompt = (f"/no_think\nA user needs the data-science concept below but does NOT know its "
              f"name. Write {n} distinct natural questions they'd ask, in everyday words, "
              f"WITHOUT using the concept's name or copying its wording.\n"
              f"Concept: {name}\nWhat it is: {desc}\n"
              'Return JSON: {"queries": ["...", "..."]}')
    payload = {"model": GEN_MODEL, "messages": [{"role": "user", "content": prompt}],
               "format": "json", "think": False, "stream": False, "options": {"temperature": 0.4}}
    try:
        r = requests.post(f"{OLLAMA_URL}/api/chat", json=payload, timeout=120)
        raw = r.json().get("message", {}).get("content", "")
        raw = re.sub(r"<think>.*?</think>", "", raw, flags=re.DOTALL)
        raw = re.sub(r"```(?:json)?", "", raw).strip()
        return json.loads(raw).get("queries", [])
    except Exception as e:  # noqa: BLE001
        print(f"  gen failed for {name}: {e}")
        return []


def generate_golden(n_per_skill: int) -> int:
    """Generate + overlap-filter + retention-filter queries, cache to sqlite."""
    con = sqlite3.connect(GOLDEN_DB)
    con.execute("CREATE TABLE IF NOT EXISTS golden (query TEXT, target_slug TEXT, "
                "PRIMARY KEY (query, target_slug))")
    kept = 0
    for slug, name, desc in _skills_with_desc():
        for q in _gen_for_skill(name, desc or "", n_per_skill):
            if _lexical_overlap(q, desc or "") > OVERLAP_MAX:
                continue  # too close to the source wording — biased
            # retention filter: target must be retrievable at all (top-EVAL_K)
            hits = json.loads(srv.run_retrieval(q, k=EVAL_K))
            if slug not in [h["skill_slug"] for h in hits]:
                continue
            con.execute("INSERT OR IGNORE INTO golden VALUES (?,?)", (q, slug))
            kept += 1
    con.commit()
    total = con.execute("SELECT COUNT(*) FROM golden").fetchone()[0]
    con.close()
    print(f"golden: +{kept} kept this run, {total} total in {GOLDEN_DB.name}")
    return total


def load_golden() -> list:
    if not GOLDEN_DB.exists():
        return []
    con = sqlite3.connect(GOLDEN_DB)
    rows = con.execute("SELECT query, target_slug FROM golden").fetchall()
    con.close()
    return rows


# =============================================================================
# Metrics (skill-level)
# =============================================================================

def rank_of(target: str, ranked_slugs: list):
    for i, s in enumerate(ranked_slugs, 1):
        if s == target:
            return i
    return None


def eval_config(config: dict, golden: list) -> dict:
    """Apply config to the retriever, run every golden query, aggregate
    recall@k / precision@k / MRR / nDCG@k at the skill level."""
    for key, val in config.items():          # inject config into the retriever module
        setattr(srv, key, val)

    recalls = {k: [] for k in (1, 3, 5, 10)}
    precisions = {k: [] for k in (1, 3, 5, 10)}
    rr, ndcg = [], []
    for q, target in golden:
        ranked = [h["skill_slug"] for h in json.loads(srv.run_retrieval(q, k=EVAL_K))]
        r = rank_of(target, ranked)
        for k in recalls:
            hit = (r is not None and r <= k)
            recalls[k].append(1.0 if hit else 0.0)
            precisions[k].append((1.0 / k) if hit else 0.0)   # single relevant target
        rr.append(1.0 / r if r else 0.0)
        ndcg.append(1.0 / math.log2(r + 1) if r else 0.0)     # ideal DCG=1 (one relevant)

    n = max(len(golden), 1)
    return {
        "n_queries": len(golden),
        **{f"recall@{k}": round(sum(v) / n, 3) for k, v in recalls.items()},
        **{f"precision@{k}": round(sum(v) / n, 3) for k, v in precisions.items()},
        "mrr": round(sum(rr) / n, 3),
        "ndcg@10": round(sum(ndcg) / n, 3),
    }


def sweep(golden: list) -> None:
    """Compare graph-leg roles — the empirical answer to parallel-vs-cascade."""
    configs = {
        "cosine_only": {"GRAPH_MODE": "parallel", "GRAPH_RRF_WEIGHT": 0.0},
        "graph_parallel": {"GRAPH_MODE": "parallel", "GRAPH_RRF_WEIGHT": 0.5},
        "graph_cascade": {"GRAPH_MODE": "cascade"},
        "both": {"GRAPH_MODE": "both", "GRAPH_RRF_WEIGHT": 0.5},
    }
    print(f"\n=== sweep over {len(golden)} golden queries ===")
    header = ["config", "recall@1", "recall@5", "mrr", "ndcg@10"]
    print("  " + "  ".join(f"{h:>14}" for h in header))
    results = {}
    for name, cfg in configs.items():
        m = eval_config(cfg, golden)
        results[name] = m
        print("  " + "  ".join(f"{str(v):>14}" for v in
              [name, m["recall@1"], m["recall@5"], m["mrr"], m["ndcg@10"]]))
    best = max(results, key=lambda n: results[n]["ndcg@10"])
    print(f"\nbest by ndcg@10: {best}  {results[best]}")
    (Path(__file__).parent / "eval_results.json").write_text(
        json.dumps(results, indent=2), encoding="utf-8")


if __name__ == "__main__":
    ap = argparse.ArgumentParser(description=__doc__)
    ap.add_argument("--gen", type=int, metavar="N", help="generate N queries/skill into the golden set")
    ap.add_argument("--sweep", action="store_true", help="measure all graph-leg configs")
    ap.add_argument("--config", choices=["parallel", "cascade", "both"], help="measure one GRAPH_MODE")
    args = ap.parse_args()
    if args.gen:
        generate_golden(args.gen)
    golden = load_golden()
    if not golden and (args.sweep or args.config):
        print("no golden queries — run --gen N first"); sys.exit(1)
    if args.sweep:
        sweep(golden)
    elif args.config:
        print(json.dumps(eval_config({"GRAPH_MODE": args.config}, golden), indent=2))
