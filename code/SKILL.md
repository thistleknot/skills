---
name: code
description: Code standards and implementation protocol. Use for any code generation, modification, or review task. Covers codebase exploration (RRS/PRRS multi-lens analysis), structure, naming, docstrings, stack defaults, data sources, contracts, checkpoints, error handling, and refactor sequence.
status: active
last_validated: 2026-04-28
supersedes: []
validation_method: session
---
# Code Standards

## ETHOS: Boil the Lake

AI makes completeness cheap. The marginal cost of doing something completely — all edge cases, all error paths, all tests — is near zero compared to the cost of revisiting half-finished work later. Always choose the complete implementation.

- Complete the error paths, not just the happy path.
- Write the tests, not just the feature.
- Handle the edge cases; don't leave them as TODOs.
- Flag oceans (multi-quarter rewrites) explicitly; never silently scope down a lake to a puddle.

## ETHOS: Search Before Building

Before writing new code, traverse three knowledge layers:

1. **Tried-and-true** — does this already exist in the codebase? Same function, same pattern, different file?
2. **New-and-popular** — is there a well-adopted library that covers this? Search before implementing from scratch.
3. **First-principles** — if nothing fits, build from the simplest composable primitives.

Only reach the first-principles layer when layers 1 and 2 are empty. Re-implementing a solved problem is waste.

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

## Silver-Standard SFT Dataset Generation

When using an LLM to generate training data for a smaller student model:

### Pydantic as validation gate
Every training sample must pass pydantic `model_validate` before being written.
Broken or schema-invalid samples are discarded and logged — never written with defaults.

### Two-list entailment schema
For tasks requiring the LLM to both extract facts and classify their logical role,
use two separate sets rather than one flat list:

```python
class AbductiveReasoning(BaseModel):
    entailed_facts: Set[str]     # facts that directly support the conclusion
    non_entailed_facts: Set[str] # extracted facts not used in this syllogism
    conclusion: str              # hypothesis maximising entailed_facts coverage
```

- Predicate tags (`observed` / `inferred`) apply to both sets.
- Every extracted fact must appear in exactly one set — enforce with `assert len(entailed & non_entailed) == 0`.
- The conclusion should be chosen by the LLM to **maximise** the size of `entailed_facts`.
- `Set[str]` gives deduplication; deterministic ordering is applied in post-processing.

### Deterministic ordering for training samples
Hard-code the sort key into the serialised training string before writing to disk.
Do not leave ordering to set iteration — it is non-deterministic across Python versions.

```python
records.sort(key=lambda r: (r.avg_char_pos, r.sentence_index, r.triplet_index))
```

Average character position is computed on the **original pre-clean text** so cleaning
(emojibake, normalisation) does not shift offsets:
```python
avg_char_pos = (original.find(sentence) + len(sentence) / 2)
```

### Training output format
Include all reasoning layers in `output_text`, not just the conclusion:

```
[ENTAILED]
subject | predicate (observed|inferred) | object
...
[NON-ENTAILED]
subject | predicate (observed|inferred) | object
...
[CONCLUSION]
The abductive hypothesis.
```

Non-entailed facts in the training target teach the student model which observations
exist but are not load-bearing — a richer epistemics signal than entailed-only output.

### Pre-processing order matters
For quotes / natural language input: `emojibake.fix(text)` **before** `nltk.sent_tokenize`.
Encoding artifacts produce malformed sentence boundaries if tokenization runs first.

---

## Context Engineering

Structuring code, files, prompts, and open tabs to maximise LLM context effectiveness.
The quality of the context window is as important as the quality of the model.

### AGENTS.md / copilot-instructions.md Authorship

The primary context injection mechanism. Write these files as if briefing a skilled
developer who has never seen this codebase before, not as internal notes.

**Required sections:**
```markdown
# Project Context
One paragraph: what the repo does, what problem it solves.

# Architecture
Key components, how they connect. One sentence per component.

# Conventions
Stack defaults, naming rules, patterns this codebase uses.

# Do Not Touch
Files / patterns that must not be modified without explicit discussion.

# Quick Start
How to build, test, lint. The three commands someone runs first.
```

**Anti-patterns:**
- Writing AGENTS.md in bullet points only — prose forces you to reason about coherence
- Omitting "Do Not Touch" — agents will helpfully refactor files you need stable
- Stale AGENTS.md — update it whenever the architecture changes or a new convention is established

### Strategic Code Comments

Comments exist to narrow the interpretation space for the LLM, not to explain obvious code.

| Comment type | When to write | Example |
|---|---|---|
| **Intent comment** | Non-obvious algorithmic choice | `# BM25 not cosine here: need term-frequency weighting for short queries` |
| **Invariant comment** | State that must hold across a block | `# Entries are append-only after this point — do not sort or deduplicate` |
| **Anti-pattern comment** | Pattern that was tried and removed | `# Tried batching here: caused OOM on 32k sequences. Keep sequential.` |
| **Context comment** | Links to external spec or decision | `# See ADR-007: why we use ULID not UUID` |

Do NOT write boilerplate (`# increment counter`), redundant paraphrase (`# return the result`),
or placeholder TODO comments that will never be resolved.

### Tab / Open-File Context Management

The LLM sees what is open in the editor. Use this deliberately:

- **Before generating a component:** open the interface it must satisfy AND one
  representative sibling implementation — the LLM will infer the pattern
- **Before generating tests:** open the implementation file AND the test file for
  a similar component — sets the testing style without a prompt
- **Before a refactor:** open only the files in scope — avoid open files that
  contaminate context with irrelevant patterns

### File Structure as Context

The directory layout communicates architecture implicitly. Structure it to match
the mental model you want the LLM to have.

```
src/
  domain/          ← pure domain logic; no I/O, no framework imports
  adapters/        ← all external integrations (DB, API, filesystem)
  application/     ← use-case orchestration; wires domain + adapters
  entrypoints/     ← HTTP handlers, CLI commands; thin layer only
```

A flat `src/` with no structure forces the LLM to guess the architecture.
An explicit layer structure makes it obvious what can depend on what.

### Prompt Window Prioritisation

When the context window is finite, prioritise in this order:

1. **Active task specification** — what is being done right now
2. **Interface contracts** — the API / schema the code must satisfy
3. **Constraints** — what must not change (AGENTS.md "Do Not Touch")
4. **Examples** — one or two representative prior implementations
5. **Background** — architecture overview, project brief

Cut from the bottom if context is tight. Never cut the active task specification.

### Evidence

- awesome-copilot: `context-engineering` instructions file, `copilot-instructions-template` skill
- Anthropic Claude Code documentation: CLAUDE.md authorship guidelines (2025)
- ACE arXiv:2510.04618 — context as evolving playbook; context quality predicts agent quality
- Copilot CLI: `copilot-instructions.md` as primary context injection point
