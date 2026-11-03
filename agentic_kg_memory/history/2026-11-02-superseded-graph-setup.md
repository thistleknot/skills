# Superseded graph setup sketch

SUPERSEDED 2026-11-02. Preserved from the skill as historical design material after confirming that the active memory-index MCP already owns scoped SQLite storage and dense retrieval is optional. Do not execute these steps; current setup boundary is in `../SKILL.md`.

## Setup Mode

If the user invokes **`agentic_kg_memory setup`**, treat that as a storage and
retrieval installation request.

### Required paths

Use these explicit paths on this machine:

- `C:\Users\user\memory-bank\wiki_memory.sqlite3`
- `C:\Users\user\memory-bank\.chroma\`  (served by the `mem-chroma` service, `127.0.0.1:8055`)
- `C:\Users\user\memory-bank\clusters.json`
- `C:\Users\user\memory-bank\cluster_metrics.json`

The SQLite file is the sparse/metadata surface.
The Chroma directory is the dense embedding surface — connect via the `mem-chroma`
`HttpClient` (do not open a second `PersistentClient` on `.chroma`; the service owns it).
KG triplet sequences use collection `memory-bank-triplet-sequences`, distinct from the
`memories` recall log in the same server.

> **Scope tags**: each wiki page should carry a `scope` field — `global` or `repo`.
> Global pages belong in `C:\Users\user\memory-bank\`. Repo-specific pages belong
> in `[repo-root]\.memory-bank\`. The SQLite and Chroma backends are partitioned
> the same way: one global instance, one per active repo (started with `--memory-dir`
> on the MCP server).

### Setup actions

When running setup, do all of the following:

1. Create `C:\Users\user\memory-bank\wiki_memory.sqlite3`
2. Create or migrate the page table:
   - `bm25_text`
   - `triplet_sequence_text`
   - `embedding_ref`
   - `cluster_id`
3. Create the graph tables: `kg_nodes`, `kg_edges` (with indexes on `dst_slug` and `edge_type`)
4. Ensure `C:\Users\user\memory-bank\.chroma\` exists as the Chroma persist directory (the `mem-chroma` service owns it)
5. Build `triplet_sequence_text` from canonicalized extracted triplets in source order
6. Embed `triplet_sequence_text` and store vectors in Chroma
7. Cluster the normalized dense vectors
8. Write the winning `cluster_id` back into SQLite
9. Persist human-readable cluster outputs to:
   - `C:\Users\user\memory-bank\clusters.json`
   - `C:\Users\user\memory-bank\cluster_metrics.json`

### Evaluation outputs

The setup step is not complete until it persists:

- cluster count
- clustering method
- normalization method
- `bss`
- `tss`
- `bss_tss_ratio`

If the system has only the design and no fitted clustering run yet, say so plainly.

