---
name: local-llm-harness-wiring
description: Wire local Ollama models into agent harnesses (pi, opencode, hermes, open-webui) reliably, optionally behind a LiteLLM gateway. Use when a local model "works in one harness but not another", reasoning shows up in the wrong field or leaks <think>, tool-calls/roles misbehave, you're standing up a LiteLLM proxy in front of Ollama, or you're debugging a local-model harness that hangs / times out / produces nothing. Encodes both the connection paradigm and the debugging traps that masquerade as model bugs.
status: active
last_validated: 2026-06-30
supersedes: []
validation_method: session
---
# Local LLM Harness Wiring

Getting local Ollama models to behave the same across agent harnesses, and not wasting hours on failures that turn out to be the *harness*, not the model. Two halves: the **connection paradigm** and the **debugging discipline**. Cross-refs: [[debugging]], [[lessons-learned]], [[substrate-selection]], [[agentic-harness]].

## Part 1 — The connection paradigm

A model works in a harness when the harness's **(endpoint, reasoning-field, thinking-activation, roles)** tuple MATCHES the model's **(template, declared capabilities)**. Only two places to fix a mismatch: the **Modelfile** (template/params) or the **connection** (endpoint/thinking/roles).

### Endpoint decides the reasoning field name
| Endpoint | Reasoning lands in | Content |
|---|---|---|
| native `http://host:11434/api/chat` | `message.thinking` | clean answer |
| OpenAI-compat `…:11434/v1/chat/completions` | `choices[].message.reasoning` | may be empty if truncated mid-think |

Ollama's `/v1` shim re-labels native `thinking` → `reasoning`. A harness must read the field matching the endpoint it dials. Reading `content` for reasoning is what surfaces as "`<think>` leaking into the answer."

### Thinking activation is the dominant failure mode (measured)
A reasoning model called with thinking **disabled** emits literal `<think>…</think>` into `content` — it always generates the tokens; Ollama only *extracts* them into a field when thinking is on. So on any harness: **enable thinking** (read the extracted field), use a **non-reasoning** model, or **strip `<think>`** client-side. Endpoint choice only decides the field *name*; activation decides whether you get a clean split at all. Tool-calls and system/developer roles were fine across qwen-family models on both endpoints.

### Model template is the other half
`ollama show --modelfile <id>` reveals the template. A minimal `{{ .Prompt }}` template runs on the GGUF-embedded template — it *works* but behaves *differently* from siblings. Rebuild bare Modelfiles with the family template (copy a proven model's `TEMPLATE`+`PARAMETER`s, swap the `FROM`) so one harness config covers every model.

## Part 2 — The LiteLLM gateway pattern

Put LiteLLM in front of Ollama as a single OpenAI-compatible endpoint; point every harness at it:
```
pi / opencode / hermes / open-webui  →  LiteLLM :4000 (/v1)  →  Ollama :11434
```
Wins: one config instead of N, centralized **request logging** (the observability that makes debugging trivial), **retries / timeouts / fallbacks** (e.g. coder-9b → coder-4b), and **model aliasing** (harnesses reference stable names; swap tags underneath). Keep `model_name` == the Ollama tag for a true drop-in (harnesses change only `baseUrl`).

### Gotchas that will bite you (all verified)
- **Provider choice — use `openai/<tag>` → `:11434/v1`, NOT `ollama_chat/`.** `ollama_chat/` hits the native `/api/chat`, which requires string `content`; harnesses (pi) send OpenAI **array** content → `json: cannot unmarshal array into ... content of type string`. The `openai/`→/v1 path passes array content + tool-calls through faithfully. Cost: no per-request `num_ctx` — usually fine (the "context too big" theory is often wrong; verify before believing it).
- **Windows UTF-8 banner crash.** LiteLLM's startup banner throws `UnicodeEncodeError` under cp1252. Launch with `PYTHONUTF8=1 PYTHONIOENCODING=utf-8`.
- **The proxy adds latency but doesn't reduce it.** Local-model latency is inference-bound; the gateway just proxies. Slow ≠ broken — check the proxy log for retries/errors before blaming the wiring.
- Minimal launch: `PYTHONUTF8=1 litellm --config cfg.yaml --port 4000 --num_workers 1`; health at `/health/readiness`; models at `/v1/models`. Config is session-scoped unless you formalize startup — a repointed harness breaks if the proxy isn't running (rollback = point `baseUrl` back to `:11434/v1`). To make the proxy durable (boot-start, auto-restart, survives logout) register it as a Windows service — see [[litellm-windows-service]].

## Part 3 — Debugging discipline (the expensive lessons)

These are why this skill exists. Each cost real hours.

1. **Isolate the harness/invocation before blaming the model.** A CLI that "hangs" or "returns nothing" is often the *test rig*: e.g. `pi -p > file` hangs with no TTY on stdout, while `pi -p … | tail` works. Reproduce the raw model call (curl the endpoint) *outside* the harness first. Half a day was lost to a phantom "model/context/VRAM" bug that was a stdout-redirect hang.
2. **Verify against ground truth, never a proxy signal.** `100% GPU`, "process is running", and a non-empty PID are NOT evidence of output. Read the **actual tokens** — the session transcript (`.pi/agent/sessions/**/*.jsonl`), the written **artifact**, or the **proxy request log**. "The model is working, just slow" was asserted from GPU% while the transcript showed zero tokens and connection errors.
3. **Separate "running" from "producing correct output".** Only claim success after seeing the artifact (file contents, rendered output, test result, non-empty `usage.output`). A local orchestrator printed `"## Implementation Complete"` with no file on disk. Overconfident narration of a wrong conclusion wastes trust and time.
4. **Classify the failure — different class, different fix.**
   - *Harness artifact* → invocation form (TTY, buffering, redirect).
   - *Config/wiring bug* → the proxy/endpoint returns an explicit error (`unmarshal array`, `Unknown agent`, 4xx).
   - *Compute starvation* (e.g. a training run owns the GPU) → request times out with **zero tokens AND no completion in the proxy log**. Not a bug — wait or free the GPU.
5. **Verify model inventory; don't assume family symmetry.** There may be no `2b` of the family you want (`qwen3.5-reasoning-oc` / `qwopus-coder-oc` were 4b/9b only), and `qwen3.5-oc:2b` (general) ≠ `qwen3-vl:2b` (vision). `ollama list` before designing around a size tier.
6. **Reasoning models make poor budget-limited subagents.** As a delegated `coder` subagent, a reasoning model spends its token budget *thinking* and never emits the `write` tool call → returns a plan or empty output, no file. The same model works fine driven **directly** with room to run. Give subagents a non-reasoning model or a large budget, and always verify the delegated artifact.

## Quick diagnostic order
1. Curl the raw endpoint (`/api/chat` and `/v1`) outside any harness — does the model answer? where's the reasoning?
2. If yes but the harness fails → isolate the invocation (TTY/redirect/buffering), then read the harness's real transcript/log.
3. If the endpoint itself errors → wiring (provider, content shape, roles, template).
4. Zero tokens + nothing in the proxy log → compute starvation, not config.
Log what you actually observed at each step; never conclude from a proxy signal.
