# Subtractive Debugging — Evidence Index

Grounding citations for behavioral contracts in `subtractive-debugging/SKILL.md`.

## Evidence Index

| Tier | Source | Claim | Contract Section Grounded |
|---|---|---|---|
| 2 | `https://git-scm.com/docs/git-bisect` | `git bisect` formalizes regression isolation as narrowing from a known good state and a known bad state until the first introducing change is found | Step 1; Step 4 |
| 5 | `https://www.st.cs.uni-saarland.de/dd/` | Delta Debugging isolates failure-inducing circumstances by systematic testing and narrowing; it applies to code changes, inputs, and executions | Step 2; Step 3; Step 5 |
| 4 | Session 2026-05-15 in `Call To Power 2` | A surface-specific checker (`.modding-harness\gl-regression.ps1`) used `IMPROVE_ARCOLOGIES` as a stable control and isolated the first Great Library regression surface to the shrine-variant bundle collision introduced after `642ce10` | Example; exit criteria |

## Contradiction Count: 0

No known contradictions as of 2026-05-15.
