# gstack Skill Topology
**Source:** garrytan/gstack — MIT license  
**Purpose:** Harness-agnostic reference. Skills are encapsulated as role-scoped cognitive modes
implementable as slash commands, personas, or sub-agents in any agentic framework
(Claude Code, OpenClaw, Copilot Agents, Aider, OpenCode, etc.).

---

## Topology Overview

```
IDEATION ----------------------------------------------------------------------
  office-hours
       ¦ (enriches)
       ?
PLANNING ----------------------------------------------------------------------
  plan-ceo-review --+
  plan-eng-review --¦--? autoplan (orchestrates all four sequentially)
  plan-design-review¦
  plan-devex-review +
       ¦
       ¦ (plan approved)
       ?
EXECUTION ----------------------------------------------------------------------
  [code changes]
  investigate (if blocked / broken)
  health (quality gate, anytime)
  careful / freeze / guard (session safety modifiers)
       ¦
       ?
REVIEW GATES -------------------------------------------------------------------
  review   --+
  codex    --¦--? gates ship
  cso      --¦
  qa       --+
  qa-only (report only, no fix)
       ¦
       ?
SHIP PIPELINE ------------------------------------------------------------------
  ship --? land-and-deploy --? canary
                ¦
                ?
          document-release
               retro (periodic)

DESIGN TRACK (parallel, feeds planning + implementation) -----------------------
  design-consultation --? design-shotgun --? design-html --? design-review
                                                              ?
                                              plan-design-review (predicts)
                                                  (boomerang: plan vs live)

BROWSER LAYER (primitive used by qa, design-review, devex-review, canary, scrape) --
  setup-browser-cookies --? browse / open-gstack-browser
                              ¦
                    +---------+-------------------------------+
                    ?         ?              ?                ?
                  scrape  benchmark        qa             canary
                    ¦
                 skillify (codify scrape ? permanent 200ms replay)

SESSION STATE ------------------------------------------------------------------
  context-save ? context-restore
  freeze ? unfreeze
  learn (cross-session knowledge)
  plan-tune (question sensitivity preferences)
```

---

## Skill Inventory

### IDEATION

**`office-hours`**  
YC-style forcing questions before any plan is written. Two modes: *startup*
(six questions exposing demand reality, status quo, narrowest wedge, desperate
specificity, observation, future-fit) and *builder* (design thinking brainstorm
for side projects, hackathons, open source). Saves a design doc. Upstream
prerequisite for all plan-review skills; run first when the problem framing is
unclear. No code context required.

---

### PLANNING

**`plan-ceo-review`**  
Scope and ambition audit on a plan doc. Four modes: SCOPE EXPANSION (challenge
assumptions, find the 10-star product), SELECTIVE EXPANSION (hold scope,
cherry-pick high-value additions), HOLD SCOPE (maximum rigor within current
boundaries), SCOPE REDUCTION (strip to essentials). Interactive — surfaces each
finding for user approval. Enriched by prior `office-hours` run.

**`plan-eng-review`**  
Architecture lock-in. Walks through data flow, diagrams, edge cases, test
coverage, and performance implications. Interactive with opinionated
recommendations per finding. Produces a hardened execution plan before
implementation begins. Enriched by `office-hours`.

**`plan-design-review`**  
Designer's eye applied to a plan doc. Rates each design dimension 0–10, explains
what a 10 would require, then edits the plan to close the gap. Works in plan
mode (pre-implementation); use `design-review` for live site audits. Enriched
implicitly by `design-consultation` output (DESIGN.md).

**`plan-devex-review`**  
Developer experience audit on a plan. Explores DX personas, benchmarks against
competitors, designs magical onboarding moments, traces friction points. Three
modes: DX EXPANSION (competitive moat), DX POLISH (bulletproof every
touchpoint), DX TRIAGE (critical gaps only). Applies to APIs, CLIs, SDKs,
libraries, platforms, and developer-facing docs. Boomerang: `devex-review`
verifies the live result against plan predictions.

**`autoplan`**  
Orchestrates `plan-ceo-review`, `plan-eng-review`, `plan-design-review`, and
`plan-devex-review` sequentially using six pre-encoded decision principles.
Auto-decides routine tradeoffs, surfaces only "taste" decisions (close
approaches, borderline scope, cross-agent disagreements) at a final approval
gate. One command ? fully reviewed plan.

---

### EXECUTION

**`investigate`**  
Systematic debugging. Four phases: investigate (gather evidence), analyze
(isolate variable), hypothesize (ranked causes), implement (fix with root cause
confirmed). Iron Law: no code change without confirmed root cause. Invoked on
errors, stack traces, regressions, or any "it was working yesterday" report.
Supersedes ad-hoc debugging.

**`health`**  
Code quality dashboard. Wraps project-native tools (type checker, linter, test
runner, dead code detector, shell linter) into a weighted composite 0–10 score.
Tracks trends across runs. Use as a gate before planning a refactor or before
`ship`.

---

### SESSION SAFETY MODIFIERS

These activate for the session duration and modify agent behavior, not code.

**`careful`**  
Intercepts destructive shell commands (rm -rf, DROP TABLE, force-push, git reset
--hard, kubectl delete) with a warning + override prompt before execution.

**`freeze`**  
Restricts Edit and Write tools to one specified directory. Blocks lateral
accidental changes during focused debug or refactor sessions.

**`unfreeze`**  
Clears the `freeze` boundary without ending the session.

**`guard`**  
Composition of `careful` + `freeze`. Maximum safety posture for prod access or
shared environments.

---

### BROWSER LAYER

**`browse`**  
Headless Chromium primitive. ~100ms per command. Navigate URLs, click elements,
fill forms, upload files, handle dialogs, diff before/after actions, take
annotated screenshots, assert element states, check responsive breakpoints.
Foundation for `qa`, `design-review`, `devex-review`, `canary`, `benchmark`,
`scrape`. Not a full session — stateless per invocation unless daemonized.

**`open-gstack-browser`** (also `connect-chrome`)  
Headed Chromium with sidebar extension. Real browser window, live activity feed,
AI-controlled via sidebar chat. Anti-bot stealth. Auto-routes model by task:
Sonnet for navigation/actions, Opus for reading/analysis. Includes layered
prompt-injection defense (ML classifier + Haiku transcript check + canary
token).

**`setup-browser-cookies`**  
Imports cookie domains from a real Chromium profile into the headless browse
session. Prerequisite for testing authenticated flows. Must run before any
`browse`/`qa` session requiring login state.

**`pair-agent`**  
Shares the live browser session with a remote agent (OpenClaw, Hermes, Codex,
Cursor, or any HTTP-capable agent). Generates a setup key and scoped access
policy (read-write or admin).

**`scrape`**  
Read-only data extraction from a web page. First-run prototypes the flow via
browser primitives and returns JSON. Subsequent calls on matching intent route to
a codified browser-skill (~200ms). For mutating flows, use a separate automation
skill.

**`skillify`**  
Codifies the most recent successful `scrape` flow into a permanent browser-skill
on disk (script.ts + script.test.ts + fixture). Run immediately after a scrape
succeeds. Future invocations with matching intent run the cached script instead
of re-driving the page.

**`benchmark`**  
Performance regression detection using browse. Establishes baselines for page
load, Core Web Vitals, and bundle sizes. Compares before/after on every PR.
Tracks trends.

**`benchmark-models`**  
Cross-model comparison for any skill. Runs the same prompt through Claude, GPT,
and Gemini side-by-side. Reports latency, tokens, cost, and optional LLM-judge
quality score. Answers model selection with data instead of preference.

---

### REVIEW GATES

**`review`**  
Pre-landing PR diff audit. Checks SQL safety, LLM trust boundary violations,
conditional side effects, migration reversibility, and structural issues against
the base branch. Specialist sub-agents per concern domain (security, performance,
API contract, testing, maintainability). Gates `ship`.

**`codex`**  
Adversarial second opinion via OpenAI Codex CLI. Three modes: *code review*
(independent diff review with pass/fail gate), *challenge* (tries to break the
code), *consult* (ask anything with session continuity). The "200 IQ adversarial
developer" overlay. Can augment or replace `review` for a cross-model challenge.

**`cso`**  
Chief Security Officer audit. Infrastructure-first: secrets archaeology,
dependency supply chain, CI/CD security, LLM/AI trust surface, skill supply
chain scanning. Then OWASP Top 10 and STRIDE threat modeling with active
verification. Two modes: *daily* (8/10 confidence gate, zero noise) and
*comprehensive* (monthly deep scan, 2/10 bar). Trend tracking across runs.

**`qa`**  
Test-fix-verify loop on a live web application. Three tiers: *Quick* (critical
and high bugs only), *Standard* (+ medium), *Exhaustive* (+ cosmetic). Each fix
committed atomically and re-verified before moving on. Produces before/after
health scores and a ship-readiness summary.

**`qa-only`**  
Same as `qa` but report-only. Produces structured bug report with health score,
screenshots, and repro steps without touching source code.

**`design-review`**  
Visual QA on a live site. Finds spacing inconsistencies, hierarchy problems,
responsive breakpoint failures, and AI-generated slop patterns. Fixes each issue
in source, commits atomically, re-verifies with before/after screenshots. Live
counterpart to `plan-design-review` (boomerang).

**`devex-review`**  
Live DX audit using `browse`. Actually navigates docs, runs the getting-started
flow, times time-to-hello-world (TTHW), screenshots error messages, evaluates
CLI help text. Produces a DX scorecard with evidence. Boomerang to
`plan-devex-review` predictions.

---

### SHIP PIPELINE

**`ship`**  
Full ship workflow: merge base branch, run tests, invoke `review`, bump VERSION,
update CHANGELOG, commit, push, create PR. Supersedes manual PR creation.
Outputs a PR ready for `land-and-deploy`.

**`landing-report`**  
Read-only queue dashboard. Shows which VERSION slots are claimed by open PRs and
which parallel workspaces have WIP likely to ship soon. No mutations — snapshot
only.

**`land-and-deploy`**  
Takes over after `ship` creates the PR. Merges, waits for CI and deploy, runs
`canary` checks to verify production health. Requires `setup-deploy`
configuration.

**`setup-deploy`**  
Detects deploy platform (Fly.io, Render, Vercel, Netlify, Heroku, GitHub
Actions, custom), production URL, health check endpoints, and deploy status
commands. Writes config to CLAUDE.md so all future `land-and-deploy` runs are
automatic.

**`canary`**  
Post-deploy monitoring via `browse`. Watches the live app for console errors,
performance regressions, and page failures. Periodic screenshots compared against
pre-deploy baselines. Alerts on anomalies.

**`document-release`**  
Post-ship doc sync. Reads all project docs, cross-references the diff, updates
README, ARCHITECTURE, CONTRIBUTING, and CLAUDE.md to match what shipped.
Polishes CHANGELOG voice, cleans up TODOS, optionally bumps VERSION.

---

### DESIGN TRACK

**`design-consultation`**  
Full design system generation from scratch. Researches the landscape, proposes
aesthetic + typography + color + layout + spacing + motion system, generates
font/color preview pages. Produces DESIGN.md as the project's design source of
truth. Run once per new project with no existing design system.

**`design-shotgun`**  
Generates multiple design variants, opens a comparison board, collects structured
feedback, iterates. Pure exploration — no implementation. Run when visual
direction is undefined.

**`design-html`**  
Converts approved mockups (from `design-shotgun`, `plan-ceo-review`, or
`plan-design-review`) into production-quality Pretext-native HTML/CSS. Text
reflows, heights computed, layouts dynamic, zero deps beyond a 30KB Pretext
library. Finalizes design into code.

---

### PERSISTENCE / INTELLIGENCE

**`learn`**  
Cross-session knowledge management. Review, search, prune, and export what the
agent has learned about the project. Learnings persist across sessions and
compound — patterns, pitfalls, past decisions. Run when "didn't we fix this
before?" comes up.

**`context-save`**  
Captures git state, decisions made, and remaining work to a snapshot. Enables
handoff across sessions or parallel workspaces without losing thread.

**`context-restore`**  
Loads the most recent `context-save` snapshot. Reconstructs working state across
Conductor/worktree handoffs.

**`retro`**  
Weekly engineering retrospective. Analyzes commit history, work patterns, code
quality metrics. Team-aware: per-person breakdowns, shipping streaks, test health
trends, growth areas. Persistent history with trend tracking.

**`plan-tune`**  
Self-tuning question sensitivity. Review which `AskUserQuestion` prompts fire
across skills, set per-question preferences (never-ask / always-ask /
ask-only-for-one-way-doors), inspect dual-track developer psychographic profile
(declared preferences vs behavioral signals). Run when the agent is asking too
many questions.

**`setup-gbrain`**  
Installs gbrain (local PGLite or Supabase-backed knowledge store), registers as
MCP server, configures per-repo trust policy. Enables persistent cross-session
memory and the gbrain search/put-page MCP tools. Optional infrastructure — gstack
functions without it.

---

### UTILITIES

**`make-pdf`**  
Renders any markdown file to publication-quality PDF. Proper margins, intelligent
page breaks, page numbers, cover page, running headers, curly quotes, clickable
TOC, optional DRAFT watermark. Not a draft artifact.

**`office-hours`** (see Ideation — also usable standalone at any phase for design
thinking brainstorm or YC-style demand validation)

**`gstack-upgrade`**  
Updates gstack itself. Detects global vs vendored install, runs upgrade, surfaces
changelog.

---

## Dependency Graph (edges)

```
# Enrichment (optional, pre-loads context)
office-hours --? plan-ceo-review
office-hours --? plan-eng-review
office-hours --? plan-devex-review
office-hours --? autoplan

# Orchestration
plan-ceo-review    -+
plan-eng-review    -¦--? autoplan
plan-design-review -¦
plan-devex-review  -+

# Design system ? plan ? live audit (boomerang loops)
design-consultation --? DESIGN.md --? plan-design-review (infers existing system)
design-shotgun --? design-html (approved variant ? production code)
plan-design-review --? design-review (plan predicts; live verifies)
plan-devex-review --? devex-review (plan predicts; live verifies)

# Browser prerequisite
setup-browser-cookies --? browse
browse --? qa, qa-only, design-review, devex-review, canary, benchmark, scrape

# Scrape codification
scrape --? skillify (one-time: codify ? future calls use cached script)

# Safety composition
careful -+
freeze  ----? guard

# Session pair
freeze ? unfreeze
context-save ? context-restore

# Ship pipeline (sequential)
[code] --? review --? ship --? land-and-deploy --? canary
                                      ¦
                               document-release

# Review gates (all gate ship)
review    -+
codex     -¦--? ship
cso       -¦
qa        -+

# Debug loop (iterative until resolved)
investigate --? [fix] --? review --? ship

# Infrastructure setup (one-time per project)
setup-deploy --? land-and-deploy
setup-gbrain --? learn, context-save/restore (enables persistence layer)
```

---

## Phase–Skill Matrix

| Phase | Skills |
|---|---|
| Ideation | office-hours |
| Planning | plan-ceo-review, plan-eng-review, plan-design-review, plan-devex-review, autoplan |
| Execution | investigate, health, careful, freeze, unfreeze, guard |
| Design | design-consultation, design-shotgun, design-html |
| Browser primitives | browse, open-gstack-browser, setup-browser-cookies, pair-agent |
| Data extraction | scrape, skillify |
| Review gates | review, codex, cso, qa, qa-only, design-review, devex-review |
| Benchmarking | benchmark, benchmark-models |
| Ship | ship, landing-report, land-and-deploy, canary |
| Post-ship | document-release, retro |
| Session state | context-save, context-restore, learn, plan-tune |
| Infrastructure | setup-deploy, setup-gbrain, gstack-upgrade |
| Utilities | make-pdf |

---

## Harness Adaptation Notes

All skills are pure Markdown prompt specs with no runtime dependencies beyond
the tools they declare (Bash, Read, Write, Edit, Grep, Glob, Agent,
AskUserQuestion, WebSearch). The `browse` skills additionally require a compiled
Chromium binary (`browse/src/` is TypeScript compiled via Bun).

To port to a different harness:

- **OpenClaw / multi-agent orchestrators:** Map each skill to a persona
  definition. Use `benefits-from` edges as optional context-injection hints
  before persona activation. The `autoplan` orchestration pattern maps directly
  to a sequential sub-agent chain.
- **AGENTS.md / Copilot:** Embed skill descriptions as role sections in
  AGENTS.md. Trigger via code comments or conversation patterns matching
  the trigger phrases.
- **Aider / OpenCode:** Wrap skill descriptions as `--system-prompt` overlays
  per task type. Chain via shell scripts for pipeline phases.
- **Browser skills:** Require the compiled `browse` binary or a Playwright/CDP
  equivalent. The session cookie import (`setup-browser-cookies`) requires
  filesystem access to the real Chromium profile.

The `preamble-tier` field (1–4) controls how much ambient context is loaded
before the skill runs — not pipeline position. Tier 4 skills (ship, land-and-deploy,
qa, review, design-review) load the most session context; Tier 1 skills (browse,
benchmark, make-pdf) are stateless primitives.