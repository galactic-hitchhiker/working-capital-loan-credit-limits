# Item 2.04 enrichment with OpenAI Batch

The workflow discovers and downloads SEC Item 2.04 filings, then OpenAI Batch
classifies **every filing**. There is no rule-based event classifier and no
label-based filter before AI review. Every input row appears in the final exports.
Completed OpenAI Batch reviews are reused; decisions from removed providers do
not bypass OpenAI review.

## Run enrichment on the files already downloaded

From the repository root, set your API key in your terminal:

```bash
export OPENAI_API_KEY='your-api-key'
```

Then run:

```bash
.venv/bin/python -m mcf.enrichment.item204.reviewers.openai_batch
```

That command defaults to:

| Setting | Default | Meaning |
| --- | --- | --- |
| Input | `results/item_204_pipeline/source/filings.jsonl` | Discovered Item 2.04 filing metadata; every row is reviewed. |
| HTML directory | `results/item_204_pipeline/source/html` | The cached SEC filing documents; an existing `rules/html` cache is reused when present. |
| Output directory | `results/item_204_openai_batch_review` | Batch jobs, saved reviews, final CSV/JSONL, and audit. |
| Model | `gpt-6-luna` | The OpenAI model used for new requests. |
| Number of reviews | All | No pilot limit or date filter unless you explicitly supply one. |
| Filing text | Entire visible filing | No character limit, truncation, or length-based skip. |
| Reasoning | `medium` | The model's reasoning effort. |
| Output tokens | `3000` | Maximum generated tokens per review, including reasoning; this does **not** limit filing input. |

If the new inventory does not exist yet, the standalone command can read the
previous `rules/classifications.jsonl` as a source inventory and use `rules/html`.
Its old labels are ignored: `NON_DEFAULT`, `QUALIFIED_DEFAULT`, and
`MANUAL_REVIEW` rows all go through OpenAI.

The **first run submits the requests and exits**. Run the **same command again**
later to check status and import finished results. While a job is pending, its
rows remain `MANUAL_REVIEW` with `llm_status: batch_pending`. Reruns reuse pending
jobs and completed reviews. Batch processing is asynchronous and has a 24-hour
completion window. See the [official Batch guide](https://developers.openai.com/api/docs/guides/batch).

Read the results in:

```text
results/item_204_openai_batch_review/classifications.csv
results/item_204_openai_batch_review/classifications.jsonl
```

The CSV is a compact filing-level table. The JSONL and individual `reviews/`
files contain explanations, evidence quotes, and request metadata. `audit.json`
contains label counts, pending counts, and job statuses. `review_log.jsonl`
records imported decisions. Keep `batches/` and `reviews/` so reruns can resume.

## Parameters you might actually need

### Retry only unresolved decisions with a stronger model

After collecting the initial batch, use the same original input, HTML directory
and output directory. For the current saved run:

```bash
.venv/bin/python -m mcf.enrichment.item204.reviewers.openai_batch \
  --input results/sec/item204/filings.jsonl \
  --html-dir results/sec/item204/html \
  --output-dir results/item_204_openai_batch_review \
  --retry-manual-review \
  --model gpt-6-sol \
  --max-output-tokens 8000 \
  --reasoning-effort medium
```

This retries saved `MANUAL_REVIEW` decisions, including validation and generation
failures, only when their model or settings differ from the requested configuration.
It preserves `QUALIFIED_DEFAULT` and `NON_DEFAULT` decisions. Missing-text cases
cannot be submitted until source text is available. All selected filings must
already have saved OpenAI reviews; a fresh output directory is not accepted.

Run the exact same command later to collect results. Pending requests are reused,
and completed retries are cached even when their answer remains `MANUAL_REVIEW`.
Change the model or settings to intentionally attempt those cases again.
The full combined CSV/JSONL is updated in the same output directory; no manual
merge is required. Do not combine this option with `--refresh` or `--retry-fallbacks`.
Add `--dry-run` to preview eligible filings without OpenAI calls (it writes local exports).

The 8000-token setting increases the previous 3000-token output/reasoning allowance;
it does not change the full-text input policy. A stronger model may still find
insufficient evidence. This command has no budget cap: higher model prices and
output allowances can exceed the earlier $15 budget. See
[official model pricing](https://developers.openai.com/api/docs/models/gpt-6-sol).

### General options

If OpenAI rejects a job with "Enqueued token limit reached", the model's queue
limit counts input tokens across pending jobs. Reducing `--max-output-tokens`
does not reduce that input-token count. Add `--batch-max-requests 200` to the
same command to prepare smaller jobs. The reviewer submits one job at a time;
rerun to collect results and submit the next job. Existing unsent large jobs and
jobs rejected specifically for enqueued-token capacity are split automatically,
preserving their original manifests and completed decisions.

Request counts do not guarantee a token count because document lengths vary.
If a smaller job still exceeds capacity, wait for other jobs or lower the request
limit further. Active jobs are never split or resubmitted. All available filing
text is preserved.

All parameters are optional for the command above.

| Parameter | When to use it |
| --- | --- |
| `--input PATH` | Your filing-inventory JSONL is somewhere else. |
| `--html-dir PATH` | Your cached filing HTML is somewhere else. |
| `--output-dir PATH` | Save this enrichment run in another directory; use the same directory when collecting results. |
| `--model MODEL` | Select another OpenAI model supporting Batch, Responses, and structured outputs. |
| `--dry-run` | Check local inputs without uploading or submitting anything. |
| `--limit N` | Deliberately run a pilot of at most N uncached filing attempts per pass. Omit it to process all; `0` also means all. |
| `--start YYYY-MM-DD` | Include filings on or after this date. Omit it for all dates present in the input. |
| `--cutoff YYYY-MM-DD` | Include filings strictly before this date. Omit it for all dates present in the input. |
| `--retry-fallbacks` | Retry saved provider/request failures after fixing their cause; retain successful reviews and other saved outcomes. |
| `--retry-manual-review` | Standalone Batch reviewer: retry saved unresolved decisions with changed model/settings, preserving resolved decisions and completed retries. |
| `--refresh` | Intentionally replace saved decisions with new AI reviews. It does not duplicate an identical pending job. Do not use it for normal collection. |

Advanced parameters are `--reasoning-effort` (default `medium`),
`--max-output-tokens` (default `3000`), and `--batch-id` (recovery of a submission
interrupted after its create request was sent). Leave these at their defaults
for normal enrichment. `--refresh` and `--retry-fallbacks` cannot be combined.
There is no provider selector, local-model configuration, budget control, or
character-limit parameter.

The input JSONL remains unchanged. Full visible filing text is used whenever
cached HTML exists, including other items incorporated by reference. An Item
2.04 extract is used only if full HTML is unavailable. If both are missing, the
row receives an explicit `fallback_missing_input` decision and stays unresolved.
The Batch reviewer does not download SEC files or external exhibits. Requests
that the API rejects are recorded as failures rather than silently omitted.

## Download missing filings and run both stages

Use this command when the source filings still need downloading, or when you
want to rebuild the source inventory from the submissions metadata:

```bash
export SEC_USER_AGENT='Your Name your.email@example.com'
.venv/bin/python -m mcf.enrichment.item204.workflow \
  --submissions ../dataset/submissions \
  --output-dir results/item_204_pipeline
```

This reuses cached HTML, retries missing downloads, inventories every Item 2.04
filing, and submits Batch reviews for every uncached filing. No event labels are
assigned during discovery. Rerun the same command to collect finished reviews. Results are in
`results/item_204_pipeline/final/`. Existing OpenAI Batch reviews in that directory
are retained unless you explicitly request `--refresh`. If a previously missing
filing becomes available, its missing-input fallback is retried automatically.

| Additional workflow parameter | Meaning |
| --- | --- |
| `--submissions PATH` | Directory containing company SEC submissions metadata; required. |
| `--output-dir PATH` | Workflow root: `source/` holds filing metadata and HTML; `final/` holds AI classifications. |
| `--user-agent TEXT` | Your name and email for SEC downloads; defaults to `SEC_USER_AGENT`. |
| `--interval SECONDS` | Delay between SEC downloads; default `0.25`, minimum `0.1`. |
| `--offline` | Use cached HTML only; do not download missing filings. |
| `--filing-limit N` | Limit the discovery/download stage for a pilot; default `0` means all. |
| `--llm-limit N` | Limit uncached AI attempts per pass; default `0` means all. |

The model, date filters, dry-run, refresh, retry, and advanced Batch options have
the same meanings as above. In the combined workflow, `--dry-run` prevents
OpenAI requests but still runs SEC discovery/downloading; add `--offline` to
prevent SEC downloads as well.

## Classification and downstream use

`QUALIFIED_DEFAULT` requires explicit payment failure, realized default-related
acceleration, or realized foreclosure/trustee-sale enforcement. `NON_DEFAULT`
requires affirmative evidence of a benign/nonqualifying event. Ambiguous,
incomplete, disputed, or unsupported evidence stays `MANUAL_REVIEW`.

The reviewer returns structured JSON, short explanations, and source-backed
quotes. Resolved answers require high evidence certainty. Acceleration requires
quotes supporting both the default trigger and actual acceleration. Item 2.04
alone, bankruptcy alone, hypothetical acceleration, and fulfilled contractual
prepayment do not establish the study's qualifying event. Manually validate a
sample before using the labels. These are disclosure classifications, not
verified contractual payment-default labels. See [SEC Form 8-K](https://www.sec.gov/files/form8-k.pdf).

`mcf.workflows.payment_default_proxy` also uses Batch only. It stops before
inventory, panel construction, and training while enrichment is pending or
limited. After collecting completed results, rerun it to continue, or pass
`--item-204-results PATH` pointing to the completed enrichment output directory.
Historical saved decisions remain readable; removing integrations does not
remove prior research artifacts.
