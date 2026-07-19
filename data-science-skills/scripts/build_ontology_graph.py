"""Build the synset->hypernym IS-A ontology graph in neo4j from pg cmetadata.

Incremental — NO re-ingest. The synset/hypernym data is already stored per
triplet in cmetadata (subject/predicate/object _synset and _hypernym). This
reads it and composes the ontology graph:

  (:Synset {id})-[:HYPERNYM]->(:Synset {id})   -- ONE 1-hop edge per term
  (:Chunk {id})-[:HAS_CONCEPT]->(:Synset {id}) -- chunk's degree-0 concepts

1-hop edges only; the full IS-A DAG is their composition (traversable via
HYPERNYM*). This is the RIGHT graph for retrieval (the earlier entity
CO_OCCURS graph was empirical co-occurrence and flopped).

Run:  python build_ontology_graph.py            # build (additive; MERGE-dedup)
      python build_ontology_graph.py --reset    # drop Synset/HYPERNYM first
"""

import argparse

import psycopg
from neo4j import GraphDatabase

PG_RAW = dict(host="localhost", port=5432, dbname="langchain",
              user="langchain", password="langchain")
COLLECTION = "data_science_skills"
NEO4J_URI = "bolt://localhost:7688"
BATCH = 500


def iter_chunk_concepts():
    """Yield (chunk_id, [(synset, hypernym), ...]) from pg cmetadata triplets."""
    with psycopg.connect(**PG_RAW) as c, c.cursor(name="ont") as cur:
        cur.itersize = 2000
        cur.execute("""
            SELECT e.cmetadata->>'chunk_id', e.cmetadata->'triplets'
            FROM langchain_pg_embedding e JOIN langchain_pg_collection col
              ON col.uuid = e.collection_id WHERE col.name = %s
        """, (COLLECTION,))
        for chunk_id, triplets in cur:
            pairs = []
            for t in (triplets or []):
                for role in ("subject", "predicate", "object"):
                    syn = t.get(f"{role}_synset")
                    hyp = t.get(f"{role}_hypernym")
                    if syn:
                        pairs.append((syn, hyp))
            if pairs:
                yield chunk_id, pairs


def build(reset: bool) -> None:
    driver = GraphDatabase.driver(NEO4J_URI, auth=None)
    with driver.session() as s:
        if reset:
            s.run("MATCH (n:Synset) DETACH DELETE n")
        s.run("CREATE CONSTRAINT dss_synset_id IF NOT EXISTS "
              "FOR (x:Synset) REQUIRE x.id IS UNIQUE")

    # rows: [{cid, syn, hyp}] flattened, batched
    buf, n_edges, n_chunks = [], 0, 0
    def flush(rows):
        with driver.session() as s:
            # synset nodes + HYPERNYM edges (hyp may be null -> just the node)
            s.run("""
                UNWIND $rows AS r
                MERGE (a:Synset {id: r.syn})
                WITH r, a WHERE r.hyp IS NOT NULL
                MERGE (b:Synset {id: r.hyp})
                MERGE (a)-[:HYPERNYM]->(b)
            """, rows=rows)
            s.run("""
                UNWIND $rows AS r
                MERGE (c:Chunk {id: r.cid})
                MERGE (sy:Synset {id: r.syn})
                MERGE (c)-[:HAS_CONCEPT]->(sy)
            """, rows=rows)

    for cid, pairs in iter_chunk_concepts():
        n_chunks += 1
        for syn, hyp in pairs:
            buf.append({"cid": cid, "syn": syn, "hyp": hyp})
            n_edges += 1
        if len(buf) >= BATCH:
            flush(buf); buf = []
    if buf:
        flush(buf)

    with driver.session() as s:
        syn = s.run("MATCH (x:Synset) RETURN count(x) AS n").single()["n"]
        hyp = s.run("MATCH (:Synset)-[r:HYPERNYM]->(:Synset) RETURN count(r) AS n").single()["n"]
        hc = s.run("MATCH (:Chunk)-[r:HAS_CONCEPT]->(:Synset) RETURN count(r) AS n").single()["n"]
    driver.close()
    print(f"ontology graph: {syn} synset nodes, {hyp} HYPERNYM edges, {hc} HAS_CONCEPT links "
          f"(from {n_chunks} chunks, {n_edges} concept mentions)")


if __name__ == "__main__":
    ap = argparse.ArgumentParser(description=__doc__)
    ap.add_argument("--reset", action="store_true", help="drop Synset nodes first")
    args = ap.parse_args()
    build(reset=args.reset)
