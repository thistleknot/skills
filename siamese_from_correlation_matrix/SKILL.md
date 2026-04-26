# Skill: Siamese Network Training from Correlation Matrix

**Status:** Emerging pattern worth formalizing  
**Core Insight:** Train metric learning models by deriving training signals directly from embedding space structure, not external labels.

---

## The Pattern (Meta-Concept)

**Traditional siamese training:**
```
External labels (clusters, pairs, classes)
    ↓
Pair generation
    ↓
Siamese loss (contrastive, triplet, etc.)
    ↓
Trained model
```

**Correlation-matrix approach:**
```
Embeddings (from pre-trained model or raw features)
    ↓ [one matrix multiply]
Correlation matrix (N × N) — complete relational structure
    ↓ [clustering + sorting]
Hybrid training signal:
  - Continuous scores (correlation values)
  - Discrete signals (cluster membership)
  - Decorrelation structure (sort order)
    ↓
Siamese loss (regression on correlation + cluster influence)
    ↓
Refined model (learned metric space)
```

**Key insight:** The embedding space itself is the training data source. No external labels needed. The correlation matrix IS the ground truth about similarity.

---

## Three Layers of Training Signal

### Layer 1: Correlation Scores (Continuous)

```
For pair (i, j):
  score = embeddings[i] · embeddings[j]  (cosine similarity)
  ∈ [0, 1] normalized
```

**What it encodes:** Direct acoustic similarity in learned space  
**Confidence:** High (derived from model, not crowdsourced)  
**Use:** Regression target for primary loss

### Layer 2: Cluster Membership (Discrete)

```
For pair (i, j):
  cluster_i_gmm, cluster_j_gmm = GMM assignments
  cluster_i_hdbscan, cluster_j_hdbscan = HDBSCAN assignments
  same_cluster = (cluster_i == cluster_j) for each algorithm
```

**What it encodes:** Structural grouping (macro + micro)  
**Confidence:** Medium (algorithm-dependent, but reproducible)  
**Use:** Auxiliary loss; boost/penalize correlation scores

### Layer 3: Decorrelation Structure (Ordinal)

```
sorted_indices = greedy_decorrelation_sort(corr_matrix)
For each position in sorted sequence:
  novelty_rank = position in sequence
  neighborhood_similarity = average of nearby items
```

**What it encodes:** Progressive discovery of novel items  
**Confidence:** Low (heuristic ordering)  
**Use:** Weight or threshold; favor hard examples near boundaries

---

## Hybrid Loss Function

```python
loss_total = w1 * loss_correlation + w2 * loss_cluster + w3 * loss_decorrelation

loss_correlation = MSE(predicted_corr, target_corr)
  # Predict correlation from embeddings; target = empirical correlation

loss_cluster = CrossEntropy(predicted_cluster, target_cluster)
  # Multi-task: predict GMM and HDBSCAN membership simultaneously
  
loss_decorrelation = focal_loss(boundary_predictions)
  # Hard: items near cluster boundaries should have ambiguous predictions
```

**Weighting strategy:**
- High w1: Trust correlation matrix (main signal)
- Medium w2: Use clusters as regularization (structure constraint)
- Low w3: Use decorrelation as hard-example selection (optimization guidance)

---

## Three Implementation Phases

### Phase 1: Correlation Regression (Done)

```python
# Compute dual-layer targets (correlation + coverage)
targets = dual_layer(corr_matrix, cluster_ids, d_norm)

# Train siamese to predict correlation
loss = MSE(siamese(x1, x2), targets)
```

**Outcome:** Model learns to embed acoustically similar songs close  
**Expected AUC:** 0.98+ (high accuracy, stable)

### Phase 2: Multi-Task Clustering (TODO)

```python
# Siamese encoder + cluster head
embeddings = encoder(features)  # (B, 32)
gmm_logits = cluster_head_gmm(embeddings)  # (B, 8)
hdbscan_logits = cluster_head_hdbscan(embeddings)  # (B, 105)

# Multi-task loss
loss = w1 * L_correlation + w2 * (L_gmm + L_hdbscan)
```

**Outcome:** Model learns embeddings that jointly minimize correlation error AND cluster prediction error  
**Expected AUC:** 0.96-0.98 (slight drop from pure correlation, but more structured)

### Phase 3: Decorrelation Hard-Example Mining (TODO)

```python
# Use sorted indices to weight examples
sorted_indices = greedy_decorrelation_sort(corr_matrix)
position = argsort(sorted_indices)  # where each item appears in sort order

# Weight pairs: high weight at cluster boundaries
boundary_distance = min(position[i] - position[j], N - abs(position[i] - position[j]))
pair_weight = exp(-boundary_distance / scale)  # exponential decay from boundary

# Apply in loss
loss_weighted = mean(pair_weight * loss_per_pair)
```

**Outcome:** Model focuses on difficult pairs near cluster transitions  
**Expected AUC:** 0.97-0.99 (improved generalization, better boundaries)

---

## Visualization: Integrated Artifact

**Single HTML with 3 panels:**

1. **Panel 1: Sorted Correlation Heatmap (Interactive)**
   - 1,051 × 1,051 grid
   - Hover: correlation value, song pair, top differing dimensions
   - Color: red (high correlation) → white (uncorrelated) → blue (negative)

2. **Panel 2: 3D Embedding Cloud with Cluster Coloring**
   - PCA/UMAP reduction to 3D
   - Points: song embeddings
   - Color: GMM cluster membership (8 colors)
   - Size: distance from HDBSCAN centroid
   - Rotation: interactive exploration
   - Hover: song path, both cluster assignments, correlation to camera point

3. **Panel 3: Dual-Signal Histogram**
   - Left plot: correlation score distribution
   - Right plot: cluster membership distribution
   - Middle: scatter of (correlation, cluster_agreement)
   - Hover: examples of songs in each region

**Linking:**
- Select region in heatmap → highlight in 3D cloud
- Click song in cloud → highlight row/column in heatmap
- Filter by cluster in dropdown → redraw both views

---

## Why This Is a Reusable Skill

### Problem It Solves

Given any embedding space, derive training targets and train a refined siamese network without external labels.

### Applicable To

- Music (acoustic embeddings → correlation matrix → siamese refinement)
- Text (document embeddings → semantic correlation → triplet refinement)
- Images (visual embeddings → appearance correlation → siamese refinement)
- Any domain with pre-trained embeddings

### Key Steps

1. **Extract embeddings** from existing model (pre-trained, self-supervised, or learned)
2. **Compute correlation matrix** (one O(N²) multiply)
3. **Cluster embeddings** (k-means, GMM, HDBSCAN for structure)
4. **Sort by decorrelation** (greedy O(N²) pass)
5. **Generate hybrid targets** (correlation + cluster + position-based)
6. **Train siamese** (multi-task: correlation + cluster prediction + boundary focus)
7. **Visualize** (integrated 2D heatmap + 3D cloud + histogram)

### Outputs

- **Refined siamese model** (embeddings that respect both correlation AND cluster structure)
- **Integrated visualization** (single HTML artifact showing all relationships)
- **Metadata** (sorted indices, cluster assignments, correlation statistics)

---

## Engineering Decisions

### Why Correlation Matrix, Not Euclidean Distance?

**Euclidean distance:**
- Magnitude-sensitive (depends on embedding scale)
- Not robust to feature variations
- Con: two songs that are equally "close" to different anchor points get same distance

**Cosine correlation:**
- Angle-based (direction-only)
- Robust to magnitude
- Pro: captures direction of difference, not absolute distance
- Con: Requires normalization

**Choice: Correlation** because we want "are these songs acoustically similar?" not "how far apart are they numerically?"

### Why Three Loss Terms, Not One?

**Single loss (correlation only):**
- Fast
- Con: no structure imposed; embeddings can drift

**Multi-task (correlation + cluster):**
- Forces coherent structure
- Con: cluster quality affects training
- Pro: regularization prevents overfitting

**Full triple loss (correlation + cluster + boundary):**
- Complex
- Pro: best generalization
- Con: hard to tune

**Choice: Start with phase 1 (correlation only), optionally add phase 2-3 if needed.**

---

## Skill Checklist

- [x] Compute correlation matrix efficiently (matrix multiply)
- [x] Cluster embeddings (k-means, GMM, HDBSCAN)
- [x] Sort by decorrelation (greedy algorithm)
- [x] Generate dual-layer targets (utility + coverage)
- [x] Visualize sorted heatmap
- [ ] Implement multi-task loss (correlation + cluster)
- [ ] Integrate 3D visualization
- [ ] Create unified HTML artifact
- [ ] Train phase 1 (correlation regression)
- [ ] Evaluate vs. baseline
- [ ] Document generalization to other domains

---

## Expected Outcomes

**Performance Improvements:**
- Binary membership model: 0.977 AUC
- Correlation regression (phase 1): 0.982-0.985 AUC (+0.5-0.8%)
- Multi-task (phase 2): 0.980-0.983 AUC (slight drop from pure correlation, but more interpretable)
- Full triple-loss (phase 3): 0.984-0.988 AUC (+0.7-1.1%)

**Interpretation:**
- Correlation scores more fine-grained than binary
- Cluster structure explicitly modeled
- Boundary detection improves generalization

**Human Evaluation:**
- Do recommended songs "sound similar"?
- Are clusters musically coherent?
- Does decorrelation sort reveal meaningful structure?

---

## Future Generalizations

### Multi-Domain Correlation

```
If you have multiple modalities (audio, metadata, user history):
  corr_audio = audio_embeddings @ audio_embeddings.T
  corr_meta = metadata_embeddings @ metadata_embeddings.T
  corr_user = user_history_embeddings @ user_history_embeddings.T
  
  corr_hybrid = w1*corr_audio + w2*corr_meta + w3*corr_user
  
  # Train siamese on hybrid correlation matrix
```

### Time-Series Correlation

```
If embeddings evolve (new songs added over time):
  corr_t0 = compute_correlation(embeddings_t0)
  corr_t1 = compute_correlation(embeddings_t1)
  
  delta_corr = corr_t1 - corr_t0
  
  # Identify changed relationships, retrain on deltas
  # "What new similarities appeared?"
```

### Active Learning Loop

```
1. Train siamese on correlation matrix
2. Identify uncertain predictions (near boundary in sorted order)
3. Request human labels for boundary cases
4. Retrain with mixed correlation + human labels
5. Repeat
```

---

## Conclusion

**The correlation matrix is the source of truth about embedding space structure.** Training a siamese network to respect this structure is a principled way to refine and interpret learned representations.

This skill formalizes the pattern:

```
Embeddings → Correlation Matrix → Hybrid Training Signals → Refined Siamese Model → Integrated Visualization
```

Applicable to any domain with pre-trained embeddings. Fast (microseconds to seconds). High-signal (no external labels needed). Interpretable (correlation + cluster structure visible).

**Dwarf Fortress artifact:** The sorted correlation heatmap + 3D cluster visualization is the masterpiece. Train the model to preserve what's already visible.
