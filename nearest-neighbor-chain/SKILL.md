---
name: nearest-neighbor-chain
description: >
  Greedy nearest-neighbor chain decomposition: convert a pairwise similarity matrix
  into an ordered list of variable-length chains (semantic threads) by walking the
  sorted pair list and extending chains only at their endpoints. Use when you have a
  correlation matrix and need to partition a corpus into semantic groups for
  consolidation, cross-referencing, or topic segmentation.
status: active
last_validated: 2026-05-04
parent_skill: gist_correlation_matrix
---

# Nearest-Neighbor Chain Decomposition

## What This Is

A greedy **path-cover** algorithm over a pairwise similarity matrix. It walks pairs
sorted by descending score and builds variable-length chains by extending endpoints only
— no branching, no merging of two existing chains. The result is a **ragged list of
chains** where:

- each chain is a semantic thread (adjacent members are maximally similar)
- a chain break marks a topic boundary
- documents below threshold τ become singletons

The "chaining effect" that is normally criticized in single-linkage clustering is here
**used intentionally** — the chain IS the semantic thread. You want it to follow the
strongest connections before backtracking to start a new topic.

---

## Named Concept

This algorithm is a **path-cover variant of single-linkage clustering** with a hard
τ cutoff. The closest formal name in the literature is **greedy nearest-neighbor chain
decomposition** (distinct from the Ward linkage NNC algorithm — this is simpler and
non-merging).

---

## Algorithm

```
Input:
  M        — symmetric N×N similarity matrix (upper triangle used)
  τ        — minimum score threshold; pairs below this are not chained

Output:
  chains   — list of ordered doc-index lists, sorted by length descending
  singletons — docs not in any multi-doc chain

-- Enumerate and sort all above-threshold pairs descending
pairs = [(M[i,j], i, j) for i < j if M[i,j] >= tau], sorted descending

visited = {}      # doc_index -> chain_index
chains  = []

for (score, i, j) in pairs:
    if score < tau:
        break          # all remaining pairs are also below tau

    ci = visited.get(i)
    cj = visited.get(j)

    if ci is not None and cj is not None:
        continue       # both already chained; skip

    if ci is None and cj is None:
        # start a new chain
        chains.append([i, j])
        visited[i] = visited[j] = len(chains) - 1

    elif ci is None:
        # i is free; extend j's chain only if j is an endpoint
        if chains[cj][-1] == j:
            chains[cj].append(i)
            visited[i] = cj
        elif chains[cj][0] == j:
            chains[cj].insert(0, i)
            visited[i] = cj
        # else j is an interior node — skip (no branching)

    else:  # cj is None
        # j is free; extend i's chain only if i is an endpoint
        if chains[ci][-1] == i:
            chains[ci].append(j)
            visited[j] = ci
        elif chains[ci][0] == i:
            chains[ci].insert(0, j)
            visited[j] = ci
        # else i is an interior node — skip (no branching)

# anything not visited becomes a singleton
for d not in visited:
    chains.append([d])

chains_sorted = sorted(chains, key=len, reverse=True)
```

---

## Key Properties

| Property | Value |
|---|---|
| Complexity | O(N² log N) to sort pairs; O(N²) to walk |
| Branching | None — only chain endpoints can be extended |
| Chain merging | None — two existing chains never join |
| Below-τ handling | Singletons; the `break` is O(1) because pairs are sorted |
| Order sensitivity | None — result is deterministic for a given sorted pair list |
| Multi-hop | Natural — chains extend greedily through the best available pair |

---

## Threshold τ Selection

τ controls what counts as a meaningful connection. Three strategies:

| Strategy | When to use |
|---|---|
| **Semantic floor** (recommended) | Use the minimum score your prescription table defines as actionable (e.g., 0.30 for xref). Stable, principled, domain-grounded. |
| **2nd-derivative elbow** | `τ = scores[argmin(diff(diff(sorted_scores))) + 2]`. Noisy for small N (<100) with sparse distributions. |
| **Largest-gap on top 20%** | Find the biggest drop in the top quintile of scores. Too aggressive for moderate N — often gives only 1–2 groups. |

For most knowledge-base and skill-library corpora, use the **semantic floor** (τ = 0.30
for TF-IDF cosine; higher for NLI-based scores). Data-driven thresholds are unstable at
small N.

---

## Prescription Mapping

When used for document consolidation, consecutive pairs in a chain receive prescriptions
based on their similarity score:

| Score range | Prescription |
|---|---|
| ≥ 0.80 | **MERGE** — strong overlap; collapse into one file |
| 0.50 – 0.80 | **migrate** — move overlapping section to the higher-authority doc |
| 0.30 – 0.50 | **xref** — add bidirectional See Also links |
| < τ | Chain boundary — separate topics; no action |

---

## Output Format

Sort chains by length descending. Emit each chain as an ordered sequence with
consecutive scores and prescriptions. Singletons follow.

```
Group 1 (4 docs):
  doc_a  --0.72 [migrate]-->  doc_b  --0.55 [xref]-->  doc_c  --0.31 [xref]-->  doc_d

Group 2 (2 docs):
  doc_e  --0.61 [migrate]-->  doc_f

Singletons (N): doc_g  doc_h  doc_i  ...
```

---

## Use Cases

| Use case | Notes |
|---|---|
| Document consolidation (`consolidation`) | Primary consumer; adds triplet Jaccard matrix builder and MERGE/migrate/xref prescriptions |
| Semantic topic segmentation | Any corpus with a precomputed similarity matrix |
| Knowledge graph partitioning | Group nodes by structural similarity before entity resolution |
| Obsidian [[wikilink]] generation | Chains define which pages should cross-reference each other |
| Skill library grouping | Used by `consolidation` over SKILL.md files |

---

## Integration

- **`gist_correlation_matrix`** — builds the raw similarity matrix this skill consumes;
  `nearest-neighbor-chain` is the decomposition layer that sits on top
- **`consolidation`** — the primary consumer; wraps this algorithm with triplet
  extraction, idempotency gate, and MERGE/migrate/xref prescription output
- **`siamese_from_correlation_matrix`** — alternative consumer: uses correlation
  structure to derive metric-learning pairs rather than chains

---

## Failure Modes

| Failure | Cause | Fix |
|---|---|---|
| All docs in one chain | τ too low | Raise τ; semantic floor is usually the right anchor |
| All singletons | τ too high or similarity matrix too sparse | Lower τ; check that boilerplate was stripped before vectorizing |
| Long chains with low-score tail hops | Chain extends through pairs near τ | Raise τ slightly; or add a max-chain-length cap |
| Inconsistent groups across runs | Tie-breaking in sort order | Use a stable sort; add a secondary sort on `(i, j)` index for determinism |
