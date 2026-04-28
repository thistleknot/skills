# Plan

## Subtask 1: Map llm-wiki ownership
- depends_on: none
- inputs: original llm-wiki concept material, `agentic_kg_memory\SKILL.md`, `gist-retriever\SKILL.md`, `memory-bank\SKILL.md`, `README.md`
- outputs: stable feature-to-skill ownership map in `.react_agent\recon.md`
- output_paths: `.react_agent\recon.md`
- completion_condition: `.react_agent\recon.md` lists the absorbed llm-wiki behaviors and their owning live skills
- validation: read `.react_agent\recon.md`
- rollback: overwrite `.react_agent\recon.md` with corrected ownership notes
- risk: low — documentation analysis only

## Subtask 2: Update memory-domain skill contracts
- depends_on: Subtask 1
- inputs: ownership map, `agentic_kg_memory\SKILL.md`, `memory-bank\SKILL.md`
- outputs: updated memory-domain contracts that absorb llm-wiki features without breaking scope boundaries
- output_paths: `agentic_kg_memory\SKILL.md`, `memory-bank\SKILL.md`
- completion_condition: the new sections are present by path and state the compiled-wiki behaviors and memory boundary explicitly
- validation: read the edited sections and run `git diff --check -- agentic_kg_memory/SKILL.md memory-bank/SKILL.md`
- rollback: reverse the added sections in those two files
- risk: medium — easiest place to blur boundaries if the wording is sloppy

## Subtask 3: Update retrieval contract and repo docs
- depends_on: Subtask 1, Subtask 2
- inputs: ownership map, `gist-retriever\SKILL.md`, `README.md`
- outputs: retrieval/pathway updates and repo documentation explaining feature absorption
- output_paths: `gist-retriever\SKILL.md`, `README.md`
- completion_condition: `gist-retriever\SKILL.md` describes the markdown/index-first progression and `README.md` names the live skills that inherited llm-wiki behaviors
- validation: read the edited sections and run `git diff --check -- gist-retriever/SKILL.md README.md`
- rollback: reverse the added sections in those two files
- risk: medium — README can easily overstate what the skills actually own

## Subtask 4: Validate and document evidence
- depends_on: Subtask 2, Subtask 3
- inputs: updated files, git diff output, task contract
- outputs: `.react_agent\progress.md`, `.react_agent\evidence.md`, todo status updates
- output_paths: `.react_agent\progress.md`, `.react_agent\evidence.md`
- completion_condition: `.react_agent\evidence.md` cites each completion condition from `.react_agent\task.md` with a concrete file path or command result
- validation: read `.react_agent\evidence.md`, run `git --no-pager diff --check`
- rollback: replace evidence/progress files with corrected summaries
- risk: low — closure artifact work
