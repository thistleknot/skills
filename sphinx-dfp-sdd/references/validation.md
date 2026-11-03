# Validation procedure

## CURRENT

The factory is an OPEN hypothesis until the following gates actually run.
A reviewed example or a valid skill package is not an executed generation test.
Record each gate as OPEN, PASS, or FAIL with commands, inputs, outputs, elapsed
time, snapshot identity, and evidence paths.

## Hypotheses and discriminating evidence

| Candidate | Supporting observation | Kill condition |
|---|---|---|
| Formal RST and diagram semantics support executable generation | Generated behavior matches independent expected outcomes | A needed behavior requires downstream LLM interpretation or hand editing |
| The selected pipeline supports structure only | Classes and references regenerate, but executable rule translation is absent | Generated rules execute all pilot scenarios without manual implementations |
| The inputs remain semantically incomplete | A valid-looking requirement has no unique executable meaning | Explicit typed rules make the pilot translations unambiguous |

The first candidate is the objective, not an established conclusion.
More than one defect may coexist; isolate the earliest failing transformation.

## Dependency ladder

```text
discover Spec Kit -> transport obligations -> validate formal semantics
    -> generate Ecore/classes and behavior -> execute acceptance
    -> compare design/implementation -> roll up revision-bound history
```

Before each experiment, list assumptions per link as TESTED or OPEN with evidence.
Run the cheapest test of the earliest OPEN assumption alone.
If it passes, test the next link; if it fails, repair the root or disposition the
approach without spending compute downstream.
A newly discovered upstream assumption reopens that gate and invalidates
dependent conclusions until its effect is resolved.

Budget each experiment below 15 minutes and no more than three experiments
before disposition; state an estimated bound before execution and a timeout.
Shrink the fixture before reducing rigor; retain matched controls.
Time production builds separately from experiments and never use production
scale to discover whether a transformation works.

## Gate: specification and transport

Use three small sources: a simple obligation, a guarded obligation with an
acceptance scenario, and an ambiguous or unsupported obligation.
Verify source-to-need mappings and hash binding for the valid cases, and
source-local rejection or explicit unresolved disposition for the invalid case.
Do not silently omit unsupported obligations or mark an incomplete import
eligible for generation.
Transport technology remains open; its output contract does not.

## Gate: executable turn

Specify these fixtures before implementing the translator; they are factory
tests and do not establish final 4X game mechanics.

| Case | Given | When | Independent expected result |
|---|---|---|---|
| Valid transition | Turn=4, phase=active, stock=8, cost=3 | Resolve the declared action | Turn=5, stock=5, phase=active |
| Rejected action | Turn=7, phase=active, stock=1, cost=4 | Request the declared action | Explicit rejection; turn, phase, and stock unchanged |
| Exact boundary | Turn=2, phase=active, stock=6, cost=6 | Resolve the declared action | Turn=3, stock=0, phase=active |

Run each isolated fixture first, then the three-case battery; repeat the same
battery after each translator change.
Check actual need exports, textual diagram definitions, Ecore types/references,
generated operations, contract enforcement, and runtime state at their handoffs.
Also reject unknown types, unresolved IDs, contradictory rules, and unsupported
effects without leaving a successful-build marker.
Keep the expected states independent of code-generation templates so a shared
template error cannot make both implementation and test agree incorrectly.
Any stub, unimplemented operation, or hand-coded downstream fix fails this gate.

## Gate: reproducibility and architecture

Generate twice into separate clean output directories from identical validated
inputs and pinned tools; compare generated source bytes and canonical structural
model representations, retaining raw artifacts for diagnosis.
Specify normalization before comparing; never remove semantic differences to
force equality or use rendered diagram layout as executable semantics.
Keep run timestamps separate from deterministic artifact content.
Then change one rule and verify the corresponding behavior and trace mappings
change while unrelated generated behavior remains stable.

Build Sphinx HTML with warnings treated as errors; verify needs and diagram
exports, visible edges, source links, inventories, and revision labels.
Use the existing diagram skill for tool selection and rendered inspection.
Check declared forbidden dependencies explicitly and exercise relevant runtime
paths; static call candidates do not establish execution order.

## Gate: temporal rollups

Use a disposable repository isolated from the user's history; never create,
rewrite, or merge commits in the project merely to test reporting.
Build one small fixture with these known milestones:

1. Introduce a feature and requirement with no implementation evidence.
2. Generate its implementation and archive matching passing acceptance evidence.
3. Change the requirement while retaining the old evidence, producing stale coverage.
4. Regenerate and verify the changed revision.
5. Retire the requirement, remove the feature as specified, and verify absence.
6. Restore the identity and generate fresh evidence.
7. Add another requirement on a branch, merge it, then revert its integration.

Verify first introduction, first evidenced implementation, represented revisions,
retirement/restoration intervals, merge origin versus integration, range sets,
and final-snapshot totals; the reverted requirement must not remain active.
Check missing evidence, a dirty worktree, and shallow history explicitly.
The same active identity must not be counted twice because two parents contain it.
Archive evidence outside the commits being identified to avoid self-hashing.

## Skill delivery acceptance

- Run skill-creator's `quick_validate.py` on the delivered directory.
- Resolve all local links, including the installed sibling skill dependencies.
- Check each accepted conversation decision against the workflow and provenance contracts.
- Review three requests: bootstrap a factory, revise an implemented rule, and retire/restore a feature.
- In each review, identify the owning skill, the first gate, required evidence, and expected current/history report changes.
- Label reviews as reviews; report factory gates as unrun until executable tools exist.
- Review the delivered files for duplicate ownership, unnecessary helpers, dead references, and speculative implementation claims.
- Report exact shipped paths, checks actually run, remaining OPEN hypotheses, and the sprawl verdict.

Creating this skill requires no game engine, compiler, live tracer, or history
collector run; those are subsequent factory tasks governed by these gates.
