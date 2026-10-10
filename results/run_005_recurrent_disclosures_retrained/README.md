# Recurrent disclosure retraining

The same recurrent 60-day Item 1.03 or reviewed Item 2.04 payment-failure target and panel population as run 004, with a new model fit.

Selected model: `xgboost`. The full setup is in `models/design.json`; `models/selection.json`, `models/metrics.csv`, and `models/bootstrap_intervals.json` contain selection and evaluation results. Predictions and fitted models are in `models/`.

This is the reference run for the assets and statement coverage investigations.

`inventory/` and `panel/` (including `panel_without_statements/` where present) are local generated data and are excluded from Git. Stored manifests and workflow summaries retain the original run paths as historical provenance; after the folder rename, those paths may no longer resolve.
