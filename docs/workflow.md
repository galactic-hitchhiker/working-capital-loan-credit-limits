# Reproduction Workflow

Run commands from the repository root with the pinned virtual environment. Every output directory must be new or empty.

## Verify

```sh
.venv/bin/python run_research.py -m unittest discover -s tests -v
```

## Full Empirical Pipeline

```sh
.venv/bin/python empirical_sec.py inventory \
  --dataset dataset \
  --cutoff 2026-09-07 \
  --output-dir results/new_run/inventory

.venv/bin/python empirical_sec.py panel \
  --dataset dataset \
  --inventory results/new_run/inventory \
  --config configs/study.sec_disclosure.json \
  --output-dir results/new_run/panel

.venv/bin/python run_research.py train_models.py \
  --config configs/study.sec_disclosure.json \
  --panel results/new_run/panel/panel.csv \
  --output-dir results/new_run/models

.venv/bin/python run_research.py empirical_policy.py \
  --models results/new_run/models/models.joblib \
  --features results/new_run/panel/features.csv \
  --policy configs/policy.sec_disclosure.json \
  --output-dir results/new_run/policy
```

The inventory identifies eligible issuers and first Item 1.03 disclosures. The panel stage reconstructs information available at each decision date. Model training applies chronological purging, expanding-window tuning, 2019 mapping calibration, 2020–2022 model selection and 2023–2025 held-out evaluation. Policy replay consumes the selected model's continuous disclosure probability.

## Reports

```sh
.venv/bin/python run_research.py empirical_report.py data \
  --input results/new_run/panel/panel.csv \
  --output-dir results/new_run/descriptive

.venv/bin/python run_research.py empirical_report.py models \
  --input results/new_run/models \
  --output-dir results/new_run/model_report

.venv/bin/python run_research.py empirical_report.py policy \
  --input results/new_run/policy \
  --output-dir results/new_run/policy_report

.venv/bin/python policy_examples.py \
  --output-dir results/new_run/worked_examples
```

## Refresh Current Thesis Evidence

```sh
.venv/bin/python export_thesis_evidence.py \
  --docs docs \
  --inventory results/full_run/inventory \
  --panel results/full_run_1/panel \
  --models results/full_run_2/models \
  --descriptive results/full_run_2/descriptive \
  --model-report results/full_run_2/model_report \
  --policy results/full_run_2/policy \
  --policy-report results/full_run_2/policy_report \
  --examples results/full_run_2/worked_examples
```

This refreshes local evidence tables, figures and Appendices C/D. It does not update Google Docs.

