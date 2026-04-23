---
name: agentic-harness
description: >
  Protocol for debugging, iterating on, and verifying automated LLM pipeline harnesses
  (dark software factories, code-generation wrappers, multi-stage agentic systems).
  Use when a harness produces incoherent output, gate failures, LLM truncation bugs,
  test-generation failures, or violation-count divergence. The core contract: set a
  coherence=False todo at task start and iterate until you can flip it to True.
---

# Agentic Harness Skill

## Core Contract — The Coherence Flag

**Before touching any harness code**, register a coherence sentinel in SQL:

```sql
INSERT INTO todos (id, title, description, status) VALUES
  ('coherence', 'Harness coherence', 
   'All known incoherence sources resolved; pipeline completes a representative run without divergence',
   'in_progress');
```

The flag stays `in_progress` (coherence=False) until every root cause in the
**Incoherence Checklist** is cleared and a live run confirms it.  
Flip it only when the pipeline actually passes:

```sql
UPDATE todos SET status = 'done' WHERE id = 'coherence';
-- coherence = True
```

> "Did you fulfill this request?" — answer only after the todo is `done`.

---

## Incoherence Checklist

Work through these in order; each is a potential root cause for a harness that
produces degraded or diverging output.

### 1. Sentinel objects fed back to the LLM
- Never return a sentinel dict (e.g. `{"kind": "ParseError", ...}`) from a
  parse function and pass it to a downstream LLM call.
- The LLM treats the sentinel as content and generates responses around it,
  creating new files / new import chains → violation count grows each round.
- **Fix**: return `[]` / `{}` / `None` on parse failure; log a warning instead.
  Salvage partially-truncated JSON by slicing at the last `}` before `]`.

### 2. Gate timeouts as false negatives
- Long-running shell commands in gates (e.g. `pip install -e .`) take 30-40 s
  to *fail* when the target file doesn't exist.  Combined with an OR chain they
  can exceed the gate timeout and return exit=-1.
- **Fix**: guard expensive operations behind file-existence checks:
  ```bash
  ([ -f pyproject.toml ] || [ -f setup.py ]) && pip install -e '.[dev]' -q \
    || pip install -r requirements.txt -q 2>/dev/null || true
  ```
- After fix, measure: gate that took 83 s → 1.2 s.

### 3. LLM output truncation mid-structure
- At `max_completion_tokens=4096`, the LLM truncates mid-JSON.
- **Fix pattern**:
  ```python
  def _salvage_json_array(raw: str) -> list:
      last_brace = raw.rfind("}")
      if last_brace == -1:
          return []
      candidate = raw[: last_brace + 1].rstrip() + "]"
      # find opening bracket
      start = candidate.find("[")
      if start == -1:
          return []
      try:
          return json.loads(candidate[start:])
      except json.JSONDecodeError:
          return []
  ```
- Always validate completeness: check for a sentinel like `# END OF FILE` or
  verify the JSON is syntactically closed before accepting the response.

### 4. Violation-count divergence (getting worse, not better)
- Symptom: violations grow round-over-round (7 → 12 → 11 → 26).
- Diagnosis: either sentinel objects (see #1) or the LLM is introducing new
  imports / files to fix existing violations, creating a cascade.
- **Distinguish import violations from LLM-reported violations**:
  - Import violations (from actual Python import attempts) are authoritative.
  - LLM-reported NameErrors / style issues are advisory; treat as soft.
- Hard-stop after `MAX_ROUNDS` and pass residual violations forward rather than
  cycling forever.  Residual LLM-only violations are usually false positives.

### 5. Test generation producing empty output
- Symptom: `generate_tests` discards all files; 0 test files written.
- Common cause: the generated source has broken imports (pygame, cv2, etc.)
  that cause `CollectionError` at pytest collection time.
- **Fix options**:
  - Have tests use inline stubs rather than importing real modules.
  - Inject `SDL_VIDEODRIVER=dummy DISPLAY=:99` before collection.
  - Generate a `conftest.py` that mocks heavy deps before any import.
- Continuation limit: if a test file generation hits 5 continuation turns and
  still has a `SyntaxError`, discard and move on; don't block the pipeline.

### 6. Full pipeline retry vs. targeted fix
- Pipeline retry on gate failure triggers full re-implementation (expensive).
- Before accepting a retry, confirm the gate failure is a *real* code defect,
  not a harness timing/tooling issue (see #2).
- Fix the harness first; only then let the pipeline retry the generated code.

---

## Observability Pattern for Long-Running Harness Runs

```bash
# Start
nohup python -m dark_factory "prompt" --output /tmp/gendir > /tmp/run.log 2>&1 &
echo "PID $!"

# Monitor
tail -f /tmp/run.log

# Key log signals to watch for:
# GOOD:  "reconcile_audit round N: M violation(s) (K from import check)"  — K decreasing
# GOOD:  "generate_tests: N files"                                         — N > 0
# GOOD:  "gate install_deps: exit=0"
# BAD:   "reconcile_audit round N: M violation(s) (0 from import check)"  — M growing
# BAD:   "ReadTimeout on attempt N" × 3+                                  — server overloaded
# BAD:   "Test for X truncated at turn 5" / SyntaxError                   — test discard
# BAD:   "gate install_deps: exit=-1"                                      — gate timeout bug
```

**ReadTimeout handling**: `MAX_RETRIES=4`, backoff `[2, 5, 10, 20]` seconds.
Silence in the log after a retry message = generation in-flight (not hung).
DEFAULT_TIMEOUT = 300 s per attempt.  A 216-second generation is slow but valid.

---

## Dark Software Factory — Specific Internals

These apply to the `dark_factory` harness at `/home/user/harness`:

| Constant | File | Value | Notes |
|---|---|---|---|
| `_MAX_ROUNDS` | `reconcile.py:23` | 4 | Fix+audit cycles; round counter is 0-based internally, displayed 1-based |
| `_SNAPSHOT_CHARS` | `reconcile.py:24` | 32 000 | Source fed to audit/fix LLM; fills most of 48K context for large projects |
| `GATE_TIMEOUT` | `gates/runner.py:14` | 120 s | Gate shell command hard cap |
| `MAX_RETRIES` | `llm.py:308` | 4 | LLM HTTP retries before raising |
| `DEFAULT_TIMEOUT` | `llm.py:49` | 300 s | Per-attempt HTTP timeout |

**Pipeline flow**: PM → implement → reconcile (audit/fix loop) → generate_tests → install_deps gate → verify → [retry ×3]

**LLM tiers**:
- `heavy` → `local-qwen` (Qwen3.6-35B-A3B, 127.0.0.1:8081, ~15-20 tok/s, 4096 max out)
- `fast`/`standard` → `copilot-proxy` (192.168.3.122:8069, gpt-4o / gpt-4.1 / claude-sonnet-4)

**Reconcile route logic** (`reconcile.py:231`):
```python
if state["violations"] and state["round"] < state["max_rounds"]:
    return "fix"   # continue loop
return END         # pass residuals to verify
```
Note: `round` increments *after* fix, so 4 fix passes happen before the `< 4` guard closes.

**Test stub pattern**: tests use inline class stubs, not real `src.*` imports.
This avoids pygame `ImportError` at collection time but means test coverage
of the real implementation requires a separate integration pass.

---

## Iteration Protocol

1. **Identify**: run the pipeline; capture log; label each failure by checklist item number.
2. **Prioritize**: fix structural incoherence (#1 sentinels, #2 gate races) before
   surface symptoms (#5 test generation), because structural bugs cause cascading failures.
3. **One fix per commit**: keep the causal chain legible; don't batch unrelated fixes.
4. **Verify the fix in isolation** before re-running the full pipeline:
   - For gate bugs: time the gate command directly in shell.
   - For parse bugs: feed a known-truncated fixture through the parse function.
   - For LLM-output bugs: replay the prompt with a checkpoint.
5. **Re-run pipeline on a representative prompt** (same complexity as the failing case).
6. **Check the coherence flag criteria** — only flip when *all* items are cleared.

---

## Checklist Before Flipping coherence → True

- [ ] Violation count converges (decreases) across reconcile rounds
- [ ] Gate `install_deps` exits 0 in < 5 s for projects without pyproject.toml
- [ ] `generate_tests` produces ≥ 1 test file per source module
- [ ] No ParseError sentinel fed to any downstream LLM call
- [ ] Pipeline completes without `retry` for a straightforward prompt
- [ ] All tests in the generated project pass (or known skips are documented)
