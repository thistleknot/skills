# System Patterns

## Architecture
Two independent stacks:

1. Quant pipeline (local Windows + IBKR)
   - FRED data -> XGBoost classifier -> regime signal
   - stooq prices -> Parkinson vol -> expected returns
   - GAM normalization (Yeo-Johnson + dual-path) -> Markowitz optimizer
   - sqlite checkpointing throughout
   - IBKR API for bracket order execution in Roth IRA

2. Homelab AI (Proxmox host pve-m7330)
   - Open-WebUI at 192.168.3.18 with pgvector backend
   - Ollama at 192.168.3.17
   - llama.cpp serving Qwen on port 8080 as OpenAI-compatible endpoint
   - SearXNG for web search
   - ComfyUI in Docker with Quadro P5200

## Key Technical Decisions
- sqlite over postgres for local pipeline checkpointing (simpler, portable)
- stooq via pandas_datareader as the canonical price source
- fastmcp for all MCP servers
- pgvector + BM25 hybrid retrieval for RAG
- RAGAS macro-F1 as single scalar RAG eval metric

## Design Patterns in Use
- Load-if-exists checkpoint pattern on all heavy computations
- Two-stage optimizer (regime filter -> portfolio optimizer)
- 13-week rolling tranches for position management
- Assertions at pipeline checkpoints; transformations reversible
- Try/except only on non-critical paths; critical paths fail fast

## Component Relationships
- FRED indicators feed the classifier
- Classifier output gates the optimizer
- Optimizer output feeds IBKR bracket order generation
- All intermediate state persisted to sqlite

## Critical Implementation Paths
- Regime classifier must run before optimizer
- GAM normalization must precede expected return input to optimizer
- Parkinson vol must be computed before bracket sizing


### 2026-04-18 21:09
Established a new content architecture pattern for the civ project: authoritative game content lives in schema-validated JSON pack files, while runtime compatibility layers project that content into legacy rule shapes for the simulation engine. This keeps downstream systems stable during migration and gives modders a one-stop folder layout similar to classic civ/CTP database-driven modding workflows.
