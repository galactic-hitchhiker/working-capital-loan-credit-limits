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

The predictive experiment uses twelve accounting features. Together they describe five broad aspects of a company: short-term liquidity, reliance on liabilities, recent financial change, profitability and cash generation, and company size. These measures were selected because each can reveal a different form of financial pressure and can be constructed consistently enough from the available SEC data.

The expected effects described below are starting assumptions, not guaranteed rules or causal claims. For example, a high-liability company may still be healthy, and rapid growth may be either a sign of success or excessive expansion. The models use the historical data to determine whether each feature is useful and how it interacts with the others.

In the formulas, $$CA$$ means current assets, $$CL$$ current liabilities, $$TA$$ total assets, $$L$$ total liabilities, $$Cash$$ cash and cash equivalents, $$NI$$ net income and $$OCF$$ operating cash flow. The latest value known at monthly decision date $$t$$ is used. The subscript $$t-12$$ refers to a comparable balance-sheet date about one year earlier, while $$a$$ refers to the latest complete annual period. Average assets and liabilities use the values at the beginning and end of that annual period.

### 3.4.1 Current Ratio

$$ \frac{CA_t}{CL_t} $$

**Meaning and purpose.** The current ratio compares resources expected to become cash relatively soon with obligations due relatively soon. It is included to show whether the company appears able to cover upcoming bills using its short-term resources.

**Expected impact.** A higher ratio is generally expected to indicate lower distress risk, while a low ratio can signal payment pressure. However, a high ratio is less reassuring when current assets mainly consist of slow-moving inventory or receivables that may be difficult to collect.

### 3.4.2 Cash to Assets

$$ \frac{Cash_t}{TA_t} $$

**Meaning and purpose.** This feature shows how much of the company's asset base is held as cash or cash equivalents. Cash provides an immediate buffer when revenue falls or payments become due. The measure is stricter than the current ratio because it does not count inventory or receivables as cash.

**Expected impact.** A higher cash share is generally expected to indicate lower short-term risk. The protection may be overstated when cash is restricted or needed to maintain normal operations.

### 3.4.3 Liabilities to Assets

$$ \frac{L_t}{TA_t} $$

**Meaning and purpose.** This feature shows how much of the company's assets are financed by obligations rather than owners' equity. Liabilities include more than bank loans. The ratio measures the overall financial burden and the size of the equity buffer available to absorb losses.

**Expected impact.** A higher ratio is generally expected to indicate greater distress risk because less of the asset base is supported by equity. However, normal liability levels differ between industries.

### 3.4.4 Asset Growth over 12 Months

$$ \frac{TA_t-TA_{t-12}}{TA_{t-12}} $$

**Meaning and purpose.** This feature shows whether the company's total asset base expanded or contracted over approximately one year. It can reveal asset sales, acquisitions, restructuring or rapid expansion that would not be visible from the current asset value alone.

**Expected impact.** Strong contraction may indicate distress or forced asset sales. Rapid growth may show successful expansion, but it may also increase risk when financed too aggressively. Therefore, no single direction is assumed.

### 3.4.5 Change in Liabilities to Assets over 12 Months

$$ \frac{L_t}{TA_t}-\frac{L_{t-12}}{TA_{t-12}} $$

**Meaning and purpose.** This feature shows whether liabilities became larger or smaller relative to assets during the year. A company's current ratio may appear acceptable while its financial position is worsening quickly, so the change provides information that the current level does not.

**Expected impact.** An increase is generally expected to indicate higher risk because the company is becoming more dependent on liabilities. A decrease is generally expected to indicate lower risk, although the reason for the change still matters.

### 3.4.6 Working Capital to Assets

$$ \frac{CA_t-CL_t}{TA_t} $$

**Meaning and purpose.** Working capital is the difference between short-term resources and short-term obligations. Dividing it by total assets makes companies of different sizes easier to compare. Unlike the current ratio, this feature shows the size of the short-term surplus or shortage relative to the whole business.

**Expected impact.** A larger positive value is generally expected to indicate lower risk. A negative value means that short-term obligations exceed short-term resources and may therefore indicate higher risk. The quality of inventory and receivables remains important.

### 3.4.7 Return on Average Assets

$$ \frac{NI_a}{\overline{TA}_a} $$

**Meaning and purpose.** Return on average assets compares annual profit or loss with the average assets used during the year. It shows whether the company generates accounting profit from its asset base and allows differently sized companies to be compared.

**Expected impact.** A higher positive return is generally expected to indicate lower risk. A low or negative return is expected to indicate higher risk because repeated losses weaken the company. Accounting profit does not necessarily mean that the company generated cash.

### 3.4.8 Operating Cash Flow to Average Assets

$$ \frac{OCF_a}{\overline{TA}_a} $$

**Meaning and purpose.** This feature compares cash generated by normal business operations with the average asset base. It shows whether the business itself produces cash instead of relying only on accounting profit, borrowing or asset sales.

**Expected impact.** A higher positive value is generally expected to indicate lower risk. A low or negative value may indicate that normal operations are consuming cash.

### 3.4.9 Operating Cash Flow to Average Liabilities

$$ \frac{OCF_a}{\overline{L}_a} $$

**Meaning and purpose.** This feature compares operating cash generation with the company's average total obligations. It indicates how large the internally generated cash flow is relative to liabilities.

**Expected impact.** A higher value is generally expected to indicate lower risk, while weak or negative cash flow relative to liabilities is expected to indicate higher risk. This is not a debt-service-coverage ratio because it does not compare cash with scheduled principal and interest payments.

### 3.4.10 Negative Income

$$ \mathbb{1}(NI_a<0) $$

**Meaning and purpose.** This indicator equals one when the company reports an annual accounting loss and zero otherwise. Moving from profit to loss may be an important warning by itself, so this feature captures that threshold separately from the size of return on assets.

**Expected impact.** A value of one is expected to indicate higher risk. A profit does not, however, prove that the company is financially safe.

### 3.4.11 Negative Operating Cash Flow

$$ \mathbb{1}(OCF_a<0) $$

**Meaning and purpose.** This indicator equals one when normal operations consume cash during the annual period. Such a company must fund operations using existing cash, new financing or asset sales. The feature captures the difference between generating and consuming cash separately from the size of the cash-flow ratios.

**Expected impact.** A value of one is generally expected to indicate higher risk, especially when negative operating cash flow continues over time. A single negative year may also result from temporary investment in inventory or other working capital.

### 3.4.12 Company Size (Log Assets)

$$ \ln(TA_t) $$

**Meaning and purpose.** This feature represents company size. The logarithm compresses the very large differences between small and large companies, preventing the largest companies from dominating the scale of the variable. Size may also reflect diversification, access to financing and resources available to absorb shocks.

**Expected impact.** Larger size is often expected to indicate lower risk, but this relationship is not guaranteed. Large companies can also have complex operations and substantial obligations. The feature therefore mainly controls for differences in company size.

**Feature construction rules.** All components of a ratio are matched to compatible reporting dates and periods. Balance-sheet values must refer to the same date, while income and cash-flow values must cover the same annual period. The 12-month change features use the closest comparable balance approximately one year earlier. Quarterly cumulative values are not added together, and missing amounts are not treated as zero. These rules apply to all twelve configured predictors.

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
