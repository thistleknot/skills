---
name: pi-ollama-config
description: Configure the pi coding agent (@earendil-works/pi-coding-agent) to use local Ollama models via ~/.pi/agent/models.json. Use when wiring Ollama, LM Studio, vLLM, or any OpenAI-compatible local server into pi, adding/removing local models, or debugging why a local model won't appear or respond in pi's /model picker.
status: active
last_validated: 2026-06-27
supersedes: []
superseded_by: null
validation_method: session
---

# Pi — Ollama / Local Model Configuration

Configure pi's model registry so local Ollama models appear in the `/model` picker and run correctly. This is about **pi runtime configuration** (`models.json`), not about pi-as-a-harness (see [[pi]]) and not about structured JSON output from Ollama (see [[ollama-structured]]).

## Where It Lives

- **File:** `~/.pi/agent/models.json` (Windows: `C:\Users\user\.pi\agent\models.json`)
- **Reload:** the file is re-read every time you open `/model` (Ctrl+L). No restart needed.
- **Persistence:** `~/.pi/agent/` survives uninstall, so config is durable.
- **Install pi:** `npm install -g --ignore-scripts @earendil-works/pi-coding-agent`

## File Shape

Top-level `providers` object. Each provider key (e.g. `ollama`) holds connection fields plus a `models` array.

```json
{
  "providers": {
    "ollama": {
      "api": "openai-completions",
      "apiKey": "ollama",
      "baseUrl": "http://localhost:11434/v1",
      "compat": { "supportsDeveloperRole": false },
      "models": [
        { "id": "llama3.1:8b" },
        { "id": "qwen2.5-coder:7b" }
      ]
    }
  }
}
```

That minimal block is enough to make both models selectable in `/model`.

## Provider Keys

| Key | Purpose | Ollama value |
|---|---|---|
| `baseUrl` | API endpoint | `http://localhost:11434/v1` (note the `/v1`) |
| `api` | wire protocol | `openai-completions` |
| `apiKey` | auth token | `"ollama"` — a placeholder; Ollama ignores it but pi requires *some* value |
| `compat` | compatibility flags | `{ "supportsDeveloperRole": false }` for local servers |
| `headers` | extra HTTP headers | optional; same value resolution as `apiKey` |
| `models` | model definitions | array, see below |
| `modelOverrides` | tweak built-in models by id | optional |

Other supported `api` values (for non-Ollama local servers): `anthropic-messages`, `google-generative-ai`, `openai-responses`.

## Model Keys

Only `id` is required. Everything else has a default.

| Key | Default | Notes |
|---|---|---|
| `id` | (required) | Exact model tag passed to the API — must match `ollama list` exactly |
| `name` | — | Human label shown in the picker and used for matching |
| `reasoning` | `false` | `true` enables extended thinking |
| `input` | `["text"]` | Use `["text","image"]` for vision models |
| `contextWindow` | `128000` | Set to the model's real context (e.g. `262144`) |
| `maxTokens` | `16384` | Max output tokens |
| `cost` | — | `{ "input":0, "output":0, "cacheRead":0, "cacheWrite":0 }` — set 0 for local |
| `thinkingLevelMap` | — | Maps pi levels to provider values (see Qwen section) |
| `api` | inherits provider | Override per-model if needed |
| `compat` | inherits provider | Per-model compatibility override |

## apiKey / headers Value Resolution

The `apiKey` and `headers` values are resolved, not just used literally:

- `"$VAR"` or `"${VAR}"` → interpolates an environment variable
- `"!command"` → runs the shell command, uses stdout
- `"$$"` → literal `$`; `"$!"` → literal `!`
- anything else → used as a literal string

For Ollama just use the literal `"ollama"`.

## Qwen3 Thinking Models

Qwen3-family reasoning models need a thinking map plus the Qwen thinking format. Full example:

```json
{
  "_launch": true,
  "id": "qwen3.5-reasoning-oc:9b",
  "contextWindow": 262144,
  "input": ["text", "image"],
  "reasoning": true,
  "thinkingLevelMap": {
    "off": null,
    "minimal": "low",
    "low": "low",
    "medium": "medium",
    "high": "high",
    "xhigh": "max"
  },
  "compat": { "thinkingFormat": "qwen" }
}
```

`off: null` means "thinking unsupported at this level." For suppressing Qwen chain-of-thought at *call time* (scripts, not pi config) see [[ollama-structured]].

## Procedure: Configure From Installed Models

1. List what Ollama actually has: `ollama list`. Copy the tag column verbatim (e.g. `qwen2.5-coder:7b`).
2. Open `~/.pi/agent/models.json`. If absent, create it with the minimal block above.
3. Add one `{ "id": "<exact-tag>" }` per model under `providers.ollama.models`.
4. For each model, set `contextWindow`, `input`, and `reasoning` to match the model's real capabilities. Coder/chat models: `input: ["text"]`. Vision models: `input: ["text","image"]`.
5. Confirm Ollama is serving: `curl http://localhost:11434/v1/models` should list your tags.
6. In pi, open `/model` (or Ctrl+L) and select the model. The list reloads on open, so no restart.

## Validation Checklist

- [ ] `baseUrl` ends in `/v1`.
- [ ] `apiKey` is present and non-empty (placeholder `"ollama"` is fine).
- [ ] `compat.supportsDeveloperRole` is `false` (most local servers reject the `developer` role).
- [ ] Every `id` matches an `ollama list` tag **character-for-character**.
- [ ] **No duplicate `id`s within a provider.** Pi merges models by `id`; a later duplicate silently overrides the earlier one, so a second entry with the same `id` makes the first disappear.
- [ ] JSON is valid (no trailing commas). A parse error means pi falls back to built-in models only and your local models vanish from `/model`.

## Failure Modes

| Symptom | Cause | Fix |
|---|---|---|
| Model not in `/model` list | id mismatch, duplicate id, or JSON parse error | Match `ollama list` exactly; remove duplicate ids; validate JSON |
| 404 / connection refused | Ollama not running or wrong `baseUrl` | Start `ollama serve`; ensure `baseUrl` is `http://localhost:11434/v1` |
| Empty / truncated replies on a Qwen model | thinking consumed the token budget | Add `thinkingLevelMap` + `compat.thinkingFormat: "qwen"`; raise `maxTokens` |
| 400 about `developer` role | local server rejects `developer` role | Set `compat.supportsDeveloperRole: false` |
| Auth error despite local server | `apiKey` missing | Add any non-empty placeholder, e.g. `"ollama"` |

## See Also

- [[pi]] — pi as a delegated external harness (different concern: how pi is used, not how its models are wired)
- [[ollama-structured]] — schema-constrained JSON output from Ollama at call time
- [[substrate-selection]] — choosing which runtime/provider sits behind the harness boundary
