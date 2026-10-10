# Appendix C: Supplementary Empirical Results

These tables are generated from the completed real-data run. Probabilities and metrics are decimal fractions unless marked as percentages. The selection rule accepted random forest. The 2023–2025 period was excluded from this run's development steps but was examined during earlier project work.

## C.1 2023–2025 probability error for raw and selected mappings

| Model | Raw Brier | Selected mapping | Selected Brier |
|---|---|---|---|
| logistic | 0.22550257 | sigmoid | 0.00239526 |
| logistic_l2 | 0.22569930 | sigmoid | 0.00239527 |
| random_forest | 0.00238402 | identity | 0.00238402 |
| xgboost | 0.00253554 | identity | 0.00253554 |

Raw diagnostic threshold metrics use 0.5; selected mappings use the frozen selection threshold. Probability metrics do not depend on that threshold. Sigmoid calibration worsened the forest's selection-period Brier score, so the workflow retained its raw identity mapping.

## C.2 Company-cluster 95% percentile intervals

| Model | ROC-AUC interval | Average-precision interval | Brier interval |
|---|---|---|---|
| constant | 0.500000–0.500000 | 0.002047–0.002840 | 0.002043–0.002834 |
| logistic | 0.800836–0.853708 | 0.008233–0.014039 | 0.002036–0.002818 |
| logistic_l2 | 0.800654–0.853572 | 0.008229–0.014028 | 0.002036–0.002818 |
| random_forest | 0.866808–0.906122 | 0.018166–0.043783 | 0.002040–0.002799 |
| xgboost | 0.877637–0.911803 | 0.019735–0.044050 | 0.002203–0.002981 |

All models use 500 valid bootstrap repetitions. These intervals condition on fitted models and omit shared time shocks and model-selection uncertainty. They are not paired confidence intervals for model differences.

## C.3 2023–2025 episode detection at frozen thresholds

| Model | Threshold | Disclosure episodes detected | Total disclosure episodes | Episode-level recall |
|---|---|---|---|---|
| constant | 0.500000 | 0 | 176 | 0.00% |
| logistic | 0.009686 | 41 | 176 | 23.30% |
| logistic_l2 | 0.009659 | 41 | 176 | 23.30% |
| random_forest | 0.057971 | 18 | 176 | 10.23% |
| xgboost | 0.135778 | 13 | 176 | 7.39% |

An episode is detected if at least one of its positive monthly rows meets the model's threshold. This differs from row-level recall and does not measure detection of every legal bankruptcy or missed payment.

## C.4 Predictor distributions before chronological purging

| Predictor | Missing | 1st percentile | Median | 99th percentile |
|---|---|---|---|---|
| current_ratio | 4.85% | 0.0019061 | 1.7141 | 31.241 |
| cash_and_equivalents_to_assets | 9.03% | 9.6418e-05 | 0.10637 | 1 |
| liabilities_to_assets | 9.31% | 0.027222 | 0.56278 | 290.5 |
| assets_growth_12m | 4.65% | -0.92592 | 0.031744 | 94.167 |
| liabilities_to_assets_change_12m | 15.56% | -73.722 | 0.0079779 | 109.71 |
| working_capital_to_assets | 4.83% | -165.96 | 0.14869 | 0.93218 |
| return_on_average_assets | 4.81% | -84.883 | -0.01577 | 0.59834 |
| operating_cashflow_to_average_assets | 0.98% | -22.07 | 0.035852 | 0.44951 |
| operating_cashflow_to_average_liabilities | 10.58% | -8.4778 | 0.048107 | 1.9589 |
| negative_net_income | 3.94% | 0 | 1 | 1 |
| negative_operating_cashflow | 0.00% | 0 | 0 | 1 |
| log_assets | 0.00% | 6.731 | 19.451 | 25.154 |

The full minima/maxima and quality flags are in feature_summary.csv and data_summary.json. Extreme ratios are retained; these summaries do not certify source accounting quality.

## C.5 Full policy sensitivity

| Scenario | Mean limit/assets | Zero limits | Mean absolute change/assets |
|---|---|---|---|
| base | 0.6678% | 3.55% | 0.02904% |
| revenue_fraction_0.1 | 0.5934% | 3.55% | 0.02593% |
| revenue_fraction_0.3 | 0.6868% | 3.55% | 0.03049% |
| cashflow_fraction_0.25 | 0.6207% | 3.55% | 0.02471% |
| cashflow_fraction_0.75 | 0.6879% | 3.55% | 0.02958% |
| cash_fraction_0.05 | 0.5925% | 3.55% | 0.02855% |
| cash_fraction_0.15 | 0.7031% | 3.55% | 0.02918% |
| risk_sensitivity_5 | 0.6716% | 3.55% | 0.02911% |
| risk_sensitivity_20 | 0.6595% | 3.55% | 0.02897% |
| increase_smoothing_0.25 | 0.6561% | 3.55% | 0.02733% |
| increase_smoothing_1 | 0.6752% | 3.55% | 0.03066% |
| monthly_increase_cap_0.05 | 0.6489% | 3.55% | 0.02678% |
| monthly_increase_cap_0.2 | 0.6848% | 3.55% | 0.03111% |
| increase_deadband_0 | 0.6684% | 3.55% | 0.02925% |
| increase_deadband_0.05 | 0.6652% | 3.55% | 0.02858% |
| cash_eligible_half | 0.5925% | 3.55% | 0.02855% |
| cash_eligible_zero | 0.3115% | 48.30% | 0.01743% |
| cap_assets_0.005 | 0.3884% | 3.55% | 0.01602% |
| cap_assets_0.02 | 0.9540% | 3.55% | 0.04155% |
| additional_debt_assets_0.005 | 0.4288% | 36.48% | 0.01936% |
| probability_doubled | 0.6595% | 3.55% | 0.02897% |
| capacity_only | 0.6751% | 3.55% | 0.02919% |
| exploratory_logistic | 0.6669% | 3.55% | 0.02906% |
| exploratory_logistic_l2 | 0.6669% | 3.55% | 0.02906% |
| exploratory_random_forest | 0.6678% | 3.55% | 0.02904% |
| exploratory_xgboost | 0.6658% | 3.55% | 0.02919% |
| fixed_initial | 0.6786% | 2.78% | 0.02107% |
| unsmoothed | 0.7399% | 2.93% | 0.04227% |

The base scenario uses the selected random-forest disclosure probability. The base and capacity-only scenarios share monthly safeguards. The independent unsmoothed formula can reopen after zero, while the base cannot do so automatically. Other model mappings are comparisons. Additional-debt, cash, exposure and cap values remain assumptions rather than observed facility terms.

## C.6 Evidence files

Full local paths and hashes are in tables/source_crosswalk.csv. Small evidence copies are in tables/. Complete row-level predictions and policy histories remain under results/. File references: metrics.csv, bootstrap_intervals.json, annual_test_metrics.csv, event_detection.csv, feature_summary.csv, feature_correlations.csv, sector_summary.csv, policy_sensitivity.csv.
