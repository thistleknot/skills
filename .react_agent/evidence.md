# Evidence

## Problem Statement
Absorb the llm-wiki features into the live skills, including the supplementary KnowledgeWeaver README material and the comparison document framing, without promoting `llm-wiki` as its own live branch.

## Root Cause / Key Change
The original mistake was treating `llm-wiki` as a placement problem instead of a feature-assimilation problem.

Resolution:
- `agentic_kg_memory\SKILL.md` now owns the compiler-side behaviors:
  - compiled persistent wiki layer
  - ingest/query/lint maintenance loop
  - durable query write-back
  - typed readable knowledge units
  - canonical-artifact / rebuildable-index rule
- `gist-retriever\SKILL.md` now owns the retriever-side progression:
  - markdown/index-first lookup
  - local markdown search (`qmd`-style) as the light retrieval layer
  - compiled-index retrieval as an access path, not the source of truth
- `memory-bank\SKILL.md` now explicitly excludes compiled corpus/wiki memory
- `README.md` now states the retriever/compiler/operator boundary and explains how the llm-wiki concept was absorbed into existing live skills

## Supplementary Material Integration
- KnowledgeWeaver README:
  - incorporated typed readable knowledge units
  - incorporated canonical markdown/readable artifacts as source of truth
  - incorporated rebuildable compiled index rule
- comparison document (`RAG LLM Wiki or GBrain.pdf` on disk):
  - incorporated `RAG = retriever`
  - incorporated `LLM Wiki = compiler`
  - incorporated `GBrain = operator / fat-skills orchestration`

## Validation

### File-state checks
Command:
```powershell
git --no-pager status --short
git --no-pager diff --check -- README.md agentic_kg_memory/SKILL.md gist-retriever/SKILL.md memory-bank/SKILL.md
```

Observed result:
```text
 M README.md
 M agentic_kg_memory/SKILL.md
 M gist-retriever/SKILL.md
 M memory-bank/SKILL.md
?? .react_agent/
?? integrate/
```

`git diff --check` returned no output.

### Path checks
Command:
```powershell
Test-Path 'C:\Users\user\Documents\dev\skills\integrate\llm-wiki\SKILL.md'
Test-Path 'C:\Users\user\Documents\dev\skills\llm-wiki'
```

Observed result:
```text
integrate_llm_wiki=True
root_llm_wiki=False
```

### Validation scope note
No common build/test manifest was found in the repo root via glob search for:
- `package.json`
- `pyproject.toml`
- `pytest.ini`
- `requirements*.txt`
- `.github/workflows/*`

So validation for this markdown-only task was limited to file readback, diff integrity, and path/state checks.

## Residual Uncertainty
- None for the requested doc/skill-contract scope.
- The `integrate\` directory remains untracked as concept input; that is consistent with the repo’s current intake-folder role.
- Historical evidence in this file reflects the original staging path, but the live repo no longer depends on that path.
