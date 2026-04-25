---
name: code
description: Code standards and implementation protocol. Use for any code generation, modification, or review task. Covers structure, naming, docstrings, stack defaults, data sources, contracts, checkpoints, error handling, and refactor sequence.
---
# Code Standards

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
