"""Step 1 of the graph-metrics plan: embed the 1,467 skill_descriptions with
nomic and write a checkpoint.db in the shape consolidation/graph_analysis.py's
load_embeddings expects: skill_derivations(skill_name, embedding_json).

skill_name = skill_slug (so graph_report communities are keyed by slug).
No LLM, no re-ingest — just embeds the pre-written descriptions.

Run:  python build_desc_checkpoint.py
"""

import json
import sqlite3
import sys
from pathlib import Path

import psycopg

sys.path.insert(0, str(Path(__file__).parent))
import mcp_server as srv          # noqa: E402
import eval_topical as tp         # noqa: E402

OUT = Path(__file__).parent / "desc_checkpoint.db"


def run():
    conn = psycopg.connect(**tp.PG_RAW)
    with conn.cursor() as cur:
        cur.execute("""SELECT DISTINCT e.cmetadata->>'skill_slug', e.cmetadata->>'skill_description'
                       FROM langchain_pg_embedding e JOIN langchain_pg_collection col
                       ON col.uuid=e.collection_id WHERE col.name=%s
                       AND coalesce(e.cmetadata->>'skill_description','')<>''""", (tp.COLLECTION,))
        rows = cur.fetchall()
    conn.close()
    slugs = [r[0] for r in rows]
    descs = [r[1] for r in rows]
    print(f"embedding {len(slugs)} descriptions with nomic ...", flush=True)
    emb = srv._get_store().embeddings
    vecs = []
    B = 200
    for i in range(0, len(descs), B):
        vecs.extend(emb.embed_documents(descs[i:i+B]))
        print(f"  {min(i+B, len(descs))}/{len(descs)}", flush=True)
    con = sqlite3.connect(OUT)
    con.execute("DROP TABLE IF EXISTS skill_derivations")
    con.execute("CREATE TABLE skill_derivations (skill_name TEXT PRIMARY KEY, embedding_json TEXT)")
    con.executemany("INSERT OR REPLACE INTO skill_derivations VALUES (?,?)",
                    [(s, json.dumps(v)) for s, v in zip(slugs, vecs)])
    con.commit(); con.close()
    print(f"wrote {OUT.name}: {len(slugs)} skill embeddings (dim={len(vecs[0])})", flush=True)


if __name__ == "__main__":
    run()
