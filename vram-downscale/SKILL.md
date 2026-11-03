---
name: vram-downscale
status: active
last_validated: 2026-07-29
description: >
  Run GPU training at the full card and BREAK loudly on overflow instead of silently
  paging, then downscale one memory knob and resume from the last checkpoint. Use when
  launching any training, fine-tuning, or batched-inference run on a fixed-VRAM card,
  especially under Windows/WDDM where the driver pages instead of raising OOM. Covers
  allocator-enforced ceilings, free-VRAM-derived sizing, the batch_size=1 antipattern,
  deriving max_length from measured token lengths, and the trip/downscale/resume ladder.
  Trigger on "out of memory", "OOM", "batch size", "max_length", "sequence length",
  "gradient checkpointing", "fits in 16GB", a run that got slow instead of failing, or
  system RAM ballooning during GPU work.
---

# VRAM downscale — break on overflow, then step down and resume

## The law

**Run at the full card. Break if you exceed it. Downscale one knob, resume from the last
checkpoint, repeat.** Never size a run below the card "to be safe" — that silently costs
throughput on every run forever. Size it to the wall and make the wall loud.

## Why this is not optional on WDDM

A Windows display GPU **does not OOM on overflow — it pages into system RAM.** A run that
wants 20 GB on a 16 GB card does not fail. It succeeds, 10x slower, and the only symptom is
system RAM ballooning. Observed 2026-07-29: a training probe ran beside a resident Ollama
model, together crossed 16 GB, and RAM went to ~64 GB with **no error anywhere**.

So the three things that look like protection and are not:

| signal | proves | does NOT prove |
|---|---|---|
| process exists (`Get-Process`, `ps`) | a PID | that it holds VRAM, or is doing work |
| `nvidia-smi` utilization | the GPU is occupied | progress — a paging/deadlocked run reports 50-60% |
| polling used-VRAM | what happened | anything preventive — by the time a poll reads 16.5 GB, it already paged |

## Enforcement: cap the allocator, do not poll

```python
free_b, total_b = torch.cuda.mem_get_info()
usable = min(free_b // MIB - SAFETY_MIB, CEILING_MIB)   # 16384 on a 16 GiB card
if usable < MIN_WORKING_SET_MIB:
    raise VramCeilingExceeded(...)                      # abort: cannot fit, do not start and hope
torch.cuda.set_per_process_memory_fraction(usable / (total_b // MIB))
```

`set_per_process_memory_fraction` is the only mechanism that actually breaks: a request past
the cap raises `torch.cuda.OutOfMemoryError` instead of being satisfied by paging. That turns
a silent 10x slowdown into an immediate, debuggable failure.

**Derive the ceiling from what is FREE, not from card capacity.** A display GPU routinely has
~10 GB already committed by things unrelated to training — a resident Ollama model
(`keep_alive` keeps it loaded AFTER its stage ends; a 9B at 256k ctx is ~9.9 GB), plus the
desktop compositor, explorer, a media player, a game launcher. Sizing against "16 GB total"
is wrong by however much someone else holds. **Check `ollama ps` before blaming your own run.**

Units: `nvidia-smi` speaks MiB, torch speaks bytes, and 16384 MiB = 17.18e9 bytes. Mixing them
is a silent 7% error. Pick MiB and stay there.

## Before adding a knob, check the sizing is not simply wrong

**`batch_size=1` is a smell, not a constraint.** Measure before accepting it:

```python
lens = [len(tok(render(r))["input_ids"]) for r in records]
print(max(lens), np.percentile(lens, 95))
```

Observed 2026-07-29: `max_length=512` against a measured **max of 172 tokens** — **81% of
every batch was padding**, and those padded activations were what forced `batch_size=1`.
Fixing the length made the batch affordable and the run ~4x faster.

- Set `max_length` from the **measured global max + ~8% slack, rounded to /8** for tensor cores.
- Then swap `batch=1 x accum=N` for `batch=N x accum=1`. **Identical effective batch, identical
  optimization trajectory, N times fewer steps.** This is free speed, not a tradeoff.
- Static state dominates a full fine-tune: for 0.87B params in fp32 with `paged_adamw_8bit`,
  weights 3.5 + grads 3.5 + optimizer 1.7 = **8.7 GB before a single token**. If that plus
  activations does not fit, the answer is a smaller model or PEFT, not a smaller batch.

## The ladder — what actually moves peak memory at batch_size=1

Do **not** scale `gradient_accumulation_steps` down: accumulation exists to keep peak low by
processing fewer samples at a time. Fewer accumulation steps means a larger live batch and
*more* memory. Scaling it is backwards.

| rung | knob | effect | cost |
|---|---|---|---|
| 0 | baseline, full ceiling | — | none |
| 1 | `gradient_checkpointing=True` | ~40% off activations | ~30% slower, **changes no data** |
| 2+ | `max_length` x0.95, repeatedly | activations scale with sequence length | truncates content — real experimental damage |

Checkpointing is rung 1 because it buys the most memory per unit of damage. `max_length`
comes after because truncation alters what the model sees, which corrupts the experiment
rather than merely slowing it. `fp16` and 8-bit optimizers are prerequisites, not rungs.

## Trip → downscale → resume

```
run at rung i
  └─ OOM?  →  empty_cache()  →  persist rung i+1 to disk  →  resume from last checkpoint
       └─ trip again? → rung i+2 …
            └─ ladder exhausted → STOP. This is a sizing problem, not a scheduling one:
               shrink the model, the data, or the eval batch. Do not loop.
```

**Persist the rung to disk, not memory.** The spec is *kill* then resume, so the retry may be
a fresh process. A rung held in memory resets to baseline on every relaunch and the backoff
loops forever without ever stepping down.

**Checkpointing is what makes killing cheap, and cheap killing is what makes the whole thing
work.** Without mid-run checkpoints every trip restarts from zero, so a stall feels expensive
to act on, so it gets tolerated — and that is how hours disappear. Earn the right to be
trigger-happy by making resume free.

## Serialize, and re-check

One card means one job. A gate that verifies a free GPU **at launch and never again** does not
prevent a second process starting beside yours — which is exactly how the 2026-07-29 overflow
happened. Either serialize all GPU work through one launcher, or re-check during the run.

## Related

`stat-partitioning` (derive the numeric bound, never guess it) · the stall/resume contract in
the operating core §4 (this skill is its memory-shaped sibling: same break-and-resume
structure, VRAM as the trigger instead of time).
