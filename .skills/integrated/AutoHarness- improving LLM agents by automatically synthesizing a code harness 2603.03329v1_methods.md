The paper's core contribution is an iterative code synthesis algorithm that uses tree search (with Thompson sampling) and LLM-based code refinement, driven by environment feedback, to generate a robust "code harness" (action verifier or policy) that prevents illegal actions in complex environments.

The main algorithm decomposes into:
1. Maintaining a tree of code hypotheses (nodes = candidate harnesses).
2. Selecting nodes to refine via Thompson sampling using a heuristic (legal action rate or reward).
3. Rolling out code harnesses in environment(s), collecting errors and feedback.
4. Using the LLM as a code refiner, conditioned on failed steps and error logs, to propose new code variants.
5. Looping until code reaches a desired heuristic value or timeout.

Below are the pseudocode blocks for the two main settings described: Harness-as-Action-Verifier and Harness-as-Policy.

---

### AutoHarness Code Synthesis (Harness-as-Action-Verifier)

**Inputs:**
- env : environment object (provides reset(), step(), etc.)
- base_code : initial code harness (contains propose_action(obs) and is_legal_action(obs, action))
- LLM : language model with code synthesis capability
- max_iterations : int (maximum synthesis iterations)
- N_envs : int (number of parallel environments, e.g. 10)
- rollout_steps : int (maximum steps per rollout, e.g. 1000)
- heuristic_goal : float (desired legal action rate, e.g. 1.0)
- heuristic_weight : float (for Thompson sampling, e.g. 1.0)

**Outputs:**
- best_code : code harness achieving heuristic_goal

```
initialize tree of code hypotheses with root node containing base_code
for iteration in 1 to max_iterations:
    # 1. Select node to refine via Thompson sampling
    for each node in tree:
        node.heuristic_value = average legal action rate from previous rollouts
        node.thompson_sample = sample from Beta(node.successes + 1, node.failures + 1) * heuristic_weight [inferred]
    select node_to_refine = node with highest thompson_sample

    # 2. Evaluate node's code in N_envs
    legal_action_count = 0
    total_action_count = 0
    failed_steps = []
    for env_idx in 1 to N_envs:
        obs = env.reset()
        for step in 1 to rollout_steps:
            action = node_to_refine.code.propose_action(obs)
            if not node_to_refine.code.is_legal_action(obs, action):
                # code thinks action is illegal
                failed_steps.append((obs, action, "Action flagged as illegal by harness"))
                break
            next_obs, reward, done, info = env.step(action)
            total_action_count += 1
            if info.get('illegal_move', False) or env execution error:
                # code allowed an illegal move or crashed
                failed_steps.append((obs, action, "Environment reports illegal move or execution error"))
                break
            else:
                legal_action_count += 1
            if done:
                break
            obs = next_obs
        if len(failed_steps) >= 5:
            break
    node_to_refine.successes = legal_action_count
    node_to_refine.failures = total_action_count - legal_action_count
    node_to_refine.heuristic_value = legal_action_count / max(1, total_action_count)

    # 3. If heuristic goal reached, return code
    if node_to_refine.heuristic_value >= heuristic_goal:
        return node_to_refine.code

    # 4. Prepare LLM refinement input
    # (a) Provide old code harness (propose_action and is_legal_action functions)
    # (b) Provide up to 5 failed steps with environment error messages
    # (c) Specify which function(s) to refine:
    #     If is_legal_action(obs, action) returned True but action is invalid: refine both functions.
    #     If is_legal_action returned False and action is invalid: refine propose_action only.
    llm_input = {
        "old_code": node_to_refine.code,
        "failed_steps": failed_steps[:5],
        "refine_instructions": based on error type as above
    }
    new_code = LLM.refine_code(llm_input)

    # 5. Add new node to the tree as child of node_to_refine
    add new node to tree with code = new_code, parent = node_to_refine
# If heuristic_goal not reached in max_iterations, return best code found
return code from node with highest heuristic_value in tree
```

**Inferred / Ambiguous:**
- Thompson sampling details use Beta(successes+1, failures+1), as per standard, but paper does not specify exact heuristic implementation.
- The error message mapping to function(s) to refine is specified in text but not as precise logic. Mapping inferred from: "If is_legal_action() returns True but the action is invalid, we refine both functions; while if is_legal_action() returns False and the action is invalid, we only refine propose_action()."
- Environment step interface and info['illegal_move'] field are inferred from standard RL conventions.
- The paper does not specify how tree nodes are stored or traversed beyond parent/child linkage.
- The logic for breaking after 5 failed steps is per "At most 5 failed steps are sampled and fed to the Critic".
- How the LLM is prompted with the failed steps and old code is not given in full detail.
- The exact format of the code harness object is not specified.

---

### AutoHarness Code Synthesis (Harness-as-Policy)

**Inputs:**
- env : environment object (provides reset(), step(), etc.)
- base_code : initial policy code (Python function: propose_action(obs))
- LLM : language model with code synthesis capability
- max_iterations : int (e.g. 256)
- N_envs : int (number of parallel environments)
- rollout_steps : int (max steps per rollout)
- heuristic_goal : float (desired value, e.g. 1.0)

**Outputs:**
- best_policy_code : code (propose_action(obs)) achieving highest heuristic value

```
initialize tree of code hypotheses with root node containing base_code
for iteration in 1 to max_iterations:
    # 1. Select node to refine via Thompson sampling
    for each node in tree:
        node.heuristic_value = average H from previous rollouts
        node.thompson_sample = sample from Beta(node.successes + 1, node.failures + 1) [inferred]
    select node_to_refine = node with highest thompson_sample

    # 2. Evaluate node's code in N_envs
    H_total = 0
    rollout_count = 0
    failed_steps = []
    for env_idx in 1 to N_envs:
        obs = env.reset()
        illegal_action = False
        reward = 0
        for step in 1 to rollout_steps:
            action = node_to_refine.code.propose_action(obs)
            next_obs, reward, done, info = env.step(action)
            if info.get('illegal_move', False) or env execution error:
                illegal_action = True
                failed_steps.append((obs, action, "Environment reports illegal move or execution error"))
                break
            if done:
                break
            obs = next_obs
        # Heuristic for harness-as-policy: H = 0 if illegal, else 0.5 + 0.5 * reward
        if illegal_action:
            H = 0
        else:
            H = 0.5 + 0.5 * reward
        H_total += H
        rollout_count += 1
        if len(failed_steps) >= 5:
            break
    node_to_refine.successes = H_total
    node_to_refine.failures = rollout_count - H_total [inferred]
    node_to_refine.heuristic_value = H_total / max(1, rollout_count)

    # 3. If heuristic goal reached, return code
    if node_to_refine.heuristic_value >= heuristic_goal:
        return node_to_refine.code

    # 4. Prepare LLM refinement input
    llm_input = {
        "old_code": node_to_refine.code,
        "failed_steps": failed_steps[:5],
        "refine_instructions": "Refine propose_action to avoid illegal actions and maximize reward." [inferred]
    }
    new_code = LLM.refine_code(llm_input)

    # 5. Add new node to the tree as child of node_to_refine
    add new node to tree with code = new_code, parent = node_to_refine
# If heuristic_goal not reached, return code from node with highest heuristic_value
return code from node with highest heuristic_value in tree
```

**Inferred / Ambiguous:**
- The definition of "successes" for Thompson sampling is mapped to H_total; failures as (rollout_count - H_total) is inferred.
- The reward normalization (r in [0.0,1.0]) and the H formula are directly from paper.
- The failure/error feedback to the LLM is less detailed in this setting; generic instructions are inferred.
- How the LLM is prompted is not specified.
- As in the first block, environment info['illegal_move'] and step semantics are inferred from standard RL conventions.
- The policy code is assumed not to call the LLM at inference time (per paper).

---