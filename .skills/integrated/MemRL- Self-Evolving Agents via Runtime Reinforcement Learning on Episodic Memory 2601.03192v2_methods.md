The paper's core contribution is MEMRL: a non-parametric, reinforcement learning-based memory retrieval and update algorithm for frozen LLM agents, centered on an Intent-Experience-Utility triplet memory structure, Two-Phase Retrieval (semantic recall + value-based selection), and runtime Q-value (utility) updates from environmental feedback.

Decomposition of core algorithmic components:
1. Intent-Experience-Utility memory triplet structure
2. Two-Phase Retrieval
   - Phase A: Similarity-based recall (top-k1 by similarity)
   - Phase B: Value-aware selection (top-k2 by combined normalized similarity and Q-value)
3. Runtime Utility Update (Monte Carlo style Q update)
4. Memory Expansion (write new experiences to memory)

Extracted methods below:

---

### Intent-Experience-Utility Memory Triplet Structure

**Inputs:**
- None [structure definition]

**Outputs:**
- M : list of triplets [(z_i : text, e_i : text, Q_i : float)] for i in 1..N

```
Each memory item m_i in M is a triplet:
    z_i = Intent (embedding or text of user query)
    e_i = Experience (raw text, e.g., solution, trajectory)
    Q_i = Utility (float; learned expected return of applying e_i to intents similar to z_i)
```

**Inferred / Ambiguous:** None

---

### Two-Phase Retrieval

**Inputs:**
- s : text or embedding (current query / user intent)
- M : list of triplets [(z_i, e_i, Q_i)] (memory bank)
- Emb : function (text -> vector) (embedding model)
- k1 : int (number of candidates for similarity recall)
- k2 : int (number of final contexts for value selection)
- delta : float (similarity threshold)
- lambda : float in [0,1] (Q-value weighting factor)

**Outputs:**
- M_ctx : list of triplets [(z_j, e_j, Q_j)] of length k2 (retrieved memory context)

```
# Phase A: Similarity-Based Recall
C = []
s_vec = Emb(s)
for each (z_i, e_i, Q_i) in M:
    sim_i = cosine_similarity(Emb(z_i), s_vec)
    if sim_i >= delta:
        C.append((z_i, e_i, Q_i, sim_i))
# Sort by sim_i descending and take top-k1
C = sorted(C, key=lambda item: item[3], reverse=True)[:k1]
if len(C) == 0:
    return []  # No context, agent must explore

# Phase B: Value-Aware Selection
# Z-score normalization of sim_i and Q_i over C
sim_list = [sim_i for (_, _, _, sim_i) in C]
Q_list = [Q_i for (_, _, Q_i, _) in C]
mean_sim, std_sim = mean(sim_list), std(sim_list)
mean_Q, std_Q = mean(Q_list), std(Q_list)
if std_sim == 0: std_sim = 1e-6  # avoid div by zero [inferred]
if std_Q == 0: std_Q = 1e-6      # avoid div by zero [inferred]

scored_C = []
for (z_i, e_i, Q_i, sim_i) in C:
    sim_norm = (sim_i - mean_sim) / std_sim
    Q_norm = (Q_i - mean_Q) / std_Q
    score = lambda * Q_norm + (1 - lambda) * sim_norm
    scored_C.append((z_i, e_i, Q_i, score))
# Sort by score descending and take top-k2
scored_C = sorted(scored_C, key=lambda item: item[3], reverse=True)[:k2]
M_ctx = [(z_i, e_i, Q_i) for (z_i, e_i, Q_i, _) in scored_C]
return M_ctx
```

**Inferred / Ambiguous:** 
- Handling std=0 in z-score normalization is inferred (std→1e-6).
- The precise type of z_i and s (text vs. embedding) is ambiguous but evidence supports text with embedding via Emb.
- Sorting and selection in both phases is explicitly described.

---

### Runtime Utility Update (Monte Carlo Q-value Update)

**Inputs:**
- m_used : list of triplets [(z_j, e_j, Q_j)] (the memory items used in current context)
- r : float (environmental reward for current episode)
- alpha : float (learning rate in (0,1])
- M : list of triplets [(z_i, e_i, Q_i)] (memory bank, to be updated in-place)

**Outputs:**
- M : updated list of triplets [(z_i, e_i, Q_i)]

```
for each (z_j, e_j, Q_j) in m_used:
    Q_j_new = Q_j + alpha * (r - Q_j)
    # Update the memory triplet in M
    find index idx in M where M[idx][0] == z_j and M[idx][1] == e_j
    if idx is found:
        M[idx] = (z_j, e_j, Q_j_new)
    else:
        [unknown] # If not found, behavior is unspecified
```

**Inferred / Ambiguous:**
- Updating only the triplets used in the retrieved context is explicit.
- Handling missing triplets is [unknown] (not described).
- Reward r assignment is environment-dependent, not detailed.
- No description of credit assignment when multiple memories are used; update is applied to all used memories.

---

### Memory Expansion (Writing New Experience)

**Inputs:**
- s : text (current user intent)
- a : text (agent's generated action/solution)
- r : float (reward received)
- Summarize : function (trajectory -> text) (LLM-based summarization)
- Q_init : float (initial Q-value for new memory, chosen by implementation)
- M : list of triplets [(z_i, e_i, Q_i)] (memory bank, to be updated in-place)

**Outputs:**
- M : updated list of triplets [(z_i, e_i, Q_i)]

```
e_new = Summarize(a)  # e.g., summarize action/trajectory using LLM
z = s
# Q_init can be 0 or r or another heuristic [inferred]
append (z, e_new, Q_init) to M
```

**Inferred / Ambiguous:**
- The Summarize function is LLM-based, but its precise behavior is not specified.
- Q_init is not specified; could be set to 0, r, or another default.
- No deduplication or memory management policy specified.

---

### End-to-End MEMRL Agent Loop

**Inputs:**
- s : text (current query/intent)
- M : list of triplets [(z_i, e_i, Q_i)] (memory bank)
- Emb : function (text -> vector)
- k1, k2, delta, lambda : retrieval hyperparameters
- alpha : float (Q-value learning rate)
- Q_init : float (initial Q for new memories)
- Summarize : function (trajectory -> text)
- FrozenLLM : function (s, M_ctx) -> a (frozen language model)
- Environment : function (a) -> r (environmental reward)

**Outputs:**
- M : updated list of triplets [(z_i, e_i, Q_i)]

```
# 1. Two-Phase Retrieval
M_ctx = TwoPhaseRetrieval(s, M, Emb, k1, k2, delta, lambda)

# 2. Generate action using the frozen LLM with retrieved context
a = FrozenLLM(s, M_ctx)

# 3. Execute action and receive reward
r = Environment(a)

# 4. Update Q-values for used memories (if any)
M = RuntimeUtilityUpdate(M_ctx, r, alpha, M)

# 5. Summarize experience and expand memory
e_new = Summarize(a)
append (s, e_new, Q_init) to M
```

**Inferred / Ambiguous:**
- The order of steps is explicit from the text and Figure 3.
- Details of the FrozenLLM input formatting are not specified.
- Summarize function is LLM-based, but implementation is unspecified.
- No explicit memory eviction or deduplication policy is given.

---