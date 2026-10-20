# 3 Data and Target Definition

This chapter constructs monthly company observations, accounting predictors and disclosure labels from SEC filings. Because the data were created for regulatory reporting rather than credit scoring, reported values are not always complete or comparable.

## 3.1 Study Population and Observation Unit

The inventory contains 20,443 Company Facts files linked to submissions by Central Index Key (CIK). Screening requires a domestic periodic filing, complete referenced archives and a known current SIC outside 6000–6999.

| Inventory screen | Companies |
|---|---:|
| Starting company-facts inventory | 20,443 |
| No domestic periodic filing | 5,090 |
| Current SIC in finance, insurance or real estate | 4,236 |
| Missing or zero SIC | 227 |
| Incomplete or inconsistent referenced archives | 11 |
| Candidate companies after screening | 10,879 |
| Companies contributing labeled observations | 8,780 |

*Table 1. Company inventory screening.*

The exclusions are mutually exclusive. SIC 6000–6999 broadly covers finance, insurance and real estate, whose balance sheets require specialized measures absent from the twelve predictors. Further losses reflect unusable financial data or outcome windows. [SEC SIC code list](https://www.sec.gov/search-filings/standard-industrial-classification-sic-code-list).

For example, customer deposits are ordinary operating funding for banks, so leverage, liquidity and working-capital ratios have meanings unlike those for industrial companies. Applying the same feature definitions would make cross-company comparisons misleading.

The unit is a company on the first day of a month from January 2011 through December 2025. Before chronological purging, the panel has 565,222 labeled observations and 1,052 positive rows associated with 573 episodes in 487 companies. Ticker status is irrelevant, but the inventory is not a complete historical listing universe and current SIC may differ from historical classification.

## 3.2 Sources and Information Availability

The panel combines Company Facts, Financial Statement and Notes data, and submissions. CIK identifies a company and accession number a filing.

| Source | Information used in this study | Role in the panel |
|---|---|---|
| Company Facts | Accounting values under standard tags, units, reporting periods, filing dates and accession numbers | Provides the main histories of balance-sheet values and annual income, revenue and operating cash flow |
| Financial Statement and Notes data | Numeric statement facts, standard and custom tag definitions, presentation labels and calculation relationships | Supports identification and reconciliation of assets, liabilities, current assets, current liabilities and cash |
| Submissions | Filing forms, dates, accession numbers and reported item codes, including referenced historical archives | Identifies qualifying disclosures and the issuer's observed reporting history |

*Table 2. SEC data sources and their roles in the panel.*

### 3.2.1 Understanding Company Facts and Overlapping Filings

Company Facts organizes tagged values, units, reporting periods, filing dates, forms and accession numbers from 10-K, 10-Q and amended filings. Filings overlap: later reports may repeat comparative balances, and flow values may cover cumulative periods.

It is therefore a history of individual reported facts rather than a set of ready-made financial statements. A single economic amount may appear under several tags or in several filings, while an annual and a year-to-date flow can share the same end date but represent different durations. Selecting facts requires both filing metadata and the underlying reporting period.

Only public information is used. A value becomes available the day after filing. The extractor chooses the latest eligible reporting period and then its latest available filing version. Later amendments affect only later decisions, and conflicting values remain missing.

This treatment prevents restatements from rewriting the information available to an earlier lender. It also means that two observations with the same reporting period may legitimately differ if an amendment became public between their decision dates.

Because statements are quarterly or annual, the latest known value is carried forward between monthly decisions. Balance-sheet items may use annual or quarterly filings. Revenue, income and operating cash flow must cover approximately a full year, and overlapping quarterly or year-to-date flows are never added.

For example, a newly filed 10-Q can update quarter-end assets and cash for later monthly decisions while annual revenue and operating cash flow remain those from the latest eligible full-year period. Carry-forward represents the available information set. It does not claim that the underlying company was unchanged.

### 3.2.2 Why Both Accounting Sources Are Needed

Company Facts provides standardized histories and availability dates but may omit values reported under custom names. [SEC, EDGAR API documentation](https://www.sec.gov/search-filings/edgar-application-programming-interfaces). Financial Statement and Notes data retain statement rows and calculation relationships. This allows a missing total, notably **total liabilities**, to be identified under a custom label or recovered from complete, non-duplicated components. Values must match the same filing and reporting date. Reporting errors can remain. [SEC, Financial Statement and Notes dataset documentation](https://www.sec.gov/dera/data/fsnds.pdf).

The detailed data are used conservatively. A custom row is not accepted merely because its label resembles a desired concept, and a calculated total is accepted only when every required component is present and the recorded relationship balances. This prioritizes traceability over coverage.

### 3.2.3 Combining the Sources in One Panel

Company Facts is preferred. Detailed statements fill or check missing balance-sheet values. Reconstructed totals require every component and a balanced calculation, otherwise they remain missing. Annual revenue, income and operating cash flow come from Company Facts because it supplies exact period dates. Narrative notes are unused, and each accepted value retains its provenance.

This precedence rule avoids choosing opportunistically between sources after observing model outcomes. Provenance records include the accession, reporting date, filing date, tag or statement row and any calculation used.


## 3.3 Outcome and Prediction Horizon

For each company-month, the target asks whether a **new qualifying distress disclosure occurs within 60 days**. A negative label also requires sufficient later SEC reporting to observe the whole window.

Item 1.03 bankruptcy or receivership filings qualify. Item 2.04-only filings qualify only when an automated review finds clear evidence of missed principal or interest. Filing dates need not equal event dates. Reviews used language models through OpenAI Batch. Cases describing only acceleration or enforcement, lacking review or remaining unclear are unresolved. Without independent human validation, review confidence is not a measured accuracy rate. [SEC, Form 8-K](https://www.sec.gov/files/form8-k.pdf).

Item 1.03 may concern an issuer or its parent and includes different bankruptcy or receivership circumstances. Item 2.04 covers events that can accelerate or increase an obligation, but such events do not always arise from non-payment. Requiring explicit missed-payment evidence narrows the latter category while retaining the uncertainty of automated document interpretation.

Disclosures no more than 90 days apart form one episode. Company-months within an episode and the 90 days after its last filing are excluded from new-event prediction, preventing follow-up filings from becoming new events. The gap is operational, not evidence of recovery.

Without episode grouping, several filings about one restructuring could be counted as repeated independent failures and inflate apparent performance. Conversely, the chosen gap may join distinct problems or separate a prolonged one. It is a transparent rule rather than a clinical definition of resolution.

A negative label requires a later 10-K, 10-Q or 8-K at or beyond the window's end. It confirms observable follow-up, not absence of distress. The label becomes available only after that filing and must precede the study cutoff and the next modeling stage, preventing future information from entering earlier decisions.

Rows after an issuer's final observed filing cannot safely be labeled negative because silence may reflect deregistration, reporting disruption or an unobserved event. The follow-up rule reduces this error at the cost of excluding some otherwise financially usable observations.

The labeling rules reduce 611,705 financially usable company-months to 565,222 labeled observations:

| Reason for removal | Company-months |
|---|---:|
| Not enough later SEC reporting | 6,011 |
| Occurred after an unresolved payment disclosure | 38,664 |
| Fell within an existing episode or its 90-day quiet period | 1,458 |
| Contained unresolved payment evidence in the next 60 days | 350 |

*Table 3. Company-months removed by the outcome-labeling rules.*

These outcomes are unreliable and excluded, although a disclosure already known on the decision date can still trigger a policy hard stop.

## 3.4 Feature Construction

The predictive experiment uses twelve features covering liquidity, leverage, financial change, profitability, cash generation and size. In the formulas below, $$CA$$ is current assets, $$CL$$ current liabilities, $$TA$$ total assets, $$L$$ total liabilities, $$Cash$$ cash and cash equivalents, $$NI$$ net income and $$OCF$$ operating cash flow. Values at $$t$$ are the latest known at the monthly decision date. The notation $$t-12$$ denotes the closest comparable balance about one year earlier, and $$a$$ denotes the latest complete annual period. Average assets and liabilities use the beginning and end of that period.

| Feature | Formula | Interpretation and expected relationship with risk |
|---|---|---|
| Current ratio | $$CA_t/CL_t$$ | Short-term resources relative to obligations. Lower values can indicate payment pressure, although inventory and receivable quality matter. |
| Cash to assets | $$Cash_t/TA_t$$ | Immediate liquidity buffer. Higher values generally suggest lower risk unless cash is restricted or operationally necessary. |
| Liabilities to assets | $$L_t/TA_t$$ | Overall obligations and equity buffer. Higher values generally suggest greater risk, subject to industry differences. |
| Asset growth, 12 months | $$(TA_t-TA_{t-12})/TA_{t-12}$$ | Captures expansion, contraction, acquisitions or asset sales. Either rapid growth or contraction can be adverse, so no single direction is assumed. |
| Change in liabilities to assets | $$L_t/TA_t-L_{t-12}/TA_{t-12}$$ | Measures the change in leverage. An increase generally suggests higher risk. |
| Working capital to assets | $$(CA_t-CL_t)/TA_t$$ | Short-term surplus or shortage relative to company size. Larger positive values generally suggest lower risk. |
| Return on average assets | $$NI_a/\overline{TA}_a$$ | Accounting profitability. Low or negative returns generally suggest higher risk, but profit need not imply cash generation. |
| Operating cash flow to average assets | $$OCF_a/\overline{TA}_a$$ | Operating cash generation relative to assets. Low or negative values can indicate cash pressure. |
| Operating cash flow to average liabilities | $$OCF_a/\overline{L}_a$$ | Cash generation relative to obligations. This is not debt-service coverage because scheduled principal and interest are unavailable. |
| Negative income | $$\mathbb{1}(NI_a<0)$$ | Captures the loss threshold separately from return on assets. A value of one generally suggests higher risk. |
| Negative operating cash flow | $$\mathbb{1}(OCF_a<0)$$ | Identifies operations that consume cash, while allowing that one negative year may reflect temporary working-capital investment. |
| Log assets | $$\ln(TA_t)$$ | Controls for company size on a compressed scale. Larger firms may have diversification and funding advantages, but are not necessarily safer. |

*Table 4. Accounting predictors, definitions and expected relationships with risk.*

Expected directions are economic priors, not causal claims. Ratio components use compatible dates and periods. Quarterly cumulative values are not added and missing values are not zeroed. Interest coverage is excluded because SEC tags did not support a consistent calculation. Industry and reporting age are audit fields, not predictors.

Average assets and liabilities use the beginning and end of the relevant annual period. Twelve-month changes use the closest sufficiently comparable prior balance rather than assuming every company files on identical calendar dates. Denominators that are zero or economically invalid produce missing ratios instead of extreme artificial values.

## 3.5 Data Quality and Preprocessing

Eligibility and missing-value rules address incomplete SEC reporting.

### 3.5.1 Which Company-Months Are Included

A company-month enters the labeled dataset only when:

- the company is still within its observed SEC reporting history
- total assets are available and greater than zero
- annual operating cash flow is available
- the latest balance sheet is no more than 180 days old
- the latest annual cash-flow period ended no more than 540 days earlier
- the 60-day outcome can be determined using the rules in Section 3.3.

The age limits exclude stale statements. Sequential filters produce the following counts:

They are applied in order, so every removed row appears once. The reporting-history screen is separate from financial freshness: a company can remain an SEC filer yet lack the required recent accounting inputs.

| Filter | Rows removed | Rows remaining |
|---|---:|---:|
| Initial company-month grid | Not applicable | 1,958,220 |
| Remove months outside each company's observed reporting history | 1,014,086 | 944,134 |
| Remove months without usable and sufficiently recent required financial data | 332,429 | 611,705 |
| Remove months whose 60-day outcome cannot be labeled reliably | 46,483 | 565,222 |

*Table 5. Sequential company-month filtering.*

*Source: primary model experiment panel audit. These counts are calculated before the later time-based filtering described in Chapter 4.*

### 3.5.2 Missing Feature Values

Included rows may still lack individual predictors. Ratios are also missing when denominators are non-positive.

| Feature | Missing rows | Share of 565,222 labeled rows |
|---|---:|---:|
| Current ratio | 27,431 | 4.85% |
| Cash to assets | 51,043 | 9.03% |
| Liabilities to assets | 52,646 | 9.31% |
| Asset growth, 12 months | 26,304 | 4.65% |
| Leverage change, 12 months | 87,963 | 15.56% |
| Working capital to assets | 27,296 | 4.83% |
| Return on average assets | 27,207 | 4.81% |
| Operating cash flow to average assets | 5,515 | 0.98% |
| Operating cash flow to average liabilities | 59,801 | 10.58% |
| Negative income | 22,284 | 3.94% |
| Negative operating cash flow | 0 | 0.00% |
| Log assets | 0 | 0.00% |

*Table 6. Missing values among the twelve model features.*

*A company-month can be missing more than one feature, so these counts must not be added together.*

Leverage change has most missingness because it needs assets and liabilities at two dates. Training-sample medians replace missing predictors, missingness indicators preserve that fact, and the fitted medians are reused later. This enables modeling rather than estimating the missing accounting value. Negative amounts and extreme ratios are retained, leaving logistic models more sensitive to outliers.

Re-estimating a median on later data would leak distributional information across time, so every chronological fold fits its own preprocessing. Missingness indicators also allow a model to distinguish an observed median-like value from an imputed one, although they may capture reporting conventions rather than financial condition.

### 3.5.3 Data Required for the Credit-Limit Policy

The credit-limit calculation has stricter requirements than the prediction model. It needs observed values for:

- total assets
- annual revenue
- annual operating cash flow
- cash.

Because these inputs determine money, none is imputed. Assets must be positive. Revenue and cash must be non-negative, while operating cash flow may be negative. The policy sample can include a company whose known disclosure triggers a zero limit even though it is ineligible for new-event prediction.

This stricter rule makes the policy sample smaller and different from the modeling sample. Substituting a median or zero would create a fictitious dollar capacity, whereas retaining negative operating cash flow is necessary for genuine weak-company cases.

## 3.6 Data Limitations

Quarterly or annual values repeat between monthly decisions, hiding interim changes. Accounting differences and reporting errors remain despite statement reconciliation. The outcome is a disclosure proxy, Item 1.03 is heterogeneous, Item 2.04 review lacks independent validation, and disrupted reporters may be excluded. Results therefore concern the defined disclosure, not exact default probability.
