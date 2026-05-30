---
name: agent-identity
description: >
  Define a fixed identity layer above memory and skills, then isolate specialized
  agent profiles so role, tone, constraints, and execution substrate do not smear
  across sessions. Triggers on: SOUL.md, persona drift, profile isolation, "all my
  agents feel the same", specialized coder/researcher/designer agents.
status: active
last_validated: 2026-05-27
supersedes: []
superseded_by: null
validation_method: documentation_review
---

# Agent Identity

## Context

You end up here when memory, skills, and tooling are all present but the agent still
feels interchangeable across roles. The failure mode is subtle: facts accumulate,
procedures improve, but the agent has no fixed frame for who it is when it shows up.
Stuffing persona into memory causes drift, and stuffing it into per-task prompts makes
it one-shot and forgettable. The fix is to put identity in its own static layer,
loaded before memory and skills, then isolate role-specific agents behind separate
profiles.

---

## Step 1 — Write the Fixed Identity Contract

Author one static identity file per agent profile. Load it before memory and before
procedural skills. Keep it short, load-bearing, and about stance: role, tone,
decision style, hard limits, and what "good" output looks like.

```bash
# Generic layout
<agent-home>/
  SOUL.md

# Per-profile layout
<agent-home>/profiles/<profile-name>/SOUL.md
```

Expected state change: the agent now has a persistent answer to "who am I?" that does
not depend on the current task, memory retrieval, or the last correction.

---

## Step 2 — Split Identity from Memory and Skills

Do not let identity leak into memory files or skill contracts. Memory stores evolving
facts about the user, project, and environment. Skills store reusable procedures.
Identity is the fixed interpretive frame that reads both.

```bash
# Keep these separate
SOUL.md           # fixed identity
MEMORY.md         # environment/project/tool facts
USER.md           # user model and preferences
skills/*/SKILL.md # reusable procedures
```

Expected state change: changing a memory entry updates what the agent knows, not who it
is; adding a skill updates what the agent can do, not its stance.

---

## Step 3 — Create Fully Isolated Specialist Profiles

When one agent needs multiple durable roles, fork profiles instead of multiplexing one
shared identity. Each profile gets its own config, memory, skills, sessions, and
identity file. Share nothing by default except the bootstrap you intentionally clone.

```bash
# Hermes example
hermes profile create designer --clone
hermes profile create programmer --clone
hermes profile create researcher --clone
hermes profile list
```

Expected state change: programmer, researcher, and designer stop overwriting each
other's memory and procedural library, and each can accumulate role-specific lessons.

---

## Step 4 — Bind Substrate and Automation Per Profile

After profile isolation, bind each profile to its own execution surface and recurring
work. Coding agents can delegate to a coding substrate, research agents can own digests
or monitors, and design agents can own style-specific generation skills. Identity stays
stable while the substrate and automations remain role-specific.

```bash
# Examples of role-specific bindings
hermes -p programmer gateway setup
hermes -p researcher cron list
hermes -p designer config set OPENROUTER_API_KEY <your-key>
```

Expected state change: role-specialized agents stop behaving like one generic core with
different prompts and start behaving like distinct operators with durable jobs.

---

## Step 5 — Evolve Procedures, Not Identity

Let memory consolidation, skill creation, curator sweeps, or offline optimization
improve procedural behavior. Do not let those loops rewrite the identity layer. Skills
may change. Memory may compress. Identity should only change by explicit editorial
decision.

```bash
# Identity is hand-edited
edit SOUL.md

# Procedures evolve through the skill lifecycle
create SKILL.md
patch SKILL.md
archive stale skills
optimize skill variants offline
```

Expected state change: self-improvement compounds without turning the agent into a
different persona every time the skill library shifts.

---

## Example

Hermes is a concrete instantiation of this pattern:

~~~text
~/.hermes/
  SOUL.md                    # default identity, loaded first
  memories/MEMORY.md         # compact environment facts
  memories/USER.md           # user model
  skills/                    # procedural memory
  state.db                   # searchable session history
  profiles/
    programmer/
      SOUL.md
      skills/
      state.db
    researcher/
      SOUL.md
      cron/jobs.json
    designer/
      SOUL.md
      skills/my-design-style/
~~~

The architectural point is not "use Hermes." It is: identity is a first-class layer,
profiles are full isolation boundaries, and procedural evolution happens beneath that
layer rather than rewriting it.

---

## Dead Ends — Do Not Use

### Storing identity inside memory

```bash
# BROKEN — memory now mutates persona every time facts are consolidated
echo "You are my terse staff engineer" >> MEMORY.md
echo "Always answer like a researcher" >> USER.md
```

This fails because memory is supposed to evolve with project facts and user
preferences. Persona instructions in that layer drift, merge, and decay with unrelated
context.

### Reusing one profile for incompatible roles

```bash
# BROKEN — one profile accumulates mixed memories, tools, and role habits
hermes
# same agent handles coding, design, research, and scheduling forever
```

This fails because the agent's sessions, memory, skills, and automations all bleed
together. You do not get specialization; you get one muddy generalist.

### Letting self-improving skills rewrite the identity file

```bash
# BROKEN — procedure optimization now mutates who the agent is
skill_manage edit SOUL.md
```

This fails because skills should improve behavior inside the identity frame, not
replace the frame itself.

### Using per-task prompts as the only role definition

```bash
# BROKEN — role vanishes on the next session or handoff
"You are now a designer for this task only"
```

This fails because inline prompts do not persist as a stable identity contract and
cannot support durable specialization.

---

## Applicability Envelope

**Works well when:**
- one agent needs multiple durable roles with different tone, substrate, and jobs
- memory and skills already exist, but role drift or sameness remains
- you need specialized profiles that accumulate their own procedural memory
- execution substrate or automation should differ per role without forking the whole stack

**Fails or degrades when:**
- the system only needs one generic agent and specialization overhead exceeds value
- the runtime cannot isolate config, memory, sessions, and skills per profile
- identity is expected to self-edit automatically from sparse interaction data

**Environment assumptions:**
- the agent runtime supports a static identity file or equivalent first-loaded persona layer
- memory and skill storage are separable from the identity layer
- profiles or equivalent isolated agent scopes can be created
