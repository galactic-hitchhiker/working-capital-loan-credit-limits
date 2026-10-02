# Appendix D: Hypothetical Worked Policy Examples

These examples support Chapter 5 and are separate from the empirical results. The borrower, probabilities and facility amounts are hypothetical. Each row changes the original example independently; the rows are not a time sequence.

| Case | Capacity (USD) | Preliminary limit (USD) | Assigned limit (USD) | Available credit (USD) | Excess exposure (USD) |
|---|---|---|---|---|---|
| base | 100,000.00 | 81,873.08 | 75,936.54 | 15,936.54 | 0.00 |
| risk_stress | 100,000.00 | 44,932.90 | 44,932.90 | 0.00 | 15,067.10 |
| cashflow_stress | 50,000.00 | 40,936.54 | 40,936.54 | 0.00 | 19,063.46 |
| lower_hard_cap | 100,000.00 | 40,000.00 | 40,000.00 | 0.00 | 20,000.00 |
| no_new_information | 100,000.00 | 81,873.08 | 70,000.00 | 10,000.00 | 0.00 |
| hard_stop | 100,000.00 | 0.00 | 0.00 | 0.00 | 60,000.00 |

The base uses annual revenue of USD 12 million, operating cash flow of USD 1.2 million, eligible cash of USD 500,000, additional principal due of USD 50,000, a 2% illustrative event probability and a USD 150,000 cap. The previous limit is USD 70,000 and outstanding exposure is USD 60,000.

Risk stress raises the probability to 8%; cash-flow stress halves operating cash flow; the lower-cap case sets the cap to USD 40,000. The information case holds the previous limit, and the hard stop sets the assigned limit to zero. Neither a lower limit nor a hard stop removes outstanding exposure.

The separate sensitivity.csv contains 18 combinations of risk probability and risk sensitivity for this hypothetical borrower. It is not the empirical policy_sensitivity.csv. File references: policy_examples.py, credit_policy.py, worked_examples.csv, sensitivity.csv.
