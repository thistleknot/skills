"""
graph_analysis.py -- Community detection, cluster analysis, and graph metrics
for the skill corpus.

Standalone usage:
    python graph_analysis.py [--db PATH] [--threshold TAU] [--out PATH] [--no-plot]

Or called from consolidate.py via --graph.

Pipeline:
    embeddings → cosine graph → WCC → Louvain → k-means BSS/TSS elbow →
    ARI cross-validation → subgraph metrics → betweenness centrality →
    DWPC (k=1, k=2) → spring layout → JSON report + PNG + observer prompt

Require:  numpy, networkx, python-louvain, scikit-learn, matplotlib installed
Guarantee: writes graph_report.json + graph.png to out_dir; prints observer prompt
Maintain:  non-breaking; does not modify .checkpoint.db schema
Assert:    at least 3 skills with embeddings before analysis begins
"""

import argparse
import json
import math
import os
import sqlite3
import sys
from pathlib import Path

# Ensure UTF-8 output on Windows consoles that default to cp1252
if hasattr(sys.stdout, "reconfigure"):
    sys.stdout.reconfigure(encoding="utf-8", errors="replace")

import matplotlib
matplotlib.use("Agg")
import matplotlib.cm as cm
import matplotlib.patches as mpatches
import matplotlib.pyplot as plt
import networkx as nx
import numpy as np
from scipy import stats as scipy_stats
from sklearn.cluster import KMeans
from sklearn.metrics import adjusted_rand_score, silhouette_score
from sklearn.preprocessing import normalize

try:
    import community as community_louvain
    _LOUVAIN_BACKEND = "python-louvain"
except ImportError:
    community_louvain = None
    _LOUVAIN_BACKEND = "networkx"

JACCARD_TAU = 0.30   # consolidation semantic floor (Jaccard domain)


# ---------------------------------------------------------------------------
# Data loading
# ---------------------------------------------------------------------------

def load_embeddings(db_path: Path) -> tuple[list[str], np.ndarray]:
    """Load skill names and unit-normalised embedding vectors from checkpoint DB.

    Require:  db_path exists; skill_derivations table has embedding_json column
    Guarantee: returns (names, E) where E.shape == (N, dim) and rows are L2-normalised
    Maintain:  skills with null or empty embedding_json are silently skipped
    Assert:    at least one embedding row must be present
    """
    con = sqlite3.connect(db_path)
    try:
        rows = con.execute(
            "SELECT skill_name, embedding_json FROM skill_derivations "
            "WHERE embedding_json IS NOT NULL AND embedding_json != '[]'"
        ).fetchall()
    finally:
        con.close()

    names: list[str] = []
    vecs: list[list[float]] = []
    for name, emb_json in rows:
        vec: list[float] = json.loads(emb_json)
        if vec:
            names.append(name)
            vecs.append(vec)

    assert names, "No embeddings found in checkpoint DB — run consolidate.py first"
    return names, normalize(np.array(vecs, dtype=float))


# ---------------------------------------------------------------------------
# Graph construction
# ---------------------------------------------------------------------------

def significance_tau(
    cosine: np.ndarray,
    alpha: float = 0.05,
    n_dim: int | None = None,
    correction: str = "bonferroni",
) -> tuple[float, float, int]:
    """Threshold: pairs whose cosine is statistically significantly above the corpus mean.

    Dense semantic corpora (all skills share domain vocabulary) have a non-zero
    background similarity floor.  A raw Pearson t-test on n=768 embedding dims makes
    almost every pair significant -- useless for graph pruning.

    Instead, model the null as the empirical background distribution of pairwise
    cosines and test whether each pair is *above average* (one-tailed z-test):

        z_ij = (cos_ij - mu) / sigma
        H0:  z_ij ~ N(0, 1)
        H1:  z_ij > 0  (pair is more similar than background)

    Apply Bonferroni or BH/FDR across all N*(N-1)/2 pairs.  The returned tau is the
    cosine value at the critical z -- pairs above tau are significantly above background.

    Rationale:  cosine IS Pearson r for unit-norm vectors.  But "is r different from 0?"
    is not the right question when all skills have r>0.15 with each other.  "Is this pair
    more correlated than typical?" is the semantically correct question, and the
    empirical z-score tests exactly that.

    Bonferroni (default): alpha_adj = alpha / n_pairs  ->  conservative, fewer edges
    BH (fdr_bh):          Benjamini-Hochberg FDR        ->  more liberal, more edges

    Require:  cosine is symmetric (N,N); off-diagonal entries in (0,1) for unit vectors
    Guarantee: returns (r_threshold, effective_alpha, n_significant_pairs)
    Maintain:  diagonal is excluded; n_dim kept for API compatibility but unused
    """
    N = cosine.shape[0]
    n_pairs = N * (N - 1) // 2

    r_vals = cosine[np.triu_indices(N, k=1)]

    mu = float(r_vals.mean())
    sigma = float(r_vals.std())
    if sigma < 1e-12:
        return float(r_vals.mean()), float(alpha), 0

    z_vals = (r_vals - mu) / sigma
    p_vals = scipy_stats.norm.sf(z_vals)  # one-tailed: P(Z > z)

    if correction == "bonferroni":
        alpha_adj = alpha / n_pairs
        sig_mask = p_vals <= alpha_adj
    else:
        sorted_idx = np.argsort(p_vals)
        sorted_p = p_vals[sorted_idx]
        thresholds = alpha * np.arange(1, n_pairs + 1) / n_pairs
        bh_mask = sorted_p <= thresholds
        if bh_mask.any():
            cutoff = int(np.where(bh_mask)[0].max())
            alpha_adj = float(sorted_p[cutoff])
        else:
            alpha_adj = 0.0
        sig_mask = p_vals <= alpha_adj

    if sig_mask.any():
        r_threshold = float(np.min(r_vals[sig_mask]))
    else:
        r_threshold = float(np.percentile(r_vals, 85.0))

    return r_threshold, float(alpha_adj), int(sig_mask.sum())


def adaptive_tau(cosine: np.ndarray, percentile: float = 85.0) -> float:
    """Fallback: percentile-based threshold when significance is not appropriate.

    Require:  cosine is symmetric (N,N); percentile in (0, 100)
    Guarantee: returns Nth percentile of off-diagonal cosines, clamped to [0.5, 0.99]
    """
    N = cosine.shape[0]
    off_diag = [float(cosine[i, j]) for i in range(N) for j in range(i + 1, N)]
    raw = float(np.percentile(off_diag, percentile))
    return max(0.50, min(0.99, raw))


def build_graph(names: list[str], E: np.ndarray, tau: float) -> tuple[nx.Graph, np.ndarray]:
    """Build weighted undirected graph from cosine similarity matrix.

    Require:  E is L2-normalised (unit rows), tau > 0
    Guarantee: edges only where cosine(i,j) > tau; no self-loops
    """
    cosine: np.ndarray = E @ E.T
    N = len(names)
    G = nx.Graph()
    G.add_nodes_from(names)
    for i in range(N):
        for j in range(i + 1, N):
            w = float(cosine[i, j])
            if w > tau:
                G.add_edge(names[i], names[j], weight=w)
    return G, cosine


# ---------------------------------------------------------------------------
# Community detection
# ---------------------------------------------------------------------------

def louvain_partition(G: nx.Graph) -> dict[str, int]:
    """Run Louvain community detection; fall back to networkx greedy modularity."""
    if _LOUVAIN_BACKEND == "python-louvain":
        return community_louvain.best_partition(G, weight="weight")
    comms = nx.algorithms.community.greedy_modularity_communities(G, weight="weight")
    return {node: cid for cid, comm in enumerate(comms) for node in comm}


def modularity_score(partition: dict[str, int], G: nx.Graph) -> float | None:
    """Return modularity for the partition, or None if backend unavailable."""
    if _LOUVAIN_BACKEND == "python-louvain":
        return community_louvain.modularity(partition, G, weight="weight")
    return None


# ---------------------------------------------------------------------------
# k-means elbow
# ---------------------------------------------------------------------------

def kmeans_elbow(E: np.ndarray, k_max: int | None = None) -> tuple[int, list[float], list[float]]:
    """Find optimal k via BSS/TSS elbow (most-concave bend in the curve).

    Require:  E is (N, dim); k tested over [2, min(k_max, N-1)]
    Guarantee: returns (optimal_k, bss_tss_curve, silhouette_curve)
    Maintain:  elbow selected by argmin of discrete second derivative (most negative = sharpest bend)

    Note: BSS/TSS is monotonically non-decreasing → directly maximising it gives k=N.
    The elbow is the k where marginal gain decelerates most sharply.
    """
    N = E.shape[0]
    k_max = min(k_max or max(2, math.ceil(math.sqrt(N))), N - 1)
    k_range = list(range(2, k_max + 1))

    total_var = float(np.sum((E - E.mean(axis=0)) ** 2))

    bss_tss_curve: list[float] = []
    sil_curve: list[float] = []

    for k in k_range:
        km = KMeans(n_clusters=k, n_init=10, random_state=42)
        labels = km.fit_predict(E)
        wss = float(km.inertia_)
        bss_tss_curve.append((total_var - wss) / total_var if total_var > 0 else 0.0)
        sil = silhouette_score(E, labels) if len(set(labels)) > 1 else 0.0
        sil_curve.append(float(sil))

    if len(bss_tss_curve) < 3:
        return k_range[0], bss_tss_curve, sil_curve

    # second derivative: negative = concave bend; most negative = sharpest elbow
    d2 = [
        bss_tss_curve[i + 2] - 2 * bss_tss_curve[i + 1] + bss_tss_curve[i]
        for i in range(len(bss_tss_curve) - 2)
    ]
    elbow_idx = int(np.argmin(d2))      # most-concave point
    optimal_k = k_range[elbow_idx + 1]  # d2[i] is centred at k_range[i+1]
    return optimal_k, bss_tss_curve, sil_curve


# ---------------------------------------------------------------------------
# Subgraph metrics
# ---------------------------------------------------------------------------

def subgraph_metrics(G: nx.Graph, partition: dict[str, int]) -> dict[int, dict]:
    """Compute density, conductance, and LCC-ratio per community.

    Require:  partition keys cover all G.nodes()
    Guarantee: returns {community_id: {members, size, density, conductance, lcc_ratio}}
    """
    metrics: dict[int, dict] = {}
    for cid in sorted(set(partition.values())):
        members = [n for n, c in partition.items() if c == cid]
        subg = G.subgraph(members)

        density = nx.density(subg)

        cut_weight = sum(
            d["weight"]
            for u, v, d in G.edges(data=True)
            if (partition[u] == cid) != (partition[v] == cid)
        )
        vol_s = sum(d for _, d in G.degree(members, weight="weight"))
        vol_rest = sum(d for n, d in G.degree(weight="weight") if partition[n] != cid)
        denom = min(vol_s, vol_rest)
        conductance = cut_weight / denom if denom > 0 else 0.0

        lcc_ratio = 0.0
        if members:
            lcc = max(nx.connected_components(subg), key=len)
            lcc_ratio = len(lcc) / len(members)

        metrics[cid] = {
            "members": members,
            "size": len(members),
            "density": round(density, 4),
            "conductance": round(conductance, 4),
            "lcc_ratio": round(lcc_ratio, 4),
        }
    return metrics


# ---------------------------------------------------------------------------
# DWPC (Degree-Weighted Path Count)
# ---------------------------------------------------------------------------

def compute_dwpc(names: list[str], cosine: np.ndarray, tau: float, k_max: int = 2) -> np.ndarray:
    """Compute hub-corrected connectivity via DWPC for paths up to length k_max.

    DWPC(i,j,k) = PC(i,j,k) / PDP(i,j,k)^0.4
      PC  = count of simple paths of length k
      PDP = product of degrees of intermediate nodes (no endpoints)

    k=1: direct edges only (no intermediates, PDP=1, DWPC = 1 per edge)
    k=2: paths through one intermediate node (O(N^3), fine for N≤200)

    Require:  cosine is (N,N); k_max in {1, 2}
    Guarantee: returns (N,N) DWPC matrix summed over k in [1..k_max]; symmetric
    """
    N = len(names)
    adj = np.where(cosine > tau, cosine, 0.0)
    degrees = (adj > 0).sum(axis=1).astype(float)

    dwpc = np.zeros((N, N), dtype=float)

    # k=1
    for i in range(N):
        for j in range(i + 1, N):
            if adj[i, j] > 0:
                dwpc[i, j] += 1.0   # PDP=1 (no intermediate nodes)
                dwpc[j, i] = dwpc[i, j]

    if k_max >= 2:
        # k=2
        for i in range(N):
            for j in range(i + 1, N):
                pc2 = 0
                pdp2 = 0.0
                for m in range(N):
                    if m != i and m != j and adj[i, m] > 0 and adj[m, j] > 0:
                        pc2 += 1
                        pdp2 += degrees[m]
                if pc2 > 0:
                    dwpc[i, j] += pc2 / max(pdp2, 1.0) ** 0.4
                    dwpc[j, i] = dwpc[i, j]

    return dwpc


# ---------------------------------------------------------------------------
# Visualisation
# ---------------------------------------------------------------------------

def render_spring_layout(
    G: nx.Graph,
    partition: dict[str, int],
    betweenness: dict[str, float],
    out_path: Path,
) -> None:
    """Render spring layout coloured by Louvain community.

    Node size encodes betweenness centrality (bridges are visually prominent).
    Edge alpha encodes similarity weight.

    Require:  out_path parent directory exists
    Guarantee: saves PNG to out_path at 150 dpi; closes figure
    """
    n_comm = len(set(partition.values()))
    try:
        cmap = matplotlib.colormaps.get_cmap("tab20")
    except AttributeError:
        cmap = cm.get_cmap("tab20", max(n_comm, 2))

    node_colors = [cmap(partition.get(n, 0) % 20) for n in G.nodes()]
    node_sizes = [300 + 4000 * betweenness.get(n, 0.0) for n in G.nodes()]
    k_spring = 1.5 / math.sqrt(len(G.nodes()) + 1)
    pos = nx.spring_layout(G, weight="weight", seed=42, k=k_spring)

    fig, ax = plt.subplots(figsize=(20, 15))
    ax.set_facecolor("#1a1a2e")
    fig.patch.set_facecolor("#1a1a2e")

    for u, v, d in G.edges(data=True):
        alpha = min(1.0, max(0.05, float(d.get("weight", 0.3))))
        nx.draw_networkx_edges(
            G, pos, edgelist=[(u, v)],
            alpha=alpha, edge_color="#8888bb", width=0.9, ax=ax,
        )

    nx.draw_networkx_nodes(
        G, pos, node_color=node_colors, node_size=node_sizes, alpha=0.88, ax=ax,
    )
    nx.draw_networkx_labels(G, pos, font_size=6, font_color="white", ax=ax)

    patches = [
        mpatches.Patch(color=cmap(cid % 20), label=f"Community {cid}")
        for cid in sorted(set(partition.values()))
    ]
    ax.legend(handles=patches, loc="lower right", fontsize=7,
              facecolor="#2a2a4e", labelcolor="white", framealpha=0.8)
    ax.set_title("Skill Graph — Spring Layout (Louvain Communities)", color="white", fontsize=14)
    ax.axis("off")

    plt.tight_layout()
    plt.savefig(out_path, dpi=150, bbox_inches="tight", facecolor=fig.get_facecolor())
    plt.close()
    print(f"Graph image saved -> {out_path}")


# ---------------------------------------------------------------------------
# Observer agent prompt
# ---------------------------------------------------------------------------

def print_observer_prompt(report: dict) -> None:
    """Print a structured disposition prompt for the observer agent."""
    g = report["graph"]
    lou = report["louvain"]
    km = report["kmeans"]
    agr = report["agreement"]

    print(f"""
{'='*80}
OBSERVER AGENT DISPOSITION PROMPT
{'='*80}
Skills: {report['n_skills']}  edges: {g['edges']}  tau: {report['tau']}
WCC: {g['wcc_count']} component(s)  sizes: {g['wcc_sizes'][:5]}

LOUVAIN -- {lou['n_communities']} communities  modularity={lou['modularity']}
K-MEANS -- optimal k={km['optimal_k']}
ARI (Louvain vs k-means) = {agr['ari']:.4f}  -> {agr['interpretation']}

COMMUNITIES (sorted by size desc):""")

    for cid_str, m in sorted(report["communities"].items(), key=lambda x: -x[1]["size"]):
        members_str = ", ".join(m["members"][:8]) + ("..." if len(m["members"]) > 8 else "")
        print(f"  [{cid_str}] size={m['size']:2d}  density={m['density']:.3f}  "
              f"conductance={m['conductance']:.3f}  lcc={m['lcc_ratio']:.2f}")
        print(f"       {members_str}")

    print("\nTOP BRIDGE SKILLS (betweenness centrality):")
    for item in report["betweenness_top10"][:7]:
        print(f"  {item['skill']:<42}  {item['score']:.5f}")

    print("\nTOP DWPC PAIRS (hub-corrected connectivity):")
    for item in report["dwpc_top15_pairs"][:7]:
        print(f"  {item['a']:<35} <-> {item['b']:<35}  {item['score']:.4f}")

    print(f"""
DISPOSITION TASK  (optionally verify against graph.png spring layout):
For each community, decide:
  CONSOLIDATE  - high density + low conductance  (redundant -> merge/migrate)
  CROSS-REF    - moderate density                (related -> See Also links)
  KEEP         - low density or high conductance (genuinely separate)
  INSPECT      - bridge skill (high betweenness) - may be cross-cutting or misclassified

OUTPUT FORMAT:
  Community <N>: [CONSOLIDATE|CROSS-REF|KEEP|INSPECT]
  Rationale: <one line>
{'='*80}""")


# ---------------------------------------------------------------------------
# Main pipeline
# ---------------------------------------------------------------------------

def run_graph_analysis(
    db_path: Path,
    tau: float | None = None,
    out_dir: Path | None = None,
    render: bool = True,
    threshold_method: str = "significance",
    alpha: float = 0.05,
    sig_correction: str = "bonferroni",
    observe: bool = False,
) -> dict:
    """Full analysis pipeline.

    Require:  db_path contains skill_derivations with embedding_json;
              numpy, networkx, sklearn, scipy, matplotlib available
    Guarantee: returns report dict; writes graph_report.json (+ graph.png if render,
               + graph_disposition.txt if observe)
    Maintain:  .checkpoint.db is not modified
    Assert:    N >= 3 skills with embeddings

    tau:              explicit threshold (overrides threshold_method when provided)
    threshold_method: 'significance' (default) — empirical z-score above background,
                      Bonferroni/BH corrected; falls back to 85th-pct if too strict
                      'percentile'   — 85th pct of pairwise cosines (explicit fallback)
    alpha:            significance level for threshold_method='significance' (default 0.05)
    sig_correction:   'bonferroni' (default, conservative) or 'fdr_bh' (Benjamini-Hochberg)
    observe:          if True, call observer LLM for community disposition after analysis
    """
    out_dir = out_dir or db_path.parent.parent

    print("Loading embeddings from checkpoint DB...")
    names, E = load_embeddings(db_path)
    N = len(names)
    n_dim = E.shape[1]
    print(f"  {N} skills  embedding_dim={n_dim}")
    assert N >= 3, f"Need >= 3 skills with embeddings, found {N}"

    cosine_full: np.ndarray = E @ E.T
    tau_method_used = threshold_method

    if tau is not None:
        tau_method_used = "explicit"
        print(f"  Explicit tau = {tau:.4f}")
    elif threshold_method == "significance":
        tau, alpha_adj, n_sig = significance_tau(cosine_full, alpha=alpha,
                                                  n_dim=n_dim, correction=sig_correction)
        n_pairs = N * (N - 1) // 2
        if n_sig == 0:
            tau_method_used = "significance->percentile_fallback"
            print(f"  Significance tau: {sig_correction} too strict (0/{n_pairs} pairs survived)")
            print(f"    -> fallback to 85th-pct  tau = {tau:.4f}")
        else:
            print(f"  Significance tau ({sig_correction}, alpha={alpha}) = {tau:.4f}")
            print(f"    effective alpha = {alpha_adj:.2e}  significant pairs = {n_sig}/{n_pairs}")
    else:
        tau = adaptive_tau(cosine_full, percentile=85.0)
        print(f"  Percentile tau (85th pct) = {tau:.4f}")

    print(f"Building cosine graph (tau={tau:.4f})...")
    G, cosine = build_graph(names, E, tau)
    print(f"  {G.number_of_nodes()} nodes  {G.number_of_edges()} edges")

    wccs = list(nx.connected_components(G))
    wcc_sizes = sorted([len(c) for c in wccs], reverse=True)
    print(f"  WCC: {len(wccs)} components  sizes={wcc_sizes[:6]}{'...' if len(wcc_sizes) > 6 else ''}")

    print("Running Louvain community detection...")
    partition = louvain_partition(G)
    n_communities = len(set(partition.values()))
    modularity = modularity_score(partition, G)
    mod_str = f"{modularity:.4f}" if modularity is not None else "N/A"
    print(f"  {n_communities} communities  modularity={mod_str}")

    print("Running k-means elbow search...")
    optimal_k, bss_tss_curve, sil_curve = kmeans_elbow(E)
    km = KMeans(n_clusters=optimal_k, n_init=10, random_state=42)
    km_labels_arr = km.fit_predict(E)
    km_labels = {names[i]: int(km_labels_arr[i]) for i in range(N)}
    sil_at_k = sil_curve[optimal_k - 2] if len(sil_curve) >= optimal_k - 1 else None
    sil_str = f"{sil_at_k:.4f}" if sil_at_k is not None else "N/A"
    print(f"  optimal k={optimal_k}  silhouette={sil_str}")

    ari = float(adjusted_rand_score(
        [partition[n] for n in names],
        [km_labels[n] for n in names],
    ))
    print(f"  ARI(Louvain, k-means)={ari:.4f}")

    print("Computing subgraph metrics...")
    comm_metrics = subgraph_metrics(G, partition)

    print("Computing betweenness centrality...")
    betweenness = nx.betweenness_centrality(G, weight="weight", normalized=True)
    top_bridges = sorted(betweenness.items(), key=lambda x: x[1], reverse=True)[:10]

    print("Computing DWPC (k=1, k=2)...")
    dwpc_mat = compute_dwpc(names, cosine, tau, k_max=2)
    top_dwpc: list[tuple[float, str, str]] = []
    for i in range(N):
        for j in range(i + 1, N):
            if dwpc_mat[i, j] > 0:
                top_dwpc.append((float(dwpc_mat[i, j]), names[i], names[j]))
    top_dwpc.sort(reverse=True)

    if render:
        render_spring_layout(G, partition, betweenness, out_dir / "graph.png")

    report = {
        "n_skills": N,
        "tau": round(tau, 6),
        "threshold_method": tau_method_used,
        "louvain_backend": _LOUVAIN_BACKEND,
        "graph": {
            "nodes": G.number_of_nodes(),
            "edges": G.number_of_edges(),
            "wcc_count": len(wccs),
            "wcc_sizes": wcc_sizes,
        },
        "louvain": {
            "n_communities": n_communities,
            "modularity": round(modularity, 6) if modularity is not None else None,
            "labels": partition,
        },
        "kmeans": {
            "optimal_k": optimal_k,
            "bss_tss_curve": [round(v, 6) for v in bss_tss_curve],
            "silhouette_curve": [round(v, 6) for v in sil_curve],
            "labels": km_labels,
        },
        "agreement": {
            "ari": round(ari, 6),
            "interpretation": (
                "high confidence — Louvain and k-means agree" if ari > 0.7
                else "moderate — surface both to observer" if ari > 0.3
                else "disagreement — different structure; surface both"
            ),
        },
        "communities": {str(cid): m for cid, m in comm_metrics.items()},
        "betweenness_top10": [
            {"skill": n, "score": round(s, 6)} for n, s in top_bridges
        ],
        "dwpc_top15_pairs": [
            {"score": round(v, 6), "a": a, "b": b} for v, a, b in top_dwpc[:15]
        ],
    }

    report_path = out_dir / "graph_report.json"
    with open(report_path, "w", encoding="utf-8") as f:
        json.dump(report, f, indent=2)
    print(f"Report saved -> {report_path}")

    print_observer_prompt(report)
    if observe:
        try:
            observer_disposition(report, out_dir)
        except RuntimeError as exc:
            print(f"  [observer] LLM call failed: {exc}")
            print("  Re-run with Ollama running, or set LLM_BASE_URL to another endpoint.")
    return report


# ---------------------------------------------------------------------------
# Observer LLM disposition
# ---------------------------------------------------------------------------

def _call_llm_observer(prompt: str, max_tokens: int = 1200) -> str:
    """Call local Ollama LLM for observer disposition. Returns raw text.

    Require:  Ollama running at LLM_BASE_URL (default http://localhost:11434/v1)
    Guarantee: returns non-empty text after <think> stripping
    Maintain:  falls back through model list; raises RuntimeError if all fail
    """
    import re as _re
    import shutil
    import subprocess

    base_url = os.environ.get("LLM_BASE_URL", "http://localhost:11434/v1")
    api_key = os.environ.get("LLM_API_KEY", "ollama")
    env_model = os.environ.get("LLM_MODEL", "qwen3.5:0.8b")
    models = list(dict.fromkeys(m for m in [env_model, "qwen2.5-coder:1.5b"] if m))

    endpoint = f"{base_url.rstrip('/')}/chat/completions"
    curl_bin = shutil.which("curl.exe") or shutil.which("curl")
    if not curl_bin:
        raise RuntimeError("curl is required for local LLM calls")

    last_err: Exception | None = None
    for model in models:
        payload = json.dumps({
            "model": model,
            "messages": [{"role": "user", "content": prompt}],
            "temperature": 0.0,
            "max_tokens": max_tokens,
        })
        try:
            result = subprocess.run(
                [curl_bin, "-sS", endpoint,
                 "-H", "Content-Type: application/json",
                 "-H", f"Authorization: Bearer {api_key}",
                 "--data-binary", "@-"],
                input=payload.encode(),
                capture_output=True,
                timeout=120,
            )
        except subprocess.TimeoutExpired as exc:
            last_err = exc
            continue
        if result.returncode != 0:
            last_err = RuntimeError(result.stderr.decode(errors="replace"))
            continue
        try:
            data = json.loads(result.stdout)
            content = data["choices"][0]["message"]["content"].strip()
            if not content:
                last_err = RuntimeError(f"model {model} returned empty content")
                continue
            content = _re.sub(r"<think>.*?</think>", "", content, flags=_re.DOTALL).strip()
            if content:
                return content
            last_err = RuntimeError(f"model {model} content empty after think-strip")
        except (KeyError, json.JSONDecodeError) as exc:
            last_err = exc

    raise last_err or RuntimeError("No LLM response from observer models")


def observer_disposition(report: dict, out_dir: Path) -> str:
    """Run the observer LLM agent on communities; save + return disposition text.

    Require:  report contains louvain.labels, communities, betweenness_top10
    Guarantee: writes graph_disposition.txt; returns raw disposition text
    Maintain:  does not modify report dict or any other output file

    Strategy: singletons and rule-deterministic cases are resolved in Python.
    Large communities (size >= 4) are sent to the LLM one at a time so the
    0.8b model can focus on a single community's member names.
    """
    from collections import defaultdict

    partition: dict[str, int] = report.get("louvain", {}).get("labels", {})
    communities_metrics: dict[str, dict] = report.get("communities", {})
    bridge_set = {
        entry["skill"]
        for entry in report.get("betweenness_top10", [])[:7]
        if entry.get("score", 0) > 0
    }

    # group members by community id
    groups: dict[int, list[str]] = defaultdict(list)
    for skill, cid in partition.items():
        groups[cid].append(skill)

    disposition_lines: list[str] = []

    for cid in sorted(groups):
        members = sorted(groups[cid])
        m = communities_metrics.get(str(cid), {})
        density = m.get("density", 0.0)
        conductance = m.get("conductance", 0.0)
        size = len(members)
        has_bridge = any(s in bridge_set for s in members)
        bridge_members = [s for s in members if s in bridge_set]

        # rule-based disposition
        if size == 1:
            disp = "INSPECT" if has_bridge else "KEEP"
            rationale = (
                f"singleton; bridge skill {bridge_members[0]}" if has_bridge
                else f"singleton; {members[0]} is isolated, no action needed"
            )
            disposition_lines.append(f"Community {cid}: {disp} - {rationale}")
            continue

        if has_bridge:
            rule_disp = "INSPECT"
        elif density > 0.8 and conductance < 0.5:
            rule_disp = "CONSOLIDATE"
        elif density >= 0.3:
            rule_disp = "CROSS-REF"
        else:
            rule_disp = "KEEP"

        # for small groups (2-3), rule is sufficient
        if size < 4:
            b_note = f"; bridge: {', '.join(bridge_members)}" if bridge_members else ""
            disposition_lines.append(
                f"Community {cid}: {rule_disp} - size={size}, "
                f"density={density:.2f}, conductance={conductance:.2f}{b_note}; "
                f"members: {', '.join(members)}"
            )
            continue

        # large community: ask LLM for name-aware rationale
        b_note = (
            f" [bridge skills present: {', '.join(bridge_members)}]"
            if bridge_members else ""
        )
        llm_prompt = (
            f"Skill library community analysis.\n"
            f"Community {cid}: size={size}, density={density:.3f}, "
            f"conductance={conductance:.3f}{b_note}\n"
            f"Members: {', '.join(members)}\n\n"
            f"Rule-based suggestion: {rule_disp}\n\n"
            f"Output exactly ONE line:\n"
            f"Community {cid}: [CONSOLIDATE|CROSS-REF|KEEP|INSPECT] - <one sentence why>\n"
            f"Confirm or override the suggestion based on whether the member names "
            f"represent genuinely overlapping skill domains."
        )
        try:
            raw = _call_llm_observer(llm_prompt, max_tokens=120)
            # grab the first line that starts with "Community N:" and strip format brackets
            for line in raw.splitlines():
                stripped = line.strip()
                if stripped.startswith(f"Community {cid}"):
                    # remove any [WORD] bracket wrapping the disposition
                    import re as _re
                    stripped = _re.sub(r"\[([A-Z\-]+)\]", r"\1", stripped)
                    disposition_lines.append(stripped)
                    break
            else:
                # fallback: use rule if model didn't produce expected format
                disposition_lines.append(
                    f"Community {cid}: {rule_disp} - (LLM did not produce expected format; "
                    f"rule-based fallback) density={density:.2f}, conductance={conductance:.2f}"
                )
        except RuntimeError as exc:
            disposition_lines.append(
                f"Community {cid}: {rule_disp} - (LLM error: {exc}; rule-based fallback)"
            )

    output = "\n".join(disposition_lines)
    # replace unicode dashes the model may echo
    output = output.replace("\u2014", "-").replace("\u2013", "-")

    out_path = out_dir / "graph_disposition.txt"
    out_path.write_text(output, encoding="utf-8")
    print(f"Disposition saved -> {out_path}")
    print("\n" + "=" * 72)
    print("OBSERVER DISPOSITION")
    print("=" * 72)
    print(output)
    print("=" * 72)
    return output


# ---------------------------------------------------------------------------
# CLI entry point
# ---------------------------------------------------------------------------

def main() -> None:
    parser = argparse.ArgumentParser(
        description="Skill library graph analysis",
        formatter_class=argparse.RawDescriptionHelpFormatter,
        epilog="""
threshold methods:
  significance  Pearson r t-test, Bonferroni or BH-FDR corrected across all pairs.
                tau = min(r) that survives the correction. The "n" in the t-test is
                the embedding dimension (nomic-embed-text: 768). Bonferroni is the
                default (conservative); use --correction fdr_bh for more edges.
  percentile    85th percentile of all pairwise cosines (simpler fallback).

examples:
  python graph_analysis.py                        # significance, bonferroni, default alpha
  python graph_analysis.py --alpha 0.01           # stricter significance
  python graph_analysis.py --correction fdr_bh    # BH-FDR (more edges)
  python graph_analysis.py --threshold 0.7        # manual tau override
  python graph_analysis.py --method percentile    # 85th-pct fallback
  python graph_analysis.py --observe              # run LLM observer disposition
""",
    )
    parser.add_argument(
        "--db", type=Path,
        default=Path(__file__).resolve().parent / ".checkpoint.db",
        help="consolidation checkpoint DB",
    )
    parser.add_argument(
        "--threshold", type=float, default=None,
        help="explicit edge weight threshold; overrides --method",
    )
    parser.add_argument(
        "--method", dest="threshold_method", default="significance",
        choices=["significance", "percentile"],
        help="threshold selection method (default: significance)",
    )
    parser.add_argument(
        "--alpha", type=float, default=0.05,
        help="significance level for --method significance (default: 0.05)",
    )
    parser.add_argument(
        "--correction", dest="sig_correction", default="bonferroni",
        choices=["bonferroni", "fdr_bh"],
        help="multiple-testing correction (default: bonferroni)",
    )
    parser.add_argument(
        "--out", type=Path,
        default=Path(__file__).resolve().parent.parent,
        help="output directory for graph_report.json, graph.png, graph_disposition.txt "
             "(default: repo root, one level above consolidation/)",
    )
    parser.add_argument("--no-plot", action="store_true", help="skip spring layout rendering")
    parser.add_argument(
        "--observe", action="store_true",
        help="run observer LLM (qwen3.5:0.8b via Ollama) to emit community dispositions",
    )
    args = parser.parse_args()

    run_graph_analysis(
        db_path=args.db,
        tau=args.threshold,
        out_dir=args.out,
        render=not args.no_plot,
        threshold_method=args.threshold_method,
        alpha=args.alpha,
        sig_correction=args.sig_correction,
        observe=args.observe,
    )


if __name__ == "__main__":
    main()
