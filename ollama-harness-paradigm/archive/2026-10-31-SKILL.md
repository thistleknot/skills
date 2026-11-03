---
name: ollama-harness-paradigm
description: The cross-harness paradigm for running local Ollama models under different agent harnesses (pi, opencode, hermes, open-webui). Use when a model "works in harness X but not Y", when reasoning shows up in the wrong field or <think> tags leak, when tool-calls or roles misbehave, or when onboarding a local model so it behaves consistently everywhere. Explains what to fix on the model side (Modelfile) vs the connection side (endpoint, thinking knob, roles).
status: active
last_validated: 2026-06-28
supersedes: []
validation_method: session
---
# Ollama Harness Paradigm

Why the same local model "just works" in open-webui, behaves oddly in one harness, and needs tuning in another. The unifying rule, the four-harness matrix, and which lever to pull.

## The core rule

A model works in a harness when the harness's **(endpoint, reasoning-field, thinking-activation, roles)** tuple MATCHES the model's **(template, declared capabilities)** contract. Mismatch on any one axis is the bug. There are only two places to fix it:

- **Model side** — the Ollama **Modelfile** (`TEMPLATE`, `PARAMETER`, capabilities).
- **Connection side** — how the harness calls Ollama (**endpoint URL, thinking knob, message roles**).

## Axis 1 — Endpoint decides the reasoning field name

Ollama exposes the same models on two HTTP surfaces, and they label reasoning differently:

| Endpoint | Reasoning lands in | Think toggle |
|----------|-------------------|--------------|
| Native `http://HOST:11434/api/chat` | `message.thinking` | request `"think": true/false` |
| OpenAI-compat `http://HOST:11434/v1/chat/completions` | `choices[].message.reasoning` | via `reasoning_effort` / provider compat |

Ollama's `/v1` shim re-labels native `thinking` → `reasoning`. **A harness must read the field that matches the endpoint it dials.** Reading `content` for reasoning is the failure that surfaces as "`<think>` tags leaking into the answer."

## Axis 2 — Thinking activation

The model's `TEMPLATE` only *splits* reasoning into its own field when the request **enables thinking**. If thinking isn't activated, a reasoning model either dumps `<think>…</think>` into `content` or stalls. Each harness has its own activation knob — the job is to set it.

## Axis 3 — Roles

`/v1` callers must respect `supportsDeveloperRole`. Some models/providers want OpenAI's `developer` role; Ollama-served models generally want `system`. Sending the wrong role is a silent quality or hard error.

## The model contract (other half of the match)

`ollama show --modelfile <id>` reveals the `TEMPLATE`. A **well-formed** chat template (Qwen/ChatML family) has:
- role markers `<|im_start|>system|user|assistant … <|im_end|>`
- a tool block rendering `.Tools` and parsing `<tool_call>…</tool_call>`
- think gating: `{{ if (and $.IsThinkSet (and .Thinking …)) }}<think>{{ .Thinking }}</think>{{ end }}`
- `PARAMETER stop <|im_start|>` / `<|im_end|>`, sane `num_ctx`, sampling params

A **broken/minimal** template (e.g. just `{{ .Prompt }}`) has none of this. The model may still answer over `/v1` (Ollama falls back to the GGUF's embedded template), but tool-calling, role handling, and think-gating become inconsistent across harnesses. **Fix: rebuild the Modelfile with the proven family template** (see `[[pi-config]]` for the Ollama→pi pipeline and the rebuild recipe).

## The four-harness matrix

| Harness | Endpoint | Reads reasoning from | Thinking knob | Roles |
|---------|----------|----------------------|---------------|-------|
| **open-webui** | native `/api/chat` | `thinking` | app default (native) | system/user/assistant |
| **opencode** | `/v1` (often LAN IP) | `reasoning` | per-model `reasoning:{effort,enabled,exclude}` via `@ai-sdk/openai-compatible` | user/assistant + `system` as metadata |
| **hermes** | `/v1` localhost | `reasoning` + `reasoning_content` (both preserved) | reads both fields; thinking-prefill retry | system/user/assistant/tool; `system→developer` only for GPT-5/Codex names |
| **pi** | `/v1` localhost | `reasoning` (`compat.thinkingFormat:"qwen"`) | per-model `thinkingLevelMap` + `settings.defaultThinkingLevel` | `system` (`compat.supportsDeveloperRole:false`) |

**Why open-webui "just works":** it speaks the native endpoint, so it gets the `thinking` field its UI was built for — no `/v1` re-labeling to reconcile. The three `/v1` harnesses all see `reasoning` and each must be told (a) to read that field and (b) how to activate thinking. They are not broken — they are *configured*.

## Diagnose before you fix

Run the probe (`skills/pi-config/tools/ollama_probe.py <model>`). It hits both endpoints with thinking on/off plus a tool-call and role check, and prints where reasoning lands, whether `<think>` leaks, whether tool-calls format, and which roles are accepted. Read the table, then decide the lever:

- Reasoning leaks into `content` on the endpoint your harness uses → **connection fix**: activate thinking / read the right field.
- Tool-calls don't format or `<think>` behaves differently than a known-good sibling model → **model fix**: the Modelfile template is wrong; rebuild it.
- A role errors or degrades output → **connection fix**: flip `supportsDeveloperRole` / role mapping.

## Measured probe results

Measured on this box (Ollama 0.30.7, qwen3.5 family + ornith). Full table in `[[pi-config]]` `FINDINGS.md`.

- **Endpoint → field name confirmed both ways.** Native `/api/chat` returns `message.thinking`; `/v1` returns `choices[].message.reasoning`. Same model, same prompt, different field — purely the endpoint.
- **The dominant failure mode is thinking-OFF leakage, not the endpoint.** Every reasoning model (qwen-reasoning, qwopus, rebuilt ornith) called with thinking **disabled** emitted literal `<think>…</think>` into `content`. With thinking **enabled**, the same call produced a clean split (empty/answer `content` + populated thinking field, no leak). The model always generates `<think>`; Ollama only *extracts* it when thinking is activated. → **Activate thinking, or use a non-reasoning model, or strip `<think>` — on every harness.**
- **Tool-calls and roles are not the problem.** `tool_calls=1` returned on both endpoints for the qwen-family models; `system` and `developer` roles were both accepted over `/v1`.
- **Modelfile standardization gives cross-model uniformity.** Pre-rebuild ornith (minimal Modelfile `TEMPLATE`, GGUF-embedded template at runtime) did NOT leak on thinking-OFF — it behaved *differently* from its siblings. After rebuilding it with the explicit qwen template, it matched the family exactly (clean ON, leak OFF). Explicit templates make all models obey one contract, so one harness config covers them all. See `[[pi-config]]` for the rebuild recipe.

<!-- consolidation:see-also:start -->
## See Also
[[pi-config]]  [[pi]]  [[ollama-structured]]  [[substrate-selection]]
<!-- consolidation:see-also:end -->
