# Disclosed payment failure within 60 days

This narrower comparison design is `configs/study.disclosed_payment_failure.json`.
The current default uses the [bankruptcy/payment-failure composite](bankruptcy_payment_failure_workflow.md).
This narrower model predicts a new **disclosure episode** of missed debt principal or interest payment
within `(decision date, decision date + 60 calendar days]`. SEC filing date defines
the outcome date. This estimates disclosure risk, not the unobserved contractual
date of default.

Both Item 1.03 and Item 2.04 are reviewed from full available filing text.
Neither heading automatically qualifies. Bankruptcy, receivership, covenant
breach, acceleration and enforcement qualify only if explicit missed-payment
evidence is also present. Required debt prepayment can qualify; optional
deferral, future payment risk and unrelated resolved historical defaults cannot.
Unclear evidence remains `MANUAL_REVIEW`.

## Reuse earlier Item 2.04 classifications

Your existing OpenAI classifications can be used directly, without submitting
new requests:

```sh
.venv/bin/python -m mcf.workflows.launcher -m mcf.workflows.payment_default_proxy \
  --dataset ../dataset \
  --config configs/study.disclosed_payment_failure.json \
  --item-204-results results/item_204_openai_batch_review \
  --statement-facts results/statement_recovery_full/companies \
  --output-dir results/disclosed_payment_failure_run
```

Use a fresh output directory. Earlier `QUALIFIED_DEFAULT / PAYMENT_FAILURE`
reviews with HIGH certainty and evidence qualify. `NON_DEFAULT / BENIGN` reviews
are reused as negatives. Acceleration and enforcement classifications remain
unresolved because they establish neither missed payment nor its absence.
Manual reviews remain unresolved. The original classifications are preserved;
the inventory records legacy provenance and reuse counts.

This reuses the earlier model's interpretation and evidence; it does not rerun
them under the revised prompt. Item 1.03-only filings without reviews are censored,
not automatically treated as payment failures. Filings containing both items can
reuse their 2.04 review. Complete 1.03 coverage still requires its evidence review.
Historical rule-only classifications cannot supply payment labels.

Every qualifying filing is saved in `inventory/disclosure_events.csv`. Repeated
disclosures no more than 90 days apart belong to one episode, measured from the
latest qualifying disclosure. A subsequent filing after a longer quiet gap starts
a new episode, including for a company with earlier episodes. Filings containing
both items are reviewed once. All episodes can contribute training outcomes;
there is no first-ever-event restriction.

Companies are excluded from training during the 90-day period following each
known qualifying disclosure and can re-enter after it. This eligibility rule uses
only disclosures already observed at the decision date. **A quiet gap does not
prove that a debt was cured**: these are disclosure episodes, not verified repeat
contractual defaults. For the latter, explicit cure dates and obligation-level
event adjudication would be a better dataset. `episode_gap_days` is configurable;
changing it requires rebuilding both inventory and panel. Choose sensitivity
analyses before looking at the revised test results.

Unreviewed, failed-input and `MANUAL_REVIEW` candidate filings censor windows
where their unresolved outcome could change the label, and later rows until
reviewed. They never silently become negatives. Negative labels require observed
issuer filing follow-up. A confirmed positive before an unresolved filing remains
positive.

## Run discovery separately

Run all commands from the repository root. Discover both items, with no lower
date bound, so prior histories are available for episode grouping. Reuse your
existing HTML cache to avoid downloading Item 2.04 files again:

```sh
SEC_USER_AGENT='Your Name your.email@example.com' \
.venv/bin/python -m mcf.enrichment.item204.discover \
  --submissions ../dataset/submissions \
  --items 1.03 2.04 \
  --cutoff 2026-09-07 \
  --html-dir results/sec/item204/html \
  --output-dir results/sec/payment_failure
```

Discovery collects all matching 8-K/8-K/A filings, including repeated filings.
Check `results/sec/payment_failure/audit.json` for download errors. Missing
documents must be recovered to get complete review coverage.

## Submit and collect payment-specific reviews

For a fresh review of both items under the revised prompt, set `OPENAI_API_KEY`
in your environment and use a fresh review folder:

```sh
.venv/bin/python -m mcf.enrichment.item204.reviewers.openai_batch \
  --input results/sec/payment_failure/filings.jsonl \
  --html-dir results/sec/item204/html \
  --output-dir results/sec/payment_failure_review \
  --payment-failure-only \
  --model gpt-6-luna \
  --max-output-tokens 3000 \
  --batch-max-requests 200
```

Rerun this **same command** to collect completed jobs and submit remaining jobs.
Jobs are submitted sequentially; 200 requests limits job size but does not
guarantee staying under a model's queued-token allowance for long documents.
All filings are processed over successive jobs; this is not a total filing cap.
Do not add `--refresh` for collection. Final results are
`results/sec/payment_failure_review/classifications.jsonl`.

| Parameter | Meaning |
|---|---|
| `--payment-failure-only` | Required for the new target; uses the payment-specific prompt and separate cache identity |
| `--input` | Inventory containing both filing items |
| `--html-dir` | Directory containing full filing HTML |
| `--output-dir` | Review state and results; keep identical when collecting |
| `--model` | Model for new requests; defaults to `gpt-6-luna` |
| `--reasoning-effort` | Defaults to `medium` |
| `--max-output-tokens` | Output/reasoning cap, default 3000; does not truncate input text |
| `--batch-max-requests` | Maximum requests per job; standalone default 50,000; example uses 200 |
| `--limit` | Total new reviews attempted in this invocation; default 0 processes all |
| `--retry-fallbacks` | Retry saved provider failures after correcting their cause |
| `--retry-manual-review` | Retry saved unresolved results with changed model/settings, keeping resolved results |

New reviews incur API charges; direct reuse above makes no OpenAI calls.
The fresh review command is a new target review, not a retry of only
the old `MANUAL_REVIEW` subset. There is no budget controller. Use a pilot with
`--limit` if you want to inspect token usage before processing everything.
The [Batch guide](item_204_workflow.md) covers failure recovery and all parameters.

## Build the panel and retrain

After pending and deferred counts reach zero, reuse the completed reviews:

```sh
.venv/bin/python -m mcf.workflows.launcher -m mcf.workflows.payment_default_proxy \
  --dataset ../dataset \
  --config configs/study.disclosed_payment_failure.json \
  --item-204-results results/sec/payment_failure_review \
  --statement-facts results/statement_recovery_full/companies \
  --output-dir results/disclosed_payment_failure_run
```

Use a fresh output root. With `--item-204-results`, this command makes no OpenAI
calls; it builds `inventory/`, `panel/`, `models/` and `workflow_summary.json`.
Without this argument, the workflow discovers both items, reviews them with the
payment-specific prompt and stops while batches are pending. To run this narrower design, specify its config explicitly; the default config
is now the bankruptcy/payment-failure design and its default batch size is 200.

To build each stage separately:

```sh
.venv/bin/python -m mcf.data.empirical inventory \
  --dataset ../dataset \
  --target disclosed_payment_failure_within_60_days \
  --episode-gap-days 90 \
  --item-204-results results/sec/payment_failure_review \
  --cutoff 2026-09-07 \
  --output-dir results/disclosed_payment_failure_run/inventory

.venv/bin/python -m mcf.data.empirical panel \
  --dataset ../dataset \
  --inventory results/disclosed_payment_failure_run/inventory \
  --config configs/study.disclosed_payment_failure.json \
  --statement-facts results/statement_recovery_full/companies \
  --output-dir results/disclosed_payment_failure_run/panel

.venv/bin/python -m mcf.workflows.launcher -m mcf.models.train \
  --config configs/study.disclosed_payment_failure.json \
  --panel results/disclosed_payment_failure_run/panel/panel.csv \
  --output-dir results/disclosed_payment_failure_run/models
```

The existing 12 financial predictors remain the initial baseline. Cash,
liquidity, leverage and cash flow already address payment ability; timestamps,
staleness controls and next-day information availability remain enforced. Adding
filing outcomes or future payment information as predictors would leak the target.
The policy's known-disclosure flag now follows the recent-payment episode rule,
rather than permanently treating every company with a past filing as defaulted.

Chronological tuning, calibration, selection, purging and company-clustered
uncertainty estimates remain in place. The minimum-class and minimum-event-company
checks still apply: narrowing the target can leave insufficient positives. The
2023–2025 results for earlier targets have already been inspected, so evaluation
on those years for this revised target is retrospective, not untouched external
validation. Future unexamined periods provide stronger confirmation.

Old `selection.json` files and historical configs retain their original target.
They must be retrained in a fresh output directory to evaluate the revised target.
Historical composite reproduction uses `configs/study.payment_default_proxy.json`
explicitly; historical Item 1.03 reproduction uses `configs/study.sec_disclosure.json`.

## Sparse-event training error

`too few distinct companies with events` counts companies with positive labels
after chronological purging, not the total number of classified documents.
The standard config requires at least 10 event companies and 10 positive and
negative company-months in each stage and each annual tuning validation fold.
Repeated positive months for one company do not create more independent companies.

In the current `run_004_recurrent_disclosures_initial` panel, tuning has 8 event companies, calibration has 9,
and the annual tuning folds have 3 (2017) and 5 (2018). The standard design therefore
stops before fitting. More payment-specific evidence review, especially for missing
1.03 filings and unresolved 2.04 cases, is the stronger way to improve coverage.
Do not add acceleration/enforcement positives just to pass the sample checks.

For an **exploratory baseline**, an explicitly separate config lowers
`min_class_count` to 5 and `min_event_companies` to 3. It keeps the target, dates,
episode rule, predictors, temporal purging and company-clustered uncertainty
estimation unchanged. The relaxed values allow fitting; they do not establish
that three event companies are sufficient for stable tuning or reliable credit
probabilities. `selection.json` records the exploratory status and its limitations.

Reuse the already built panel; no discovery, inventory rebuild or OpenAI calls:

```sh
.venv/bin/python -m mcf.workflows.launcher -m mcf.models.train \
  --config configs/study.disclosed_payment_failure.exploratory.json \
  --panel results/run_004_recurrent_disclosures_initial/panel/panel.csv \
  --output-dir results/run_004_recurrent_disclosures_initial/models_exploratory
```

Use a fresh model output directory. The standard config retains its original
minimum counts. Later results should be reported as exploratory until coverage
and independent validation are improved.
