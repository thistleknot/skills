---
name: pxpipe-claude-sdk-litellm
description: >
  End-to-end runbook for exposing subscription-billed Claude (Fable/Opus/Sonnet)
  through the local LiteLLM `:4000` gateway as plain OpenAI-format models, via a
  pxpipe-proxy (token-compression) + claude-agent-sdk shim chain. Three services:
  pxpipe-proxy (:47821, compresses tokens before api.anthropic.com), claude-sdk-shim
  (:47831, FastAPI wrapper over claude-agent-sdk using the Claude Code CLI's OAuth
  session — no API key), and litellm (:4000, routes claude-fable-5/opus-4-8/sonnet-5
  as `openai/` models to the shim). Use when rebuilding this chain from scratch,
  when one of the three services needs reinstalling, when a pxpipe npm update wipes
  the Node 25 undici patch and claude-* routes start 502ing, or when extending the
  same pattern to a new subscription-backed model. Triggers on: "pxpipe", "claude
  agent sdk shim", "subscription claude via litellm", "claude-sdk-shim", "OAuth no
  API key litellm", "token compression proxy", "rebuild the claude sdk chain".
  Cross-refs [[litellm-windows-service]] for the NSSM/service-registration mechanics
  this skill reuses (do not re-derive NSSM traps here — read that skill for those).
status: active
last_validated: 2026-07-20
supersedes: []
validation_method: session
---

# pxpipe + claude-agent-sdk-backed LiteLLM instance

Exposes cloud Claude models (billed against the Claude subscription, not the
Anthropic API) as plain OpenAI-format `/v1/chat/completions` models on the shared
`:4000` LiteLLM gateway, so any OpenAI client (hermes, pi, opencode, open-webui)
can dial `claude-fable-5` / `claude-opus-4-8` / `claude-sonnet-5` with no API key.

**Full chain:**
```
any OpenAI client (hermes, pi, ...)
  -> litellm :4000                      (routes model name -> shim, OpenAI format)
  -> claude-sdk-shim :47831             (FastAPI, wraps claude-agent-sdk)
  -> claude-agent-sdk -> Claude Code CLI (subscription OAuth, ~/.claude/.credentials.json)
  -> pxpipe-proxy :47821                (token compression before upstream)
  -> api.anthropic.com
```

This is deliberately **not** the same as pointing litellm straight at pxpipe: pxpipe
forwards whatever client credentials it's given and cannot inject the Claude Code
OAuth session itself — the SDK shim is the piece that actually authenticates as the
subscription. See [[litellm-windows-service]] for the NSSM registration mechanics
(elevate-with-`-File`, UTF-8 env, port-up polling, LocalSystem quirks) — reused
verbatim for all three services below, not repeated here.

## Why three separate services

- **pxpipe-proxy** — pure token-compression reverse proxy. Nothing here knows about
  OAuth; it just shrinks request bodies before they hit Anthropic. Runs standalone
  because it's reusable for any upstream, not just the SDK chain.
- **claude-sdk-shim** — the only piece that holds the subscription session. It shells
  out via `claude-agent-sdk`, which spawns the Claude Code CLI, which reads the OAuth
  credential file and (critically) inherits `ANTHROPIC_BASE_URL` pointed at pxpipe so
  compression applies to real subscription traffic.
- **litellm** — unchanged shared gateway; just gets three more `openai/` model
  entries pointed at the shim's port. Already durable per [[litellm-windows-service]].

Three failure domains stay independent: pxpipe dying doesn't kill OAuth-less local
Ollama traffic through the same `:4000`; the shim dying doesn't kill compression for
other proxied traffic.

## Part A — pxpipe-proxy (compression layer, :47821)

```powershell
npm install -g pxpipe-proxy
# creates C:\Users\<you>\AppData\Roaming\npm\node_modules\pxpipe-proxy\ + pxpipe.cmd shim
```

Register as an NSSM service pointed at the **installed** `bin/cli.js`, not `npx`
(npx's per-user cache is fragile under the LocalSystem account NSSM runs as):
```
nssm install pxpipe-proxy  "C:\Program Files\nodejs\node.exe"
nssm set pxpipe-proxy AppParameters  "C:\Users\<you>\AppData\Roaming\npm\node_modules\pxpipe-proxy\bin\cli.js"
nssm set pxpipe-proxy AppStdout  C:\Users\<you>\.pi\logs\pxpipe-proxy.log
nssm set pxpipe-proxy AppStderr  C:\Users\<you>\.pi\logs\pxpipe-proxy.log
nssm set pxpipe-proxy AppRotateFiles 1; nssm set pxpipe-proxy AppRotateOnline 1; nssm set pxpipe-proxy AppRotateBytes 5242880
nssm set pxpipe-proxy Start SERVICE_AUTO_START
nssm set pxpipe-proxy AppExit Default Restart; nssm set pxpipe-proxy AppRestartDelay 3000; nssm set pxpipe-proxy AppThrottle 5000
```
Same elevate-with-`-File` / verify-after-boot discipline as [[litellm-windows-service]] Part C.

### Known trap: Node 25 undici detached-ArrayBuffer 502

As of pxpipe-proxy 0.9.0 on Node 25, every non-compressed (below the
`below_min_chars` threshold) request 502s. Root cause: undici re-extracts a
shared `ArrayBuffer` that's already been detached by an earlier read. Fixed with a
**local patch to the installed package** (lost on `npm update -g pxpipe-proxy` —
check upstream first, reapply if still broken):

In `...\npm\node_modules\pxpipe-proxy\dist\node.js`:
1. Copy probe request bodies via `.slice(0)` before `countTokensUpstream` touches
   them (breaks the shared-buffer aliasing that causes the detach).
2. Wrap byte request bodies in `new Blob([...])` before the upstream `fetch` call
   (Blob owns its own copy, sidesteps the detached-ArrayBuffer re-extraction).
3. Optional: a `console.error` in the forward-fetch catch block to see the real
   cause on any future 502 instead of a bare status code.

Verify the patch: a non-compressed request through `:47821` should return a real
upstream response (even a 401 with a placeholder key counts — it proves the full
chain reached `api.anthropic.com` instead of 502ing inside pxpipe).

## Part B — claude-sdk-shim (OAuth bridge, :47831)

```powershell
pip install claude-agent-sdk==0.2.123   # into whichever venv the service will run from, e.g. py310
```

Minimal FastAPI shim (`C:\Users\<you>\.pi\claude_sdk_shim.py`) exposing
`/v1/chat/completions`, `/v1/models`, `/health`:

```python
"""OpenAI-compatible shim over claude-agent-sdk.

Preconditions: Claude Code OAuth credentials at ~/.claude/.credentials.json;
no ANTHROPIC_API_KEY in the service environment (would shadow OAuth).
Failure modes: SDK/CLI errors propagate as HTTP 500, fail fast, no fallback.
Client-supplied OpenAI tool definitions are ignored, not silently half-applied
— the SDK owns its own agent loop and cannot accept external tool schemas.
"""
import time, uuid
from fastapi import FastAPI
from pydantic import BaseModel
from claude_agent_sdk import query, ClaudeAgentOptions, AssistantMessage, ResultMessage, TextBlock

app = FastAPI(title="claude-sdk-shim")

class ChatMessage(BaseModel):
    role: str
    content: str | list

class ChatRequest(BaseModel):
    model: str
    messages: list[ChatMessage]
    stream: bool = False
    max_tokens: int | None = None
    temperature: float | None = None  # accepted, not forwarded — SDK owns sampling

def _flatten(content) -> str:
    if isinstance(content, str):
        return content
    return "\n".join(p.get("text", "") for p in content if isinstance(p, dict))

def _to_prompt(messages: list[ChatMessage]) -> tuple[str | None, str]:
    system_parts = [_flatten(m.content) for m in messages if m.role == "system"]
    convo = "\n\n".join(f"{m.role}: {_flatten(m.content)}" for m in messages if m.role != "system")
    return ("\n\n".join(system_parts) or None), convo

async def _run(req: ChatRequest) -> tuple[str, dict]:
    system_prompt, prompt = _to_prompt(req.messages)
    options = ClaudeAgentOptions(model=req.model, system_prompt=system_prompt, max_turns=1, allowed_tools=[])
    text_parts, usage = [], {"prompt_tokens": 0, "completion_tokens": 0, "total_tokens": 0}
    async for message in query(prompt=prompt, options=options):
        if isinstance(message, AssistantMessage):
            for block in message.content:
                if isinstance(block, TextBlock):
                    text_parts.append(block.text)
        elif isinstance(message, ResultMessage) and message.usage:
            u = message.usage
            usage = {"prompt_tokens": u.get("input_tokens", 0), "completion_tokens": u.get("output_tokens", 0),
                      "total_tokens": u.get("input_tokens", 0) + u.get("output_tokens", 0)}
    return "".join(text_parts), usage

@app.post("/v1/chat/completions")
async def chat_completions(req: ChatRequest):
    text, usage = await _run(req)
    return {
        "id": f"chatcmpl-{uuid.uuid4().hex[:24]}", "object": "chat.completion",
        "created": int(time.time()), "model": req.model,
        "choices": [{"index": 0, "message": {"role": "assistant", "content": text}, "finish_reason": "stop"}],
        "usage": usage,
    }

@app.get("/health")
async def health():
    return {"status": "ok"}
```

Run: `uvicorn claude_sdk_shim:app --host 127.0.0.1 --port 47831`

Register as an NSSM service — **the env vars are the load-bearing part**:
```
nssm install claude-sdk-shim  "C:\Users\<you>\py310\Scripts\python.exe"
nssm set claude-sdk-shim AppParameters  "-m uvicorn claude_sdk_shim:app --host 127.0.0.1 --port 47831"
nssm set claude-sdk-shim AppDirectory   C:\Users\<you>\.pi
nssm set claude-sdk-shim AppEnvironmentExtra ^
    ANTHROPIC_BASE_URL=http://127.0.0.1:47821 ^
    CLAUDE_CONFIG_DIR=C:\Users\<you>\.claude ^
    PYTHONIOENCODING=utf-8 PYTHONUTF8=1
nssm set claude-sdk-shim Start SERVICE_AUTO_START
nssm set claude-sdk-shim AppExit Default Restart; nssm set claude-sdk-shim AppRestartDelay 3000; nssm set claude-sdk-shim AppThrottle 5000
```

### Traps specific to this service

- **`ANTHROPIC_BASE_URL` must be set explicitly in `AppEnvironmentExtra`, even if
  it's already set machine-wide.** NSSM/Windows services don't re-read machine env
  changes until reboot — a service started before you set the machine var won't see
  it. Set it directly on the service to route the CLI's traffic through pxpipe
  without waiting for a reboot.
- **`CLAUDE_CONFIG_DIR` must point at the real user's `.claude`, not LocalSystem's.**
  NSSM services run as LocalSystem by default, whose home directory has no OAuth
  credentials. Point `CLAUDE_CONFIG_DIR` at `C:\Users\<you>\.claude` explicitly or
  every request 401s with no credentials found — this looks like an auth bug but is
  actually a wrong-home-directory bug.
- **Never set `ANTHROPIC_API_KEY` on this service.** Its presence causes the CLI to
  prefer key auth over the OAuth session, silently defeating the whole point of
  routing through the subscription instead of metered API billing.
- **Client tool definitions are dropped, not forwarded.** `allowed_tools=[]` and
  `max_turns=1` in `ClaudeAgentOptions` are deliberate — the SDK owns its own
  agent loop and cannot accept an external OpenAI tool schema. Any caller sending
  `tools=[...]` gets a plain-chat response with the tools silently ignored. If you
  need tool-calling against these models, that requires a native SDK-aware harness
  provider, not this shim (hermes has one landing in PR #65982).
- **First-token latency is 10–30s.** The SDK renders context images/setup before
  the CLI streams anything. Set generous client timeouts (30–60s) on anything
  calling through this chain; a slow first byte is expected, not a hang.

## Part C — LiteLLM routes (:4000)

Add to `litellm_config.yaml` — `openai/` provider prefix, pointed at the shim, no
real key (`subscription-oauth` is a placeholder string, not a secret since the shim
ignores whatever key is sent and auths via OAuth internally):

```yaml
  - model_name: claude-fable-5
    litellm_params: { model: openai/claude-fable-5, api_base: http://127.0.0.1:47831/v1, api_key: "subscription-oauth" }
  - model_name: claude-opus-4-8
    litellm_params: { model: openai/claude-opus-4-8, api_base: http://127.0.0.1:47831/v1, api_key: "subscription-oauth" }
  - model_name: claude-sonnet-5
    litellm_params: { model: openai/claude-sonnet-5, api_base: http://127.0.0.1:47831/v1, api_key: "subscription-oauth" }
```

Restart the litellm service (it doesn't hot-reload `model_list`) — see
[[litellm-windows-service]] Part C for the restart/verify procedure. Then:
```powershell
(Invoke-RestMethod http://127.0.0.1:4000/v1/models).data.id   # should list the three claude-* names
```

## End-to-end verification (one shot, costs subscription usage)

Don't loop — one short completion is enough to prove the chain:
```powershell
Invoke-RestMethod http://127.0.0.1:4000/v1/chat/completions -Method Post -ContentType 'application/json' -Body '{"model":"claude-fable-5","messages":[{"role":"user","content":"Reply with exactly: OK"}]}'
```
Or through any downstream OpenAI-compatible client. A `401` at the pxpipe layer
(`api.anthropic.com` reachable, placeholder key rejected) already proves the proxy
hop works — full green light is the shim call above returning real text.

## Known limitations (don't try to fix these — they're structural)

- **pxpipe compression is lossy on exact strings.** Fine for prose/gist; unreliable
  for byte-exact IDs, counts, or hashes riding through compressed context.
- **Billing may still draw on plan limits, not a separate Agent SDK credit** — see
  upstream issue #47260. Don't assume subscription routing is metering-free.
- **No tool-calling passthrough** (see Part B trap above) until a native SDK-aware
  provider lands (hermes PR #65982 or equivalent for other harnesses).

## Rollback (per service, admin shell)
```powershell
C:\Users\<you>\.pi\bin\nssm.exe stop claude-sdk-shim;  C:\Users\<you>\.pi\bin\nssm.exe remove claude-sdk-shim confirm
C:\Users\<you>\.pi\bin\nssm.exe stop pxpipe-proxy;     C:\Users\<you>\.pi\bin\nssm.exe remove pxpipe-proxy confirm
npm uninstall -g pxpipe-proxy
pip uninstall claude-agent-sdk
Remove-Item C:\Users\<you>\.pi\claude_sdk_shim.py, C:\Users\<you>\.pi\sdk_smoke.py
Remove-Item C:\Users\<you>\.pi\logs\pxpipe-proxy.log, C:\Users\<you>\.pi\logs\claude-sdk-shim.log
Remove-Item -Recurse C:\WINDOWS\system32\config\systemprofile\.pxpipe   # admin, LocalSystem's runtime data
```
Then remove the three `claude-*` entries from `litellm_config.yaml` and restart litellm.
Full change log with exact byte sizes and timestamps: `C:\Users\<you>\.pi\MANIFEST-pxpipe-proxy-service.md`.
