# Tech Context

## Technologies Used
- Python 3.10 (conda env py310) on Windows
- FastAPI, Pydantic, Streamlit, Gradio, FastMCP
- XGBoost, scikit-learn, scipy, cvxpy
- pandas, pandas_datareader (stooq), numpy
- sqlite3 for checkpointing
- pgvector, BM25, GIST embeddings, ColBERT, cross-encoder reranking
- IBKR API (ib_insync or native) for execution
- Proxmox (pve-m7330), Docker, Rocky Linux 9
- Ollama, llama.cpp, Open-WebUI, ComfyUI
- Quadro P5200 GPU in homelab

## Development Setup
- Windows primary workstation, py310 conda env
- Homelab on Proxmox at 192.168.3.x subnet
- Ollama inference at 192.168.3.17
- Open-WebUI at 192.168.3.18
- llama.cpp OpenAI-compatible endpoint on port 8080
- GitHub Copilot CLI for agentic coding sessions

## Technical Constraints
- Price data: stooq only via pandas_datareader. Yahoo Finance/yfinance banned.
- Fundamentals: FMP free tier or SEC EDGAR XBRL only
- IBKR execution in Roth IRA â€” real money, no runaway automation
- Windows paths use backslash; Python code must use pathlib or raw strings

## Dependencies
- fastmcp (installed in py310)
- pandas_datareader for stooq
- cvxpy for portfolio optimization
- ib_insync or IBKR native API
- Optuna TPE for hyperparameter search

## Tool Usage Patterns
- sqlite load-if-exists before any heavy computation
- Assertions at every pipeline stage boundary
- Complete files delivered, never partial
- RAGAS macro-mean as RAG eval scalar
