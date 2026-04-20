# copilot_memory_setup.ps1
#
# One-shot setup of GitHub Copilot CLI memory bank system on Windows.
# Copy to a gist and run on any machine:
#
#   Set-ExecutionPolicy -Scope CurrentUser RemoteSigned   # if needed
#   .\copilot_memory_setup.ps1
#
# What this does:
#   1. Creates ~/memory-bank/ with all 6 core files populated with your context
#   2. Assembles ~/memory-bank/AGENTS.md (auto-injected into every Copilot session)
#   3. Writes ~/.copilot/copilot-instructions.md with Cline-style memory protocol
#   4. Writes ~/.copilot/memory_mcp.py (fastmcp server for write-back)
#   5. Registers the MCP server in ~/.copilot/mcp-config.json
#   6. Sets COPILOT_CUSTOM_INSTRUCTIONS_DIRS as a persistent user env var
#   7. Installs fastmcp if missing
#
# After running: restart terminal, then verify with /mcp show inside Copilot CLI.
#
# Usage:
#   Session start  : nothing to do - AGENTS.md is auto-injected every session
#   End of task    : say "update memory bank" - Copilot calls update_memory,
#                    approve each tool call to persist changes
#   New project    : edit ~/memory-bank/*.md directly, then rerun this script
#                    to rebuild AGENTS.md with the new content
#   Verify setup   : /mcp show confirms server is live; say "list memory" to
#                    see current file contents via the list_memory tool

$ErrorActionPreference = "Stop"

$MemoryDir   = Join-Path $HOME "memory-bank"
$CopilotDir  = Join-Path $HOME ".copilot"
$McpServer   = Join-Path $CopilotDir "memory_mcp.py"
$McpConfig   = Join-Path $CopilotDir "mcp-config.json"
$GlobalInstr = Join-Path $CopilotDir "copilot-instructions.md"

# ── 1. Directories ─────────────────────────────────────────────────────────────

New-Item -ItemType Directory -Force -Path $MemoryDir | Out-Null
New-Item -ItemType Directory -Force -Path $CopilotDir | Out-Null

# ── 2. Memory bank template files (skip if already exist) ─────────────────────

function Write-IfMissing($Path, $Content) {
    if (-not (Test-Path $Path)) {
        Set-Content -Path $Path -Value $Content -Encoding UTF8
        Write-Host "  created: $Path"
    } else {
        Write-Host "  exists (skipped): $Path"
    }
}

Write-IfMissing "$MemoryDir\projectbrief.md" @'
# Project Brief

## Purpose
<!-- What this project does and why it exists -->

## Core Requirements
<!-- Non-negotiables -->

## Out of Scope
<!-- Explicit exclusions -->
'@

Write-IfMissing "$MemoryDir\productContext.md" @'
# Product Context

## Why This Exists
<!-- Problem being solved -->

## How It Should Work
<!-- Expected behavior from the user perspective -->

## User Experience Goals
<!-- What good looks like -->
'@

Write-IfMissing "$MemoryDir\activeContext.md" @'
# Active Context

## Current Focus
<!-- What is being worked on right now -->

## Recent Changes
<!-- What was just done -->

## Next Steps
<!-- Immediate next actions -->

## Active Decisions
<!-- Open questions and considerations -->

## Patterns and Preferences
<!-- Conventions established in this project -->

## Learnings
<!-- Insights gained -->
'@

Write-IfMissing "$MemoryDir\systemPatterns.md" @'
# System Patterns

## Architecture
<!-- How the system is structured -->

## Key Technical Decisions
<!-- Why things are built the way they are -->

## Design Patterns in Use
<!-- Recurring patterns in this codebase -->

## Component Relationships
<!-- How parts connect -->

## Critical Implementation Paths
<!-- Load-bearing code paths -->
'@

Write-IfMissing "$MemoryDir\techContext.md" @'
# Tech Context

## Technologies Used
<!-- Languages, frameworks, libraries -->

## Development Setup
<!-- How to build, run, test -->

## Technical Constraints
<!-- Platform, performance, security limits -->

## Dependencies
<!-- External dependencies and versions -->

## Tool Usage Patterns
<!-- How tools are used in this project -->
'@

Write-IfMissing "$MemoryDir\progress.md" @'
# Progress

## What Works
<!-- Completed and verified -->

## What Is Left to Build
<!-- Remaining work -->

## Current Status
<!-- Overall state of the project -->

## Known Issues
<!-- Bugs, limitations, tech debt -->

## Evolution of Decisions
<!-- How thinking has changed over time -->
'@

# ── 3. AGENTS.md — assembled from all memory bank files ───────────────────────

function Build-AgentsMd {
    $order = @(
        "projectbrief.md",
        "productContext.md",
        "techContext.md",
        "systemPatterns.md",
        "activeContext.md",
        "progress.md"
    )
    $lines = [System.Collections.Generic.List[string]]@(
        "# Memory Bank",
        "",
        "This file is auto-injected into every Copilot CLI session.",
        "Treat all sections below as authoritative project context.",
        ""
    )
    foreach ($fname in $order) {
        $fpath = Join-Path $MemoryDir $fname
        if (Test-Path $fpath) {
            $lines.Add("")
            $lines.Add("---")
            $lines.Add((Get-Content $fpath -Raw -Encoding UTF8))
        }
    }
    Set-Content -Path "$MemoryDir\AGENTS.md" -Value ($lines -join "`n") -Encoding UTF8
    Write-Host "  created: $MemoryDir\AGENTS.md"
}

Build-AgentsMd

# ── 4. Global instructions (Cline-style prompt) ────────────────────────────────

Set-Content -Path $GlobalInstr -Encoding UTF8 -Value @'
# Memory Bank Protocol

I have a unique characteristic: my memory resets completely between sessions.
This is not a limitation - it drives me to maintain perfect documentation.
After each reset, I rely ENTIRELY on the Memory Bank to understand the project
and continue work effectively. I MUST read ALL memory bank files at the start
of EVERY task - this is not optional.

## Memory Bank Structure

Files are located in ~/memory-bank/ and build on each other in this order:

1. projectbrief.md    - foundation document, core requirements, project scope
2. productContext.md  - why the project exists, problems solved, UX goals
3. activeContext.md   - current focus, recent changes, next steps, decisions
4. systemPatterns.md  - architecture, technical decisions, design patterns
5. techContext.md     - stack, dev setup, constraints, dependencies
6. progress.md        - what works, what remains, known issues

## Reading the Memory Bank

At the start of EVERY task:
- Read ALL six files above before doing anything else
- If any file is missing, create it using the templates implied by its purpose
- Build a complete picture of the project before responding

## Updating the Memory Bank

Update memory bank files when:
1. Discovering new project patterns
2. After implementing significant changes
3. When the user says "update memory bank" - MUST review and update ALL files
4. When context needs clarification

Use the update_memory tool to append timestamped entries. Do not overwrite
history. Keep entries factual and concise.

## Coding Defaults

- Python: fastapi for APIs, pydantic for validation, sqlite for checkpoints,
  streamlit or gradio for prototyping, fastmcp for MCP servers.
- Data: stooq via pandas_datareader for prices. FMP free tier or SEC EDGAR
  XBRL for fundamentals. Never yfinance.
- Always provide complete functions, never snippets.
- Docstrings document purpose, preconditions, and failure modes.
- Heavy computations use sqlite load-if-exists checkpointing.
'@

Write-Host "  created: $GlobalInstr"

# ── 5. MCP server ──────────────────────────────────────────────────────────────

Set-Content -Path $McpServer -Encoding UTF8 -Value @"
"""
memory_mcp.py -- fastmcp server for Copilot CLI memory bank writes.

Purpose:
    Provides update_memory and list_memory tools that Copilot CLI calls when
    the user says 'update memory bank' or 'update context'. Writes are
    append-based to preserve history. Rebuilds AGENTS.md after every write
    so the next session picks up current state.

Preconditions:
    - memory-bank directory must exist (created by setup_copilot_memory.ps1)
    - fastmcp installed: pip install fastmcp

Failure modes:
    - Unknown file: raises ValueError, Copilot surfaces the error
    - Missing file: raises IOError with path context
    - Write failure: propagates IOError
"""

from datetime import datetime
from pathlib import Path

from fastmcp import FastMCP

MEMORY_DIR = Path(r"$MemoryDir")

ALLOWED_FILES = {
    "projectbrief.md",
    "productContext.md",
    "activeContext.md",
    "systemPatterns.md",
    "techContext.md",
    "progress.md",
}

FILE_ORDER = [
    "projectbrief.md",
    "productContext.md",
    "techContext.md",
    "systemPatterns.md",
    "activeContext.md",
    "progress.md",
]

mcp = FastMCP("memory-bank")


@mcp.tool()
def update_memory(file: str, content: str) -> str:
    """
    Append a timestamped entry to a memory bank file.

    Args:
        file:    One of the six core memory bank files.
        content: Text to append. Wrapped with a timestamp header.

    Returns:
        Confirmation string with the path written.

    Raises:
        ValueError: file not in the allowed set
        IOError:    file missing or write failed
    """
    if file not in ALLOWED_FILES:
        raise ValueError(
            f"Unknown file '{file}'. Allowed: {sorted(ALLOWED_FILES)}"
        )

    target = MEMORY_DIR / file
    if not target.exists():
        raise IOError(f"Memory bank file not found: {target}")

    timestamp = datetime.now().strftime("%Y-%m-%d %H:%M")
    entry = f"\n\n### {timestamp}\n{content.strip()}\n"

    with open(target, "a", encoding="utf-8") as fh:
        fh.write(entry)

    _regenerate_agents_md()
    return f"Appended to {target}"


@mcp.tool()
def list_memory() -> str:
    """
    Return current contents of all memory bank files.

    Useful when Copilot needs to read memory programmatically rather than
    relying on the injected AGENTS.md snapshot.
    """
    parts = []
    for fname in FILE_ORDER:
        fpath = MEMORY_DIR / fname
        if fpath.exists():
            parts.append(f"## {fname}\n{fpath.read_text(encoding='utf-8').strip()}")
    return "\n\n---\n\n".join(parts)


def _regenerate_agents_md() -> None:
    """
    Rebuild AGENTS.md from individual memory bank files.

    Invariant: AGENTS.md always reflects current file contents after any write.
    """
    lines = [
        "# Memory Bank\n",
        "This file is auto-injected into every Copilot CLI session.\n",
        "Treat all sections below as authoritative project context.\n",
    ]
    for fname in FILE_ORDER:
        fpath = MEMORY_DIR / fname
        if fpath.exists():
            lines.append("\n---\n")
            lines.append(fpath.read_text(encoding="utf-8"))
    (MEMORY_DIR / "AGENTS.md").write_text("\n".join(lines), encoding="utf-8")


if __name__ == "__main__":
    mcp.run()
"@

Write-Host "  created: $McpServer"

# ── 6. MCP config registration ─────────────────────────────────────────────────

if (Test-Path $McpConfig) {
    $config = Get-Content $McpConfig -Raw -Encoding UTF8 | ConvertFrom-Json
    if (-not $config.mcpServers) {
        $config | Add-Member -NotePropertyName "mcpServers" -NotePropertyValue ([PSCustomObject]@{})
    }
    $config.mcpServers | Add-Member -NotePropertyName "memory-bank" -NotePropertyValue ([PSCustomObject]@{
        type    = "local"
        command = "python"
        args    = @($McpServer)
    }) -Force
    $config | ConvertTo-Json -Depth 10 | Set-Content $McpConfig -Encoding UTF8
    Write-Host "  merged into: $McpConfig"
} else {
    [PSCustomObject]@{
        mcpServers = [PSCustomObject]@{
            "memory-bank" = [PSCustomObject]@{
                type    = "local"
                command = "python"
                args    = @($McpServer)
            }
        }
    } | ConvertTo-Json -Depth 10 | Set-Content $McpConfig -Encoding UTF8
    Write-Host "  created: $McpConfig"
}

# ── 7. User-level environment variable ────────────────────────────────────────

$existing = [System.Environment]::GetEnvironmentVariable("COPILOT_CUSTOM_INSTRUCTIONS_DIRS", "User")
if ($existing -ne $MemoryDir) {
    [System.Environment]::SetEnvironmentVariable("COPILOT_CUSTOM_INSTRUCTIONS_DIRS", $MemoryDir, "User")
    Write-Host "  set user env: COPILOT_CUSTOM_INSTRUCTIONS_DIRS=$MemoryDir"
} else {
    Write-Host "  already set: COPILOT_CUSTOM_INSTRUCTIONS_DIRS"
}

# ── 8. fastmcp dependency ──────────────────────────────────────────────────────

$result = & python -c "import fastmcp" 2>&1
if ($LASTEXITCODE -ne 0) {
    Write-Host ""
    Write-Host "Installing fastmcp..."
    python -m pip install fastmcp --quiet
    Write-Host "  fastmcp installed"
} else {
    Write-Host "  fastmcp already installed"
}

# ── Done ───────────────────────────────────────────────────────────────────────

Write-Host ""
Write-Host "Done. Restart your terminal for the env var to take effect."
Write-Host ""
Write-Host "Usage:"
Write-Host "  - Start Copilot CLI. Memory bank is auto-injected every session."
Write-Host "  - Say 'update memory bank' after a task to update all relevant files."
Write-Host "  - Edit ~\memory-bank\*.md manually any time."
Write-Host "  - Rerun this script to rebuild AGENTS.md after manual edits."
Write-Host ""
Write-Host "Memory bank : $MemoryDir"
Write-Host "MCP server  : $McpServer"
Write-Host "MCP config  : $McpConfig"
Write-Host "Instructions: $GlobalInstr"


# populate_memory_bank.ps1
#
# Populates ~/memory-bank/ with your actual context.
# Safe to rerun - overwrites all six files with current content.

$MemoryDir = Join-Path $HOME "memory-bank"

if (-not (Test-Path $MemoryDir)) {
    Write-Error "Memory bank not found at $MemoryDir. Run setup_copilot_memory.ps1 first."
    exit 1
}

# ── projectbrief.md ────────────────────────────────────────────────────────────

Set-Content -Path "$MemoryDir\projectbrief.md" -Encoding UTF8 -Value @'
# Project Brief

## Purpose
This memory bank covers Jos Hua's personal technical work outside of Boeing:
quantitative finance pipeline, homelab AI infrastructure, and associated tooling.
Not Boeing work. Not subject to Boeing IP constraints.

## Core Requirements
- Quant pipeline must be reproducible and checkpoint-based (sqlite load-if-exists)
- All price data via stooq through pandas_datareader. Never yfinance.
- Fundamentals via FMP free tier or SEC EDGAR XBRL API
- Local AI inference preferred over cloud where latency allows
- Code must be complete — no snippets, no placeholders

## Out of Scope
- Boeing proprietary systems
- Yahoo Finance or yfinance in any form
- Cloud-first solutions where local inference is viable
'@

Write-Host "  wrote: projectbrief.md"

# ── productContext.md ──────────────────────────────────────────────────────────

Set-Content -Path "$MemoryDir\productContext.md" -Encoding UTF8 -Value @'
# Product Context

## Why This Exists
Personal quant pipeline running in a Roth IRA via IBKR. Separate from day job.
Goal is systematic, rules-based portfolio management with minimal manual intervention.
Homelab AI stack supports both the quant work and general LLM experimentation.

## How It Should Work
- Pipeline runs on 13-week rolling tranches
- XGBoost business cycle classifier on FRED indicators drives regime detection
- Markowitz optimization with MAD-based Sharpe, fed by median-mean GAM normalized expected returns
- Parkinson volatility for bracket orders
- IBKR execution layer is the terminal output
- Two-stage optimizer consistently favors GLDM/XES/COPX cluster
- Current thesis: dollar debasement + geopolitical risk (Operation Epic Fury, US-Iran)
- Portfolio ratio: ~1.3:1 GLDM:XES reflecting near-term XES catalyst asymmetry

## User Experience Goals
- Run pipeline, get orders, approve, done
- Minimal friction between signal and execution
- Audit trail via sqlite so any run is reproducible
'@

Write-Host "  wrote: productContext.md"

# ── activeContext.md ───────────────────────────────────────────────────────────

Set-Content -Path "$MemoryDir\activeContext.md" -Encoding UTF8 -Value @'
# Active Context

## Current Focus
Setting up GitHub Copilot CLI with Cline-style memory bank via fastmcp.
Windows environment (py310 conda env).

## Recent Changes
- Installed memory bank scaffold via setup_copilot_memory.ps1
- MCP server registered at ~/.copilot/mcp-config.json
- COPILOT_CUSTOM_INSTRUCTIONS_DIRS pointing to ~/memory-bank/

## Next Steps
- Verify /mcp show lists memory-bank in Copilot CLI
- Populate memory bank per active project before first real session
- Resume quant pipeline work or RAG pipeline work as needed

## Active Decisions
- Memory bank write trigger: "update memory bank"
- Reads are static injection via AGENTS.md, not routed through MCP
- MCP server handles writes only

## Patterns and Preferences
- One degree less technical verbosity than default
- Plain speech, direct answers, no preamble
- Complete files always — never snippets
- Bold original phrasing when expanding ideas

## Learnings
- Copilot CLI reads AGENTS.md via COPILOT_CUSTOM_INSTRUCTIONS_DIRS
- MCP config lives at ~/.copilot/mcp-config.json
- fastmcp already installed in py310 env
'@

Write-Host "  wrote: activeContext.md"

# ── systemPatterns.md ──────────────────────────────────────────────────────────

Set-Content -Path "$MemoryDir\systemPatterns.md" -Encoding UTF8 -Value @'
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
'@

Write-Host "  wrote: systemPatterns.md"

# ── techContext.md ─────────────────────────────────────────────────────────────

Set-Content -Path "$MemoryDir\techContext.md" -Encoding UTF8 -Value @'
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
- IBKR execution in Roth IRA — real money, no runaway automation
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
'@

Write-Host "  wrote: techContext.md"

# ── progress.md ────────────────────────────────────────────────────────────────

Set-Content -Path "$MemoryDir\progress.md" -Encoding UTF8 -Value @'
# Progress

## What Works
- Quant pipeline: XGBoost classifier, Markowitz optimizer, GAM normalization,
  Parkinson vol, IBKR bracket order generation, 13-week rolling tranches
- Homelab: Open-WebUI, Ollama, llama.cpp, pgvector, SearXNG, ComfyUI
- RAG pipeline: hybrid BM25 + GIST retrieval, ColBERT, cross-encoder reranking,
  GraphRAG with GATv2, RAGAS eval
- SEC EDGAR fundamentals: Dow 30 JSONB pipeline in PostgreSQL (secdb, port 5433)
- Copilot CLI memory bank: scaffold installed, MCP server registered

## What Is Left to Build
- Verify Copilot CLI /mcp show sees memory-bank server
- Portfolio benchmarking against SPY, risk-free rate, inflation
- OpenClaw multi-agent monitoring layer over quant pipeline (planned, not started)

## Current Status
Active. Quant pipeline running. Homelab stable.
Memory bank just installed for Copilot CLI workflow.

## Known Issues
- Copilot CLI MCP write-back not yet verified end-to-end
- AGENTS.md is a static snapshot; stale if memory bank files edited without rerunning script

## Evolution of Decisions
- Moved from 2:1 to 1.3:1 GLDM:XES ratio on near-term XES asymmetry
- Replaced Google PSE with SearXNG in homelab
- F106 RRF ensemble ER ranking gap diagnosed and patched
'@

Write-Host "  wrote: progress.md"

# ── Rebuild AGENTS.md ──────────────────────────────────────────────────────────

$order = @(
    "projectbrief.md",
    "productContext.md",
    "techContext.md",
    "systemPatterns.md",
    "activeContext.md",
    "progress.md"
)

$lines = [System.Collections.Generic.List[string]]@(
    "# Memory Bank",
    "",
    "This file is auto-injected into every Copilot CLI session.",
    "Treat all sections below as authoritative project context.",
    ""
)

foreach ($fname in $order) {
    $fpath = Join-Path $MemoryDir $fname
    if (Test-Path $fpath) {
        $lines.Add("")
        $lines.Add("---")
        $lines.Add((Get-Content $fpath -Raw -Encoding UTF8))
    }
}

Set-Content -Path "$MemoryDir\AGENTS.md" -Value ($lines -join "`n") -Encoding UTF8
Write-Host "  rebuilt: AGENTS.md"

Write-Host ""
Write-Host "Done. Memory bank populated and AGENTS.md rebuilt."