# autoresearch Feature Topology

**Source:** `karpathy/autoresearch` @ `228791fb499afffb54b46200aca536f79142f117`  
**Clone:** `/home/user/harness/integrate/autoresearch`  
**Purpose:** A very small autonomous-ML-research harness centered on one real training program, one fixed evaluation envelope, and one keep-or-discard loop. The most portable value is not the sci-fi "swarm" framing from the README; it is the operational contract: narrow mutable surface, immutable eval harness, fixed wall-clock budget, scalar reward, and branch-backed experimental progression.

---

## Topology Overview

```text
HUMAN ORG-CODE LAYER ───────────────────────────────────────────────────────────
  program.md
       │
       ├── defines the researcher policy
       ├── sets branch discipline
       ├── constrains editable surface
       ├── defines keep / discard logic
       └── turns a generic coding agent into an autoresearch worker

EXPERIMENT CONTROL LOOP ────────────────────────────────────────────────────────
  inspect repo
    -> edit train.py
    -> git commit
    -> run `uv run train.py > run.log 2>&1`
    -> grep val_bpb / peak_vram_mb
    -> append results.tsv
    -> keep commit if better
    -> reset if equal / worse / crash

IMMUTABLE EVAL ENVELOPE ───────────────────────────────────────────────────────
  prepare.py
       │
       ├── fixed data source + tokenizer build
       ├── fixed TIME_BUDGET = 300s
       ├── fixed MAX_SEQ_LEN / eval token budget
       ├── fixed val_bpb evaluation harness
       └── read-only substrate for all experiments

MUTABLE MODEL SURFACE ─────────────────────────────────────────────────────────
  train.py
       │
       ├── GPT architecture
       ├── attention pattern
       ├── optimizer implementation
       ├── hyperparameters
       ├── batch sizing
       └── training loop details

EXPERIMENT LEDGER ─────────────────────────────────────────────────────────────
  git branch autoresearch/<tag>
  +
  untracked results.tsv
       │
       ├── commit
       ├── val_bpb
       ├── memory_gb
       ├── keep / discard / crash
       └── short experiment description

RUNTIME SUBSTRATE ─────────────────────────────────────────────────────────────
  single NVIDIA GPU
  uv-managed Python environment
  local cache at ~/.cache/autoresearch
```

---

## Feature Inventory

### RESEARCHER POLICY AS MARKDOWN

**`program.md as org code`**  
The repo does not embed an agent runtime. Instead, it externalizes the researcher's operating rules into `program.md`: setup sequence, branch naming, allowed edits, forbidden edits, experiment loop, timeout handling, crash handling, and indefinite autonomy.

**Migration value:** extremely high. This is the cleanest reusable pattern in the repo. `program.md` behaves like a lightweight skill or task contract that can be transplanted into Copilot, OpenCode, Aider, Pi, or a manager-led harness.

### NARROW MUTATION BOUNDARY

**`train.py is the only editable research surface`**  
All meaningful experimentation is concentrated in one file: architecture, optimizer, schedules, batch sizing, and training logic.

**`prepare.py is explicitly read-only`**  
Data loading, tokenizer training, fixed constants, and evaluation logic are locked down and treated as the benchmark substrate rather than part of the search space.

**`pyproject.toml is fixed`**  
No dependency churn is allowed inside the experiment loop.

**Migration value:** extremely high. This is a strong harness pattern: freeze the benchmark envelope, expose a single mutable wedge, and make attribution of gains much cleaner.

### FIXED-BUDGET EXPERIMENT LOOP

**`TIME_BUDGET = 300`**  
Runs are normalized to a fixed five-minute wall-clock training budget in `prepare.py`.

**`val_bpb` as the scalar reward**  
The score is validation bits-per-byte, not a task-specific accuracy metric. Lower is better, and the README explicitly frames this as comparable across vocab choices.

**`timeout / crash semantics`**  
`program.md` tells the agent to treat runs over ten minutes as failures and to log crashes distinctly.

**Migration value:** highest-priority. This repo is basically a compact worked example of "define a reward, cap the budget, loop autonomously."

### KEEP / DISCARD STATE MACHINE

**`advance on improvement`**  
The branch advances only when the new commit improves `val_bpb`.

**`reset on failure or non-improvement`**  
Equal-or-worse runs are explicitly reverted rather than allowed to accumulate into state drift.

**`results.tsv` as the experiment log**  
The ledger is intentionally simple and untracked: commit hash, score, memory, status, description.

**Migration value:** very high. The state machine is trivial but durable: mutate -> evaluate -> keep or revert. A stronger harness can preserve this contract while swapping TSV for sqlite/MLflow.

### REPRODUCIBLE DATA + TOKENIZER SUBSTRATE

**`prepare.py downloads a pinned dataset shard set`**  
The code downloads parquet shards from `karpathy/climbmix-400b-shuffle`, reserves the last shard for validation, and caches everything under `~/.cache/autoresearch`.

**`tokenizer is trained once and reused`**  
Tokenizer artifacts and token-byte lookup are cached and then consumed by the training loop and eval code.

**`runtime utilities are shared from prepare.py`**  
The training script imports the tokenizer, dataloader, and `evaluate_bpb` directly from the fixed prep module.

**Migration value:** high. The pattern of "build benchmark substrate once, then hold it fixed" is portable even if the exact dataset is not.

### SELF-CONTAINED TRAINING PROGRAM

**`single-file training core`**  
`train.py` contains the GPT model, Muon+AdamW optimizer logic, schedules, training loop, final eval, and printed result summary.

**`hardware-targeted tuning`**  
The baseline is clearly tuned for a single NVIDIA GPU and even names H100 throughput assumptions in the logging path.

**Migration value:** medium. The "single-file editable model lab" is useful as a substrate, but the exact code is workload-specific rather than a general orchestration primitive.

### EXTERNAL-AGENT RUNTIME ASSUMPTION

**`bring your own agent`**  
The README explicitly assumes you launch Claude, Codex, or another coding agent in the repo and point it at `program.md`.

**`permissions disabled`**  
The suggested usage assumes the surrounding agent runtime can be permission-constrained.

**Migration value:** high. The repo is not a control plane; it is a substrate contract meant to be driven by an external harness.

---

## What Is Actually Portable

### HIGH-VALUE PORTABLE PATTERNS

**`org-code prompt as the real harness surface`**  
The core system behavior lives in `program.md`, not in framework-specific orchestration code.

**`immutable benchmark / mutable candidate split`**  
Freeze the evaluator and allow changes only in the candidate implementation surface.

**`fixed-budget scalar hill-climbing`**  
Every candidate gets the same wall-clock budget and the same score extractor.

**`branch progression only on measured improvement`**  
Keep state monotonic. Do not let failed ideas contaminate the branch.

**`lightweight experiment ledger`**  
Even a simple TSV is enough to turn the loop into something auditable.

### PORTABLE WITH ADAPTATION

**`single editable file`**  
Great for a minimal prototype, but most real harnesses will need a slightly wider editable set or a generated patch surface.

**`grep-based metric extraction`**  
Works for a tiny repo; larger systems should emit structured JSON, sqlite rows, or MLflow metrics instead of parsing logs.

**`results.tsv`**  
Portable conceptually, but likely better replaced with sqlite or MLflow for concurrent or long-lived campaigns.

### REFERENCE-ONLY / NOT THE MAIN VALUE

**`swarm rhetoric`**  
The README talks about autonomous swarms, but the baseline implementation is actually a single-agent research loop with one human-authored program file.

**`single-GPU H100-centric defaults`**  
Important for the reference implementation, not for the harness pattern itself.

**`Python-training-specific substrate`**  
The exact model/trainer code does not generalize broadly; the loop contract does.

---

## Harness Adaptation Notes

### FOR `agentic-harness`

Treat `program.md` as the **proposal policy** and wrap it with stronger legality gates:

1. lock the benchmark substrate (`prepare.py`, dependencies, evaluator)
2. expose only the intended mutation surface (`train.py` or a defined subset)
3. run the candidate in a bounded execution envelope
4. extract the score structurally
5. keep / revert based on measured delta
6. log the attempt into a durable ledger

This is the smallest clean example in the wild of a reward-driven code-improvement loop over a real ML workload.

### FOR `opencode`, `aider`, `pi`, OR COPILOT CLI

The portable transplant is:

- **task contract:** `program.md`
- **edit boundary:** `train.py`
- **fixed benchmark:** `prepare.py`
- **run command:** `uv run train.py > run.log 2>&1`
- **metric extractor:** `grep "^val_bpb:\|^peak_vram_mb:" run.log`
- **state machine:** keep on improvement, revert otherwise

That gives you the behavioral core without importing the repo's exact training code.

### FOR A STRONGER FACTORY

The immediate upgrades over the baseline are obvious:

- replace `results.tsv` with sqlite or MLflow
- emit structured run artifacts instead of grep-only logs
- add parallel worker lanes across GPUs / branches
- formalize keep / discard as a verifier gate
- archive rejected candidates and their metrics
- separate proposer, runner, and critic roles instead of overloading one agent

---

## Bottom-Line Classification

| Area | Verdict | Why it matters |
|---|---|---|
| Research-loop contract | **Primary value** | Clean mutate -> run -> score -> keep/revert loop |
| `program.md` prompt surface | **Primary value** | Human-authored org code is the real reusable harness seam |
| Fixed-budget scalar evaluation | **Primary value** | Makes autonomous improvement measurable and comparable |
| Single-file training substrate | **Useful reference** | Good demo workload, but not the key transferable idea |
| Swarm framing | **Mostly narrative** | The actual implementation is one agent + one prompt contract |
| Control-plane architecture | **Absent** | No built-in session router, queue, safety layer, or multi-agent manager |

**Bottom line:** `autoresearch` is not a general agent framework like OpenClaw or gstack. It is more valuable as a **minimal reward-driven experimentation pattern**: freeze the evaluator, narrow the edit surface, give an external coding agent an explicit org-code prompt, and let it hill-climb on a real metric. That pattern is highly portable into your agentic harness work.
