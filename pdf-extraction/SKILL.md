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
    (crop PNG)  (java text) (line detect)
          │          │          │
          └──────────┴──────────┘
                     │
               Ollama VLM (qwen3-vl:2b)
                     │
              enhanced MD table
```

Tabula uses percentage area coordinates (from top-left); camelot uses PDF
point coordinates (BOTTOMLEFT origin). The VLM receives all three sources
and the cropped image, uses the image as authoritative truth.

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

## Related Skills

| Skill | Relationship |
|-------|-------------|
| `auto-ingest` | arxiv corpus variant: queue-based daemon, same Phase 2-5 scripts |
| `class-balancing` | Box-Cox log-ratio weighting used by layout classifier |
| `deep-research` | consumer: calls convert_pdf + get_methods via MCP |
| `mcp-tool-registry` | pattern reference for FastMCP server design |
