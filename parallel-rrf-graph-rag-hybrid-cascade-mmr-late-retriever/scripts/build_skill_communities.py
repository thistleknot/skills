"""GraphRAG-analogue, deterministic (no LLM): Leiden communities over a skill-skill
graph, using the SAME library GraphRAG uses (graspologic.hierarchical_leiden).

The graph's PROPER job is clustering (not retrieval scoring): build a skill-skill
graph (edge = # shared entities, hub entities capped like stopwords), run
hierarchical Leiden -> data-driven topical communities that cross folder
boundaries (regularization spans regression/ + misc/). Community "report" =
aggregated member skill_descriptions (already written; no LLM).

Emits skill_communities.json: {skill_slug: {level0: cid, level1: cid, ...}} plus
per-community member lists. Consumed by retrieval (return a query's community =
its topical cluster).

Run:  python build_skill_communities.py [--max-skills-per-entity 30] [--max-cluster 25]
"""

import argparse
import json
import sys
from collections import defaultdict
from itertools import combinations
from pathlib import Path

import psycopg

sys.path.insert(0, str(Path(__file__).parent))
import eval_ablation as ab   # noqa: E402  (PG_RAW, COLLECTION)

OUT = Path(__file__).parent / "skill_communities.json"


def skill_concepts(conn, mode):
    """{skill_slug: {concept_id: weight_class}}. mode='entities' -> raw entities
    (GraphRAG noun-phrase baseline). mode='ontology' -> synset-collapsed nodes
    (weight 2, synonym identity) + hypernyms (weight 1, broader links) from the
    triplets' *_synset/*_hypernym — the operator's collapsed ontology."""
    sc = defaultdict(lambda: defaultdict(int))
    with conn.cursor(name="sc") as cur:
        cur.itersize = 2000
        if mode == "entities":
            cur.execute("""SELECT e.cmetadata->>'skill_slug', e.cmetadata->'entities'
                           FROM langchain_pg_embedding e JOIN langchain_pg_collection col
                           ON col.uuid=e.collection_id WHERE col.name=%s""", (ab.COLLECTION,))
            for slug, ents in cur:
                if slug and ents:
                    for e in ents:
                        if e:
                            sc[slug][e] = max(sc[slug][e], 1)
        else:  # ontology
            cur.execute("""SELECT e.cmetadata->>'skill_slug', e.cmetadata->'triplets'
                           FROM langchain_pg_embedding e JOIN langchain_pg_collection col
                           ON col.uuid=e.collection_id WHERE col.name=%s""", (ab.COLLECTION,))
            for slug, trips in cur:
                if not (slug and trips):
                    continue
                for t in trips:
                    for role in ("subject", "predicate", "object"):
                        syn = t.get(f"{role}_synset")
                        hyp = t.get(f"{role}_hypernym")
                        if syn:
                            sc[slug][syn] = max(sc[slug][syn], 2)   # collapsed concept node
                        if hyp and mode != "synset":                # 'synset' = collapse only, NO hypernyms
                            sc[slug].setdefault(hyp, 1)              # broader link (never downgrade a synset)
    return sc


def build_graph(sc, max_skills_per_concept):
    """networkx skill-skill graph; edge weight = sum over shared non-hub concepts
    of min(weightclass) — synset matches (2) count more than hypernym matches (1)."""
    import networkx as nx
    concept_skills = defaultdict(dict)   # concept -> {skill: weightclass}
    for slug, concepts in sc.items():
        for c, wc in concepts.items():
            concept_skills[c][slug] = wc
    kept = {c: sks for c, sks in concept_skills.items()
            if 2 <= len(sks) <= max_skills_per_concept}
    pair_w = defaultdict(int)
    for c, sks in kept.items():
        items = sorted(sks.items())
        for (a, wa), (b, wb) in combinations(items, 2):
            pair_w[(a, b)] += min(wa, wb)   # shared concept contributes its (weaker) weight class
    G = nx.Graph()
    G.add_nodes_from(sc.keys())
    for (a, b), w in pair_w.items():
        G.add_edge(a, b, weight=w)
    return G, len(kept)


def run(max_skills_per_entity, max_cluster, mode):
    from graspologic.partition import hierarchical_leiden
    conn = psycopg.connect(**ab.PG_RAW)
    try:
        print(f"mode={mode}", flush=True)
        se = skill_concepts(conn, mode)
        G, n_kept = build_graph(se, max_skills_per_entity)
        import networkx as nx
        # Leiden needs a connected-ish graph; run on the largest component, isolates -> own community
        comps = list(nx.connected_components(G))
        giant = max(comps, key=len)
        print(f"skills={G.number_of_nodes()} edges={G.number_of_edges()} "
              f"non-hub-entities={n_kept} components={len(comps)} giant={len(giant)}", flush=True)
        Gg = G.subgraph(giant).copy()
        clusters = hierarchical_leiden(Gg, max_cluster_size=max_cluster, random_seed=7)
        # modularity of the finest partition (community-quality proxy, mode compare)
        finest = {}
        for c in clusters:
            finest[c.node] = c.cluster if finest.get(c.node) is None else finest[c.node]
        part = defaultdict(set)
        for node, cid in finest.items():
            part[cid].add(node)
        mod = nx.algorithms.community.modularity(Gg, list(part.values()), weight="weight")
        print(f"modularity={mod:.3f}", flush=True)
        # map: skill -> {level: community_id}; and community -> members (finest level)
        skill_comm = defaultdict(dict)
        for c in clusters:
            skill_comm[c.node][c.level] = c.cluster
        maxlevel = max((lv for d in skill_comm.values() for lv in d), default=0)
        members = defaultdict(list)
        for slug, lv in skill_comm.items():
            members[lv.get(maxlevel, lv[max(lv)])].append(slug)
        sizes = sorted((len(v) for v in members.values()), reverse=True)
        print(f"hierarchical_leiden levels=0..{maxlevel}  finest communities={len(members)}  "
              f"sizes: max={sizes[0]} median={sizes[len(sizes)//2]} singletons={sum(1 for s in sizes if s==1)}",
              flush=True)
        # show 3 sample communities to check cross-folder topical coherence
        big = sorted(members.items(), key=lambda kv: -len(kv[1]))[:3]
        for cid, ms in big:
            folders = defaultdict(int)
            for m in ms:
                folders[m.split('/')[0]] += 1
            print(f"\n  community {cid} ({len(ms)} skills, folders={dict(folders)}):", flush=True)
            for m in sorted(ms)[:12]:
                print(f"    {m}", flush=True)
        OUT.write_text(json.dumps({"skill_comm": {k: v for k, v in skill_comm.items()},
                                   "members": {str(k): v for k, v in members.items()},
                                   "maxlevel": maxlevel}, indent=2), encoding="utf-8")
        print(f"\nwrote {OUT.name}", flush=True)
    finally:
        conn.close()


if __name__ == "__main__":
    ap = argparse.ArgumentParser(description=__doc__)
    ap.add_argument("--max-skills-per-entity", type=int, default=30)
    ap.add_argument("--max-cluster", type=int, default=25)
    ap.add_argument("--mode", choices=["entities", "ontology", "synset"], default="ontology")
    args = ap.parse_args()
    run(args.max_skills_per_entity, args.max_cluster, args.mode)
