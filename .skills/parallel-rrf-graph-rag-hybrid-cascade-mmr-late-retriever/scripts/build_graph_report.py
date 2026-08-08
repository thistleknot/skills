"""Step 2: run the consolidation graph-metrics toolkit on our description
embeddings, emitting graph_report.json for the community retrieval lane.

Reuses consolidation/graph_analysis.py functions (build_graph, adaptive_tau,
louvain_partition, subgraph_metrics) — but computes DWPC VECTORIZED (the skill's
k=2 DWPC is a pure-python O(N^3) triple loop, intractable at N=1467; the identical
formula is Abin@Abin matrix math → seconds). DWPC(i,j) = PC1 + PC2/max(PDP2,1)^0.4.

Emits graph_report.json:
  skill_comm      {slug: community_id}         (Louvain on the cosine graph)
  comm_metrics    {cid: {size,density,conductance,lcc_ratio}}   (gating)
  dwpc_neighbors  {slug: [[neighbor_slug, score], ...top 30]}   (hub-corrected expansion)
  modularity, tau

Run:  python build_graph_report.py [--percentile 85] [--topm 30]
"""

import argparse
import json
import sys
from pathlib import Path

import numpy as np

CONSOL = Path("C:/Users/user/.claude/skills/consolidation")
sys.path.insert(0, str(CONSOL))
import graph_analysis as ga       # noqa: E402

CKPT = Path(__file__).parent / "desc_checkpoint.db"
OUT = Path(__file__).parent / "graph_report.json"


def dwpc_matrix(cosine, tau):
    """Identical to graph_analysis.compute_dwpc(k_max=2) but as matmuls.
    DWPC(i,j) = 1[edge] (k=1) + PC2/max(PDP2,1)^0.4 (k=2, hub-corrected)."""
    adj = np.where(cosine > tau, cosine, 0.0)
    np.fill_diagonal(adj, 0.0)
    Abin = (adj > 0).astype(float)
    deg = Abin.sum(axis=1)
    PC2 = Abin @ Abin
    np.fill_diagonal(PC2, 0.0)
    PDP2 = Abin @ (deg[:, None] * Abin)
    k2 = np.where(PC2 > 0, PC2 / np.maximum(PDP2, 1.0) ** 0.4, 0.0)
    dwpc = Abin + k2
    np.fill_diagonal(dwpc, 0.0)
    return dwpc


def subgraph_dwpc_neighbors(names, cosine, tau, part, topm):
    """DWPC computed WITHIN each community subgraph (hub-correction relative to
    the community, not the global hub structure) -> per-skill top-M within-community
    DWPC neighbors. Coarse communities act as candidate pools; subgraph DWPC does
    the precise ranking inside them (operator: 'use dwpc on subgraphs')."""
    idx = {n: i for i, n in enumerate(names)}
    by_comm = {}
    for n, c in part.items():
        by_comm.setdefault(c, []).append(n)
    neighbors = {}
    for c, members in by_comm.items():
        if len(members) < 2:
            neighbors[members[0]] = []
            continue
        gi = [idx[m] for m in members]
        sub = cosine[np.ix_(gi, gi)]
        d = dwpc_matrix(sub, tau)
        for li, m in enumerate(members):
            row = d[li]
            top = np.argsort(-row)[:topm]
            neighbors[m] = [[members[j], round(float(row[j]), 4)] for j in top if row[j] > 0]
    return neighbors


def run(percentile, topm):
    names, E = ga.load_embeddings(CKPT)
    print(f"loaded {len(names)} skill embeddings", flush=True)
    cosine = E @ E.T
    tau = ga.adaptive_tau(cosine, percentile)
    G, _ = ga.build_graph(names, E, tau)
    print(f"tau={tau:.4f}  nodes={G.number_of_nodes()} edges={G.number_of_edges()} "
          f"density={G.number_of_edges()/(len(names)*(len(names)-1)/2):.3f}", flush=True)
    part = ga.louvain_partition(G)
    mod = ga.modularity_score(part, G)
    metrics = ga.subgraph_metrics(G, part)
    ncomm = len(set(part.values()))
    print(f"louvain: {ncomm} communities  modularity={mod:.3f}", flush=True)
    neighbors = subgraph_dwpc_neighbors(names, cosine, tau, part, topm)
    report = {
        "tau": round(float(tau), 4), "modularity": round(float(mod or 0.0), 4),
        "skill_comm": {n: int(part[n]) for n in names},
        "comm_metrics": {str(cid): {k: v for k, v in m.items() if k != "members"}
                         for cid, m in metrics.items()},
        "dwpc_neighbors": neighbors,
    }
    OUT.write_text(json.dumps(report), encoding="utf-8")
    # quick quality readout: community size + density/conductance distribution
    sizes = sorted((m["size"] for m in metrics.values()), reverse=True)
    dens = [m["density"] for m in metrics.values() if m["size"] > 2]
    cond = [m["conductance"] for m in metrics.values() if m["size"] > 2]
    print(f"community sizes: max={sizes[0]} median={sizes[len(sizes)//2]} "
          f"singletons={sum(1 for s in sizes if s==1)}", flush=True)
    print(f"density (size>2): median={np.median(dens):.3f}  conductance median={np.median(cond):.3f}", flush=True)
    print(f"wrote {OUT.name}", flush=True)


if __name__ == "__main__":
    ap = argparse.ArgumentParser(description=__doc__)
    ap.add_argument("--percentile", type=float, default=85.0)
    ap.add_argument("--topm", type=int, default=30)
    args = ap.parse_args()
    run(args.percentile, args.topm)
