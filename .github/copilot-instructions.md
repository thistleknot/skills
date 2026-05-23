# Skills Repository — Copilot Instructions

## Repository Purpose

This is a composable skill library for agentic coding, memory, retrieval, tuning, and orchestration. Each skill lives in its own folder as `SKILL.md`. Skills are invoked by name inside the Copilot CLI `/skill` command.

## Skill Graph Architecture

Skills are organized into five branches (see README.md for the full AST):

- **execution/** — `react-agent` (outer OS), `reasoning`, `code`, `debugging`, `validation`, `architecture`
- **orchestration/** — `agentic-harness` (pipeline control), `checklist`, `continuity-log`, `deep-research`, `timeout-guard`
- **memory/** — `memory-bank` (project state), `todo`, `agentic_kg_memory` (semantic graph), `gist-retriever`, `kg_ontology`, `request-intent-resolution`
- **tuning/** — `hyper-parm_tuning`, `optuna-nested-cv`, `mlflow`, `representation-pipeline`, `stratified-quota-sampling`
- **learning/** — `deep-q-rl`

### Critical Relationships

1. `react-agent` is the outer execution OS. All other skills are invoked from inside it.
2. `agentic-harness` is the multi-framework stationmaster (OpenClaw, Claude Code, OpenCode, GitHub Copilot CLI). It routes, gates, and reconciles pipeline work.
3. `memory-bank` = project operating state (what changed, what matters next). `agentic_kg_memory` = semantic evidence graph (what the corpus means). Never conflate them.
4. `checklist` is a subskill of `agentic-harness` — LLM-as-judge findings about artifacts, not a todo tracker.
5. `continuity-log` preserves compact-safe distilled state between long turns and compactions.
6. `gist-retriever` is the retrieval sub-skill under `agentic_kg_memory`.

## Skill File Structure

Every skill folder contains:
- `SKILL.md` — behavioral contract and trigger conditions (the API surface)

Complex skills may also include:
- `DESCRIPTION.md` — why it exists, when to invoke it
- `ARCHITECTURE.md` — how it works, data flow, design decisions
- `HISTORY.md` — milestones, lessons learned, known gaps

When authoring a new skill, `SKILL.md` is mandatory; the others are added when the skill becomes complex enough to need its own onboarding story.

## `integrate\` Is Volatile

`integrate\` is a concept intake folder, not a branch in the live skill graph. Concepts staged there are candidates waiting to be absorbed into live skills — they are not first-class skills and must not be treated as one. Promote intentionally.

## Memory Bank Protocol

### Foreign-repo guard

These instructions apply to the `C:\Users\user\Documents\dev\skills` repository. When
working in any other repo, do not force the skills repo memory-bank workflow, do not
look for a local memory bank there, and do not front-load memory-bank discovery unless
the user explicitly asks for that continuity layer.

At the start of every session, read all six memory bank files in order before acting:
1. `~/memory-bank/projectbrief.md`
2. `~/memory-bank/productContext.md`
3. `~/memory-bank/activeContext.md`
4. `~/memory-bank/systemPatterns.md`
5. `~/memory-bank/techContext.md`
6. `~/memory-bank/progress.md`

Update `activeContext.md` and `progress.md` after any significant change (architectural decision, completed feature, resolved blocker).

## `.react_agent\` Workspace

Long-running tasks use `.react_agent\` as a persistent workspace (the "character sheet between sessions"):
- `task.md` — quest and win condition
- `recon.md` — what is known
- `plan.md` — intended route
- `progress.md` — current state, open items
- `evidence.md` — proof of what happened

If these files exist, read them before doing any work on a continuing task.

## Key Code Conventions

### Python Stack Defaults
- Checkpointing: `sqlite` (load-if-exists pattern)
- APIs: `fastapi`
- Validation: `pydantic`
- Prototyping: `gradio` or `streamlit`
- MCP servers: `fastmcp`
- Data prices: `stooq` via `pandas_datareader` — `pdr.DataReader(tickers, 'stooq')`
- Fundamentals: FMP free tier or SEC EDGAR XBRL API
- **Banned**: `yfinance`, Yahoo Finance

### Code Structure Order
```
imports → constants → classes → functions → main
```
Order vars and functions in the sequence they are called during processing.

### Checkpoint Pattern
```python
if checkpoint_exists(path):
    data = load(path)
else:
    data = derive()
    save(data, path)
```

### Naming
No temporal or subjective adjectives: not `optimized`, `enhanced`, `revised`, `v2`, `_new`. Update the original.

### Change Sequence
Remove dead/redundant code first. Add new features second.

### Try/Except Discipline
- Critical paths: fail fast — no try/except
- Unit tests: fail fast — no try/except with fallbacks
- Non-critical paths: try/except acceptable

### Interface Contracts
Document at every interface boundary: **Require** (preconditions), **Guarantee** (postconditions), **Maintain** (invariants), **Assert** (execution checkpoints — place in `main`, not in class methods).

## Agentic Harness Core Rule

When working on any automated pipeline or harness: **fix the mechanism, not the artifact**. Patching a single bad output without fixing the generator that produced it leaves the harness incoherent.

The coherence gate: register a `coherence` sentinel as `in_progress` before touching harness code; flip to `done` only when a full representative run completes without divergence.

## Training / ML Convention

When training a model:
- Always use a train/test split
- Run Optuna on a small subset (patience=5, up to 20 epochs) to find best hyperparameters
- Apply best Optuna params to full train (patience=20, up to 100 epochs)
- Evaluate on held-out test set at the end only

## Dialectic Operating Mode

This repository's Copilot sessions operate in dialectic mode, not assistant mode:
- Challenge framing before accepting it
- Present factual claims as `[observed]` or `[inferred]` subject-predicate-object triplets, followed by an abductive syllogism
- Lead with the answer or the uncertainty — no preamble
- When wrong: say so, fix it, move on
