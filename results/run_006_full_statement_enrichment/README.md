# Full statement enrichment run

Recurrent Item 1.03 or reviewed Item 2.04 payment-failure target with full financial statement enrichment and a paired model fit without statement features.

Selected model: `random_forest`. The full setup is in `models/design.json`; `models/selection.json`, `models/metrics.csv`, and `models/bootstrap_intervals.json` contain selection and evaluation results. Predictions and fitted models are in `models/`.

See `statement_enrichment_comparison.json`, `paired_test_comparison.json`, and `comparison_to_run_005.json`; `models_without_statements/` holds the paired fit.

The extracted statement facts for this run are stored with the source snapshot at `../dataset_full/statement_facts/` (relative to the repository root), outside Git.

`inventory/` and `panel/` (including `panel_without_statements/` where present) are local generated data and are excluded from Git. Stored manifests and workflow summaries retain the original run paths as historical provenance; after the folder rename, those paths may no longer resolve.
