---
name: inflight-request-queue
description: >
  Keep a bounded number of independent blocking I/O requests in flight (a "queue of N", often 2)
  instead of issuing them strictly sequentially, to overlap the round-trip + server compute and
  eliminate idle gaps. Use when making many INDEPENDENT calls in a loop to a local model server
  (Ollama / vLLM / TGI), a REST API, or a database — anywhere a sequential blocking loop leaves the
  server idle while the client packages and sends the next request. Covers the thread-pool /
  asyncio-semaphore pattern, order preservation, fail-fast error propagation, the server-side
  concurrency prerequisite (e.g. OLLAMA_NUM_PARALLEL), why "more in flight" is not always better,
  and the rule to benchmark the real speedup. Trigger on: a `for`-loop of blocking API/LLM/DB calls,
  "this is slow / serial", LLM-as-judge batch scoring, embedding/generation fan-out.
---

# In-Flight Request Queue (bounded concurrency for independent I/O)

## The problem
A naive loop over independent I/O calls blocks fully on each one:
```python
for item in items:
    results.append(call(item))   # send -> WAIT (round-trip + server compute) -> next
```
While you wait, the server is idle; then you package-and-send the next request; then the server
works while *you* sit idle. The two never overlap. For N calls of latency L, wall-clock ≈ N·L.

## The fix: keep K requests in flight
Issue up to K calls concurrently (**K=2 is the common sweet spot for a single local model
server**). While request i is computed server-side, request i+1 is already queued/sent.
Wall-clock ≈ N·L / (effective server concurrency).

```python
from concurrent.futures import ThreadPoolExecutor

def run_many(items, call, k=2):
    out = [None] * len(items)
    with ThreadPoolExecutor(max_workers=k) as ex:
        futs = {ex.submit(call, it): i for i, it in enumerate(items)}
        for fut, i in futs.items():
            out[i] = fut.result()    # re-raises -> fail-fast, never a silent gap
    return out
```
- **Threads** for blocking I/O (urllib/requests/db drivers release the GIL while waiting). Use
  **asyncio + `Semaphore(k)`** instead if the client library is async-native.
- **Order-preserving** — index the futures; never rely on completion order.
- **Fail-fast** — `fut.result()` re-raises, so a genuinely failed item aborts rather than producing
  a silent gap. NEVER fabricate a placeholder result to fill a hole.

## Prerequisites & caveats
- **The server must actually allow K concurrent requests**, or you gain nothing (they queue
  server-side — correct, just no speedup). Ollama: `OLLAMA_NUM_PARALLEL >= K`. DB: `pool_size >= K`.
  API: watch rate limits.
- **More is not always better.** Past the server's real parallelism (or its memory budget), extra
  in-flight requests add contention/latency, not throughput. For one local model, K=2–4 is usually
  the whole win. Bound K; don't unleash N.
- **Preserve error semantics.** Whatever the sequential version did on failure (raise / retry), the
  concurrent version must do the same. Concurrency is an orchestration change, not a correctness
  change.
- **Independent items only.** For calls with no ordering dependency. Do NOT pipeline calls where
  N+1 depends on N's result.

## Always measure
The speedup depends entirely on whether the server supports the concurrency, so confirm it with a
real A/B (sequential vs queued, same workload, wall-clock) and report the **measured** number — not
"should be faster." A queue in front of a `num_parallel=1` server is a no-op dressed up as a win.
