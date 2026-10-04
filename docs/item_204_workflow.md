# Item 2.04 candidate-event review

`mcf/enrichment/item204/classify.py` is separate from the current Item 1.03 inventory and model pipeline. It scans every main CIK submission file and its referenced historical archives, finds exact Item 2.04 filings in 8-K/8-K/A records, downloads primary-document HTML, and extracts the Item 2.04 narrative with Beautiful Soup.

## Single rules-then-LLM workflow

The unified command downloads or reuses filing HTML, applies the deterministic
classifier, and sends only `MANUAL_REVIEW` cases to the selected provider:

```sh
SEC_USER_AGENT='Your Name your.email@example.com' \
.venv/bin/python -m mcf.enrichment.item204.workflow \
  --submissions ../dataset/submissions \
  --output-dir results/item_204_pipeline
```

Ollama and `qwen3.5:9b` are the defaults. Rule outputs and HTML are stored under
`rules/`; merged final decisions and the organized review cache are under `final/`.
The top-level `workflow_audit.json` records hashes and final counts. Reruns reuse
downloaded HTML and successful LLM decisions. Use `--retry-fallbacks` after fixing
a provider problem.

For the complete composite Item 1.03 + Item 2.04 panel and model, run:

```sh
SEC_USER_AGENT='Your Name your.email@example.com' \
.venv/bin/python -m mcf.workflows.launcher -m mcf.workflows.payment_default_proxy \
  --dataset ../dataset \
  --output-dir results/payment_default_proxy
```

This uses `configs/study.payment_default_proxy.json`, constructs the combined
inventory, builds the point-in-time panel and trains the existing model families.
Qualified Item 2.04 and Item 1.03 filings are positive disclosure events. An
unresolved or missing Item 2.04 decision censors any label window it affects.
Same-filing Item 1.03/2.04 records are deduplicated by accession number.

The target is deliberately named a payment-default **disclosure proxy**. Item 1.03
does not require a missed payment, and Item 2.04 can describe acceleration or
enforcement without proving nonpayment. The fitted probability therefore must not
be reported as the probability of verified contractual payment default.

## Install and run

```sh
.venv/bin/python -m pip install -r mcf/enrichment/item204/requirements.txt

# Metadata-only inventory: no network requests.
.venv/bin/python -m mcf.enrichment.item204.classify \
  --submissions ../dataset/submissions \
  --output-dir results/item_204_review \
  --start 2011-01-01 --cutoff 2026-09-07 --discover-only

# First inspect a small downloaded pilot.
.venv/bin/python -m mcf.enrichment.item204.classify \
  --submissions ../dataset/submissions \
  --output-dir results/item_204_review \
  --start 2011-01-01 --cutoff 2026-09-07 \
  --user-agent 'Your Name your.email@example.com' --limit 50
```

Remove `--limit 50` to review all matching filings. Use your real contact details in the SEC User-Agent. The cutoff is exclusive, matching the current inventory's convention. Adjust the submissions path if your dataset has a different location.

Successful downloads are cached in `html/`; reruns reuse them and retry previously failed downloads. `--offline` parses existing cached files without downloading. Each run rebuilds the CSV, JSONL and audit for its selected scope; a limited pilot therefore replaces the summary outputs, but keeps the HTML cache. Do not run two processes against the same output directory.

## Outputs

- `classifications.csv`: compact filing-level review table with classification, source link and Item 1.03 overlap flags.
- `classifications.jsonl`: full Item 2.04 extracted text, regex evidence, extraction status, HTML hash, archive completeness and errors.
- `audit.json`: rule version, filtering dates and class/status counts.
- `html/`: cached original filing bytes for reproducibility.

`QUALIFIED_DEFAULT` means that the rules found strong evidence of an actual default event in the extracted section. It can include covenant defaults and acceleration, and does not itself certify a missed payment. `payment_default_evidence` separately flags payment-related phrases; it is a review aid, not a verified label. `NON_DEFAULT` represents apparently benign or hypothetical language. Unsupported, short, cross-referenced or failed downloads remain `MANUAL_REVIEW` rather than silently becoming negatives.

The classifier requires strong financial-default and realized-event evidence in the same sentence. It recognizes missed payments, unpaid principal/interest, realized acceleration, and initiated/completed enforcement. Hypothetical or negated sentences cannot qualify automatically; unresolved strong-default language stays `MANUAL_REVIEW`. Technical covenant breaches and benign redemption language can be `NON_DEFAULT` when no strong event evidence is present. JSONL preserves both raw regex matches and `qualifying_event_sentences`; `payment_default_evidence` requires the same contextual checks. These conservative rules can miss real events in complex or multi-sentence narratives, so validate a manually reviewed sample before using labels. The audit records `item204-v5-modal-may`; rerun classification to refresh outputs using cached HTML.

## Using candidates in a future inventory

Run this as a one-time preprocessing stage before constructing a revised inventory. Keep all Item 2.04 filings in the audit, including co-filed Item 1.03 records. For additional filing candidates, review `QUALIFIED_DEFAULT` records where `prior_or_same_item_103` is false; do not filter on a later Item 1.03 date when constructing historical eligibility, since that uses future information.

Before changing labels, manually validate precision across classes and years, resolve incorporated-by-reference text, and deduplicate amendments/repeated reports of the same economic event. Preserve the filing availability date separately from the underlying event date. Define whether the new target is payment default, covenant default, acceleration, or a composite distress disclosure. The standalone classifier does not change existing inventories or training labels; the composite workflow writes a new inventory, panel and model run under its own output directory.

Item 2.04 includes triggering events that materially accelerate or increase financial obligations, which can extend beyond missed payments. Source: [SEC Form 8-K](https://www.sec.gov/files/form8-k.pdf).

Payment-failure verbs now require a financial object directly after them. Newlines and semicolons do not split event evidence away from a conditional clause. Disputed or alleged events require manual review. Explicit nonpayment (for example, “did not pay interest”) remains positive evidence; this differs from denying that a default occurred.

## Local Ollama review (recommended setup for your machine)

All enrichment code is in `mcf/enrichment/item204/`. Run commands from the repository root using `-m`:

| File | Purpose |
| --- | --- |
| `classify.py` | SEC discovery, HTML download/cache, and regex classification |
| `reviewers/common.py` | Shared conservative prompt, quote validation, resume cache, and exports |
| `reviewers/openai.py` | OpenAI Responses API reviewer; needs `OPENAI_API_KEY` |
| `reviewers/ollama.py` | Local Ollama reviewer; default `qwen3.5:9b`, no API key |
| `requirements.txt` | Beautiful Soup dependencies for both reviewers |

Start the Ollama app (or run `ollama serve` if no server is running). You have already pulled `qwen3.5:9b`; no additional model download is needed.

Check local files without inference:

```bash
.venv/bin/python -m mcf.enrichment.item204.reviewers.ollama --dry-run
```

Review a pilot with your default model:

```bash
.venv/bin/python -m mcf.enrichment.item204.reviewers.ollama --limit 20
```

Remove `--limit 20` to review all remaining eligible cases. Repeating a limited run reuses successful reviews and advances through new cases. Invalid model answers remain manual and are retried on subsequent runs. Full runs can take substantial time on local hardware.

Ollama reads the same `results/item_204_review/classifications.jsonl` and cached `html/` directory as OpenAI. Its separate output directory is **`results/item_204_ollama_review/`**, containing merged JSONL/CSV, `audit.json`, and the `reviews/` decision store. Every terminal decision is saved as an individual JSON file there, including conservative fallback decisions. Each file contains the filing identifiers, status, model/provider settings, explanation, evidence, and input scope. An explicit `--limit` deferral is not stored because no decision was made. The original classifier and OpenAI results are preserved. No SEC downloads or external model API requests occur; the default endpoint is `http://localhost:11434/api/chat`. Only local HTTP endpoints are accepted.

Generated decision files are organized independently from the Python source:

```text
reviews/
├── qualified_default/
├── non_default/
└── manual_review/
    ├── fallback_missing_input/
    ├── fallback_validation_error/
    ├── fallback_provider_error/
    ├── fallback_provider_unavailable/
    └── fallback_context_budget/
```

Only folders containing decisions are created. Legacy flat review files are organized automatically at startup. Cache discovery is recursive, so moving them does not cause reprocessing. When `--retry-fallbacks` succeeds, the fallback file is removed and its replacement is stored under the resulting classification.

Generation uses JSON schema, temperature 0, thinking disabled, 32,768 context tokens, and a 4,096-token output budget. Missing/invalid/incomplete evidence stays `MANUAL_REVIEW`. `--think` enables thinking, but it can be slower and exhaust the output budget. A conservative byte-based budget prevents oversized inputs from being silently truncated; it may skip filings that would fit under exact tokenization. The default `--max-chars` is 24,000. To allow longer filings, increase both limits if your RAM permits:

```bash
.venv/bin/python -m mcf.enrichment.item204.reviewers.ollama \
  --limit 20 --num-ctx 65536 --max-chars 50000
```

The reviewer no longer silently skips oversized inputs. When the full filing exceeds `--max-chars`, it sends the previously extracted Item 2.04 narrative instead and records `llm_input_scope: item_204_extract`. If even that text exceeds the configured context budget, it emits an explicit conservative `MANUAL_REVIEW` result with `fallback_context_budget`. `--timeout 600` is the default per-request timeout in seconds; increase it if your computer generates slowly. Model settings are included in Ollama cache keys. If you replace the weights behind the same model tag, use a fresh `--output-dir` to avoid reusing reviews generated by the earlier weights.

The provider uses Ollama's [chat API](https://docs.ollama.com/api/chat) and [structured outputs](https://docs.ollama.com/capabilities/structured-outputs). Validate a manually reviewed sample before using LLM labels in the study.

## Additional LLM review of unresolved filings

`mcf/enrichment/item204/reviewers/openai.py` reads only `MANUAL_REVIEW` records from the original JSONL and uses already downloaded HTML. It never fetches SEC documents. Beautiful Soup extracts the full visible filing, allowing the model to follow internal references from Item 2.04. External exhibits are not fetched. Large filings use the saved Item 2.04 extract.

Use an OpenAI API model available to your account that supports Responses structured outputs. The model is explicitly supplied for reproducibility. Install `mcf/enrichment/item204/requirements.txt` if needed; no additional SDK is required.

First inspect cached inputs without making API calls:

```bash
.venv/bin/python -m mcf.enrichment.item204.reviewers.openai --model YOUR_MODEL --dry-run
```

Set `OPENAI_API_KEY` in your shell environment securely, then review a pilot:

```bash
.venv/bin/python -m mcf.enrichment.item204.reviewers.openai --model YOUR_MODEL --limit 20
```

Omit `--limit` to process all remaining cases. The limit counts new API attempts, including failures; cached reviews do not consume it. This sends public filing text to OpenAI and incurs API charges. Do not run multiple processes against the same output directory.

Outputs are separate under `results/item_204_llm_review/`:

- `classifications.jsonl`: all original records, with LLM decisions and provenance added for reviewed manual cases.
- `classifications.csv`: concise merged labels and review status.
- `reviews/`: resumable review cache keyed by filing HTML hash, requested model, prompt, schema, and version. Each response records exact supporting quotes, explanation, event type, model, usage, and timestamp.
- `audit.json`: input hash, counts, API attempts, and configuration.

The label is `QUALIFIED_DEFAULT` to match the existing classifier (rather than `QUALIFY_DEFAULT`). Only high-certainty answers with verbatim evidence can receive `QUALIFIED_DEFAULT` or `NON_DEFAULT`. Payment failure, acceleration, and enforcement are recorded separately. Generic defaults, disputed claims, unavailable references, invalid quotes, errors, and uncertainty stay `MANUAL_REVIEW`. A historical event that was later cured can qualify; inspect the explanation for timing. LLM certainty is not a calibrated probability, and quote verification does not establish semantic correctness. Manually validate a sample before adding these candidate labels to the study target.

Original classifications, inventory, panel, and model outputs are preserved. Reruns rebuild the separate merged outputs and reuse successful reviews; errors are retried. Changing the model, prompt, or HTML produces a new cache entry. Prefer a pinned model snapshot when available. A dry run rebuilds its output with original labels, so use a separate `--output-dir` if preserving an earlier reviewed export.

API implementation follows the [official Structured Outputs guide](https://developers.openai.com/api/docs/guides/structured-outputs).

### Limits, missing files, and API failures

`--limit 20` permits at most 20 new API attempts per run. `deferred_limit` means an eligible filing is waiting for the next run; it is not an error. Successful cached reviews are reused, so repeated runs advance through the remaining filings.

When cached HTML is absent or lacks an Item 2.04 heading, the reviewer uses `item_204_text` saved by the original classifier. Check `llm_input_scope` to distinguish a full filing from the extracted narrative. If neither source exists, it writes `fallback_missing_input` with an explicit conservative `MANUAL_REVIEW` explanation. The reviewer intentionally does not download missing filings. Recover missing files using the original downloader with the same date filters and a valid SEC user agent, then rerun LLM review if full-filing context is required.

On an HTTP rejection, the script records the API's error code/message and stops further API requests for that run. The first rejected record is `api_error`; other eligible records are `deferred_api_failure`. Completed reviews are still exported and cached. HTTP 429 can indicate exhausted quota (`insufficient_quota`) or temporary rate limits. Resolve billing/project quota for the former; wait and retry for the latter. Authentication/model/request errors also require correction before rerunning. Details are in `audit.json` under `api_stop_reason` and in the CSV `llm_error` column. No automatic retry loop consumes the pilot allowance.

See the [official API error guide](https://developers.openai.com/api/docs/guides/error-codes).

### SEC context and per-review logging

Both providers receive an explicit, paraphrased definition of Form 8-K Item 2.04 from the [SEC form](https://www.sec.gov/files/form8-k.pdf), plus examples that distinguish missed payments, realized acceleration, and hypothetical/technical events. Item 2.04 is broader than the study's qualifying-default definition; its presence alone must not produce a positive label. The prompt asks for issuer attribution, payment timing/grace periods, and any cure or waiver to be reflected in the explanation.

The console prints a start message before inference, then one compact line with the validated classification, event type, and certainty after each completed review. Full explanations and verbatim evidence are appended immediately to `review_log.jsonl` in the provider's output directory. On later runs, an existing decision for the same filing, provider, and model is loaded from `reviews/` without another model call and without a duplicate log entry. Legacy review files are recognized by their stored HTML hash. Use `--retry-fallbacks` to retry only decisions marked `fallback: true`; successful cached reviews remain untouched, and a successful retry replaces its fallback file. Use `--refresh` only when you intentionally want to rerun every stored decision. The two flags cannot be combined. Logs contain decision explanations, not hidden thinking output. Missing/failed reviews remain visible in the classifications exports and audit.

After a provider failure has been corrected, retry unresolved decisions with:

```bash
.venv/bin/python -m mcf.enrichment.item204.reviewers.ollama \
  --model gemma3:4b \
  --output-dir results/item_204_gemma4b_1_review \
  --retry-fallbacks
```

The current prompt/version (`item204-llm-v3-explicit-outcomes`) changes cache keys, so older reviews are regenerated on the next run. Earlier cached files remain intact. Every attempted filing now produces a one-line console/log outcome. Provider, validation, context, and missing-input failures become explicit conservative `MANUAL_REVIEW` records rather than disappearing. Model-added ellipses in evidence are accepted only when the remaining fragments can be mapped back to an exact source passage; unsupported quotes are discarded, and a resolved label still requires at least one verified quote. Test the new prompt with a small pilot before a full run.
