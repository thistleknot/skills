---
name: ollama-harness-paradigm
description: Compare local Ollama behavior across open-webui, opencode, hermes, and Pi using the retained four-harness matrix and dated probe evidence. Use for cross-harness compatibility review, not generic wiring or diagnosis.
status: active
last_validated: 2026-10-31
supersedes: []
validation_method: source consolidation review; retained dated probe evidence
---

# Ollama Harness Paradigm

Use this skill to compare behavior across the four documented harnesses. For the canonical endpoint, thinking, roles, Modelfile, and diagnosis contract, use [local-llm-harness-wiring](../local-llm-harness-wiring/SKILL.md). This matrix is an evidence record, not a guarantee for later model or harness versions.

## The four-harness matrix

| Harness | Endpoint | Reads reasoning from | Thinking knob | Roles |
|---|---|---|---|---|
| **open-webui** | native `/api/chat` | `thinking` | app default (native) | system/user/assistant |
| **opencode** | `/v1` (often LAN IP) | `reasoning` | per-model `reasoning:{effort,enabled,exclude}` via `@ai-sdk/openai-compatible` | user/assistant + `system` as metadata |
| **hermes** | `/v1` localhost | `reasoning` + `reasoning_content` (both preserved) | reads both fields; thinking-prefill retry | system/user/assistant/tool; `system→developer` only for GPT-5/Codex names |
| **pi** | `/v1` localhost | `reasoning` (`compat.thinkingFormat:"qwen"`) | per-model `thinkingLevelMap` + `settings.defaultThinkingLevel` | `system` (`compat.supportsDeveloperRole:false`) |

Historical interpretation: open-webui used the native endpoint, so its UI received `thinking` directly. The `/v1` harnesses required endpoint-specific reasoning-field handling and thinking activation. Confirm this again when the model, Ollama, or harness version changes.

## Measured probe results — historical

Measured on this box on 2026-06-28: Ollama 0.30.7, qwen3.5 family, and ornith. Full table in `[[pi-config]]` `FINDINGS.md`.

- **Endpoint → field name confirmed both ways.** Native `/api/chat` returned `message.thinking`; `/v1` returned `choices[].message.reasoning`. Same model and prompt, different field.
- **The dominant measured failure was thinking-OFF leakage.** qwen-reasoning, qwopus, and rebuilt ornith emitted literal `<think>…</think>` in `content` with thinking disabled. With thinking enabled, the same calls split cleanly into an answer and thinking field. This is historical evidence, not a substitute for a probe on a new version.
- **Tool-calls and roles were not the measured problem.** `tool_calls=1` returned on both endpoints for the qwen-family models; `system` and `developer` roles were both accepted over `/v1`.
- **Explicit Modelfiles standardized behavior.** Pre-rebuild ornith used a minimal Modelfile and differed from sibling models; rebuilding with the explicit qwen template made its thinking-on/off behavior match the family. See `[[pi-config]]` for the rebuild recipe.

## Boundary

Use `local-llm-harness-wiring` to diagnose or repair a concrete integration. Use `pi-config` to change Pi configuration or rebuild a model. Keep this skill for cross-harness comparison and dated measured evidence.

## Archive

The superseded generic connection and diagnosis guidance is preserved verbatim in [archive/2026-10-31-SKILL.md](archive/2026-10-31-SKILL.md). It was reduced because that guidance duplicated `local-llm-harness-wiring`.

<!-- consolidation:see-also:start -->
## See Also
[[pi-config]]  [[pi]]  [[ollama-structured]]  [[substrate-selection]]  [[local-llm-harness-wiring]]
<!-- consolidation:see-also:end -->
