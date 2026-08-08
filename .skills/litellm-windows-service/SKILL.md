---
name: litellm-windows-service
description: >
  End-to-end runbook for standing up a local LiteLLM-fronted model stack on Windows:
  (A) prepare the ollama Modelfiles it serves — regenerate from base GGUFs with a
  working tools+think TEMPLATE, a sane num_ctx, and self-describing tags; (B) tune
  KV-cache quantization + flash attention so large-context models fit in VRAM; and
  (C) register LiteLLM as an always-on Windows service via NSSM so the shared :4000
  gateway survives reboot/logout and auto-restarts. Use when a manual `litellm
  --port 4000` keeps dying, when a base GGUF can't tool-call or its context OOMs the
  GPU, when 256k models won't fit in VRAM, or when pi/opencode/hermes/open-webui all
  depend on one gateway. Triggers on: "make litellm persistent", "litellm dies on
  reboot", "nssm litellm", "run litellm as a Windows service", "ollama KV cache
  quantization / q4_0 / flash attention", "model won't tool-call", "rebuild the
  Modelfile", "num_ctx too big / OOM", "self-describing model tags".
  Encodes the no-admin path and the elevation/UTF-8/LocalSystem/KV/template traps.
status: active
last_validated: 2026-07-01
supersedes: []
validation_method: session
---

# LiteLLM Local Stack on Windows (models → VRAM → service)

The end-to-end runbook for a local, LiteLLM-fronted model stack on Windows — the shared
`:4000` gateway that pi/opencode/hermes/open-webui all dial. Three parts: **(A)** prepare
the ollama models (Modelfiles), **(B)** make them fit in VRAM (KV-cache), **(C)** front
them with a durable service so the endpoint never dies.
Cross-refs: [[local-llm-harness-wiring]] (connection paradigm + debugging discipline),
[[substrate-selection]].

## Part A — Prepare the models (Modelfiles)

Base GGUFs (e.g. from Jackrong) frequently ship two problems that masquerade as harness bugs:
1. **No / broken tools template** → the model can never emit tool calls, so agentic use fails
   silently. Check: `ollama show <tag> --modelfile | grep -c tool_call` — a working Qwen3.5
   template has **11**; a bare `{{ .Prompt }}` GGUF template has **0**. (The `Qwopus3.5-4B-Coder`
   GGUF shipped 0; the reasoning + 9b-coder bases shipped 11.)
2. **Oversized baked `num_ctx`** (e.g. 131072 / 262144) → over the `/v1` shim nothing passes
   `num_ctx`, so ollama eagerly allocates a giant KV cache → slow cold-load / timeouts (see Part B).

**Regenerate a clean tag** (`ollama create` is a manifest/blob op — **no GPU inference, safe
during training**):
```
# Modelfile
FROM <base-gguf-tag>                 # or FROM <an-existing-good-tag> if bases are deleted
TEMPLATE """<canonical Qwen3.5 tools+think template>"""   # only if the base lacks one
PARAMETER num_ctx 262144             # the context you actually want (see Part B for VRAM cost)
PARAMETER num_predict 32768
PARAMETER stop <|im_start|>
PARAMETER stop <|im_end|>
PARAMETER temperature 0.6
PARAMETER top_k 20
PARAMETER top_p 0.95
```
```powershell
ollama create qwen3.5-reasoning-thinking-256k:4b -f Modelfile
```
- **Get the TEMPLATE from a model that already has one**: `ollama show <good-model> --modelfile`
  copies its full tools+think `TEMPLATE`; swap the `FROM`. Don't hand-write it.
- **Re-root, don't stack**: `FROM <base-gguf>` yields a clean single derivation; `FROM <derived-tag>`
  layers override on override. If the base is gone, `FROM <canonical-tag> + PARAMETER num_ctx N`
  inherits the good template and just overrides the param — also fine.
- **Self-describing tags** — name them `<family>-<capability>-thinking-<ctx>:<size>` so any picker
  shows capability / thinking / context at a glance:
  `qwen3.5-reasoning-thinking-256k:4b`, `qwopus-coding-thinking-256k:4b` (+ `:9b`).
  Rename with `ollama cp <old> <new>` (copies manifest, shares blobs) then `ollama rm <old>`.
  **Then global find/replace the tag string across EVERY config** — litellm_config.yaml,
  opencode.json + the oh-my-opencode-slim files, pi models.json/settings.json/agents, Hermes
  config.yaml + context_length_cache.yaml — **and restart the litellm service** so its
  `model_list` matches. A missed reference = "model not found" in one harness only.
- **Keep only canonical tags** in ollama; `ollama rm` the raw base GGUF tags so nothing
  auto-selects the unfixed model. Safe — canonical tags share the weight blobs (ollama refcounts;
  it never deletes a blob still referenced).
- Verify each: `ollama show <tag> --modelfile | grep -c tool_call` == 11 and `... | grep num_ctx`.

## Part B — Fit them in VRAM (KV-cache quantization)

The **KV cache is a SEPARATE quantization from the model weights** — this trips everyone up. Weights
are q4/q5 (the GGUF, ~2.5 GB for a 4b); the **KV cache defaults to f16 regardless**, and at 256k
that's **~8 GB per 4b model**. So a q5 model still needs 8 GB of f16 KV — the weight quant does
nothing for it. On a 16 GB card, two 256k models (or one + a training run) OOM → ollama's runner
dies → `:4000` returns "Connection error" (which is honest: the upstream died, not LiteLLM).

**LiteLLM cannot fix this** — it only proxies HTTP; the KV cache lives in llama.cpp/ollama. Set it
at the **ollama** layer (user env, no admin), then restart ollama:
```powershell
[Environment]::SetEnvironmentVariable('OLLAMA_FLASH_ATTENTION','1','User')   # REQUIRED for KV quant
[Environment]::SetEnvironmentVariable('OLLAMA_KV_CACHE_TYPE','q4_0','User')  # or q8_0
# restart ollama so it picks up the env:
Get-Process 'ollama app','ollama','llama-server' -EA SilentlyContinue | Stop-Process -Force
Start-Process 'C:\Users\<you>\AppData\Local\Programs\Ollama\ollama app.exe'
```
Measured KV for **256k / 4b** (options are only f16 / q8_0 / q4_0 — there is no q5 for KV):

| KV dtype | 256k KV size | reasoning-4b total |
|---|---|---|
| f16 (default) | 8192 MiB | ~11 GB |
| q8_0 (≈lossless) | 4352 MiB | 8.9 GB |
| q4_0 (smallest) | 2304 MiB | 6.8 GB |

- Restarting ollama does **not** touch training (a separate CUDA process) but may auto-apply a
  pending ollama update. The env vars are user-scope and persist across reboots.
- If two big models + training still OOM, add `OLLAMA_MAX_LOADED_MODELS=1` so ollama swaps them
  (≈15 s reload) instead of holding both resident.
- Confirm it took: server.log shows `OLLAMA_FLASH_ATTENTION:true`, `OLLAMA_KV_CACHE_TYPE:q4_0`, and
  `KV buffer size = 2304 MiB`; `ollama ps` shows the smaller footprint.

## Part C — Durable LiteLLM service (NSSM)

A hand-launched `litellm --config … --port 4000` dies on reboot/logout and takes every harness's
endpoint with it. Register it as an always-on Windows service.

### When NSSM vs a Scheduled Task
- **NSSM service** (this skill): true always-on — starts at **boot before login**, runs as
  LocalSystem, auto-restarts on crash, no console. Needs admin **once** to create the service.
- **Scheduled Task at logon**: the no-admin fallback. Starts only at interactive logon, runs as
  you. Use when you cannot elevate at all. (Register with `Register-ScheduledTask -Trigger
  (New-ScheduledTaskTrigger -AtLogOn)` running a hidden wrapper that loops litellm.)

### Procedure (register the service)

#### 1. Acquire NSSM (portable, no admin)
```powershell
New-Item -ItemType Directory -Force C:\Users\<you>\.pi\bin | Out-Null
Invoke-WebRequest https://nssm.cc/release/nssm-2.24.zip -OutFile $env:TEMP\nssm.zip
Expand-Archive $env:TEMP\nssm.zip $env:TEMP\nssm -Force
Copy-Item $env:TEMP\nssm\nssm-2.24\win64\nssm.exe C:\Users\<you>\.pi\bin\nssm.exe
```
`nssm.exe` is a single portable binary — downloading/extracting needs no admin. (Only the
`nssm install`/`start` step below does.)

#### 2. Registration script (`register-litellm-service.ps1`)
Idempotent, self-logging (transcript), verifies at the end. See the companion
`register-litellm-service.ps1` in this skill folder — key settings:
```
nssm install litellm  C:\Users\<you>\py310\Scripts\litellm.exe
nssm set litellm AppParameters '--config C:\Users\<you>\.pi\litellm_config.yaml --port 4000'
nssm set litellm AppDirectory  C:\Users\<you>\.pi
nssm set litellm AppEnvironmentExtra PYTHONIOENCODING=utf-8 PYTHONUTF8=1   # <-- REQUIRED
nssm set litellm AppStdout <log>;  nssm set litellm AppStderr <log>
nssm set litellm AppRotateFiles 1; nssm set litellm AppRotateOnline 1; nssm set litellm AppRotateBytes 5242880
nssm set litellm Start SERVICE_AUTO_START
nssm set litellm AppExit Default Restart; nssm set litellm AppRestartDelay 3000; nssm set litellm AppThrottle 5000
```

#### 3. Register + start (elevated — one UAC)
```powershell
Start-Process powershell -Verb RunAs -ArgumentList '-NoProfile','-ExecutionPolicy','Bypass',`
  '-File','C:\Users\<you>\.pi\register-litellm-service.ps1'
```

#### 4. Verify
```powershell
Get-Service litellm                                   # Running / Automatic
(Invoke-RestMethod http://127.0.0.1:4000/v1/models).data.id   # self-describing model tags
```

## Traps (each cost real time — all verified)
- **Elevate with `-File`, never a `-Command` string.** Passing the work as
  `Start-Process -Verb RunAs -ArgumentList '-Command',"…nested quotes…"` mangles the quotes
  across the UAC boundary → the elevated shell runs **nothing** and you get a 0-byte log with
  no service created (looks like "UAC was denied" but it wasn't). Point `-File` at a script;
  have the script `Start-Transcript` so its output is readable (elevated output isn't piped back).
- **UTF-8 env is mandatory.** LiteLLM's startup banner throws `UnicodeEncodeError` under Windows
  cp1252 and the service exits immediately. Set `PYTHONIOENCODING=utf-8` + `PYTHONUTF8=1` via
  `AppEnvironmentExtra` (a plain launch needs them too — see [[local-llm-harness-wiring]]).
- **Service runs as LocalSystem → you can't kill/restart its PID as a normal user**
  (`Stop-Process` → *Access is denied*). That's correct, not a failure. Manage it with
  `Restart-Service litellm` / `Stop-Service litellm` from an **admin** shell, or `nssm restart litellm`.
- **litellm binds `:4000` ~10–20s after the service reports `Running`.** The service Status flips
  to Running when the process launches, not when the port is up. Verify with a poll loop on
  `Get-NetTCPConnection -LocalPort 4000`, not an instant check, or you'll think it failed.
- **Free the port before installing.** If a manual litellm still holds `:4000`, the service start
  fights it. The script stops any `:4000` listener first (`Get-NetTCPConnection … | Stop-Process`).
- **Ollama isn't a service** (starts in the user session). A boot-start litellm service may 500
  briefly until Ollama is up — acceptable, litellm forwards lazily; no hard dependency needed.

## Rollback
```powershell
# admin:
C:\Users\<you>\.pi\bin\nssm.exe stop litellm
C:\Users\<you>\.pi\bin\nssm.exe remove litellm confirm
```
Then relaunch manually if needed: `PYTHONUTF8=1 PYTHONIOENCODING=utf-8 litellm --config <cfg> --port 4000`.
Deleting `nssm.exe` and the script leaves no residue beyond the (removed) service entry.
