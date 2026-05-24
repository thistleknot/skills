---
name: reasoning_curation_sampler
description: >
  Construct a stratified, token-efficient training distribution for reasoning
  transfer using **conditional stratification**. Used when mixing disparate 
  linguistic classes (jokes, prose, definitions) into a single regimen. 
  Enforces strict length filtering per class and token-budget equality 
  to stabilize gradients and maximize structural transfer between classes.
metadata:
  status: active
  last_validated: 2026-05-09
  validation_method: logic
---

# Reasoning Curation Sampler

## When to Use

Use this skill when:

- preparing a multi-class SFT dataset where one goal is **reasoning transfer** (e.g., teaching a smaller model to associate puns with logic or irony)
- mixing highly disparate data types (e.g., short puns vs. long philosophical quotes)
- gradient variance is unstable due to mixed context lengths
- you need to force a "soft" balance across classes without drowning rare formats in volume

Do **not** use this skill when:

- the dataset is already homogenous in length and structure -> use standard random sampling
- you are doing raw continued pretraining (SMP) on pure text -> use `corpus_distributor` instead
- the goal is purely lexical retrieval without logical inference

---

## Scope Boundary and Paired Skills

This skill owns the **sampling distribution** and **batch construction** protocols.

It owns:

- **Conditional Stratification:** Defining length filters *per class* to preserve natural length profiles
- calculating token-balance weights to ensure equal token exposure across genres
- pairing "short/abstract" reasoning (jokes) with "long/grounded" reasoning (prose) via isomorphism
- generating the final batched stream

It does **not** own:

- the actual model training loop -> `training_engine`
- semantic graph storage or fact extraction -> `agentic_kg_memory`
- skill promotion or procedural updates -> `skill-wiki`

---

## Core Principles

- **Conditional Stratification:** Do not force all data into global bins. Instead, sample the *class first*, then apply the length filter within that class. This preserves the natural `P(length | class)` distribution.
- **Token Budget Equality:** Weights must scale by the inverse of the *expected length within your filter threshold*. This ensures that dense short formats (jokes) and sparse long formats (prose) contribute equally to the total token budget.
- **Isomorphic Anchoring:** Transfer "reasoning capability" by pairing structurally identical but semantically distinct formats (e.g., an irony-laden quote next to an ironic pun) rather than mixing them randomly.
- **Temperature Scheduling:** Use Softmax temperature as a curriculum dial—starting high for "exploration" (rare/long formats) and lowering it for "convergence" (grounded formats).

---

## Curation Protocol

1.  **Define Class-Length Profiles.**
    *   For each data class (Joke, Quote, Prose, etc.), calculate the conditional statistics:
        *   `μ_i`: Average token count for records *within your filter threshold*.
        *   `σ_i`: Variance within the threshold (to define the bins).
    *   *Note:* This step prevents "genre-length collision" where a short prose passage would be binned with long jokes in a global sort.

2.  **Calculate Class-Equalized Weights.**
    *   Calculate weights based on the inverse of the expected token cost: `W_class = 1 / μ_i`.
    *   Apply Softmax Balancing with Temperature `T` to get `P_class`:
        *   `P_class_i = exp((log(W_class_i)) / T) / Σ exp((log(W_class_j)) / T)`
    *   *Effect:* This ensures every *token* has equal probability of being sampled, regardless of whether it came from a short joke or a long quote.

3.  **Iterative Sampling Loop (The "Outer Filter").**
    *   **Step A (Class Draw):** Select a class `C` from the distribution `P_class`.
    *   **Step B (Record Draw):** Draw a random record from class `C`.
    *   **Step C (Inner Filter):** Check if the record's length falls within your 95% interval window for class `C`.
        *   If *Yes*: Proceed to batch assembly.
        *   If *No*: Reject and return to Step A.

4.  **Batch Assembly.**
    *   Maintain a running `current_batch_tokens`.
    *   Add record tokens until `current_batch_tokens` reaches the target batch size (or hits the `max_tokens_of_bin` for the drawn class).
    *   *Constraint:* Pad only to the `max_tokens_of_bin` (or the length of the longest record in the current batch). Do not pad to the absolute global maximum, or you waste compute.

5.  **Stream and Verify.**
    *   Output the batch stream. Ensure that the final distribution of "Reasoning" classes (Jokes/Logic) matches the `P_class` target.

---

## Output Artifacts

- **Batch Stream:** A generator yielding strictly padded, token-balanced batches.
- **Weight Map (`sampling_weights.json`):** A JSON mapping of Class to its final Softmax probability (based on length-normalized weights).
- **Filter Map (`length_filters.json`):** A lookup table defining the min/max token thresholds for each class.
- **Pairing Index (`isomorphic_map.json`):** A lookup table linking specific short-form reasoning to long-form reasoning for curriculum pairing.

---

## Routing Rules

| Artifact kind | Destination |
| --- | --- |
| Binned and weighted data | `training_engine` (or raw torch DataLoader) |
| Isomorphic Pairing Map | `dataset_augmentation` (for synthesis) |
| Sampling weights | `training_config.yaml` |

---

## Example: The "Joke-to-Prose" Transfer

A smaller model is being trained on a mix of "Laffy Taffy" puns and Brown Corpus prose. The goal is to teach the model **abductive inference**.

1.  **Class-First Sampling:** The sampler draws a class. Let's say it draws "Joke" with probability `0.4` and "Prose" with probability `0.6`.
2.  **Conditional Filtering:**
    *   For the **Joke** draw: The system applies the "Joke Length Filter" (e.g., 10–50 tokens). It rejects a 60-token joke but accepts a 30-token pun.
    *   For the **Prose** draw: The system applies the "Prose Length Filter" (e.g., 200–600 tokens). It rejects a 50-token definition.
3.  **Token Equalization:** Because Jokes are short (μ_joke = 20) and Prose is long (μ_prose = 400), the sampler up-weights the Jokes by a factor of 20.
4.  **Pairing:** The sampler finds a specific Joke about a "Doctor" and pairs it with a Prose passage about a "Doctor" (e.g., a medical metaphor).
5.  **Result:** The model is forced to process high-entropy tokens (jokes) and low-entropy tokens (prose) in equal quantities, learning the *abductive structure* rather than just the vocabulary.

---

## Dead Ends — Do Not Use

### Global Length Binning
Forcing all classes into a single set of quartiles (e.g., Q1 = 10-50 tokens) creates semantic mismatches. A 40-token joke and a 40-token definition belong to different reasoning classes and should not be binned together if your goal is class-balanced transfer.

### Uniform Class Sampling
If you assign a "25% chance" to each class regardless of length, you will drown the model in short data (jokes/definitions) and starve it of long context. Always weight by **inverse token cost**.

### Pairing Semantically, Not Structurally
Don't pair a joke about a "doctor" with a medical quote about a "doctor." That is just topic clustering. You must pair based on **logical structure** (e.g., logic of deception, logic of paradox) to achieve reasoning transfer.

---

## Applicability Envelope

**Works well when:**

- you have a "weaker" or smaller model that requires high-information-density signals to learn logic
- the dataset contains mixed-length formats with distinct genre profiles
- you need to balance "creativity" (jokes) with "precision" (prose)

**Fails or degrades when:**

- the model has a very small context window (< 2k tokens) -> Conditional Stratification is less useful than standard truncation
- the "reasoning" in the data is purely factual and not structural (e.g., simple Q&A)
- you are training a massive model (70B+) that can naturally absorb the variance without forced binning

## Auto-Binning Trigger

If the dataset size exceeds 1 million records:

1.  Sample a random 10,000-record subset *per class*.
2.  Estimate the conditional token distribution (mean/variance) for each class.
3.  Pre-compute the `sampling_weights.json` and `length_filters.json`.
4.  Store the map so the training loop can reference it without re-sorting the full million-record dataset.
