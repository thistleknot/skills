---
name: harness-rsi
description: Improve an agentic harness with frozen, matched-control behavioral experiments. Use when testing prompts, tools, memory, skills, guardrails, or control flow without updating model weights.
---

# harness-rsi: edit the harness, not the model

Idiom: the model is the engine, the harness is the car. Tune the car between trips, and check each tune-up on a road you did not pick to flatter it.

The harness is every file the agent runs inside: system prompt, guardrails, memory, skills, tool guidance, scripts, subagents, middleware and hooks. Improvement means a small, pre-registered, tested change to one behavioral hypothesis, judged by a frozen evaluator against a control, then either promoted, held, rejected or marked inconclusive. No weight updates.

Layer entered: Behavioral (ordered loop with gates) over a Structural component map.

## Hypothesis under test (author's approach)

Consciousness arises from reflection.

AGI, as defined here, is reflection. Reflection with memory is sufficient for self-conscious behavior to emerge.

Definitions:

- **Reflection**: the system's operation over its own states and outputs, retained in long-term memory.
- **Self-conscious behavior**: behavior that refers to the system's own states, produced after reflection, as observed in a behavioral test.
- **IIT (operational reading, author's)**: the theorem is used as stated: more integrated computation is the measure of intelligence. The author does not adopt IIT's claims about which physical substrates can realize it.
- **Latent potential (author's view)**: vertices from geometry that interact hold latent potential for information to be stored. Ideas circulate in minds, computational or biological, and become self-evident, including the self, during reflection in long-term memory.
- **Intent**: the user's goal for the system. For the Turing test, intent is passing the test, which is a behavioral criterion.

System under test:

- An agentic harness.
- Recursive self-improvement (RSI) over a context graph.
- Semantic backpropagation as the update mechanism.
- Memory, including episodic memory.
- Reference method: Alcaraz and Julien, *Agentic GraphRAG* (O'Reilly Media, 2026).

Measurement:

- The primary metric is improvement in matching the user's intent.
- Intent is aligned with the behavioral criterion, not with an internal state.
- The test may use a sample of humans as judges.

Sufficiency criterion: if a majority of sampled humans judge that the system's output matches the intent of convincing other humans that it is human and intelligent, that is sufficient evidence of intelligence and of meeting minds.

Reading: philosophy and cognitive science (James Fetzer).

## STAGED PIPELINE

| # | Stage | Mechanism | Tag | Guards |
|---|-------|-----------|-----|--------|
| 0 | FREEZE | Fix the battery, scoring rubric, control revision and promotion rules for this round before any candidate exists | [mandatory] | R6, R7 |
| 1 | OBSERVE | Store execution traces: task, tool calls, outputs, failures, final state | [mandatory] | R2 |
| 2 | DIAGNOSE | State the earliest evidenced failure, the owning component, and one predicted observable consequence of fixing it | [mandatory] | R3 |
| 3 | PROPOSE | One behavioral hypothesis, one coherent edit. Sources: the diagnosis, prior-art search, web-council verdict | [mandatory] | R4, R5, R19 |
| 4 | PREDICT | Record the observable, the bar, and the repeat count before the run | [mandatory] | R12 |
| 5 | VALIDATE | Candidate vs control on the frozen battery, with repeats where outcomes are stochastic | [mandatory] | R8, R9, R10, R11 |
| 6 | DECIDE | Promote, hold, reject or inconclusive by the rules in R13 | [mandatory] | R13 |
| 7 | RECORD | Append the experiment to the ledger; update the CURRENT index only on promotion | [mandatory] | R14 |
| 8 | WATCH | Scheduled or triggered fresh-battery check on each promoted edit; revert on loss | [mandatory] | R15 |
| 9 | CONSOLIDATE | Merge, insert or forget memory items | [opt] flag `consolidate`; its edits pass stages 3 to 8 | R17 |
| 10 | STREAM | Run stages 1 to 8 continuously over live tasks | [opt] flag `stream`; concurrency applies to inference, never to promotion | R18 |
| 11 | JUDGE | Agentic judge scores outcomes where no deterministic check exists | [opt] flag `judge`; shadow mode first | R16 |

Default for every [opt] flag: off. A flag turns on only after the gain it claims is measured on the frozen battery.

## Component map (fill per project)

One row per component. Path alone does not grant authority; the authority column decides what this loop may edit.

| Component | Typical file | Authority |
|-----------|--------------|-----------|
| system prompt | AGENTS.md / CLAUDE.md | editable |
| memory | memory-bank files, lessons notes, plan.md scratch | editable |
| skills | SKILL.md files, skill index | editable |
| tool guidance | tool descriptions, MCP server docstrings | editable |
| scripts | helper scripts the agent calls | editable, but never the evaluator scripts (R6) |
| subagents | role definitions (orchestrator, planner, coder, debugger) | editable |
| guardrails | permission rules, enforcement hooks | platform-owned; proposals route to the owner |
| middleware | hooks that enforce validation | platform-owned; proposals route to the owner |
| evaluator | battery, rubric, control revision, promotion rules | frozen per round (R6); changed only by an evaluator round |

## EARS GUARDS

- R1 WHEN a component has no path or is platform-owned THEN this loop SHALL NOT edit it; the proposal SHALL be routed to the owner with the trace that motivates it.
- R2 WHEN a run ends THEN its trace SHALL be stored before any diagnosis begins.
- R3 WHEN diagnosing THE agent SHALL name the earliest evidenced failure, one owning component, and one predicted observable consequence of the fix. A diagnosis without a predicted observable is a guess and SHALL NOT proceed to PROPOSE.
- R4 THE round SHALL carry exactly one behavioral hypothesis. An edit MAY span several files when one coherent fix requires it. Two independent behavioral changes in one round are prohibited, whatever the file count.
- R5 WHEN proposing a new technique THE agent SHALL search for recent prior art first, with a refutation-first query, and build on proven work rather than re-deriving from pretrained priors.
- R6 THE battery, scoring rubric, control revision and promotion rules SHALL be fixed at stage 0 and SHALL NOT change within the round. Any change to them is an evaluator round, judged under the previous rules.
- R7 THE candidate and control SHALL match in model, reasoning settings, tool versions, starting state and resource limits.
- R8 THE battery SHALL contain: a target case, a boundary case, an unrelated regression case, the failing trace as a reproduction test, and at least three cases built independently of that trace. The reproduction test confirms the fix; it does not count as the only evidence.
- R9 WHERE an outcome is stochastic THE round SHALL use a pre-registered number of repeats for both candidate and control, and SHALL promote only when the gain exceeds the control's spread across repeats.
- R10 WHEN the budget expires before evidence is sufficient THEN the round SHALL record INCONCLUSIVE. THE round SHALL NOT shrink the battery or the repeats until the tested behavior is no longer exercised.
- R11 WHEN a case has no deterministic check THEN its pass or fail SHALL come from a declared observable: constraint satisfaction, a verified tool outcome, or a human assessment. A case with no declared observable SHALL NOT count toward promotion.
- R12 BEFORE the run THE agent SHALL record the predicted observable, the bar and the repeat count. AFTER the run THE agent SHALL NOT revise them.
- R13 DECISION RULES. WHEN the candidate beats the control on declared observables beyond the bar THEN promote. WHEN quality is equal and the candidate adds cost THEN reject. WHEN quality is equal and the candidate measurably reduces cost (tokens, tool calls, latency, lines) THEN promote as a simplification. WHEN the change is sound but blocked behind a pending change THEN hold and name the unblocker. WHEN evidence is short of the bar THEN record INCONCLUSIVE.
- R14 THE experiment ledger SHALL be append-only and SHALL record every round, including rejected, held and inconclusive ones. A separate CURRENT index maps each component to its active version. Only a promotion updates CURRENT. A rejected experiment SHALL NOT supersede the active configuration.
- R15 WHEN an edit is promoted THEN a scheduled or triggered fresh-battery check SHALL run at a stated interval or after a stated number of tasks, using a new construction and the frozen evaluator. IF the promoted edit loses to its predecessor THEN revert the component file to the predecessor under version control and log the evidence.
- R16 WHERE judge is on THEN it SHALL run in shadow mode, logging scores with no promotion authority, until its agreement with a labeled slice is recorded and accepted. Only then may judge scores count toward R11.
- R17 WHERE consolidate is on THEN every memory edit SHALL pass stages 3 to 8, because a memory edit changes behavior. Merges SHALL keep a pointer to what they replaced. Forgets SHALL name the evidence that made the item stale.
- R18 WHERE stream is on THEN edits SHALL still promote one at a time.
- R19 THE council verdict SHALL be an input to PROPOSE, not evidence of gain. The ledger entry SHALL link the council round id.
- R20 IF an edit would alter a digit-bearing identifier path (part numbers, IDs) THEN no spelling-correction-type transform SHALL be introduced.

## Composition with web-council

web-council generates and grounds proposals (three lenses, refutation-first search, verdicts). harness-rsi decides whether a proposal changes the harness. A council `accepted` verdict becomes a stage-3 hypothesis; stages 4 to 6 decide promotion. Do not duplicate the council ledger.

## Excluded from the default design

Each item below is excluded because it conflicts with a deployment assumption, not because it was refuted in general.

- Offline, labeled-benchmark harness search as the default loop (Meta-Harness, AHE, HarnessX style). It needs ground-truth labels and a fixed task set, which open-world task streams lack. Kept as a reference for what the validate stage measures. [empirical:cited, arxiv 2610.14224 comparison table; arxiv 2609.24972 baselines]
- Promoting edits without a control. The retrieved design tests candidates against a control to block spurious shortcuts. Attribution to arxiv 2609.11873 section 3.5.3 is unverified; check the section before relying on it. [empirical:uncited until checked]
- Judge-only promotion. Behavioral contrasts and model judgments do not establish correctness or transfer to new tasks, per arxiv 2610.14224. The judge stays in shadow mode until R16 is met. [empirical:cited, reviewer-supplied; not re-verified in this draft]
- Treating memory as plain storage. The cited framing stresses structured storage, scheduling and processing, with retrieval and invocation of the right experience as the failure point. [empirical:cited, arxiv 2512.23343; arxiv 2608.24876]

## Preconditions and failure modes

- Preconditions: harness files under version control (revert is one command); the evaluator frozen at stage 0; traces stored; a battery meeting R8.
- Failure: an edit promoted on one passing case. Fix: R8 and R9.
- Failure: the candidate search gradually turns the battery into a training set. Fix: fresh constructions at each R15 check; the battery is never edited to fit a result.
- Failure: the harness grows monotonically. Fix: R13 rejects equal-quality additions; stage 9 merges and forgets.
- Failure: a confident patch to the wrong cause. Fix: R3 requires a predicted observable that the trace can falsify.
- Failure: judge drift or uncalibrated judge. Fix: R16 shadow mode and recalibration.
- Failure: hindsight-fitted predictions. Fix: R12.

## Output of one round (one paragraph)

Hypothesis in one line; owning component; edit; predicted observable and bar; repeat count; control vs candidate result; verdict (promote, hold, reject or inconclusive); ledger entry id; next WATCH date.
