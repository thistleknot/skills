You want the paper’s **main methods** turned into pseudo-code, not the prose around them. The load-bearing parts are the AHE outer loop and its three observability pillars: component observability, experience observability, and decision observability.

[observed] The paper presents **Algorithm 1 AHE outer loop** as the core method.  
[observed] The paper describes **component observability** as a decoupled, file-level harness substrate.  
[observed] The paper describes **experience observability** as layered trajectory distillation through Agent Debugger.  
[observed] The paper describes **decision observability** as a change manifest with self-declared predictions and next-round verification.  
[inferred] The paper’s main method is best represented as one outer optimization loop plus three supporting subroutines.  
[inferred] The most faithful pseudo-code should preserve rollback, attribution, distillation, editing, and commit order.

```text
Procedure AHE_MAIN(seed_harness H0, base_model M, benchmark D, rollouts_per_task k, max_iterations N):
    Require:
        - H0 is a valid minimal harness workspace
        - M is fixed during evolution
        - D is a benchmark with tasks that can be rolled out
        - k >= 2 for pass@1 estimation and attribution stability
        - N >= 1
    Guarantee:
        - Returns the best harness encountered during evolution
        - Every accepted edit is written to version control
        - Every iteration produces structured evidence and a change manifest
    Maintain:
        - Only harness workspace files are editable
        - Runs directory, tracer, verifier, and model configuration remain read-only
        - Each iteration preserves rollback capability at file granularity

    H_best ? H0

    for t in 1..N do:
        T_t ? ROLLOUT(M, H_best, D, k)
        T~_t ? CLEAN(T_t)

        if t = 2 then:
            V_t ? ATTRIBUTE(previous_manifest C_{t-1}, previous_traces T_{t-1}, current_traces T_t)
            H_prev ? ROLLBACK(H_best, V_t)
        else:
            V_t ? Ø
            H_prev ? H_best
        end if

        R_t ? AGENT_DEBUGGER(T~_t)
        (H_t, C_t) ? EVOLVE(H_prev, R_t, V_t)
        COMMIT(H_t, C_t, t)

        if PASS_AT_1(T_t) > PASS_AT_1(ROLLOUT(M, H_best, D, k)) then:
            H_best ? H_t
        end if
    end for

    return H_best
```

```text
Procedure ROLLOUT(model M, harness H, benchmark D, k):
    Require:
        - H can execute benchmark tasks
        - M can be queried under the harness
        - k >= 1
    Guarantee:
        - Returns k traces per task
    Failure modes:
        - Task timeout
        - Infrastructure abort
        - Tool or middleware error

    traces ? Ø
    for each task d in D do:
        traces[d] ? run M under H on d, repeated k times
    end for
    return traces
```

```text
Procedure CLEAN(traces T):
    Require:
        - T is a set of raw rollout traces
    Guarantee:
        - Returns traces with base64 and duplicate tool output removed
    Failure modes:
        - Over-aggressive cleanup can remove useful evidence if schema is malformed

    T_clean ? remove_base64(T)
    T_clean ? deduplicate_tool_output(T_clean)
    return T_clean
```

```text
Procedure ATTRIBUTE(previous_manifest C_prev, previous_traces T_prev, current_traces T_curr):
    Require:
        - C_prev exists from the prior iteration
        - T_prev and T_curr are comparable across iterations
    Guarantee:
        - Returns a verdict object identifying which prior edits should be kept or rolled back
    Failure modes:
        - If task mapping is inconsistent, attribution can become unreliable

    V ? compare predicted fixes/regressions in C_prev against observed deltas from T_prev to T_curr
    return V
```

```text
Procedure ROLLBACK(harness H, verdict V):
    Require:
        - H is a versioned workspace with file-level edits
        - V identifies rejected or unsafe edits
    Guarantee:
        - Returns harness H with rejected edits reverted
    Failure modes:
        - If edit boundaries are not file-local, rollback may be incomplete

    for each rejected_edit in V do:
        revert rejected_edit in H
    end for
    return H
```

```text
Procedure AGENT_DEBUGGER(clean_traces T~):
    Require:
        - T~ is cleaned rollout evidence
    Guarantee:
        - Returns layered evidence corpus: per-task reports plus benchmark overview
    Failure modes:
        - If traces are too sparse, root-cause inference may be weak

    reports ? analyze each task trajectory for failure patterns and success patterns
    overview ? aggregate reports into benchmark-level summary
    return (reports, overview)
```

```text
Procedure EVOLVE(harness H, evidence R, verdict V):
    Require:
        - H is editable only within the harness workspace
        - R is structured evidence from Agent Debugger
        - V contains attribution from the previous round
    Guarantee:
        - Returns updated harness H_new and a change manifest C_new
        - Each edit is paired with a predicted fix set and regression risk set
    Failure modes:
        - Overfitting to benchmark-specific evidence
        - Unsafe edit proposals outside allowed workspace

    C_new ? Ø
    H_new ? H

    for each evidence_item r in R do:
        candidate_edit ? propose edit to H_new based on r and V
        if candidate_edit is within allowed workspace then:
            apply candidate_edit to H_new
            add manifest entry to C_new:
                - evidence cited
                - inferred root cause
                - targeted fix
                - predicted fixes
                - predicted regressions
        end if
    end for

    return (H_new, C_new)
```

```text
Procedure COMMIT(harness H, manifest C, iteration t):
    Require:
        - H and C are consistent
        - iteration t is known
    Guarantee:
        - Writes a versioned git commit for the round
    Failure modes:
        - Missing or inconsistent manifest entries

    write H to workspace
    write C to manifest file
    git commit workspace at tag t
```

[observed] The paper also describes a one-shot explore agent that seeds reusable skills during iteration 1.  
[inferred] That can be represented as an optional bootstrap subroutine, not as the main loop itself.

```text
Procedure BOOTSTRAP_SKILLS(seed_source, references):
    Require:
        - seed_source contains the NexAU source
        - references contain public coding-agent examples
    Guarantee:
        - Returns a small initial skill set
    Failure modes:
        - Skills may be benchmark-specific if overfit during seeding

    skills ? extract reusable skills from seed_source and references
    return skills
```

[syllogism] The paper’s method is not a single optimizer over prompts; it is a closed loop over a fixed model and an editable harness.  
[syllogism] The loop needs three things to work: a clean action space, structured evidence, and a verifiable prediction ledger.  
[syllogism] Therefore, the correct pseudo-code is the outer AHE iteration plus the three subroutines that implement component, experience, and decision observability.