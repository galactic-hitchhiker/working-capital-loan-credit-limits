# Bankruptcy/receivership or payment failure within 60 days

This is the current default target, configured in
`configs/study.bankruptcy_or_payment_failure.json`.

| Source | Outcome rule |
|---|---|
| Exact Item 1.03 on 8-K/8-K/A | Automatically qualifies, without LLM payment-evidence conditions |
| Item 2.04 without 1.03 | Requires `QUALIFIED_DEFAULT` and `PAYMENT_FAILURE`, HIGH certainty and evidence quotes |
| 2.04 acceleration/enforcement alone | Remains unresolved for this outcome |
| Missing or manual 2.04-only review | Remains unresolved |

Both sources contribute **outcome labels**, not financial predictor features.
Future filing information cannot be used as an input predictor for an earlier
prediction date. A filing containing both items counts once; Item 1.03 qualifies
even if its 2.04 review is negative or unresolved.

All qualifying filings are retained. Reports within a rolling 90-day gap form
one disclosure episode; later episodes for the same company can contribute new
outcomes. The model predicts a new disclosure episode within the next 60 calendar
days. Recent known episodes are excluded from the training risk set for 90 days.
Unresolved earlier 2.04-only evidence still censors affected labels. The episode
gap is operational and does not establish contractual cure.

This is a broad disclosure proxy. Item 1.03 includes bankruptcy/receivership and
confirmation of reorganization plans, so it does not prove a new missed payment
or complete inability to repay in each filing. See
[SEC Form 8-K, Item 1.03](https://www.sec.gov/files/form8-k.pdf).

## Reuse your existing reviews and train

```sh
.venv/bin/python -m mcf.workflows.launcher -m mcf.workflows.payment_default_proxy \
  --dataset ../dataset \
  --config configs/study.bankruptcy_or_payment_failure.json \
  --disclosure-results results/item_204_openai_batch_review \
  --output-dir results/bankruptcy_payment_failure_run
```

Use a fresh output directory. This command makes **no OpenAI calls**. It reads
all 1.03 dates from local submissions and the saved 2.04 classifications, rebuilds
`inventory/` and `panel/`, then trains into `models/`. Check
`models/selection.json` for selection and metrics, and `workflow_summary.json`
for the full run summary. A payment-only panel cannot be reused under this target;
its labels and censoring are different.

The default retains the 12 point-in-time financial predictors and the standard
minimum of 10 event companies and 10 positive/negative rows for each development
stage and annual tuning validation fold. Chronological splits, purging,
calibration and company-clustered uncertainty remain in place. Evaluation on
2023–2025 is retrospective because earlier results were examined.

A preflight reconstruction using the local `run_003` financial feature histories
and current saved reviews found 56 event companies in tuning (103 positive
company-months) and 43 in calibration. The annual tuning validation folds contain
31 (2017) and 26 (2018) event companies. All standard stage/fold sample minima pass.
These are label/sample checks, not fitted-model performance results.

Without `--disclosure-results`, the workflow discovers/reviews only 2.04 using
the payment-specific prompt; 1.03 needs no AI review. Rerun to collect pending
Batch jobs before training. For separate discovery/review parameters, see the
[Batch guide](item_204_workflow.md); use `--items 2.04` for discovery and
`--payment-failure-only` for the reviewer. Keep one review output folder across
submission and collection.

For stage-by-stage operation:

```sh
.venv/bin/python -m mcf.data.empirical inventory \
  --dataset ../dataset \
  --target disclosed_bankruptcy_or_payment_failure_within_60_days \
  --episode-gap-days 90 \
  --disclosure-results results/item_204_openai_batch_review \
  --cutoff 2026-09-07 \
  --output-dir results/bankruptcy_payment_failure_run/inventory

.venv/bin/python -m mcf.data.empirical panel \
  --dataset ../dataset \
  --inventory results/bankruptcy_payment_failure_run/inventory \
  --config configs/study.bankruptcy_or_payment_failure.json \
  --output-dir results/bankruptcy_payment_failure_run/panel

.venv/bin/python -m mcf.workflows.launcher -m mcf.models.train \
  --config configs/study.bankruptcy_or_payment_failure.json \
  --panel results/bankruptcy_payment_failure_run/panel/panel.csv \
  --output-dir results/bankruptcy_payment_failure_run/models
```

Earlier narrower payment-failure configs and their
[guide](disclosed_payment_failure_workflow.md) remain available for comparison.
The historical first-event composite is also preserved under
`configs/study.payment_default_proxy.json`.
