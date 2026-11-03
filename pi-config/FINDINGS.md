# FINDINGS — local-model pi setup + cross-harness Ollama paradigm

Date: 2026-06-28. Environment: Windows, Ollama (D:\OllamaModels), pi 0.80.2.
Companion to `[[pi-config]]` and `[[ollama-harness-paradigm]]`.

## 1. Endpoint/field probe (ollama_probe.py)

Probe hits BOTH endpoints (native `/api/chat`, OpenAI `/v1`) with thinking on/off,
plus a tool-call and role check. `num_predict=256` cap (so reasoning models truncate;
we measure WHERE output lands, not full answers).

Raw evidence: `tmp/probe_evidence_raw.txt` (note: a stale buffered run interleaved with the live run; rows below are the reconciled, consistent values). `+` = field populated, `leak` = literal `<think>` in `content`.

| Model | native think=ON | native think=OFF | /v1 default | tool-call native/v1 | roles sys/dev |
|-------|-----------------|------------------|-------------|----------------------|---------------|
| qwen3.5-reasoning-oc:9b | `thinking`+, content empty, no leak | no thinking field, **`<think>` LEAKS into content** | `reasoning`+ | tool_calls=1 / tool_calls=1 ✓ | accepted / accepted |
| qwopus-coder-oc:9b | `thinking`+, no leak | no thinking field, **`<think>` LEAKS** | `reasoning`+, also answered content | tool_calls=1 / tool_calls=1 ✓ | accepted / accepted |
| ornith:9b (pre-rebuild) | `thinking`+(514c), no leak | no field, **no leak** (answered plainly) | `reasoning`+ | tool_calls=1 / (slow/timeout) ✓ | (slow) / accepted |
| ornith:9b (post-rebuild) | `thinking`+, no leak | no field, **`<think>` LEAKS** (now matches family) | `reasoning`+ | tool_calls=1 / tool_calls=1 ✓ | accepted / accepted |

### The actionable rule (measured, not theorized)
**A reasoning model called with thinking DISABLED leaks literal `<think>…</think>` into `content`.** Mechanism: these models are trained to always emit `<think>` tokens; Ollama only *extracts* them into a separate field (`thinking` native / `reasoning` on /v1) when the request **enables thinking**. With thinking off, the model still generates `<think>`, and Ollama leaves it in `content`. So across ANY harness:
- Enable thinking so Ollama extracts it into its field (then read `thinking` on `/api/chat`, `reasoning` on `/v1`), **or**
- use a non-reasoning model for that role, **or**
- strip `<think>…</think>` client-side.
This — not the endpoint choice — is the dominant "works vs. doesn't" factor. Endpoint only decides the field *name*; thinking-activation decides whether you get a clean split at all. Tool-calling and `system`/`developer` roles worked on every qwen-family model on both endpoints.

## 2. Ornith Modelfile rebuild

- Pre: `TEMPLATE = {{ .Prompt }}` (minimal/raw — no role markers, tool block, or `<think>` gating) despite Capabilities = tools/thinking/completion.
- Action: rebuilt `ornith:9b` from `hf.co/deepreinforce-ai/Ornith-1.0-9B-GGUF:ornith-1.0-9b-Q6_K.gguf` with the verbatim qwen3.5-reasoning-oc TEMPLATE + PARAMETERs (Modelfile: `tmp/ornith.Modelfile`).
- Post: **strict improvement.** Now matches the qwen family exactly (clean think-split when ON, `<think>` leak when OFF, `reasoning` on /v1). `/v1` tool-call went from **timeout → working in 9.1s**; per-call latency dropped ~4× (9–13s vs 47–56s pre) because `num_ctx` is now explicitly 262144 instead of an unset default. Conclusion: ornith was *functional* pre-rebuild (GGUF-embedded template) but **inconsistent + slower**; the explicit Modelfile makes it uniform, faster, and reliably tool-callable over both endpoints.

## 3. Coder / delegation test — Conway's Game of Life (interactive HTML)

Test case: build `tmp/conway.html` — a self-contained interactive Game of Life (canvas grid, click-to-toggle, Start/Stop/Step/Clear/Random, B3/S23, generation counter).

- **Orchestrator → coder delegation: FIRES but does NOT converge (documented blocker).** With the harness fixed (pipe form) and 600s budget, the 4b orchestrator called the `subagent` tool to delegate to `coder`, but the chain failed in three stages (from the real transcript):
  1. `subagent`→coder returned **"completed without making edits… returned planning/scratchpad output instead"** — the coder subagent produced a *plan* rather than writing the file.
  2. Orchestrator then invented a non-existent agent: **"Unknown agent: codex."**
  3. Orchestrator finally declared **"## Implementation Complete — I have successfully created mul.py"** — but **`mul.py` was never created.** The local 4b orchestrator *falsely claimed success.*
  Net: the delegation *mechanism* works (subagent fires), but the small-model orchestration loop doesn't reliably produce artifacts and can hallucinate completion. The **direct** coder (§3 above) writes+tests files correctly; delegation through the 4b does not.
- **Second attempt (tool-first coder + explicit task): still fails — root cause isolated.** Strengthened `coder.md` ("you MUST call write, do not plan") and passed an explicit task. Result across **3 subagent invocations** (artifacts in `…/subagent-artifacts/`): the 9b coder DID load and fire, received a correct task + acceptance contract, but every `*_output.md` is **empty** and no `mul.py` was written anywhere. The orchestrator also hit repeated subagent-tool **validation errors** ("I keep getting validation errors") before the calls landed. Likely root cause: `qwopus-coder-oc:9b` is a *reasoning* model — as a budget-limited subagent it spends its tokens on reasoning and never emits the `write` tool call (same "empty content, all reasoning" pattern the probe showed). **Conclusion: delegation FIRES but does not converge; use the coder directly, or give subagents a non-reasoning/larger budget. Blocker fully characterized — not pursuing further per the autonomy clause.**
- Direct doer test (`pi -p --model qwopus-coder-oc:9b --thinking low`) building conway.html: **FAILED — zero output.** Session transcript (`.pi/agent/sessions/--C--Users-user-.pi-tmp--/*.jsonl`) shows both attempts errored with `usage.output=0`: first `500 ... wsarecv: An existing connection was forcibly closed`, retry `Request timed out`. The redirected `.log` stayed empty (pi `-p` buffers stdout to exit) and `ollama ps` showed 100% GPU — neither indicates real progress; only the session jsonl revealed the failure.

### ROOT CAUSE (corrected) — it was the test harness, not pi/Ollama/context
Earlier theories (contextWindow 262144 too high → VRAM OOM) were **wrong**, disproven by direct measurement:
- Ollama `/v1` is healthy: 4b answers "DEF-OK" complete in **6s**; qwopus-9b generates valid code at **both** num_ctx 32768 and 262144 (20–31s, HTTP 200, no drop). The model and server are fine.
- The real confound: **`pi -p` hangs when stdout is redirected to a file (`> log 2>&1`)** but works when **piped (`2>&1 | tail`)**. Same prompt/model: file-redirect → 0 bytes, killed at timeout; pipe → returns in 26s, rc=0. pi behaves differently without a TTY on stdout.
- The original Conway/add.py "zero-token / wsarecv / timeout" failures were largely this harness artifact (plus, in the first run, a transient 500). Lesson: I was debugging my own test harness, not the product. → see `[[avoid-overconfident-wrong]]`, `[[keep-finger-on-model-outputs]]`.

Config changes still applied as sensible defaults (reversible): `contextWindow` 32768, per-model `maxTokens` caps, `defaultThinkingLevel: low`, removed `_launch`, added `qwen3.5-oc:2b`.

### Doer test (correct harness): ✅ PASS
`pi -p --model qwopus-coder-oc:9b --thinking low` (piped) built `add.py`, ran it, asserts passed, reported "pass". rc=0, **215s**. Verified by artifact: `add.py` (115 bytes, correct `add()` + 3 asserts incl. a string-concat case). Transcript clean: `assistant out=62 stop=toolUse → toolResult → assistant out=31 stop=stop`, no errors. The qwopus doer works end-to-end through pi; it's just slow (~3.5 min multi-turn on a local 9b).

## 4. Orchestrator A/B sweep

Same planning prompt (6-step plan for an interactive Conway GoL page), `pi -p --model X --thinking low`, piped, 220s cap, VRAM-serialized. Raw: `tmp/ab_sweep.out`.

| Model | Role | Verdict | Latency-feel | Notes |
|-------|------|---------|--------------|-------|
| **qwen3.5-reasoning-oc:4b** | orchestrator | ✅ **best** | fast — clean exit **59s** | concise, correct, well-structured plan; only model to finish (rc=0). Minor: stated "B3: birth if 1 or 3" (B3 = exactly 3). |
| qwen3.5-reasoning-oc:9b | orchestrator | ✗ not viable | too slow — **0 output @ 220s timeout** | over-thinks; never produced a plan within budget. Skip for orchestration in print mode. |
| ornith:9b (rebuilt) | orchestrator | ◑ good plan, slow | best-written 6-step plan, but **did not exit by 220s** (rc=124) | highest-quality content (correct B3/S23, styling step); non-terminating in budget — usable only with a long timeout. |
| qwen3.5-oc:2b | orchestrator | ◑ low quality | verbose, **timed out @220s** | rambling, imprecise ("template literals within HTML string interpolation"); the "max-efficiency" tier trades too much quality. |

Coder/doer (`qwopus-coder-oc:9b`): ✅ completes real file-write+run tasks (add.py, 215s) — see §3.

## 4b. LiteLLM gateway (pi → LiteLLM:4000 → Ollama) — WORKING

Stood up LiteLLM (py310 v1.75.0) as a single OpenAI-compatible gateway on `:4000`, config at `C:\Users\user\.pi\litellm_config.yaml`. pi repointed (`models.json` `baseUrl` → `http://localhost:4000/v1`; model ids unchanged since `model_name` == ollama tag).

**Verified through the gateway:**
- `/v1/models` lists all 7 tags; `/health` green.
- Reasoning model: clean `content` answer + separate `thinking` field, **no `<think>` leak** (direct probe).
- Tool-calls pass through (`tool_calls` returned, 17s).
- pi chat: `PROXY-OK` (rc=0). pi coder: built+validated `add2.py` (correct, asserts) through the proxy.
- Every request logged: `POST /v1/chat/completions → 200 OK` (the observability win).

**Two gotchas (solved):**
1. **UTF-8 banner crash on Windows** — LiteLLM's startup banner hits `UnicodeEncodeError` under cp1252. Launch with `PYTHONUTF8=1 PYTHONIOENCODING=utf-8`.
2. **`ollama_chat/` rejects pi's payloads** — pi sends OpenAI *array* `content`; Ollama's native `/api/chat` wants a string (`cannot unmarshal array into ... content`). **Fix: use `openai/<tag>` with `api_base http://localhost:11434/v1`** (Ollama's OpenAI shim accepts arrays). Cost: no per-request `num_ctx` — acceptable, since the num_ctx theory was disproven (models stable at default ctx). Set pi models to `input:["text"]` (vision not needed for orchestrator/coder).

**Caveat — latency:** the gateway adds modest overhead and does NOT reduce local-model latency. Trivial chat ≈169s cold (vs ~26s direct, mostly cold load); the 9b coder created the file but pi's full multi-turn session exceeded a 400s budget. No retries/errors in the log — it's model inference time. For interactive use it's fine; for long delegated tasks, expect minutes.

**Launch command (background, this session):**
`PYTHONUTF8=1 PYTHONIOENCODING=utf-8 C:\Users\user\py310\Scripts\litellm --config C:\Users\user\.pi\litellm_config.yaml --port 4000 --num_workers 1`

**Expand to other harnesses (one-line repoint each, once desired):** opencode `provider.ollama.options.baseURL` → `:4000/v1`; hermes `model.base_url` + `providers.ollama-launch.api` → `:4000/v1`; open-webui `OLLAMA_BASE_URL`/OpenAI-connection → `:4000/v1`. **Rollback for pi:** set `baseUrl` back to `http://localhost:11434/v1`.

## 5. Recommendation

**Leave `settings.json` on `qwen3.5-reasoning-oc:4b` as orchestrator** (already set). It was the only candidate to plan cleanly and exit fast (59s, rc=0); the 9b over-thinks to no benefit, ornith plans well but won't terminate promptly, and the 2b is too imprecise. Pair it with **`qwopus-coder-oc:9b` as the `coder` doer** (proven on real tasks). Net: light 4b reasoner routes/plans, heavy 9b coder implements — the orchestrator/doer split works, with the caveat that local 9b doer turns are slow (~3–4 min/task).
