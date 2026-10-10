# Item 1.03 baseline

First recorded Item 1.03 bankruptcy or receivership disclosure within 60 days. This run uses the original first-event target, 2011–2025 monthly decisions, and SEC data observed through 2026-09-07.

Selected model: `random_forest`. The full setup is in `models/design.json`; `models/selection.json`, `models/metrics.csv`, and `models/bootstrap_intervals.json` contain selection and evaluation results. Predictions and fitted models are in `models/`.

The baseline for the later Item 1.03 plus Item 2.04 comparison.

`inventory/` and `panel/` (including `panel_without_statements/` where present) are local generated data and are excluded from Git. Stored manifests and workflow summaries retain the original run paths as historical provenance; after the folder rename, those paths may no longer resolve.
