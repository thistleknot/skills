# sundaiclaw/hacker Feature Topology

**Source:** `sundaiclaw/hacker` @ `fb23383` — MIT license  
**Purpose:** OpenSpec-first autonomous shipping stack. The reusable core is a spec-driven change workflow (`openspec-*` + Fabro workflow authoring). Around that, the repo adds a Sundai-specific operator pipeline and an OpenClaw-specific observability app.

---

## Topology Overview

```text
SPEC-DRIVEN CHANGE LAYER ───────────────────────────────────────────────────────
  openspec-explore
       │ (clarify / think / inspect, but do not implement)
       ▼
  openspec-propose ──► openspec-workflow
                            │
                            ├──► openspec-apply-change
                            │        (implement tasks from the active change)
                            │
                            └──► openspec-archive-change
                                     (finalize / archive / optional spec sync)

WORKFLOW AUTHORING LAYER ──────────────────────────────────────────────────────
  fabro-create-workflow
       │
       └──► authors `.fabro` graphs + `.toml` run configs used by
            openspec-workflow / Fabro build pipelines

REFERENCE SUBLAYER ────────────────────────────────────────────────────────────
  review-loop
  archive-action
       │
       └── reusable protocols embedded by the OpenSpec workflow family;
          useful as reference material, not primary standalone imports

SUNDAI OPERATOR LAYER ─────────────────────────────────────────────────────────
  sundai-project-pipeline
       │
       ├── research / ideation
       ├── repo bootstrap + early deploy
       ├── Sundai draft creation + metadata sync
       ├── OpenSpec artifact generation
       ├── Fabro validate / preflight / run
       ├── publish / polish / QA / About-page sync
       └── assumes pre-authorized Sundai + GCP + OpenClaw environment

OBSERVABILITY LAYER ───────────────────────────────────────────────────────────
  agent-build-observatory
       │
       ├── observability-schema.ts    (runs / events / commands schema)
       ├── observability-db.ts        (Postgres or SQLite storage)
       ├── observability.ts           (run/event projection layer)
       ├── dashboard + API routes     (Next.js UI)
       └── openclaw-runtime.ts        (collector from ~/.openclaw/... sessions)
```

---

## Feature Inventory

### SPEC-DRIVEN CHANGE

**`openspec-explore`**  
Explore-mode stance for idea shaping, requirement clarification, and codebase investigation. Explicitly forbids implementation; allows reading files, comparing options, drawing diagrams, and optionally capturing decisions into OpenSpec artifacts. **Directly portable.**

**`openspec-propose`**  
One-shot change bootstrapper. Creates a change, walks OpenSpec artifact dependencies, generates `proposal.md`, `design.md`, `tasks.md`, and any apply-required artifacts until the change is implementation-ready. **Directly portable.**

**`openspec-workflow`**  
The umbrella OpenSpec + Fabro operating model. Splits work into: spec authoring, review loop, Fabro workflow setup, validation, implementation, verification, and PR/ship handoff. Requires `openspec`, `fabro`, `gh`, and `git`. **Directly portable with light environment adaptation.**

**`openspec-apply-change`**  
Task execution skill for an existing OpenSpec change. Reads the active schema, pulls context files from `openspec instructions apply --json`, works tasks in sequence, and updates task checkboxes as implementation proceeds. **Directly portable.**

**`openspec-archive-change`**  
Finalization/archival skill. Checks artifact completion, task completion, optional delta-spec sync, then archives `openspec/changes/<name>` into a dated archive path. Includes explicit warning/confirm behavior. **Directly portable.**

### WORKFLOW AUTHORING

**`fabro-create-workflow`**  
Natural-language-to-Fabro workflow author. Chooses topology, writes DOT graphs, writes optional TOML run configs, assigns models via stylesheet, and validates with preflight. Strong reusable primitive for agent pipeline design. **Directly portable.**

### REFERENCE MATERIAL

**`review-loop`**  
Protocol for artifact review before implementation: when to review, how to give repo-aware reviewers access, how to process objections, and how to log review rounds. Best treated as a reusable reference folded into local review/documentation skills. **Reference-only / partially portable.**

**`archive-action`**  
GitHub Actions recipe for auto-archiving OpenSpec changes on PR merge. Useful operational pattern, but not a first-pass skill import by itself. **Reference-only / partially portable.**

### SUNDAI-SPECIFIC OPERATOR PIPELINE

**`sundai-project-pipeline`**  
Full 15-step autonomous Sundai Club shipping run: ideation, repo creation, early deploy, Sundai draft creation, OpenSpec artifact generation, Fabro execution, publish, repo metadata sync, and post-ship polish. Assumes `.env.sundai`, Sundai APIs, Clerk session minting, GCP deploys, OpenClaw VM layout, and a pre-authorized operator model. **Not portable as-is.**

### OBSERVABILITY

**`agent-build-observatory`**  
Next.js dashboard for live agent-build visibility: current stage, timeline, command activity, changed files, artifacts, sub-agent hierarchy, and deploy outcomes. Uses Postgres when `DATABASE_URL` is set, otherwise SQLite fallback. **Partially portable.**

**`observability-schema.ts`**  
Clean normalized schema for `runs`, `events`, and `commands`, with explicit `stage`, `status`, `owner`, and command lifecycle states. This is the strongest reusable observability artifact in the repo. **Portable concept / schema.**

**`openclaw-runtime.ts`**  
Collector that reads `~/.openclaw/agents/*/sessions/sessions.json`, derives runtime state from transcript/tool activity, and projects it into the observability schema. Valuable as a pattern, but tightly coupled to OpenClaw storage layout. **Not portable as-is.**

---

## Dependency Graph (edges)

```text
openspec-explore ──► openspec-propose
openspec-propose ──► openspec-workflow
fabro-create-workflow ──► openspec-workflow
review-loop ──► openspec-workflow
openspec-workflow ──► openspec-apply-change
archive-action ──► openspec-archive-change

sundai-project-pipeline ──► openspec-workflow
sundai-project-pipeline ──► fabro-create-workflow
sundai-project-pipeline ──► deploy / Sundai API / GCP / repo metadata sync

observability-schema.ts ──► observability-db.ts / observability.ts / dashboard
openclaw-runtime.ts ──► observability-schema.ts
agent-build-observatory ──► dashboard + API + runtime collector
```

---

## Phase–Feature Matrix

| Phase | Features | Portability |
|---|---|---|
| Explore / clarify | `openspec-explore` | Direct |
| Draft change artifacts | `openspec-propose`, `openspec-workflow` | Direct |
| Workflow authoring | `fabro-create-workflow` | Direct |
| Implement from spec | `openspec-apply-change`, `openspec-workflow` | Direct |
| Archive / sync change | `openspec-archive-change`, `archive-action` | Direct skill + reference doc |
| Full autonomous ship | `sundai-project-pipeline` | Not portable as-is |
| Build observability | `agent-build-observatory`, `observability-schema.ts` | Partial |
| Runtime collection | `openclaw-runtime.ts` | Not portable as-is |
| Artifact review discipline | `review-loop` | Reference-only |

---

## Harness Adaptation Notes

1. **Directly portable first-pass:** `openspec-workflow`, `openspec-propose`, `openspec-explore`, `openspec-apply-change`, `openspec-archive-change`, `fabro-create-workflow`.
2. **Reference-only / fold into existing local skills:** `review-loop`, `archive-action`, and the observability schema concepts.
3. **Rebuild instead of porting:** `sundai-project-pipeline`, Sundai `.env` contracts, GCP/OpenClaw deployment docs, and the OpenClaw runtime collector.
4. **Best reusable non-skill concept:** the observability `runs / events / commands` model from `agent-build-observatory`.

---

## Bottom-Line Classification

- **Portable now:** OpenSpec skill family + Fabro workflow authoring
- **Portable as concepts:** review loop, archive automation pattern, observability schema
- **Not portable without redesign:** Sundai operator pipeline, OpenClaw runtime collector, deploy/auth environment contract
