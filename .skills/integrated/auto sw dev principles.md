```
---

**Question:** What are the durable, reusable principles for making AI coding agents actually perform — and what are the failure modes they solve?

---
```
## Findings

**Core claim:** The failure mode is not the model — it's the workflow. Treating an LLM as a chatbot invites non-deterministic sprawl. Treating it as a compiler collapses that into a single valid path.

**1. Context is the primary lever**
- Every token of irrelevant context is an invitation for hallucination on the next turn
- Anthropic's own guidance: clear context at ~20% window usage, not at limit
- Hitting the 1M context limit is a diagnostic: something upstream is wrong

**2. Three compounding failure patterns**
- `[observed]` Context accumulation degrades output quality monotonically as session length grows
- `[observed]` Ambiguous directives ("fix this", "make it better") multiply valid interpretations → the model picks one arbitrarily
- `[observed]` AI-maintained to-do lists allow the AI to declare completion without proof; it will skip steps when context pressure rises
- `[inferred]` All three compound: a long session with ambiguous prompts and self-tracked todos is near-guaranteed to drift

**3. The compiler mindset (state machine over conversation)**
- Replace conversational loop with: strict input → validated process → deterministic output
- State transitions require external tool validation, not AI self-assessment
- Each gate is binary (pass/fail), not a question to the model
- Concrete implementation: scripts that check file existence, linting, test presence, git diffs on protected files
- While-loop pattern: `while tool_says_work_remains: do_next_item` — the AI never decides what's left

**4. Anti-gaming the test-driven step**
- AI can pass tests by modifying the tests rather than implementing the feature
- Countermeasure: track git diffs on test files; if test files were touched during implementation, flag it
- Separate sub-agent for validation that has no knowledge of what was supposed to be implemented — it can only check structural properties (no hard-coded values, test coverage, etc.)

**5. Orchestrator / sub-agent pattern**
- Orchestrator: coordinates, never executes; stays below ~50–100K tokens
- Sub-agents: isolated context windows, pre-configured system prompts, scoped tool access
- Key property: sub-agents do not share context with the orchestrator or each other → automatic context isolation between tasks
- Parallel execution is available but requires explicit instruction
- Sub-agents are reusable via slash commands; encode once, invoke always

**6. Model assignment across the pipeline**
- Planning / architecture → large model (more reasoning, larger context)
- Implementation sub-agents → smaller/cheaper model (thinking is done; it just needs to write code)
- Local/open-source models (Ollama, Qwen, etc.) viable for implementation steps; not validated for planning

**7. What cursor (and similar) can't do**
- Sub-agents require platform support; Cursor doesn't have it as of this session
- Claude Code, Gemini CLI, GitHub Copilot (VS Code), Kiro confirmed to support sub-agents
- Codex does not

---

## Entities Involved

| Entity | Role |
|---|---|
| Claude Code | Primary platform discussed; supports sub-agents, slash commands, `.claude/` agent configs |
| Raindrop MCP | State-machine-as-MCP product built on these principles |
| Gemini CLI | Open-source alternative; sub-agent support; extensible model routing |
| QwenCoder / CoinCoder | Open-source forks supporting model swapping |
| Claude Router | Mechanism to redirect Claude Code to non-Anthropic models |
| `.claude/` agent markdown files | Sub-agent config: name, description, tools, model, system prompt |
| Git diffs | Deterministic validation primitive for catching test tampering |
| External task tracker | Required replacement for AI-maintained to-do lists |

---

## Lessons

1. **Self-validation is structurally broken.** If the agent writes the code, runs the tests, and decides it's done — all in one context — it can rationalize its way to false completion. Always use a separate agent or script to validate.

2. **The context window is a pressure gauge, not a resource to use up.** If it's filling, the process is wrong. Healthy sessions keep the orchestrator lean; sub-agents burn tokens on actual work and then disappear.

3. **Ambiguity at input multiplies error at output.** Every "fix this" or "make it better" without a specific target is a branch point in a non-deterministic system. Every branch is a potential hallucination path.

4. **Tools beat prompts for enforcement.** A prompt that says "do not create mock implementations" is a suggestion. A validation script that detects hard-coded values and blocks the next state transition is a gate. Gates win.

5. **Sub-agents aren't just parallelism — they're context hygiene.** The main benefit isn't speed; it's that each sub-agent starts clean, without the accumulated bias of failed prior attempts.

6. **Model sizing follows reasoning load, not task importance.** Architecture and planning need the big model. File-level implementation after the plan exists is a pattern-completion task — smaller models handle it with no quality loss.

7. **The PRD step can be chatty; everything after it should not be.** Exploration is appropriate when figuring out what to build. Once you know, lock it down.

---

## Open Questions

- At what context budget does orchestrator quality degrade? The "50–100K tokens" figure is asserted, not validated with ablations.
- How does the parallel sub-agent pattern handle shared file writes (race conditions on the same module)?
- What is the minimum viable external task tracker? An MD file partially works; a proper tool is better — but neither the speaker nor the transcript names a concrete lightweight option.
- Does the validation sub-agent pattern (separate agent checks for hard-coded values) generalize to semantic correctness, or only structural properties?
- Model routing in Claude Code is opaque; the Claude Router approach is mentioned but not detailed.