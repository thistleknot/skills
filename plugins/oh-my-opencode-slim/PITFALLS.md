# OMO-Slim Pitfalls

Critical mistakes that caused production stalls. Read before editing any agent config.

---

## ❌ PITFALL 1: Wrong `task` tool field names in `orchestratorPrompt`

**Symptom:** Orchestrator receives a planner response, then stalls indefinitely with no error shown.

**Root cause:** The `orchestratorPrompt` fields in `oh-my-opencode-slim.json` are injected into the
orchestrator's context. If they describe wrong field names for the `task` tool, the orchestrator
calls `task()` with those wrong names → **silent SchemaError → stall loop**.

### ✅ Correct field names

```
task(
  description: "3-5 word label",   ← REQUIRED
  subagent_type: "agent-name",     ← REQUIRED (NOT "agent")
  prompt: "full instructions"      ← REQUIRED (NOT "instructions")
)
```

### ❌ Wrong field names (will stall)

| Wrong | Correct |
|-------|---------|
| `agent` | `subagent_type` |
| `instructions` | `prompt` |
| `subtask` | `task` (and don't use subtask — it loops back to orchestrator) |

**Every `orchestratorPrompt` that contains a DELEGATION SCHEMA MUST use `subagent_type` and `prompt`.**

---

## ❌ PITFALL 2: Gemma 26B as orchestrator + Gemma 26B as planner

**Symptom:** Orchestrator successfully calls planner (~50s), planner returns, orchestrator stalls.

**Root cause:** Two ~50s turns back-to-back push context to 50% of Gemma's 262K limit (131K tokens).
Compaction fires, strips the plan, orchestrator re-plans from scratch → infinite loop.

**Fix:** Use DeepSeek V4 Flash as orchestrator (`openrouter` preset). 1M context → compaction
threshold at 500K, never hit in normal multi-phase tasks. Keep Gemma as `oracle`/planner slot.

---

## ❌ PITFALL 3: Calling agent names as direct tools

**Symptom:** `invalid tool [tool=explorer]` or `invalid tool [tool=researcher]` error.

**Root cause:** Agent names (`explorer`, `researcher`, `scout`, etc.) are **not callable tools**.
The only way to invoke an agent is via the `task` tool with `subagent_type`.

**Wrong:**
```
explorer("find all .tga files")    ← throws invalid tool
```

**Correct:**
```
task(subagent_type="explorer", description="find tga files", prompt="...")
```

---

## ❌ PITFALL 4: Context limits set too high in `opencode.json`

**Symptom:** OpenCode never compacts; model errors out mid-task with context overflow.

**Root cause:** `limit.context` in `opencode.json` must match the model's REAL input token limit.
A value higher than the model's actual limit means compaction never fires, and the model itself
errors before OpenCode's compaction threshold is reached.

**Always verify against OpenRouter API before setting `limit.context`:**

| Model | Real limit |
|-------|-----------|
| `google/gemma-4-26b-a4b-it` | 262,144 |
| `deepseek/deepseek-v4-flash` | 1,048,576 |
| `qwen/qwen3.5-9b` | 262,144 |
| `z-ai/glm-4.7-flash` | 202,752 (NOT 2,000,000) |
| `google/gemini-2.5-flash-lite` | 1,048,576 |
| `xiaomi/mimo-v2-flash` | 262,144 |
| `ibm-granite/granite-4.1-8b` | 131,072 |

---

## ❌ PITFALL 5: Orchestrator repetition loops - no sampler penalties set

**Symptom:** Orchestrator prints the same sentence 10+ times ("Wait, I'll check using `task` with `explorer`… Actually, I'll just wait.") then times out.

**Root cause:** Without `frequency_penalty`/`presence_penalty`, nothing taxes repeated token sequences. A model that hesitates once will hesitate forever — each repetition is as probable as the last.

**Fix:** Add repetition penalties in `opencode.json` under the model variant's `modelKwargs`, then point the OMO-Slim preset at that variant. Do not add sampler keys directly to `oh-my-opencode-slim.json`; the plugin schema rejects unknown preset fields and falls back to default config.

```jsonc
// opencode.json
"deepseek/deepseek-v4-flash": {
  "variants": {
    "orchestrator": {
      "reasoning": { "effort": "high", "enabled": true },
      "modelKwargs": { "frequency_penalty": 0.4, "presence_penalty": 0.2 }
    }
  }
}

// oh-my-opencode-slim.json
"orchestrator": { "model": "openrouter/deepseek/deepseek-v4-flash", "variant": "orchestrator" }
```

**Rule:** Every orchestrator variant in `opencode.json` MUST have `frequency_penalty` >= 0.4. Any new orchestrator variant you add - set it immediately, not after the first stall.

| Parameter | Effect | Recommended range for orchestrator |
|-----------|--------|-------------------------------------|
| `frequency_penalty` | Taxes tokens proportional to how many times they've appeared -> directly breaks repeat loops | 0.4-0.6 |
| `presence_penalty` | Taxes any token that appeared at all -> broader novelty push | 0.2-0.3 |

**Do NOT rely on prompt instructions alone to stop repetition.** Sampler-level suppression is the only reliable fix, but it must live in `opencode.json` `modelKwargs`, not in the OMO-Slim plugin preset object.


---

## ❌ PITFALL 6: Using displayName instead of slot key as subagent_type

**Symptom:** Unknown agent type: planner is not a valid agent type (or researcher, coder, visionary)

**Root cause:** displayName in the config is **cosmetic only** (UI label). OpenCode routes by the **slot key**.

| Config slot key | displayName (UI only) | Correct subagent_type |
|---|---|---|
| `oracle` | planner | `"oracle"` |
| `fixer` | coder | `"fixer"` |
| `explorer` | researcher | `"explorer"` |
| `observer` | visionary | `"observer"` |

**Rule:** `subagent_type` = slot key. Always. The displayName is never a valid routing value.

**Every orchestrator.md and orchestratorPrompt MUST use slot keys - never displayNames - in any example or routing table.**

---

## ❌ PITFALL 7: Reusing a stale resumed session after config changes

**Symptom:** A resumed session keeps hanging on the same task even after the live config is fixed.

**Root cause:** `opencode -s <session_id>` reattaches to the old session state. If that session was created before the config repair, it can keep the poisoned control flow even while the new config loads correctly.

**Fix:** After any harness/config repair, start a fresh session against the synced config. Do not use `-s` until the new run has proven it can complete the target task.

**Rule:** Config repair and stale-session recovery are separate steps. First sync the config, then launch a new session, then validate the task on that clean run.

---

## ❌ PITFALL 8: Scout search-loop from a weak exit contract

**Symptom:** `scout` launches successfully, but it burns multiple internal turns repeating asset scans, broadening extensions, or re-scanning the same directories instead of handing back a bounded result.

**Root cause:** The routing policy said "use scout first," but the scout prompt did not force a one-pass exit once useful directory counts or candidate files were already known. The model kept treating "maybe I can find something better" as permission for another search round.

**Fix:** For CTP2/game-asset hunts, the scout prompt must require:
- one bounded pass across `Scenarios\\*\\scen0000\\default\\graphics\\pictures` and `ctp2_data\\default\\graphics\\pictures`
- at most one follow-up gamedata reference-file read
- no repeated glob for the same extension
- immediate `NEXT: handyman|fixer|observer` once directories, counts, or candidate files are known

**Rule:** Search-first does not mean search-until-satisfied. A scout task that already found the likely directories must stop and hand off.

---

## ❌ PITFALL 9: Orchestrator `timeout` set too low (60s)

**Symptom:** Session silently dies after a single subagent dispatch. No error shown. Appears as a stall.

**Root cause:** `opencode.json` `agent.orchestrator.timeout` was set to 60000ms (60s). A single subagent call (especially planner or fixer hitting a slow model) can take 90–180s. When the orchestrator turn exceeds the timeout, the session terminates mid-chain.

**Fix:** Set `agent.orchestrator.timeout` to at least 300000 (5 minutes).

```jsonc
"agent": {
  "orchestrator": {
    "timeout": 300000,   // ← was 60000; subagent calls can take 90-180s
    ...
  }
}
```

**Rule:** Never set orchestrator `timeout` below 300000. The bottleneck is subagent latency, not orchestrator thinking time.

---

## ❌ PITFALL 10: `orchestrator_conservative` variant has zero penalties

**Symptom:** After two stall resets (balanced → conservative sampler rotation), the session immediately enters a repetition loop and stalls again. The stall recovery makes things worse.

**Root cause:** `orchestrator_conservative` was set to `frequency_penalty: 0.0, presence_penalty: 0.0` to maximise determinism. But a model with zero penalties that hesitates once will repeat that hesitation indefinitely.

**Fix:** Even the conservative variant must have minimum repetition penalties:

```jsonc
"orchestrator_conservative": {
  "modelKwargs": {
    "temperature": 0.1,
    "top_p": 1.0,
    "frequency_penalty": 0.4,   // ← was 0.0
    "presence_penalty": 0.2     // ← was 0.0
  }
}
```

**Rule:** `frequency_penalty >= 0.4` on ALL orchestrator variants, including conservative. Zero-penalty conservative is the stall rotation that makes things worse, not better.

---

## ✅ Verified fix: 2026-05-23

After applying PITFALL 9 + 10 fixes to `agents/opencode.json`:

- **Test 1** (single hop): `opencode run "List files in agents/"` → orchestrator → handyman → result. Exit 0. ~2 min.
- **Test 2** (two hops): `opencode run "Read first 5 lines of orchestrator.toml and count TOMLs"` → orchestrator → handyman (both tasks in one subagent call) → result. Exit 0. ~3 min.

Both ran from `agents/` dir so `opencode.json` was discovered from CWD. No `--config` flag needed.
