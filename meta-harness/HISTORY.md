# Meta-Harness History

## 2026-05-24

### Context
- Promoted intake content from `integrate/meta-harness/SKILL.md` into the live skill library.
- Wired `meta-harness` into the orchestration branch and key-relationship map in `README.md`.

### Lessons
1. Separation of concerns is load-bearing: requester-level objective framing and issue-level harness execution should be distinct lanes.
2. A parent manager layer reduces worker drift by forcing one scoped objective per child session.
3. Upstream-first repair mapping (source -> transform -> artifact) should be explicit before delegation to avoid downstream patch churn.

### Impact
- `meta-harness` now codifies the manager role above `agentic-harness`.
- The skill graph now documents where request decomposition stops and execution mechanics begin.
