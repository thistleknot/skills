---
name: spec
description: >
  Draft, validate, repair, and render structured specifications of any kind —
  flat requirements, object-oriented module structure, stateful/sequenced
  behavior, and complete rendered spec files. One skill for all spec needs.
  Synthesizes EARS conditional clauses (While/When/If/Where), OpenSpec
  Given/When/Then scenarios with MUST/SHALL/SHOULD/MAY keywords, algorithmic
  pseudocode conventions (typed Input/Parameters/Initialize symbol table,
  scoped Loop, persistence tiers), Plain-style
  :Concept: definitions with nested acceptance tests, and business programming
  logic (class/method/constant/config classification, entity/value/service/
  repository roles). Use to spec anything before implementing it, convert code
  into a spec, review or repair a spec, or decide what kind of spec a component
  needs. Trigger on "spec this", "write the spec", "pseudocode the loop",
  "spec the classes", "requirements for", "convert this to a spec", or any
  design-before-build moment.
metadata:
  triggers:
    - "spec this"
    - "write the spec"
    - "spec before I implement"
    - "pseudocode the loop"
    - "spec the classes"
    - "convert this code to a spec"
    - "requirements for this component"
  status: active
  last_validated: 2026-07-18
  validation_method: source-grounded (Codeplain plain docs incl. canonical section order + Mavin EARS ruleset + Fission-AI/OpenSpec concepts.md + Algol-tradition algorithmic pseudocode conventions + Evans DDD tactical patterns); self-consistency pass 2026-07-03 (example validated against own checklist); TOON tabular collapse added 2026-07-18, grounded in toon-format/spec, self-consistency pass 2026-07-18 (fixed decision-table checklist conflict; TOON example validates against own checklist)
  supersedes: plain-spec, hybrid-spec, structural-spec
---

# spec

## Scope

One skill, four layers. Every spec task lands in exactly one layer, or
composes them inside a single document:

| Layer | Question it answers | When |
|---|---|---|
| **Requirements** | What conditions must hold? | Flat, order-independent behavior |
| **Structural** | What exists and what role does it play? | Classes, methods, functions, constants, configs |
| **Behavioral** | What order, what persists? | Loops, pipelines, state machines, transactions |
| **Rendered** | What is the durable artifact? | The complete spec file that outlives the code |

Nothing here depends on any other skill or external format. The rendered
layer *is* the final artifact — there is no promotion step out of this skill.

Spec evolution is out of scope by design: this skill has no delta/changelog
format. Updating an existing spec means rewriting it in place via Repair
mode. Do not invent a versioning scheme; version control belongs to the
repository, not the spec grammar.

## Layer Selection

1. Order and persistence load-bearing (a step depends on what a prior step
   left behind, or a variable resets at one loop level and survives
   another) → **Behavioral**. This rule scopes to a **single procedure in
   isolation** — "pseudocode this loop," "spec this retry logic."
2. The question is what should exist — class vs. function, method vs. free
   function, constant vs. config, what role a class plays → **Structural**.
   A whole module enters here **even when it contains stateful procedures**;
   those procedures get Behavioral blocks hosted under their structural
   lines (see Handoff to Behavioral). Rule 1 never routes a module.
3. Conditions and observable outcomes with no ordering constraints →
   **Requirements**.
4. Producing the module's durable source-of-truth document → **Rendered**,
   composing the other layers inside it.

A structural spec hosts behavioral blocks (a stateful method's body) and
requirements lines (a method's contract strength). Composition is normal;
picking the wrong entry layer is the error this section prevents.

## Absorbed Primitives

| Source | Primitive | Lives in layer |
|---|---|---|
| EARS | `While/When/If/Where` clauses, fixed order, Complex form | Requirements, Behavioral |
| OpenSpec | `Given/When/Then` scenarios; `MUST/SHALL/SHOULD/MAY` | Requirements, all |
| Algorithmic pseudocode (Algol tradition) | typed symbol table; `Loop forever/while/over`; scoped persistence | Behavioral |
| Plain | `:Concept:` discipline; section order; nested acceptance tests; modal verbs | Rendered |
| Business logic (DDD) | classification tests; entity/value/service/repository roles | Structural |
| TOON | tabular collapse of uniform arrays: `name[N]{fields}:` header + rows | Rendered |

These are attributions, not dependencies, and each names the convention as
borrowed, not an originator — the substrate is older in every case (RFC-2119
keywords under OpenSpec, when/if requirements predating EARS). OpenSpec's
change-proposal/delta workflow is deliberately **not** absorbed — only its
scenario syntax and strength keywords (see Scope). The grammar below is
complete on its own.

---

## Layer 1 — Requirements

Flat statements, one behavior each. Conditional headers use reserved EARS
keywords with exact semantics — never invent others:

```
While <precondition>: <response>          # state-driven
When <trigger>: <response>                # event-driven
If <unwanted condition>: <response>       # error handling
Where <optional feature>: <response>      # feature-gated
While <precondition>, When <trigger>: <response>   # Complex form
```

Ubiquitous (unconditional) requirements take no header. Strength keywords on
any statement where contract strength matters: `MUST`/`SHALL` (hard),
`SHOULD` (recommended), `MAY` (optional).

Externally observable outcomes get a scenario:

```
Given <initial state>, When <action>, Then <observable result>.
```

Rules:

- One subject, one concrete response per statement. No bundling.
- More than three stacked preconditions, or multi-variable branching →
  decision-table escape hatch:

```
While the result of [table.csv](table.csv) is "Response 1": <response>
```

- Decision-table schema: one column per condition, left to right; final
  column is the response; one row per condition combination. No other
  columns, no merged cells.
- A small decision table may inline as a TOON table (see Layer 4, Tabular
  collapse) rather than an external CSV — `decision[N]{cond1,cond2,response}:`
  with the same left-to-right schema. Keep the external CSV form once the
  table would push the spec past its line budget.

---

## Layer 2 — Structural

Prototypes plus one-line docstrings. No bodies, no literal values, no
control flow.

### Grammar

```
### <Module>, for <one-sentence purpose>

Config: <key> — <role>, <type/domain>, varies by <env | tenant | deploy>
Constant: <NAME> — <domain meaning>          # meaning stated, value omitted

class <Name> [<role>]: <one-line domain purpose>
    state: <symbol> — <type>, <who mutates it>
    <method(sig) -> ret>: <purpose; at least one failure mode>
        (Require: <precondition>; Guarantee: <postcondition>)

def <function(sig) -> ret>: <pure transformation; why it isn't a method>
```

Role sits in square brackets — parentheses after a class name read as Python
inheritance, and a spec must never be mistakable for code. `varies by` is
mandatory on every `Config` line. The free function's "why it isn't a
method" clause is required — it's the artifact of having run the
classification test.

**Type ownership.** Every type named in a signature is either **owned** by
the module — then it must appear as a `class` line with a bracketed role —
or **external** — then it is referenced bare and never classified. A
module's spec classifies only what the module is responsible for; classifying
someone else's type is a boundary violation. If ownership is unclear, flag
it (`Receipt — owned or external?`) rather than silently picking.

### Classification tests

The four decisions this layer exists to make explicit:

1. **Class vs. free function.** Persistent state across calls, or guards an
   invariant → class. Pure transformation → free function. Zero `state:`
   lines and zero invariants = a namespace, not a class — demote it.
2. **Method vs. free function.** Reads/writes the class's `state:` or
   enforces its invariant → method. Otherwise pull it out, even if the code
   currently has it inside the class.
3. **Constant vs. config.** Who changes it. Developer changes it and the
   program means something different → `Constant`. Operator/environment
   changes it between deployments with no code change → `Config`. `varies
   by` makes the test's answer visible in the spec itself.
4. **Class role.** Exactly one of:
   - `entity` — identity, mutable state, persists across operations
   - `value` — immutable, defined entirely by its data, no identity
   - `service` — stateless coordinator, orchestrates entities/values
   - `repository` — persistence boundary between storage and domain objects
   One class, one role. Ambiguity → escape hatch: write
   `class Cart [entity? value?]:` and ask, or split into the immutable data
   (`value`) and the thing that mutates it (`entity` or `service`).

### Handoff to Behavioral

A method whose purpose contains loop/order/persistence language keeps
signature + one-line purpose here and gets a Behavioral block attached
directly beneath it. The class's `state:` lines seed that block's symbol
table — reference, don't re-declare. Needing a Behavioral block is itself
diagnostic: stateful sequencing usually belongs on a `service`, not a
`value`.

---

## Layer 3 — Behavioral

For behavior where order and persistence are load-bearing.

### Symbol table

One symbol per line, type/range required:

```
Input: <symbol> — <role>, <type/domain>
Parameters: <symbol> ∈ <range>
Uses: <symbol> — <external operation>, <signature or result domain>
Initialize: <symbol> ← <value>
```

- `Input` — data the caller passes for this invocation.
- `Parameters` — caller-supplied tuning knobs, per invocation. If a value is
  supplied by the environment/deployment rather than the caller, it is a
  Layer-2 `Config`: reference it by name in steps, never re-declare it as a
  `Parameters` line. Caller-supplied wins the tie only when the caller can
  genuinely vary it per call.
- `Uses` — external operations the behavior invokes (gateway calls, other
  modules' functions). Declares the result domain so clause conditions have
  something to gate on. Anything invoked in a step must appear here or be
  owned by the module.
- `Initialize` — placement determines persistence tier (below).

Assignment steps (`x ← ...`) are exempt from the Layer-1 subject/response
rule — the assignment is its own subject and response.

### Control flow

```
Loop <forever | while <condition> | over <collection>>:
    <step>
```

Every `Loop` states `forever` or an explicit termination condition. Never
bare.

### Conditional clauses

Same reserved keywords as Layer 1, used as headers over steps inside a loop
body. Clauses are **gates, not loops**: a clause block runs once per pass
when its condition holds. Repetition comes only from an enclosing `Loop` —
`While` gates on state, `Loop while` iterates.

### Sequencing and scope rules

1. **Sequential execution.** Steps in a block run top-to-bottom, once per
   pass, in written order.
2. **Nesting is indentation.** Each indent opens one scope; no braces or
   `end`.
3. **Scoped persistence.** A symbol `Initialize`d inside a `Loop` resets
   each time that loop is re-entered and persists across its own iterations
   and any nested loop. `Initialize`d before any loop → global. Never
   `Initialize`d, only computed → transient, recomputed every pass. Every
   symbol falls in exactly one tier, visible from where its `Initialize`
   sits or its absence.
4. **`Otherwise` for exclusivity.** Same-level clauses are independent —
   each that holds fires, every pass. Chain with `Otherwise <keyword>:` (or
   bare `Otherwise:` fallthrough) for exclusive alternatives, first match
   wins.

---

## Contracts (all layers)

Inline, one type per annotation, stack with `;`:

```
<line>   (Require: <caller precondition>)
<line>   (Guarantee: <postcondition>)
<line>   (Maintain: <invariant>)
<line>   (Assert: <checkpoint check>)
```

`Maintain` binding and scope:

- On a class line or member → holds across every method call on the class.
- Inside a Behavioral block → binds to the **nearest enclosing `Loop`** and
  holds across that loop's iterations, regardless of how many clause blocks
  sit between the annotation and the loop. To bind to an outer loop, attach
  the annotation to that loop's own line.
- When a method carries both a structural `Maintain` and a behavioral one,
  they are different claims; don't collapse them.

`Assert` fires at its written position on the paths that reach it. An
`Assert` after a loop therefore claims nothing about aborted or
early-exited runs — if the check should only hold on normal completion, the
control flow already says so; if it must hold on every exit path including
aborts, state that explicitly in the assert text.

---

## Layer 4 — Rendered

The durable artifact form. Section order is fixed:

```
---
description: '<Module purpose>'
import:
  - <other-spec>            # brings in all primitives except functional specs
---

***definitions***

- :Concept: is <role in the domain, not implementation>.

***implementation reqs***

- <resource references, environment constraints>

***test reqs***

- <fixtures, sample data resources>

***functional specs***

- <requirement bullet, plain English or :Concept:-anchored>
  - <nested acceptance test — indentation is meaningful>
```

Rules:

- Concept names are unique **within this file and its declared imports**.
  Charset: `+ - . 0-9 A-Z _ a-z`, colon-wrapped at both ends; each
  definition starts with the concept being defined. When an import cannot be
  read at validation time, flag the collision check as unverified — never
  assert uniqueness you couldn't check.
- Not every functional spec needs a `:Concept:` — plain English is valid
  where no domain concept is at stake.
- Modal verbs: `should` / `must not` / `may`.
- 20–60 lines per spec; over 80 suggests a wrong module boundary — split.
- Write fresh from intent when converting code. Never transcribe
  implementation back into the spec.

### Folding the other layers in

- Structural class → one `:Concept:` definition, role noted in prose;
  `state:` symbols become `:Concept:`s only when they carry cross-cutting
  meaning. External types are referenced bare in prose, never defined as
  concepts.
- Structural method + contracts → one functional-spec bullet;
  `Require`/`Guarantee` fold into its nested acceptance test.
- Requirements statement → one functional-spec bullet, condition kept in the
  `when`/`while` clause.
- Behavioral unconditional step → one bullet; conditional clause → one
  bullet per branch (`Otherwise` chains fold into one bullet — exclusivity
  is noted in prose); `Assert`/`Guarantee`/`Then` → nested acceptance test;
  global and loop-scoped symbols → `:Concept:`s with reset scope noted in
  prose; transient symbols stay prose; `Uses` lines → implementation reqs.
- `Config`/`Constant` lines → implementation reqs; when two or more share a
  shape, collapse them into a TOON table (see Tabular collapse) rather than
  one prose bullet each.

### Tabular collapse (TOON)

Uniform arrays in the Rendered layer collapse into a TOON table instead of
one prose bullet per element. A table declares the field schema once and
streams rows:

```
<name>[<N>]{<field>,<field>,...}:
  <val>,<val>,...          # one row per element, N rows total
```

`[N]` is the element count — a guardrail, not decoration: row count MUST
equal N or the table is malformed. Fields are declared once in `{}`; every
row supplies them in that order. Values containing a comma, colon, or
leading/trailing space are double-quoted.

Collapse only where the region is **uniform and flat**:

- Two or more `Config` lines → `config[N]{key,role,type,varies_by}:`.
- Two or more `Constant` lines → `constant[N]{name,meaning}:`.
- A set of same-shape `Given/When/Then` scenarios with no per-scenario
  nesting → `scenarios[N]{given,when,then}:`.
- A flat battery of same-clause requirements (all `When`, all `While`, …)
  with no nested acceptance tests → `reqs[N]{condition,response,strength}:`.

Do **not** collapse when:

- Any element carries a nested acceptance test — nesting has no TOON form;
  those stay bullets.
- The elements are non-uniform — different fields, or mixed EARS keywords
  that change what a column means. A table would misrepresent their shape.
- There is exactly one element — a header plus one row costs more than a
  plain bullet.

A TOON table declares data shape, not control flow, so it does not trip the
"never mistakable for code" rule. Field names are column labels, not
`:Concept:` definitions, so they do not count against concept uniqueness —
but a field naming a defined concept still uses the concept charset.

Example — two configs and a scenario battery in collapsed form:

```
config[2]{key,role,type,varies_by}:
  tax_rate,fraction applied to subtotal,decimal,tenant
  currency,ISO code used for pricing,string,tenant

scenarios[2]{given,when,then}:
  one chargeable order,retry completes normally,order charged exactly once
  charge returns gateway_outage,retry aborts,no order charged more than once
```

---

## Procedure

1. Restate the intent; pick the entry layer via Layer Selection. Say which
   and why in one line.
2. Requirements: one subject + one response per statement; keywords only
   from the reserved set; over three preconditions → decision table with
   the fixed schema.
3. Structural: enumerate everything the module needs, settle owned vs.
   external for every type in every signature, run all four classification
   tests before writing lines, tag every owned class with exactly one
   bracketed role.
4. Behavioral: classify every symbol (global / loop-scoped / transient)
   before it appears in a step; declare every external operation with a
   `Uses` line; if more than one loop, draw the nesting and settle which
   symbol resets where before writing steps; write loops outermost-first,
   scoped `Initialize` directly under each; mark each clause independent or
   `Otherwise`-chained.
5. Attach contracts and strength keywords where correctness depends on
   them; check every `Assert` against the abnormal-exit paths that skip it.
6. Rendered: fold per the rules above; collapse uniform flat regions into
   TOON tables (Tabular collapse); verify section order and concept
   uniqueness within file plus readable imports.
7. Validate against the checklist.

## Validation Checklist

Requirements:

- Every conditional header is While/When/If/Where — no invented keywords.
- Every statement has one subject and at least one concrete response.
- Blocks over three preconditions moved to a decision-table matching the
  fixed schema (conditions left-to-right, response last, one row per
  combination) — an external CSV resource, or an inline TOON
  `decision[N]{...}` table while small.

Structural:

- Every type in every signature is either declared with a role (owned) or
  referenced bare (external) — no unclassified owned types, no classified
  external types, no silent picks on ambiguous ownership.
- Every class has exactly one role in square brackets; parenthetical roles
  are a syntax violation; ambiguity uses `[role? role?]`, never a silent
  pick.
- No class with zero `state:` lines and zero invariant.
- Every method touches state or enforces the invariant; every free function
  states why it isn't a method.
- Every `Config` carries `varies by`; every `Constant` states meaning, not
  a value. No bodies, values, or control flow anywhere in the layer.
- Every method purpose names at least one failure mode.
- Methods with order/persistence language have a Behavioral block, not
  inlined behavior.

Behavioral:

- Every symbol classifiable as global / loop-scoped / transient from its
  `Initialize` placement or absence.
- Every external operation invoked in a step has a `Uses` line with a
  result domain.
- No `Parameters` line duplicates a Layer-2 `Config`; environment-supplied
  values referenced by Config name.
- Every `Loop` states `forever` or explicit termination.
- Complementary clauses `Otherwise`-chained or confirmed intentional as
  independent.
- Every symbol appears in the table before use; none redefined.
- Every `Assert` consistent with every path that reaches it — an assert
  contradicted by a declared abort/early-exit branch is a spec bug.
- Assignment steps (`x ← ...`) exempt from the subject/response rule.

Rendered:

- Section order: definitions → implementation reqs → test reqs → functional
  specs.
- Every referenced concept defined first; names unique within file plus
  readable imports; unreadable imports flagged as unverified; charset
  valid.
- Acceptance tests nested under their functional bullet, indentation
  meaningful.
- Every TOON table's row count equals its declared `[N]`; each row supplies
  exactly the declared `{fields}` in order; no row carries a nested
  acceptance test; single-element regions stay prose bullets.
- 20–60 lines; over 80 → propose the split.

Contracts (all layers):

- Exactly one of Require/Guarantee/Maintain/Assert per annotation.
- Every behavioral `Maintain` bound to the intended loop — nearest
  enclosing by default, attached to the outer loop's line when the claim is
  outer-scoped.
- Class-scoped and loop-scoped `Maintain`s on the same member kept as
  separate claims.

## Repair Rules

- Preserve intent; never silently drop a statement, step, or member.
- Invented keyword → collapse to nearest reserved clause, or drop the
  header.
- Symbol used before declaration → add to correct tier; ask if scope is
  ambiguous.
- External operation invoked without a `Uses` line → add the line; ask for
  the result domain if it can't be inferred from the gating clauses.
- Owned type without a role, or external type with one → fix per the type
  ownership rule; ask when ownership itself is ambiguous.
- `Parameters` line shadowing a `Config` → remove the Parameters line,
  reference the Config by name; confirm the value is genuinely
  environment-supplied first.
- Assert contradicted by an abort/early-exit path → rescope the assert to
  the paths where it holds, or move the claim into a Given/When/Then
  happy-path scenario; ask which the author meant.
- Complementary clauses not chained → ask exclusive or independent; don't
  assume.
- Class with no state and no invariant → propose demotion; ask before
  removing.
- Method never touching state → propose extraction as free function.
- Constant that varies by deployment → reclassify as Config, confirm first;
  Config that never varies → reclassify as Constant.
- Class doing two roles → flag the split; don't pick one silently.
- Parenthetical role → rewrite to brackets; mechanical, no confirmation.
- Method description creeping into loop/order language → strip to signature
  + purpose, move behavior to a Behavioral block.
- Missing failure mode, or step with no subject/response → flag, don't
  guess.
- Rendered spec over 80 lines → propose the module split with import lines.

## Output Modes

1. **Draft** — complete spec at the selected layer(s) from intent, written
   fresh, never transcribed from code.
2. **Validate** — verdict, violations by line, corrected version if
   recoverable.
3. **Repair** — repaired spec plus change list.
4. **Render** — the complete Rendered-layer file, folding whatever
   Requirements/Structural/Behavioral content exists.

## Example (layers composed)

Entry layer: Structural — this is a module ("what exists"), hosting one
Behavioral block for the stateful retry procedure.

```
### OrderService, for placing and pricing customer orders

Config: tax_rate — decimal fraction applied to subtotal, varies by tenant
Constant: MAX_LINE_ITEMS — upper bound on items per order, business rule

class Order [entity]: a customer's in-progress or placed purchase
    state: line_items — list[LineItem], mutated by add_item/remove_item
    state: status — enum{draft, placed, cancelled}, mutated only by OrderService
    add_item(item: LineItem) -> None: append a line item; fails over MAX_LINE_ITEMS
        (Require: status == draft; Guarantee: len(line_items) <= MAX_LINE_ITEMS)

class LineItem [value]: an immutable quantity/price pair on an order

class Receipt [value]: immutable proof of a completed placement

class RetryReport [entity]: per-run accumulation of charge outcomes,
    mutated only within retry_failed_charges

class OrderService [service]: coordinates order placement and pricing
    place(order: Order) -> Receipt: MUST reject empty orders
        (Require: order.status == draft; Guarantee: order.status == placed)
    retry_failed_charges(batch: list[Order]) -> RetryReport: re-attempt charges
        with bounded retries; fails closed on gateway outage

        Input: batch — orders with failed charges, list[Order]
        Parameters: max_attempts ∈ ℤ⁺        # caller-supplied per run, not a Config
        Uses: charge — external payment gateway call,
              Order -> enum{success, gateway_outage, decline}
        Initialize: report ← empty RetryReport        # global to this run

        Loop over each order o in batch:
            Initialize attempts ← 0                   # loop-scoped: reset per order
            Loop while attempts < max_attempts:
                result ← charge(o)                    # transient
                When result is success:
                    record o in report                (Maintain: report counts ≤ len(batch))
                Otherwise If result is gateway_outage:
                    abort the batch                   (Guarantee: no partial double-charge)
                Otherwise:
                    attempts ← attempts + 1
        Assert: on normal completion (no abort), every order in batch
                appears in report exactly once

        Given a batch with one chargeable order, When retry_failed_charges
          completes normally, Then report MUST show that order charged
          exactly once.
        Given a batch where charge returns gateway_outage, When
          retry_failed_charges aborts, Then no order MUST be charged more
          than once.

def apply_discount(total: Money, pct: Decimal) -> Money: pure transform,
    no order state involved — belongs outside any class
```

`Money` and `Decimal` are external types — referenced bare, never
classified. The `Maintain` on `record o in report` binds to the nearest
enclosing loop (the inner retry loop) per the binding rule; the claim also
holds at the outer loop, but the annotation asserts only the inner scope.

Rendered form of the same module folds `Order`, `OrderService`,
`RetryReport` into `:Concept:` definitions, `Config`/`Constant`/`Uses` into
implementation reqs, each method into a functional-spec bullet with its
`Guarantee`/`Then` as nested acceptance tests.

## Notes for This Stack

- This skill subsumes the earlier plain-spec, hybrid-spec, and
  structural-spec files; retire them from the registry to avoid double
  triggering.
- The classification tests and the persistence tiers are the actual
  deliverables — a spec that skips them is a diagram or a transcript, not a
  spec.
- Pipeline stages map naturally to one rendered spec per stage with imports
  for shared concepts; the anti-pattern when converting existing code is
  leaking implementation back into the spec. Write from intent.
- Verification is by the acceptance tests the spec produces, not by a
  semantics-preservation proof — reproducible under pinned local inference
  is not the same claim as correct.
---

## Hard gate: when spec-first is mandatory

Before proposing or writing code, state in one line which spec layer governs the
work and why: **Requirements** (flat observable behavior), **Structural**
(classes, functions, methods, constants, configs, roles), **Behavioral**
(ordered/stateful logic, loops, transactions, pipelines), **Rendered** (the
durable module spec artifact), or **Catalog** (registering or mapping specs to
files).

Block coding and produce or repair a spec first when the change affects any of:

- externally observable behavior
- control flow or sequencing
- persistence or state lifetime
- public interfaces
- class or function boundaries
- constants-vs-config decisions
- file-to-spec ownership
- acceptance criteria

If the spec is missing, stale, ambiguous, or contradicted by the request, the
next step is to draft, validate, or repair it — not to code.

**Order of operations.** Draft or repair the spec, validate it against this
skill, implement, then reconcile the spec against what actually shipped. No code
change is complete unless its governing spec is current. Where code and spec
disagree, that mismatch is a defect to resolve explicitly, not to paper over.
Never write implementation-first and backfill the spec later.

**Allowed exception.** Truly mechanical edits with no change to behavior,
structure, contracts, or configuration semantics — typo fixes in comments or
docs, formatting-only changes, semantically neutral renames. When taking this
exception, say explicitly why the change is mechanical and why no spec update is
required.

**Completion criteria.** For any spec-governed task, done means: the spec is
drafted or updated, the spec is validated, the code matches the spec, acceptance
tests trace back to the spec, and any rendered or cataloged artifact the workflow
requires is reconciled.
