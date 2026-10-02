# Input Contracts

## SEC Empirical Workflow

The `dataset/` directory must contain:

- `companyfacts/CIK##########.json` files with US-GAAP facts, units, reporting periods, filing dates and accession identifiers;
- `submissions/CIK##########.json` files with filing form, date, accession and item information;
- any historical submission files referenced by the main submissions records.

The study configuration must define `data_kind`, decision dates, observation cutoff, 60-day horizon, stage boundaries and the ordered predictor list.

## Point-in-Time Rules

A financial fact can enter a monthly row only after its filing date. Balance-sheet facts must satisfy the configured age limit. Annual-flow facts must represent a valid annual period and satisfy their age limit. Restatements and duplicate facts are resolved deterministically, with source details written to provenance.

Outcome labels represent the first recorded Form 8-K or 8-K/A Item 1.03 disclosure within 60 calendar days. Negative labels require observable follow-up beyond the horizon. This label is not contractual payment default.

## Model Panel

Each labeled row requires a company identifier, decision date, label and label-availability date. Predictors may be missing and are imputed inside each fitting sample. Identifiers, names, filing references, event dates and future data are excluded from predictors.

The configured predictor set contains 12 fields: current ratio, cash and equivalents to assets, liabilities to assets, 12-month asset growth, 12-month change in liabilities to assets, working capital to assets, return on average assets, operating cash flow to average assets, operating cash flow to average liabilities, negative net income, negative operating cash flow and log assets.

## Policy Inputs

Policy replay requires revenue, operating cash flow, reported cash, assets, the selected event probability and the source dates needed for freshness checks. Facility exposure, additional payments and cash eligibility are scenario inputs when they are not observed. Missing required policy inputs cause exclusion; they are not silently replaced with zero.

The resulting limits are hypothetical unless facility-level exposure, utilization, repayment, default, recovery, loss, pricing and profitability data are supplied and validated.

