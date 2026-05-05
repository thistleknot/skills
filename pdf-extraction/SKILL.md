---
name: pdf-extraction
description: >
  Full 6-phase PDF → enriched Markdown pipeline. Use when converting any PDF
  into a structured document with VLM image descriptions, enhanced tables, and
  extracted pseudocode methods. Entrypoint: run_pipeline.bat. MCP interface:
  pipeline_mcp.py on port 9003. Calls class-balancing skill for table layout
  classifier training.
status: active
last_validated: 2026-05-02
depends_on:
  - class-balancing   # Box-Cox weights for layout classifier
  - auto-ingest       # arxiv corpus variant of this pipeline
---

# PDF Extraction Skill

## Scope Boundary

This skill owns the **general-purpose PDF→enriched Markdown pipeline**.

It owns:
- `run_pipeline.bat` — single entrypoint; pass any `.pdf` or `.md`
- `post_process_md-csv.py` — Phase 2: base64 strip, `<image_NNN>` tokens, CSV
- `vlm_describe.py` — Phase 3: Ollama VLM describes each image
- `reinsert_descriptions.py` — Phase 4: inserts descriptions back into MD
- `enhance_tables.py` — Phase 1.5: tabula+camelot+VLM table fusion
- `extract_methods.py` — Phase 5: strips references, extracts pseudocode via gpt-4.1
- `train_layout_classifier.py` — trains EfficientNet-B0 to classify layout regions
- `~/.copilot/pipeline_mcp.py` — MCP server for agent-callable conversion

It does **not** own:
- The arxiv corpus ingest queue → see `auto-ingest` skill
- pgvector embedding and retrieval → see retrieval pipeline
- The copilot-proxy endpoint (external infrastructure)

The `auto-ingest` skill is the arxiv-specific variant of this pipeline. Both share
the same Phase 2-5 scripts but `auto-ingest` is queue-driven (daemon + SQLite),
while this skill is on-demand (bat + MCP call).

---

## Pipeline Phases

| Phase | Script | Input → Output | Typical time |
|-------|--------|----------------|-------------|
| 1 | `docling` (external CLI) | `.pdf` → `.md` + `.json` (base64 images, layout JSON) | 30-100 s |
| 1.5 | `enhance_tables.py` | `.pdf`+`.md`+`.json` → `.md` (VLM-fused tables) | 0 s if no tables, ~30 s/table otherwise |
| 2 | `post_process_md-csv.py` | `.md` → `.md` (tokens) + `.csv` (base64 store) | 2-5 s |
| 3 | `vlm_describe.py` | `.csv` → `.csv` + `description` column via Ollama | 1-5 min |
| 4 | `reinsert_descriptions.py` | `.md` + `.csv` → `.md` (descriptions embedded) | 2-5 s |
| 5 | `extract_methods.py` | `.md` → `_methods.md` via gpt-4.1 copilot-proxy | 20-60 s |

**Completion signal**: `{stem}_methods.md` exists alongside the input PDF.

---

## Invocation

### Direct (CLI)
```bat
run_pipeline.bat "C:\path\to\paper.pdf"
run_pipeline.bat "C:\path\to\already_extracted.md"
```

Output lands **beside the input file** (same directory, same stem).

### Via MCP (agents / deep-research)

The `pdf-pipeline` MCP server exposes four tools:

| Tool | Purpose |
|------|---------|
| `convert_pdf(pdf_path, wait=False)` | Launch pipeline; optionally block until done |
| `pipeline_status(pdf_path)` | Return phase completion state for a PDF |
| `get_methods(pdf_path)` | Return `_methods.md` content when done |
| `list_jobs(directory)` | Scan directory for converted / pending PDFs |

```python
# deep-research integration pattern:
result = convert_pdf("C:/path/paper.pdf", wait=True)
methods = get_methods("C:/path/paper.pdf")
```

---

## Infrastructure Constraints (Windows-specific)

| Component | Location | Notes |
|-----------|----------|-------|
| Python | `C:\Users\user\py310\Scripts\python.exe` | conda env |
| Pipeline bat | `C:\Users\user\arxiv_id_lists\run_pipeline.bat` | Windows only |
| Ollama (VLM) | `http://192.168.3.17:11434` | homelab, `qwen3-vl:2b` |
| copilot-proxy | `http://localhost:8069` | gpt-4.1 text only — strips images |
| MCP server | `~/.copilot/pipeline_mcp.py` port 9003 | HTTP + stdio modes |

The pipeline is **not portable** without:
- Windows or a bat wrapper replacement
- Ollama accessible at the configured IP
- copilot-proxy running locally
- Java runtime (for tabula)

---

## Table Enhancement Sub-pipeline (Phase 1.5)

Only runs when `{stem}.json` exists (docling `--to json` output).

```
docling JSON  →  table bboxes (BOTTOMLEFT coords)
                     │
          ┌──────────┼──────────┐
          │          │          │
     pymupdf      tabula     camelot
    (crop PNG)  (java text) (lattice→stream)
          │          │          │
          └──────────┴──────────┘
                     │
               Ollama VLM (qwen3-vl:2b)
               [image = authoritative]
                     │
               Jaccard fingerprint
               (MD block matching)
                     │
              patched MD in-place
```

### Extractor failure modes (in VLM arbitration prompt)

| Extractor | Failure mode |
|-----------|-------------|
| Docling | May hallucinate column spans in complex tables; reliable for simple grids |
| Tabula | Column alignment drifts on rotated/skewed tables; needs clear delimiters |
| Camelot lattice | Requires visible grid lines; splits merged/spanning cells |
| Camelot stream | Column boundaries drift in multi-column/dense layouts |

The VLM prompt explicitly names each failure mode so the judge doesn't simply
pick the longest output.

### Camelot pre-classification

`extract_camelot` returns `(text, flavor, accuracy_pct)`. Lattice is tried
first; if it succeeds, `accuracy >= 80` signals a ruled table. The flavor and
accuracy are passed to the VLM prompt as context — a lattice run with 95%
accuracy is a more trustworthy input than a stream run with 40%.

### Cross-reference: JSON table → MD pipe block

`find_md_table_match(md_content, docling_md, fallback_idx)` uses Jaccard
token overlap between the docling table reconstruction and each `|...|` pipe
block in the markdown. If the best overlap score ≥ 0.25 the fingerprint match
is used; otherwise falls back to positional (N-th JSON table → N-th MD block).
This prevents silent wrong-block patching when table counts diverge between
docling JSON and the rendered markdown.

Coordinate spaces: tabula uses percentage coordinates from top-left; camelot
uses PDF points in BOTTOMLEFT origin. Both are converted via `_tabula_area`
and `_camelot_area` helpers from the docling BOTTOMLEFT bbox.

---

## Layout Classifier Training (`train_layout_classifier.py`)

Trains an EfficientNet-B0 classifier over docling-detected element crops.

Classes from docling labels: `table`, `picture`, `section_header`, `text`,
`list_item`, `caption`, `formula`, `footnote`, `page_header`, `page_footer`.

Class weighting uses the **Box-Cox log-ratio** protocol (see `class-balancing`
skill): `log_inv = log(N / count_c)` → Box-Cox transform → normalize → CrossEntropyLoss weight.

Training protocol (from system instructions):
1. Optuna sweep on 30% subset: patience=5, ≤20 epochs, `n_trials=15`
2. Full training with best params: patience=20, ≤100 epochs
3. Holdout evaluation (15% test split)

Checkpoint DB: `checkpoints/layout_classifier.db`

```bash
python train_layout_classifier.py --json-dir path/to/json_files/
python train_layout_classifier.py --pdf-dir path/to/pdfs/   # runs docling first
```

---

## Setup Mode

Invoke when pipeline_mcp.py is not yet registered.

### 1. Confirm pipeline files exist
```powershell
Test-Path "C:\Users\user\arxiv_id_lists\run_pipeline.bat"
Test-Path "C:\Users\user\.copilot\pipeline_mcp.py"
```

### 2. Add to `~/.copilot/mcp-config.json`
```json
"pdf-pipeline": {
  "type": "local",
  "command": "C:\\Users\\user\\py310\\Scripts\\python.exe",
  "args": ["C:\\Users\\user\\.copilot\\pipeline_mcp.py"]
}
```

### 3. Add to `start_mcp.ps1` (port 9003)
```powershell
$PipelineScript = "C:\Users\user\.copilot\pipeline_mcp.py"
$PipelinePort   = 9003
if (Test-Port $PipelinePort) {
    Write-Host "pdf-pipeline MCP already running (port $PipelinePort)"
} else {
    Write-Host "starting pdf-pipeline MCP on port $PipelinePort ..."
    Start-Process -FilePath $python `
        -ArgumentList @($PipelineScript, "--port", $PipelinePort) `
        -WindowStyle Hidden
    Start-Sleep -Seconds 2
    if (Test-Port $PipelinePort) { Write-Host "  started OK" }
    else { Write-Warning "  port $PipelinePort not responding" }
}
```

### 4. Update start_mcp.ps1 mcp-config sync block
Add alongside memory-bank and todo:
```powershell
$config.mcpServers.'pdf-pipeline'.command = $python
```

---

## MCP Server Scaffold

`~/.copilot/pipeline_mcp.py` — synthesize from this if missing:

See the actual file at `C:\Users\user\.copilot\pipeline_mcp.py`.

Key contracts:
- `convert_pdf`: launches `run_pipeline.bat` via `subprocess.Popen`; stores
  job in `~/.copilot/pipeline_jobs.db`; returns immediately unless `wait=True`
- `pipeline_status`: checks for `_methods.md` existence → `done`; bat process
  still running → `running`; neither → `not_started`
- `get_methods`: reads `_methods.md`; errors if not done
- `list_jobs`: scans a directory for `*_methods.md` files to show completion

---

## Integration with deep-research

When `deep-research` encounters a PDF URL or local path:

1. Check `pipeline_status(pdf_path)` — if `done`, call `get_methods(pdf_path)`
2. If `not_started`, call `convert_pdf(pdf_path, wait=True)` (~3-8 min)
3. If `running`, poll `pipeline_status` with 30s back-off

The `_methods.md` output is the primary enrichment artifact — it contains
the paper's core algorithmic contributions as structured pseudocode, suitable
for RAG chunking and similarity search.

---

## Figure / Schematic Transcription (Phase 3)

`vlm_describe.py` runs a single generic prompt for all images. For **annotated
diagrams, schematics, and parts illustrations** this is insufficient — the
spatial relationship between annotation labels and the components they point to
is lost in a prose caption.

### Image type taxonomy

| Type | Best output format | Prompt strategy |
|------|--------------------|-----------------|
| Chart / plot | Markdown table of data series + axis labels | Extract values explicitly |
| Simple diagram / flowchart | Numbered list of nodes + edges | "List every labeled box and every arrow" |
| Annotated part / assembly | Structured list: component → annotation text → spatial relationship | Two-pass (labels first, then associations) |
| Circuit / schematic | Component list + net list or ASCII topology | "List every component identifier and its connections" |
| Photo (no annotation) | Single-paragraph dense caption | Generic PROMPT is fine |

### Two-pass strategy for annotated images

For images where annotation labels point to specific parts:

**Pass 1 — label extraction:**
```
List every text label visible in this image, exactly as written.
Return as a JSON array of strings.
```

**Pass 2 — association:**
```
For each label below, identify what component or region it points to
and describe that component's function or appearance.
Labels: {labels_from_pass1}
Return as JSON: [{"label": "...", "component": "...", "description": "..."}]
```

The two-pass approach prevents the model from hallucinating label text in a
single-pass description where spatial attention competes with content generation.

### Structured output for schematics

For circuit diagrams or architecture schematics, request a net/edge list rather
than prose — this is semantically lossless and RAG-searchable:

```
Transcribe this schematic. Return JSON:
{
  "components": [{"id": "...", "type": "...", "label": "..."}],
  "connections": [{"from": "id", "to": "id", "label": "..."}]
}
```

### Integration point

These specialized prompts are not yet wired into `vlm_describe.py`. Docling's
own layout labels (`picture` vs `table` vs `figure`) provide the classification
signal — no separate classifier call needed.

Recommended implementation path:
1. Add a `PROMPT_TEMPLATES` dict keyed by docling label type
2. Pass docling label to `vlm_describe.py` via the CSV `image_type` column
3. Keep current generic `PROMPT` as the `picture`/unknown fallback
4. `value_added` gate is unchanged — runs before the type-specific prompt

### Multimodal RAG strategy for diagrams

**Research conclusion (ColPali paper arXiv:2407.01449, SciGraphQA arXiv:2308.03349,
DocParsing survey arXiv:2410.21169):**

| Approach | Retrieval (diagrams) | Generation | Verdict |
|---|---|---|---|
| Text transcription only (current) | ⚠️ Loses spatial/structural info | ❌ No image at gen time | **Broken for diagrams** |
| **Hybrid: description for retrieval + base64 at gen time** | ✅ Text finds relevant chunks | ✅ VLM gets full image | **Production optimum** |
| CLIP/SigLIP visual embedding | ❌ Worse than text on documents | — | Not suitable |
| ColPali (page-level patch vectors) | ✅✅ Best on visually rich docs | ✅ | Long-term; needs GPU infra |

**Critical gap in the current pipeline**: `vlm_describe.py` computes descriptions
and writes them to `{paper_id}_images.csv`, but `ingestion/arxiv_chunking_pipeline.py`
never reads the CSV. Chunks contain `<image_NNN>` placeholder tags but no
descriptions — the VLM work is discarded before retrieval.

**Tier 1 fix (no new infrastructure):** In the chunking pipeline, load
`{paper_id}_images.csv` and expand `<image_NNN>` to:
```
<image_001 desc="VLM description here" value_added="true">
```
This makes descriptions BM25/dense searchable at zero additional cost.

**Tier 2 (hybrid production pattern):** Store per-image in pgvector chunks:
- `description` (text, for retrieval)
- `base64_data` (for VLM at answer generation time)
- `value_added` flag
- `paper_id` + `image_index` cross-reference

At query time: text retrieval finds the chunk → image base64 is fetched →
passed to VLM alongside text context. Spatial structure (annotations, wire
topology, call-outs) is preserved for answering, not transcribed away.

**Tier 3 (long-term):** ColPali/ColQwen2 for L1 visual retrieval. Stores
1024×128 float32 patch embeddings per page (~257KB). MaxSim late interaction
over patches — each query token attends to the most relevant image region.
~0.16s/page indexing vs. 10-30s for captioning. ColQwen2 (Qwen2-VL 2B)
outperforms ColPali by +5.3 nDCG@5. Given Qwen3-VL is already in this
pipeline, ColQwen2 is a natural Tier 3 upgrade.

### Multimodal RAG strategy for diagrams

**Architecture context**: This pipeline is **not** a chunked retrieval pipeline.
Retrieval uses titles/abstracts only (Chroma + manual BM25 on disk). The PDF
pipeline runs only after a paper is already selected for deeper reading. The
output (`_methods.md`) is a reading/extraction artifact, not a retrieval document.

**Research conclusion (ColPali arXiv:2407.01449, SciGraphQA arXiv:2308.03349):**
For annotated parts diagrams, circuit schematics, and architecture diagrams,
text transcription is measurably lossy — spatial topology (what label points
at what, which wire connects where) cannot be faithfully recovered as prose.

**Correct pattern for this pipeline:**
- Infographics, charts, plots → VLM description in `_methods.md` is sufficient
- Schematics, annotated assemblies, circuit diagrams → preserve base64, pass
  image + question to VLM at query time rather than transcribing upfront

The base64 already exists after Phase 2: all images are stored in
`{stem}_images.csv` keyed by `<image_NNN>` tag. Table crops are in
`{stem}_table_crops/`. No new storage required.

**Query-time pattern** (single paper, no retrieval layer):
```python
# Load CSV, find image by tag
df = pd.read_csv("paper_images.csv")
row = df[df.image_index == "001"].iloc[0]
b64 = row["base64_data"]
# Pass image + question to VLM
response = ollama.generate(model="qwen3-vl:2b",
    prompt="What does the feedback loop in this diagram do?",
    images=[b64])
```

**What NOT to do**: CLIP/SigLIP embeddings for document images — benchmarks
show they perform worse than BM25 on document retrieval. ColPali is only
relevant if moving to a chunked/page-level retrieval architecture later.

---

## Related Skills

| Skill | Relationship |
|-------|-------------|
| `auto-ingest` | arxiv corpus variant: queue-based daemon, same Phase 2-5 scripts |
| `class-balancing` | Box-Cox log-ratio weighting used by layout classifier |
| `deep-research` | consumer: calls convert_pdf + get_methods via MCP |
| `mcp-tool-registry` | pattern reference for FastMCP server design |
<!-- consolidation:see-also:start -->
## See Also
[[auto-ingest]]
<!-- consolidation:see-also:end -->
