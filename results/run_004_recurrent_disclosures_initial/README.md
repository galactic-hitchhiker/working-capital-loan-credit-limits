# Initial recurrent disclosure model

New Item 1.03 bankruptcy or receivership and reviewed Item 2.04 payment-failure episodes within 60 days. Disclosures within 90 days form one episode; later episodes can reenter the sample.

Selected model: `xgboost`. The full setup is in `models/design.json`; `models/selection.json`, `models/metrics.csv`, and `models/bootstrap_intervals.json` contain selection and evaluation results. Predictions and fitted models are in `models/`.

This broader target was specified after earlier target results were examined, so its 2023–2025 evaluation is retrospective.

`inventory/` and `panel/` (including `panel_without_statements/` where present) are local generated data and are excluded from Git. Stored manifests and workflow summaries retain the original run paths as historical provenance; after the folder rename, those paths may no longer resolve.
