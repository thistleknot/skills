---
name: schema-induction
description: >
  Cross-instance schema discovery via pairwise contrast. Collect N examples of
  the same kind, partition each pair into SAME | VARIES, aggregate to find
  constants and variable dimensions, characterize ranges and minima. Root:
  Aristotelian diairesis (genus + differentia). CRISP-DM analog: Data
  Understanding. Invoke when you have multiple instances of an unknown format,
  config, API response, or artifact and need to reverse-engineer the schema,
  find required vs optional fields, or isolate what dimensions carry the
  meaningful variance.
status: active
last_validated: 2026-05-20
supersedes: []
validation_method: session
---

# Schema Induction

## Root

Aristotle's **diairesis**: divide a genus by its differentia.

> Two mods for the same game are the *same* by genus (same engine, same format)
> but *different* by differentia (different stats, different item IDs).
> The genus gives you the constants. The differentia gives you the variable dimensions.

CRISP-DM calls this the **Data Understanding** phase: describe, explore, verify.
The operation is identical — you are doing data discovery on a set of structured examples.

---

## Trigger

Invoke when:

- You have ≥ 2 instances of the same kind and need to know the schema
- A config, mod, API response, or artifact format is undocumented
- You need to find what fields are required vs optional
- You need to isolate which dimension carries the bug (one instance works, one doesn't)
- You are doing CRISP-DM Data Understanding on a corpus of structured documents

Do NOT invoke when:
- You already have a schema (use it directly)
- You have only one instance (no contrast is possible — use `diagnostic-scanner` instead)

---

## The Five-Step Loop

### Step 1 — Collect

Gather N instances of the same kind. Minimum: 2. Useful signal starts at 3–5.

Label each instance. The label should capture what you know about it:
- `mod_A` (working), `mod_B` (broken)
- `response_200`, `response_404`, `response_500`
- `config_passing`, `config_failing_1`, `config_failing_2`

If some instances are known-good and some known-bad, label them explicitly — the
SAME/VARIES partition across that axis directly isolates the causal dimension.

---

### Step 2 — Pairwise Partition (SAME | VARIES)

For each pair of instances, walk every field/key/attribute and classify:

| Classification | Meaning |
|---|---|
| `SAME` | Same field present, same value (or same type + same range) |
| `VARIES` | Same field present, different value |
| `ABSENT_A` | Field present in B, absent in A |
| `ABSENT_B` | Field present in A, absent in B |

Produce a partition table per pair:

```
Pair (mod_A, mod_B):
  SAME:     format_version=2, engine="unity", asset_type="weapon"
  VARIES:   damage=12 vs 47, range=5 vs 12, name="sword" vs "rifle"
  ABSENT_A: mod_B has field `splash_radius` — absent in mod_A
  ABSENT_B: (none)
```

Do this for all C(N,2) pairs. For large N, a representative sample suffices (min 3 pairs).

---

### Step 3 — Aggregate

From all pair partitions:

**Constants** = fields that appear in SAME across ALL pairs
- These are the genus-level invariants — every instance must have them
- Candidate required fields

**Universal variables** = fields that appear in VARIES across all pairs
- These are the dimensions of meaningful difference
- Candidate required fields with variable values

**Conditional fields** = fields that appear in ABSENT_A or ABSENT_B in some pairs but SAME in others
- These are optional — present in some instances, absent in others

**Orphan fields** = fields that appear in only one instance
- Possibly instance-specific extensions, errors, or noise

---

### Step 4 — Characterize

For each field in the aggregate:

**Constants:**
- Type (string, int, enum, bool)
- Value (the constant value itself)
- Presence: required (present in 100% of instances)

**Variables:**
- Type
- Observed range: [min, max] for numerics; enumerated values for categoricals
- Cardinality: how many distinct values observed
- Distribution hint: uniform / skewed / bimodal (if enough instances)
- Presence: required (100%) vs optional (< 100%)

**Emit a field table:**

```
Field            | Class    | Type   | Constant Value | Observed Range  | Required
-----------------|----------|--------|----------------|-----------------|--------
format_version   | constant | int    | 2              | —               | yes
engine           | constant | string | "unity"        | —               | yes
asset_type       | constant | string | "weapon"       | —               | yes
damage           | variable | int    | —              | [1, 500]        | yes
range            | variable | int    | —              | [1, 50]         | yes
name             | variable | string | —              | (free text)     | yes
splash_radius    | optional | float  | —              | [0.5, 10.0]     | no
```

---

### Step 5 — Emit the Minimum Schema

The minimum schema = constants + required variables. Everything else is optional.

```
MINIMUM SCHEMA (required fields every instance must have):
  format_version: int = 2          # constant
  engine: string = "unity"         # constant
  asset_type: string = "weapon"    # constant
  damage: int ∈ [1, 500]           # required variable
  range: int ∈ [1, 50]             # required variable
  name: string                     # required variable

OPTIONAL EXTENSIONS:
  splash_radius: float ∈ [0.5, 10.0]   # present in ranged/explosive weapons only
```

This is the CRISP-DM Data Understanding output: schema + domain constraints.

---

## Debugging Application

When one instance works and one doesn't, the VARIES partition **is the bug search space**.

Protocol:
1. Collect: known-good instance(s) + broken instance(s)
2. Partition: find all VARIES fields between good and bad groups
3. Rank VARIES fields by causal plausibility (domain knowledge, proximity to failure)
4. Test hypothesis: fix the highest-ranked VARIES field in the broken instance → retest
5. If fixed: the differentia was the cause. Document.
6. If not fixed: eliminate that field, move to next.

This is `subtractive-debugging` applied at the schema level rather than the git-diff level.
The difference: subtractive-debugging anchors on a time axis (what changed); schema-induction
anchors on a structural axis (what differs between instances right now).

---

## Worked Example — API Response Schema Discovery

You have 5 API responses. You don't know the schema. Run the loop:

**Collect:** resp_1 through resp_5 (mix of success and error responses)

**Pairwise partition** (abbreviated):
- SAME across all: `status`, `timestamp`, `request_id`
- VARIES: `data` (present in success, absent in errors), `error_code` (present in errors, absent in success)
- ABSENT in some: `pagination` (only in list responses), `retry_after` (only in 429)

**Aggregate:**
- Constants: `status`, `timestamp`, `request_id` → always required
- Universal variables: none (data and error_code are conditional)
- Conditional: `data` (success only), `error_code` (error only), `pagination` (list only), `retry_after` (429 only)

**Minimum schema:**
```
request_id: string   # always
timestamp: ISO8601   # always
status: int          # always
```

**Conditional extensions by status group:**
```
2xx: + data: object
4xx/5xx: + error_code: string, + message: string
429: + retry_after: int
list endpoints: + pagination: { page, per_page, total }
```

---

## Integration Points

- **`subtractive-debugging`** — use schema-induction first when the regression is across instances (not across time); hand off to subtractive-debugging once you've identified the differentia field as the change vector
- **`diagnostic-scanner`** — use after schema-induction to validate a new instance against the induced schema
- **`reasoning`** — the SAME/VARIES partition is a deductive step; ranking causal plausibility of VARIES fields is abductive
- **`feature-catalog`** — schema-induction produces the field inventory that feature-catalog operates on
- **`validation`** — the induced minimum schema becomes a validation contract

<!-- consolidation:see-also:start -->
## See Also
[[react-fastapi-sqlite]]  [[semantic-search-enrichment]]  [[code-extraction]]
<!-- consolidation:see-also:end -->
