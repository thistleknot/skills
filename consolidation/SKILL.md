---
name: consolidation
description: >
  Triplet-based document consolidation: derive pairwise correlation matrix from
  subject-predicate-object triplet overlap, run greedy nearest-neighbor chain
  decomposition to surface merge candidates and cross-reference opportunities,
  and emit sorted group reports for living knowledge bases and skill libraries.
  Embeddings are pre-computed lazily via async queue to decouple from consolidation runs.
status: active
last_validated: 2026-05-24
supersedes: []
validation_method: run against skills repo; verify groups are semantically coherent; verify embedding queue is async and non-blocking
---

# Consolidation Skill

## Purpose

As a knowledge base or skill library grows, documents drift: content duplicates across files, cross-references go stale, related concepts fragment into separate pages. Consolidation is the periodic process that detects these conditions and prescribes the correct action — merge, migrate, cross-reference, or keep separate.

This skill operationalises consolidation as a **data pipeline**, not a manual review. The output is a ranked group report the agent (or human) acts on directly.

---

## Trigger Conditions

Invoke when:

- The skill library has grown by ≥5 new entries since the last consolidation run
- A semantic search query returns contradictory results from multiple files
- A `skill-wiki` intake review flags possible duplication
- Scheduled: once per major release cycle or merge batch

---

## Idempotency Gate

**Do not run consolidation just because the user asked.** Check first:

```
prev_hashes = load_checkpoint(.checkpoint.db)
changed = skills_added ∪ skills_removed ∪ {s | hash(s) ≠ prev_hash(s)}

if len(changed) < 2:
    "Only N skill(s) changed (need ≥2). Skipping."
    exit
```

**Why ≥2?** A single changed skill only shifts the correlation scores for pairs involving that one skill. Unless that skill sits exactly on τ, the group structure won't change. Two changes guarantee at least one pair relationship could plausibly cross the τ boundary in either direction.

Override with `--force` when you need to re-run regardless (e.g., after changing τ itself or after a bulk import).

---

## Embedding Queue Separation

**Embeddings are NOT computed on-demand during consolidation runs.** Instead, they are pre-computed lazily as skills change via an async queue service (`embedding_queue_server.py`). This decouples embedding ingestion from the consolidation pipeline and prevents embeddings from going stale.

### Architecture

- **Skills change** → emit task to queue server (via git hook or file watcher)
- **Queue server** (fastapi, port 8000) → process tasks asynchronously; checkpoint to `.checkpoint.db`
- **Consolidation run** → cancel pending queue, batch-flush stale skills, continue with similarity matrix

### Before running consolidation

If you have the queue server running:
```bash
curl -X POST http://localhost:8000/queue/cancel-pending
```

This cancels pending tasks and lets consolidation submit them as a batch. If the queue server is not running, consolidation proceeds normally using the last-cached embeddings.

### See Also

- `embedding_queue_server.py` — fastapi service that owns the embedding queue checkpoint
- `AGENTS.md` — "Agentic Memory Embedding Queue Architecture" section in the skills repo root

---

## Executable

```
python consolidation/consolidate.py [--force] [--root PATH] [--obsidian [N]] [--graph]
```

Flags:
- `--force` — bypass idempotency check; always re-run
- `--root PATH` — override skills root directory
- `--obsidian [N]` — write `[[wikilinks]]` See Also sections in each SKILL.md; generate `_skill_graph.md` (default N=3 neighbors)
- `--graph` — run graph analysis after the main pipeline (community detection, k-means elbow, betweenness centrality, DWPC, spring layout); writes `graph_report.json` + `graph.png`

Standalone graph analysis (reads from existing checkpoint, does not re-derive):
```
python consolidation/graph_analysis.py [--db PATH] [--threshold TAU] [--out PATH] [--no-plot]
```

Checkpoint stored at `consolidation/.checkpoint.db` (SQLite). Content hashes keyed by skill name; `run_log` table records history.

---

## Protocol

### Step 1 — Extract triplets

For each document `d`, first strip structural boilerplate that inflates shared vocabulary across all files (YAML front matter, markdown section headers, table rows, code fences). Then extract from the remaining prose:

```
triplets(d) = { (subject, predicate, object) }
              extracted by the active LLM with the prompt:
              "List all factual claims in this text as (S, P, O) triples. One per line."
```

**Why strip boilerplate first**: skill files share structural vocabulary ("trigger conditions", "failure modes", "when to use") across every document. Including this inflates pairwise similarity uniformly, flattening the distribution and making τ-based separation unreliable. Strip before vectorising; only prose differentiates skills.

Cache triplets in a SQLite checkpoint keyed by `(doc_path, content_hash)`. Skip re-extraction on unchanged files.

### Step 2 — Build the correlation matrix

For each pair `(d_i, d_j)` compute a similarity score:

```
sim(i, j) = |triplets(d_i) ∩ triplets(d_j)| / |triplets(d_i) ∪ triplets(d_j)|
```

This is Jaccard similarity on the triplet sets. For large corpora where exact string match underestimates semantic overlap, substitute NLI-based soft Jaccard: a triplet `t_i` is considered to match `t_j` if `NLI_entailment(t_i, t_j) > θ` (θ ≈ 0.7).

Store the full N×N matrix as a SQLite table `similarity(doc_a TEXT, doc_b TEXT, score REAL)`.

### Step 3 — Greedy nearest-neighbor chain decomposition

**Invoke the `nearest-neighbor-chain` skill.** Full algorithm spec, pseudocode, and
failure modes live there. This step is a direct call to that sub-skill with the
similarity matrix `M` from Step 2 and **τ = 0.3** as the semantic floor.

Summary of what `nearest-neighbor-chain` does:
- Sorts all above-τ pairs by score descending
- Walks pairs greedily, extending chains only at their endpoints (no branching)
- Any doc not reachable above τ becomes a singleton
- Returns chains sorted by length descending

**τ = 0.3** is the semantic floor from the prescription table below — the minimum
xref-worthy overlap. Data-driven thresholds (elbow, largest-gap) are unstable for
small N with sparse similarity distributions; the prescription table already encodes
what "meaningful overlap" means.

Documents below τ become singletons — genuinely distinct topics requiring no
resolution. A large singleton count is expected and correct with TF-IDF surface
similarity; with NLI-based soft Jaccard on real triplets, chains grow longer but
singletons remain a meaningful signal.

### Step 4 — Classify within-chain relationships

For each consecutive pair `(d_i, d_{i+1})` in a chain:

| sim score | Prescription |
|---|---|
| ≥ 0.8 | **Merge candidate** — strong content overlap, consider collapsing into one file |
| 0.5 – 0.8 | **Migrate** — move the overlapping section from the lower-authority doc into the higher |
| 0.3 – 0.5 | **Cross-reference** — add `See also:` links in both directions |
| < 0.3 | Chain boundary — treat as separate topics (should not be chained if τ is set correctly) |

Between chains: if the highest between-chain pair exceeds 0.3, emit a cross-reference suggestion. No merge across chain boundaries.

### Step 5 — Emit the group report

Sort chains by length descending. For each chain, list documents with their within-chain similarity scores. Flag merge candidates in red, cross-reference candidates in yellow.

```
Group 1 (5 docs):
  agentic_kg_memory  ──0.72──  gist-retriever  ──0.61──  gist_correlation_matrix  ──0.55──  kg_ontology  ──0.48──  memory-architecture
  Prescriptions: agentic_kg_memory ↔ gist-retriever [migrate], gist_correlation_matrix ↔ kg_ontology [xref]

Group 2 (4 docs):
  ...
```

---

## Artifacts

| Artifact | Location | Contents |
|---|---|---|
| `triplets.db` | session checkpoint | doc → triplet cache |
| `similarity.db` | session checkpoint | N×N similarity scores |
| `consolidation_report.md` | output | sorted group report with prescriptions |
| `graph_report.json` | `consolidation/` | community labels, subgraph metrics, betweenness, DWPC pairs (--graph only) |
| `graph.png` | `consolidation/` | spring layout coloured by Louvain community (--graph only) |

---

## Graph Analysis Pipeline (`--graph`)

An optional second-pass analysis that operates on the embedding space rather than the Jaccard triplet space. The two views are complementary: NNC chains reflect surface-term overlap; the graph analysis reflects semantic proximity in embedding space.

### Pipeline

```
embeddings (from .checkpoint.db)
  ↓
cosine similarity matrix (unit-norm dot product)
  ↓  adaptive τ = 85th pct of pairwise cosines  (user-overridable via --threshold)
cosine graph  (networkx, weighted edges)
  ↓
WCC  →  enumerate disconnected islands / isolated skills
  ↓
Louvain community detection  →  partition + modularity score
  ↓  cross-validate
k-means (k=2..√N)  →  BSS/TSS elbow (argmin second derivative)  →  optimal k
  ↓
ARI(Louvain, k-means)  >0.7 high confidence | >0.3 surface both | else disagreement
  ↓
per-community subgraph metrics: density · conductance · LCC ratio
  ↓
betweenness centrality  →  bridge skill detection
  ↓
DWPC (k=1 direct, k=2 one-hop)  →  hub-corrected pair connectivity
  ↓
spring layout (Fruchterman–Reingold)  →  graph.png
  ↓
observer agent disposition prompt  →  per-community CONSOLIDATE | CROSS-REF | KEEP | INSPECT
```

### Threshold Notes

- **Jaccard τ = 0.3** (Step 3 NNC): semantic floor for the fusion score (Jaccard-dominated)
- **Graph τ = auto (85th pct)**: cosine similarities are uniformly higher than fusion scores, so a fixed 0.3 would produce a near-complete graph with trivial communities. The 85th-pct adaptive threshold yields ~10–15% edge density, which is the structurally informative regime. Pass `--threshold <value>` to override.

### Observer Agent Disposition Rubric

| Metric profile | Prescription |
|---|---|
| High density + low conductance | **CONSOLIDATE** — community is internally redundant |
| Moderate density, any conductance | **CROSS-REF** — related but distinct; add See Also |
| Low density or high conductance | **KEEP** — genuinely separate topics |
| High betweenness centrality | **INSPECT** — bridge/hub skill; may span multiple communities |

### BSS/TSS Elbow

BSS/TSS is monotonically non-decreasing with k; maximising it directly gives k=N.
The elbow is selected at the k with the most-negative second derivative (sharpest deceleration in marginal gain). Silhouette score is computed in parallel as a secondary criterion.

### DWPC vs Betweenness

- **Betweenness centrality**: O(N·E) via networkx; identifies nodes that lie on many shortest paths; most interpretable for bridge detection
- **DWPC (k=1, k=2)**: degree-weight normalises path counts to penalise hub-mediated connectivity; PC vs DWPC delta exposes hub bias in pairs; O(N³) for k=2 but tractable at N≤500

---

## Integration

- **`nearest-neighbor-chain`**: sub-skill called in Step 3; owns the chain decomposition algorithm, τ selection guidance, and failure modes
- **`agentic_kg_memory`**: source of triplet extraction prompt; triplets feed back into the KG as entity relationships
- **`gist_correlation_matrix`**: lower-level operator; `consolidation` calls the matrix builder and adds the chain-decomposition + prescription layer on top
- **`skill-wiki`**: consumes the merge/migrate prescriptions as governance actions (promote, supersede, cross-ref)
- **`skill-sync`**: handles the mechanical file-level merge once prescriptions are approved

---

## Failure Modes

| Failure | Cause | Fix |
|---|---|---|
| All docs in one chain | τ too low | Raise τ to elbow; rerun |
| All singletons | τ too high or triplet extraction sparse | Lower τ or improve extraction prompt |
| Merge candidate is false positive | Triplets share surface terms, not meaning | Switch to NLI-based soft Jaccard |
| Stale report | Docs changed since last run | Re-extract triplets for changed files only (content-hash check) |
<!-- consolidation:see-also:start -->
## See Also
[[code]]  [[openspec-archive-change]]  [[causal-inference]]
<!-- consolidation:see-also:end -->
