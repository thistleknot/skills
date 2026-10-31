---
name: orange
description: "Use Orange Data Mining for visual, traceable data science workflows: EDA, preparation, modeling, clustering, dimensionality reduction, and evaluation. Prefer its installed widgets over handwritten analysis code when they meet the objective."
---

# Orange Data Mining

Use Orange when a visual, editable workflow can answer the data science question. Prefer installed widgets over handwritten code. Do not force Orange onto deployment services, workloads it cannot handle, or a capability it lacks; use a minimal, visibly labelled Python Script bridge only when necessary, documenting its inputs, outputs, and reason.

## Establish the question

Before connecting learners, inspect the input in [File/CSV File Import, Data Table, and Data Info](https://orangedatamining.com/widget-catalog/): schema, target, identifier fields, missing values, duplicates, and row count. State the question, baseline, metric, split policy, and a bounded test budget. Use only the widgets needed for that question; add-ons are conditional on their installed version and core widgets are the default.

## Build the appropriate visual flow

- Predictive work: connect data and one or more learners to `Test and Score`; use `Select Columns` to exclude identifiers and set roles. Send the `Preprocessor` output, not globally transformed data, to `Test and Score`, then use `Confusion Matrix` and `ROC Analysis` for classification or suitable regression measures. [Orange's preprocessing guidance](https://orangedatamining.com/widget-catalog/transform/preprocess/) specifies that fitting learned transforms outside cross-validation can leak test-fold information; configure feature selection inside `Preprocess`, never with a globally fitted `Rank`, and connect imputation, scaling, feature selection, and rank-like learned steps through the evaluation path.
- Respect the data-generating order. For time or grouped data, use a time/group-aware or fixed train/test split rather than random cross-validation. Use [Test and Score](https://orangedatamining.com/widget-catalog/evaluate/testandscore/) cross-validation only when the split assumptions fit the question.
- Unsupervised work: inspect and preprocess, then use suitable tools such as `PCA` or `k-Means`, `Scatter Plot`, and `Silhouette Plot`. Do not report classification scores when there is no target.

## Preserve a runnable trace

Save the editable `.ows` workflow as the primary artifact. An `.ows` stores widget settings and connections, not the data, so include the data or stable access instructions, preferably with relative paths. Record Orange and add-on versions, widget settings, split and seed, baseline, comparison, metric, and a node-edge inventory plus a canvas image or report. This makes the visual workflow auditable; [Orange documents the data-sharing requirement](https://orangedatamining.com/blog/orange-essentials-saving-and-sharing-workflows/).

If the Orange UI is available, reopen the saved workflow and run it on at least three varied small inputs before claiming execution validation. Check intermediate outputs, connections, row counts, variable types and targets, and leakage. Keep each validation run below 15 minutes. If the UI is unavailable, distinguish an authored workflow from an executed one: XML, screenshots, or API-only output do not demonstrate that the GUI workflow ran. Inspect installed widget names and channel types before generating an `.ows`; start from an installed template or tool-generated workflow instead of inventing serialized properties.

## Document it

Use [the Sphinx skill](../sphinx/SKILL.md) when the workflow needs a durable architecture or functional page. Preserve evidence for each connection and label observed outputs separately from proposed changes.
