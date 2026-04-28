# Task

## Execution Contract
- required_outputs:
  - updated `agentic_kg_memory\SKILL.md` with the llm-wiki compiled-memory and maintenance-loop behaviors absorbed into the live contract
  - updated `gist-retriever\SKILL.md` with the lighter markdown/index-first retrieval progression absorbed into the live contract
  - updated `memory-bank\SKILL.md` with a sharper boundary against compiled corpus/wiki memory
  - updated `README.md` describing the absorption of llm-wiki features into existing skills while preserving `integrate\` as concept intake
  - `.react_agent\recon.md`, `.react_agent\plan.md`, `.react_agent\progress.md`, and `.react_agent\evidence.md`
- budget:
  - 4 subtasks
  - repo-doc edits only
- permission_scope:
  - may modify `README.md`
  - may modify `agentic_kg_memory\SKILL.md`
  - may modify `gist-retriever\SKILL.md`
  - may modify `memory-bank\SKILL.md`
  - may create/update files under `.react_agent\`
  - may read the original staged llm-wiki source if it still exists, but the repo must not depend on that path after absorption
- completion_conditions:
  - `agentic_kg_memory\SKILL.md` explicitly captures llm-wiki's compiled persistent knowledge layer, ingest/query/lint loop, and write-back semantics without violating its existing scope
  - `gist-retriever\SKILL.md` explicitly captures the lightweight markdown/index-first retrieval path and optional local search progression without displacing its existing hybrid retrieval contract
  - `memory-bank\SKILL.md` explicitly distinguishes project operating memory from compiled domain/corpus wiki memory
  - `README.md` explains that llm-wiki features were absorbed into existing skills without depending on the staged `integrate\llm-wiki` path
  - the live repo no longer requires `integrate\llm-wiki\SKILL.md` to understand or preserve the absorbed behavior
  - a repo-appropriate validation artifact exists at `.react_agent\evidence.md`
- designated_output_paths:
  - `C:\Users\user\Documents\dev\skills\agentic_kg_memory\SKILL.md`
  - `C:\Users\user\Documents\dev\skills\gist-retriever\SKILL.md`
  - `C:\Users\user\Documents\dev\skills\memory-bank\SKILL.md`
  - `C:\Users\user\Documents\dev\skills\README.md`
  - `C:\Users\user\Documents\dev\skills\.react_agent\recon.md`
  - `C:\Users\user\Documents\dev\skills\.react_agent\plan.md`
  - `C:\Users\user\Documents\dev\skills\.react_agent\progress.md`
  - `C:\Users\user\Documents\dev\skills\.react_agent\evidence.md`

## Scope
In scope:
- skill-contract documentation changes
- README taxonomy/relationship updates that explain feature absorption
- execution artifacts under `.react_agent\`

Out of scope:
- creating a new live `llm-wiki\` skill unless a true ownership gap appears
- changing MCP setup, runtime code, or external tooling
- rewriting the upstream concept file as part of the absorption pass

## Risks
- overstuffing `agentic_kg_memory` with retrieval details that belong in `gist-retriever`
- blurring `memory-bank` into corpus memory instead of keeping it as project operating memory
- narrating absorption in `README.md` without making the underlying skill contracts actually own the behavior
