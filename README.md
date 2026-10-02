# Master thesis: dynamic short-term corporate credit limits

This repository contains the empirical study and thesis draft for **Dynamic Determination of Short-Term Corporate Credit Limits Using Machine Learning**. Start with the [thesis index](docs/README.md), use the [workflow](docs/workflow.md) to reproduce the study, and consult the [input contracts](docs/input_contracts.md) for required data fields.

## Current Empirical Result

The study uses local SEC company-facts and submissions data. It contains 588,111 labeled company-month observations from 9,075 issuers and predicts the first recorded Form 8-K or 8-K/A Item 1.03 bankruptcy or receivership disclosure within the next 60 days. This outcome is not payment default.

The models use 12 point-in-time predictors covering liquidity, cash, leverage, growth, working capital, profitability, operating cash flow and company size. Chronological development uses:

| Stage | Period | Purpose |
|---|---|---|
| Training | 2011–2016 | Estimate preprocessing and model parameters |
| Tuning | 2017–2018 | Select hyperparameters with expanding temporal folds |
| Calibration | 2019 | Fit probability mappings before COVID-19 |
| Selection and robustness | 2020–2022 | Select mapping, model and threshold across regimes |
| Held-out evaluation | 2023–2025 | Evaluate frozen choices |

Random forest with its raw identity mapping is selected. Sigmoid calibration is rejected for the forest because it worsens selection Brier error.

| Held-out metric | Selected random forest |
|---|---:|
| ROC-AUC | 0.9089 |
| Average precision | 0.027475 |
| Brier score | 0.0020872 |
| Precision at frozen threshold | 3.97% |
| Recall at frozen threshold | 12.85% |

Average precision is 12.99 times the held-out event share. The probability estimates an Item 1.03 filing event. It must not be interpreted as a payment-default probability.

The 2023–2025 labels are excluded from every development step in the reported run. Those years were examined during earlier project iterations, so the thesis describes the result as held-out evaluation rather than a completely untouched external validation.

## Policy Result

The base historical simulation uses the selected forest's continuous probability. It covers 99,674 company-months from 3,872 companies. The median assigned limit is USD 3.79 million, the mean is 0.653% of assets, and 5.69% of observations receive a zero limit.

The policy results are hypothetical. The SEC data do not observe actual facility limits, utilization, repayments, contractual defaults, recoveries, losses, pricing or profitability. Capacity rules, cash eligibility, additional debt, exposure and caps are explicit scenario assumptions.

## Main Files

| File | Purpose |
|---|---|
| `empirical_sec.py` | Build issuer inventory, disclosure labels and monthly panel |
| `sec_data.py`, `sec_point_in_time.py` | Extract point-in-time financial facts and ratios |
| `configs/study.sec_disclosure.json` | Define target, stages, controls and 12 predictors |
| `risk_models.py`, `train_models.py` | Tune, calibrate, select and evaluate four model families |
| `model_evaluation.py`, `temporal_validation.py` | Metrics, thresholds, bootstrap and chronological purging |
| `credit_policy.py`, `empirical_policy.py` | Calculate and replay hypothetical limits |
| `empirical_report.py` | Produce descriptive, model and policy reports |
| `export_thesis_evidence.py` | Refresh thesis evidence tables and Appendices C/D |
| `tests/` | Verify extraction, chronology, modeling and policy behavior |

Current result roots are:

- `results/full_run/inventory/` — issuer inventory and disclosure events;
- `results/full_run_1/panel/` — improved panel and feature provenance;
- `results/full_run_2/models/` — selected models and evaluation;
- `results/full_run_2/policy/` — policy decisions and sensitivity;
- `results/full_run_2/descriptive/`, `model_report/`, `policy_report/` and `worked_examples/` — regenerated reporting material.

## Verify the Code

The recorded environment uses Python 3.13.15 and packages pinned in `requirements-lock.txt`.

```sh
.venv/bin/python run_research.py -m unittest discover -s tests -v
```

## Rebuild from Scratch

Each output directory must be new or empty.

### 1. Build the issuer inventory

```sh
.venv/bin/python empirical_sec.py inventory \
  --dataset dataset \
  --cutoff 2026-09-07 \
  --output-dir results/new_run/inventory
```

This scans company-facts and submission histories, applies issuer eligibility rules, locates first Item 1.03 disclosures and records source hashes.

### 2. Build the point-in-time panel

```sh
.venv/bin/python empirical_sec.py panel \
  --dataset dataset \
  --inventory results/new_run/inventory \
  --config configs/study.sec_disclosure.json \
  --output-dir results/new_run/panel
```

This selects only facts filed by each monthly decision date, constructs the 12 predictors and creates a 60-day label only when follow-up is observable. Review `panel_audit.json`, `features.csv` and `feature_provenance.jsonl`.

### 3. Train and evaluate models

```sh
.venv/bin/python run_research.py train_models.py \
  --config configs/study.sec_disclosure.json \
  --panel results/new_run/panel/panel.csv \
  --output-dir results/new_run/models
```

This runs expanding temporal tuning, refits family winners, fits 2019 probability mappings, selects the final model and threshold in 2020–2022, and evaluates frozen choices in 2023–2025. No winsorization is currently applied. Begin review with `selection.json`, `stage_audit.json`, `tuning_fold_scores.csv`, `metrics.csv` and `bootstrap_intervals.json`.

### 4. Replay the policy

```sh
.venv/bin/python run_research.py empirical_policy.py \
  --models results/new_run/models/models.joblib \
  --features results/new_run/panel/features.csv \
  --policy configs/policy.sec_disclosure.json \
  --output-dir results/new_run/policy
```

This applies the selected probability, financial capacity, exposure cap, hard stops and monthly update rules. Review `policy_audit.json`, `limit_paths.csv` and `policy_sensitivity.csv`.

### 5. Generate reports

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

To refresh the thesis evidence from the current completed run:

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

The exporter copies compact evidence tables and regenerates Appendices C and D. It does not edit Google Docs.
