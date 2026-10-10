# Run 004 feature coverage investigation

The main opportunities are accounting-component recovery and the annual cash-flow
eligibility gate. Merely adding similar-looking tags would mix accounting scopes.
This investigation preserves the original `results/run_004_recurrent_disclosures_initial` and creates a separate
rebuild at `results/run_004_liabilities_coverage/panel`.

## What is actually missing?

The inventory has 20,335 issuers, of which 10,881 are candidates. The other issuers
are excluded by the existing study screen: 4,982 have no domestic periodic filings,
4,232 fall in SIC 6000–6999, 228 have unknown SIC, and 12 have incomplete archives.
These are sample exclusions, not missing predictor cells.

Run 004 contains 563,607 labeled company-months from 8,770 issuers. Across its 12
predictors, **92.05% of cells are already observed**, but only 356,967 rows (63.34%)
have every predictor. Missingness is concentrated in a few features:

| Feature | Missing before | Missing after | Values recovered |
| --- | ---: | ---: | ---: |
| Liabilities / assets | 99,083 | 98,282 | 801 |
| 12-month leverage change | 130,556 | 130,224 | 332 |
| Operating cash flow / average liabilities | 102,998 | 102,643 | 355 |
| Return on average assets | 36,007 | 27,457 | 8,550 |
| Negative net income | 30,801 | 22,200 | 8,601 |

Cash / assets is missing in 50,766 rows and current ratio in 27,541; this change
does not fill those. The extractor already reconstructs unrestricted cash from
explicit components and liabilities from current plus noncurrent totals.

## Implemented recovery

Both the ordinary and incremental extractors now recover parent net income from:

- Consolidated `ProfitLoss` minus explicitly reported
  `NetIncomeLossAttributableToNoncontrollingInterest`.
- `NetIncomeLossAvailableToCommonStockholdersBasic` plus explicitly reported
  `PreferredStockDividendsAndOtherAdjustments`.

Components must match the exact flow period and accession and be available before
the decision date. Direct net income takes precedence. An absent adjustment is
never assumed to be zero. The formulas retain the existing parent-income definition;
`ProfitLoss` by itself would change that definition.

Total liabilities can also be recovered as reported liabilities-and-equity minus
consolidated permanent equity minus an **explicitly reported total temporary-equity
amount**, all for the same balance-sheet date and accession. Parent-only equity is
not substituted for consolidated equity. Negative permanent equity is valid; a
negative derived liability amount is rejected. Component provenance is retained.

The rebuild recovered **18,639 feature cells**, reduced net-income missingness from
5.47% to 3.94%, and increased complete rows to **363,033**, a gain of 6,066.
These are modest overall gains, concentrated in profitability. All 563,607 row keys,
labels, and previously observed predictor values were checked and remained identical.
Feature availability was checked against decision dates. No claim of improved
predictive performance is made; models have not been retrained on this rebuild.

## Largest remaining opportunity: liabilities

Among the 99,083 original missing-liability rows, **93,947 (94.82%)** have an
unambiguous same-accession liabilities-and-equity/equity pair:

- 32,523 have consolidated permanent equity.
- 61,424 have only parent equity available to this check, requiring noncontrolling
  interest reconciliation.
- Across these pairs, 20,310 rows have earlier or current standard-tag evidence of
  temporary/redeemable securities. The remaining 73,637 have no such standard-tag
  evidence; this does **not** establish that temporary equity is zero.

These counts are review opportunities, not safely recoverable totals. A naive
`assets - StockholdersEquity` fallback can count noncontrolling and temporary equity
as liabilities. In particular, this can distort distressed-company leverage.

The generated `liabilities_review_queue.csv` groups the opportunities into **32,856
issuer/period/accession/scope combinations**, ranks them by affected monthly rows,
and links to filing indexes. Use the original balance-sheet presentation and XBRL
calculation relationships to verify the equity components or recover a custom
liabilities total. Repeated monthly observations should share that extraction work.
The review queue refers to the original panel, so it also includes rows subsequently
filled by the strict fallback.

Company Facts alone cannot settle every case: the [SEC API documentation](https://www.sec.gov/search-filings/edgar-application-programming-interfaces)
states that its aggregated facts use non-custom taxonomies and apply to the entire
filing entity. Custom totals and statement relationships may require the original
filing/XBRL package. The available local dataset contains Company Facts and
submissions archives, not those full statement packages.

## Why whole company-months disappear

The rebuilt audit now explains the 335,246 financial-data exclusions. Reasons overlap:

| Reason | Excluded company-months |
| --- | ---: |
| Missing/conflicting annual operating cash flow | 195,465 |
| Stale annual operating cash flow | 105,211 |
| Missing/conflicting assets | 74,721 |
| Stale balance sheet | 84,299 |
| Nonpositive assets | 8,571 |

Annual operating cash flow is missing or stale in **89.69%** of financial-data
exclusions. The current panel requires it even when balance-sheet predictors could
be usable. The separate 1,013,505 months outside observed reporting life should not
be interpreted as feature-extraction failures.

The next ML-feed experiment should retain rows with fresh, positive assets even
when annual flows are unavailable, leaving unavailable/stale flow features missing.
Keep the policy-input eligibility check separate: a row usable for risk prediction
need not support a cash-flow-based credit-limit scenario. This changes the sample
definition, so compare it as a separate retrospective experiment, not a silent
replacement of run 004. The existing training pipeline already fits median
imputation and missingness indicators within training; zero-filling is unnecessary.

A second experiment should reconstruct TTM flows as annual + current YTD − prior
comparable YTD, with matched fiscal periods, accounting scope, units, and historical
filing availability. Alternatively expose YTD/quarterly flows as explicitly distinct
features. Do not multiply arbitrary YTD cash flow by four or substitute it into an
annual ratio. TTM can improve freshness but still requires sufficient source history;
it will not resolve every annual-flow exclusion. These sample/feature-definition
experiments are recommendations, not changes made by this patch.

## Reproduce and verify

Use a new output directory for each panel rebuild:

```sh
.venv/bin/python -m mcf.data.empirical panel \
  --dataset ../dataset \
  --inventory results/run_004_recurrent_disclosures_initial/inventory \
  --config results/run_004_recurrent_disclosures_initial/panel/design.json \
  --output-dir results/run_004_liabilities_coverage/panel

.venv/bin/python -m mcf.data.coverage \
  --panel results/run_004_recurrent_disclosures_initial/panel/panel.csv \
  --dataset ../dataset \
  --output results/run_004_liabilities_coverage/liabilities_review.json \
  --compare-panel results/run_004_liabilities_coverage/panel/panel.csv

.venv/bin/python -m unittest discover -s tests -q
```

Artifacts: rebuilt `panel.csv`, `features.csv`, source provenance and hashes;
`panel_audit.json` with exclusion reasons and derivation counts;
`liabilities_review.json`, `liabilities_review_queue.csv`, and `comparison.json`.
The comparison includes both panel hashes and rejects changes to existing values
or row labels. Validation: 148 tests passed (one local-data-dependent test skipped),
including filing-day availability, same-accession components, explicit adjustments,
temporary-equity handling, direct-value precedence, and agreement between extractors.
