# 3 Data and Target Definition

This chapter describes the SEC accounting data and disclosure labels used in run 006. The observation is a company at a monthly decision date.

## 3.1 Study Population and Observation Unit

The run 006 inventory contains 20,443 company-facts files. Each company is linked to its submissions history through its Central Index Key, or CIK. The screen requires at least one domestic periodic filing, complete referenced historical archives and a known current SIC code outside 6000–6999.

| Inventory screen | Companies |
|---|---:|
| Starting company-facts inventory | 20,443 |
| No domestic periodic filing | 5,090 |
| Current SIC in finance, insurance or real estate | 4,236 |
| Missing or zero SIC | 227 |
| Incomplete or inconsistent referenced archives | 11 |
| Candidate companies after screening | 10,879 |
| Companies contributing labeled observations | 8,780 |

The four inventory exclusions are mutually exclusive. Further losses reflect missing or stale financial information and unavailable outcome windows.

The unit is a company at the first day of a month. Decision dates run from January 2011 through December 2025. The completed panel has 565,222 labeled company-month observations before chronological purging. It contains 1,052 positive rows associated with 573 disclosure episodes in 487 companies.

Current ticker status is not required. The inventory nevertheless does not reconstruct a complete historical listing universe, and current SIC may differ from a company's historical classification.

## 3.2 Sources and Information Availability

The dataset combines SEC Company Facts, Financial Statement and Notes data, and submissions in one monthly company panel. Company Facts and Financial Statement and Notes data supply accounting information from corporate filings; submissions supply the filing history used to define disclosure outcomes and reporting follow-up. CIK identifies the company, while the accession number identifies the individual filing.

| Source | Information used in this study | Role in the panel |
|---|---|---|
| Company Facts | Accounting values under standard tags, units, reporting periods, filing dates and accession numbers | Provides the main histories of balance-sheet values and annual income, revenue and operating cash flow |
| Financial Statement and Notes data | Numeric statement facts, standard and custom tag definitions, presentation labels and calculation relationships | Supports identification and reconciliation of assets, liabilities, current assets, current liabilities and cash |
| Submissions | Filing forms, dates, accession numbers and reported item codes, including referenced historical archives | Identifies qualifying disclosures and the issuer's observed reporting history |

### 3.2.1 Why Both Accounting Sources Are Needed

Company Facts provides a convenient history of reported values organized by accounting concept. However, the SEC's XBRL APIs aggregate facts using non-custom taxonomies that apply to the whole filing entity. They do not provide the complete presentation and calculation structure of the statements. A required amount may therefore be reported in a filing without appearing as a usable value under the standard tag sought by the extractor. [SEC, EDGAR API documentation](https://www.sec.gov/search-filings/edgar-application-programming-interfaces).

This matters for financial-ratio construction. For example, a balance sheet may report individual liability components or a custom liabilities total without a usable standard `Liabilities` value. The extractor needs enough context to identify the intended total and avoid combining overlapping components. Missing a standard tag alone does not establish that the company failed to report the underlying amount.

The Financial Statement and Notes datasets provide tag definitions, statement labels and arithmetic relationships within filings alongside numeric values. These records allow the study to check what a reported line represents and how it relates to other amounts. The datasets are extracts from filings and can contain inconsistencies; they do not guarantee complete or accurate accounting information. [SEC, Financial Statement and Notes dataset documentation](https://www.sec.gov/dera/data/fsnds.pdf).

### 3.2.2 Combining the Sources in One Panel

The extraction procedure uses both accounting sources when constructing each company-month observation. Direct Company Facts totals take priority. Financial Statement and Notes records support a value when the required total can be identified from statement labels or reconciled from complete calculation components. For example, total liabilities can be derived from a liabilities-and-equity equation only when the relevant components are recognized and the reported equation reconciles. This supports the liabilities-to-assets, leverage-change and cash-flow-to-liabilities predictors.

The statement importer uses consolidated USD balance-sheet facts from domestic periodic filings. It matches them to exact reporting dates using Company Facts anchors from the same accession. Custom totals require agreement between tag and statement labels; incomplete or conflicting calculations remain unresolved. The procedure records the source and derivation of each accepted amount rather than summing all available components indiscriminately.

Although the source is named Financial Statement and Notes, its use here concerns numeric accounting facts and statement structure. Narrative note text is not a model predictor. Annual revenue, net income and operating cash flow use Company Facts records with exact annual start and end dates; the importer does not infer annual flows from the bulk statement dataset's quarter-count durations. Both accounting sources contribute to the same panel under common rules for currency, reporting period and information availability.

### 3.2.3 Information Availability and Provenance

The local SEC snapshot was extracted before run 006. The study cutoff is 7 September 2026. The inventory identified 2,287 qualifying Item 1.03 or reviewed Item 2.04 filing records before episode grouping. This count includes excluded issuers; it is not the number of model events. The main submissions record is combined with every historical file referenced by it.

Financial extraction primarily uses USD values under standard US-GAAP tags from Forms 10-K, 10-Q and their amendments, with the statement-based mappings described above. A fact becomes available on the calendar day after its filing date. The fiscal period, fiscal-year label and XBRL frame are not treated as publication dates.

At each decision, the extractor chooses the latest eligible reporting period and then the latest filing vintage already known. A later restatement can affect a later decision but cannot change an earlier snapshot. Conflicting totals at the selected period and filing vintage remain missing.

Every selected fact retains its tag, value, period, filing date and accession number. SHA-256 hashes record the input files. The faster incremental extractor follows the same rules as the reference extractor; their outputs are checked on constructed accounting cases and a real company history.

## 3.3 Outcome and Prediction Horizon

The target is a new disclosure episode. Every Form 8-K or 8-K/A with exact Item 1.03 qualifies. An Item 2.04-only filing qualifies when its review identifies an explicit missed debt principal or interest payment, assigns high certainty and provides supporting quotations.

Item 2.04 reviews were generated automatically by language models through OpenAI Batch and reused from saved results. Acceleration or enforcement alone, missing reviews and ambiguous records remain unresolved for this target. No independent human validation sample is documented in the saved run; the review's certainty flag is not a measured label-accuracy rate. Appendix B records the review models and provenance.

Qualifying disclosures no more than 90 days apart form one episode. Decisions during an episode and its 90-day quiet gap are excluded from prediction; later eligible decisions can predict a new episode. The gap is an operational rule, not proof of cure.

Item 1.03 covers bankruptcy or receivership matters and can also include reorganization-related reporting. It can concern the registrant or its parent. A filing date is not necessarily the start of the underlying event or the date of a missed payment. [SEC, Form 8-K, Item 1.03](https://www.sec.gov/files/form8-k.pdf).

Let T be the start date of the next qualifying disclosure episode and t the decision date. For an eligible company-month, the positive label is:

$$ y_{i,t}=1 \quad \text{if} \quad t<T_i\leq t+60\ \text{calendar days}. $$

A zero means that no new qualifying episode occurs in this interval and that the issuer has a qualifying filing at or after the horizon. Qualifying follow-up forms are 10-K, 10-Q, 8-K and their amendments. This establishes observed reporting follow-up, not proof that the company did not experience distress. Unresolved Item 2.04-only records prevent a negative label where their status could change the outcome.

Decisions after the issuer's final qualifying filing are outside the observed reporting life.

Positive labels wait until the full horizon has elapsed. For negatives, availability is the day after the first qualifying follow-up filing at or after the horizon. Labels must be available before the study cutoff and before the next chronological modeling stage if used in an earlier stage.

This treatment removes 6,011 otherwise financially usable rows for insufficient issuer follow-up, 38,664 rows after unresolved payment disclosures, 1,458 during episode washout and 350 with unresolved payment evidence in the forward window. These categories reduce 611,705 usable feature rows to 565,222 labeled rows. Known disclosures remain relevant to policy hard stops.

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

Current assets, current liabilities, total liabilities and cash are matched to the selected total-assets balance date. Direct Company Facts totals take priority. When a total is absent, the extractor can use reconciled SEC statement calculations or complete same-filing components; each derivation and its source remain in provenance. The 12-month change features use the closest comparable balance date 330–400 days earlier; prior assets and liabilities must share that date. Net income is matched to the latest available annual operating-cash-flow period. Opening assets and liabilities must refer to the day before that annual period begins, and closing values must match its end. The negative-income and negative-cash-flow indicators remain missing when their source flow is unavailable rather than treating missing values as zero.

Annual flows must span 330–400 days. This accommodates some fiscal-year variation while excluding ordinary quarterly and year-to-date flows. Revenue and operating cash flow used in the policy must have identical annual start and end dates.

These are last reported annual values. No trailing twelve-month series is reconstructed. Cumulative year-to-date figures are not added as if they were separate quarters.

Interest coverage is excluded because reliable construction requires further tag reconciliation. Asset growth and leverage change are included; industry and reporting age are audit fields.

## 3.5 Data Quality and Preprocessing

An observation needs positive total assets, a balance-sheet period no older than 180 days and an annual-flow period no older than 540 days. Age is measured from period end, not filing date. A usable annual operating-cash-flow record is required for the cash-flow predictors.

The candidate company-month grid contains 1,958,220 possible rows. Of these, 1,014,086 fall outside observed reporting lives and 332,429 lack sufficiently fresh required financial information. The remaining 611,705 rows have usable snapshots; outcome exclusions reduce these to 565,222 labeled rows.

Within the labeled panel, current ratio is missing in 27,431 rows, working capital to assets in 27,296 and liabilities to assets in 52,646. Log assets is available throughout because positive assets are an entry requirement. Chapter 4 describes fitting-only median imputation and missing-value indicators.

Ratios with nonpositive denominators remain missing. Negative working capital, net income and operating cash flow are retained. No observation is dropped merely because an observed financial ratio is unusually large.

Policy calculations use a stricter complete-input subset. Required revenue and cash amounts are not filled with model medians or silently replaced with zero. This produces a different sample for Chapter 7, whose coverage is reported separately.

## 3.6 Descriptive Analysis

Annual observation counts and positive labels vary substantially. Figure 6.1 shows this variation, and Appendix C gives the full annual table. These counts precede chronological purging; a December observation can refer to a disclosure in the following year.

Predictor percentiles, missingness and sector summaries describe the constructed sample. They are not population estimates for all US companies. Changing event shares also motivate the separate calibration and later evaluation periods.

## 3.7 Data Limitations

The main data limitations are incomplete accounting coverage, filing and taxonomy noise, and dependence on observed reporting activity. Unresolved Item 2.04 evidence removes some outcome windows, while the absence of independent review validation leaves classification error uncertain.

Freshness requirements can exclude companies with disrupted reporting. These exclusions and the use of current industry metadata limit how far the findings generalize beyond the observed sample. Chapter 8 discusses the implications for prediction and lending.
