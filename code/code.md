# Code Standards

## Explore Before Writing

LLMs default to junior-developer behavior: they write code locally correct but globally wrong — duplicating abstractions, missing patterns, creating ripple effects. Counteract by building a hierarchical mental model of the codebase *before* generating any code.

**Senior vs. Junior mental model**

| Junior | Senior |
|---|---|
| Focuses on "what" and "how" — implementation details | Focuses on "why" and "what if" — system-level consequences |
| Duplicates functionality; misses reuse opportunities | Recognizes patterns; extends existing abstractions |
| Operates by trial and error | Distinguishes incidental code from foundational logic |

**Ranked Recursive Summarization (RRS)**

Treat the codebase as a tree, not flat files. Build understanding bottom-up — files first, then directories, then the root:

```python
def rrs(node, context=""):
    if is_file(node):
        chunks = split_into_chunks(read_file(node))
        return summarize(rank_by_importance(chunks, context))
    return summarize([rrs(child, context) for child in node.children])
```

Rank leaf chunks by importance before summarizing. Each parent summary is built from already-compressed children.

**Prismatic RRS (PRRS) — multi-lens analysis**

A single importance ranking is context-dependent. Run RRS through multiple lenses:

```python
LENSES = ["architecture", "data_flow", "security", "patterns", "dependencies"]

def prrs(root):
    return {lens: rrs(root, context=f"Analyze importance from {lens} perspective")
            for lens in LENSES}
```

Each lens surfaces different load-bearing code: `architecture` → structure; `data_flow` → coupling; `security` → trust boundaries; `patterns` → reuse opportunities; `dependencies` → blast radius of changes.

**Without tooling**

1. Write a summary for each top-level directory describing its role and key abstractions.
2. Generate a lens-specific doc for each concern (e.g. `ARCHITECTURE.md`, `DATA_FLOW.md`).
3. Include the relevant lens doc in context before generating code for that concern.
4. Improve manual summaries with an LLM — iterate until the summary would catch pattern violations.

## Structure (Data-Centric Order)
```
imports        # sorted by use-case category; deduplicated
constants      # single source of truth; define once, use everywhere
classes        # entities; member functions = accessor API to predicates
functions      # utility predicates; shared across classes
main           # orchestration; assert checkpoints here, not in classes; return data
```
Order vars and functions in the order they are called during processing.

## Scope
Touch only what the change requires. Whole functions, never snippets — in full or it didn't happen. Single contiguous codeblock per instruction set. Finding all the spots that need updating is your job.

## Naming
No temporal or subjective adjectives — not optimized, enhanced, revised, v2, _new. Update the original. Clear, descriptive names without redundant qualifiers.

## Docstrings
Document purpose, preconditions, and failure modes. Not boilerplate.

## Stack Defaults
- Checkpointing: `sqlite`
- APIs: `fastapi`
- Validation: `pydantic`
- Prototyping: `gradio` or `streamlit`
- MCP: `fastmcp`

## Data Sources
- Prices: stooq via `pandas_datareader` — `pdr.DataReader(tickers, 'stooq')`
- Fundamentals: FMP free tier or SEC EDGAR XBRL API
- Banned: `yfinance`, Yahoo Finance

## Change Sequence
Remove dead or redundant code first. Add new features second.

## Checkpoints
Heavy computations use load-if-exists. Prefer sqlite.
```python
if checkpoint_exists(path):
    data = load(path)
else:
    data = derive()
    save(data, path)
```

## Contracts at Interfaces
- **Require** — preconditions caller must meet
- **Guarantee** — postconditions implementation promises
- **Maintain** — invariants that hold throughout
- **Assert** — validate at execution points; place in main, not in class functions

Assertions at pipeline checkpoints. Transformations must be reversible.

## Try/Except Discipline
- Critical paths: fail fast — no try/except
- Unit tests: fail fast — no try/except with fallbacks
- Non-critical paths: try/except acceptable

## Error Schema
Check for: rogue n/a, duplicate keys, missing fields, wrong joins, off-by-one bounds, type mismatches, duplicate function definitions.

## Refactor Pass Sequence
- **Pass 1 (within file):** imports top → classes → functions → constants → main; order by call sequence
- **Pass 2 (across files):** deduplicate; merge similarly-named functions; main to last
- **Pass 3 (optional):** consolidate predicates; convert duplicated logic to classes
