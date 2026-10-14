# Reproduction Workflow

Run commands from the repository root with the pinned virtual environment. Every output directory must be new or empty.

## Verify

```sh
.venv/bin/python -m mcf.workflows.launcher -m unittest discover -s tests -v
```

## Current Bankruptcy/Payment-Failure Pipeline

Use the [bankruptcy/payment-failure workflow](bankruptcy_payment_failure_workflow.md)
for the current recurrent 60-day target. Item 1.03 qualifies automatically;
2.04 requires reviewed payment-failure evidence. The primary model experiment's completed inventory,
panel and fitted models are under `results/run_006_full_statement_enrichment/`.
The historical commands below document the earlier Item 1.03-only study.

## Historical Empirical Pipeline

The commands below document the earlier Item 1.03-only study. The current
trainer requires an Item 2.04 disclosure target and attached audited statement
facts; use the current pipeline above for new model runs.

```sh
.venv/bin/python -m mcf.data.empirical inventory \
  --dataset dataset \
  --cutoff 2026-09-07 \
  --output-dir results/new_run/inventory

.venv/bin/python -m mcf.data.empirical panel \
  --dataset dataset \
  --inventory results/new_run/inventory \
  --config configs/study.sec_disclosure.json \
  --output-dir results/new_run/panel

.venv/bin/python -m mcf.workflows.launcher -m mcf.models.train \
  --config configs/study.sec_disclosure.json \
  --panel results/new_run/panel/panel.csv \
  --output-dir results/new_run/models

.venv/bin/python -m mcf.workflows.launcher -m mcf.policy.empirical \
  --models results/new_run/models/models.joblib \
  --features results/new_run/panel/features.csv \
  --policy configs/policy.sec_disclosure.json \
  --output-dir results/new_run/policy
```

The inventory identifies eligible issuers and first Item 1.03 disclosures. The panel stage reconstructs information available at each decision date. Model training applies chronological purging, expanding-window tuning, 2019 mapping calibration, 2020–2022 model selection and 2023–2025 held-out evaluation. Policy replay consumes the selected model's continuous disclosure probability.

## Reports

```sh
.venv/bin/python -m mcf.workflows.launcher -m mcf.reporting.empirical data \
  --input results/new_run/panel/panel.csv \
  --output-dir results/new_run/descriptive

.venv/bin/python -m mcf.workflows.launcher -m mcf.reporting.empirical models \
  --input results/new_run/models \
  --output-dir results/new_run/model_report

.venv/bin/python -m mcf.workflows.launcher -m mcf.reporting.empirical policy \
  --input results/new_run/policy \
  --output-dir results/new_run/policy_report

.venv/bin/python -m mcf.policy.examples \
  --output-dir results/new_run/worked_examples
```

## Primary Model Experiment Policy and Reports

The primary model experiment's panel and models are frozen. From a checkout containing their local
generated files, create the policy replay and report directories with these
commands (each destination must be new or empty):

```sh
.venv/bin/python -m mcf.workflows.launcher -m mcf.policy.empirical \
  --models results/run_006_full_statement_enrichment/models/models.joblib \
  --features results/run_006_full_statement_enrichment/panel/features.csv \
  --policy configs/policy.sec_disclosure.json \
  --output-dir results/run_006_full_statement_enrichment/policy

.venv/bin/python -m mcf.workflows.launcher -m mcf.reporting.empirical data \
  --input results/run_006_full_statement_enrichment/panel/panel.csv \
  --output-dir results/run_006_full_statement_enrichment/descriptive

.venv/bin/python -m mcf.workflows.launcher -m mcf.reporting.empirical models \
  --input results/run_006_full_statement_enrichment/models \
  --output-dir results/run_006_full_statement_enrichment/model_report

.venv/bin/python -m mcf.workflows.launcher -m mcf.reporting.empirical policy \
  --input results/run_006_full_statement_enrichment/policy \
  --output-dir results/run_006_full_statement_enrichment/policy_report
```

## Refresh Current Thesis Evidence

```sh
.venv/bin/python -m mcf.reporting.thesis_evidence \
  --docs docs/thesis \
  --inventory results/run_006_full_statement_enrichment/inventory \
  --panel results/run_006_full_statement_enrichment/panel \
  --models results/run_006_full_statement_enrichment/models \
  --descriptive results/run_006_full_statement_enrichment/descriptive \
  --model-report results/run_006_full_statement_enrichment/model_report \
  --policy results/run_006_full_statement_enrichment/policy \
  --policy-report results/run_006_full_statement_enrichment/policy_report \
  --examples results/history/item_103_model_evolution/03_rolling_temporal_validation_random_forest/worked_examples
```

This refreshes the evidence tables, figures and Appendices C/D under `docs/thesis/`. It does not update Google Docs.

## Experimental composite disclosure proxy

The following independent workflow classifies Item 2.04 filings with rules and an
LLM fallback, combines qualified records with Item 1.03, constructs a new panel,
and trains the model families:

```sh
SEC_USER_AGENT='Your Name your.email@example.com' \
.venv/bin/python -m mcf.workflows.launcher -m mcf.workflows.payment_default_proxy \
  --dataset ../dataset \
  --statement-facts results/statement_recovery_full/companies \
  --output-dir results/payment_default_proxy
```

It uses `configs/study.payment_default_proxy.json`. Unresolved Item 2.04 filings
censor affected windows. The target is a disclosure proxy and is not verified
contractual payment default.
