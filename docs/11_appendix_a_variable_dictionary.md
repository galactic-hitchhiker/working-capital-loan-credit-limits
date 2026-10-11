# Appendix A: Variable Dictionary

The empirical study uses USD, standard US-GAAP tags and Forms 10-K, 10-Q and their amendments. Financial facts must have a filing date strictly before the decision date. Conflicting selected values remain missing.

## A.1 Financial fields

| Field | Source or definition | Timing and treatment |
|---|---|---|
| assets | Assets | Latest known balance-sheet date; positive assets required |
| liabilities | Direct Liabilities; otherwise reconciled statement calculation or complete same-filing components | Same balance date as assets; derivation basis and components retained in provenance |
| current_assets | AssetsCurrent or SEC Financial Statement and Notes facts | Same balance date as assets |
| current_liabilities | LiabilitiesCurrent or SEC Financial Statement and Notes facts | Same balance date as assets |
| reported_cash | CashAndCashEquivalentsAtCarryingValue or SEC Financial Statement and Notes facts | Same balance date; not verified eligible cash |
| operating_cashflow_annual | NetCashProvidedByUsedInOperatingActivities | Latest known annual period spanning 330–400 days |
| revenue_annual | RevenueFromContractWithCustomerExcludingAssessedTax; RevenueFromContractWithCustomerIncludingAssessedTax; Revenues; SalesRevenueNet | Exact same annual start/end as operating cash flow; conflicting same-vintage totals remain missing |
| net_income | NetIncomeLoss | Same annual period as operating cash flow |
| current_ratio | Current assets / current liabilities | Denominator must be positive; missing inputs remain missing |
| cash_and_equivalents_to_assets | Cash and cash equivalents / assets | Same balance date; direct or conservatively reconstructed cash total |
| liabilities_to_assets | Total liabilities / assets | Same balance date; leverage predictor |
| assets_growth_12m | (Latest total assets − prior-year total assets) / prior-year total assets | Prior balance end must be 330–400 days before the current balance end |
| liabilities_to_assets_change_12m | Current liabilities/assets − prior-year liabilities/assets | Prior assets and liabilities use the same comparable balance date |
| working_capital_to_assets | (Current assets − current liabilities) / assets | Negative values allowed |
| return_on_average_assets | Annual net income / mean of opening and closing assets | Opening date is one day before annual start; closing date is annual end |
| operating_cashflow_to_average_assets | Annual operating cash flow / mean of opening and closing assets | Flow and stock periods are matched |
| operating_cashflow_to_average_liabilities | Annual operating cash flow / mean of opening and closing liabilities | Flow and stock periods are matched; denominator must be positive |
| negative_net_income | One when annual net income is negative; zero otherwise | Missing when annual net income is unavailable |
| negative_operating_cashflow | One when annual operating cash flow is negative; zero otherwise | Missing when annual operating cash flow is unavailable |
| log_assets | Natural logarithm of total assets in USD | Used as size predictor |
| balance_age_days | Decision date minus balance period end | At most 180 days |
| flow_age_days | Decision date minus annual period end | At most 540 days |
| feature_available_on | Latest selected financial filing date plus one calendar day | Must be no later than decision |
| flow_basis | last_reported_annual_not_TTM | No reconstructed trailing twelve-month series |

The twelve configured ratio, trend, indicator and size fields enter model fitting. Current SIC is a sample screen, not a predictor. Company names, CIKs, filing accessions, event identifiers and outcome dates are not predictors. The narrower `cash_only_to_assets` value remains available for extraction audits but is not a configured predictor.

Negative current-ratio values and extreme ratios are retained in the fixed experiment and reported as data-quality limitations. The extractor checks source timing and period consistency; it does not certify every accounting value as economically valid.

File references: mcf/data/sec.py, mcf/data/point_in_time.py, feature_provenance.jsonl, feature_summary.csv.

## A.2 Target and panel fields

| Field | Meaning |
|---|---|
| company_id | Ten-digit SEC CIK |
| decision_date | First day of the observation month |
| event_type | disclosed_bankruptcy_or_payment_failure_within_60_days |
| episode_start | Filing date of a new qualifying Item 1.03 or reviewed Item 2.04 payment-failure episode; recorded in the disclosure inventory |
| event_id | Company, target and disclosure-episode start; present only for positive rows |
| horizon_days | 60 calendar days |
| horizon_end | Decision date plus 60 days |
| label | One for a new qualifying episode in the forward window; zero for no such episode with qualifying follow-up and no unresolved candidate |
| label_available_on | Day after full horizon for positives; day after first qualifying filing at/after horizon for negatives |
| label_source | Positive accession number or negative reporting-history reference |
| coverage_source | Main submissions file and referenced archives |
| known_disclosure | Recent qualifying episode known before the decision; used for policy hard stops in the separate features file |
| data_kind | empirical for the completed study |

The qualifying follow-up forms are 10-K, 10-Q, 8-K and their amendments. A zero label concerns observed reporting, not verified absence of payment default. Decisions during a known episode or its 90-day quiet gap do not enter predictive fitting; later episodes can enter.

## A.3 Policy inputs and outputs

| Input | Base scenario | Evidence status |
|---|---|---|
| Annual revenue and operating cash flow | Reported matching annual values | Observed financial facts |
| Eligible cash | 100% of reported cash | Eligibility assumption |
| Additional external debt payments within 60 days | Zero | Scenario assumption, not verified absence of payments |
| Hard cap | 1% of reported assets | Policy assumption |
| Outstanding facility exposure | Zero | Hypothetical facility assumption |
| Risk probability | Selected random-forest identity probability | Estimated probability of a new qualifying disclosure episode within 60 days |
| Previous limit | Prior assigned limit within the continuous segment | Simulation state |
| Information changed | Financial amounts, probability, cap or hard-stop state changed numerically | Computed review condition |
| Hard stop | Recent qualifying disclosure known before decision | Research eligibility rule during the episode quiet gap |
| New segment | First row or a gap in monthly observations | Fresh hypothetical assessment, not an observed reopening |

The policy outputs capacity, multiplier, preliminary limit, assigned limit, available credit, excess exposure, binding constraint and update reason. Outstanding exposure remains separate from the assigned limit.

The sensitivity cases change policy parameters, eligible cash, cap size, additional payments or probability. The selected random forest drives the base scenario; XGBoost and logistic mappings are model-comparison cases. Every probability refers to the defined disclosure event, never payment-default PD.

File references: mcf/policy/credit.py, mcf/policy/empirical.py, policy.sec_disclosure.json, policy_audit.json, comparison_paths.csv.
