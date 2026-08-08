---
name: pi-config
description: Configure the .pi agent — register providers and models in models.json, set defaults in settings.json, and wire local Ollama models (built from Modelfiles) into pi as an OpenAI-compatible provider. Use when adding/editing pi models, onboarding a local LLM, debugging "model not found", or tuning reasoning/thinking behavior.
status: active
last_validated: 2026-06-28
supersedes: []
validation_method: session
---
# Pi Config

How to configure the `.pi` agent: file layout, provider/model schema, and the full **Ollama Modelfile → pi** pipeline. This is the *configuration* skill — distinct from `[[pi]]`, which describes pi-as-delegated-harness.

> Docs: https://pi.dev/docs (Settings, Custom Models, Custom Providers). Field details below were validated against a live `pi 0.80.2` + Ollama install.

## File Layout

Pi reads JSON config from two scopes. **Project overrides global**; nested objects are *merged* (per-key), not replaced.

| File | Scope | Purpose |
|------|-------|---------|
| `~/.pi/agent/settings.json` | global | defaults, packages, theme, thinking level |
| `~/.pi/agent/models.json`   | global | provider + model registry |
| `~/.pi/agent/auth.json`     | global | OAuth/login tokens (managed by `/login`) |
| `.pi/settings.json`         | project | per-repo overrides of any settings key |

On Windows, `~` = `C:\Users\<you>`. Edit files directly, or use `/settings` (settings) and `/login` (auth) inside a pi session.

## The Ollama → Pi Pipeline

Local Ollama models reach pi through Ollama's **OpenAI-compatible endpoint** at `http://localhost:11434/v1`. Three steps:

### 1. Build the model from a Modelfile

A Modelfile defines a named, reusable model: base weights + chat template + sampling params + system prompt.

```dockerfile
# qwen3.5-reasoning-oc.Modelfile
FROM hf.co/Jackrong/Qwen3.5-9B-Claude-4.6-Opus-Reasoning-Distilled-v2-GGUF:Qwen3.5-9B.Q5_K_M.gguf

# Sampling
PARAMETER temperature 0.6
PARAMETER top_p 0.95
PARAMETER num_ctx 262144          # context window — must match contextWindow in models.json

# Optional: bake in a system prompt / template
SYSTEM """You are a careful reasoning assistant."""
# TEMPLATE """..."""              # only if overriding the base chat template
```

```bash
ollama create qwen3.5-reasoning-oc:9b -f qwen3.5-reasoning-oc.Modelfile
ollama list                                   # confirm the tag exists
ollama show --modelfile qwen3.5-reasoning-oc:9b   # inspect template/params of an existing model
```

The Ollama **tag** (`qwen3.5-reasoning-oc:9b`) is the `id` you reference in pi. They must match exactly.

### 2. Register the provider + model in `models.json`

```json
{
  "providers": {
    "ollama": {
      "api": "openai-completions",
      "apiKey": "ollama",
      "baseUrl": "http://localhost:11434/v1",
      "compat": { "supportsDeveloperRole": false },
      "models": [
        { "id": "qwopus-coder-oc:9b", "contextWindow": 262144, "input": ["text"] },
        {
          "id": "qwen3.5-reasoning-oc:9b",
          "_launch": true,
          "contextWindow": 262144,
          "input": ["text", "image"],
          "reasoning": true,
          "thinkingLevelMap": {
            "off": null, "minimal": "low", "low": "low",
            "medium": "medium", "high": "high", "xhigh": "max"
          },
          "compat": { "thinkingFormat": "qwen" }
        }
      ]
    }
  }
}
```

### 3. Make it the default in `settings.json`

```json
{
  "defaultProvider": "ollama",
  "defaultModel": "qwen3.5-reasoning-oc:9b",
  "defaultThinkingLevel": "medium",
  "theme": "dark",
  "packages": [
    "npm:@ollama/pi-web-search",
    "npm:pi-subagents",
    "npm:pi-memory",
    "npm:pi-interactive-shell"
  ]
}
```

## Multi-Model Orchestrator / Doer Split

To run a **light reasoning model as orchestrator** and delegate implementation to a **heavier coder model**, you don't switch models manually — you pin a subagent to its own model. Per-subagent model selection is supported by `pi-subagents` via frontmatter.

**1. Register every model you want switchable** in `models.json` (so `/model` and subagent `model:` can reach them). Register at both `9b` and `4b` sizes to A/B efficiency.

**2. Set the orchestrator as the default** in `settings.json` — e.g. `"defaultModel": "qwen3.5-reasoning-oc:4b"`. A 4b reasoning model is often enough for planning/routing while the 9b coder does the heavy edits.

**3. Pin a doer subagent to the coder model.** User-scope agents live in `~/.pi/agent/agents/*.md` (or `~/.agents/`); project agents in `<project>/.pi/agents/`. The model reference is `provider/id`:

```markdown
---
name: coder
description: Implementation/doer subagent — writes and edits code.
model: ollama/qwopus-coder-oc:9b
fallbackModels: ollama/qwopus-coder-oc:4b
thinking: low
tools: read, grep, find, ls, bash, edit, write, contact_supervisor
systemPromptMode: replace
defaultContext: fork
---
You are `coder`: the single writer thread. Turn the approved plan into narrow, correct edits...
```

Subagent frontmatter keys that matter here: `model` (`provider/id`; `false`/empty = inherit orchestrator's), `fallbackModels` (comma-separated), `thinking` (`off`…`xhigh`), `tools`, `systemPromptMode` (`replace`/`append`), `defaultContext` (`fork` isolates context). pi warns at load if `model` isn't in the registry.

**Result:** orchestrator (reasoning-4b) plans → delegates to `coder` (qwopus-9b) → coder returns a structured result. This mirrors the planner/executor pattern but on local weights. Manual `/model` switching still works for ad-hoc cases; the subagent pin is for automatic delegation.

> Reasoning vs vision: a model's `input` and `reasoning` must match the weights. Qwen3.5 reasoning/coder GGUFs are vision-capable (`["text","image"]`); Ornith-1.0-9B is text-only (`["text"]`). All are qwen-arch → `thinkingFormat: "qwen"`. 4b variants cap context at `131072` (their Modelfile `num_ctx`), 9b at `262144`.

## Provider Schema (`models.json`)

| Field | Meaning |
|-------|---------|
| `api` | streaming impl. `openai-completions` for Ollama/LM-Studio/most OpenAI-compatible servers. Others: `openai-responses`, `anthropic-messages`, `mistral-conversations`, `google-generative-ai`. |
| `apiKey` | literal string, `$ENV_VAR`, or `!command`. Ollama ignores it — any placeholder (`"ollama"`) works. |
| `baseUrl` | endpoint. Ollama: `http://localhost:11434/v1` (note the `/v1`). |
| `authHeader` | `true` adds `Authorization: Bearer <apiKey>`. Omit for Ollama. |
| `headers` | extra request headers. |
| `compat` | provider-wide compatibility tweaks (see below). |
| `models` | array of model entries. |

## Model Schema (entries under `models`)

| Field | Meaning |
|-------|---------|
| `id` | **must equal the Ollama tag** (`name:tag`). |
| `contextWindow` | token window. Keep ≤ the Modelfile's `num_ctx` or Ollama silently truncates. |
| `input` | modalities: `["text"]`, or `["text","image"]` for VLMs (e.g. Qwen3-VL). |
| `reasoning` | `true` exposes thinking controls for the model. |
| `thinkingLevelMap` | maps pi's levels (`off/minimal/low/medium/high/xhigh`) to the model's native effort tokens. `null` disables thinking at that level. |
| `maxTokens` | cap on output tokens (optional). |
| `cost` | `{input,output,cacheRead,cacheWrite}` per-token; set to `0` for local models so dashboards read $0. |
| `name` | optional display label. |
| `_launch` | marks the entry pi auto-launches/pre-warms on startup. |

### `compat` options (provider or model level)

| Key | Use |
|-----|-----|
| `supportsDeveloperRole` | `false` → pi sends `system` instead of OpenAI's `developer` role. Set `false` for Ollama. |
| `thinkingFormat` | how thinking is encoded: `qwen`, `qwen-chat-template`, `openai`, `openrouter`. Qwen reasoning GGUFs → `qwen`. |
| `supportsReasoningEffort` | provider accepts a `reasoning_effort` field. |
| `maxTokensField` | use `max_tokens` instead of `max_completion_tokens`. |
| `requiresToolResultName` | some servers require a name on tool results. |
| `cacheControlFormat` | e.g. `anthropic` prompt-cache markers (not relevant for Ollama). |

## Key `settings.json` Fields

| Field | Meaning |
|-------|---------|
| `defaultProvider` / `defaultModel` | startup model. |
| `defaultThinkingLevel` | `off`…`xhigh`; routed through the model's `thinkingLevelMap`. |
| `hideThinkingBlock` | suppress thinking output in the UI. |
| `packages` | npm/git extensions loaded at launch (web-search, subagents, memory, shell). |
| `extensions` / `skills` / `prompts` / `themes` | local resource paths. |
| `theme` | `dark`, `light`, or a custom theme. |
| `externalEditor` | command for the Ctrl+G editor. |
| `quietStartup` | hide the startup banner. |

## Verify

```bash
ollama ps                       # is the model loaded / will it load?
pi --version                    # confirm CLI present (validated: 0.80.2)
# In a pi session:
#   /model                      → should list ollama models; pick one
#   send a prompt               → confirms baseUrl + tag + template all align
```

Quick endpoint sanity check (proves Ollama's OpenAI shim, independent of pi):

```bash
curl http://localhost:11434/v1/chat/completions -H "Content-Type: application/json" \
  -d '{"model":"qwen3.5-reasoning-oc:9b","messages":[{"role":"user","content":"ping"}]}'
```

## Failure Modes

- **"model not found" / empty `/model` list** — the `id` in `models.json` doesn't match an `ollama list` tag exactly (tag, casing, `:size`), or Ollama isn't running.
- **Connection refused** — wrong `baseUrl` (missing `/v1`, wrong port) or `ollama serve` not up.
- **Thinking tags leak into output** (`<think>…`) — `compat.thinkingFormat` is wrong for the model, or `reasoning` is `false` while the template still emits think blocks. For Qwen reasoning GGUFs use `thinkingFormat: "qwen"`.
- **Context truncation / forgotten content** — `contextWindow` exceeds the Modelfile `num_ctx`. Rebuild the Modelfile with a larger `PARAMETER num_ctx`, or lower `contextWindow`.
- **Role errors from the server** — set `compat.supportsDeveloperRole: false`.
- **Edits ignored** — editing the project `.pi/settings.json` when you meant global `~/.pi/agent/`, or vice versa. Remember: project merges over global per-key.

## Tuning Notes (measured 2026-06-28)

- **Reasoning models leak `<think>` when thinking is OFF.** Measured across qwen-reasoning-9b, qwopus-9b, and ornith: calling a reasoning model over `/v1` or `/api/chat` with thinking disabled puts literal `<think>…</think>` in `content`. Keep `reasoning: true` + a sane `defaultThinkingLevel` (≥`low`) for reasoning models so Ollama extracts thinking into the `reasoning` field instead. The full cross-harness analysis lives in `[[ollama-harness-paradigm]]`.
- **Orchestrator thinking budget.** A 4b reasoning orchestrator on `defaultThinkingLevel: medium` did not converge a delegated coding task in 600s. Drop the orchestrator to `low` and cap its `maxTokens` (e.g. 8192) so routing turns stay short; reserve deeper thinking for the coder. Mirrors opencode's orchestrator variant (`effort: low`, tight output cap).
- **Match `contextWindow` to the Modelfile `num_ctx`.** Ornith with an unset `num_ctx` ran ~4× slower and timed out on `/v1` tool-calls; rebuilding with explicit `num_ctx 262144` fixed both. 4b qwen variants cap at `131072`.
- **Rebuild bare Modelfiles for cross-harness consistency.** A model whose `ollama show --modelfile` TEMPLATE is just `{{ .Prompt }}` runs on its GGUF-embedded template — it works but behaves *differently* from siblings. Rebuild it with the family template (recipe: copy the proven model's `TEMPLATE`+`PARAMETER`s, swap the `FROM` to the target GGUF) so one harness config covers every model.
- **`pi -p` needs a TTY/pipe on stdout — do NOT redirect to a file.** `pi -p ... > log 2>&1` hangs indefinitely (zero output, killed by timeout); `pi -p ... 2>&1 | tail` (or `| cat`) works and returns normally. Many hours were lost chasing a phantom "model/context" bug that was actually this harness artifact. When scripting pi, always pipe.
- **Orchestrator/doer split: the doer works, the 4b-orchestrated delegation does not (yet).** Direct `pi --model qwopus-coder-oc:9b` reliably writes+runs files (~3–4 min/task). But 4b-orchestrator → `coder` subagent delegation, while it *fires*, fails to converge: the coder subagent returned a plan instead of edits, the orchestrator invented a non-existent agent, then **falsely reported "Implementation Complete" with no file written.** Always verify the actual artifact after a delegated run — local small-model orchestrators can hallucinate success. For now prefer driving the coder directly over 4b delegation. See `[[avoid-overconfident-wrong]]`, `[[keep-finger-on-model-outputs]]`.

## Boundary

- This skill owns **pi configuration files** (models/settings/auth) and the **local-model onboarding** pipeline.
- `[[pi]]` owns the runtime *role* of pi (delegated harness under an outer orchestrator). Don't conflate "how pi is configured" with "what pi is for."
- Ollama Modelfile authoring beyond what's needed to register a model (advanced templates, adapters, quantization) is Ollama's domain, not pi's.

<!-- consolidation:see-also:start -->
## See Also
[[ollama-harness-paradigm]]  [[pi]]  [[ollama-structured]]  [[substrate-selection]]
<!-- consolidation:see-also:end -->
