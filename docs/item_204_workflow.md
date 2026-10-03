# Item 2.04 candidate-event review

`classify_item_204.py` is separate from the current Item 1.03 inventory and model pipeline. It scans every main CIK submission file and its referenced historical archives, finds exact Item 2.04 filings in 8-K/8-K/A records, downloads primary-document HTML, and extracts the Item 2.04 narrative with Beautiful Soup.

## Install and run

```sh
.venv/bin/python -m pip install -r requirements-item204.txt

# Metadata-only inventory: no network requests.
.venv/bin/python classify_item_204.py \
  --submissions ../dataset/submissions \
  --output-dir results/item_204_review \
  --start 2011-01-01 --cutoff 2026-09-07 --discover-only

# First inspect a small downloaded pilot.
.venv/bin/python classify_item_204.py \
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

The classifier requires strong financial-default and realized-event evidence in the same sentence. It recognizes missed payments, unpaid principal/interest, realized acceleration, and initiated/completed enforcement. Hypothetical or negated sentences cannot qualify automatically; unresolved strong-default language stays `MANUAL_REVIEW`. Technical covenant breaches and benign redemption language can be `NON_DEFAULT` when no strong event evidence is present. JSONL preserves both raw regex matches and `qualifying_event_sentences`; `payment_default_evidence` now requires the same contextual checks. These conservative rules can miss real events in complex or multi-sentence narratives, so validate a manually reviewed sample before using labels. The audit records `item204-v4-payment-context`; rerun classification to refresh outputs using cached HTML.

## Using candidates in a future inventory

Run this as a one-time preprocessing stage before constructing a revised inventory. Keep all Item 2.04 filings in the audit, including co-filed Item 1.03 records. For additional filing candidates, review `QUALIFIED_DEFAULT` records where `prior_or_same_item_103` is false; do not filter on a later Item 1.03 date when constructing historical eligibility, since that uses future information.

Before changing labels, manually validate precision across classes and years, resolve incorporated-by-reference text, and deduplicate amendments/repeated reports of the same economic event. Preserve the filing availability date separately from the underlying event date. Define whether the new target is payment default, covenant default, acceleration, or a composite distress disclosure. Rebuild the panel, stage audit and models only after freezing that definition. The current script does not change existing inventories or training labels.

Item 2.04 includes triggering events that materially accelerate or increase financial obligations, which can extend beyond missed payments. Source: [SEC Form 8-K](https://www.sec.gov/files/form8-k.pdf).

Payment-failure verbs now require a financial object directly after them. Newlines and semicolons do not split event evidence away from a conditional clause. Disputed or alleged events require manual review. Explicit nonpayment (for example, “did not pay interest”) remains positive evidence; this differs from denying that a default occurred.
