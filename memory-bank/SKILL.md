---
name: memory-bank
description: >
  Operational project memory for long-running work. Use when reading or updating
  project brief, product context, active context, system patterns, tech context,
  and progress so work survives session resets and resumes cleanly.
---

# Memory Bank

## Scope Boundary

This skill is for **project and session continuity**.

It is not the semantic-memory graph.

Use `memory-bank` for:
- project onboarding
- restoring context after a reset
- current focus, blockers, and next steps
- architecture and stack decisions
- progress checkpoints across sessions

Do **not** use `memory-bank` for:
- triplet extraction
- corpus retrieval
- NLI premise validation
- throughline ranking
- graph edge reinforcement

Those belong to `agentic_kg_memory`.

## Setup Mode

If the user invokes **`memory-bank setup`**, treat that as an installation request,
not a normal retrieval/update request.

### Required setup artifacts

In this environment, the authoritative paths are:

- `C:\Users\user\memory-bank\`
- `C:\Users\user\memory-bank\AGENTS.md`
- `C:\Users\user\.copilot\copilot-instructions.md`
- `C:\Users\user\.copilot\memory_mcp.py`
- `C:\Users\user\.copilot\mcp-config.json`

If a TOML-based Copilot config exists, check and mirror the setup there too:

- `C:\Users\user\.config\github-copilot\config.toml`

In the current machine state, `mcp-config.json` exists and `config.toml` does not.
Do not invent a TOML file if the CLI is already using `mcp-config.json`; only edit
the TOML path if that installation actually has one.

### Setup actions

When running setup, do all of the following:

1. Create `C:\Users\user\memory-bank\` if missing
2. Create the six canonical markdown files if missing
3. Assemble `C:\Users\user\memory-bank\AGENTS.md`
4. Write `C:\Users\user\.copilot\copilot-instructions.md`
5. Write `C:\Users\user\.copilot\memory_mcp.py`
6. Register the `memory-bank` MCP server in `C:\Users\user\.copilot\mcp-config.json`
7. If `C:\Users\user\.config\github-copilot\config.toml` exists, mirror the MCP registration there
8. Set the user environment variable `COPILOT_CUSTOM_INSTRUCTIONS_DIRS` to `C:\Users\user\memory-bank`
9. Ensure `fastmcp` is importable in the active Python environment; install it if missing
10. Ensure the semantic backend directories exist for KG search:
   - `C:\Users\user\memory-bank\wiki_memory.sqlite3`
   - `C:\Users\user\.copilot\chroma\memory-bank\`

### MCP registration snippet

```json
{
  "mcpServers": {
    "memory-bank": {
      "type": "local",
      "command": "python",
      "args": ["C:\\Users\\user\\.copilot\\memory_mcp.py"]
    }
  }
}
```

### Windows bootstrap snippets

If setup is running on Windows, these two checks are part of the install contract:

```powershell
[System.Environment]::SetEnvironmentVariable(
    "COPILOT_CUSTOM_INSTRUCTIONS_DIRS",
    "C:\Users\user\memory-bank",
    "User"
)

python -c "import fastmcp" 2>$null
if ($LASTEXITCODE -ne 0) {
    python -m pip install fastmcp
}
```

Do not consider setup complete unless the environment variable is present and
`fastmcp` imports successfully.

### Python MCP server scaffold

`memory-bank setup` should not stop at file names and config keys. It should be
able to synthesize the write-back server from markdown in this skill.

```python
from datetime import datetime
from pathlib import Path

from fastmcp import FastMCP

MEMORY_DIR = Path(r"C:\Users\user\memory-bank")

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
    if file not in ALLOWED_FILES:
        raise ValueError(f"Unknown file '{file}'. Allowed: {sorted(ALLOWED_FILES)}")

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
    parts = []
    for fname in FILE_ORDER:
        fpath = MEMORY_DIR / fname
        if fpath.exists():
            parts.append(f"## {fname}\n{fpath.read_text(encoding='utf-8').strip()}")
    return "\n\n---\n\n".join(parts)


def _regenerate_agents_md() -> None:
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
```

### Chroma bootstrap scaffold

If semantic KG mode is being provisioned during `memory-bank setup`, bootstrap the
dense backend in the same setup flow so `agentic_kg_memory` can use it immediately.

```python
import sqlite3
from pathlib import Path

import chromadb

SQLITE_PATH = Path(r"C:\Users\user\memory-bank\wiki_memory.sqlite3")
CHROMA_DIR = Path(r"C:\Users\user\.copilot\chroma\memory-bank")
COLLECTION_NAME = "memory-bank-triplet-sequences"


def ensure_semantic_backend() -> chromadb.Collection:
    CHROMA_DIR.mkdir(parents=True, exist_ok=True)

    with sqlite3.connect(SQLITE_PATH) as conn:
        conn.execute(
            """
            CREATE TABLE IF NOT EXISTS wiki_pages (
                page_id TEXT PRIMARY KEY,
                intent TEXT NOT NULL,
                objective TEXT NOT NULL,
                bm25_text TEXT NOT NULL,
                triplet_sequence_text TEXT NOT NULL,
                embedding_ref TEXT,
                cluster_id TEXT,
                wiki_summary TEXT,
                history_json TEXT NOT NULL DEFAULT '[]'
            )
            """
        )
        conn.commit()

    client = chromadb.PersistentClient(path=str(CHROMA_DIR))
    return client.get_or_create_collection(
        name=COLLECTION_NAME,
        metadata={"hnsw:space": "cosine"},
    )
```

### Setup behavior rule

When the user says **`memory-bank setup`**, the agent should:

1. write the markdown files
2. write `memory_mcp.py` from the Python scaffold above
3. register the MCP server
4. set `COPILOT_CUSTOM_INSTRUCTIONS_DIRS` for the user profile
5. verify or install `fastmcp`
6. provision the optional SQLite + Chroma backend if semantic search is requested
7. report the exact paths created or updated

### Semantic backend note

`memory-bank` remains the **project operating memory** skill, but its setup step
may provision the persistent stores required by `agentic_kg_memory`:

- SQLite metadata store at `C:\Users\user\memory-bank\wiki_memory.sqlite3`
- Chroma persist directory at `C:\Users\user\.copilot\chroma\memory-bank\`

This lets the project-memory server and the KG-memory skill share a stable backend
without collapsing their responsibilities into one skill.

### Setup completion contract

After setup, an agent should be able to confirm:

- the six markdown files exist
- `AGENTS.md` exists
- `/mcp show` lists `memory-bank`
- `C:\Users\user\.copilot\mcp-config.json` contains the registration
- `COPILOT_CUSTOM_INSTRUCTIONS_DIRS` points at `C:\Users\user\memory-bank`
- `python -c "import fastmcp"` exits successfully
- if semantic KG mode is enabled, the SQLite and Chroma paths exist

## Canonical Files

Read and maintain these six files:

1. `projectbrief.md`
2. `productContext.md`
3. `activeContext.md`
4. `systemPatterns.md`
5. `techContext.md`
6. `progress.md`

## What Each File Stores

### `projectbrief.md`
- project purpose
- hard requirements
- out-of-scope boundaries

### `productContext.md`
- why the project exists
- user-facing goals
- success criteria from the operator's point of view

### `activeContext.md`
- current focus
- recent changes
- active decisions
- immediate next steps

### `systemPatterns.md`
- architecture
- design patterns
- component relationships
- implementation constraints that keep recurring

### `techContext.md`
- stack
- dependencies
- environment assumptions
- setup commands and technical constraints

### `progress.md`
- what works
- what remains
- known issues
- milestone history

## Read Protocol

At task start:
- read all six files
- build a coherent picture before acting
- treat missing files as a memory gap that should be repaired

## Write Protocol

Update the memory bank when:
- a significant feature or fix lands
- an architectural decision changes
- a blocker is discovered or resolved
- the resume point for a future session changes
- the user explicitly asks to update memory

## Writing Rules

- Keep entries factual and concise
- Append dated milestones rather than rewriting history away
- Prefer stable operating context over transient scratch notes
- Capture decisions and their consequences, not just actions taken
- Record resume points explicitly so a future session can restart quickly

## Relation to KG Memory

The split is:

- `memory-bank` = **project operating memory**
- `agentic_kg_memory` = **semantic evidence memory**

`memory-bank` tells you:
- what project you are in
- what changed recently
- what matters next

`agentic_kg_memory` tells you:
- what the evidence says
- how pages and throughlines cluster
- which conclusions are currently strongest

If needed, the memory bank can reference page IDs, throughline IDs, or corpus
artifacts, but it should not become the graph itself.

## Anti-Patterns

Avoid:
- storing corpus triplets in the memory bank
- using progress.md as a retrieval index
- mixing project-state notes with evidence-level conclusions
- rewriting history instead of appending milestone context
- keeping only chat-local context when a stable file belongs in memory-bank

## Minimal Output Contract

When using this skill, report:
- which memory-bank files were read or updated
- what project-state fact changed
- what the new resume point is
- any blocker or decision that future sessions must inherit
