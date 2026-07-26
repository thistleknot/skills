---
name: stat-partitioning
status: active
last_validated: 2026-07-26
description: >
  Derive principled numeric boundaries on a measurable space instead of picking
  magic constants. Use when setting a threshold, cutoff, outlier band, chunk
  boundary, or exclusion rule and the value would otherwise be guessed. Covers
  median/MAD robust scale, log and Box-Cox transforms with back-transform, ECDF
  thresholds, and the decision-class-first rule. Trigger on "what threshold",
  "where do I cut", "flag outliers", "bin this", skewed or heavy-tailed data, or
  any hardcoded numeric constant in a filter.
---

# Statistical partitioning

Use this when the space is measurable and you need defensible boundaries for
chunking, review, filtering, or refactoring. The failure this prevents is the
magic constant: a threshold that works on the sample it was tuned against and
silently misbehaves everywhere else.

## Protocol

1. **Measure a feature that may reveal structure.** If the feature has no
   relationship to the decision, no amount of statistics rescues the cutoff.

2. **Choose a center that matches the distribution.** Prefer the median for
   skewed, heavy-tailed, or noisy data. The mean is only defensible on data that
   is roughly symmetric and outlier-free — verify, do not assume.

3. **Estimate spread with a robust statistic.** Prefer MAD (median absolute
   deviation) when outliers would distort the standard deviation.

4. **Use the median as the first partition.** It is the cheapest cut that carries
   real information, and it is the baseline every fancier boundary must beat.

5. **Derive candidate boundaries from center and spread.**
   - Under roughly normal assumptions, `sigma_hat = 1.4826 * MAD` gives a
     sigma-like scale; bands follow as `median +/- k * sigma_hat`.
   - Under strong skew, transform first (log, Box-Cox, Yeo-Johnson when the data
     contains zeros or negatives), estimate boundaries in the transformed space,
     then **back-transform the boundary** — never report a transformed-space
     threshold as if it were a raw-space one.
   - When the distributional form is untrustworthy, use ECDF quantiles directly.
     They assume nothing and are exact on the observed sample.

6. **Define the decision class before choosing the cutoff.** Typical range,
   anomaly band, chunk boundary, and hard exclusion are four different questions
   and take four different cutoffs. Picking the number before naming the decision
   is how a threshold ends up serving none of them.

7. **Validate against the actual task.** Keep the partition only if it improves
   structure, chunking, recall, or recovery on a real measurement. A boundary that
   is statistically tidy and task-neutral is not an improvement.

## Where this does not apply

Do not force the method where the shape disagrees. Multimodal structure wants
clustering; latent structure wants factor analysis; genuinely categorical
structure wants explicit grouping. A median cut across two well-separated modes
lands in the empty valley between them and partitions nothing.

## Contract

- **Require** — a measurable feature, and a named decision class.
- **Guarantee** — every boundary traces to a center, a spread estimator, and a
  stated distributional assumption.
- **Maintain** — boundaries derived in transformed space are reported in raw
  space.
- **Assert** — no hardcoded numeric constant survives without a derivation or an
  explicit note that it was chosen arbitrarily.

## Related

`median-bifurcation` for the median-cut-as-contrastive-signal pattern.
`bm25-corpus-sampling` and `stratified-quota-sampling` apply this machinery to
corpus composition. `reasoning` (top-down mode) for when the space is not yet
measurable.
