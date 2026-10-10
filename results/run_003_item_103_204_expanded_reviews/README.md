# Expanded Item 2.04 review proxy

Same first-event Item 1.03 plus qualified Item 2.04 target as run 002, rebuilt after additional Item 2.04 reviews. The inventory reports 858 qualified defaults versus 770 in run 002.

Selected model: `xgboost`. The full setup is in `models/design.json`; `models/selection.json`, `models/metrics.csv`, and `models/bootstrap_intervals.json` contain selection and evaluation results. Predictions and fitted models are in `models/`.

The label definition is unchanged; the review coverage and resulting sample differ.

`inventory/` and `panel/` (including `panel_without_statements/` where present) are local generated data and are excluded from Git. Stored manifests and workflow summaries retain the original run paths as historical provenance; after the folder rename, those paths may no longer resolve.
