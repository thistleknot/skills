# Provenance contract

## CURRENT

The rollup answers: what is required now, which revision is represented in code,
what evidence supports it, when it changed, and which decisions explain it.
This is a reporting contract; no history collector ships with this skill.

## Identity and links

Use stable feature, requirement, model-element, decision, and acceptance-scenario
IDs; preserve existing IDs and never derive identity solely from a title or path.
Use a content hash for a revision, and record its Git commit when committed.
Record splits, merges, and replacements as explicit supersession relationships;
do not silently reuse a retired identity for a different obligation.

Trace forward and backward through:

```text
feature -> specification -> requirement revision -> model/diagram element
    -> generated symbol/contract -> acceptance scenario -> run evidence
decision -> affected requirements/models/generator choices
```

Store explicit links in the existing needs model and generation manifest;
derive inverse links instead of maintaining duplicate mutable lists.
An external graph is an index over these records, not a second editable source
of requirements or a replacement for evidence.

## Minimum records

| Record | Required information |
|---|---|
| Requirement revision | Stable ID, feature, content hash, source location, lifecycle state, supersession if applicable |
| Transport | Source and output hashes, mapping, method/version, excluded/unresolved obligations and reasons |
| Generation | Input snapshot, interpreter, tool/dependency/template/configuration identities, generated output hashes, symbol mappings |
| Verification | Requirement revision, code/output hash, scenario/test ID, expected and observed result, pass/fail, run identity |
| Observation | Tool/version, command, scanned scope/exclusions, source locations, provenance label, runtime scenario if applicable |
| Decision | Stable ID, decision, rationale, alternatives, evidence, affected IDs, date, superseded decision if applicable |
| History event | Entity ID/revision, event type, parent/child commit comparison, recorded time, evidence reference |

Do not put a commit's own ID into a tracked file generated within that commit;
bind tracked content hashes to commit IDs in the post-commit or CI report.
Dirty snapshots must include their content identity and dirty state separately.

## Lifecycle and evidence

Keep specification lifecycle (`active`, `retired`, `superseded`) separate from
implementation evidence (`unverified`, `passing`, `failing`, `stale`).
An active requirement can have no implementation; a retired requirement can
still have code that must be removed.
For the current report, compare requirement revisions and output hashes against
current evidence; a previous pass does not certify modified inputs or output.
Report passing acceptance as evidence for the specified scenarios, not proof
that all possible behavior is correct.

Retirement preserves the requirement and its rationale as history.
When retirement requires removal, regenerate without the feature, verify its
absence, and remove only orphaned generated code within the owned scope.
Restoration keeps the original identity but needs evidence for the restored
revision; a later restoration does not erase the retirement interval.
Fail unresolved hard deletion from authored requirements unless an explicit
retirement or supersession record explains the disappeared identity.

## Git queries and aggregates

- Default history scope: ancestors of the requested revision, default HEAD, in a full clone; report shallow or missing history as incomplete.
- Define events by entity changes between snapshots, not timestamps or commit-message keywords.
- Compare merge results to their first parent for integration events; retain parent identities and distinguish side-branch origin from integration.
- Find the introducing commit through the ancestry graph when origin detail is requested; incomparable branch origins remain multiple origins.
- Count each stable entity once in each added/changed/retired/restored set for a selected range; expose event frequency as a separate metric.
- Compute current totals from the ending snapshot, not by blindly summing commit deltas across merges.
- Count a feature as currently passing only when all its active mandatory requirement revisions have matching passing evidence.
- Report a feature with zero active mandatory requirements as having no active obligations, not automatically implemented.
- Derive first-evidenced implementation from archived revision-bound runs; report unknown when historical runs are unavailable.
- Treat revert as another snapshot change and recompute status; do not subtract evidence by commit-message convention.

The minimum current table contains feature/requirement ID, lifecycle, current
requirement revision, represented revision in code, implementation evidence,
source/code links, and freshness.
The minimum historical table contains introductions, revisions, retirements,
restorations, first evidenced implementations, and integrations where distinct.
Allow commit-range and feature filters; expose totals with their denominator,
such as passing active mandatory requirements / active mandatory requirements.
Absent evidence is not a failed test and is not a pass.

## Freshness and diagrams

Regenerate reports at each validated revision and compare current content hashes
when displaying them; a previous successful report remains bound to its own
revision after a failed or dirty build.
Automated update hooks or watchers are optional deployment choices, not a
substitute for freshness checks.

Use the existing `sphinx` skill for Pyreverse structure, approximate code2flow
calls, and observed runtime calls; retain raw focused evidence and render the
canonical filtered views from needs.
Check pycallgraph's installed package/fork and interpreter compatibility before
adoption; do not silently substitute a tracer.
Include Graphify as a queryable cross-artifact index and refresh relevant paths;
preserve EXTRACTED/INFERRED/AMBIGUOUS distinctions and source snapshot identities.
Neither an absent trace edge nor an inferred graph edge proves architecture
conformance; enforce declared dependency and behavior contracts with checks.
