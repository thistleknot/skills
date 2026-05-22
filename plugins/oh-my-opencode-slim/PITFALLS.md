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
task(subagent_type="researcher", description="find tga files", prompt="...")
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
