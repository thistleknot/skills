<!--
Canonical example: rocky10-gnome-rdp/SKILL.md
Model your skill after that one. Born from triage, not theory.
Treat the skill as a model-agnostic, combinatorial plugin: discrete, slot-in,
and reusable across agents.
Steps verified end-to-end. Dead Ends named with exact broken syntax.
No hedging language. Commands copy-pasteable.
-->

---
name: {skill-name}
description: >
  {One sentence: what this skill does and when to invoke it. Include trigger
  phrases: "triggers on: X, Y, Z".}
---

# {Skill Name}

## Context

*Why you end up here. The situation, the constraint, what prior approaches fail.*
*Keep it to 3–5 sentences. If you can't explain the context in that space, the*
*skill isn't crystallized yet.*

---

## Step 1 — {First Action}

*What you do and why. One paragraph max.*

```bash
# exact commands that worked
```

*What the expected output or state change is.*

---

## Step 2 — {Next Action}

```bash
# commands
```

---

## {Continue steps as needed}

---

## Dead Ends — Do Not Use

*This section is mandatory. A skill without dead ends wasn't triage'd.*

### {Thing that seems obvious but breaks}

```bash
# BROKEN — reason it doesn't work on this system/version
broken-command --with-flag
```

### {Another dead end}

*Why it fails. Be specific: version mismatch, missing dependency, wrong env, etc.*

---

<!--
Promotion gate (fill out before moving to skills/):
- [ ] Steps verified end-to-end in at least one real session
- [ ] Dead ends section present (not left blank)
- [ ] No existing skill covers ≥80% of this (checked README.md)
- [ ] Judge capability rule satisfied if any LLM verdict used as evidence
     (→ evaluator-optimizer § Judge Model Capability Rule)
-->
