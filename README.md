# Master thesis: dynamic short-term corporate credit limits

This repository contains the empirical study and thesis draft for **Dynamic Determination of Short-Term Corporate Credit Limits Using Machine Learning**. Start with the [thesis index](docs/README.md), use the [workflow](docs/workflow.md) to reproduce the study, and consult the [input contracts](docs/input_contracts.md) for required data fields.

## Current Prediction Target

The default workflow predicts **disclosed bankruptcy/receivership or payment
failure within 60 days**. Every Item 1.03 filing qualifies automatically. Item
2.04-only filings qualify only with `QUALIFIED_DEFAULT / PAYMENT_FAILURE` and
source-backed evidence; acceleration/enforcement alone remain unresolved.

Both sources are outcome events for training. All qualifying filings are saved;
reports within a rolling 90-day gap form one episode, and later episodes can
contribute further outcomes for the same company. The quiet gap is an operational
rule, not verified cure. The outcome is a broader disclosure proxy, not a verified
contractual payment-default probability.

Run the study with the [staged pipeline](docs/pipeline.md): `download`,
`inventory`, `classify`, `panel`, and `train` can run separately, or `all` can
coordinate them. Existing feature, label, and model functions remain in use.

Use `configs/study.bankruptcy_or_payment_failure.json` and the
[combined-target guide](docs/bankruptcy_payment_failure_workflow.md). Your earlier
2.04 reviews can be reused without new OpenAI calls; 1.03 needs no AI review.
The narrower payment-only configs remain available for comparison. Existing
results below describe the historical target and have not been retrained here.

## Historical Empirical Result

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

| Path | Purpose |
|---|---|
| `mcf/data/` | SEC ingestion, point-in-time facts, disclosure labels and panel construction |
| `configs/` | Current payment-failure design, historical study designs and policy parameters |
| `mcf/models/` | Model definitions, temporal validation, training, evaluation and prediction |
| `mcf/policy/` | Credit-limit rules, replay, examples and sensitivity analysis |
| `mcf/reporting/` | Empirical reports, figures and thesis evidence exports |
| `mcf/workflows/` | Payment-failure training workflow, synthetic demo and command launcher |
| `mcf/enrichment/item204/` | SEC Item 1.03/2.04 discovery/download and OpenAI Batch evidence review |
| `mcf/common.py` | Shared configuration, file and serialization helpers |
| `tests/` | Verify extraction, chronology, modeling and policy behavior |
| `docs/` | Thesis chapters, input contracts and workflow/parameter guides |
| `results/` | Local source caches, generated runs and preserved research history |

The Item 2.04 implementation has two stages:

```text
mcf/enrichment/item204/
├── discover.py                 # Inventory filings and download/cache SEC HTML
├── workflow.py                 # Run discovery, then submit/collect Batch reviews
└── reviewers/
    ├── common.py               # Source text, output schema, validation and review cache
    └── openai_batch.py         # Submit, resume and collect OpenAI Batch jobs
```

OpenAI Batch is the only AI provider. Discovery assigns no event labels; the
reviewer processes every filing with available source text, reusing completed
OpenAI reviews. Missing text is recorded as unresolved in the final exports.
The previous `classify.py`, synchronous OpenAI and Ollama entry points have been
removed. Historical artifacts remain available under `results/history/`.

Runnable Python files begin with their purpose, run command and parameter list,
including defaults and required inputs. Run modules from the repository root
using `.venv/bin/python -m ...`. For command-line help:

```sh
.venv/bin/python -m mcf.enrichment.item204.workflow --help
.venv/bin/python -m mcf.enrichment.item204.reviewers.openai_batch --help
.venv/bin/python -m mcf.workflows.payment_default_proxy --help
```

## Download SEC source data

The standalone downloader fetches and unpacks Company Facts, submissions, both
Financial Statement and Notes archives and the separate face-financial series. It discovers the available statement
periods, resumes interrupted downloads, and retains ZIPs for feature extraction.

```sh
export SEC_USER_AGENT="Your Name your-email@example.com"
python3 scripts/download_sec_dataset.py \
  --output-dir ../dataset_full --start-year 2009 --end-year 2026
```

Use a fresh directory to preserve existing research snapshots. Add `--dry-run`
to preview the download plan. See [download instructions](docs/sec_dataset_download.md)
for the output layout, selective downloads and feature-import commands.

## Results Structure

The current local layout separates cached SEC sources, model runs and history:

```text
results/
├── sec/item204/
│   ├── filings.jsonl           # Item 2.04 source inventory
│   ├── html/                   # Cached filing documents
│   └── audit.json              # Discovery audit
├── run_001_item_103_baseline/
│   ├── inventory/              # Issuer inventory and disclosure events
│   ├── panel/                  # Monthly features and labels
│   └── models/                 # Training outputs
└── history/
    ├── item_103_model_evolution/
    ├── item_204_enrichment_evolution/
    └── incomplete_experiments/
```

Paths are supplied through command-line parameters. Moving source files does
not change CLI defaults: the standalone Batch reviewer still looks under
`results/item_204_pipeline/source/` unless explicit paths are supplied. Use the
[cached-filings command below](#review-the-current-cached-filings) for
`results/sec/item204/`. New study runs should use fresh output directories.

The completed thesis run is preserved in the results history:

- `results/history/item_103_model_evolution/01_initial_full_pipeline_xgboost/inventory/` — issuer inventory and disclosure events;
- `results/history/item_103_model_evolution/02_improved_sec_fact_coverage_xgboost/panel/` — improved panel and feature provenance;
- `results/history/item_103_model_evolution/03_rolling_temporal_validation_random_forest/` — selected models, reports, policy decisions and worked examples.

See [the history guide](results/history/README.md) and
[history index](results/history/index.json) for the complete
model and Item 2.04 enrichment evolution.

## Verify the Code

The recorded environment uses Python 3.13.15 and packages pinned in `requirements-lock.txt`.

```sh
.venv/bin/python -m mcf.workflows.launcher -m unittest discover -s tests -v
```

## Rebuild from Scratch

The following steps rebuild the Item 1.03 study. Each output directory must be
new or empty. Item 2.04 enrichment, described later, uses resumable directories.
Set `--dataset` to your local SEC dataset root; the examples below use `dataset`,
while the composite examples use `../dataset`.
These steps document the historical study. The current trainer requires an
Item 2.04 disclosure target and attached audited statement facts; use the
combined workflow below for new model training.

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

## Train the Bankruptcy/Payment-Failure Target

Reuse your existing 2.04 reviews and automatically include every Item 1.03:

```sh
.venv/bin/python -m mcf.workflows.launcher -m mcf.workflows.payment_default_proxy \
  --dataset ../dataset \
  --config configs/study.bankruptcy_or_payment_failure.json \
  --disclosure-results results/item_204_openai_batch_review \
  --statement-facts results/statement_recovery_full/companies \
  --output-dir results/bankruptcy_payment_failure_run
```

This makes no OpenAI calls and builds a fresh combined inventory, monthly panel
and models. Use a new output root. Training requires completed Item 2.04 reviews
and attached audited statement facts. The workflow now defaults to this config.
The [step-by-step guide](docs/bankruptcy_payment_failure_workflow.md) explains
label rules, recurrence, validation and separate stage commands.

The 12 financial predictors and chronological validation remain the baseline.
Standard sample minima remain 10 event companies and 10 positive/negative rows.
Changes to the target require rebuilding the panel and retraining; they do not
guarantee better metrics. Revised 2023–2025 evaluation is retrospective.

The [narrow payment-only guide](docs/disclosed_payment_failure_workflow.md)
and its optional exploratory sparse-event config remain available for comparison.

## Historical Composite Item 1.03 + Item 2.04 Model

The commands below reproduce the earlier broader target. They require its config
explicitly; use the payment-failure guide above for the current target.


The repository also supports a separate experimental target named
`first_sec_payment_default_disclosure_proxy`. It combines every Item 1.03 filing
with Item 2.04 filings classified as `QUALIFIED_DEFAULT` by OpenAI Batch. Every
Item 2.04 filing with available source text is reviewed by AI; there is no
rule-based event classification. Remaining
unresolved Item 2.04 cases censor affected label windows instead of becoming
negative observations.

Run enrichment, combined inventory construction, panel construction and model
training with one command:

```sh
SEC_USER_AGENT='Your Name your.email@example.com' \
.venv/bin/python -m mcf.workflows.launcher -m mcf.workflows.payment_default_proxy \
  --config configs/study.payment_default_proxy.json \
  --dataset ../dataset \
  --statement-facts results/statement_recovery_full/companies \
  --output-dir results/payment_default_proxy
```

This uses OpenAI Batch with `gpt-6-luna`. Set `OPENAI_API_KEY` before running.
The first pass submits jobs and stops before training while reviews are pending;
rerun the same command after completion to collect reviews and continue.

### Run Item 2.04 enrichment separately

The enrichment workflow discovers and downloads filing HTML, then submits
every uncached Item 2.04 filing with available text to OpenAI Batch. Event labels
are assigned only by AI. The default model is `gpt-6-luna`, and the entire visible
filing text is sent. Set `OPENAI_API_KEY` before running:

```sh
SEC_USER_AGENT='Your Name your.email@example.com' \
.venv/bin/python -m mcf.enrichment.item204.workflow \
  --submissions ../dataset/submissions \
  --output-dir results/item_204_pipeline
```

Final classifications are written to
`results/item_204_pipeline/final/classifications.jsonl`. Reruns reuse downloaded
HTML, pending Batch jobs and completed OpenAI reviews. The workflow stores source
metadata in `source/filings.jsonl`, cached documents in `source/html/`, and Batch
jobs, reviews and exports under `final/`. Rerun the same command to collect
finished jobs. After correcting a provider problem, retry
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
  --config configs/study.payment_default_proxy.json \
  --dataset ../dataset \
  --item-204-results results/item_204_pipeline/final \
  --statement-facts results/statement_recovery_full/companies \
  --output-dir results/payment_default_proxy
```

This skips discovery, downloading and AI review, then builds the combined
inventory, panel and models.

### Review the current cached filings

To use the reorganized source cache without downloading the filings again, set
`OPENAI_API_KEY` and run:

```sh
.venv/bin/python -m mcf.enrichment.item204.reviewers.openai_batch \
  --input results/sec/item204/filings.jsonl \
  --html-dir results/sec/item204/html \
  --output-dir results/sec/item204/final
```

Rerun this exact command to check pending jobs and collect completed reviews.
The resulting `results/sec/item204/final` directory can then be passed to
`mcf.workflows.payment_default_proxy` with `--item-204-results`.

Each unique filing request is a separate JSONL item; multiple items are submitted
together in a Batch job. Identical request bodies are deduplicated. The number
of new requests depends on available text and the existing review cache.

| Parameter | Meaning |
|---|---|
| `--input`, `--html-dir` | Source inventory and cached documents for the standalone reviewer |
| `--output-dir` | Keep the same review destination when submitting and collecting results |
| `--model` | Model for new requests; default `gpt-6-luna` |
| `--limit N` | Standalone reviewer pilot limit; default `0` processes all uncached filings |
| `--filing-limit N`, `--llm-limit N` | Combined enrichment workflow's discovery/review limits; both default to `0` (all) |
| `--start`, `--cutoff` | Optional inclusive start and exclusive cutoff filing dates, in `YYYY-MM-DD` format |
| `--dry-run` | Inspect inputs without OpenAI calls; the combined workflow can still download SEC HTML |
| `--offline` | Discovery/combined workflow only: use cached HTML; OpenAI calls remain enabled |
| `--retry-fallbacks` | Retry saved provider failures after fixing their cause |
| `--refresh` | Request fresh reviews instead of reusing saved decisions; omit for normal collection |
| `--max-output-tokens` | Generated-token cap including reasoning; default `3000`, not an input-text limit |
| `--reasoning-effort` | Reasoning setting for new requests; default `medium` |

Full available filing text is used without a character cap. Missing source text
remains visible as `fallback_missing_input`. See the
[enrichment parameter guide](docs/item_204_workflow.md) for all options,
environment variables, recovery and output details.

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
  --statement-facts results/statement_recovery_full/companies \
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

Discover filing metadata and download source documents:

```sh
SEC_USER_AGENT='Your Name your.email@example.com' \
.venv/bin/python -m mcf.enrichment.item204.discover \
  --submissions ../dataset/submissions \
  --output-dir results/item_204_pipeline/source \
  --cutoff 2026-09-07
```

Then classify all Item 2.04 filings with OpenAI Batch (`OPENAI_API_KEY` must be set):

```sh
.venv/bin/python -m mcf.enrichment.item204.reviewers.openai_batch \
  --input results/item_204_pipeline/source/filings.jsonl \
  --html-dir results/item_204_pipeline/source/html \
  --output-dir results/item_204_pipeline/final
```

Rerun the same command to collect completed Batch results. See
[the enrichment parameter guide](docs/item_204_workflow.md) for defaults and options.

The study design is in `configs/study.payment_default_proxy.json`. The resulting
probability concerns the composite SEC disclosure proxy. Item 1.03 includes
bankruptcy or receivership disclosures, while Item 2.04 includes several kinds of
triggering events; the output must not be described as a verified contractual
payment-default probability.
