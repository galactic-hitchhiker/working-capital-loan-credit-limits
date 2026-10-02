# Appendix C: Supplementary Empirical Results

These tables are generated from the completed real-data run. Probabilities and metrics are decimal fractions unless marked as percentages. The selection rule accepted random forest.

## C.1 Held-out probability error for raw and selected mappings

| Model | Raw Brier | Selected mapping | Selected Brier |
|---|---|---|---|
| logistic | 0.21244017 | sigmoid | 0.00210242 |
| logistic_l2 | 0.21248288 | sigmoid | 0.00210243 |
| random_forest | 0.00208715 | identity | 0.00208715 |
| xgboost | 0.14496754 | sigmoid | 0.00208964 |

Raw diagnostic threshold metrics use 0.5; selected mappings use the frozen selection threshold. Probability metrics do not depend on that threshold. Sigmoid calibration worsened the forest's selection-period Brier score, so the workflow retained its raw identity mapping.

## C.2 Company-cluster 95% percentile intervals

| Model | ROC-AUC interval | Average-precision interval | Brier interval |
|---|---|---|---|
| constant | 0.500000–0.500000 | 0.001774–0.002456 | 0.001771–0.002452 |
| logistic | 0.797350–0.847876 | 0.007193–0.013866 | 0.001765–0.002439 |
| logistic_l2 | 0.797169–0.847690 | 0.007180–0.013839 | 0.001765–0.002439 |
| random_forest | 0.893416–0.924268 | 0.019284–0.049572 | 0.001750–0.002420 |
| xgboost | 0.893687–0.926593 | 0.021421–0.056022 | 0.001761–0.002419 |

All models use 500 valid bootstrap repetitions. These intervals condition on fitted models and omit shared time shocks and model-selection uncertainty. They are not paired confidence intervals for model differences.

## C.3 Held-out event detection at frozen thresholds

| Model | Threshold | Event companies detected | Total event companies | Company-level recall |
|---|---|---|---|---|
| constant | 0.500000 | 0 | 160 | 0.00% |
| logistic | 0.024204 | 2 | 160 | 1.25% |
| logistic_l2 | 0.023949 | 2 | 160 | 1.25% |
| random_forest | 0.041010 | 24 | 160 | 15.00% |
| xgboost | 0.033276 | 32 | 160 | 20.00% |

A company is detected if at least one positive monthly row meets its model's threshold. This differs from row-level recall and does not measure detection of every legal bankruptcy.

## C.4 Predictor distributions before chronological purging

| Predictor | Missing | 1st percentile | Median | 99th percentile |
|---|---|---|---|---|
| current_ratio | 4.89% | 0.0020196 | 1.7175 | 30.897 |
| cash_and_equivalents_to_assets | 8.99% | 9.9618e-05 | 0.10578 | 1 |
| liabilities_to_assets | 17.79% | 0.031022 | 0.56044 | 230.85 |
| assets_growth_12m | 4.70% | -0.92244 | 0.031516 | 75.967 |
| liabilities_to_assets_change_12m | 23.28% | -53.245 | 0.0079532 | 87.111 |
| working_capital_to_assets | 4.87% | -143.2 | 0.1501 | 0.93119 |
| return_on_average_assets | 6.62% | -79.18 | -0.014735 | 0.61328 |
| operating_cashflow_to_average_assets | 1.02% | -20.257 | 0.038156 | 0.44351 |
| operating_cashflow_to_average_liabilities | 18.47% | -7.5399 | 0.047204 | 1.8536 |
| negative_net_income | 5.71% | 0 | 1 | 1 |
| negative_operating_cashflow | 0.00% | 0 | 0 | 1 |
| log_assets | 0.00% | 6.9295 | 19.508 | 25.151 |

The full minima/maxima and quality flags are in feature_summary.csv and data_summary.json. Extreme ratios are retained; these summaries do not certify source accounting quality.

## C.5 Full policy sensitivity

| Scenario | Mean limit/assets | Zero limits | Mean absolute change/assets |
|---|---|---|---|
| base | 0.6527% | 5.69% | 0.02845% |
| revenue_fraction_0.1 | 0.5803% | 5.69% | 0.02538% |
| revenue_fraction_0.3 | 0.6714% | 5.69% | 0.02989% |
| cashflow_fraction_0.25 | 0.6066% | 5.69% | 0.02409% |
| cashflow_fraction_0.75 | 0.6725% | 5.69% | 0.02894% |
| cash_fraction_0.05 | 0.5791% | 5.69% | 0.02801% |
| cash_fraction_0.15 | 0.6871% | 5.69% | 0.02859% |
| risk_sensitivity_5 | 0.6561% | 5.69% | 0.02848% |
| risk_sensitivity_20 | 0.6453% | 5.69% | 0.02845% |
| increase_smoothing_0.25 | 0.6412% | 5.69% | 0.02678% |
| increase_smoothing_1 | 0.6599% | 5.69% | 0.03005% |
| monthly_increase_cap_0.05 | 0.6341% | 5.69% | 0.02623% |
| monthly_increase_cap_0.2 | 0.6695% | 5.69% | 0.03048% |
| increase_deadband_0 | 0.6533% | 5.69% | 0.02866% |
| increase_deadband_0.05 | 0.6501% | 5.69% | 0.02800% |
| cash_eligible_half | 0.5791% | 5.69% | 0.02801% |
| cash_eligible_zero | 0.3027% | 49.66% | 0.01714% |
| cap_assets_0.005 | 0.3796% | 5.69% | 0.01567% |
| cap_assets_0.02 | 0.9331% | 5.69% | 0.04054% |
| additional_debt_assets_0.005 | 0.4185% | 38.05% | 0.01882% |
| probability_doubled | 0.6453% | 5.69% | 0.02845% |
| capacity_only | 0.6593% | 5.69% | 0.02852% |
| exploratory_logistic | 0.6522% | 5.69% | 0.02846% |
| exploratory_logistic_l2 | 0.6522% | 5.69% | 0.02846% |
| exploratory_random_forest | 0.6527% | 5.69% | 0.02845% |
| exploratory_xgboost | 0.6500% | 5.69% | 0.02853% |
| fixed_initial | 0.6621% | 5.04% | 0.02041% |
| unsmoothed | 0.7226% | 5.24% | 0.04113% |

The base scenario uses the selected random-forest disclosure probability. The base and capacity-only scenarios share monthly safeguards. The independent unsmoothed formula can reopen after zero, while the base cannot do so automatically. Other model mappings are comparisons. Additional-debt, cash, exposure and cap values remain assumptions rather than observed facility terms.

## C.6 Evidence files

Full local paths and hashes are in tables/source_crosswalk.csv. Small evidence copies are in tables/. Complete row-level predictions and policy histories remain under results/. File references: metrics.csv, bootstrap_intervals.json, annual_test_metrics.csv, event_detection.csv, feature_summary.csv, feature_correlations.csv, sector_summary.csv, policy_sensitivity.csv.
