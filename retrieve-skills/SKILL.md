---
name: retrieve-skills
description: >
  Retrieval-augmented skill routing. Use at the start of any non-trivial task
  to check whether specialized instructions exist in the local skill store.
  Calls the retrieve-skills MCP server to find relevant skills by semantic
  similarity, then reads full instructions for any skill worth applying.
inclusion: auto
---

# Retrieve Skills

## When to Use

At the start of any task that might benefit from specialized instructions:
- Building features, fixing bugs, writing specs
- Any domain-specific work (PDF processing, MLflow, debugging protocols, etc.)
- When you're unsure whether relevant guidance exists

## How to Use

1. Call the `retrieve_skills` MCP tool with a short task description
2. Review the results — PASS means the skill cleared the relevance gate
3. For any PASS skill, call `read_skill(name)` to get full instructions
4. Apply the instructions if relevant to the current task

## Tools Available (via MCP server "retrieve-skills")

- `retrieve_skills(query, k=3)` — semantic search over ~166 stored skills
- `read_skill(name)` — get full SKILL.md body for a specific skill

## Notes

- Skills that PASS the gate are highly relevant (ColBERT reranker + margin gate)
- CANDIDATE skills are below the gate but might still be useful — use judgment
- The store covers: coding patterns, debugging protocols, spec workflows, ML pipelines, and more
