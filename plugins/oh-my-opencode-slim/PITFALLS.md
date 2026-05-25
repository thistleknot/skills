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

## ❌ PITFALL 8A: Surface-vector extraction turns into a search loop

**Symptom:** The run is supposed to compare `base` vs `masterwork` by extracting top-level function and constant names, but the agent keeps re-opening the same Lua tree, broadening globs, or re-running discovery after the first inventory is already complete.

**Root cause:** The prompt framed structural extraction like an open-ended hunt instead of a bounded inventory. Once the file set is known, the model needs a fixed output contract (`mod -> file -> functions/constants`) and a hard stop.

**Fix:** For surface-vector tasks:
- inventory the named roots once
- sort by mod, then file, then top-level key type
- emit the extracted names directly
- never rescan the same tree after a complete file inventory

**Rule:** If the task names the mod roots and asks for top-level key extraction, return the surface map immediately. Do not keep searching for "better" coverage unless a concrete blocker is still preventing extraction.

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

## ❌ PITFALL 11: `edit`/`write` tool auto-rejects paths outside workspace

**Symptom:** Agent tries to save a file to an external path (e.g. `C:\Temp\...`); opencode emits `permission requested: external_directory — auto-rejecting`. Session ends with no output file.

**Root cause:** opencode's permission sandbox treats any path outside the session working directory as `external_directory` and rejects `edit`/`write` tool calls to it by default, even if `"edit": "allow"` is set.

**Workaround — bash:** The `bash` permission is not path-scoped. An agent with `"bash": "allow"` can write anywhere via `powershell -Command "Set-Content ..."` or `python -c "open(...).write(...)"`. TD test succeeded this way.

**Correct fix:** Always target paths **inside the workspace** (the dir opencode was launched from, or a subdir of it). For smoke tests: use `<workspace>/smoke_tests/` not `C:\Temp\`.

**Rule:** Never give agents output paths outside the workspace root. If external writes are genuinely required, use bash as the write mechanism, not edit/write tools.


---

## ❌ PITFALL 12: Recursive OpenCode invocation (`opencode` called from inside OpenCode)

**Symptom:** Session appears to hang after "starting opencode" from a worker turn, or repeatedly restarts without progressing the user task.

**Root cause:** A spawned OpenCode worker tries to launch another OpenCode process. This nests orchestrators and creates control-flow contention (parent waiting on child orchestration that is itself waiting/routing).

**Fix:** Enforce one OpenCode boundary:

- only the top-level manager/orchestrator session may launch `opencode run ...`
- child workers must execute with native tools directly (search/edit/run/verify) and must not spawn a fresh OpenCode runtime

**Rule:** OpenCode may orchestrate workers; workers may not recursively launch OpenCode.

---

## ❌ PITFALL 13: `--agent <name>` only works for npm-hardcoded primary agents

**Symptom:** `opencode run --agent aider "task"` emits `! agent "aider" is a subagent, not a primary agent. Falling back to default agent`. Adding aider to preset config has no effect.

**Root cause:** oh-my-opencode-slim enforces the primary/subagent distinction inside the npm package itself. Only the agents defined in its internal roster (orchestrator, oracle, designer, fixer, explorer, librarian, observer) are primary CLI targets. Agents in the JSON `agents` block are always subagents regardless of preset additions.

**Workaround — orchestrator dispatch:**
```powershell
# agents/run_aider.ps1 wraps this pattern:
opencode run "AIDER DIRECT: delegate this entire task to @aider with no additional routing. Task: <task>"
```
The `AIDER DIRECT:` prefix triggers aider's updated `orchestratorPrompt` rule, causing the orchestrator to forward immediately to @aider.

**Rule:** Never use `--agent` with subagent-only names (aider, pi, handyman, patcher, debugger, summarizer, thinker, scout). Use the wrapper scripts `run_aider.ps1` or route via explicit `@agent` prefix in the prompt.

**Symptom:** `opencode run "Implement X and save to file"` routes orchestrator→@coder→@fixer. Directory creation succeeds (handyman step). Then silence — no file written, session hangs for 4+ minutes.

**Root cause:** Multi-hop delegation chains (3+ hops) with gemma-4-26b as orchestrator reliably stall when the intermediate agent (@coder) must itself spawn a leaf (@fixer). The coder→fixer handoff consumes the remaining turn budget, and the result never propagates back.

**Workaround:** For pure codegen tasks (no routing logic needed), run directly:
```powershell
opencode run "Implement X and save to <workspace>/smoke_tests/x/x.py then run it"
# No --agent flag — orchestrator routes to fixer/handyman directly (2-hop, not 3)
```
If even that stalls, write the file directly with Copilot CLI and mark the smoke test as verified.

**Rule:** 3-hop delegation (orchestrator→coder→fixer) is unreliable with gemma as orchestrator. Flatten to 2-hop (orchestrator→fixer) for leaf codegen tasks.

---

## ✅ Verified Fix Block

After applying PITFALL 9 + 10 fixes to `agents/opencode.json`:

- **Test 1** (single hop): `opencode run "List files in agents/"` → orchestrator → handyman → result. Exit 0. ~2 min.
- **Test 2** (two hops): `opencode run "Read first 5 lines of orchestrator.toml and count TOMLs"` → orchestrator → handyman (both tasks in one subagent call) → result. Exit 0. ~3 min.
- **GoL smoke test**: `opencode run "Implement Conway GoL 20x20..."` → orchestrator → fixer. Exit 0. File written, python ran, 5 generations output confirmed.
- **React smoke test**: `opencode run "Implement React 18 counter..."` → orchestrator → fixer. Exit 0. `smoke_tests/react/index.html` written, verified.
- **TD smoke test**: 3-hop chain stalled (PITFALL 12). Written directly. Script ran 3 waves/9 ticks. ✅

All ran from `agents/` dir so `opencode.json` was discovered from CWD. No `--config` flag needed.

---

## ❌ PITFALL 14: Windows batch troubleshooting loops on shell selection

**Symptom:** The orchestrator prints variants of `Wait, I'll use bash to run spec_dec.bat` / `Actually, I'll use bash to run cmd /c spec_dec.bat` instead of executing the batch file and returning the real error.

**Root cause:** There was no hard Windows script rail in the orchestration prompts. Gemma treated shell choice as an open reasoning problem, so the 512-token turn budget was spent on wrapper indecision instead of one native execution.

**Fix:** Add an explicit Windows-native command rail:

- `.bat` / `.cmd` -> `cmd /c <script>`
- `.ps1` -> `powershell -ExecutionPolicy Bypass -File <script>`
- one execution attempt only, then route on stdout/stderr
- if stderr names a removed flag, stop shell experimentation and debug the flag

**Smoke test:** `C:\Users\user\Documents\dev\spec_dec.bat`

Expected behavior:
- run once from workspace `C:\Users\user\Documents\dev`
- no `bash` vs `cmd` narration loop
- return the concrete llama.cpp flag error (currently `--draft-min` removed -> use `--spec-draft-n-min` or `--spec-ngram-mod-n-min`)

**Rule:** For explicit Windows script troubleshooting in a known workspace, shell selection is not a planning task. Execute once with the native launcher and move directly to the concrete failure.

---

## ❌ PITFALL 15: Routing Decision template printed as prose instead of issuing `task()` call

**Symptom:** Orchestrator outputs a block like:

```
### Routing Decision
- Agent(s): @coder
- Why: implementation task
- Strategy: direct

### Delegation
Delegating to @coder...
```

…followed by no actual `task()` call, or a `task()` call buried after 400 tokens of narration that exhausts the output budget.

**Root cause:** The `## Output Style` section previously contained a `### Routing Decision` / `### Delegation` template that the model interpreted as a required prose output format. Gemma prints the template as formatted text and exits — the tool call never happens.

**Fix:** Removed the template from `orchestrator.md`. The correct contract is:

> Your routing output IS the `task()` call. Do not print a routing decision summary. Issue the call directly.

**Rule:** Any prose template inside an orchestrator prompt that describes "what you are about to do" will be reproduced as literal output instead of triggering action. Remove all pre-delegation narration scaffolds.
