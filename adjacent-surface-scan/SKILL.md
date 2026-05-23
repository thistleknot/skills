---
name: adjacent-surface-scan
description: >
  One-degree-out debugging protocol. Use when an error names one concrete
  missing/invalid item inside a structured surface: image filename, UI asset,
  config key, enum value, schema field, route, selector, database reference,
  or resource handle. Before fixing the named item, scan sibling references in
  the same file/template/module and the equivalent peer file so the fix covers
  the local family, not just the first reported leaf.
status: active
last_validated: 2026-05-22
supersedes: []
validation_method: session
---

# Adjacent Surface Scan

## Core Thesis

**A single named error is usually the first visible leaf of a local family.**

When a system reports one missing item, do not immediately create or rename
that item. First inspect one degree out:

1. the containing file or template
2. sibling references with the same prefix, suffix, type, or role
3. peer files that define the same surface in another locale/profile/scenario
4. the asset/schema layer that resolves those references

The goal is not a repo-wide audit. The goal is a bounded sibling scan before a
one-item fix.

---

## Trigger Conditions

Use this skill when the symptom has this shape:

```text
Unable to find <single named thing>
Unknown field <single named thing>
Invalid enum <single named thing>
Missing route/selector/resource <single named thing>
```

Especially when the named thing belongs to a visible family:

- `ctp1_button_up.tga` -> button images in the same LDL templates
- `uptg06f-2.tga` -> adjacent `uptg06*.tga` border pieces
- `DESCRIPTION_UNIT_X` -> nearby unit string keys
- `ICON_ADVANCE_X` -> adjacent icon/database/string triplets
- one missing JSON/YAML field -> sibling fields in the same schema block

---

## Protocol

### Step 1 - Locate the first concrete reference

Find the file and line that names the broken item.

```text
Broken item: <name>
Reference file: <path>
Reference line: <line>
Resolver layer: <where the runtime expects to find it>
```

Do not fix yet.

### Step 2 - Scan siblings in the same surface

In the containing file, list nearby references with the same role:

- same extension (`*.tga`, `*.json`, `*.txt`)
- same prefix/suffix (`ctp1_button_*`, `uptg06*`, `DESCRIPTION_*`)
- same template/block/object
- same resolver field (`image0`, `image1`, `disabledimage0`)

Expected output:

```text
Sibling family:
- <name A> at <line>
- <name B> at <line>
- <name C> at <line>
```

If siblings share the same obsolete prefix or missing resolver, fix the family.
If they do not, keep the fix to the named item.

### Step 3 - Compare the peer surface

Find the equivalent file or block in the nearest peer surface:

- `default` vs `english`
- scenario override vs base file
- current template vs stock template
- one schema version vs another
- one working feature instance vs the broken instance

Ask:

```text
Does the peer surface use a different known-good name or structure?
```

If yes, prefer the peer's known-good reference over inventing a placeholder.

### Step 4 - Check resolver semantics before creating anything

Before adding a file/key/route, determine how resolution works:

- Does a loose file override packed assets?
- Does a scenario override shadow base data?
- Does a missing field inherit from a default?
- Does adding a duplicate key change lookup order?

If adding the missing item changes precedence, do not add it unless that is the
explicit desired behavior.

### Step 5 - Apply the narrow family fix

Choose the smallest fix that covers the local family:

| Finding | Fix shape |
|---|---|
| One typo only | Rename that reference |
| Obsolete prefix across sibling references | Replace all sibling references in the same template/block |
| Missing generated output for a known owned asset | Regenerate only owned assets |
| Runtime expects packed stock asset | Point to packed stock asset; do not create loose placeholder |
| Multiple unrelated missing families | Stop and create separate issues/tasks |

### Step 6 - Verify both leaf and siblings

After the fix, verify:

- the original named item no longer appears in unresolved references
- sibling references in the same family now use valid names
- no broad placeholder or precedence-changing artifact was created
- the containing surface still parses/loads

---

## CTP2 UI Example

Bad first move:

```text
Error: Unable to find ctp1_button_up.tga
Fix: create ctp1_button_up.tga placeholder
```

Correct one-degree-out scan:

1. `ctp1_button_up.tga` appears in `fancy.ldl` and `ns_template.ldl`
2. sibling `ctp1_button_down.tga` appears beside it
3. stock CTP2 templates use `upbt01aU.tga` / `upbt01aD.tga`
4. loose TGAs override packed UI art
5. fix the obsolete sibling pair in the LDL templates

Correct fix:

```text
ctp1_button_up.tga   -> upbt01aU.tga
ctp1_button_down.tga -> upbt01aD.tga
```

No loose files created.

---

## Relationship to Other Skills

| Need | Use |
|---|---|
| Error names one concrete item and likely siblings exist | `adjacent-surface-scan` |
| Output is wrong but no error names the item | `pipeline-input-review` |
| Need root-cause investigation from stack trace/error path | `debugging` |
| One instance works and one fails; compare differentia | `schema-induction` |
| Regression from known-good commit | `subtractive-debugging` |

---

## Anti-Patterns

| Anti-pattern | Why it fails |
|---|---|
| Fix only the first reported missing filename | Runtime reports the next sibling on the next run |
| Create a placeholder before checking resolution order | Placeholder can override real packed/default assets |
| Search the whole repo before reading the containing block | Too broad; loses the local family shape |
| Treat peer files as duplicates without comparing them | Peer files often reveal the intended stock name |
| Collapse unrelated families into one fix | Increases blast radius and hides which change worked |

<!-- consolidation:see-also:start -->
<!-- consolidation:see-also:end -->
