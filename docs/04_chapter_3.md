# 3 Data and Target Definition

This chapter describes the actual dataset used for training and testing. All financial observations and outcome labels come from the supplied local SEC company-facts and submissions files. Synthetic data is used only in separate software tests.

## 3.1 Study Population and Observation Unit

The starting inventory contains 20,335 company-facts files. Each company is linked to its submissions history through its Central Index Key, or CIK. The screen requires at least one domestic periodic filing, complete referenced historical archives and a known current SIC code outside 6000–6999.

| Inventory screen | Companies |
|---|---:|
| Starting company-facts inventory | 20,335 |
| No domestic periodic filing | 4,982 |
| Current SIC in finance, insurance or real estate | 4,232 |
| Missing or zero SIC | 228 |
| Incomplete or inconsistent referenced archives | 12 |
| Candidate companies after screening | 10,881 |
| Companies contributing labeled observations | 9,075 |

The four exclusion categories are mutually exclusive under the implemented screen order. The final reduction also reflects missing or stale financial information and unavailable outcome windows.

The unit is a company at the first day of a month. Decision dates run from January 2011 through December 2025. The completed panel has 588,111 labeled company-month observations before chronological purging. It contains 875 positive rows associated with 472 distinct first-disclosure events.

Current ticker status is not a sample requirement. This avoids deliberately selecting only companies that remain listed. Nevertheless, the local company-facts inventory does not establish a complete historical listing universe. Current SIC is also a retrospective screen rather than a point-in-time industry classification.

## 3.2 Sources and Information Availability

Company facts provide structured accounting values, units, reporting periods and filing references. Submissions provide filing forms, filing dates, accession numbers and reported item codes. The main submission record is combined with every historical file referenced by it. [SEC, EDGAR API documentation](https://www.sec.gov/search-filings/edgar-application-programming-interfaces).

The local data was downloaded and extracted in September 2026. The study cutoff is 7 September 2026. The inventory identified 1,915 Item 1.03 filing records across all company-facts issuers. This count includes repeat disclosures and excluded sectors; it is not the number of model events.

Financial extraction uses USD values under standard US-GAAP tags from Forms 10-K, 10-Q and their amendments. A fact becomes available on the calendar day after its filing date. The fiscal period, fiscal-year label and XBRL frame are not treated as publication dates.

At each decision, the extractor chooses the latest eligible reporting period and then the latest filing vintage already known. A later restatement can affect a later decision but cannot change an earlier snapshot. Conflicting totals at the selected period and filing vintage remain missing.

Every selected fact retains its tag, value, period, filing date and accession number. SHA-256 hashes record the input files. The faster incremental extractor follows the same rules as the reference extractor; their outputs are checked on constructed accounting cases and a real company history.

## 3.3 Outcome and Prediction Horizon

The target is the first recorded Form 8-K or 8-K/A filing whose item list includes Item 1.03. The earliest filing date in the supplied combined history defines the event date. Subsequent records do not create additional first events.

Item 1.03 covers bankruptcy or receivership matters and can also include reorganization-related reporting. It can concern the registrant or its parent. A first record in the supplied history is therefore not necessarily the start of bankruptcy, and its filing date is not a payment-default date. [SEC, Form 8-K, Item 1.03](https://www.sec.gov/files/form8-k.pdf).

Let T be the first recorded disclosure date and t the decision date. The positive label is:

$$ y_{i,t}=1 \quad \text{if} \quad t<T_i\leq t+60\ \text{calendar days}. $$

A zero means that no first recorded disclosure occurs in this interval and that the issuer has a qualifying filing at or after the horizon. Qualifying follow-up forms are 10-K, 10-Q, 8-K and their amendments. This establishes observed reporting follow-up, not proof that the company did not experience any economic distress.

Decisions on or after the first disclosure are excluded from the predictive sample. The study does not model re-entry after restructuring. Decisions after the issuer's final qualifying filing are also outside the observed reporting life.

Positive labels wait until the full horizon has elapsed. For negatives, availability is the day after the first qualifying follow-up filing at or after the horizon. Labels must be available before the study cutoff and before the next chronological modeling stage if used in an earlier stage.

This treatment removes 6,237 otherwise financially usable rows for insufficient issuer follow-up. Another 15,481 usable feature rows are on or after the first disclosure and are excluded from prediction. These post-disclosure rows may remain relevant to policy hard stops.

The target is an observed reporting proxy. An absent item code cannot prove the absence of legal default, and historical metadata may contain errors or omissions. The findings therefore apply to the specified SEC disclosure outcome.

## 3.4 Feature Construction

The predictive experiment uses twelve measures:

$$ \operatorname{CurrentRatio}_{i,t}=\frac{CA_{i,t}}{CL_{i,t}}. $$

$$ \operatorname{CashToAssets}_{i,t}=\frac{CashAndEquivalents_{i,t}}{TA_{i,t}}. $$

$$ \operatorname{LiabilitiesToAssets}_{i,t}=\frac{L_{i,t}}{TA_{i,t}}. $$

$$ \operatorname{AssetGrowth12m}_{i,t}=\frac{TA_{i,t}-TA_{i,t-12}}{TA_{i,t-12}}. $$

$$ \operatorname{LeverageChange12m}_{i,t}=\frac{L_{i,t}}{TA_{i,t}}-\frac{L_{i,t-12}}{TA_{i,t-12}}. $$

$$ \operatorname{WorkingCapitalToAssets}_{i,t}=\frac{CA_{i,t}-CL_{i,t}}{TA_{i,t}}. $$

$$ \operatorname{ROA}_{i,t}=\frac{NI_{i,\mathrm{annual}}}{(TA_{i,\mathrm{opening}}+TA_{i,\mathrm{closing}})/2}. $$

$$ \operatorname{OCFToAssets}_{i,t}=\frac{OCF_{i,\mathrm{annual}}}{(TA_{i,\mathrm{opening}}+TA_{i,\mathrm{closing}})/2}. $$

$$ \operatorname{OCFToLiabilities}_{i,t}=\frac{OCF_{i,\mathrm{annual}}}{(L_{i,\mathrm{opening}}+L_{i,\mathrm{closing}})/2}. $$

$$ \operatorname{NegativeIncome}_{i,t}=\mathbb{1}(NI_{i,\mathrm{annual}}<0). $$

$$ \operatorname{NegativeOCF}_{i,t}=\mathbb{1}(OCF_{i,\mathrm{annual}}<0). $$

$$ \operatorname{LogAssets}_{i,t}=\ln(TA_{i,t}). $$

Current assets, current liabilities, total liabilities and cash are matched to the selected total-assets balance date. Total liabilities use the direct `Liabilities` concept when available. Otherwise, the extractor adds `LiabilitiesCurrent` and `LiabilitiesNoncurrent` only when both come from the same filing accession and are nonnegative; the derivation and both components remain in provenance. The 12-month change features use the closest comparable balance date 330–400 days earlier; prior assets and liabilities must share that date. Net income is matched to the latest available annual operating-cash-flow period. Opening assets and liabilities must refer to the day before that annual period begins, and closing values must match its end. The negative-income and negative-cash-flow indicators remain missing when their source flow is unavailable rather than treating missing values as zero.

Annual flows must span 330–400 days. This accommodates some fiscal-year variation while excluding ordinary quarterly and year-to-date flows. Revenue and operating cash flow used in the policy must have identical annual start and end dates.

These are last reported annual values. No trailing twelve-month series is reconstructed. Cumulative year-to-date figures are not added as if they were separate quarters.

Interest coverage and growth remain outside the fitted specification because reliable construction requires additional tag reconciliation and period handling. Industry and reporting age are audit fields, not model inputs.

## 3.5 Data Quality and Preprocessing

An observation needs positive total assets, a balance-sheet period no older than 180 days and an annual-flow period no older than 540 days. Age is measured from period end, not filing date. A usable annual operating-cash-flow record is required for the cash-flow predictors.

The candidate company-month grid contains 1,958,580 possible rows. Of these, 1,013,505 fall outside observed reporting lives and 335,246 lack sufficiently fresh required financial information. The remaining 609,829 rows have usable snapshots; outcome exclusions reduce these to 588,111 labeled rows.

Within the labeled panel, current ratio is missing in 28,767 rows, working capital to assets in 28,649 and return on average assets in 38,911. Log assets is available throughout because positive assets are an entry requirement. Chapter 4 describes training-only median imputation and missing-value indicators.

Ratios with nonpositive denominators remain missing. Negative working capital, net income and operating cash flow are retained. No observation is dropped merely because an observed financial ratio is unusually large.

Policy calculations use a stricter complete-input subset. Required revenue and cash amounts are not filled with model medians or silently replaced with zero. This produces a different sample for Chapter 7, whose coverage is reported separately.

## 3.6 Descriptive Analysis

The number of observations and positive labels varies substantially over time:

| Decision year | Labeled rows | Positive rows |
|---|---:|---:|
| 2011 | 10,324 | 10 |
| 2012 | 39,910 | 38 |
| 2013 | 49,198 | 45 |
| 2014 | 46,105 | 57 |
| 2015 | 37,554 | 50 |
| 2016 | 30,456 | 58 |
| 2017 | 27,391 | 44 |
| 2018 | 33,750 | 52 |
| 2019 | 41,742 | 71 |
| 2020 | 42,945 | 114 |
| 2021 | 44,151 | 11 |
| 2022 | 48,408 | 37 |
| 2023 | 48,496 | 114 |
| 2024 | 45,039 | 114 |
| 2025 | 42,642 | 60 |

These counts precede chronological purging. Positive rows are decision-date labels, so a row in December can refer to a disclosure in the following year.

The changing counts show why a single overall event rate is insufficient. A model calibrated in a higher-event period may overstate probabilities in a later lower-event period. This possibility is examined in Chapter 6.

The supplementary report provides predictor percentiles, missingness, correlations, sector counts and annual event shares. These descriptions concern the constructed sample; they should not be interpreted as population estimates for all US companies.

## 3.7 Data Limitations

There are five main limitations. First, the target records disclosures rather than verified legal-event onset or facility payment default. Second, snapshot coverage depends on standard tags, USD reporting and freshness rules, which may exclude companies with unusual accounting or disrupted reporting.

Third, complete follow-up is conditional on observed filing activity. Companies that disappear from the reporting record without a usable disclosure cannot automatically be labeled negative. Fourth, current industry metadata and the downloaded inventory do not fully reconstruct historical sample membership.

Finally, financial statements do not establish cash eligibility, payments due in the next 60 days, facility utilization or recoveries. The policy analysis must keep these assumptions visible. These limitations affect both external validity and the strength of conclusions about lending.

File references: mcf/data/empirical.py, mcf/data/sec.py, mcf/data/point_in_time.py, issuer_inventory.csv, disclosure_events.csv, inventory_audit.json, panel_audit.json, feature_provenance.jsonl, panel.csv, features.csv, 11_appendix_a_variable_dictionary.md.
