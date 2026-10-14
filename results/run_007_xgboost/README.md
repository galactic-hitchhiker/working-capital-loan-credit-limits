# Expanded XGBoost search

Prepared run configuration; no empirical training results yet. Uses the run 007
experimental target, features and chronological stages. Trains XGBoost plus the
constant benchmark, with 64 candidates: the eight legacy candidates and 28 seeded
parameter samples evaluated with both unweighted and balanced class weights.

The wider search varies depth, learning rate, number of trees, minimum child
weight, row/column sampling, L1/L2 regularization and minimum split loss. Parameter
semantics follow the [XGBoost documentation](https://xgboost.readthedocs.io/en/release_3.0.0/parameter.html).
`xgboost_candidates` in `design.json` accepts even integers >= 8; `seed` fixes the
sample. Designs without these optional settings retain their original search.

Ranking remains mean annual tuning AP lift, with Brier skill as the tie breaker.
Calibration and selection retain their separate periods, and test rows do not
enter hyperparameter selection. This design has only one tuning year (2018);
the expanded search can overfit that year and does not guarantee improvement.
Previously examined evaluation periods remain retrospective evidence.

Run from the repository root with Python 3.11 and the pinned dependencies:

```sh
python3.11 -m venv .venv
.venv/bin/python -m pip install -r requirements.txt
```

If the run 007 panel already exists locally, reuse it in place:

```sh
bash results/run_007_xgboost/run.sh results/run_007_experimental/panel/panel.csv
```

Otherwise, with the source dataset and imported statement facts available:

```sh
.venv/bin/python -m mcf.workflows.pipeline panel \
  --dataset ../dataset_full \
  --config results/run_007_xgboost/design.json \
  --item-204-results results/item_204_openai_batch_review/classifications.jsonl \
  --statement-facts ../dataset_full/statement_facts/companies \
  --output-dir results/run_007_xgboost
bash results/run_007_xgboost/run.sh
```

Adjust the dataset/statement paths if stored elsewhere. Reusing a panel requires
its adjacent audit, manifest and statement-facts hash list; do not copy only the CSV.
Model outputs go to `models/`, and console output goes to `train.log`. An existing
nonempty `models/` directory is rejected to preserve research outputs.
