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

## Source Structure

All application Python modules live under the `mcf/` package. Tests remain in
`tests/`, and generated artifacts remain in `results/`.

| Package | Purpose |
|---|---|
| `mcf/data/` | SEC ingestion, point-in-time facts, disclosure labels and panel construction |
| `configs/study.sec_disclosure.json` | Define target, stages, controls and 12 predictors |
| `mcf/models/` | Model definitions, temporal validation, training, evaluation and prediction |
| `mcf/policy/` | Credit-limit rules, replay, examples and sensitivity analysis |
| `mcf/reporting/` | Empirical reports, figures and thesis evidence exports |
| `mcf/workflows/` | End-to-end demo and environment-aware command launcher |
| `mcf/enrichment/item204/` | Item 2.04 rule and LLM enrichment workflow |
| `mcf/common.py` | Shared configuration, file and serialization helpers |
| `tests/` | Verify extraction, chronology, modeling and policy behavior |

The completed thesis run is preserved in the results history:

- `results/history/item_103_model_evolution/01_initial_full_pipeline_xgboost/inventory/` — issuer inventory and disclosure events;
- `results/history/item_103_model_evolution/02_improved_sec_fact_coverage_xgboost/panel/` — improved panel and feature provenance;
- `results/history/item_103_model_evolution/03_rolling_temporal_validation_random_forest/` — selected models, reports, policy decisions and worked examples.

See `results/history/README.md` and `results/history/index.json` for the complete
model and Item 2.04 enrichment evolution.

## Verify the Code

The recorded environment uses Python 3.13.15 and packages pinned in `requirements-lock.txt`.

```sh
.venv/bin/python -m mcf.workflows.launcher -m unittest discover -s tests -v
```

## Rebuild from Scratch

Each output directory must be new or empty.

### 1. Build the issuer inventory

```sh
.venv/bin/python -m mcf.data.empirical inventory \
  --dataset dataset \
  --cutoff 2026-09-07 \
  --output-dir results/new_run/inventory
```

This scans company-facts and submission histories, applies issuer eligibility rules, locates first Item 1.03 disclosures and records source hashes.

### 2. Build the point-in-time panel

```sh
.venv/bin/python -m mcf.data.empirical panel \
  --dataset dataset \
  --inventory results/new_run/inventory \
  --config configs/study.sec_disclosure.json \
  --output-dir results/new_run/panel
```

This selects only facts filed by each monthly decision date, constructs the 12 predictors and creates a 60-day label only when follow-up is observable. Review `panel_audit.json`, `features.csv` and `feature_provenance.jsonl`.

### 3. Train and evaluate models

```sh
.venv/bin/python -m mcf.workflows.launcher -m mcf.models.train \
  --config configs/study.sec_disclosure.json \
  --panel results/new_run/panel/panel.csv \
  --output-dir results/new_run/models
```

This runs expanding temporal tuning, refits family winners, fits 2019 probability mappings, selects the final model and threshold in 2020–2022, and evaluates frozen choices in 2023–2025. No winsorization is currently applied. Begin review with `selection.json`, `stage_audit.json`, `tuning_fold_scores.csv`, `metrics.csv` and `bootstrap_intervals.json`.

### 4. Replay the policy

```sh
.venv/bin/python -m mcf.workflows.launcher -m mcf.policy.empirical \
  --models results/new_run/models/models.joblib \
  --features results/new_run/panel/features.csv \
  --policy configs/policy.sec_disclosure.json \
  --output-dir results/new_run/policy
```

This applies the selected probability, financial capacity, exposure cap, hard stops and monthly update rules. Review `policy_audit.json`, `limit_paths.csv` and `policy_sensitivity.csv`.

### 5. Generate reports

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

To refresh the thesis evidence from the current completed run:

```sh
.venv/bin/python -m mcf.reporting.thesis_evidence \
  --docs docs \
  --inventory results/history/item_103_model_evolution/01_initial_full_pipeline_xgboost/inventory \
  --panel results/history/item_103_model_evolution/02_improved_sec_fact_coverage_xgboost/panel \
  --models results/history/item_103_model_evolution/03_rolling_temporal_validation_random_forest/models \
  --descriptive results/history/item_103_model_evolution/03_rolling_temporal_validation_random_forest/descriptive \
  --model-report results/history/item_103_model_evolution/03_rolling_temporal_validation_random_forest/model_report \
  --policy results/history/item_103_model_evolution/03_rolling_temporal_validation_random_forest/policy \
  --policy-report results/history/item_103_model_evolution/03_rolling_temporal_validation_random_forest/policy_report \
  --examples results/history/item_103_model_evolution/03_rolling_temporal_validation_random_forest/worked_examples
```

The exporter copies compact evidence tables and regenerates Appendices C and D. It does not edit Google Docs.

## Composite Item 1.03 + Item 2.04 Model

The repository also supports a separate experimental target named
`first_sec_payment_default_disclosure_proxy`. It combines every Item 1.03 filing
with Item 2.04 filings classified as `QUALIFIED_DEFAULT`. Deterministic rules run
first; only `MANUAL_REVIEW` cases are sent to the configured LLM. Remaining
unresolved Item 2.04 cases censor affected label windows instead of becoming
negative observations.

Run enrichment, combined inventory construction, panel construction and model
training with one command:

```sh
SEC_USER_AGENT='Your Name your.email@example.com' \
.venv/bin/python -m mcf.workflows.launcher -m mcf.workflows.payment_default_proxy \
  --dataset ../dataset \
  --output-dir results/payment_default_proxy
```

This defaults to local Ollama with `gemma3:12b`. Pull the model once before the
first run:

```sh
ollama pull gemma3:12b
```

Use `--model MODEL_NAME` to select another installed Ollama model. Review cache
keys include the model name, so existing decisions produced by another model are
preserved and `gemma3:12b` creates its own cached decisions.

### Run Item 2.04 enrichment separately

The enrichment workflow downloads or reuses filing HTML, applies the deterministic
rules, and sends only `MANUAL_REVIEW` cases to Ollama. It also defaults to
`gemma3:12b`:

```sh
SEC_USER_AGENT='Your Name your.email@example.com' \
.venv/bin/python -m mcf.enrichment.item204.workflow \
  --submissions ../dataset/submissions \
  --output-dir results/item_204_pipeline
```

Final classifications are written to
`results/item_204_pipeline/final/classifications.jsonl`. Reruns reuse downloaded
HTML and successful model decisions. After correcting a provider problem, retry
only stored fallback decisions with:

```sh
.venv/bin/python -m mcf.enrichment.item204.workflow \
  --submissions ../dataset/submissions \
  --output-dir results/item_204_pipeline \
  --retry-fallbacks
```

Use the completed enrichment in the remaining end-to-end workflow with:

```sh
.venv/bin/python -m mcf.workflows.launcher -m mcf.workflows.payment_default_proxy \
  --dataset ../dataset \
  --item-204-results results/item_204_pipeline/final \
  --output-dir results/payment_default_proxy
```

This skips discovery, rule classification and LLM review, then builds the combined
inventory, panel and models.

### Run every stage separately

Build the combined Item 1.03 + qualified Item 2.04 inventory:

```sh
.venv/bin/python -m mcf.data.empirical inventory \
  --dataset ../dataset \
  --cutoff 2026-09-07 \
  --item-204-results results/item_204_pipeline/final \
  --output-dir results/payment_default_proxy/inventory
```

Build the point-in-time panel:

```sh
.venv/bin/python -m mcf.data.empirical panel \
  --dataset ../dataset \
  --inventory results/payment_default_proxy/inventory \
  --config configs/study.payment_default_proxy.json \
  --output-dir results/payment_default_proxy/panel
```

Train and evaluate the model families:

```sh
.venv/bin/python -m mcf.workflows.launcher -m mcf.models.train \
  --config configs/study.payment_default_proxy.json \
  --panel results/payment_default_proxy/panel/panel.csv \
  --output-dir results/payment_default_proxy/models
```

Inventory, panel and model output directories must be new or empty. The Item 2.04
directory is resumable because downloaded HTML and individual review decisions are
cached.

### Run the two Item 2.04 stages separately

Run deterministic discovery, download and classification:

```sh
SEC_USER_AGENT='Your Name your.email@example.com' \
.venv/bin/python -m mcf.enrichment.item204.classify \
  --submissions ../dataset/submissions \
  --output-dir results/item_204_pipeline/rules \
  --cutoff 2026-09-07
```

Then review only the remaining manual cases with Ollama:

```sh
.venv/bin/python -m mcf.enrichment.item204.reviewers.ollama \
  --input results/item_204_pipeline/rules/classifications.jsonl \
  --html-dir results/item_204_pipeline/rules/html \
  --output-dir results/item_204_pipeline/final
```

The study design is in `configs/study.payment_default_proxy.json`. The resulting
probability concerns the composite SEC disclosure proxy. Item 1.03 includes
bankruptcy or receivership disclosures, while Item 2.04 includes several kinds of
triggering events; the output must not be described as a verified contractual
payment-default probability.
