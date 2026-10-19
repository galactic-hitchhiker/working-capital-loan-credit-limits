# 3 Data and Target Definition

The U.S. Securities and Exchange Commission (SEC) oversees US securities markets and corporate reporting by public issuers. Companies submit periodic financial reports and reports of important events through its Electronic Data Gathering, Analysis, and Retrieval system (EDGAR). These public filings contain accounting values, filing dates and information about disclosed corporate events.

This chapter describes how SEC data are used to construct the accounting predictors and disclosure labels for the primary model experiment. The data were created for regulatory reporting rather than credit scoring, so not every reported value is complete, economically comparable or suitable for the model. The observation is a company at a monthly decision date.

## 3.1 Study Population and Observation Unit

The inventory for the primary model experiment contains 20,443 company-facts files. Each company is linked to its submissions history through its Central Index Key, or CIK. The screen requires at least one domestic periodic filing, complete referenced historical archives and a known current SIC code outside 6000–6999.

| Inventory screen | Companies |
|---|---:|
| Starting company-facts inventory | 20,443 |
| No domestic periodic filing | 5,090 |
| Current SIC in finance, insurance or real estate | 4,236 |
| Missing or zero SIC | 227 |
| Incomplete or inconsistent referenced archives | 11 |
| Candidate companies after screening | 10,879 |
| Companies contributing labeled observations | 8,780 |

The four inventory exclusions are mutually exclusive. SIC codes 6000–6999 broadly cover finance, insurance and real-estate companies. These companies are excluded because their balance sheets differ from those of ordinary operating companies: for example, deposits are normal business funding for banks, so leverage, liquidity and working-capital ratios have different meanings. Their assessment requires specialized measures that are not included among the twelve predictors. Further losses reflect missing or stale financial information and unavailable outcome windows. [SEC SIC code list](https://www.sec.gov/search-filings/standard-industrial-classification-sic-code-list).

The unit is a company at the first day of a month. Decision dates run from January 2011 through December 2025. The completed panel has 565,222 labeled company-month observations before chronological purging. It contains 1,052 positive rows associated with 573 disclosure episodes in 487 companies.

Current ticker status is not required. The inventory nevertheless does not reconstruct a complete historical listing universe, and current SIC may differ from a company's historical classification.

## 3.2 Sources and Information Availability

This study combines three SEC sources in one monthly company panel: Company Facts, Financial Statement and Notes data, and submissions. Company Facts and Financial Statement and Notes data supply accounting information from corporate filings, while submissions provide the filing history used to define disclosure outcomes and reporting follow-up. The Central Index Key (CIK) identifies the company, while the accession number identifies an individual filing.

| Source | Information used in this study | Role in the panel |
|---|---|---|
| Company Facts | Accounting values under standard tags, units, reporting periods, filing dates and accession numbers | Provides the main histories of balance-sheet values and annual income, revenue and operating cash flow |
| Financial Statement and Notes data | Numeric statement facts, standard and custom tag definitions, presentation labels and calculation relationships | Supports identification and reconciliation of assets, liabilities, current assets, current liabilities and cash |
| Submissions | Filing forms, dates, accession numbers and reported item codes, including referenced historical archives | Identifies qualifying disclosures and the issuer's observed reporting history |

### 3.2.1 Understanding Company Facts and Overlapping Filings

Company Facts is an SEC dataset that organizes individual accounting values from a company's filings into one history. A record contains the accounting tag, value, unit, reporting period, filing date, form and accession number. It is therefore not a separate financial statement: it is a collection of values taken from statements filed over time.

The dataset includes annual Forms 10-K, quarterly Forms 10-Q and their amendments. These filings can overlap. A later filing may repeat an earlier balance for comparison, while quarterly revenue, income and cash-flow amounts may cover cumulative parts of a year. Such records cannot simply be added together.

For each monthly decision date, the study uses only filings that were already public; a value becomes usable on the day after filing. For each accounting item, the extractor first selects the latest eligible reporting period and then the latest filing version available for that period. If an amendment is filed later, it can change later monthly observations but cannot rewrite earlier ones. Conflicting values from the same selected filing date remain missing rather than being chosen arbitrarily.

The panel has one decision date per month, but companies normally publish financial statements only quarterly or annually. Fresh accounting data are therefore not available every month. The latest known value is carried forward until a newer filing becomes available, so the same assets, liabilities or cash value may appear in several consecutive monthly observations. This is intentional: it represents what a lender could have known at each date instead of inventing monthly updates. Balance-sheet values can come from annual or quarterly filings, while revenue, net income and operating cash flow are restricted to periods covering approximately a full year. Quarterly and cumulative year-to-date flows are not added together.

For example, after a company files a 10-Q, the project can use its newer quarter-end assets for subsequent monthly decisions. However, it continues to use the latest complete annual revenue and operating cash flow instead of combining the overlapping quarterly amounts.

### 3.2.2 Why Both Accounting Sources Are Needed

The two accounting sources provide different parts of the same picture. Company Facts works like a standardized summary of a company's reported numbers. It makes values easier to follow over time and records when each value was reported. However, it does not preserve the complete financial statement and may miss an amount when a company reports it under a different name. [SEC, EDGAR API documentation](https://www.sec.gov/search-filings/edgar-application-programming-interfaces).

The Financial Statement and Notes data are closer to the original statements. They retain the names of statement rows and information about how amounts form a total. For example, Company Facts may not show a standard total for liabilities even though the balance sheet reports that total under another name or lists the parts needed to calculate it. The detailed statement data help identify the correct amount without adding the same item twice.

Using both sources combines the advantages of each one. Company Facts provides the consistent history, while the Financial Statement and Notes data help explain, check or fill values that are missing or unclear. A value is used only when it can be linked to the same filing and reporting date and passes the checks described below. Both sources can still contain reporting errors or inconsistencies. [SEC, Financial Statement and Notes dataset documentation](https://www.sec.gov/dera/data/fsnds.pdf).

A concrete example is **total liabilities**. When Company Facts does not contain a usable standard value for total liabilities, the detailed statement data can provide the reported total under a custom name or the complete balance-sheet components needed to recover it. This recovered value can then be used to calculate ratios that compare liabilities with assets or cash flow.

### 3.2.3 Combining the Sources in One Panel

Each monthly observation starts with Company Facts. When Company Facts contains a usable value, that value is preferred. The Financial Statement and Notes data are used only to fill or check missing balance-sheet values, such as total liabilities.

Before a statement value is accepted, it must belong to the same company, filing and reporting date. If a total is calculated from smaller parts, all required parts must be present and the calculation must balance. Unclear or conflicting values remain missing rather than being guessed.

Annual revenue, net income and operating cash flow come from Company Facts because it provides their exact annual start and end dates. Narrative text from the notes is not used by the model. The source and calculation of every accepted value are recorded so that the result can be checked later.


## 3.3 Outcome and Prediction Horizon

For every company-month, the model asks a simple question: **will the company make a new qualifying distress disclosure within the next 60 days?** A disclosure within this period produces a positive label (`1`). A negative label (`0`) means that no qualifying disclosure was observed during the period and that enough later SEC reporting exists to observe the complete 60 days.

Two types of Form 8-K disclosure can qualify. Item 1.03 reports bankruptcy or receivership matters, including some reorganizations. It may concern the company or its parent, and the filing date is not necessarily the date on which the financial problem began. Item 2.04 covers events that can accelerate or increase a financial obligation. An Item 2.04-only filing is included here only when its review finds clear evidence of a missed principal or interest payment. [SEC, Form 8-K, Item 1.03](https://www.sec.gov/files/form8-k.pdf).

The Item 2.04 reviews were produced by language models through OpenAI Batch. Filings that mention only acceleration or enforcement, lack a review, or remain unclear are treated as unresolved. The model's confidence description is not a measured accuracy rate because no separate human validation sample was recorded. Appendix A provides the reproduction and review details.

Several related filings may describe the same financial problem. Qualifying disclosures no more than 90 days apart are therefore grouped into one episode. Company-months during that episode and for 90 days after its last disclosure are not used to predict another event. This prevents follow-up filings about an already known problem from being counted as new events. The 90-day rule is a practical assumption, not proof that the company recovered afterward.

A negative label requires evidence that the company continued filing with the SEC until at least the end of the 60-day window. The evidence can be a later Form 10-K, 10-Q or 8-K, including an amendment. If the decision date falls after the company's final qualifying filing, there is not enough reporting history to determine whether no event occurred, so the row is left unlabeled. This confirms observable SEC follow-up, not that the company was free from financial distress.

Labels are used only after their complete 60-day window can be observed. A negative label becomes available on the day after the first qualifying follow-up filing at or beyond the end of that window. All labels must be available before the study cutoff and, for an earlier modeling stage, before the next chronological stage begins. These rules prevent the model from using future information.

The labeling rules reduce 611,705 financially usable company-months to 565,222 labeled observations:

| Reason for removal | Company-months |
|---|---:|
| Not enough later SEC reporting | 6,011 |
| Occurred after an unresolved payment disclosure | 38,664 |
| Fell within an existing episode or its 90-day quiet period | 1,458 |
| Contained unresolved payment evidence in the next 60 days | 350 |

These rows are excluded because their outcomes cannot be labeled reliably. However, a disclosure already known on the decision date can still stop the credit policy from offering a limit.

## 3.4 Feature Construction

The predictive experiment uses twelve features covering liquidity, leverage, financial change, profitability, cash generation and size. In the formulas below, $$CA$$ is current assets, $$CL$$ current liabilities, $$TA$$ total assets, $$L$$ total liabilities, $$Cash$$ cash and cash equivalents, $$NI$$ net income and $$OCF$$ operating cash flow. Values at $$t$$ are the latest known at the monthly decision date; $$t-12$$ denotes the closest comparable balance about one year earlier; and $$a$$ denotes the latest complete annual period. Average assets and liabilities use the beginning and end of that period.

| Feature | Formula | Interpretation and expected relationship with risk |
|---|---|---|
| Current ratio | $$CA_t/CL_t$$ | Short-term resources relative to obligations; lower values can indicate payment pressure, although inventory and receivable quality matter. |
| Cash to assets | $$Cash_t/TA_t$$ | Immediate liquidity buffer; higher values generally suggest lower risk unless cash is restricted or operationally necessary. |
| Liabilities to assets | $$L_t/TA_t$$ | Overall obligations and equity buffer; higher values generally suggest greater risk, subject to industry differences. |
| Asset growth, 12 months | $$(TA_t-TA_{t-12})/TA_{t-12}$$ | Captures expansion, contraction, acquisitions or asset sales. Either rapid growth or contraction can be adverse, so no single direction is assumed. |
| Change in liabilities to assets | $$L_t/TA_t-L_{t-12}/TA_{t-12}$$ | Measures the change in leverage; an increase generally suggests higher risk. |
| Working capital to assets | $$(CA_t-CL_t)/TA_t$$ | Short-term surplus or shortage relative to company size; larger positive values generally suggest lower risk. |
| Return on average assets | $$NI_a/\overline{TA}_a$$ | Accounting profitability; low or negative returns generally suggest higher risk, but profit need not imply cash generation. |
| Operating cash flow to average assets | $$OCF_a/\overline{TA}_a$$ | Operating cash generation relative to assets; low or negative values can indicate cash pressure. |
| Operating cash flow to average liabilities | $$OCF_a/\overline{L}_a$$ | Cash generation relative to obligations; this is not debt-service coverage because scheduled principal and interest are unavailable. |
| Negative income | $$\mathbb{1}(NI_a<0)$$ | Captures the loss threshold separately from return on assets; a value of one generally suggests higher risk. |
| Negative operating cash flow | $$\mathbb{1}(OCF_a<0)$$ | Identifies operations that consume cash, while allowing that one negative year may reflect temporary working-capital investment. |
| Log assets | $$\ln(TA_t)$$ | Controls for company size on a compressed scale; larger firms may have diversification and funding advantages, but are not necessarily safer. |

These expected relationships are economic priors rather than causal claims. Models determine whether the features are useful in the study data and can capture combinations that differ from the expected direction.

All ratio components are matched to compatible reporting dates and periods. Balance-sheet values refer to the same date, annual flows cover the same period, and change features use the closest comparable balance about one year earlier. Quarterly cumulative values are not added and missing amounts are not treated as zero.

Interest coverage is not included because the available SEC tags could not support a sufficiently reliable and consistent calculation. Industry and reporting age are retained for auditing but are not model features.

## 3.5 Data Quality and Preprocessing

SEC filings do not provide every accounting value for every company and period. The study therefore applies clear rules for deciding which monthly observations can be used and how missing feature values are handled.

### 3.5.1 Which Company-Months Are Included

A company-month enters the labeled dataset only when:

- the company is still within its observed SEC reporting history;
- total assets are available and greater than zero;
- annual operating cash flow is available;
- the latest balance sheet is no more than 180 days old;
- the latest annual cash-flow period ended no more than 540 days earlier; and
- the 60-day outcome can be determined using the rules in Section 3.3.

These age limits prevent the model from relying on financial statements that are too old. Whether information was public at the decision date is determined from its filing date, as explained in Section 3.2.

The filters reduce the initial monthly grid as follows. They are applied in order, so every removed observation appears in only one row.

| Filter | Rows removed | Rows remaining |
|---|---:|---:|
| Initial company-month grid | — | 1,958,220 |
| Remove months outside each company's observed reporting history | 1,014,086 | 944,134 |
| Remove months without usable and sufficiently recent required financial data | 332,429 | 611,705 |
| Remove months whose 60-day outcome cannot be labeled reliably | 46,483 | 565,222 |

*Source: primary model experiment panel audit. These counts are calculated before the later time-based filtering described in Chapter 4.*

### 3.5.2 Missing Feature Values

An included company-month does not need to have all twelve model features. For example, assets and annual operating cash flow may be available while liabilities or a comparable balance from the previous year are missing. A ratio is also missing when its denominator is zero or negative.

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

*A company-month can be missing more than one feature, so these counts must not be added together.*

Leverage change has the most missing values because it requires both assets and liabilities at two comparable dates about one year apart. Log assets and the negative-operating-cash-flow indicator have no missing values because assets and annual operating cash flow are required before a company-month can enter the dataset.

The model pipeline requires a numeric value for every feature. During training, each missing value is therefore replaced with the median observed in the relevant training data. The model also receives a separate yes-or-no indicator showing that the original value was missing. The same training median is then used for later observations, so evaluation data cannot influence preprocessing. This procedure makes modeling possible; it does not estimate the company's actual missing accounting value.

Negative working capital, income and operating cash flow are kept because they can be important warning signs. Very large or small ratios are also kept rather than capped or removed. This preserves reported information but leaves the models, especially logistic regression, more sensitive to unusual values.

### 3.5.3 Data Required for the Credit-Limit Policy

The credit-limit calculation has stricter requirements than the prediction model. It needs observed values for:

- total assets;
- annual revenue;
- annual operating cash flow; and
- cash.

These values directly determine a monetary limit, so missing amounts are not replaced with medians or zeros. Assets must be positive, revenue and cash cannot be negative, and all four values must be valid numbers. Operating cash flow may be negative because this can reflect genuine financial weakness.

The policy evaluation can also include a company with a disclosure already known at the decision date. Such a case is not used to predict a new event, but the known disclosure activates a rule that prevents the policy from offering credit. The policy sample therefore differs from the labeled model sample; Chapter 7 reports it separately.

## 3.6 Data Limitations

The panel is monthly, but companies normally report only quarterly or annually. Financial values are therefore repeated until a new filing appears, and the model cannot observe changes occurring between filings.

Accounting formats also differ across companies. This thesis combines Company Facts with Financial Statement and Notes data to recover some missing balance-sheet values, but missing, conflicting or incorrectly reported amounts can remain.

The outcome is an SEC disclosure proxy, not a verified default. Item 1.03 covers different situations, Item 2.04 reviews were automated without a separate human validation sample, and some cases remain unresolved. Companies with disrupted reporting may also be excluded. The results should therefore be interpreted as predictions of the defined disclosure outcome, not exact default probabilities.
