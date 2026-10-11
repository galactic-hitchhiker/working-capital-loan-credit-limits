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

Qualifying disclosures no more than 90 days apart form one episode. The 90-day interval approximates one quarter: it groups follow-up filings about the same distress event and prevents decisions soon after a known disclosure from being treated as new, event-free prediction opportunities. Decisions during an episode and its 90-day quiet gap are excluded from prediction; later eligible decisions can predict a new episode. This is a pragmatic grouping rule, not an empirically established cure period or proof of cure.

Item 1.03 covers bankruptcy or receivership matters and can also include reorganization-related reporting. It can concern the registrant or its parent. A filing date is not necessarily the start of the underlying event or the date of a missed payment. [SEC, Form 8-K, Item 1.03](https://www.sec.gov/files/form8-k.pdf).

Let T be the start date of the next qualifying disclosure episode and t the decision date. For an eligible company-month, the positive label is:

$$ y_{i,t}=1 \quad \text{if} \quad t<T_i\leq t+60\ \text{calendar days}. $$

A zero means that no new qualifying episode occurs in this interval and that the issuer has a qualifying filing at or after the horizon. Qualifying follow-up forms are 10-K, 10-Q, 8-K and their amendments. This establishes observed reporting follow-up, not proof that the company did not experience distress. Unresolved Item 2.04-only records prevent a negative label where their status could change the outcome.

Decisions after the issuer's final qualifying filing are outside the observed reporting life.

Positive labels wait until the full horizon has elapsed. For negatives, availability is the day after the first qualifying follow-up filing at or after the horizon. Labels must be available before the study cutoff and before the next chronological modeling stage if used in an earlier stage.

This treatment removes 6,011 otherwise financially usable rows for insufficient issuer follow-up, 38,664 rows after unresolved payment disclosures, 1,458 during episode washout and 350 with unresolved payment evidence in the forward window. These categories reduce 611,705 usable feature rows to 565,222 labeled rows. Known disclosures remain relevant to policy hard stops.

## 3.4 Feature Construction

The predictive experiment uses twelve accounting measures. In the table below, each formula applies to one company at a monthly decision date $t$. Values indexed by $t$ are the latest eligible reported facts known before that decision, not necessarily values measured on the decision date. $CA$ means current assets, $CL$ current liabilities, $TA$ total assets, $L$ total liabilities, $Cash$ cash and cash equivalents, $NI$ net income and $OCF$ operating cash flow.

The subscript $t-12$ denotes a comparable balance-sheet date about twelve months earlier. The subscript $a$ denotes the latest available annual operating-cash-flow period, to which net income is matched. $\overline{TA}_a$ and $\overline{L}_a$ are the arithmetic means of opening and closing assets and liabilities for that period. The indicator $\mathbb{1}(\cdot)$ equals one when its condition holds and zero otherwise.

| Predictor | Formula | What it measures |
|---|---|---|
| Current ratio | $CA_t/CL_t$ | Current assets relative to current liabilities. A higher value indicates more short-term asset cover. |
| Cash to assets | $Cash_t/TA_t$ | The portion of the asset base reported as cash or cash equivalents; reported cash is not necessarily available for lending purposes. |
| Liabilities to assets | $L_t/TA_t$ | The share of assets financed by obligations rather than equity. |
| Asset growth, 12 months | $(TA_t-TA_{t-12})/TA_{t-12}$ | The percentage expansion or contraction of the balance sheet over about a year. Growth is not assumed to be beneficial. |
| Leverage change, 12 months | $L_t/TA_t-L_{t-12}/TA_{t-12}$ | Change in the total-liabilities-to-assets ratio over about a year; a positive value indicates more liabilities relative to assets. |
| Working capital to assets | $(CA_t-CL_t)/TA_t$ | The short-term funding surplus or shortfall scaled by company size. Negative values mean current liabilities exceed current assets. |
| Return on average assets (ROA) | $NI_a/\overline{TA}_a$ | Annual accounting profit or loss relative to average assets during the year. |
| Operating cash flow to average assets | $OCF_a/\overline{TA}_a$ | Annual operating cash generation or use relative to average assets. |
| Operating cash flow to average liabilities | $OCF_a/\overline{L}_a$ | Annual operating cash generation or use relative to average liabilities. This is not debt-service coverage. |
| Negative income | $\mathbb{1}(NI_a<0)$ | Whether the company reported an annual accounting loss, separate from the size of that loss. |
| Negative operating cash flow | $\mathbb{1}(OCF_a<0)$ | Whether operations used cash over the annual period. |
| Log assets | $\ln(TA_t)$ | Company size on a compressed scale, using total assets in US dollars. |

*Accounting predictors used in model fitting. Ratios with nonpositive denominators remain missing, as described in Section 3.5.*

Appendix A lists the underlying accounting fields, exact timing rules and model field names. These descriptions indicate what each constructed measure represents; they do not assign a causal effect or assume that a high or low value always has the same risk implication.

Current assets, current liabilities, total liabilities and cash are matched to the selected total-assets balance date. Direct Company Facts totals take priority. When a total is absent, the extractor can use reconciled SEC statement calculations or complete same-filing components; each derivation and its source remain in provenance. The 12-month change features use the closest comparable balance date 330–400 days earlier; prior assets and liabilities must share that date. Net income is matched to the latest available annual operating-cash-flow period. Opening assets and liabilities must refer to the day before that annual period begins, and closing values must match its end. The negative-income and negative-cash-flow indicators remain missing when their source flow is unavailable rather than treating missing values as zero.

Annual flows must span 330–400 days. This accommodates some fiscal-year variation while excluding ordinary quarterly and year-to-date flows. Revenue and operating cash flow used in the policy must have identical annual start and end dates.

These are last reported annual values. No trailing twelve-month series is reconstructed. Cumulative year-to-date figures are not added as if they were separate quarters.

Interest coverage is excluded because reliable construction requires further tag reconciliation. Asset growth and leverage change are included; industry and reporting age are audit fields.

## 3.5 Data Quality and Preprocessing

### 3.5.1 Observation Eligibility

A company-month must have positive total assets and a usable annual operating-cash-flow record. The balance-sheet period must end no more than 180 days before the decision date, and the annual-flow period no more than 540 days before it. These limits restrict the use of old financial information. Age is measured from the accounting period end; the separate filing-date rule in Section 3.2 determines whether the information was known at the decision date.

The following table shows how the candidate company-month grid becomes the labeled panel. Exclusions are applied in sequence, so each removed row is counted once here.

| Stage | Rows removed | Rows remaining |
|---|---:|---:|
| Candidate company-month grid | — | 1,958,220 |
| Exclude decisions outside observed reporting lives | 1,014,086 | 944,134 |
| Exclude missing, conflicting or stale required financial data, or nonpositive assets | 332,429 | 611,705 |
| Apply disclosure-episode and outcome-observability exclusions from Section 3.3 | 46,483 | 565,222 |

*Source: run 006 panel audit. Counts precede the chronological purging described in Chapter 4.*

### 3.5.2 Missing Predictors and Extreme Values

Passing the eligibility checks does not require every predictor to be observed. A company can have usable total assets and annual operating cash flow while lacking another accounting field or a comparable historical balance. Ratios also remain missing when their denominator is nonpositive. The table below reports missing values in the labeled panel before imputation.

| Predictor | Rows with a missing value | Share of labeled rows |
|---|---:|---:|
| Current ratio | 27,431 | 4.85% |
| Cash to assets | 51,043 | 9.03% |
| Liabilities to assets | 52,646 | 9.31% |
| Asset growth, 12 months | 26,304 | 4.65% |
| Leverage change, 12 months | 87,963 | 15.56% |
| Working capital to assets | 27,296 | 4.83% |
| Return on average assets (ROA) | 27,207 | 4.81% |
| Operating cash flow to average assets | 5,515 | 0.98% |
| Operating cash flow to average liabilities | 59,801 | 10.58% |
| Negative income | 22,284 | 3.94% |
| Negative operating cash flow | 0 | 0.00% |
| Log assets | 0 | 0.00% |

*Source: run 006 feature summary. Each percentage uses 565,222 labeled company-months as its denominator. A row can lack several predictors, so the counts overlap and must not be added to estimate excluded observations.*

The 12-month leverage change has the highest missing share. Its construction requires both assets and liabilities at two comparable balance dates. Log assets and the negative-operating-cash-flow indicator are complete because their source values are required for entry. Operating cash flow to average assets can still be missing when the matched opening or closing asset balance is unavailable, even though annual cash flow itself is observed. Appendix C reports the predictor distributions alongside these missing shares.

During model fitting, missing predictors are replaced with medians calculated from the fitting sample. An additional indicator records whether a value was missing when that predictor has missing values in the fitting sample. These transformations are learned within each fitting stage and applied unchanged to its later evaluation observations; Chapter 4 describes the procedure. Imputation supplies model inputs without establishing the missing accounting amounts.

Negative working capital, net income and operating cash flow are retained because they can describe financial weakness. Extreme observed ratios are also retained: the experiment neither drops a row solely for an unusually large ratio nor caps extreme values through winsorization. Timing and reconciliation checks therefore do not certify that every reported amount is economically plausible. Extreme ratios remain a data-quality limitation, particularly for the logistic models.

### 3.5.3 Inputs to the Credit-Limit Policy

The policy replay requires observed total assets, annual revenue, annual operating cash flow and reported cash. These amounts determine monetary limits, so missing required policy inputs lead to exclusion rather than replacement with model medians or zeros. Assets must be positive, revenue and cash must be nonnegative, and all four amounts must be finite. Negative operating cash flow remains permissible.

The replay draws from the usable financial snapshots in the evaluation period and can include known-disclosure cases that are excluded from predictive fitting but activate a policy hard stop. Its sample therefore differs from the labeled prediction sample. Chapter 7 reports its coverage and results separately.

## 3.6 Descriptive Analysis

Annual observation counts and positive labels vary substantially. Figure 6.1 shows this variation, and Appendix C gives the full annual table. These counts precede chronological purging; a December observation can refer to a disclosure in the following year.

Predictor percentiles, missingness and sector summaries describe the constructed sample. They are not population estimates for all US companies. Changing event shares also motivate the separate calibration and later evaluation periods.

## 3.7 Data Limitations

The main data limitations are incomplete accounting coverage, filing and taxonomy noise, and dependence on observed reporting activity. Unresolved Item 2.04 evidence removes some outcome windows, while the absence of independent review validation leaves classification error uncertain.

Freshness requirements can exclude companies with disrupted reporting. These exclusions and the use of current industry metadata limit how far the findings generalize beyond the observed sample. Chapter 8 discusses the implications for prediction and lending.
