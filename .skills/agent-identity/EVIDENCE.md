## Evidence Index

| Tier | Source | Claim | Contract section grounded |
|---|---|---|---|
| 2 | https://github.com/NousResearch/hermes-agent | Hermes exposes a first-class `SOUL.md`, profile isolation, built-in memory, skills, session store, and cron-backed automation as separate surfaces. | Context; Steps 1-4; Example |
| 2 | https://hermes-agent.nousresearch.com/docs/user-guide/features/memory-providers | Built-in memory remains separate from external memory providers, supporting the split between static identity and evolving memory layers. | Step 2; Applicability Envelope |
| 2 | https://github.com/NousResearch/hermes-agent-self-evolution | Skill evolution is an offline optimization surface with guardrails and PR review, which supports evolving procedures without rewriting identity. | Step 5; Dead Ends |
| 3 | https://www.dailydoseofds.com/p/hermes-agent-masterclass/ | The Hermes walkthrough articulates the fixed-identity-above-memory pattern (`SOUL.md`), profile cloning, skill curation, and role-specific substrate binding in one coherent operator flow. | Context; Steps 1-5; Example |

## Notes

- The distinguishing contract grounded here is not "Hermes exists." It is the reusable
  pattern that identity should be static, first-loaded, and profile-isolated while
  memory and skills evolve beneath it.
