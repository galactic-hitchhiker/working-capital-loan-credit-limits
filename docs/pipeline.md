# Staged SEC study pipeline

Use one coordinator for the current bankruptcy/payment-failure study. Each stage
can also be run independently. The coordinator calls the existing extraction,
review, panel and training functions; it does not change their label or feature
rules.

| Step | Command | Main outputs |
| --- | --- | --- |
| 1. Download | `download` | SEC ZIPs and unpacked Company Facts, submissions, Notes and face statements in `--dataset` |
| 2. Inventory | `inventory` | `source_inventory/` for issuer screening; `DATASET/statement_facts/companies/` for recovered statement facts |
| 3a. Classify | `classify` | `disclosures/final/classifications.jsonl` from OpenAI Batch, or supplied reviews |
| 3b. Panel | `panel` | Reviewed `inventory/`, then `panel/panel.csv` and feature provenance |
| 4. Train | `train` | `models/` with model selection, metrics and audit files |

The source inventory uses Company Facts and submissions to identify issuers.
The statement importer then reads the downloaded **Financial Statement and Notes**
ZIPs, anchored to that inventory, and stores the extracted facts with `--dataset`.
SEC's separate face-statement ZIPs are retained
under `financial_statements/face/`; the existing importer uses the Notes ZIPs.

Item 2.04 decisions are necessary to build the **final** disclosure inventory.
For that reason, `panel` first calls the existing reviewed inventory builder and
then the existing company-month panel builder. The extra `source_inventory/`
supports statement extraction; `inventory/`, `panel/` and `models/` retain their
existing schemas and calculations.

## Run everything

```sh
export SEC_USER_AGENT="Your Name your-email@example.com"
export OPENAI_API_KEY="your-key"
.venv/bin/python -m mcf.workflows.pipeline all \
  --dataset ../dataset_full \
  --output-dir results/new_run
```

The downloader includes both SEC statement series. Downloading the full history
requires substantial disk space. OpenAI Batch may still have pending work after
the first run; rerun the same command to collect it. Completed downloads and the
source inventory are reused. If a later stage fails after writing its output,
run that stage separately with a fresh output root or inspect its audit first.

For an already downloaded SEC snapshot, use `--skip-download`. To reuse existing
statement facts and classifications without new statement import or OpenAI calls:

```sh
.venv/bin/python -m mcf.workflows.pipeline all \
  --skip-download \
  --dataset ../dataset_full \
  --statement-facts ../dataset_full/statement_facts/companies \
  --disclosure-results results/item_204_openai_batch_review/final \
  --output-dir results/new_run
```

## Run stages separately

```sh
.venv/bin/python -m mcf.workflows.pipeline download \
  --dataset ../dataset_full --output-dir results/new_run

.venv/bin/python -m mcf.workflows.pipeline inventory \
  --dataset ../dataset_full --output-dir results/new_run

.venv/bin/python -m mcf.workflows.pipeline classify \
  --dataset ../dataset_full --output-dir results/new_run

.venv/bin/python -m mcf.workflows.pipeline panel \
  --dataset ../dataset_full --output-dir results/new_run

.venv/bin/python -m mcf.workflows.pipeline train \
  --output-dir results/new_run
```

The `classify` step uses the existing [Item 2.04 Batch workflow](item_204_workflow.md).
Supply `--disclosure-results PATH` to reuse a completed classifications file or
directory. `panel` accepts the same option when run alone. Supply
`--statement-facts PATH` to reuse a statement supplement directory. Each stage
uses the study configuration passed with `--config`; the current combined target
is the default.

After training, the existing reporting and [policy simulation](workflow.md) can
turn model outputs into thesis tables, figures and illustrative credit limits.
Those are useful downstream steps but are kept separate from fitting the model.
