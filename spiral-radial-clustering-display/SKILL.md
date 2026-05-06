---
name: spiral-radial-clustering-display
description: >
  Multi-dimensional spiral radial clustering visualization with hierarchical layer encoding.
  Maps decorrelated ordering and centrality metrics into 2D space via UMAP while preserving
  topological structure. Produces interactive Gestalt-encoded visualizations with position
  (spiral), color (macro-cluster), opacity (micro-cluster agreement), and size (hub centrality).
parent_skill: representation-pipeline
status: active
last_validated: 2026-04-28
---

# Spiral-Radial Clustering Display

## When to use

Use this skill when you need to visualize multi-layered clustering structure where:

- **Layer 1 (macro)**: Coarse categorical clustering (e.g., GMM genres, 8-16 clusters)
- **Layer 2 (micro)**: Fine-grained clustering (e.g., HDBSCAN, 50-200 clusters)
- **Layer 3 (ordering)**: Decorrelated sequence that defines radial/angular arrangement (e.g., sorted correlation matrix, greedy selection order)
- **Layer 4 (centrality)**: Hub/peripheral metric (e.g., correlation hubness, closeness, degree)

And where:
- Visual separation is critical (Gestalt grouping by hue/opacity)
- Spiral topology is meaningful (inner = central, outer = peripheral, angle = decorrelated ordering)
- Zoom/pan interactivity is required for exploration
- Hover metadata should show all layer memberships

Do NOT use it for:
- Single-layer clustering (use standard t-SNE/UMAP)
- Non-hierarchical data (use force-directed graphs directly)
- Cases where topological structure is noise, not signal

---

## Architecture

### Input Requirements

```python
# Required vectors/arrays:
features: ndarray (n_songs, n_features)           # raw feature space
gmm_labels: ndarray (n_songs,)                    # macro clusters: 0 to K_macro-1
hdbscan_labels: ndarray (n_songs,)                # micro clusters: 0 to K_micro-1 (or -1 for noise)
sorted_indices: ndarray (n_songs,)                # decorrelated ordering (e.g., greedy selection index sequence)
```

### 3D Feature Construction

Map four dimensions into 3D space that UMAP will project to 2D:

| Dimension | Name | Semantics | Range | Encoding in 2D |
|-----------|------|-----------|-------|---|
| Dim 1 | Macro Cluster ID | Genre/macro-structure | [0, K_macro) | **Color** |
| Dim 2 | Radial Distance | Distance to nearest macro centroid | [0, max_dist] | **Position radius** (via UMAP) |
| Dim 3 | Angular Position | Position in decorrelated ordering | [0, 2π] | **Position angle** (via UMAP) |
| *Output* | Hubness | Centrality in decorrelated sequence | [0, 1] | **Size** |

**Construction steps:**

```python
import numpy as np
from scipy.spatial.distance import cdist
from sklearn.preprocessing import StandardScaler

# Step 1: Compute GMM centroids
gmm_centers = np.array([
    features[gmm_labels == k].mean(axis=0) 
    for k in range(K_macro)
])

# Step 2: Build 3D feature space
dim1 = gmm_labels.astype(np.float32)  # Macro cluster ID (0-7)

distances = cdist(features, gmm_centers, metric='euclidean')
dim2 = distances.min(axis=1).astype(np.float32)  # Distance to nearest centroid

# Map sorted position to angle: first song → angle 0, last → 2π
sorted_position = np.argsort(np.argsort(sorted_indices))  # Invert to get position-in-order
dim3 = (2 * np.pi * sorted_position / len(sorted_position)).astype(np.float32)

features_3d = np.column_stack([dim1, dim2, dim3])

# Step 3: Standardize for UMAP (critical for metric='euclidean')
scaler = StandardScaler()
features_3d_scaled = scaler.fit_transform(features_3d)
```

### UMAP Projection

Project 3D → 2D, preserving local neighborhood structure (spiral topology):

```python
import umap

mapper = umap.UMAP(
    n_components=2,
    n_neighbors=15,        # balance: 15-20 for 1000+ points
    min_dist=0.1,          # allow some separation
    metric='euclidean',    # use standardized 3D Euclidean space
    random_state=42        # reproducibility
)
coords_2d = mapper.fit_transform(features_3d_scaled)
```

**Why this works:**
- UMAP preserves **neighborhood structure**: songs close in 3D (similar GMM, radius, angle) stay close in 2D
- Spiral topology **emerges naturally** from dim2 (radius) and dim3 (angle) structure
- No explicit polar coordinate transformation needed—UMAP encodes it implicitly

### Visual Encoding (Gestalt)

**Position** (via UMAP 2D coords)
- Macro clusters (GMM) occupy separate spatial regions
- Micro clusters (HDBSCAN) appear as sub-regions within each macro region
- Angle/radius structure creates spiral appearance within each macro region

**Color** (via GMM layer)
- 8 distinct, saturated colors (one per macro cluster)
- Gestalt principle: color similarity → semantic grouping
- Example palette: `['red', 'blue', 'green', 'orange', 'purple', 'cyan', 'magenta', 'yellow']`

**Opacity** (via HDBSCAN layer)
- Noise points (HDBSCAN label == -1): opacity 0.3 (faint, boundary)
- Cluster core (HDBSCAN label >= 0): opacity 0.8 (clear, confident)
- Gestalt principle: opacity → certainty/salience

**Size** (via hubness/centrality)
- Songs early in decorrelated ordering → larger
- Songs late in ordering → smaller
- Range: 5-15 pt diameter (avoid extremes)
- Formula: `size = 5 + 10 * (1.0 - sorted_position / n_songs)`
- Gestalt principle: size → importance/centrality

---

## Implementation Walkthrough

### Phase 1: Load and Preprocess

```python
import sqlite3
import numpy as np
from pathlib import Path

# Load features from database
conn = sqlite3.connect("music_features.db")
cursor = conn.cursor()
cursor.execute("SELECT path, vector FROM features ORDER BY path")
rows = cursor.fetchall()
paths = [r[0] for r in rows]
features = np.array([np.frombuffer(r[1]) for r in rows], dtype=np.float32)
conn.close()

# Handle overflow/NaN
features = np.nan_to_num(features, nan=0.0, posinf=1.0, neginf=-1.0)

# Load clustering and ordering
gmm_labels = np.load("gmm_labels.npy")
hdbscan_labels = np.load("hdbscan_labels.npy")
sorted_indices = np.load("correlation_sorted_indices.npy")  # or your ordering
```

### Phase 2: Construct 3D Space

```python
from scipy.spatial.distance import cdist

# Normalize features for stability
features_norm = features / (np.linalg.norm(features, axis=1, keepdims=True) + 1e-8)

# Compute GMM centers
gmm_centers = np.array([
    features_norm[gmm_labels == k].mean(axis=0)
    for k in range(8)
])

# Build 3D features
dim1 = gmm_labels.astype(np.float32)
distances = cdist(features_norm, gmm_centers, metric='euclidean')
dim2 = distances.min(axis=1).astype(np.float32)

sorted_position = np.zeros(len(sorted_indices), dtype=np.int32)
for pos, idx in enumerate(sorted_indices):
    sorted_position[idx] = pos
dim3 = (2 * np.pi * sorted_position / len(sorted_position)).astype(np.float32)

features_3d = np.column_stack([dim1, dim2, dim3])
```

### Phase 3: Standardize and Project

```python
from sklearn.preprocessing import StandardScaler
import umap

scaler = StandardScaler()
features_3d_scaled = scaler.fit_transform(features_3d)

mapper = umap.UMAP(n_neighbors=15, min_dist=0.1, n_components=2, random_state=42)
coords_2d = mapper.fit_transform(features_3d_scaled)
```

### Phase 4: Render with Plotly

```python
import plotly.graph_objects as go

fig = go.Figure()

# Colors for each GMM cluster
colors = ['red', 'blue', 'green', 'orange', 'purple', 'cyan', 'magenta', 'yellow']

# Plot each GMM cluster
for gmm_id in range(8):
    mask = gmm_labels == gmm_id
    indices = np.where(mask)[0]
    
    opacity = np.where(hdbscan_labels[mask] >= 0, 0.8, 0.3)
    sizes = 5 + 10 * (1.0 - sorted_position[mask] / len(sorted_position))
    
    fig.add_trace(go.Scatter(
        x=coords_2d[mask, 0],
        y=coords_2d[mask, 1],
        mode='markers',
        name=f"Genre {gmm_id}",
        marker=dict(
            size=sizes,
            color=colors[gmm_id],
            opacity=opacity,
            line=dict(width=0.5, color='rgba(0,0,0,0.2)')
        ),
        text=[
            f"<b>{Path(paths[i]).stem}</b><br>" +
            f"GMM: {gmm_labels[i]}<br>" +
            f"HDBSCAN: {hdbscan_labels[i]}<br>" +
            f"Rank: {sorted_position[i]}/{len(sorted_position)}"
            for i in indices
        ],
        hoverinfo='text',
    ))

fig.update_layout(
    title="Spiral-Radial Clustering",
    xaxis=dict(showgrid=False, zeroline=False),
    yaxis=dict(showgrid=False, zeroline=False),
    width=1400, height=900,
    plot_bgcolor='rgba(20,20,30,1)',
    font=dict(color='white'),
    hovermode='closest',
)

fig.write_html("clustering_visualization.html")
```

---

## Key Decisions

### 1. Why UMAP and not t-SNE?

**UMAP preserves global structure** better than t-SNE. Since we baked spiral topology into the 3D input, we want UMAP to respect that. t-SNE would "crumple" the spiral.

### 2. Why standardize the 3D features?

**Scales matter differently**: GMM ID is 0-7 (tiny), radius is 0-5000 (huge), angle is 0-2π. Standardization puts them on equal footing so UMAP can balance their contribution.

### 3. How many neighbors for UMAP?

- **1000 points**: `n_neighbors=15` (local detail)
- **10000 points**: `n_neighbors=30` (more global)
- Start at 15, increase if you see disconnected clusters.

### 4. When to tune `min_dist`?

- `min_dist=0.01`: very tight clustering (risk of clumping)
- `min_dist=0.1`: moderate separation (default, good for this use case)
- `min_dist=0.5`: very loose clustering (risk of scatter)

---

## Failure Modes & Fixes

| Symptom | Cause | Fix |
|---------|-------|-----|
| Single blob, no separation | UMAP params too loose, or features don't cluster well | Reduce `min_dist` to 0.05, increase `n_neighbors` to 20 |
| All points in one color | GMM didn't fit, or only 1 cluster | Re-run GMM with `n_components=8`, check feature scaling |
| No spiral visible | Sorted ordering doesn't encode meaningful structure | Verify `sorted_indices` is from decorrelated selection (not random) |
| Some colors invisible | Colors too similar or opacity washes them out | Use more saturated palette, adjust opacity range [0.3, 0.9] |
| UMAP hangs on 1000+ points | n_neighbors too large + slow metric | Use `n_neighbors=15`, metric='euclidean', `random_state=42` |
| Hover shows NaN | Path parsing error or missing metadata | Ensure all indices map correctly; use `Path(path).stem` for names |

---

## Interpretation Guide

**What you should see:**

1. **8 distinct color regions** (one per GMM cluster), spatially separated
2. **Sub-regions within each color** (HDBSCAN micro-clusters), either as tight sub-clusters or opacity gradients
3. **Spiral pattern within each region**: central (larger, opaque) → outer (smaller, fader)
4. **Smooth gradation**: no sharp discontinuities (sign of bad ordering or clustering)

**What the layers tell you:**

- **Position**: overall neighborhood (which songs are similar across all three dimensions)
- **Color**: macro-genre (which flavor family)
- **Opacity**: confidence (core members vs boundary members of that genre)
- **Size**: hub importance (if you remove this song, how many others lose a connection?)

**Zooming in:**

Each color region, when zoomed to 10-20% view, should show distinct spiral arms or rings. This is HDBSCAN sub-clusters arranged radially by their decorrelated rank.

---

## Advanced Tuning

### Hybrid Scoring (Optional)

If you want to combine multiple centrality metrics before encoding as size:

```python
# Option: blend centrality metrics
degree = (corr > threshold).sum(axis=1)  # Hub count
betweenness = ...  # if you have networkx
closeness = ...

# Normalize and blend
centrality = 0.6 * (degree / degree.max()) + 0.4 * (closeness / closeness.max())
sizes = 5 + 10 * centrality
```

### Interactive Annotations

Add click-to-expand or hover-to-play-audio:

```python
# In Plotly, use customdata to embed URL or metadata
fig.add_trace(go.Scatter(
    ...
    customdata=urls,  # YouTube URL, audio file path, etc.
    hovertemplate="<b>%{text}</b><br>URL: %{customdata}<extra></extra>"
))
```

### 3D Rendering (Optional)

If you want full 3D (don't project, visualize directly):

```python
fig = go.Figure(data=[go.Scatter3d(
    x=features_3d_scaled[:, 0],
    y=features_3d_scaled[:, 1],
    z=features_3d_scaled[:, 2],
    mode='markers',
    marker=dict(color=gmm_labels, colorscale='Viridis', size=5)
)])
fig.show()
```

---

## References

- **Gestalt Principles**: Proximity, similarity, closure, continuity (applied via position, color, opacity, size)
- **UMAP Papers**: McInnes et al., "UMAP: Uniform Manifold Approximation and Projection for Dimension Reduction"
- **Spiral Topology**: Decorrelated ordering (from greedy selection) as natural angular coordinate in hierarchical clustering
- **Plotly Interactivity**: Hover metadata, zoom, pan all native; no custom JS needed

---

## Next Steps

1. **Caching**: Save UMAP mapper to disk (pickle) so reruns don't recompute
2. **Batch Processing**: Extend to N separate clustering problems (e.g., per-user playlists)
3. **Comparison View**: Side-by-side of old vs new clustering (or different GMM/HDBSCAN seeds)
4. **Export**: Save coords + clustering to CSV for downstream analysis
<!-- consolidation:see-also:start -->
## See Also
[[siamese_from_correlation_matrix]]  [[gist_correlation_matrix]]  [[cluster-quantized-knn]]  [[representation-pipeline]]  [[agentic_kg_memory]]
<!-- consolidation:see-also:end -->
