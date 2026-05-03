---
name: cluster-quantized-knn
description: >
  Cluster-quantized O(1) approximate distance for KNN scoring and walk-mode
  traversal over embedding spaces. Use when you have a pre-clustered corpus
  (micro/meso/macro labels or any cluster assignment), a fixed KNN index, and
  need fast per-pair similarity queries at query time — especially for interactive
  or real-time use cases where recomputing distances on every step is too slow.
  Covers precomputation protocol, two-path routing (unfiltered vs filter-first),
  and the correctness boundary where the approximation breaks down.
status: active
last_validated: 2026-05-02
supersedes: []
validation_method: session
---

# Cluster-Quantized KNN

## When to Use

Use this skill when:

- You have a corpus with **cluster assignments** (from KMeans, HDBSCAN, etc.) and a **pre-built KNN index**
- You need **O(1) distance approximations** at query time — real-time walk, streaming recommendation, interactive ranking
- Exact pairwise distance is fast enough offline (precompute once) but too slow per-query
- Your corpus is **moderately sized** (100–100k points) — the centroid matrix is C² where C = cluster count

Do NOT use when:
- You have no cluster structure (use exact distance or HNSW instead)
- The corpus changes frequently (centroid table goes stale)
- Precision > ~90% is required (use exact distance or product quantization)

---

## Core Idea

Replace `dist(i, j) = sqrt(Σ(xi−xj)²)` with a triangle-inequality approximation:

```
dist(i, j) ≈ centDist[cluster_i][cluster_j] + intra[i] + intra[j]
```

Where:
- `centDist[a][b]` = Euclidean distance between cluster centroids a and b (precomputed)
- `intra[i]` = distance from song i to its own cluster centroid (precomputed)

**Precomputation**: O(N) + O(C²) — one pass to compute centroids, one pass for intra-distances, one C×C matrix for centroid-to-centroid distances.

**Query time**: O(1) — two array lookups + one hash table lookup.

**Error profile**: Exact within same-cluster pairs (centDist = 0). Across clusters, provides an upper bound with error proportional to intra-cluster radius. Error is loose at cluster boundaries but acceptable for perceptual similarity ranking where ground truth is fuzzy anyway.

---

## Precomputation (JavaScript)

```javascript
const _kqCent  = {};                          // cluster_label → {x, y, z}
const _kqIntra = new Float32Array(SONGS.length); // song_idx → dist to own centroid
const _kqCentD = {};                          // "ci|cj" → centroid distance

(function _precomputeClusterDists() {
  // Pass 1: accumulate centroid sums
  const sums = {};
  for (let i = 0; i < SONGS.length; i++) {
    const s = SONGS[i], c = s.micro;  // use whatever cluster label field you have
    if (!sums[c]) sums[c] = {x:0, y:0, z:0, n:0};
    sums[c].x += s.x; sums[c].y += s.y; sums[c].z += s.z; sums[c].n++;
  }
  for (const c in sums) {
    const s = sums[c];
    _kqCent[c] = {x: s.x/s.n, y: s.y/s.n, z: s.z/s.n};
  }

  // Pass 2: intra-cluster distance per point
  for (let i = 0; i < SONGS.length; i++) {
    const s = SONGS[i], ct = _kqCent[s.micro];
    const dx = s.x-ct.x, dy = s.y-ct.y, dz = s.z-ct.z;
    _kqIntra[i] = Math.sqrt(dx*dx + dy*dy + dz*dz);
  }

  // Pass 3: centroid-to-centroid distances (symmetric, skip i>j)
  const ckeys = Object.keys(_kqCent);
  for (let a = 0; a < ckeys.length; a++) {
    for (let b = a; b < ckeys.length; b++) {
      const ca = _kqCent[ckeys[a]], cb = _kqCent[ckeys[b]];
      const dx = ca.x-cb.x, dy = ca.y-cb.y, dz = ca.z-cb.z;
      const d = a === b ? 0 : Math.sqrt(dx*dx + dy*dy + dz*dz);
      _kqCentD[ckeys[a]+'|'+ckeys[b]] = d;
      _kqCentD[ckeys[b]+'|'+ckeys[a]] = d;
    }
  }
})();
```

Python equivalent:
```python
import numpy as np

def precompute_cluster_dists(points: np.ndarray, labels: np.ndarray):
    """
    points: (N, D) float array of embedding coordinates
    labels: (N,) int array of cluster assignments
    Returns: centroids dict, intra_dist array, centroid_dist dict
    """
    clusters = np.unique(labels)
    centroids = {c: points[labels == c].mean(axis=0) for c in clusters}
    intra = np.array([np.linalg.norm(points[i] - centroids[labels[i]])
                      for i in range(len(points))])
    cent_dist = {}
    for a in clusters:
        for b in clusters:
            key = (min(a,b), max(a,b))
            if key not in cent_dist:
                cent_dist[key] = np.linalg.norm(centroids[a] - centroids[b])
    return centroids, intra, cent_dist
```

---

## Two-Path Routing

The approximation works well for **song-to-song** (unfiltered): the KNN index is pre-sorted, cluster pruning skips distant clusters entirely.

It **breaks** for **filter-then-rank**: a metadata filter can cut a cluster in half. The centroid of the surviving half is now wrong. The intra-cluster radius assumption no longer holds.

```
┌────────────────────────────────┐
│  hasFilter?                    │
│  (sel.length < 0.9 * N)        │
└────────┬───────────────────────┘
         │ yes                    │ no
         ▼                        ▼
  Filter-first path         Song-to-song path
  ─────────────────         ─────────────────
  1. Get all filtered        1. Use KNN[seed] — already
     survivors (exact dist      rank-sorted from prebuilt index
     is cheap at <1045 pts)  2. Cluster-approx _dist3d() O(1)
  2. Sort by _distExact()       inside MMR/density scorer
  3. Slice top-K*3           3. No centroid pruning needed
  4. Feed to scorer             (KNN provides it implicitly)
```

```javascript
// O(1) approximate — use for unfiltered song-to-song
function _dist3d(i, j) {
  const ci = SONGS[i].micro, cj = SONGS[j].micro;
  const cd = ci === cj ? 0 : (_kqCentD[ci + '|' + cj] || 0);
  return cd + _kqIntra[i] + _kqIntra[j];
}

// Exact Euclidean — use for filter-first path over small survivor sets
function _distExact(i, j) {
  const a = SONGS[i], b = SONGS[j];
  const dx = a.x - b.x, dy = a.y - b.y, dz = a.z - b.z;
  return Math.sqrt(dx * dx + dy * dy + dz * dz);
}
```

---

## Walk Mode Scorers

Both scorers work on a candidate list produced by either path above.

### MMR (Maximal Marginal Relevance)
Greedy no-repeat — maximizes similarity to current song while penalizing similarity to recently played:

```javascript
function _ppMMRSelect(curIdx, candidates) {
  // score = λ·sim(c, current) − (1−λ)·max_sim(c, recent_trail)
  // sim = 1 / (1 + dist)  — converts distance to [0,1] similarity
  const lambda = 0.6;
  const recent = ppWalkTrail.slice(-12);
  let bestScore = -Infinity, best = candidates[0];
  for (const c of candidates) {
    const simCur = 1 / (1 + _dist3d(c, curIdx));
    let maxSimPlayed = 0;
    for (const p of recent) {
      const s = 1 / (1 + _dist3d(c, p));
      if (s > maxSimPlayed) maxSimPlayed = s;
    }
    const score = lambda * simCur - (1 - lambda) * maxSimPlayed;
    if (score > bestScore) { bestScore = score; best = c; }
  }
  return best;
}
```

**λ tuning**: 0.6 = mild decorrelation. Increase toward 1.0 for strict nearest-neighbor. Decrease toward 0.5 for more exploration.

### Density Walk (Stochastic)
Weighted random with temperature — closer songs are more likely but not certain:

```javascript
function _ppDensitySelect(curIdx, candidates) {
  // weight = exp(−dist / T),  T = median distance (adaptive temperature)
  const dists = candidates.map(c => _dist3d(c, curIdx));
  const sorted = [...dists].sort((a, b) => a - b);
  const T = sorted[Math.floor(sorted.length / 2)] || 1;
  const weights = dists.map(d => Math.exp(-d / T));
  const total = weights.reduce((a, b) => a + b, 0);
  let r = Math.random() * total;
  for (let i = 0; i < candidates.length; i++) {
    r -= weights[i];
    if (r <= 0) return candidates[i];
  }
  return candidates[candidates.length - 1];
}
```

**Adaptive temperature**: using median distance means T scales with how spread-out the local neighborhood is. Dense clusters → low T → strong preference for nearest. Sparse regions → high T → more uniform random.

---

## Correctness Boundary

| Scenario | Use | Why |
|---|---|---|
| Unfiltered, full corpus | `_dist3d` (approx) | KNN pre-sorted; approx error acceptable for perceptual ranking |
| Active filter cuts corpus | `_distExact` (exact) | Filter may bisect clusters; centroid table invalid for survivors |
| Same-cluster pair | `_dist3d` (exact match) | `centDist = 0`, only intra terms; exact within triangle bound |
| Very small corpus (<50 pts) | Either | Exact is fast enough; approx has no advantage |

---

## No-Repeat + Trail History

```javascript
// Shared state across both paths
let ppWalkPlayed = new Set();  // no-repeat tracking
let ppWalkTrail  = [];         // ordered play history for prev/next navigation
let ppWalkTrailPos = -1;       // current position in trail

// On exhaustion: reset and continue (don't stop)
if (unplayed.length === 0) {
  ppWalkPlayed.clear();
  ppWalkPlayed.add(curIdx);
  candidates = fullPool;
}

// Append to trail (truncate forward branch if user went back then forward)
if (ppWalkTrailPos < ppWalkTrail.length - 1) {
  ppWalkTrail = ppWalkTrail.slice(0, ppWalkTrailPos + 1);
}
ppWalkTrail.push(next);
if (ppWalkTrail.length > 100) ppWalkTrail.shift();  // cap memory
ppWalkTrailPos = ppWalkTrail.length - 1;
```

---

## Evidence

- Applied in `cluster_explorer_v6_3d.html` (music corpus, ~1045 songs, UMAP 3D coords, micro-cluster labels from KMeans)
- Two-path routing validated: filter-first path uses `_distExact` over filtered survivors; unfiltered path uses `_dist3d` (cluster-approx) with KNN pre-sort
- MMR formula from: Carbonell & Goldstein (1998) "The Use of MMR, Diversity-Based Reranking for Reordering Documents and Producing Summaries"
- Density walk temperature: adaptive median — scales with local neighborhood density
